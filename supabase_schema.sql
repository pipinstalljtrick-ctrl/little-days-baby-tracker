create table if not exists public.baby_events (
  id text primary key,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

alter table public.baby_events enable row level security;

drop policy if exists "Caregivers can read their own family log" on public.baby_events;
create policy "Caregivers can read their own family log"
  on public.baby_events for select to authenticated
  using (auth.uid() = user_id);

drop policy if exists "Caregivers can add to their own family log" on public.baby_events;
create policy "Caregivers can add to their own family log"
  on public.baby_events for insert to authenticated
  with check (auth.uid() = user_id);

drop policy if exists "Caregivers can update their own family log" on public.baby_events;
create policy "Caregivers can update their own family log"
  on public.baby_events for update to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Caregivers can remove from their own family log" on public.baby_events;
create policy "Caregivers can remove from their own family log"
  on public.baby_events for delete to authenticated
  using (auth.uid() = user_id);