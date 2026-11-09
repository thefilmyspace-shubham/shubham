-- Each person's app language: English, Hindi or Hinglish. Safe to run more than once.
alter table public.users add column if not exists language text;

do $$ begin
  alter table public.users add constraint users_language check (language is null or language in ('en', 'hi', 'hinglish'));
exception when duplicate_object then null;
end $$;
