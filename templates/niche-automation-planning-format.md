# Niche Automation Planning Format

Jab bhi kisi naye business type (restaurant, gym, salon, clinic, coaching, kirana...) ke liye automation ya software banana ho, yeh format copy karo aur har section bharo. Rule: jab tak Section 1 se 4 nahi bhare, code mat likhna.

Copy karne ke liye: `cp templates/niche-automation-planning-format.md plans/<niche>-plan.md`

---

## 0. Niche snapshot (10 min)

| Sawaal | Jawab |
|---|---|
| Business type | |
| India mein kitne outlets (source ke saath) | |
| Hum kitne owners ko personally jaante hain | |
| Owner software kitni baar use karega: roz / hafte / mahine | |
| Kya government compliance hai (GST, FSSAI, licence, e-invoice) | |
| Abhi kaam kaise chalta hai: register / Excel / WhatsApp / koi app | |
| Owner ka average monthly revenue | |
| Woh software pe saal ka kitna de sakta hai (revenue ka 0.5–1%) | |

**Red flag check:** agar use "mahine mein ek baar" hai aur koi compliance nahi, toh product sticky nahi hoga. Gym jaisa case. Tab daily-use hook dhoondo (attendance, schedule, bill) warna niche chhod do.

---

## 1. Dominant player check (1–2 ghante research)

Har niche ka ek "Petpooja" hota hai, ya nahi hota. Dono case mein yeh table bharo.

| Sawaal | Jawab |
|---|---|
| Market leader kaun hai, kitne outlets | |
| Unka pricing format (per outlet/saal, per user/mahina, % of sales, freemium) | |
| Unki actual price INR mein | |
| Unke top 10 features | |
| Unke add-ons jo alag se bikte hain | |
| Unki 5 sabse badi complaints (Play Store, G2, Techjockey, Reddit) | |
| Kya koi free ya open-source alternative hai, kaunse features missing | |
| Unka moat kya hai: integration, field sales, compliance, hardware, brand | |
| Leader ka cost structure: field-heavy ya online | |

**Nikalna kya hai:** (a) kaunse features table stakes hain jo bina diye product bikta hi nahi, (b) kaunsi complaint hum solve kar sakte hain, (c) leader ka moat hum copy kar sakte hain ya nahi.

---

## 2. Day in the life (owner ke saath 30 min call)

Owner se poochho: subah se raat tak kya-kya karte ho. Har kaam ki ek row.

| Kaam | Kitni baar (roz/hafta/mahina) | Kaun karta hai | Kitna time | Abhi kaise (manual/semi/auto) | Dard score 1–5 | Automate ho sakta hai? |
|---|---|---|---|---|---|---|
| | | | | | | |

Minimum 15 rows. Jo kaam roz hota hai aur dard 4+ hai, wahi pehla feature hai.

Common buckets jo har niche mein hote hain:
- Paisa aana: bill, UPI, udhaar, pending payment, reminder
- Paisa jaana: supplier, salary, kharcha
- Log: attendance, shift, commission, hiring
- Customer: database, repeat, reminder, feedback, reviews
- Stock: kya khatam ho raha hai, order kab karna
- Compliance: GST, licence renewal, logs
- Reporting: owner ko raat ko kya jaanna hai
- Third party: aggregators, marketplaces, banks

---

## 3. Feature tiers

Section 2 ke rows ko in 5 tiers mein baanto. Tier 1 aur 2 = MVP. Baaki baad mein.

**Tier 1: Daily hook (sticky banata hai)**
Jo feature owner ya staff roz 5+ baar use kare. Bina iske product chhoot jaata hai.
- 

**Tier 2: Paisa (pay karne ki wajah)**
Billing, udhaar, pending payment reminder, daily sales summary. Yeh owner ko dikhne wala value hai.
- 

**Tier 3: Compliance (chhodne se darr)**
GST reports, licence reminders, records. Data yahan lock hota hai.
- 

**Tier 4: Automation (hamara USP)**
WhatsApp bots, AI summary, reconciliation, auto-reminders, forecasting. Yahan Claude API aur WhatsApp API lagti hai.
- 

**Tier 5: Baad mein / kabhi nahi**
Jo leader ke paas hai par koi use nahi karta, ya jo banane mein mehenga hai aur value kam.
- 

---

## 4. Hard dependency check (yahin pe cost tay hoti hai)

Har "haan" ek cost aur ek delay hai. Restaurant mein 4 haan the, gym mein 0.

| Dependency | Haan/Nahi | Agar haan toh kya chahiye | Cost | Time |
|---|---|---|---|---|
| Hardware (printer, scanner, biometric, terminal) | | | | |
| Offline chalna zaroori (net gaya toh dukaan rukegi?) | | | | |
| Third-party permission (Zomato/Swiggy jaisa partner API, NDA) | | | | |
| Government API (GSP for e-invoice, e-way bill) | | | | |
| Payment gateway (card MDR) ya sirf UPI QR kaafi | | | | |
| Multi-outlet / multi-user | | | | |
| Regional language UI | | | | |
| Bahut zyada volume (1 lakh+ records/outlet/saal) | | | | |

