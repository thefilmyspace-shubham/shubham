import "server-only";
import { allBatches, batchShort } from "@/lib/batches";
import { studentDetails } from "@/lib/students";
import type { Student } from "@/lib/types";
import type { BatchOption, FormInitial } from "./StudentForm";

export async function batchOptions(): Promise<BatchOption[]> {
  const list = await allBatches();
  return list.map((b) => ({ id: b.id, board: b.board, class: b.class, label: batchShort(b) }));
}

export async function formInitial(student: Student): Promise<FormInitial> {
  const d = await studentDetails(student.id);
  const mobiles: FormInitial["mobiles"] = {};
  for (const g of d.guardians) mobiles[g.relation] = { mobile: g.mobile, name: g.name };
  return {
    id: student.id,
    status: student.status,
    code: student.code,
    name: student.name,
    board: student.board,
    current_class: student.current_class,
    session_year: student.session_year,
    school: student.school,
    batch_id: student.batch_id,
    father_name: student.father_name,
    mother_name: student.mother_name,
    guardian_name: student.guardian_name,
    email: student.email,
    monthly_fee: Number(student.monthly_fee),
    feePlan: {
      fee_plan: student.fee_plan ?? "monthly",
      monthly_fee: Number(student.monthly_fee),
      fee_due_day: student.fee_due_day ?? 5,
      fee_schedule: Array.isArray(student.fee_schedule) ? student.fee_schedule : [],
    },
    mobiles,
    loginRelation: d.guardians.find((g) => g.is_login_number)?.relation ?? null,
    marksheets: d.marksheets.slice(0, 2).map((m) => ({
      id: m.id,
      year_label: m.year_label,
      file_name: m.file_name,
      typed_percentage: m.typed_percentage === null ? null : Number(m.typed_percentage),
      ai: m.ai_check_result,
      note: m.ai_note,
    })),
    consentGiven: Boolean(d.consent),
  };
}
