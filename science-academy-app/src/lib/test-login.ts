// Temporary "test login" for the testing group: chosen test accounts log in
// with one shared tester code instead of an emailed code, until a set date.
// Off unless all three settings are present. Never for Admin.
//   TEST_LOGIN_CODE=482917                       six digits, given to testers
//   TEST_LOGIN_UNTIL=2026-11-20                  last day it works (India time)
//   TEST_LOGIN_ACCOUNTS=FC-01,FC-02,RC-01,MG-01,98XXXXXXXX,97XXXXXXXX
//                                                staff IDs and/or parents' login numbers

export type TestLoginSettings = { code?: string; until?: string; accounts?: string };

export function testLoginSettings(): TestLoginSettings {
  return { code: process.env.TEST_LOGIN_CODE, until: process.env.TEST_LOGIN_UNTIL, accounts: process.env.TEST_LOGIN_ACCOUNTS };
}

/** The tester code for this account today, or null when test login does not apply. */
export function testLoginCodeFor(
  user: { role: string; staff_id: string | null; mobile: string },
  today: string,
  s: TestLoginSettings = testLoginSettings(),
): string | null {
  if (!s.code || !/^\d{6}$/.test(s.code) || !s.until || !/^\d{4}-\d{2}-\d{2}$/.test(s.until) || !s.accounts) return null;
  if (today > s.until) return null;
  if (user.role === "admin") return null;
  const list = s.accounts
    .split(",")
    .map((x) => x.trim().toUpperCase())
    .filter(Boolean);
  const mine = [user.staff_id?.toUpperCase(), user.mobile].filter(Boolean) as string[];
  return mine.some((id) => list.includes(id)) ? s.code : null;
}
