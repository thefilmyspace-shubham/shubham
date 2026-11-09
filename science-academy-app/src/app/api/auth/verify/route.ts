import { NextResponse, type NextRequest } from "next/server";
import { z } from "zod";
import { verifyLoginCode } from "@/lib/otp";
import { startSession } from "@/lib/session";
import { logActivity } from "@/lib/activity";
import { resolvePermissions } from "@/lib/permissions";
import { adminClient } from "@/lib/supabase/admin";
import { LANG_COOKIE, asLang, isLang, translator } from "@/lib/i18n";

const Body = z.object({ challenge: z.string(), code: z.string().trim() });

/** Step 3 of login: check the code and sign in on this device (until Log out). */
export async function POST(req: NextRequest) {
  const t = translator(asLang(req.cookies.get(LANG_COOKIE)?.value));
  const parsed = Body.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: t("core.auth.enterCode") }, { status: 400 });
  const result = await verifyLoginCode(parsed.data.challenge, parsed.data.code, t);
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: 400 });
  try {
    await startSession(result.user, req.headers.get("user-agent"));
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: t("core.auth.signInFailed") }, { status: 500 });
  }
  const user = result.user;
  // First login on a device where a language was chosen: keep it on the login too.
  const chosen = req.cookies.get(LANG_COOKIE)?.value;
  if (!user.language && isLang(chosen)) await adminClient().from("users").update({ language: chosen }).eq("id", user.id);
  await logActivity(
    { user, sessionId: "", perms: resolvePermissions(user.role, {}, {}), ownBatchIds: null },
    "auth.login",
    { type: "user", id: user.id },
  );
  return NextResponse.json({ ok: true, home: user.role === "parent" ? "/parent" : "/" });
}
