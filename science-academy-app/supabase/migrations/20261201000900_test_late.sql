-- Test attendance: "Late" (came, but late). Safe to run again.
alter table public.test_attendance add column if not exists late boolean not null default false;
notify pgrst, 'reload schema';
