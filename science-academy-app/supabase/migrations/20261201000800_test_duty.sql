-- Tests: a faculty member on duty (marks who came, even outside their own
-- batches), "Test done", and the test's own attendance. Safe to run again.

alter table public.tests add column if not exists faculty_id uuid references public.users (id) on delete set null;
alter table public.tests add column if not exists done_at timestamptz;
alter table public.tests add column if not exists done_by uuid references public.users (id) on delete set null;
create index if not exists tests_faculty on public.tests (faculty_id, date);

create table if not exists public.test_attendance (
  test_id uuid not null references public.tests (id) on delete cascade,
  student_id uuid not null references public.students (id) on delete cascade,
  present boolean not null,
  marked_by uuid references public.users (id) on delete set null,
  marked_at timestamptz not null default now(),
  primary key (test_id, student_id)
);

alter table public.test_attendance enable row level security;
revoke all on public.test_attendance from anon, authenticated;
