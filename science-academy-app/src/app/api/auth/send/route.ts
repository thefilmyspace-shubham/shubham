import { NextResponse, type NextRequest } from "next/server";
import { z } from "zod";
import { findLoginUser, sendLoginCode } from "@/lib/otp";
import { ROLES } from "@/lib/permissions";

const Body = z.object({
  role: z.enum(ROLES as [string, ...string[]]),
  identifier: z.string().trim().min(3).max(120),
});

/** Step 2 of login: find the person and send them an SMS code. */
export async function POST(req: NextRequest) {
  const parsed = Body.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: "Enter your email, ID or mobile number." }, { status: 400 });
  const { role, identifier } = parsed.data;
  const user = await findLoginUser(role as (typeof ROLES)[number], identifier);
  if (!user) {
    const what =
      role === "parent"
        ? "No student is registered with this login number or email."
        : "No login found with this email, ID or number for this role.";
    return NextResponse.json({ error: `${what} Please check, or contact the academy.` }, { status: 404 });
  }
  const result = await sendLoginCode(user);
  if (!result.ok) return NextResponse.json(result, { status: result.retryAfter ? 429 : 400 });
  return NextResponse.json(result);
}
