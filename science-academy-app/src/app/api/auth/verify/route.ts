import { NextResponse, type NextRequest } from "next/server";
import { z } from "zod";
import { verifyLoginCode } from "@/lib/otp";
import { startSession } from "@/lib/session";
import { logActivity } from "@/lib/activity";
import { resolvePermissions } from "@/lib/permissions";

const Body = z.object({ challenge: z.string(), code: z.string().trim() });

/** Step 3 of login: check the code and sign in on this device (until Log out). */
export async function POST(req: NextRequest) {
  const parsed = Body.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: "Enter the 6 digit code." }, { status: 400 });
  const result = await verifyLoginCode(parsed.data.challenge, parsed.data.code);
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: 400 });
  try {
    await startSession(result.user, req.headers.get("user-agent"));
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Could not sign in. Please try again." }, { status: 500 });
  }
  const user = result.user;
  await logActivity(
    { user, sessionId: "", perms: resolvePermissions(user.role, {}, {}), ownBatchIds: null },
    "auth.login",
    { type: "user", id: user.id },
  );
  return NextResponse.json({ ok: true, home: user.role === "parent" ? "/parent" : "/" });
}
