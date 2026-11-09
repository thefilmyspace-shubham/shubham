-- Starting data: the two staff groups and the first Admin login.
-- Change the Admin's name, mobile and email before the first login (the login code is emailed):
--   update public.users set name = 'Owner name', mobile = '98XXXXXXXX', email = 'owner@gmail.com' where staff_id = 'AD-01';

insert into public.groups (kind, name) values
  ('management', 'Management'),
  ('faculty', 'Faculty')
on conflict do nothing;

insert into public.users (staff_id, role, name, mobile)
values ('AD-01', 'admin', 'Admin', '9999999999')
on conflict do nothing;
