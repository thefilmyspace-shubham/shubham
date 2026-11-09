import { NextResponse, type NextRequest } from "next/server";
import { childrenOf, getViewer } from "@/lib/auth";
import { CHILD_COOKIE } from "@/lib/parent";

/** Switch the child shown in the parent app (only to one of the parent's own children). */
export async function GET(req: NextRequest) {
  const viewer = await getViewer();
  const next = req.nextUrl.searchParams.get("next") ?? "/parent";
  const safeNext = next.startsWith("/parent") ? next : "/parent";
  const res = NextResponse.redirect(new URL(safeNext, req.url));
  if (!viewer || viewer.user.role !== "parent") return res;
  const id = req.nextUrl.searchParams.get("child");
  const children = await childrenOf(viewer.user);
  if (id && children.some((c) => c.id === id)) {
    res.cookies.set(CHILD_COOKIE, id, { httpOnly: true, sameSite: "lax", path: "/", maxAge: 60 * 60 * 24 * 365 });
  }
  return res;
}
