-- Fee reminder automation: WhatsApp messages sent to parents (one per fee
-- row and kind, so a re-run never sends twice) and the reception call tasks
-- made the day after a due date. Safe to run more than once.

create table if not exists public.whatsapp_messages (
  id uuid primary key default gen_random_uuid(),
  ledger_id uuid references public.fees_ledger (id) on delete set null,
  student_id uuid references public.students (id) on delete cascade,
  kind text not null,                       -- fee_due_tomorrow
  to_mobile text not null,
  status text not null check (status in ('sent', 'failed', 'skipped')),
  error text,
  provider_id text,
  created_at timestamptz not null default now()
);
create unique index if not exists whatsapp_messages_once on public.whatsapp_messages (ledger_id, kind) where status = 'sent';
alter table public.whatsapp_messages enable row level security;
revoke all on public.whatsapp_messages from anon;

create table if not exists public.call_tasks (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students (id) on delete cascade,
  ledger_id uuid unique references public.fees_ledger (id) on delete cascade,
  due_date date not null,
  task_date date not null,                  -- the day after the due date
  status text not null default 'open' check (status in ('open', 'done')),
  done_at timestamptz,
  done_by uuid references public.users (id),
  created_at timestamptz not null default now()
);
create index if not exists call_tasks_open on public.call_tasks (status, task_date);
alter table public.call_tasks enable row level security;
revoke all on public.call_tasks from anon;
