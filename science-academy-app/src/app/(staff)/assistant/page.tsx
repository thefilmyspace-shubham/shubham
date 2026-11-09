import { Bot, CheckCircle2, Download, Eye, Info, ShieldCheck, Trash2, XCircle } from "lucide-react";
import { requirePermission, can } from "@/lib/auth";
import { assistantClient, conversation, type AiMessage } from "@/lib/assistant/chat";
import { capabilitiesFor, suggestionsFor } from "@/lib/assistant/gating";
import type { AiActionRow } from "@/lib/assistant/actions";
import { adminClient } from "@/lib/supabase/admin";
import { rupees, timeLabel } from "@/lib/format";
import { Banner, Card, Chip, Empty, PageHeader } from "@/components/ui";
import { Composer } from "./Composer";
import { cancelAiAction, clearConversation, confirmAiAction } from "./actions";

export const metadata = { title: "AI assistant" };

export default async function AssistantPage() {
  const viewer = await requirePermission("ai.ask");
  const ready = assistantClient() !== null;
  const messages = await conversation(viewer.user.id);
  const actionIds = messages.flatMap((m) => (m.attachment?.kind === "action" ? [m.attachment.id] : []));
  const { data: actionRows } = actionIds.length
    ? await adminClient().from("ai_actions").select("*").in("id", actionIds)
    : { data: [] };
  const actions = new Map(((actionRows ?? []) as AiActionRow[]).map((a) => [a.id, a]));
  const canAct = can(viewer, "ai.act");
  const caps = capabilitiesFor(viewer.perms);

  return (
    <div className="flex min-h-dvh flex-col">
      <PageHeader
        title="AI assistant"
        subtitle={canAct ? "Answers questions · can prepare actions you confirm" : "Read only · answers questions"}
        back="/"
        right={
          messages.length > 0 ? (
            <form action={clearConversation}>
              <button className="btn btn-ghost px-2.5 py-1.5 text-[13px]" title="Clear conversation">
                <Trash2 size={15} /> <span className="hidden sm:inline">Clear</span>
              </button>
            </form>
          ) : null
        }
      />
      <div className="mx-auto w-full max-w-3xl flex-1 space-y-3 px-4 pt-3 pb-4 lg:px-8">
        {!ready && (
          <Banner tone="warn" icon={Info}>
            AI is not set up yet. Add the Claude API key (ANTHROPIC_API_KEY) to the app settings to switch it on.
          </Banner>
        )}
        <Card className="p-4">
          <div className="flex items-center gap-2">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-primary-soft text-primary">
              <Bot size={19} />
            </span>
            <p className="font-bold text-navy">What it can do</p>
          </div>
          <ul className="mt-2 space-y-1 text-[13.5px] text-muted">
            {caps.map((c) => (
              <li key={c} className="flex gap-2">
                <span className="text-green">•</span>
                {c}
              </li>
            ))}
          </ul>
          <p className="mt-2 flex items-start gap-1.5 text-[12px] text-faint">
            <ShieldCheck size={14} className="mt-0.5 shrink-0" />
            It follows the same access as your screens, answers only what you ask, and says when it cannot find something.
            {canAct ? " It never sends anything without your confirmation." : ""}
          </p>
        </Card>

        {messages.length === 0 && ready && <Empty icon={Bot}>Ask a question, or tap a suggestion below.</Empty>}

        {messages.map((m) => (
          <Bubble key={m.id} message={m} action={m.attachment?.kind === "action" ? actions.get(m.attachment.id) : undefined} canAct={canAct} />
        ))}
      </div>
      {ready && <Composer suggestions={messages.length === 0 ? suggestionsFor(viewer.perms) : suggestionsFor(viewer.perms).slice(0, 3)} />}
    </div>
  );
}

