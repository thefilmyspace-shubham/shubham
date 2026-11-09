import { NextResponse, type NextRequest } from "next/server";
import { getViewer } from "@/lib/auth";
import { endSession } from "@/lib/session";
import { logActivity } from "@/lib/activity";

/** Log out on this device. */
export async function POST(req: NextRequest) {
  const viewer = await getViewer();
  if (viewer) await logActivity(viewer, "auth.logout", { type: "user", id: viewer.user.id });
  await endSession(viewer?.sessionId ?? null);
  return NextResponse.redirect(new URL("/login", req.url), { status: 303 });
}
