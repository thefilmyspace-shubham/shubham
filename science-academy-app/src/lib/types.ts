import type { Board } from "./ids";
import type { Role } from "./permissions";

export type AppUser = {
  id: string;
  auth_user_id: string | null;
  staff_id: string | null;
  role: Role;
  name: string;
  mobile: string;
  email: string | null;
  status: "active" | "suspended";
  /** en | hi | hinglish; missing until the language migration has run. */
  language?: string | null;
  created_at: string;
};

export type Batch = {
  id: string;
  board: Board;
  class: number;
  name: string;
  start_time: string | null;
  active: boolean;
};

export type StudentStatus = "draft" | "active" | "left" | "passed_out";

export type Student = {
  id: string;
  roll_number: number | null;
  board: Board;
  current_class: number;
  session_year: number;
  admission_session: number | null;
  name: string;
  school: string | null;
  batch_id: string | null;
  father_name: string | null;
  mother_name: string | null;
  guardian_name: string | null;
  email: string | null;
  monthly_fee: number;
  /** Missing until the fee plans migration has run. */
  fee_plan?: "monthly" | "one_time" | "installments" | "manual";
  fee_due_day?: number;
  total_fee?: number | null;
  fee_schedule?: { due_date: string; amount: number; label: string }[] | null;
  status: StudentStatus;
  code: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type GuardianRelation = "father" | "mother" | "guardian" | "alternate";

export type Guardian = {
  id: string;
  student_id: string;
  relation: GuardianRelation;
  name: string | null;
  mobile: string;
  is_login_number: boolean;
};

export type AiCheck = "pending" | "matched" | "mismatch" | "cant_read";

export type Marksheet = {
  id: string;
  student_id: string;
  year_label: string;
  file_path: string | null;
  file_name: string | null;
  typed_percentage: number | null;
  ai_check_result: AiCheck;
  ai_read_name: string | null;
  ai_read_percentage: number | null;
  ai_note: string | null;
  created_at: string;
};

export type AttendanceStatus = "P" | "A" | "L";

export type AttendanceRow = {
  id: string;
  student_id: string;
  batch_id: string;
  date: string;
  status: AttendanceStatus;
  marked_by: string | null;
  marked_at: string;
  locked_at: string;
};

export type LedgerRow = {
  id: string;
  student_id: string;
  month: string;
  amount: number;
  paid: number;
  due_date?: string | null;
  label?: string | null;
  installment_no?: number | null;
};

export type PaymentMode = "upi" | "bank" | "cash";

export type Invoice = {
  id: string;
  number: string;
  series_year: number;
  seq: number;
  student_id: string;
  student_code: string;
  student_name: string;
  board: Board;
  class: number;
  month: string;
  fee_amount: number;
  paid_before: number;
  received: number;
  balance_after: number;
  modes: PaymentMode[];
  reference: string | null;
  paid_on: string;
  status: "issued" | "cancelled";
  cancelled_reason: string | null;
  cancelled_by: string | null;
  cancelled_at: string | null;
  emailed_at: string | null;
  created_by: string;
  created_at: string;
};

export type CallOutcome = "will_pay_today" | "promised_date" | "not_connected" | "wrong_number" | "needs_admin";

export type CallLogRow = {
  id: string;
  student_id: string;
  month: string | null;
  guardian_name: string | null;
  guardian_mobile: string;
  called_by: string;
  outcome: CallOutcome;
  follow_up_date: string | null;
  note: string | null;
  attempt_no: number;
  created_at: string;
};

export type Tag = "School" | "Coaching";

export type TimetableEntry = {
  id: string;
  batch_id: string;
  weekday: number;
  start_time: string;
  end_time: string | null;
  subject: string;
  faculty_id: string | null;
  tag: Tag;
};

export type Test = {
  id: string;
  name: string;
  board: Board;
  class: number;
  batch_id: string | null;
  subject: string | null;
  date: string;
  start_time: string | null;
  tag: Tag;
  max_marks: number | null;
  created_by: string | null;
  /** Faculty on duty: marks the test's attendance (and marks) for every student of it. */
  faculty_id?: string | null;
  /** "Test done": moves it from Upcoming to the tests that need marks. */
  done_at?: string | null;
  done_by?: string | null;
};

export type Mark = {
  test_id: string;
  student_id: string;
  score: number | null;
  absent: boolean;
};

export type GroupKind = "batch" | "management" | "faculty";

export type Group = {
  id: string;
  kind: GroupKind;
  batch_id: string | null;
  name: string;
};

export type MessageType = "chat" | "timetable" | "test" | "notice";

export type Message = {
  id: string;
  group_id: string;
  sender_id: string;
  type: MessageType;
  body: string;
  attachment_path: string | null;
  attachment_name: string | null;
  created_at: string;
};

export type Notification = {
  id: string;
  user_id: string;
  kind: string;
  title: string;
  body: string | null;
  link: string | null;
  read_at: string | null;
  created_at: string;
};
