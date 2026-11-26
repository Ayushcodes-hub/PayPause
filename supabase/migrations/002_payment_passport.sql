-- Payment Passport: private history of structured PayGuard assessments.
create table if not exists public.payment_passport_assessments (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    assessment_id text not null,
    risk_score integer not null check (risk_score between 0 and 100),
    risk_level text not null check (
        risk_level in ('low', 'moderate', 'high', 'critical')
    ),
    input_type text not null check (
        input_type in ('upi', 'url', 'both')
    ),
    assessment jsonb not null,
    created_at timestamptz not null default now(),
    unique (user_id, assessment_id)
);

create index if not exists idx_passport_user_created
on public.payment_passport_assessments (user_id, created_at desc);

alter table public.payment_passport_assessments enable row level security;

revoke all on public.payment_passport_assessments from anon, authenticated;
grant select, delete on public.payment_passport_assessments to authenticated;
grant select, insert, delete on public.payment_passport_assessments to service_role;

drop policy if exists "Users read own passport assessments"
on public.payment_passport_assessments;
create policy "Users read own passport assessments"
on public.payment_passport_assessments
for select to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users delete own passport assessments"
on public.payment_passport_assessments;
create policy "Users delete own passport assessments"
on public.payment_passport_assessments
for delete to authenticated
using ((select auth.uid()) = user_id);