**Rule:** agar 3+ haan hain toh pilot se pehle woh permissions/hardware shuru karo, kyunki woh critical path hai, code nahi.

---

## 5. Reuse checklist (zero-cost ka asli source)

Pehle dekho humare paas kya bana hua hai. Naya sirf wahi likho jo yahan nahi hai.

| Module | Hai? | Kahan se (project/repo) | Is niche mein kaam aayega? |
|---|---|---|---|
| GST billing + invoice PDF | | | |
| Parties / udhaar khata | | | |
| WhatsApp reminder (utility messages) | | | |
| Daily summary to owner (raat ka WhatsApp) | | | |
| Attendance (QR/phone) | | | |
| Salary / commission calc | | | |
| Customer database + tags | | | |
| Stock + low-stock alert | | | |
| Reports / export | | | |
| GST assistant (Claude, rules in system prompt) | | | |
| Auth, multi-tenant, roles | | | |
| Payment link / UPI QR | | | |

---

## 6. Cost sheet (pilot, 5–20 customers)

Code ki cost lagbhag zero maano (AI tools). Baaki lines bharo.

| Line | Estimate | Note |
|---|---|---|
| Code | ₹0 | Founder time |
| Infra (Supabase/E2E, 20 outlets) | ₹2,000–5,000/mahina | |
| WhatsApp API | ₹0.115/utility msg | Messages/mahina × rate |
| SMS (agar chahiye) | ₹0.15/msg + ₹5,900 DLT | Avoid, WhatsApp use karo |
| Claude API | ₹500–12,000/mahina | Haiku vs Opus, Section 4 ke hisaab se |
| Government/partner API | | Section 4 se |
| Test hardware | | Section 4 se |
| Play Store / Apple | ₹2,000 ek baar / ₹8,500 saal | |
| Domain, SSL, email | ₹2,000–5,000/saal | |
| Support (pehle 6 mahine) | Founder time | |
| Onboarding per customer | ₹300–800 remote | Field install ₹1,500–3,500, avoid |
| **Pilot total (6 mahine)** | | |

---

## 7. Distribution plan (sabse mehenga hissa, isliye sabse pehle)

| Sawaal | Jawab |
|---|---|
| Pehle 5 customers kaun (naam) | |
| Woh abhi kya use karte hain aur kitna dete hain | |
| Unse referral kaise aayenge (WhatsApp group, association, dealer) | |
| Reseller channel kaun ho sakta hai (printer dealer, CA, supplier) | |
| Pricing model: per outlet/saal, per mahina, free + paid tier, % of sales | |
| Hamari price vs leader ki price | |
| Break-even kitne customers pe (Section 6 total ÷ per-customer margin) | |
| Agar 6 mahine mein 30 referrals nahi aaye toh kya: band, ya agency add-on | |

---

## 8. Sticky test (launch se pehle, haan/nahi)

- [ ] Staff ya owner roz use karega (Tier 1 hai)
- [ ] Owner ka paisa isse dikhta hai (Tier 2 hai)
- [ ] Data yahan lock hota hai (customers, udhaar, GST history)
- [ ] Chhodne pe compliance ya reporting toot jaati hai
- [ ] Leader se ek cheez saaf behtar hai (price, support, ek automation)
- [ ] Bina field visit ke onboard ho sakta hai (video + WhatsApp)

4 se kam tick = product sticky nahi hai, scope badlo.

---

## 9. Go / No-go score

Har line 1–5. Total 35 mein se.

| Criteria | Score |
|---|---|
| Market size (outlets × jo de sakte hain) | |
| Leader kamzor ya absent | |
| Daily use frequency | |
| Compliance pull | |
| Hard dependencies kam (Section 4 mein 0–1 haan) | |
| Reuse zyada (Section 5 mein 6+ modules) | |
| Distribution ready (Section 7 mein 5 naam) | |
| **Total** | |

- 28+: pilot shuru karo
- 20–27: ek cheez fix karo (usually distribution ya daily hook), phir dubara score
- 20 se kam: chhod do, agli niche

---

## Example: Gym (short, reference ke liye)

- Snapshot: ~46,500 commercial gyms, koi leader nahi, use mahine mein 1 baar (renewal) = red flag, compliance nahi
- Leader: koi nahi, 20 chhote players ₹500–25,000/mahina, sab same features
- Daily hook dhoondha: member QR attendance + trainer ka daily client schedule
- Tier 2: membership plan, renewal reminder WhatsApp, pending payment list, GST bill
- Hard dependencies: 0 haan
- Reuse: billing, parties, WhatsApp reminder, daily summary, attendance = 5 modules
- Cost: pilot ₹50,000 ke andar
- Distribution: jo gyms jaante hain wahan se, warna skip
- Score: market 2, leader 4, daily use 2 (hook ke baad 4), compliance 1, dependency 5, reuse 4, distribution ? = decide after naming 5 gyms
