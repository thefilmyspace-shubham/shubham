# Science Academy App

Science Academy (Ratlam) ka apna app: students, fees, bills, attendance, timetable, tests, ranks, groups aur parents ke updates, sab ek jagah. TFS team app jaisa hi phone pe chalta hai, aur computer pe bhi.

Science Academy's own app for about 500 students (classes 6 to 12, CBSE and MP Board): registration, monthly fees and bills, reception call log, faculty attendance on the phone, timetable and tests, ranks, WhatsApp-style groups, a parent app and an AI assistant. It is a web app that works on phones and desktops and can be added to the home screen.

Built from `Science-Academy-App-Spec.md`. Every screen shows "Powered by TFS · The First Solutions".

**Stack:** Next.js 16 (on Vercel, Mumbai region), Supabase (Postgres with row level security, auth sessions, file storage, realtime chat), MSG91 for SMS OTP, Claude API for the marksheet check and the assistant, Resend for emailing bills.

---

## 1. Accounts to make with the new Science Academy email

Make one new Gmail for the academy (for example `scienceacademy.ratlam@gmail.com`; the owner picks the name) and open every account below with it, so the academy owns its data and bills, not TFS.

| Service | What for | Notes |
|---|---|---|
| Gmail | Owner of all accounts below | Turn on 2-step verification. |
| GitHub | Holds the code | Make a private repo `science-academy-app` and push this folder to it (step 3). |
| Supabase | Database, logins, files | New project, region **Mumbai (ap-south-1)**, free plan is fine to start; Pro (daily backups by Supabase too) when live. |
| Vercel | Runs the app | Import the GitHub repo. Region is set to Mumbai in `vercel.json`. |
| MSG91 | SMS OTP | Needs **DLT registration** (Jio / Airtel / Vi DLT portal): register the academy as entity, a 6-letter sender ID (e.g. `SCIACD`), and an OTP template such as `Your Science Academy login code is ##otp##. It is valid for 10 minutes. Do not share it.` Put the approved template into MSG91 Flow and copy the template ID. |
| Anthropic Console | Claude API key | For the AI marksheet check and the AI assistant. Add a small monthly spend limit. |
| Resend | Emailing bills to parents | Verify the academy's domain (or use Resend's test sender while trying). Optional: without it, the Email button says email is not set up. |

## 2. Set up the database (Supabase)

1. Supabase → SQL Editor → New query. Paste and **Run** the files in `supabase/migrations/` **in name order**:
   `20261201000000_init.sql`, then `20261201000100_seed.sql`, then any later files.
   (Or with the CLI: `npx supabase link --project-ref <ref>` then `npx supabase db push`.)
2. Put the owner's real name and mobile on the first Admin login (AD-01):
   ```sql
   update public.users set name = 'Owner Name', mobile = '98XXXXXXXX' where staff_id = 'AD-01';
   ```
3. Do **not** run `scripts/sql/demo-seed.sql` on the live database. It is sample data for demos and local testing only.

## 3. Put it online (Vercel)

1. Push this folder to the academy's GitHub repo:
   ```bash
   git init && git add . && git commit -m "Science Academy app"
   git remote add origin https://github.com/<academy-account>/science-academy-app.git
   git push -u origin main
   ```
