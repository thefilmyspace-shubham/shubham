import "server-only";
import Anthropic from "@anthropic-ai/sdk";
import { adminClient } from "../supabase/admin";
import type { Viewer } from "../auth";
import { ROLE_LABEL } from "../permissions";
import { todayIst } from "../format";
import { sessionLabel, sessionYearFor } from "../ids";
import { toolNamesFor } from "./gating";
import { runTool, toolsFor, type AnswerTable, type ToolContext } from "./tools";

export const ASSISTANT_MODEL = "claude-sonnet-5-5";
const MAX_STEPS = 6;
const HISTORY = 12;

export type AiAttachment = AnswerTable | { kind: "action"; id: string };

export type AiMessage = {
  id: string;
  user_id: string;
  role: "user" | "assistant";
  body: string;
  attachment: AiAttachment | null;
  created_at: string;
};

let client: Anthropic | null = null;

/** Null when ANTHROPIC_API_KEY is not set (the page says AI is not set up yet). */
export function assistantClient(): Anthropic | null {
  if (!process.env.ANTHROPIC_API_KEY) return null;
  client ??= new Anthropic();
  return client;
}

function systemPrompt(viewer: Viewer): string {
  const tools = toolNamesFor(viewer.perms);
  const canAct = tools.includes("propose_fee_reminders");
  return [
    "You are the assistant inside the Science Academy app (a coaching institute in Ratlam, Madhya Pradesh; classes 6 to 12; CBSE and MP Board).",
    `You are helping ${viewer.user.name} (${viewer.user.staff_id}, ${ROLE_LABEL[viewer.user.role]}). Today is ${todayIst()} (India). Session ${sessionLabel(sessionYearFor(new Date()))}.`,
    "",
    "Rules:",
    "- Answer ONLY what was asked. If asked for a student's attendance, give only attendance: no marks, fees or contacts.",
    "- Use the tools for every fact. Never guess or invent names, numbers or IDs. If data is missing or unclear, say so plainly (for example 'No marks entered for this test yet').",
    "- If several students match a name, list them briefly and ask which one. Do not pick one yourself.",
    "- You can only use the tools you have. They already follow this person's access. If asked for something no tool gives (for example fees without the fee tools), say this login does not have access to it.",
    "- Student IDs look like MP9-025-26 (board, class, roll, session). Earlier IDs also work in find_student.",
    "- When a comparison table is made, it is shown under your answer with a Download PDF button; give a 1-2 line summary, not the whole table again.",
    canAct
      ? "- Actions: you never send anything yourself. propose_fee_reminders only prepares a list; the admin sees a confirm card and decides. Say that it is waiting for their confirmation."
      : "- You are read-only for this person. You cannot send messages or change anything; say so if asked.",
    "- Fee reminders go privately to each parent. Never suggest posting fees in a batch group.",
    "- Be short. Plain text, simple English, short lists. Amounts in rupees like ₹35,200.",
  ].join("\n");
}

export type AskResult = { ok: true } | { ok: false; error: string };

/** One question: saved, answered with tools, answer saved (with a table or action card). */
export async function askAssistant(viewer: Viewer, text: string): Promise<AskResult> {
  const question = text.trim().slice(0, 2000);
  if (!question) return { ok: false, error: "Type a question." };
  const ai = assistantClient();
  if (!ai) return { ok: false, error: "AI is not set up yet." };
  const db = adminClient();

  const { data: past } = await db
    .from("ai_messages")
    .select("role, body")
    .eq("user_id", viewer.user.id)
    .order("created_at", { ascending: false })
    .limit(HISTORY);
  await db.from("ai_messages").insert({ user_id: viewer.user.id, role: "user", body: question });

  const history = ((past ?? []) as { role: "user" | "assistant"; body: string }[]).reverse();
  // The API needs turns to alternate, starting with the user.
  const messages: Anthropic.MessageParam[] = [];
  for (const m of history) {
    const last = messages[messages.length - 1];
    if (!last && m.role === "assistant") continue;
    if (last && last.role === m.role) last.content = `${last.content}\n\n${m.body}`;
    else messages.push({ role: m.role, content: m.body });
  }
  if (messages.length && messages[messages.length - 1].role === "user") messages.pop();
  messages.push({ role: "user", content: question });

  const ctx: ToolContext = { table: null, actionId: null };
  const tools = toolsFor(viewer);
  let answer = "";
  try {
    for (let step = 1; step <= MAX_STEPS; step++) {
      const last = step === MAX_STEPS;
      const res = await ai.messages.create({
        model: ASSISTANT_MODEL,
        max_tokens: 2000,
        system: systemPrompt(viewer),
        tools,
        messages,
        ...(last ? { tool_choice: { type: "none" as const } } : {}),
      });
      const textOut = res.content
        .filter((b): b is Anthropic.TextBlock => b.type === "text")
        .map((b) => b.text)
        .join("")
        .trim();
      const calls = res.content.filter((b): b is Anthropic.ToolUseBlock => b.type === "tool_use");
      if (res.stop_reason !== "tool_use" || !calls.length || last) {
        answer = textOut;
        break;
      }
      messages.push({ role: "assistant", content: res.content });
      const results = await Promise.all(
        calls.map(async (call): Promise<Anthropic.ToolResultBlockParam> => {
          const r = await runTool(viewer, call.name, call.input, ctx);
          return { type: "tool_result", tool_use_id: call.id, content: r.content, ...(r.isError ? { is_error: true } : {}) };
        }),
      );
      messages.push({ role: "user", content: results });
    }
  } catch (err) {
    console.error("assistant failed", err);
    answer = "Sorry, I could not answer right now. Please try again.";
  }

  const attachment: AiAttachment | null = ctx.actionId ? { kind: "action", id: ctx.actionId } : ctx.table;
  await db.from("ai_messages").insert({
    user_id: viewer.user.id,
    role: "assistant",
    body: answer || "I could not find an answer to that.",
    attachment,
  });
  return { ok: true };
}

export async function conversation(userId: string, limit = 60): Promise<AiMessage[]> {
  const { data } = await adminClient()
    .from("ai_messages")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(limit);
  return ((data ?? []) as AiMessage[]).reverse();
}
