-- PayPause migration 004: production persistence corrections
-- Additive migration: preserves migrations 001-003.

-- 1. Subscription response requires this persisted value.
ALTER TABLE public.subscriptions
ADD COLUMN IF NOT EXISTS monthly_equivalent_cost numeric(14,2);

-- 2. Explicit ownership for experiment records.
ALTER TABLE public.experiment_assignments
ADD COLUMN IF NOT EXISTS owner_user_id uuid
REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE public.experiment_submissions
ADD COLUMN IF NOT EXISTS owner_user_id uuid
REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE public.experiment_events
ADD COLUMN IF NOT EXISTS owner_user_id uuid
REFERENCES auth.users(id) ON DELETE CASCADE;

-- Existing legacy rows may not have an unambiguous owner.
-- NOT VALID preserves those rows but enforces ownership for new writes.
ALTER TABLE public.experiment_assignments
ADD CONSTRAINT experiment_assignments_owner_required
CHECK (owner_user_id IS NOT NULL) NOT VALID;

ALTER TABLE public.experiment_submissions
ADD CONSTRAINT experiment_submissions_owner_required
CHECK (owner_user_id IS NOT NULL) NOT VALID;

ALTER TABLE public.experiment_events
ADD CONSTRAINT experiment_events_owner_required
CHECK (owner_user_id IS NOT NULL) NOT VALID;

-- Replace global uniqueness with owner-scoped uniqueness.
ALTER TABLE public.experiment_assignments
DROP CONSTRAINT IF EXISTS experiment_assignments_participant_id_experiment_name_key;

ALTER TABLE public.experiment_assignments
ADD CONSTRAINT experiment_assignments_owner_participant_experiment_key
UNIQUE (owner_user_id, participant_id, experiment_name);

ALTER TABLE public.experiment_submissions
DROP CONSTRAINT IF EXISTS experiment_submissions_scoped_key_key;

CREATE UNIQUE INDEX IF NOT EXISTS
experiment_submissions_owner_scoped_key_uidx
ON public.experiment_submissions (owner_user_id, scoped_key);

CREATE INDEX IF NOT EXISTS experiment_assignments_owner_idx
ON public.experiment_assignments (owner_user_id, experiment_name);

CREATE INDEX IF NOT EXISTS experiment_submissions_owner_idx
ON public.experiment_submissions (owner_user_id, experiment_name);

CREATE INDEX IF NOT EXISTS experiment_events_owner_idx
ON public.experiment_events (owner_user_id, experiment_name);

-- 3. Preserve fields generated and validated by ExperimentService.
ALTER TABLE public.experiment_submissions
ADD COLUMN IF NOT EXISTS start_timestamp text;

ALTER TABLE public.experiment_submissions
ADD COLUMN IF NOT EXISTS details jsonb NOT NULL DEFAULT '{}'::jsonb;

