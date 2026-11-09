import { describe, expect, it } from "vitest";
import { parseEmail } from "../otp";

describe("login identifier", () => {
  it("reads emails in any case", () => {
    expect(parseEmail(" ScienceAcademyRTM@Gmail.com ")).toBe("scienceacademyrtm@gmail.com");
    expect(parseEmail("AD-01")).toBeNull();
    expect(parseEmail("9827327824")).toBeNull();
  });
});
