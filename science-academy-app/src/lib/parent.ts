import "server-only";
import { cookies } from "next/headers";
import { childrenOf, requireParent, type Viewer } from "./auth";
import type { Student } from "./types";

export const CHILD_COOKIE = "sa_child";

/**
 * The parent and the child they are looking at. A parent with two children
 * in the academy switches between them with the child strip (?child=<id>,
 * remembered in a cookie). A parent only ever gets their own children.
 */
export async function parentContext(childParam?: string | null): Promise<{ viewer: Viewer; children: Student[]; child: Student | null }> {
  const viewer = await requireParent();
  const children = await childrenOf(viewer.user);
  const jar = await cookies();
  const wanted = childParam ?? jar.get(CHILD_COOKIE)?.value ?? null;
  const child = children.find((c) => c.id === wanted) ?? children[0] ?? null;
  return { viewer, children, child };
}
