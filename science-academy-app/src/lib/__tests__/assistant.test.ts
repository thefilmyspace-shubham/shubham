import { describe, expect, it } from "vitest";
import { resolvePermissions } from "../permissions";
import { canUseAssistant, toolAllowed, toolNamesFor } from "../assistant/gating";

describe("assistant tool gating", () => {
  it("admin gets every tool, including the action", () => {
    const tools = toolNamesFor(resolvePermissions("admin", {}, {}));
    expect(tools).toContain("propose_fee_reminders");
    expect(tools).toContain("overdue_list");
    expect(tools).toContain("student_contacts");
  });
  it("management never gets fee data or actions", () => {
    const tools = toolNamesFor(resolvePermissions("management", {}, {}));
    expect(tools).not.toContain("fee_status");
    expect(tools).not.toContain("overdue_list");
    expect(tools).not.toContain("propose_fee_reminders");
    expect(tools).toContain("compare_batches");
    expect(tools).toContain("student_attendance");
  });
  it("reception can ask about fees but cannot act", () => {
    const tools = toolNamesFor(resolvePermissions("reception", {}, {}));
    expect(tools).toContain("overdue_list");
    expect(tools).not.toContain("propose_fee_reminders");
  });
  it("faculty cannot use the assistant at all by default", () => {
    const perms = resolvePermissions("faculty", {}, {});
    expect(canUseAssistant(perms)).toBe(false);
    expect(toolNamesFor(perms)).toEqual([]);
  });
  it("follows per-person changes", () => {
    const noContacts = resolvePermissions("reception", {}, { "students.contacts": false });
    expect(toolAllowed("student_contacts", noContacts)).toBe(false);
    // ai.act is admin-only: an override cannot give it to management.
    const tried = resolvePermissions("management", {}, { "ai.act": true, "fees.view": true });
    expect(toolAllowed("propose_fee_reminders", tried)).toBe(false);
    expect(toolAllowed("fee_status", tried)).toBe(true);
  });
});
