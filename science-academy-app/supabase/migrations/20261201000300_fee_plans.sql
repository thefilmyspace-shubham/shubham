-- Fee plans: monthly, one time, installments or a manual schedule, with a
-- due date on every fee row. Safe to run more than once.

alter table public.students
  add column if not exists fee_plan text not null default 'monthly',
  add column if not exists fee_due_day int not null default 5,
  add column if not exists total_fee numeric(10, 2);

do $$ begin
  alter table public.students add constraint students_fee_plan check (fee_plan in ('monthly', 'one_time', 'installments', 'manual'));
exception when duplicate_object then null;
end $$;
do $$ begin
  alter table public.students add constraint students_fee_due_day check (fee_due_day between 1 and 28);
exception when duplicate_object then null;
end $$;

-- Each fee row (a month for monthly plans, an installment otherwise) has its own due date.
alter table public.fees_ledger
  add column if not exists due_date date,
  add column if not exists label text,
  add column if not exists installment_no int;

update public.fees_ledger set due_date = month + 4 where due_date is null;

-- The payment plan agreed at registration (for the record; the fee rows are made from it).
alter table public.students add column if not exists fee_schedule jsonb;
