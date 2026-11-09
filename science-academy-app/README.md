# Science Academy App

Science Academy (Ratlam) ka apna app: students, fees, bills, attendance, timetable, tests, ranks, groups aur parents ke updates, sab ek jagah. TFS team app jaisa hi phone pe chalta hai, aur computer pe bhi.

Science Academy's own app for about 500 students (classes 6 to 12, CBSE and MP Board): registration, monthly fees and bills, reception call log, faculty attendance on the phone, timetable and tests, ranks, WhatsApp-style groups, a parent app and an AI assistant. It is a web app that works on phones and desktops and can be added to the home screen.

Built from `Science-Academy-App-Spec.md`. Every screen shows "Powered by TFS · The First Solutions".

**Stack:** Next.js 16 (on Vercel, Mumbai region), Supabase (Postgres with row level security, auth sessions, file storage, realtime chat), the academy's Gmail for login codes and bills (like the TFS app; SMS through MSG91 can be switched on later), Claude API for the marksheet check and the assistant.

---

## 1. Accounts to make with the new Science Academy email

Make one new Gmail for the academy (for example `scienceacademy.ratlam@gmail.com`; the owner picks the name) and open every account below with it, so the academy owns its data and bills, not TFS.

| Service | What for | Notes |
|---|---|---|
| Gmail | Owner of all accounts below, and sends login codes and bills | Turn on 2-step verification, then make an **App password** (Google Account → Security → 2-Step Verification → App passwords, name it "Science Academy App"). Copy the 16 letters. |
| GitHub | Holds the code | Make a private repo `science-academy-app` and push this folder to it (step 3). |
| Supabase | Database, logins, files | New project, region **Mumbai (ap-south-1)**, free plan is fine to start; Pro (daily backups by Supabase too) when live. |
| Vercel | Runs the app | Import the GitHub repo. Region is set to Mumbai in `vercel.json`. |
| MSG91 (later, optional) | SMS OTP instead of email | Not needed to start. Needs **DLT registration** (Jio / Airtel / Vi DLT portal): register the academy as entity, a 6-letter sender ID (e.g. `SCIACD`), and an OTP template such as `Your Science Academy login code is ##otp##. It is valid for 10 minutes. Do not share it.` Put the approved template into MSG91 Flow and copy the template ID. |
| Anthropic Console | Claude API key | For the AI marksheet check and the AI assistant. Add a small monthly spend limit. |

## WhatsApp fee reminders (optional)

Every day (about 9 AM) the app:
1. **A day before a due date** sends the parent a WhatsApp message (and an in-app reminder).
2. **On the due date** tells Reception who is due today, to call tomorrow if unpaid.
3. **The day after**, if still unpaid, makes a **call task** at the top of Reception's Call log. Logging the call closes it.

Steps 2 and 3 and the in-app reminder work without WhatsApp. For the WhatsApp message:
1. business.facebook.com (with the academy Gmail) → **WhatsApp Manager** → add a phone number for the academy (a number not already used on the WhatsApp app).
2. **Message templates → Create**: category **Utility**, name `fee_due_tomorrow`, language English, body for example:
   `Dear Parent, the fee of {{1}} of {{2}} is due on {{3}}. Please pay on time. – Science Academy, Ratlam`
3. When it is approved: **Business settings → System users** → make a permanent token with `whatsapp_business_messaging`.
4. In Vercel add `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` (from WhatsApp Manager → API setup), `WHATSAPP_FEE_TEMPLATE=fee_due_tomorrow`, then Redeploy.

Meta charges a small fee per message. Every message sent (or failed) is recorded in the `whatsapp_messages` table, and a fee row never gets the same message twice.

## 2. Set up the database (Supabase)

1. Supabase → SQL Editor → New query. Paste and **Run** the files in `supabase/migrations/` **in name order**:
   `20261201000000_init.sql`, then `20261201000100_seed.sql`, then any later files (`20261201000300_fee_plans.sql`, `20261201000400_language.sql`, `20261201000500_fee_automation.sql` ...). Later files are safe to run again.
   (Or with the CLI: `npx supabase link --project-ref <ref>` then `npx supabase db push`.)
