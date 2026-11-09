-- Parent queries: a private chat between a parent and the academy staff about
-- one child (no AI; staff answer by hand). Safe to run more than once.

create table if not exists public.query_threads (
  id uuid primary key default gen_random_uuid(),
  parent_user_id uuid not null references public.users (id) on delete cascade,
  student_id uuid not null references public.students (id) on delete cascade,
  status text not null default 'open' check (status in ('open', 'resolved')),
  last_message_at timestamptz not null default now(),
  last_from text not null default 'parent' check (last_from in ('parent', 'staff')),
  created_at timestamptz not null default now(),
  unique (parent_user_id, student_id)
);
create index if not exists query_threads_recent on public.query_threads (last_message_at desc);

create table if not exists public.query_messages (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid not null references public.query_threads (id) on delete cascade,
  sender_id uuid not null references public.users (id),
  body text not null default '',
  attachment_path text,
  attachment_name text,
  created_at timestamptz not null default now()
);
create index if not exists query_messages_thread on public.query_messages (thread_id, created_at);

-- When each person last opened a thread (for unread counts).
create table if not exists public.query_reads (
  thread_id uuid not null references public.query_threads (id) on delete cascade,
  user_id uuid not null references public.users (id) on delete cascade,
  last_read_at timestamptz not null default now(),
  primary key (thread_id, user_id)
);

alter table public.query_threads enable row level security;
alter table public.query_messages enable row level security;
alter table public.query_reads enable row level security;
revoke all on public.query_threads, public.query_messages, public.query_reads from anon;

-- Realtime: a parent sees new messages in their own threads; staff who answer queries see all.
drop policy if exists query_messages_read on public.query_messages;
create policy query_messages_read on public.query_messages
  for select to authenticated using (
    exists (
      select 1 from public.query_threads t
      where t.id = thread_id
        and (t.parent_user_id = (public.current_app_user()).id
             or (public.current_app_user()).role in ('admin', 'management', 'reception'))
    )
  );

do $$ begin
  alter publication supabase_realtime add table public.query_messages;
exception when duplicate_object then null;
end $$;