-- 4. Atomic, owner-scoped submission + event persistence.
-- The service-generated submission ID and event IDs are retained.
CREATE OR REPLACE FUNCTION public.submit_experiment_atomically_v2(
    p_owner_user_id uuid,
    p_submission jsonb,
    p_events jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_submission public.experiment_submissions%ROWTYPE;
    v_event public.experiment_events%ROWTYPE;
    v_events jsonb := '[]'::jsonb;
    v_inserted integer;
    v_participant_id text;
    v_experiment_name text;
    v_submission_id text;
    v_scoped_key text;
    v_event_json jsonb;
BEGIN
    IF p_owner_user_id IS NULL THEN
        RAISE EXCEPTION 'Owner user ID is required';
    END IF;

    IF p_submission IS NULL OR jsonb_typeof(p_submission) <> 'object' THEN
        RAISE EXCEPTION 'A valid submission object is required';
    END IF;

    IF p_events IS NULL OR jsonb_typeof(p_events) <> 'array' THEN
        RAISE EXCEPTION 'Events must be a JSON array';
    END IF;

    v_participant_id := p_submission->>'participant_id';
    v_experiment_name := p_submission->>'experiment_name';
    v_submission_id := p_submission->>'id';
    v_scoped_key := p_submission->>'scoped_key';

    IF v_participant_id IS NULL
       OR v_participant_id <> p_owner_user_id::text THEN
        RAISE EXCEPTION 'Participant does not match authenticated owner';
    END IF;

    IF v_submission_id IS NULL OR v_scoped_key IS NULL
       OR v_experiment_name IS NULL THEN
        RAISE EXCEPTION 'Submission ID, scoped key and experiment name are required';
    END IF;

    INSERT INTO public.experiment_submissions (
        id,
        scoped_key,
        owner_user_id,
        participant_id,
        experiment_name,
        scenario_id,
        variant,
        selected_answer,
        selected_action,
        is_correct,
        score,
        feedback,
        abandoned,
        metadata,
        submitted_at,
        start_timestamp,
        details
    )
    VALUES (
        v_submission_id,
        v_scoped_key,
        p_owner_user_id,
        v_participant_id,
        v_experiment_name,
        p_submission->>'scenario_id',
        p_submission->>'variant',
        p_submission->>'selected_answer',
        p_submission->>'selected_action',
        COALESCE((p_submission->>'is_correct')::boolean, false),
        COALESCE((p_submission->>'score')::numeric, 0),
        COALESCE(p_submission->>'feedback', ''),
        COALESCE((p_submission->>'abandoned')::boolean, false),
        COALESCE(p_submission->'metadata', '{}'::jsonb),
        COALESCE((p_submission->>'submitted_at')::timestamptz, now()),
        p_submission->>'start_timestamp',
        COALESCE(p_submission->'details', '{}'::jsonb)
    )
    ON CONFLICT (owner_user_id, scoped_key) DO NOTHING;

    GET DIAGNOSTICS v_inserted = ROW_COUNT;

    IF v_inserted = 0 THEN
        SELECT *
        INTO v_submission
        FROM public.experiment_submissions
        WHERE owner_user_id = p_owner_user_id
          AND scoped_key = v_scoped_key;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Conflicting submission could not be retrieved';
        END IF;

        RETURN jsonb_build_object(
            'is_new', false,
            'submission', to_jsonb(v_submission),
            'events', '[]'::jsonb
        );
    END IF;

    -- Events are inserted only after a new submission succeeds.
    FOR v_event_json IN
        SELECT value FROM jsonb_array_elements(p_events)
    LOOP
        IF v_event_json->>'participant_id' IS DISTINCT FROM v_participant_id
           OR v_event_json->>'experiment_name' IS DISTINCT FROM v_experiment_name
           OR v_event_json->>'submission_id' IS DISTINCT FROM v_submission_id THEN
            RAISE EXCEPTION 'Experiment event does not belong to this submission';
        END IF;

        INSERT INTO public.experiment_events (
            event_id,
            owner_user_id,
            experiment_name,
            participant_id,
            metric_name,
            event_data,
            created_at
        )
        VALUES (
            COALESCE(v_event_json->>'event_id',
                     'evt_' || replace(gen_random_uuid()::text, '-', '')),
            p_owner_user_id,
            v_experiment_name,
            v_participant_id,
            v_event_json->>'metric_name',
            v_event_json,
            COALESCE((v_event_json->>'created_at')::timestamptz, now())
        )
        RETURNING * INTO v_event;

        v_events := v_events || jsonb_build_array(to_jsonb(v_event));
    END LOOP;

    SELECT *
    INTO v_submission
    FROM public.experiment_submissions
    WHERE owner_user_id = p_owner_user_id
      AND id = v_submission_id;

    RETURN jsonb_build_object(
        'is_new', true,
        'submission', to_jsonb(v_submission),
        'events', v_events
    );
END;
$$;

REVOKE ALL ON FUNCTION public.submit_experiment_atomically_v2(uuid, jsonb, jsonb)
FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.submit_experiment_atomically_v2(uuid, jsonb, jsonb)
TO service_role;

-- 5. Backfill subscription monthly equivalents.
UPDATE public.subscriptions
SET monthly_equivalent_cost = ROUND(
    CASE frequency
        WHEN 'weekly' THEN amount * 52 / 12
        WHEN 'monthly' THEN amount
        WHEN 'quarterly' THEN amount / 3
        WHEN 'yearly' THEN amount / 12
        ELSE amount
    END, 2
)
WHERE monthly_equivalent_cost IS NULL;

ALTER TABLE public.subscriptions
ALTER COLUMN monthly_equivalent_cost SET NOT NULL;

-- 6. Safely recover legacy experiment ownership.
-- Only associate a participant with an owner when participant_id is a UUID
-- that actually exists in auth.users. Never guess an owner.
UPDATE public.experiment_assignments AS e
SET owner_user_id = u.id
FROM auth.users AS u
WHERE e.owner_user_id IS NULL
  AND e.participant_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  AND e.participant_id::uuid = u.id;

UPDATE public.experiment_submissions AS e
SET owner_user_id = u.id
FROM auth.users AS u
WHERE e.owner_user_id IS NULL
  AND e.participant_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  AND e.participant_id::uuid = u.id;

UPDATE public.experiment_events AS e
SET owner_user_id = u.id
FROM auth.users AS u
WHERE e.owner_user_id IS NULL
  AND e.participant_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  AND e.participant_id::uuid = u.id;

-- 7. Keep unresolved legacy records quarantined.
-- The NOT VALID owner constraints still reject new rows without owners.
-- Existing unresolvable rows remain inaccessible to owner-scoped queries.


-- 8. Atomic recovery incident creation.
CREATE OR REPLACE FUNCTION public.create_recovery_incident_atomically(
    p_user_id uuid,
    p_incident jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_incident public.recovery_incidents%ROWTYPE;
    v_key text;
    v_provider text;
    v_transaction_ref text;
    v_fingerprint text;
BEGIN
    IF p_user_id IS NULL OR p_incident IS NULL
       OR jsonb_typeof(p_incident) <> 'object' THEN
        RAISE EXCEPTION 'Valid user and incident are required';
    END IF;

    v_key := NULLIF(p_incident->>'idempotency_key', '');
    v_provider := lower(btrim(p_incident->>'provider'));
    v_transaction_ref := NULLIF(lower(btrim(p_incident->>'transaction_ref')), '');

    -- Serialize equivalent create requests for this user.
    v_fingerprint := concat_ws('|',
        p_user_id::text,
        p_incident->>'category',
        v_provider,
        p_incident->>'amount',
        p_incident->>'incident_datetime',
        COALESCE(v_transaction_ref, '<none>')
    );
    PERFORM pg_advisory_xact_lock(hashtextextended(v_fingerprint, 0));

    IF v_key IS NOT NULL THEN
        SELECT * INTO v_incident
        FROM public.recovery_incidents
        WHERE user_id = p_user_id AND idempotency_key = v_key;

        IF FOUND THEN
            RETURN jsonb_build_object(
                'incident', to_jsonb(v_incident),
                'is_duplicate', true
            );
        END IF;
    END IF;

    -- A transaction reference must match on both sides, or be absent on both.
    SELECT * INTO v_incident
    FROM public.recovery_incidents
    WHERE user_id = p_user_id
      AND category = p_incident->>'category'
      AND lower(btrim(provider)) = v_provider
      AND abs(amount - (p_incident->>'amount')::numeric) <= 0.001
      AND incident_datetime = (p_incident->>'incident_datetime')::timestamptz
      AND (
          (NULLIF(lower(btrim(transaction_ref)), '') IS NULL
           AND v_transaction_ref IS NULL)
          OR
          (NULLIF(lower(btrim(transaction_ref)), '') = v_transaction_ref
           AND v_transaction_ref IS NOT NULL)
      )
    ORDER BY created_at DESC
    LIMIT 1;

    IF FOUND THEN
        RETURN jsonb_build_object(
            'incident', to_jsonb(v_incident),
            'is_duplicate', true
        );
    END IF;

    INSERT INTO public.recovery_incidents (
        id, user_id, category, incident_datetime, provider,
        transaction_ref, amount, currency, description, status,
        evidence_references, timeline, follow_up_date,
        credentials_disclosed, idempotency_key,
        latest_complaint_draft, created_at, updated_at
    )
    VALUES (
        COALESCE(p_incident->>'id',
            'inc_' || replace(gen_random_uuid()::text, '-', '')),
        p_user_id,
        p_incident->>'category',
        (p_incident->>'incident_datetime')::timestamptz,
        p_incident->>'provider',
        NULLIF(p_incident->>'transaction_ref', ''),
        (p_incident->>'amount')::numeric,
        COALESCE(p_incident->>'currency', 'INR'),
        p_incident->>'description',
        COALESCE(p_incident->>'status', 'reported'),
        COALESCE(p_incident->'evidence_references', '[]'::jsonb),
        COALESCE(p_incident->'timeline', '[]'::jsonb),
        NULLIF(p_incident->>'follow_up_date', '')::date,
        COALESCE(p_incident->>'credentials_disclosed', 'not_sure'),
        v_key,
        NULL,
        now(),
        now()
    )
    RETURNING * INTO v_incident;

    RETURN jsonb_build_object(
        'incident', to_jsonb(v_incident),
        'is_duplicate', false
    );
END;
$$;

-- 9. Owner-scoped incident updates. Status changes append timeline events
-- without replacing existing evidence or complaint drafts.
CREATE OR REPLACE FUNCTION public.update_recovery_incident_atomically(
    p_user_id uuid,
    p_incident_id text,
    p_fields jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_incident public.recovery_incidents%ROWTYPE;
    v_old_status text;
    v_new_status text;
BEGIN
    SELECT * INTO v_incident
    FROM public.recovery_incidents
    WHERE id = p_incident_id AND user_id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    v_old_status := v_incident.status;
    v_new_status := COALESCE(p_fields->>'status', v_old_status);

    UPDATE public.recovery_incidents
    SET
        status = v_new_status,
        description = COALESCE(p_fields->>'description', description),
        notes = CASE
            WHEN p_fields ? 'notes' THEN p_fields->>'notes'
            ELSE notes
        END,
        follow_up_date = CASE
            WHEN p_fields ? 'follow_up_date'
            THEN NULLIF(p_fields->>'follow_up_date', '')::date
            ELSE follow_up_date
        END,
        credentials_disclosed = COALESCE(
            p_fields->>'credentials_disclosed', credentials_disclosed
        ),
        evidence_references = CASE
            WHEN p_fields ? 'evidence_references'
            THEN p_fields->'evidence_references'
            ELSE evidence_references
        END,
        updated_at = now(),
        timeline = CASE
            WHEN v_new_status IS DISTINCT FROM v_old_status THEN
                COALESCE(timeline, '[]'::jsonb) ||
                jsonb_build_array(jsonb_build_object(
                    'timestamp', now(),
                    'event', 'Status changed from ' || v_old_status || ' to ' || v_new_status,
                    'status', v_new_status
                ))
            ELSE COALESCE(timeline, '[]'::jsonb)
        END
    WHERE id = p_incident_id AND user_id = p_user_id
    RETURNING * INTO v_incident;

    RETURN to_jsonb(v_incident);
END;
$$;

-- 10. Atomic complaint draft persistence and timeline append.
CREATE OR REPLACE FUNCTION public.save_recovery_complaint_draft(
    p_user_id uuid,
    p_incident_id text,
    p_draft jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_incident public.recovery_incidents%ROWTYPE;
    v_draft jsonb;
BEGIN
    IF p_draft IS NULL OR jsonb_typeof(p_draft) <> 'object' THEN
        RAISE EXCEPTION 'A valid complaint draft is required';
    END IF;

    v_draft := p_draft ||
        jsonb_build_object(
            'incident_id', p_incident_id,
            'generated_at', COALESCE(p_draft->'generated_at', to_jsonb(now()))
        );

    UPDATE public.recovery_incidents
    SET
        latest_complaint_draft = v_draft,
        timeline = COALESCE(timeline, '[]'::jsonb) ||
            jsonb_build_array(jsonb_build_object(
                'timestamp', now(),
                'event', 'Complaint draft generated',
                'status', status
            )),
        updated_at = now()
    WHERE id = p_incident_id AND user_id = p_user_id
    RETURNING * INTO v_incident;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    RETURN v_draft;
END;
$$;

-- 11. Atomic evidence removal and timeline update.
CREATE OR REPLACE FUNCTION public.remove_recovery_evidence_atomically(
    p_user_id uuid,
    p_incident_id text,
    p_evidence_id text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_incident public.recovery_incidents%ROWTYPE;
    v_evidence jsonb;
    v_new_evidence jsonb;
BEGIN
    SELECT * INTO v_incident
    FROM public.recovery_incidents
    WHERE id = p_incident_id AND user_id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'incident_found', false,
            'evidence_found', false,
            'incident', NULL
        );
    END IF;

    SELECT value INTO v_evidence
    FROM jsonb_array_elements(
        COALESCE(v_incident.evidence_references, '[]'::jsonb)
    )
    WHERE value->>'id' = p_evidence_id
    LIMIT 1;

    IF v_evidence IS NULL THEN
        RETURN jsonb_build_object(
            'incident_found', true,
            'evidence_found', false,
            'incident', NULL
        );
    END IF;

    SELECT COALESCE(jsonb_agg(value), '[]'::jsonb)
    INTO v_new_evidence
    FROM jsonb_array_elements(
        COALESCE(v_incident.evidence_references, '[]'::jsonb)
    )
    WHERE value->>'id' <> p_evidence_id;

    UPDATE public.recovery_incidents
    SET
        evidence_references = v_new_evidence,
        timeline = COALESCE(timeline, '[]'::jsonb) ||
            jsonb_build_array(jsonb_build_object(
                'timestamp', now(),
                'event', 'Evidence removed: ' ||
                    COALESCE(v_evidence->>'title', 'Untitled') ||
                    ' (' || p_evidence_id || ')',
                'status', status
            )),
        updated_at = now()
    WHERE id = p_incident_id AND user_id = p_user_id
    RETURNING * INTO v_incident;

    RETURN jsonb_build_object(
        'incident_found', true,
        'evidence_found', true,
        'incident', to_jsonb(v_incident)
    );
END;
$$;

-- Restrict all recovery RPCs to the backend service role.
REVOKE ALL ON FUNCTION public.create_recovery_incident_atomically(uuid, jsonb)
FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.update_recovery_incident_atomically(uuid, text, jsonb)
FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.save_recovery_complaint_draft(uuid, text, jsonb)
FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.remove_recovery_evidence_atomically(uuid, text, text)
FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.create_recovery_incident_atomically(uuid, jsonb)
TO service_role;
GRANT EXECUTE ON FUNCTION public.update_recovery_incident_atomically(uuid, text, jsonb)
TO service_role;
GRANT EXECUTE ON FUNCTION public.save_recovery_complaint_draft(uuid, text, jsonb)
TO service_role;
GRANT EXECUTE ON FUNCTION public.remove_recovery_evidence_atomically(uuid, text, text)
TO service_role;

ALTER TABLE public.recovery_incidents
ADD COLUMN IF NOT EXISTS notes text;
