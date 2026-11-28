
-- PayPause migration 003: Persistent application modules
-- Existing Supabase Auth remains the source of user identity.
-- Backend service-role access must always scope queries by user_id.

create extension if not exists pgcrypto;

-- =========================================================
-- 1. PAYMENTS
-- =========================================================

create table if not exists public.payments (
    id text primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    transaction_ref text,
    provider text not null,
    merchant text not null,
    amount numeric(14,2) not null check (amount > 0),
    currency varchar(5) not null default 'INR',
    category varchar(50) not null default 'general',
    payment_date timestamptz not null,
    status text not null default 'completed',
    verification_status text not null default 'user_recorded',
    refund_status text not null default 'not_requested',
    refund_reference text,
    expected_refund_date date,
    refund_notes text,
    refund_requested_at timestamptz,
    linked_bill_id text,
    linked_incident_id text,
    notes varchar(500),
    duplicate_warning boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_payments_user_date
on public.payments(user_id, payment_date desc);

create index if not exists idx_payments_user_ref
on public.payments(user_id, transaction_ref);

create index if not exists idx_payments_user_refund
on public.payments(user_id, refund_status);

-- =========================================================
-- 2. SUBSCRIPTIONS
-- =========================================================

create table if not exists public.subscriptions (
    id text primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    amount numeric(14,2) not null check (amount >= 0),
    currency varchar(5) not null default 'INR',
    frequency text not null check (
        frequency in ('weekly', 'monthly', 'quarterly', 'yearly')
    ),
    start_date date not null,
    next_expected_date date,
    category varchar(50) not null default 'general',
    provider text,
    cancellation_reminder_days integer not null default 3,
    notes text,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_subscriptions_user_active
on public.subscriptions(user_id, is_active);

create index if not exists idx_subscriptions_user_next_date
on public.subscriptions(user_id, next_expected_date);

-- =========================================================
-- 3. RECOVERY INCIDENTS
-- =========================================================

create table if not exists public.recovery_incidents (
    id text primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    category text not null,
    incident_datetime timestamptz not null,
    provider text,
    transaction_ref text,
    amount numeric(14,2),
    currency varchar(5) not null default 'INR',
    description text not null,
    status text not null default 'reported',
    evidence_references jsonb not null default '[]'::jsonb,
    timeline jsonb not null default '[]'::jsonb,
    follow_up_date date,
    credentials_disclosed boolean not null default false,
    idempotency_key text,
    latest_complaint_draft jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint recovery_evidence_array
        check (jsonb_typeof(evidence_references) = 'array'),
    constraint recovery_timeline_array
        check (jsonb_typeof(timeline) = 'array')
);

create unique index if not exists idx_recovery_idempotency
on public.recovery_incidents(user_id, idempotency_key)
where idempotency_key is not null;

create index if not exists idx_recovery_user_created
on public.recovery_incidents(user_id, created_at desc);

create index if not exists idx_recovery_user_status
on public.recovery_incidents(user_id, status);

-- =========================================================
-- 4. EXPERIMENT ASSIGNMENTS
-- =========================================================

create table if not exists public.experiment_assignments (
    id uuid primary key default gen_random_uuid(),
    participant_id text not null,
    experiment_name text not null,
    feature_name text,
    variant text,
    traits jsonb not null default '{}'::jsonb,
    assigned_at timestamptz not null default now(),
    unique(participant_id, experiment_name)
);

create index if not exists idx_experiment_assignments_name
on public.experiment_assignments(experiment_name);

-- =========================================================
-- 5. EXPERIMENT SUBMISSIONS
-- =========================================================

create table if not exists public.experiment_submissions (
    id text primary key,
    scoped_key text not null unique,
    participant_id text not null,
    experiment_name text not null,
    scenario_id text not null,
    variant text,
    selected_answer text,
    selected_action text,
    is_correct boolean not null default false,
    score numeric(10,2) not null default 0,
    feedback text,
    abandoned boolean not null default false,
    metadata jsonb not null default '{}'::jsonb,
    submitted_at timestamptz not null default now()
);

create index if not exists idx_experiment_submissions_name
on public.experiment_submissions(experiment_name);

create index if not exists idx_experiment_submissions_participant
on public.experiment_submissions(participant_id);

-- =========================================================
-- 6. EXPERIMENT EVENTS
-- =========================================================

create table if not exists public.experiment_events (
    event_id text primary key,
    experiment_name text,
    participant_id text,
    metric_name text,
    event_data jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_experiment_events_name
on public.experiment_events(experiment_name);

create index if not exists idx_experiment_events_participant
on public.experiment_events(participant_id);

-- =========================================================
-- 7. ROW LEVEL SECURITY
-- =========================================================

alter table public.payments enable row level security;
alter table public.subscriptions enable row level security;
alter table public.recovery_incidents enable row level security;

alter table public.experiment_assignments enable row level security;
alter table public.experiment_submissions enable row level security;
alter table public.experiment_events enable row level security;

-- User-owned financial and recovery data: backend service role only.
revoke all on public.payments from anon, authenticated;
revoke all on public.subscriptions from anon, authenticated;
revoke all on public.recovery_incidents from anon, authenticated;

grant all on public.payments to service_role;
grant all on public.subscriptions to service_role;
grant all on public.recovery_incidents to service_role;

-- Experiments are also backend-managed.
revoke all on public.experiment_assignments from anon, authenticated;
revoke all on public.experiment_submissions from anon, authenticated;
revoke all on public.experiment_events from anon, authenticated;

grant all on public.experiment_assignments to service_role;
grant all on public.experiment_submissions to service_role;
grant all on public.experiment_events to service_role;

-- =========================================================
-- 8. ATOMIC EXPERIMENT SUBMISSION
-- =========================================================

create or replace function public.submit_experiment_atomically(
    p_submission jsonb,
    p_events jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_existing public.experiment_submissions%rowtype;
    v_new_id text;
    v_event jsonb;
    v_event_id text;
begin
    if nullif(p_submission ->> 'scoped_key', '') is null then
        raise exception 'scoped_key is required';
    end if;

    insert into public.experiment_submissions (
        id,
        scoped_key,
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
        metadata
    )
    values (
        'subm_' || replace(gen_random_uuid()::text, '-', ''),
        p_submission ->> 'scoped_key',
        p_submission ->> 'participant_id',
        p_submission ->> 'experiment_name',
        p_submission ->> 'scenario_id',
        p_submission ->> 'variant',
        p_submission ->> 'selected_answer',
        p_submission ->> 'selected_action',
        coalesce((p_submission ->> 'is_correct')::boolean, false),
        coalesce((p_submission ->> 'score')::numeric, 0),
        p_submission ->> 'feedback',
        coalesce((p_submission ->> 'abandoned')::boolean, false),
        coalesce(p_submission -> 'metadata', '{}'::jsonb)
    )
    on conflict (scoped_key) do nothing
    returning id into v_new_id;

    if v_new_id is null then
        select *
        into v_existing
        from public.experiment_submissions
        where scoped_key = p_submission ->> 'scoped_key';

        return jsonb_build_object(
            'is_new', false,
            'submission', to_jsonb(v_existing),
            'events', '[]'::jsonb
        );
    end if;

    if jsonb_typeof(coalesce(p_events, '[]'::jsonb)) <> 'array' then
        raise exception 'p_events must be an array';
    end if;

    for v_event in
        select value from jsonb_array_elements(coalesce(p_events, '[]'::jsonb))
    loop
        v_event_id := coalesce(
            nullif(v_event ->> 'event_id', ''),
            'evt_' || replace(gen_random_uuid()::text, '-', '')
        );

        insert into public.experiment_events (
            event_id,
            experiment_name,
            participant_id,
            metric_name,
            event_data
        )
        values (
            v_event_id,
            v_event ->> 'experiment_name',
            v_event ->> 'participant_id',
            v_event ->> 'metric_name',
            v_event
        );
    end loop;

    return jsonb_build_object(
        'is_new', true,
        'submission', (
            select to_jsonb(s)
            from public.experiment_submissions s
            where s.id = v_new_id
        ),
        'events', coalesce(p_events, '[]'::jsonb)
    );
end;
$$;

revoke all on function public.submit_experiment_atomically(jsonb, jsonb)
from public, anon, authenticated;

grant execute on function public.submit_experiment_atomically(jsonb, jsonb)
to service_role;
