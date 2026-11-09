import { NextResponse, type NextRequest } from "next/server";
import { z } from "zod";
import { findLoginUser, sendLoginCode } from "@/lib/otp";
import { ROLES } from "@/lib/permissions";
import { LANG_COOKIE, asLang, translator } from "@/lib/i18n";

const Body = z.object({
  role: z.enum(ROLES as [string, ...string[]]),
  identifier: z.string().trim().min(3).max(120),
});

/** Step 2 of login: find the person and send them a code (in the login screen's language). */
export async function POST(req: NextRequest) {
  const t = translator(asLang(req.cookies.get(LANG_COOKIE)?.value));
  const parsed = Body.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: t("core.auth.enterIdentifier") }, { status: 400 });
  const { role, identifier } = parsed.data;
  const user = await findLoginUser(role as (typeof ROLES)[number], identifier);
  if (!user) {
    return NextResponse.json({ error: role === "parent" ? t("core.auth.notFoundParent") : t("core.auth.notFoundStaff") }, { status: 404 });
  }
  const result = await sendLoginCode(user, t);
  if (!result.ok) return NextResponse.json(result, { status: result.retryAfter ? 429 : 400 });
  return NextResponse.json(result);
}
