import { NextResponse } from "next/server";
import { getViewer } from "@/lib/auth";
import { vapidKeys } from "@/lib/push";

/** The public push key for this app (logged-in people only). */
export async function GET() {
  const viewer = await getViewer();
  if (!viewer) return NextResponse.json({ error: "Login required" }, { status: 401 });
  const k = await vapidKeys();
  if (!k) return NextResponse.json({ error: "Not set up" }, { status: 503 });
  return NextResponse.json({ publicKey: k.publicKey });
}
