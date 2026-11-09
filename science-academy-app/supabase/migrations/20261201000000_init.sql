-- Science Academy app: full schema.
--
-- Access model: every table has row level security ON. The browser never reads
-- tables directly except two realtime feeds (chat messages of groups the person
-- may read, and their own notifications). Everything else goes through the
-- Next.js server, which checks the permissions engine (role defaults + per
-- person overrides, src/lib/permissions.ts) and then uses the service role.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- People
-- ---------------------------------------------------------------------------

create type public.app_role as enum ('admin', 'management', 'reception', 'faculty', 'parent');

create table public.users (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique references auth.users (id) on delete set null,
  staff_id text unique,                 -- AD-01, MG-01, RC-01, FC-01; null for parents
  role public.app_role not null,
  name text not null,
  mobile text not null,                 -- 10 digits, no +91
  email text,
  status text not null default 'active' check (status in ('active', 'suspended')),
  created_at timestamptz not null default now(),
  constraint users_mobile_format check (mobile ~ '^[6-9][0-9]{9}$'),
  constraint users_staff_id_role check ((role = 'parent') = (staff_id is null))
);
-- A mobile number can belong to one staff login and one parent login at most.
create unique index users_mobile_role_kind on public.users (mobile, (role = 'parent'));

-- Running number per staff role: AD-01, MG-01, RC-01, FC-01.
create or replace function public.next_staff_id(p_role public.app_role)
returns text
language plpgsql
as $$
declare
  prefix text := case p_role
    when 'admin' then 'AD' when 'management' then 'MG'
    when 'reception' then 'RC' when 'faculty' then 'FC' end;
  n int;
begin
  if prefix is null then
    raise exception 'parents have no staff id';
  end if;
  select coalesce(max(substring(staff_id from 4)::int), 0) + 1 into n
  from public.users where staff_id like prefix || '-%';
  return prefix || '-' || lpad(n::text, 2, '0');
end $$;

-- One-time login codes (SMS). Only a hash is stored.
create table public.otp_codes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  code_hash text not null,
  expires_at timestamptz not null,
  attempts int not null default 0,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);
create index otp_codes_user on public.otp_codes (user_id, created_at desc);

-- Each signed-in device. Logout, "Log out everywhere" and suspend revoke rows;
-- a session not in this table (or revoked) is refused even if its token is valid.
create table public.login_sessions (
  session_id uuid primary key,          -- Supabase auth session id (JWT claim)
  user_id uuid not null references public.users (id) on delete cascade,
  user_agent text,
  created_at timestamptz not null default now(),
  revoked_at timestamptz
);
create index login_sessions_user on public.login_sessions (user_id);

-- ---------------------------------------------------------------------------
-- Batches
-- ---------------------------------------------------------------------------

create table public.batches (
  id uuid primary key default gen_random_uuid(),
  board text not null check (board in ('CB', 'MP')),
  class int not null check (class between 6 and 12),
  name text not null,                   -- PCB, PCM, Foundation...
  start_time text,                      -- "8:00 AM"
  active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (board, class, name, start_time)
);

create table public.faculty_batches (
  user_id uuid not null references public.users (id) on delete cascade,
  batch_id uuid not null references public.batches (id) on delete cascade,
  subject text,
  primary key (user_id, batch_id)
);

-- ---------------------------------------------------------------------------
-- Students and IDs
-- ---------------------------------------------------------------------------

-- The one academy-wide roll counter. Only ever goes up, so a number is never
-- reused (not after leaving, not after a deleted draft).
create table public.roll_counter (
  id boolean primary key default true check (id),
  last_roll int not null default 0
);
insert into public.roll_counter (id, last_roll) values (true, 0);

create or replace function public.allocate_roll()
returns int
language sql
as $$
  update public.roll_counter set last_roll = last_roll + 1 where id returning last_roll;
$$;

-- MP9-025-26. Roll is 3 digits zero padded; from 1000 it simply has 4 digits.
create or replace function public.format_student_id(p_board text, p_class int, p_roll int, p_session int)
returns text
language sql
immutable
as $$
  select p_board || p_class::text || '-' ||
         case when p_roll < 1000 then lpad(p_roll::text, 3, '0') else p_roll::text end ||
         '-' || lpad((p_session % 100)::text, 2, '0');
$$;

