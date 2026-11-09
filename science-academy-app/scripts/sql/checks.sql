-- Behaviour checks run after the migrations by scripts/test-migrations.sh.
\set ON_ERROR_STOP on

-- IDs
do $$ begin
  assert public.format_student_id('MP', 9, 25, 26) = 'MP9-025-26', 'MP9-025-26';
  assert public.format_student_id('CB', 12, 87, 26) = 'CB12-087-26', 'CB12-087-26';
  assert public.format_student_id('CB', 10, 1000, 27) = 'CB10-1000-27', 'four digits after 999';
  assert public.format_student_id('MP', 6, 7, 2030) = 'MP6-007-30', 'session uses last two digits';
end $$;

-- Roll numbers: one running count, never reused.
do $$
declare a int; b int; c int;
begin
  a := public.allocate_roll();
  b := public.allocate_roll();
  assert b = a + 1, 'running count';
  -- A failed registration still burns its number (never reused).
  begin
    c := public.allocate_roll();
    raise exception 'rollback';
  exception when others then null;
  end;
  c := public.allocate_roll();
  assert c > b, 'counter only goes up';
end $$;

-- Staff IDs
do $$ begin
  assert public.next_staff_id('admin') = 'AD-02', 'AD-01 is seeded';
  assert public.next_staff_id('faculty') = 'FC-01', 'first faculty';
end $$;

insert into public.users (staff_id, role, name, mobile) values ('RC-01', 'reception', 'Desk', '9000000001');
insert into public.batches (board, class, name, start_time) values ('MP', 9, 'PCB', '8:00 AM');

do $$ begin
  assert (select count(*) from public.groups where kind = 'batch') = 1, 'a batch gets its parents group';
  assert (select name from public.groups where kind = 'batch') = 'MP Board 9 · PCB 8:00 AM', 'group name';
end $$;

insert into public.students (roll_number, board, current_class, session_year, name, monthly_fee, batch_id)
select 25, 'MP', 9, 26, 'Test Student', 2500, id from public.batches limit 1;

do $$ begin
  assert (select code from public.students where roll_number = 25) = 'MP9-025-26', 'generated code';
end $$;

-- A second student may not take roll 25.
do $$ begin
  begin
    insert into public.students (roll_number, board, current_class, session_year, name)
    values (25, 'CB', 12, 26, 'Duplicate');
    raise exception 'duplicate roll accepted';
  exception when unique_violation then null;
  end;
end $$;

-- Only one login number per student.
insert into public.guardians (student_id, relation, name, mobile, is_login_number)
select id, 'father', 'Father', '9876543210', true from public.students where roll_number = 25;
do $$ begin
  begin
    insert into public.guardians (student_id, relation, name, mobile, is_login_number)
    select id, 'mother', 'Mother', '9876543211', true from public.students where roll_number = 25;
    raise exception 'two login numbers accepted';
  exception when unique_violation then null;
  end;
end $$;

-- Bills: running numbers, balance, ledger, cancel keeps the number.
do $$
declare
  s uuid := (select id from public.students where roll_number = 25);
  u uuid := (select id from public.users where staff_id = 'RC-01');
  i1 public.invoices; i2 public.invoices; i3 public.invoices;
begin
  i1 := public.create_invoice(s, '2026-11-01', 2500, 1000, array['cash'], null, '2026-11-03', 26, u);
  assert i1.number = 'SA-26-0001', 'first bill number ' || i1.number;
  assert i1.balance_after = 1500, 'balance';
  assert i1.student_code = 'MP9-025-26', 'bill keeps the ID of the day';
  i2 := public.create_invoice(s, '2026-11-01', 2500, 1500, array['upi'], 'UTR123', '2026-11-04', 26, u);
  assert i2.number = 'SA-26-0002', 'second bill number';
  assert i2.paid_before = 1000 and i2.balance_after = 0, 'previous payments counted';
  assert (select paid from public.fees_ledger where student_id = s) = 2500, 'ledger paid';

  -- A failed bill does not burn a number (no gaps).
  begin
    perform public.create_invoice(s, '2026-11-01', 2500, 0, array['cash'], null, '2026-11-04', 26, u);
    raise exception 'zero bill accepted';
  exception when check_violation then null;
  end;
  i3 := public.create_invoice(s, '2026-12-01', 2500, 2500, array['bank'], null, '2026-12-05', 26, u);
  assert i3.number = 'SA-26-0003', 'no gap after a failed bill: ' || i3.number;

  perform public.cancel_invoice(i2.id, 'Wrong amount', u);
  assert (select status from public.invoices where id = i2.id) = 'cancelled', 'cancelled stays in the list';
  assert (select paid from public.fees_ledger where student_id = s and month = '2026-11-01') = 1000, 'cancel reverses payment';

  begin
    perform public.cancel_invoice(i1.id, '  ', u);
    raise exception 'cancel without reason accepted';
  exception when raise_exception then
    if sqlerrm <> 'reason required' then raise; end if;
  end;

  begin
    delete from public.invoices where id = i1.id;
    raise exception 'bill deleted';
  exception when raise_exception then
    if sqlerrm not like '%never deleted%' then raise; end if;
  end;
end $$;

-- Activity log is append-only.
insert into public.activity_log (actor_label, action) values ('AD-01 Admin', 'test');
do $$ begin
  begin
    delete from public.activity_log;
    raise exception 'log deleted';
  exception when raise_exception then
    if sqlerrm not like '%append-only%' then raise; end if;
  end;
end $$;

-- RLS: a parent can read their child's batch group, nobody else's; no direct table reads.
insert into auth.users (id, email) values
  ('00000000-0000-0000-0000-0000000000a1', null),
  ('00000000-0000-0000-0000-0000000000a2', null);
insert into public.users (role, name, mobile, auth_user_id) values
  ('parent', 'Father', '9876543210', '00000000-0000-0000-0000-0000000000a1'),
  ('parent', 'Other parent', '9123456789', '00000000-0000-0000-0000-0000000000a2');
insert into public.messages (group_id, sender_id, type, body)
select g.id, u.id, 'notice', 'Holiday on Monday' from public.groups g, public.users u
where g.kind = 'batch' and u.staff_id = 'AD-01';
insert into public.messages (group_id, sender_id, body)
select g.id, u.id, 'staff only' from public.groups g, public.users u
where g.kind = 'management' and u.staff_id = 'AD-01';

set role authenticated;
set request.jwt.claim.sub = '00000000-0000-0000-0000-0000000000a1';
do $$ begin
  assert (select count(*) from public.messages) = 1, 'parent sees only their batch group';
  assert (select count(*) from public.students) = 0, 'no direct student reads';
  assert (select count(*) from public.invoices) = 0, 'no direct bill reads';
end $$;
set request.jwt.claim.sub = '00000000-0000-0000-0000-0000000000a2';
do $$ begin
  assert (select count(*) from public.messages) = 0, 'other parent sees nothing';
end $$;
reset role;
