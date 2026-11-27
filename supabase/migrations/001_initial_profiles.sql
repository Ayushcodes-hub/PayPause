-- PayPause migration 001: User profiles
-- Supabase Auth remains the source of user identity.

create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    full_name text,
    avatar_url text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

comment on table public.profiles is
    'User profile information linked to Supabase Auth.';

-- Automatically create a profile when a user registers.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.profiles (id, full_name)
    values (
        new.id,
        nullif(trim(new.raw_user_meta_data ->> 'full_name'), '')
    )
    on conflict (id) do nothing;

    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_user();

-- Maintain updated_at whenever a profile is changed.
create or replace function public.set_profile_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists profiles_updated_at on public.profiles;

create trigger profiles_updated_at
before update on public.profiles
for each row
execute function public.set_profile_updated_at();

-- Enable row-level security.
alter table public.profiles enable row level security;

-- Remove broad access before granting only the required operations.
revoke all on table public.profiles from anon, authenticated;

grant select on table public.profiles to authenticated;

-- Allow the trusted backend service-role client to read profiles.
grant select on table public.profiles to service_role;
grant update (full_name, avatar_url)
on table public.profiles to authenticated;

drop policy if exists "Users can read their own profile"
on public.profiles;

create policy "Users can read their own profile"
on public.profiles
for select
to authenticated
using ((select auth.uid()) = id);

drop policy if exists "Users can update their own profile"
on public.profiles;

create policy "Users can update their own profile"
on public.profiles
for update
to authenticated
using ((select auth.uid()) = id)
with check ((select auth.uid()) = id);

-- Restrict direct execution of trigger functions.
revoke execute on function public.handle_new_user()
from public, anon, authenticated;

revoke execute on function public.set_profile_updated_at()
from public, anon, authenticated;
