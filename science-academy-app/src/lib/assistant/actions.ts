import "server-only";
import { adminClient } from "../supabase/admin";
import { can, type Viewer } from "../auth";
import { logActivity } from "../activity";
import { notify, parentUserOf } from "../notify";
import { balanceOf } from "../fees";
import { monthLabel, rupees } from "../format";
import type { LedgerRow } from "../types";

export type AiActionRow = {
  id: string;
  requested_by: string;
  kind: string;
  summary: string;
  payload: { month: string; total: number; students: { id: string; name: string; code: string | null; balance: number }[] };
  status: "proposed" | "confirmed" | "cancelled" | "done" | "failed";
  result: { sent: number; skippedPaid: number; noLogin: number } | null;
  created_at: string;
  decided_at: string | null;
};

/**
 * Admin confirmed the card: send each parent a private fee reminder (their
 * own login, never a batch group). Balances are checked again first, so a
 * fee paid since the proposal is skipped.
 */
export async function confirmAction(viewer: Viewer, id: string): Promise<{ ok: boolean; error?: string }> {
  if (!can(viewer, "ai.act") || !can(viewer, "fees.view")) return { ok: false, error: "Only Admin can let the AI take actions." };
  const db = adminClient();
  // Claim it once: a double tap cannot send twice.
  const { data: claimed } = await db
    .from("ai_actions")
    .update({ status: "confirmed", decided_at: new Date().toISOString() })
    .eq("id", id)
    .eq("requested_by", viewer.user.id)
    .eq("status", "proposed")
    .select("*")
    .maybeSingle<AiActionRow>();
  if (!claimed) return { ok: false, error: "This action was already decided." };
  if (claimed.kind !== "send_fee_reminders") {
    await db.from("ai_actions").update({ status: "failed" }).eq("id", id);
    return { ok: false, error: "Unknown action." };
  }

  const { month, students } = claimed.payload;
  const { data: ledger } = await db
    .from("fees_ledger")
    .select("*")
    .eq("month", month)
    .in("student_id", students.map((s) => s.id));
  const rows = (ledger ?? []) as LedgerRow[];
  let sent = 0;
  let skippedPaid = 0;
  let noLogin = 0;
  for (const s of students) {
    const row = rows.find((r) => r.student_id === s.id);
    const balance = row ? balanceOf(row) : 0;
    if (balance <= 0) {
      skippedPaid++;
      continue;
    }
    const parent = await parentUserOf(s.id);
    if (!parent) {
      noLogin++;
      continue;
    }
    await notify([
      {
        userId: parent.id,
        kind: "fee_reminder",
        title: "Fee reminder",
        body: `${s.name}: ${rupees(balance)} is due for ${monthLabel(month)}. Please pay at the earliest. Ignore if already paid.`,
        link: "/parent/fees",
        dedupeKey: `fee-reminder:${s.id}:${month}:${id}`,
      },
    ]);
    await db.from("fee_reminders").insert({ student_id: s.id, month, stage: "reminded", created_by: viewer.user.id });
    sent++;
  }
  const result = { sent, skippedPaid, noLogin };
  await db.from("ai_actions").update({ status: "done", result }).eq("id", id);
  await logActivity(viewer, "ai.action", { type: "ai_action", id }, { kind: claimed.kind, summary: claimed.summary, ...result });
  return { ok: true };
}

export async function cancelAction(viewer: Viewer, id: string): Promise<void> {
  if (!can(viewer, "ai.act")) return;
  await adminClient()
    .from("ai_actions")
    .update({ status: "cancelled", decided_at: new Date().toISOString() })
    .eq("id", id)
    .eq("requested_by", viewer.user.id)
    .eq("status", "proposed");
}
