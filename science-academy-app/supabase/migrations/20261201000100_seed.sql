-- Starting data: the two staff groups and the first Admin login.
-- Change the Admin's name and mobile before the first login:
--   update public.users set name = 'Owner name', mobile = '98XXXXXXXX' where staff_id = 'AD-01';

insert into public.groups (kind, name) values
  ('management', 'Management'),
  ('faculty', 'Faculty')
on conflict do nothing;

insert into public.users (staff_id, role, name, mobile)
values ('AD-01', 'admin', 'Admin', '9999999999')
on conflict do nothing;