function Bubble({ message, action, canAct }: { message: AiMessage; action?: AiActionRow; canAct: boolean }) {
  const mine = message.role === "user";
  const att = message.attachment;
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[88%] space-y-2 ${mine ? "items-end" : ""}`}>
        <div className={`rounded-2xl px-3.5 py-2.5 text-[14px] whitespace-pre-wrap shadow-card ${mine ? "rounded-br-md bg-bubble-out" : "rounded-bl-md bg-bubble-in"}`}>
          {message.body}
          <span className="mt-1 block text-right text-[10.5px] text-faint">{timeLabel(message.created_at)}</span>
        </div>
        {att?.kind === "table" && (
          <Card className="overflow-hidden">
            <div className="flex items-center justify-between gap-2 border-b border-line px-3 py-2">
              <p className="min-w-0 truncate text-[13px] font-bold text-navy">{att.title}</p>
              <a href={`/api/assistant/pdf?message=${message.id}`} className="btn btn-soft shrink-0 px-2.5 py-1 text-[12.5px]">
                <Download size={14} /> PDF
              </a>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[12.5px]">
                <thead>
                  <tr className="text-muted">
                    {att.columns.map((c) => (
                      <th key={c} className="px-3 py-1.5 font-semibold whitespace-nowrap">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {att.rows.map((r, i) => (
                    <tr key={i}>
                      {r.map((cell, j) => (
                        <td key={j} className="px-3 py-1.5 whitespace-nowrap">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
        {att?.kind === "action" && action && <ActionCard action={action} canAct={canAct} />}
      </div>
    </div>
  );
}

function ActionCard({ action, canAct }: { action: AiActionRow; canAct: boolean }) {
  const count = action.payload.students.length;
  return (
    <Card className="border border-warn/30 p-3.5">
      <p className="text-[12px] font-bold tracking-wide text-warn uppercase">Confirm before sending</p>
      <p className="mt-0.5 text-[15px] font-extrabold text-navy">
        {count} {count === 1 ? "parent" : "parents"}, {rupees(action.payload.total)}
      </p>
      <p className="text-[12.5px] text-muted">{action.summary}. Each parent gets a private reminder in their own login. Nothing is posted in groups.</p>
      <details className="mt-2">
        <summary className="flex cursor-pointer items-center gap-1 text-[12.5px] font-bold text-primary">
          <Eye size={14} /> See the list
        </summary>
        <ul className="mt-1.5 max-h-48 space-y-0.5 overflow-y-auto text-[12.5px]">
          {action.payload.students.map((s) => (
            <li key={s.id} className="flex justify-between gap-2">
              <span className="truncate">
                {s.name} <span className="text-faint">{s.code}</span>
              </span>
              <span className="font-semibold">{rupees(s.balance)}</span>
            </li>
          ))}
        </ul>
      </details>
      {action.status === "proposed" && canAct ? (
        <div className="mt-3 flex gap-2">
          <form action={confirmAiAction} className="flex-1">
            <input type="hidden" name="id" value={action.id} />
            <button className="btn btn-green w-full">
              <CheckCircle2 size={16} /> Confirm and send
            </button>
          </form>
          <form action={cancelAiAction}>
            <input type="hidden" name="id" value={action.id} />
            <button className="btn btn-ghost">
              <XCircle size={16} /> Cancel
            </button>
          </form>
        </div>
      ) : (
        <div className="mt-2">
          {action.status === "done" && (
            <Chip tone="ok">
              Sent to {action.result?.sent ?? 0}
              {action.result?.skippedPaid ? ` · ${action.result.skippedPaid} paid since` : ""}
              {action.result?.noLogin ? ` · ${action.result.noLogin} without login` : ""}
            </Chip>
          )}
          {action.status === "cancelled" && <Chip>Cancelled</Chip>}
          {action.status === "confirmed" && <Chip tone="primary">Sending…</Chip>}
          {action.status === "failed" && <Chip tone="danger">Failed</Chip>}
        </div>
      )}
    </Card>
  );
}