2. Vercel → Add New → Project → import the repo.
3. Environment variables (Vercel → Settings → Environment Variables), all listed in `.env.example`:
   - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (Supabase → Project Settings → API)
   - `NEXT_PUBLIC_APP_URL` (the Vercel URL or the academy's domain)
   - `MSG91_AUTH_KEY`, `MSG91_OTP_TEMPLATE_ID`
   - `ANTHROPIC_API_KEY`
   - `RESEND_API_KEY`, `BILL_FROM_EMAIL` (optional)
   - `CRON_SECRET` (any long random text)
   - Bill details: `ACADEMY_ADDRESS`, `ACADEMY_PHONE`, `ACADEMY_UPI_ID`, `ACADEMY_BANK_NAME`, `ACADEMY_ACCOUNT_NUMBER`, `ACADEMY_IFSC`, `ACADEMY_ACCOUNT_NAME`. Until these are set, bills print the placeholders `[YOUR UPI ID]`, `[BANK NAME]` and so on, and no payable QR code is printed.
4. Deploy. The daily job (`vercel.json` → `/api/cron/daily`, 6:00 AM IST) creates the month's fee rows, sends reminders and makes the daily Excel backup.
5. Log in as Admin (role Admin → `AD-01` or the owner's mobile → SMS code). Then, in order:
   1. **Batches & faculty**: add batches (board, class, name, time). Each batch gets its parents' group automatically.
   2. **Access control → Add staff**: Management (MG-xx), Reception (RC-xx), Faculty (FC-xx). Each logs in with their ID or mobile.
   3. Batches & faculty: assign faculty to their batches.
   4. Reception starts registering students.

## 4. Run it on a computer (development)

```bash
npm install
npx supabase start          # local Supabase in Docker (applies the migrations)
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -f scripts/sql/demo-seed.sql   # optional sample data
cp .env.example .env.local  # fill in the local keys printed by `supabase start`
npm run dev
```

Without MSG91 keys, in development the login code is printed in the terminal and shown on the OTP screen. In production a missing SMS setup is an error, never a bypass.

With the demo data: Admin `AD-01`, Management `MG-01`, Reception `RC-01`, Faculty `FC-01`..`FC-03`; parents log in with the father's number shown on a student's profile.

Checks:

```bash
npm run typecheck && npm run lint && npm test   # types, lint, unit tests
npm run test:db                                  # migrations + database rules on a throwaway Postgres
```

## 5. How the important rules work

- **Login:** role → ID or mobile → SMS code (6 digits, 10 minutes, 5 tries, resend after 30 s). Asked once; the person stays logged in on that device until **Log out**. Admin can **Log out everywhere** or **Suspend** a login from Access control; that ends every session at once.
- **Student ID:** `BOARD CLASS-ROLL-SESSION`, e.g. `MP9-025-26`. The roll number comes from one academy-wide counter when **Register** is pressed, is never reused (not after a student leaves, not after a deleted draft), and becomes 4 digits after 999. Promotion changes class and session (`MP9-025-26` → `MP10-025-27`) and keeps the roll; every earlier ID still finds the student and is shown as "Earlier ID". Bills keep the ID the student had that day.
- **Bills:** numbered `SA-26-0001` onwards per session year, made inside one database transaction, so a failed bill never leaves a gap. Bills can't be deleted (the database refuses). Only Admin can cancel, with a reason; the number stays in the list as cancelled and the payment comes off the ledger.
- **Fees:** monthly, due on the 5th. Paid / Partial / Pending / Overdue are worked out from the ledger. Fee reminders go only to the parent's own login, never into a batch group (the group composer blocks fee-like messages).
- **Attendance:** faculty mark it on the phone for their own batches. It locks 24 hours after saving; after that only Admin and Management can correct it, and every correction is logged.
- **Permissions:** defaults follow the table in the spec (§5). Admin changes them per role or per person in **Access control**. Admin-only controls (access control, activity log, promotion, backup, AI actions) can't be given away, and Admin can't lock themselves out. The AI assistant uses the same permissions as the screens.
- **Data safety (children's data):** consent is recorded at registration; no student photos are collected; marksheets and backups sit in private storage opened only through short-lived links after a permission check; every table has row level security on (the browser can only read the chat messages and notifications that belong to it; everything else goes through the server's permission checks); HTTPS everywhere and Supabase encrypts data at rest. The activity log is append-only.

## 6. Open items (from the spec)

- Roll numbers above 999: built as 4 digits (`1000` and up). **Confirm with the owner.**
- Real UPI ID, QR code, bank details, address and phone for the bill (environment variables above).
- Logo: done (`public/brand/`, cut from the owner's file; PDFs use `src/lib/brand-logo.ts`). A bigger original (PNG/PDF/CDR) would print sharper. TFS logo for the footer (text for now).
- MSG91 account and DLT template approval.
- Management correcting attendance: built as allowed and logged (Admin can turn it off in Access control).
