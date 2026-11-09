import { describe, expect, it } from "vitest";
import { compareMarksheet, namesMatch, parseMarksheetReply } from "../ai/marksheet-compare";
import { earlierIds, parseClassQuery, parseRegistration, type IdHistoryRow } from "../students";

describe("marksheet name match", () => {
  it("ignores case, spaces and word order", () => {
    expect(namesMatch("RAHUL  SHARMA", "Rahul Sharma")).toBe(true);
    expect(namesMatch("Sharma Rahul", "Rahul Sharma")).toBe(true);
    expect(namesMatch("Rahul Kumar Sharma", "Rahul Sharma")).toBe(true);
  });
  it("lets initials match full words", () => {
    expect(namesMatch("R. K. Sharma", "Rahul Kumar Sharma")).toBe(true);
    expect(namesMatch("Rahul Sharma", "R Sharma")).toBe(true);
  });
  it("rejects different people", () => {
    expect(namesMatch("Rohit Sharma", "Rahul Sharma")).toBe(false);
    expect(namesMatch("Rahul Verma", "Rahul Sharma")).toBe(false);
    expect(namesMatch("R S", "Rahul Sharma")).toBe(false);
  });
});

describe("marksheet compare", () => {
  const reply = (r: Partial<{ readable: boolean; name: string | null; percentage: number | null; note: string }>) => ({
    readable: true,
    name: "Rahul Sharma",
    percentage: 87.4,
    note: "",
    ...r,
  });
  it("matches within half a percent", () => {
    expect(compareMarksheet(reply({}), "rahul sharma", 87.4).result).toBe("matched");
    expect(compareMarksheet(reply({}), "Rahul Sharma", 87).result).toBe("matched");
    expect(compareMarksheet(reply({}), "Rahul Sharma", 86.8).result).toBe("mismatch");
  });
  it("flags a different name", () => {
    const r = compareMarksheet(reply({ name: "Rohit Sharma" }), "Rahul Sharma", 87.4);
    expect(r.result).toBe("mismatch");
    expect(r.note).toContain("Rohit Sharma");
  });
  it("never guesses on unclear reads", () => {
    expect(compareMarksheet(reply({ readable: false }), "Rahul Sharma", 87.4).result).toBe("cant_read");
    expect(compareMarksheet(reply({ name: null }), "Rahul Sharma", 87.4).result).toBe("cant_read");
    expect(compareMarksheet(reply({ percentage: null }), "Rahul Sharma", 87.4).result).toBe("cant_read");
  });
  it("parses the model reply", () => {
    expect(parseMarksheetReply('```json\n{"readable":true,"name":"A B","percentage":"91.2","note":"ok"}\n```')).toEqual({
      readable: true,
      name: "A B",
      percentage: 91.2,
      note: "ok",
    });
    expect(parseMarksheetReply("sorry")).toBeNull();
  });
});

function form(fields: Record<string, string>): FormData {
  const f = new FormData();
  for (const [k, v] of Object.entries(fields)) f.set(k, v);
  return f;
}

const base = {
  name: "Rahul Sharma",
  board: "MP",
  current_class: "9",
  session_year: "26",
  batch_id: "b1",
  father_name: "Suresh Sharma",
  father_mobile: "+91 98765 43210",
  mother_mobile: "9876543211",
  login_relation: "father",
  consent: "on",
  consent_by: "Suresh Sharma",
  monthly_fee: "2500",
  email: "",
};

describe("registration form", () => {
  it("accepts a full registration", () => {
    const r = parseRegistration(form(base), "register");
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.data.guardians).toEqual([
        { relation: "father", name: "Suresh Sharma", mobile: "9876543210" },
        { relation: "mother", name: null, mobile: "9876543211" },
      ]);
      expect(r.data.loginRelation).toBe("father");
      expect(r.data.student.monthly_fee).toBe(2500);
    }
  });
  it("needs consent, batch and a login number to register", () => {
    const r = parseRegistration(form({ ...base, consent: "", batch_id: "", login_relation: "" }), "register");
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.errors.consent).toBeTruthy();
      expect(r.errors.batch_id).toBeTruthy();
      expect(r.errors.login_relation).toBeTruthy();
    }
  });
  it("lets a draft skip them", () => {
    expect(parseRegistration(form({ ...base, consent: "", batch_id: "", login_relation: "" }), "draft").ok).toBe(true);
  });
  it("login number must be an entered number", () => {
    const r = parseRegistration(form({ ...base, login_relation: "guardian" }), "draft");
    expect(r.ok).toBe(false);
  });
  it("rejects bad and repeated numbers", () => {
    const r = parseRegistration(form({ ...base, mother_mobile: "98765 43210", guardian_mobile: "12345" }), "draft");
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.errors.mother_mobile).toMatch(/already/);
      expect(r.errors.guardian_mobile).toBeTruthy();
    }
  });
});

describe("search helpers", () => {
  it("reads class queries", () => {
    expect(parseClassQuery("class 9")).toEqual({ board: null, cls: 9 });
    expect(parseClassQuery("MP10")).toEqual({ board: "MP", cls: 10 });
    expect(parseClassQuery("cb 12")).toEqual({ board: "CB", cls: 12 });
    expect(parseClassQuery("Rahul")).toBeNull();
  });
  it("lists earlier IDs, newest first", () => {
    const h = (code: string, from: string): IdHistoryRow => ({
      id: code,
      student_id: "s",
      roll_number: 25,
      board: "MP",
      class: 9,
      session_year: 26,
      code,
      valid_from: from,
      valid_to: null,
    });
    expect(earlierIds([h("MP9-025-26", "2026-04-01"), h("MP10-025-27", "2027-04-01"), h("MP8-025-25", "2025-04-01")], "MP10-025-27")).toEqual([
      "MP9-025-26",
      "MP8-025-25",
    ]);
  });
});