create table public.students (
  id uuid primary key default gen_random_uuid(),
  roll_number int unique,               -- null only while a draft
  board text not null check (board in ('CB', 'MP')),
  current_class int not null check (current_class between 6 and 12),
  session_year int not null check (session_year between 0 and 99),  -- 26 = 2026-27
  admission_session int,
  name text not null,
  school text,
  batch_id uuid references public.batches (id),
  father_name text,
  mother_name text,
  guardian_name text,
  email text,
  monthly_fee numeric(10, 2) not null default 0,
  status text not null default 'active' check (status in ('draft', 'active', 'left', 'passed_out')),
  code text generated always as (
    case when roll_number is null then null
         else public.format_student_id(board, current_class, roll_number, session_year) end
  ) stored,
  created_by uuid references public.users (id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint students_registered_has_roll check (status = 'draft' or roll_number is not null)
);
create index students_batch on public.students (batch_id);
create index students_class on public.students (board, current_class);
create index students_name on public.students (lower(name));

-- Every ID a student has had. The current one has valid_to null.
create table public.student_id_history (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students (id) on delete cascade,
  roll_number int not null,
  board text not null,
  class int not null,
  session_year int not null,
  code text not null,
  valid_from date not null default current_date,
  valid_to date
);
create index student_id_history_code on public.student_id_history (code);
create index student_id_history_student on public.student_id_history (student_id);

create table public.guardians (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students (id) on delete cascade,
  relation text not null check (relation in ('father', 'mother', 'guardian', 'alternate')),
  name text,
  mobile text not null check (mobile ~ '^[6-9][0-9]{9}$'),
  is_login_number boolean not null default false
);
create index guardians_student on public.guardians (student_id);
create index guardians_mobile on public.guardians (mobile);
-- Only one login number per student.
create unique index guardians_one_login on public.guardians (student_id) where is_login_number;

create table public.marksheets (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students (id) on delete cascade,
  year_label text not null,             -- "2025-26 (Class 8)"
  file_path text,                       -- storage: marksheets bucket
  file_name text,
  typed_percentage numeric(5, 2),
  ai_check_result text not null default 'pending'
    check (ai_check_result in ('pending', 'matched', 'mismatch', 'cant_read')),
  ai_read_name text,
  ai_read_percentage numeric(5, 2),
  ai_note text,
  created_at timestamptz not null default now()
);
create index marksheets_student on public.marksheets (student_id);

create table public.consents (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students (id) on delete cascade,
  text_version text not null,
  given_by text not null,               -- parent/guardian name
  given_at timestamptz not null default now(),
  recorded_by uuid references public.users (id)
);

create table public.faculty_notes (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students (id) on delete cascade,
  author_id uuid not null references public.users (id),
  note text not null,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Attendance
-- ---------------------------------------------------------------------------

create table public.attendance (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students (id) on delete cascade,
  batch_id uuid not null references public.batches (id),
  date date not null,
  status text not null check (status in ('P', 'A', 'L')),
  marked_by uuid references public.users (id),
  marked_at timestamptz not null default now(),
  locked_at timestamptz not null default now() + interval '24 hours',
  unique (student_id, date)
);
create index attendance_batch_date on public.attendance (batch_id, date);

create table public.attendance_notes (
  batch_id uuid not null references public.batches (id) on delete cascade,
  date date not null,
  note text not null,
  written_by uuid references public.users (id),
  primary key (batch_id, date)
);

-- ---------------------------------------------------------------------------
-- Fees, bills, calls
-- ---------------------------------------------------------------------------

create table public.fees_ledger (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students (id) on delete cascade,
  month date not null check (extract(day from month) = 1),
  amount numeric(10, 2) not null,
  paid numeric(10, 2) not null default 0,
  created_at timestamptz not null default now(),
  unique (student_id, month)
);
create index fees_ledger_month on public.fees_ledger (month);

-- One running invoice series per session year: SA-26-0001, SA-26-0002 ...
create table public.invoice_counter (
  series_year int primary key,
  last_number int not null default 0
);

create table public.invoices (
  id uuid primary key default gen_random_uuid(),
  number text not null unique,
  series_year int not null,
  seq int not null,
  student_id uuid not null references public.students (id),
  student_code text not null,           -- the ID the student had on this day
  student_name text not null,
  board text not null,
  class int not null,
  month date not null,
  fee_amount numeric(10, 2) not null,
  paid_before numeric(10, 2) not null default 0,
  received numeric(10, 2) not null check (received > 0),
  balance_after numeric(10, 2) not null,
  modes text[] not null check (modes <@ array['upi', 'bank', 'cash'] and cardinality(modes) > 0),
  reference text,
  paid_on date not null,
  status text not null default 'issued' check (status in ('issued', 'cancelled')),
  cancelled_reason text,
  cancelled_by uuid references public.users (id),
  cancelled_at timestamptz,
  emailed_at timestamptz,
  created_by uuid not null references public.users (id),
  created_at timestamptz not null default now(),
  unique (series_year, seq),
  constraint invoices_cancel_reason check (status = 'issued' or length(trim(coalesce(cancelled_reason, ''))) > 0)
);
create index invoices_student on public.invoices (student_id, month);

-- Bills are never deleted.
create or replace function public.forbid_delete()
returns trigger
language plpgsql
as $$
begin
  raise exception '% rows are never deleted', tg_table_name;
end $$;
create trigger invoices_no_delete before delete on public.invoices
  for each row execute function public.forbid_delete();

-- Makes a bill atomically: next number in the series (no gaps, because the
-- counter only moves when the bill row is saved in the same transaction),
-- and the payment is added to the month's ledger.
create or replace function public.create_invoice(
  p_student uuid,
  p_month date,
  p_fee numeric,
  p_received numeric,
  p_modes text[],
  p_reference text,
  p_paid_on date,
  p_series_year int,
  p_created_by uuid
) returns public.invoices
language plpgsql
as $$
declare
  s public.students;
  ledger public.fees_ledger;
  n int;
  inv public.invoices;
begin
  select * into s from public.students where id = p_student and status <> 'draft';
  if not found then raise exception 'student not found'; end if;

  insert into public.fees_ledger (student_id, month, amount)
  values (p_student, p_month, p_fee)
  on conflict (student_id, month) do update set amount = excluded.amount
  returning * into ledger;

  insert into public.invoice_counter (series_year, last_number) values (p_series_year, 0)
  on conflict (series_year) do nothing;
  update public.invoice_counter set last_number = last_number + 1
  where series_year = p_series_year returning last_number into n;

  insert into public.invoices (
    number, series_year, seq, student_id, student_code, student_name, board, class,
    month, fee_amount, paid_before, received, balance_after, modes, reference, paid_on, created_by
  ) values (
    'SA-' || lpad(p_series_year::text, 2, '0') || '-' || lpad(n::text, 4, '0'),
    p_series_year, n, s.id, s.code, s.name, s.board, s.current_class,
    p_month, p_fee, ledger.paid, p_received, greatest(p_fee - ledger.paid - p_received, 0),
    p_modes, nullif(trim(p_reference), ''), p_paid_on, p_created_by
  ) returning * into inv;

  update public.fees_ledger set paid = paid + p_received where id = ledger.id;
  return inv;
end $$;

-- Cancelling keeps the number in the list and takes the money off the ledger.
create or replace function public.cancel_invoice(p_invoice uuid, p_reason text, p_by uuid)
returns public.invoices
language plpgsql
as $$
declare
  inv public.invoices;
begin
  if length(trim(coalesce(p_reason, ''))) = 0 then raise exception 'reason required'; end if;
  update public.invoices
     set status = 'cancelled', cancelled_reason = trim(p_reason), cancelled_by = p_by, cancelled_at = now()
   where id = p_invoice and status = 'issued'
  returning * into inv;
  if not found then raise exception 'bill not found or already cancelled'; end if;
  update public.fees_ledger set paid = greatest(paid - inv.received, 0)
   where student_id = inv.student_id and month = inv.month;
  return inv;
end $$;

create table public.call_log (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students (id) on delete cascade,
  month date,
  guardian_name text,
  guardian_mobile text not null,
  called_by uuid not null references public.users (id),
  outcome text not null check (outcome in ('will_pay_today', 'promised_date', 'not_connected', 'wrong_number', 'needs_admin')),
  follow_up_date date,
  note text,
  attempt_no int not null,
  created_at timestamptz not null default now(),
  constraint call_log_promise_date check (outcome <> 'promised_date' or follow_up_date is not null)
);
create index call_log_student on public.call_log (student_id, created_at desc);

-- Private fee reminders (parent's own login) and the reminder chain counts.
create table public.fee_reminders (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students (id) on delete cascade,
  month date not null,
  stage text not null check (stage in ('reminded', 'called', 'escalated')),
  created_by uuid references public.users (id),
  created_at timestamptz not null default now()
);
create index fee_reminders_month on public.fee_reminders (month, stage);

-- ---------------------------------------------------------------------------
-- Timetable, tests, marks
-- ---------------------------------------------------------------------------

create table public.timetable_entries (
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references public.batches (id) on delete cascade,
  weekday int not null check (weekday between 1 and 7),   -- 1 = Monday
  start_time time not null,
  end_time time,
  subject text not null,
  faculty_id uuid references public.users (id),
  tag text not null default 'Coaching' check (tag in ('School', 'Coaching')),
  created_at timestamptz not null default now()
);
create index timetable_batch on public.timetable_entries (batch_id, weekday);

create table public.tests (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  board text not null check (board in ('CB', 'MP')),
  class int not null check (class between 6 and 12),
  batch_id uuid references public.batches (id) on delete cascade,  -- null = whole class
  subject text,
  date date not null,
  start_time time,
  tag text not null check (tag in ('School', 'Coaching')),
  max_marks numeric(6, 2),
  created_by uuid references public.users (id),
  created_at timestamptz not null default now()
);
create index tests_class_date on public.tests (board, class, date);

create table public.marks (
  test_id uuid not null references public.tests (id) on delete cascade,
  student_id uuid not null references public.students (id) on delete cascade,
  score numeric(6, 2),
  absent boolean not null default false,
  entered_by uuid references public.users (id),
  entered_at timestamptz not null default now(),
  primary key (test_id, student_id),
  constraint marks_score_or_absent check (absent or score is not null)
);

-- ---------------------------------------------------------------------------
-- Groups (chat)
-- ---------------------------------------------------------------------------

create table public.groups (
  id uuid primary key default gen_random_uuid(),
  kind text not null check (kind in ('batch', 'management', 'faculty')),
  batch_id uuid unique references public.batches (id) on delete cascade,
  name text not null,
  created_at timestamptz not null default now(),
  constraint groups_batch check ((kind = 'batch') = (batch_id is not null))
);
create unique index groups_one_staff_kind on public.groups (kind) where kind <> 'batch';

-- Members are worked out from roles and batches (see can_read_group), so a
-- new parent or faculty member is in the right groups at once. This table
-- holds explicit extras only (for example a guest in the Management group).
create table public.group_members (
  group_id uuid not null references public.groups (id) on delete cascade,
  user_id uuid not null references public.users (id) on delete cascade,
  primary key (group_id, user_id)
);

create table public.messages (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.groups (id) on delete cascade,
  sender_id uuid not null references public.users (id),
  type text not null default 'chat' check (type in ('chat', 'timetable', 'test', 'notice')),
  body text not null default '',
  attachment_path text,
  attachment_name text,
  created_at timestamptz not null default now()
);
create index messages_group on public.messages (group_id, created_at desc);

create table public.message_reads (
  message_id uuid not null references public.messages (id) on delete cascade,
  user_id uuid not null references public.users (id) on delete cascade,
  read_at timestamptz not null default now(),
  primary key (message_id, user_id)
);

-- New batch → its parents' group.
create or replace function public.batch_group()
returns trigger
language plpgsql
as $$
begin
  insert into public.groups (kind, batch_id, name)
  values ('batch', new.id,
    case new.board when 'CB' then 'CBSE' else 'MP Board' end || ' ' || new.class || ' · ' ||
    new.name || coalesce(' ' || new.start_time, ''))
  on conflict (batch_id) do nothing;
  return new;
end $$;
create trigger batches_group after insert on public.batches
  for each row execute function public.batch_group();

-- ---------------------------------------------------------------------------
-- Notifications, permissions, logs, AI
-- ---------------------------------------------------------------------------

create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  kind text not null,
  title text not null,
  body text,
  link text,
  dedupe_key text,
  read_at timestamptz,
  created_at timestamptz not null default now(),
  unique (user_id, dedupe_key)
);
create index notifications_user on public.notifications (user_id, created_at desc);

create table public.role_permissions (
  role public.app_role not null,
  key text not null,
  allowed boolean not null,
  updated_by uuid references public.users (id),
  updated_at timestamptz not null default now(),
  primary key (role, key)
);

create table public.user_permissions (
  user_id uuid not null references public.users (id) on delete cascade,
  key text not null,
  allowed boolean not null,
  updated_by uuid references public.users (id),
  updated_at timestamptz not null default now(),
  primary key (user_id, key)
);

create table public.activity_log (
  id bigint generated always as identity primary key,
  actor_id uuid references public.users (id),
  actor_label text not null,            -- "AD-01 Name" at the time
  action text not null,                 -- bill.create, attendance.correct ...
  entity text,
  entity_id text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index activity_log_created on public.activity_log (created_at desc);

-- The activity log is append-only.
create or replace function public.forbid_change()
returns trigger
language plpgsql
as $$
begin
  raise exception '% is append-only', tg_table_name;
end $$;
create trigger activity_log_append_only before update or delete on public.activity_log
  for each row execute function public.forbid_change();

create table public.ai_actions (
  id uuid primary key default gen_random_uuid(),
  requested_by uuid not null references public.users (id),
  kind text not null,                   -- send_fee_reminders ...
  summary text not null,
  payload jsonb not null,
  status text not null default 'proposed' check (status in ('proposed', 'confirmed', 'cancelled', 'done', 'failed')),
  result jsonb,
  created_at timestamptz not null default now(),
  decided_at timestamptz
);

create table public.ai_messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  body text not null,
  attachment jsonb,                     -- {kind:'pdf', title, rows} or {kind:'action', id}
  created_at timestamptz not null default now()
);
create index ai_messages_user on public.ai_messages (user_id, created_at);

create table public.backups (
  id uuid primary key default gen_random_uuid(),
  file_path text not null,
  rows_total int not null,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Helpers for realtime RLS
-- ---------------------------------------------------------------------------

create or replace function public.current_app_user()
returns public.users
language sql stable security definer set search_path = public
as $$
  select * from public.users where auth_user_id = auth.uid() and status = 'active' limit 1;
$$;

-- Who may read a group:
--   batch group: admin, management, and parents of an active student in the batch
--   management group: admin, management, reception
--   faculty group: admin, management, reception, faculty
--   plus explicit extras in group_members.
create or replace function public.can_read_group(p_group uuid)
returns boolean
language sql stable security definer set search_path = public
as $$
  with me as (select * from public.current_app_user()), g as (select * from public.groups where id = p_group)
  select coalesce((
    select case
      when exists (select 1 from public.group_members gm where gm.group_id = g.id and gm.user_id = me.id) then true
      when g.kind = 'management' then me.role in ('admin', 'management', 'reception')
      when g.kind = 'faculty' then me.role in ('admin', 'management', 'reception', 'faculty')
      when g.kind = 'batch' then me.role in ('admin', 'management')
        or (me.role = 'parent' and exists (
          select 1 from public.students s join public.guardians gu on gu.student_id = s.id
          where s.batch_id = g.batch_id and s.status = 'active' and gu.is_login_number and gu.mobile = me.mobile))
      else false end
    from me, g), false);
$$;

-- ---------------------------------------------------------------------------
-- Row level security: on everywhere, deny by default.
-- ---------------------------------------------------------------------------

do $$
declare t text;
begin
  for t in select tablename from pg_tables where schemaname = 'public' loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon', t);
  end loop;
end $$;

create policy messages_read on public.messages
  for select to authenticated using (public.can_read_group(group_id));

create policy notifications_read_own on public.notifications
  for select to authenticated using (user_id = (public.current_app_user()).id);

-- Server-only functions: never callable from the browser.
revoke execute on function public.create_invoice(uuid, date, numeric, numeric, text[], text, date, int, uuid) from public, anon, authenticated;
revoke execute on function public.cancel_invoice(uuid, text, uuid) from public, anon, authenticated;
revoke execute on function public.allocate_roll() from public, anon, authenticated;
revoke execute on function public.next_staff_id(public.app_role) from public, anon, authenticated;

-- Realtime: chat and the bell.
alter publication supabase_realtime add table public.messages, public.notifications;

-- ---------------------------------------------------------------------------
-- Storage: private buckets, read through short signed links from the server.
-- ---------------------------------------------------------------------------

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('marksheets', 'marksheets', false, 10485760, array['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'application/pdf']),
  ('attachments', 'attachments', false, 20971520, null),
  ('backups', 'backups', false, null, null)
on conflict (id) do nothing;