2. Put the owner's real name and mobile on the first Admin login (AD-01):
   ```sql
   update public.users set name = 'Owner Name', mobile = '98XXXXXXXX', email = 'owner@gmail.com' where staff_id = 'AD-01';
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
   - `OTP_CHANNEL` = `email`, `SMTP_USER` (the academy Gmail), `SMTP_PASSWORD` (the 16-letter App password)
   - `ANTHROPIC_API_KEY`
   - `CRON_SECRET` (any long random text)
   - Bill details: `ACADEMY_ADDRESS`, `ACADEMY_PHONE`, `ACADEMY_UPI_ID`, `ACADEMY_BANK_NAME`, `ACADEMY_ACCOUNT_NUMBER`, `ACADEMY_IFSC`, `ACADEMY_ACCOUNT_NAME`. Until these are set, bills print the placeholders `[YOUR UPI ID]`, `[BANK NAME]` and so on, and no payable QR code is printed.
4. Deploy. The daily job (`vercel.json` → `/api/cron/daily`, about 9 AM IST) creates the month's fee rows, runs the fee reminder automation, sends reminders and makes the daily Excel backup.
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

Without `SMTP_USER`/`SMTP_PASSWORD` (or MSG91 keys for SMS), in development the login code is printed in the terminal and shown on the OTP screen. In production a missing setup is an error, never a bypass.

With the demo data: Admin `AD-01`, Management `MG-01`, Reception `RC-01`, Faculty `FC-01`..`FC-03`; parents log in with the father's number shown on a student's profile.

Checks:

```bash
npm run typecheck && npm run lint && npm test   # types, lint, unit tests
npm run test:db                                  # migrations + database rules on a throwaway Postgres
```

## 5. How the important rules work

- **Login:** role → ID or mobile → 6-digit code by **email** (10 minutes, 5 tries, resend after 30 s). Staff get it on their own email (Admin sets it in Access control); a parent gets it on the email saved on their child's registration (needed to Register). Set `OTP_CHANNEL=sms` once MSG91/DLT is ready to send it by SMS to the mobile instead. Asked once; the person stays logged in on that device until **Log out**. Admin can **Log out everywhere** or **Suspend** a login from Access control; that ends every session at once.
- **Student ID:** `BOARD CLASS-ROLL-SESSION`, e.g. `MP9-025-26`. The roll number comes from one academy-wide counter when **Register** is pressed, is never reused (not after a student leaves, not after a deleted draft), and becomes 4 digits after 999. Promotion changes class and session (`MP9-025-26` → `MP10-025-27`) and keeps the roll; every earlier ID still finds the student and is shown as "Earlier ID". Bills keep the ID the student had that day.
- **Bills:** numbered `SA-26-0001` onwards per session year, made inside one database transaction, so a failed bill never leaves a gap. Bills can't be deleted (the database refuses). Only Admin can cancel, with a reason; the number stays in the list as cancelled and the payment comes off the ledger.
- **Fees:** each student has a payment plan chosen at registration: **Monthly** (fee + due day of the month), **One time**, **Installments** (total, how many, first date, gap; the app splits it and every date/amount can be changed) or a **Manual** schedule. Every fee row has its own due date; Admin and Reception change dates, amounts and the plan on the student's Fees page (logged). Paid / Partial / Pending / Overdue are worked out from the ledger. Fee reminders go only to the parent's own login, never into a batch group (the group composer blocks fee-like messages).
- **Attendance:** faculty mark it on the phone for their own batches. It locks 24 hours after saving; after that only Admin and Management can correct it, and every correction is logged.
- **Permissions:** defaults follow the table in the spec (§5). Admin changes them per role or per person in **Access control**. Admin-only controls (access control, activity log, promotion, backup, AI actions) can't be given away, and Admin can't lock themselves out. The AI assistant uses the same permissions as the screens.
- **Data safety (children's data):** consent is recorded at registration; no student photos are collected; marksheets and backups sit in private storage opened only through short-lived links after a permission check; every table has row level security on (the browser can only read the chat messages and notifications that belong to it; everything else goes through the server's permission checks); HTTPS everywhere and Supabase encrypts data at rest. The activity log is append-only.

## 6. Open items (from the spec)

- Roll numbers above 999: built as 4 digits (`1000` and up). **Confirm with the owner.**
- Real UPI ID, QR code, bank details, address and phone for the bill (environment variables above).
- Logo: done (`public/brand/`, cut from the owner's file; PDFs use `src/lib/brand-logo.ts`). A bigger original (PNG/PDF/CDR) would print sharper. TFS logo for the footer (text for now).
- SMS login (optional, later): MSG91 account and DLT template approval, then `OTP_CHANNEL=sms`.
- Management correcting attendance: built as allowed and logged (Admin can turn it off in Access control).
