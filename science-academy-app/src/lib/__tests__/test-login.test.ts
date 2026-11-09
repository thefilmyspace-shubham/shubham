import { describe, expect, it } from "vitest";
import { testLoginCodeFor } from "../test-login";

const s = { code: "482917", until: "2026-11-20", accounts: "FC-01, rc-01,9810000037" };
const fc = { role: "faculty", staff_id: "FC-01", mobile: "9000000031" };

describe("test login", () => {
  it("works for listed accounts until the date", () => {
    expect(testLoginCodeFor(fc, "2026-11-10", s)).toBe("482917");
    expect(testLoginCodeFor({ role: "reception", staff_id: "RC-01", mobile: "9000000021" }, "2026-11-20", s)).toBe("482917");
    expect(testLoginCodeFor({ role: "parent", staff_id: null, mobile: "9810000037" }, "2026-11-10", s)).toBe("482917");
  });
  it("stops after the date, for unlisted accounts, and never for Admin", () => {
    expect(testLoginCodeFor(fc, "2026-11-21", s)).toBeNull();
    expect(testLoginCodeFor({ role: "faculty", staff_id: "FC-02", mobile: "9000000032" }, "2026-11-10", s)).toBeNull();
    expect(testLoginCodeFor({ role: "admin", staff_id: "AD-01", mobile: "9000000000" }, "2026-11-10", { ...s, accounts: "AD-01" })).toBeNull();
  });
  it("is off unless fully set up", () => {
    expect(testLoginCodeFor(fc, "2026-11-10", { ...s, code: "" })).toBeNull();
    expect(testLoginCodeFor(fc, "2026-11-10", { ...s, code: "1234" })).toBeNull();
    expect(testLoginCodeFor(fc, "2026-11-10", { ...s, until: undefined })).toBeNull();
  });
});
