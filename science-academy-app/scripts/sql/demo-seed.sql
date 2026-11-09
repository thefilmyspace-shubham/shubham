-- DEMO DATA ONLY. Fills the app with sample staff, batches, students, fees,
-- bills, attendance, tests and group posts so it can be shown before real
-- data exists. Every name and number here is made up.
-- Do NOT run this on the live database once real students are entered.
--
-- Run after the migrations:  psql "$DATABASE_URL" -f scripts/sql/demo-seed.sql

begin;

-- Staff (AD-01 is created by the seed migration).
update public.users set name = 'Demo Admin', mobile = '9000000000' where staff_id = 'AD-01';
insert into public.users (staff_id, role, name, mobile) values
  ('MG-01', 'management', 'Neha Joshi', '9000000011'),
  ('RC-01', 'reception', 'Pooja Rathore', '9000000021'),
  ('FC-01', 'faculty', 'Rakesh Sharma', '9000000031'),
  ('FC-02', 'faculty', 'Anita Verma', '9000000032'),
  ('FC-03', 'faculty', 'Imran Khan', '9000000033')
on conflict do nothing;

-- Batches (each gets its parents' group from the trigger).
insert into public.batches (board, class, name, start_time) values
  ('MP', 9, 'PCB', '8:00 AM'),
  ('MP', 10, 'PCM', '9:30 AM'),
  ('CB', 9, 'Foundation', '4:00 PM'),
  ('CB', 10, 'Science', '5:30 PM'),
  ('CB', 11, 'PCB', '7:00 AM'),
  ('CB', 12, 'PCM', '6:00 PM'),
  ('MP', 12, 'PCB', '3:00 PM'),
  ('CB', 8, 'Foundation', '2:00 PM')
on conflict do nothing;

insert into public.faculty_batches (user_id, batch_id, subject)
select u.id, b.id, s.subject
from (values
  ('FC-01', 'MP', 9, 'Physics'), ('FC-01', 'MP', 10, 'Physics'), ('FC-01', 'CB', 12, 'Physics'),
  ('FC-02', 'CB', 9, 'Biology'), ('FC-02', 'CB', 11, 'Biology'), ('FC-02', 'MP', 12, 'Biology'),
  ('FC-03', 'CB', 10, 'Chemistry'), ('FC-03', 'CB', 8, 'Science'), ('FC-03', 'CB', 11, 'Chemistry')
) as s(staff, board, class, subject)
join public.users u on u.staff_id = s.staff
join public.batches b on b.board = s.board and b.class = s.class
on conflict do nothing;

-- Students: 12 per batch.
do $$
declare
  first_names text[] := array['Aarav','Vivaan','Aditya','Riya','Ananya','Kabir','Ishaan','Diya','Saanvi','Arjun','Meera','Rohan',
    'Priya','Yash','Tanvi','Harsh','Kavya','Dev','Nisha','Aryan','Sneha','Kunal','Pari','Om'];
  last_names text[] := array['Sharma','Patel','Jain','Verma','Rathore','Choudhary','Agrawal','Malviya','Joshi','Solanki','Gupta','Trivedi'];
  schools text[] := array['St. Joseph''s Convent','Kendriya Vidyalaya','Govt. Excellence School','Sophia Convent','Delhi Public School','Saraswati Shishu Mandir'];
  b record;
  i int;
  s_id uuid;
  roll int;
  fname text;
  lname text;
  fee numeric;
begin
  for b in select * from public.batches order by board, class loop
    for i in 1..12 loop
      roll := public.allocate_roll();
      fname := first_names[1 + (abs(hashtext(b.id::text || i)) % array_length(first_names, 1))];
      lname := last_names[1 + (abs(hashtext(i || b.id::text)) % array_length(last_names, 1))];
      fee := case when b.class >= 11 then 3000 when b.class >= 9 then 2500 else 1800 end;
      insert into public.students (roll_number, board, current_class, session_year, admission_session, name, school, batch_id,
        father_name, mother_name, email, monthly_fee, status)
      values (roll, b.board, b.class, 26, 26, fname || ' ' || lname, schools[1 + roll % array_length(schools, 1)], b.id,
        'Mr. ' || lname, 'Mrs. ' || lname, lower(fname) || roll || '@example.com', fee, 'active')
      returning id into s_id;
      insert into public.student_id_history (student_id, roll_number, board, class, session_year, code, valid_from)
      values (s_id, roll, b.board, b.class, 26, public.format_student_id(b.board, b.class, roll, 26), '2026-04-01');
      insert into public.guardians (student_id, relation, name, mobile, is_login_number) values
        (s_id, 'father', 'Mr. ' || lname, '98' || lpad((10000000 + roll * 37)::text, 8, '0'), true),
        (s_id, 'mother', 'Mrs. ' || lname, '97' || lpad((10000000 + roll * 41)::text, 8, '0'), false);
      insert into public.consents (student_id, text_version, given_by) values (s_id, 'v1', 'Mr. ' || lname);
      insert into public.marksheets (student_id, year_label, typed_percentage, ai_check_result, ai_note)
      values (s_id, '2025-26', 60 + (roll * 7) % 38, case when roll % 9 = 0 then 'cant_read' when roll % 13 = 0 then 'mismatch' else 'matched' end,
        case when roll % 9 = 0 then 'Photo is blurry. Please upload a clearer photo.' end);
    end loop;
  end loop;
end $$;

-- One student promoted from last year, to show "Earlier ID".
update public.student_id_history set valid_from = '2026-04-01'
where student_id = (select id from public.students where batch_id = (select id from public.batches where board = 'MP' and class = 10) order by roll_number limit 1);
insert into public.student_id_history (student_id, roll_number, board, class, session_year, code, valid_from, valid_to)
select id, roll_number, board, 9, 25, public.format_student_id(board, 9, roll_number, 25), '2025-04-01', '2026-03-31'
from public.students where batch_id = (select id from public.batches where board = 'MP' and class = 10) order by roll_number limit 1;

-- Parent logins for every login number.
insert into public.users (role, name, mobile)
select distinct on (g.mobile) 'parent', g.name, g.mobile from public.guardians g where g.is_login_number
on conflict do nothing;

-- Fees: June to November 2026. Older months mostly paid; this month mixed.
do $$
declare
  s record;
  m date;
  rc uuid := (select id from public.users where staff_id = 'RC-01');
  k int;
begin
  for s in select * from public.students where status = 'active' order by roll_number loop
    for m in select generate_series('2026-06-01'::date, '2026-11-01'::date, interval '1 month')::date loop
      k := abs(hashtext(s.id::text || m::text)) % 10;
      if m < '2026-11-01' and k < 9 then
        perform public.create_invoice(s.id, m, s.monthly_fee, s.monthly_fee,
          array[(array['upi','cash','bank'])[1 + k % 3]], case when k % 3 = 0 then 'UPI' || (100000 + k * 7919) end,
          m + (2 + k % 6), 26, rc);
      elsif m = '2026-11-01' and k < 5 then
        perform public.create_invoice(s.id, m, s.monthly_fee, s.monthly_fee, array['upi'], 'UPI' || (200000 + k),
          m + (1 + k), 26, rc);
      elsif m = '2026-11-01' and k < 7 then
        perform public.create_invoice(s.id, m, s.monthly_fee, round(s.monthly_fee / 2), array['cash'], null, m + 3, 26, rc);
      else
        insert into public.fees_ledger (student_id, month, amount) values (s.id, m, s.monthly_fee)
        on conflict do nothing;
      end if;
    end loop;
  end loop;
end $$;

-- A few calls and reminders.
insert into public.fee_reminders (student_id, month, stage, created_by)
select l.student_id, l.month, 'reminded', (select id from public.users where staff_id = 'RC-01')
from public.fees_ledger l where l.month = '2026-11-01' and l.paid < l.amount;
insert into public.call_log (student_id, month, guardian_name, guardian_mobile, called_by, outcome, follow_up_date, note, attempt_no, created_at)
select l.student_id, l.month, g.name, g.mobile, (select id from public.users where staff_id = 'RC-01'),
  (array['not_connected','promised_date','will_pay_today'])[1 + abs(hashtext(l.student_id::text)) % 3],
  '2026-11-12', 'Father said salary comes on 10th', 1, now() - interval '2 days'
from public.fees_ledger l join public.guardians g on g.student_id = l.student_id and g.is_login_number
where l.month = '2026-11-01' and l.paid = 0
limit 6;
update public.call_log set follow_up_date = null where outcome <> 'promised_date';
insert into public.fee_reminders (student_id, month, stage, created_by)
select student_id, month, 'called', called_by from public.call_log;

-- Timetable: each batch three days a week.
insert into public.timetable_entries (batch_id, weekday, start_time, end_time, subject, faculty_id, tag)
select b.id, d.weekday, to_timestamp(coalesce(b.start_time, '8:00 AM'), 'HH:MI AM')::time,
  (to_timestamp(coalesce(b.start_time, '8:00 AM'), 'HH:MI AM') + interval '90 minutes')::time,
  coalesce(fb.subject, 'Science'), fb.user_id, 'Coaching'
from public.batches b
cross join (values (1), (3), (5)) d(weekday)
left join lateral (select * from public.faculty_batches f where f.batch_id = b.id limit 1) fb on true;

-- Tests: two past coaching tests per class and one upcoming school exam.
insert into public.tests (name, board, class, subject, date, tag, max_marks, created_by)
select t.name || ' ' || b.class, b.board, b.class, t.subject, t.date::date, t.tag, t.max_marks,
  (select id from public.users where staff_id = 'MG-01')
from (select distinct board, class from public.batches) b
cross join (values
  ('Unit Test 3 · Class', 'Physics', '2026-10-18', 'Coaching', 50),
  ('Monthly Test Oct · Class', 'Science', '2026-11-01', 'Coaching', 100),
  ('School Half Yearly · Class', 'Science', '2026-11-24', 'School', 80)
) t(name, subject, date, tag, max_marks);

insert into public.marks (test_id, student_id, score, absent, entered_by)
select t.id, s.id,
  case when abs(hashtext(t.id::text || s.id::text)) % 17 = 0 then null
       else round((t.max_marks * (0.42 + (abs(hashtext(s.id::text || t.id::text)) % 56) / 100.0))::numeric, 1) end,
  abs(hashtext(t.id::text || s.id::text)) % 17 = 0,
  (select id from public.users where staff_id = 'MG-01')
from public.tests t
join public.students s on s.board = t.board and s.current_class = t.class and s.status = 'active'
where t.date < '2026-11-09';

-- Attendance: last 30 days on class days.
insert into public.attendance (student_id, batch_id, date, status, marked_by, marked_at, locked_at)
select s.id, s.batch_id, d::date,
  case when abs(hashtext(s.id::text || d::text)) % 100 < (case when s.roll_number % 11 = 0 then 35 else 8 end) then 'A'
       when abs(hashtext(d::text || s.id::text)) % 100 < 6 then 'L' else 'P' end,
  fb.user_id, d + interval '9 hours', d + interval '33 hours'
from public.students s
join lateral (select user_id from public.faculty_batches f where f.batch_id = s.batch_id limit 1) fb on true
cross join generate_series('2026-10-10'::date, '2026-11-08'::date, interval '1 day') d
where extract(isodow from d) in (1, 3, 5) and s.status = 'active';

-- Group posts.
insert into public.messages (group_id, sender_id, type, body, created_at)
select g.id, (select id from public.users where staff_id = 'MG-01'), 'test',
  'Monthly Test on Sunday 15 Nov, 9 AM. Syllabus: chapters 1 to 4. Bring your own calculator.', now() - interval '1 day'
from public.groups g where g.kind = 'batch';
insert into public.messages (group_id, sender_id, type, body, created_at)
select g.id, (select id from public.users where staff_id = 'AD-01'), 'notice',
  'Classes will stay closed on 12 Nov for Diwali. Regular classes from 13 Nov.', now() - interval '3 hours'
from public.groups g where g.kind = 'batch';
insert into public.messages (group_id, sender_id, body, created_at)
select g.id, u.id, m.body, now() - m.ago
from public.groups g
join (values
  ('faculty', 'FC-01', 'MP 9 PCB attendance done. 2 students absent 3 days in a row, please check.', interval '5 hours'),
  ('faculty', 'MG-01', 'Thanks Rakesh sir. Reception will call the parents.', interval '4 hours'),
  ('management', 'RC-01', 'November collection update: 60% done. Calls going on for the rest.', interval '2 hours'),
  ('management', 'AD-01', 'Good. Escalate anyone above 20 days to me.', interval '1 hour')
) m(kind, staff, body, ago) on g.kind = m.kind
join public.users u on u.staff_id = m.staff;

commit;
