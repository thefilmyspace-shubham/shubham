import { describe, expect, it } from "vitest";
import { isLocked, overrideSummary, resolvePermissions } from "../permissions";

describe("permissions engine", () => {
  it("follows the spec defaults", () => {
    const mg = resolvePermissions("management", {}, {});
    expect(mg["fees.view"]).toBe(false);
    expect(mg["groups.post_batch"]).toBe(true);
    const rc = resolvePermissions("reception", {}, {});
    expect(rc["bills.create"]).toBe(true);
    expect(rc["bills.cancel"]).toBe(false);
    expect(rc["groups.post_batch"]).toBe(false);
    const fc = resolvePermissions("faculty", {}, {});
    expect(fc["students.contacts"]).toBe(false);
    expect(fc["attendance.mark"]).toBe(true);
    expect(fc["ai.ask"]).toBe(false);
    const ad = resolvePermissions("admin", {}, {});
    expect(Object.values(ad).every(Boolean)).toBe(true);
  });
  it("person beats role beats default", () => {
    const p = resolvePermissions("faculty", { "ranks.view": false }, { "ranks.all_batches": true });
    expect(p["ranks.view"]).toBe(false);
    expect(p["ranks.all_batches"]).toBe(true);
    const q = resolvePermissions("faculty", { "ranks.view": false }, { "ranks.view": true });
    expect(q["ranks.view"]).toBe(true);
  });
  it("locks admin-only keys and the admin column", () => {
    expect(isLocked("management", "ai.act")).toBe(true);
    expect(isLocked("admin", "fees.view")).toBe(true);
    const p = resolvePermissions("management", { "admin.access": true }, { "ai.act": true });
    expect(p["admin.access"]).toBe(false);
    expect(p["ai.act"]).toBe(false);
    const a = resolvePermissions("admin", { "fees.view": false }, { "fees.view": false });
    expect(a["fees.view"]).toBe(true);
  });
  it("summarises per-person changes", () => {
    expect(overrideSummary("faculty", {}, { "ranks.all_batches": true })).toBe("1 extra: see ranks of all batches");
    expect(overrideSummary("faculty", {}, {})).toBeNull();
  });
});
