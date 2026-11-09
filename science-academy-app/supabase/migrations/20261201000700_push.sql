-- Phone notifications (web push): each phone a person turned notifications on
-- for, and the app's own push keys (made by the app on first use). Safe to run again.

create table if not exists public.push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  endpoint text not null unique,
  p256dh text not null,
  auth text not null,
  user_agent text,
  created_at timestamptz not null default now()
);
create index if not exists push_subscriptions_user on public.push_subscriptions (user_id);

create table if not exists public.app_secrets (
  key text primary key,
  value text not null,
  created_at timestamptz not null default now()
);

alter table public.push_subscriptions enable row level security;
alter table public.app_secrets enable row level security;
revoke all on public.push_subscriptions, public.app_secrets from anon, authenticated;
