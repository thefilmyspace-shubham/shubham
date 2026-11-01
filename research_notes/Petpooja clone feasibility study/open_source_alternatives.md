# Open-source restaurant POS alternatives as a base for a Petpooja-equivalent (research notes, 2026-11-01)

Scope note: searched GitHub (via `gh search repos`), Hacker News, Product Hunt, Reddit, LinkedIn, Inc42/YourStory/Entrackr for 2025–2026 "open-sourced Petpooja-like" software, then catalogued established projects. GitHub API `repos/*` calls were blocked in this session, so star/licence/date figures come from `gh search repos` output (snapshot 2026-11-01) and repo pages fetched via WebFetch.

## KQ1. Which project is most likely "the recently open-sourced Petpooja-like software"? Evidence.

### Takeaway
The best match is **Nodedr OrderRestro** (GitHub `Raktim94/nodedr-restaurant-pos`): an India-first (GST CGST/SGST + HSN, UPI QR, ₹), AGPL-3.0, self-hosted restaurant POS created on 3 Aug 2026 by NodeDR Infotech Pvt Ltd, which is explicitly marketed as a "free Petpooja billing alternative" and already has ~275 stars / 167 forks. The strong runner-up is **FloCafe** (`FreeOpenSourcePOS/FloCafe`, MIT, created 7 May 2026, ~166 stars, Electron desktop, India tax pack, WhatsApp e-bill), promoted by Codify Apps as the open-source answer to Petpooja. Neither is a "startup that open-sourced its commercial Petpooja clone"; I found no Inc42/YourStory/HN/Reddit/LinkedIn announcement of such an event.

### Cited Findings

**Candidate A — Nodedr OrderRestro (`Raktim94/nodedr-restaurant-pos`)**
- GitHub metadata: created 2026-08-03, last push 2026-11-01, AGPL-3.0, TypeScript, 275 stars; description "Self-hosted restaurant POS with tables, kitchen display, reservations, QR ordering, loyalty and local-network operation." — [GitHub search snapshot via gh CLI, 2026-11-01](https://github.com/Raktim94/nodedr-restaurant-pos)
- Repo page: 275 stars, 167 forks, 247 commits, 12 open issues; developed by NodeDR Infotech Private Limited, maintainer Raktim Ranjit, copyright 2026; AGPL-3.0 with explicit note that modified versions run as a network service must publish source — [GitHub repo](https://github.com/Raktim94/nodedr-restaurant-pos)
- Tech stack: NestJS API, PostgreSQL + Prisma, Next.js (App Router) + Tailwind v4, Socket.IO realtime, TanStack Query, shared Zod schemas, pnpm/Turborepo monorepo, Docker Compose, JWT + optional TOTP 2FA; Windows MSIX client; CasaOS/ZimaOS one-click install; Swagger REST API; MCP server; English/Spanish/French UI — [GitHub repo](https://github.com/Raktim94/nodedr-restaurant-pos)
- Feature list (self-described): dine-in/takeaway billing, bill merge, discounts, gift cards, tips, refunds; India GST (plus US sales tax, EU VAT, Spain IVA) set per branch inclusive/exclusive; UPI QR for exact bill amount with "payment received" sound and customer-facing second screen; KOTs routed to kitchen stations, live KDS, prep tracking; inventory with recipes, weighted-average costing, POs, goods receipts, batch/lot, FIFO waste; attendance, shift scheduling, leave, payroll, tip pool; multi-branch switcher, cross-branch overview, stock transfers; QR table ordering, call waiter, request bill, click & collect, scheduled orders; offline LAN operation (order-taking, billing, KDS, printing run without internet); direct USB ESC/POS printing + cash drawer; 18 reports with CSV/Excel/PDF export and scheduled SMTP email; CRM/loyalty points, referrals, memberships, vouchers, feedback; reservations, waitlist, floor plan; accounting (P&L, balance sheet); RBAC, audit log, backup/restore — [GitHub repo](https://github.com/Raktim94/nodedr-restaurant-pos)
- Docs shipped in repo: TUTORIAL.md (56 screenshots), user-manual PDF, PROJECT.md, ARCHITECTURE.md, ROADMAP.md, SECURITY-AUDIT-REPORT.md, COMPLIANCE-INDIA.md, docs/integrations-api.md, docs/KIOSK-AND-KDS.md; live demo orderrestro.nodedr.com — [GitHub repo](https://github.com/Raktim94/nodedr-restaurant-pos)
- Roadmap timeline (from ROADMAP.md): project started 2026-08-03 and "Phases 0–3 finished the same day"; Phase 4 core 2026-08-04; procurement + USB printing 2026-08-14; multi-region tax/localisation 2026-09-27; Phases 5–7 items 2026-10-04; bank reconciliation, balance sheet, UPI QR, scheduled emails 2026-10-11. Caveat in the log: the 2026-09-27 migration "was not run through Prisma in that session, and backend tests were not run" — [ROADMAP.md](https://raw.githubusercontent.com/Raktim94/nodedr-restaurant-pos/master/ROADMAP.md)
- Explicitly marketed as a Petpooja alternative: Webotapp Academy article (published/updated 2026-10-25, author Paban Bhuyan) titled "Best Free Petpooja Billing Alternative: Nodedr OrderRestro", with a feature table claiming parity on GST billing (CGST+SGST), table/floor management, KDS (built-in vs Petpooja paid add-on), UPI QR, QR self-order, offline/LAN mode, and Petpooja pricing of ₹3,000–₹8,000/outlet/month (figure unverified, vendor-written) — [Webotapp Academy](https://academy.webotapp.com/petpooja-billing-alternative-free-restaurant-pos)
- Developer's case study: OrderRestro is a sibling of "Nodedr POS" (retail POS), reusing its auth/receipt/printing patterns; Raktim Ranjit was the sole named developer (architecture, backend, web app, packaging, docs); no named customers or deployments; no open-sourcing date given — [raktimranjit.com case study](https://raktimranjit.com/projects/orderrestro)
- No launch announcement found on Reddit, LinkedIn or Hacker News; the AlternativeTo listing shows "1 star, 1 fork" (stale) and no reviews — [AlternativeTo](https://alternativeto.net/software/nodedr-orderrestro/about/); [search summary](https://news.ycombinator.com/item?id=7795500) (HN hit was an unrelated 2014 thread)
- Many near-identical forks/mirrors exist (Fedgix, Malesh245, TagoreT, adityachatare, Subhadipwork, rahulb477, anjali-0210), consistent with 167 forks — [Fedgix mirror](https://github.com/Fedgix/nodedr-restaurant-pos); [rahulb477 mirror](https://github.com/rahulb477/restaurant-managment-pos)

**Candidate B — FloCafe (`FreeOpenSourcePOS/FloCafe`)**
- GitHub metadata: created 2026-05-07, last push 2026-11-01, MIT, TypeScript, 166 stars; "Free, open-source, offline-first Point of Sale for cafes, restaurants, and food businesses" — [GitHub search snapshot via gh CLI](https://github.com/FreeOpenSourcePOS/FloCafe)
- Repo page: 166 stars, 78 forks, 1,528 commits, 31 open issues; Electron desktop shell, Express API + WebSocket (port 3001), standalone KDS server (3002), server/waiter app server (3003), Next.js renderer, Zustand, SQLite; installers for Windows/macOS/Linux plus Mac App Store, Microsoft Store, Snap Store; browser POS/KDS over LAN — [GitHub repo](https://github.com/FreeOpenSourcePOS/FloCafe)
- Features: touch counter POS; modifiers; Kanban KDS with prep-time tracking; floor plan; handheld waiter app; split payments (equal split, multiple tenders, partial loyalty redemption); inventory (supplies, recipe portions, deliveries, waste, unit costs, audit log); 58/80 mm thermal receipts and KOTs over USB/network; roles Owner/Manager/Cashier/Server/Chef; 24–25 languages incl. RTL; 131 country profiles; signed, versioned country tax packs; backups + optional Google Drive; loyalty/CRM; cash drawer reconciliation; CSV/Excel reports; multi-counter on LAN; optional WhatsApp bill delivery and cloud reporting — [GitHub repo](https://github.com/FreeOpenSourcePOS/FloCafe)
- Changelog: versions 1.7.9 (2026-07-07) → 3.8.6 (2026-09-13); India tax pack and GSTIN validation entries (2.7.0 on 2026-08-04, 2.9.5 on 2026-08-09, 3.2.2 on 2026-08-17); WhatsApp e-billing added 1.9.9 (2026-07-22); cloud sync/registration entries from 1.8.3 onward; no entries for UPI, Zomato, Swiggy, aggregator, e-invoice or multi-outlet — [CHANGELOG.md](https://raw.githubusercontent.com/FreeOpenSourcePOS/FloCafe/main/CHANGELOG.md)
- Marketing page: FloCafe is made by Codify Apps Private Limited (codify.tech), MIT, latest release 3.13.14; positions itself against Petpooja ("strongest Zomato and Swiggy integration, over 200k Indian restaurants, per-terminal subscriptions"); says FloCafe offers "code access for aggregator and e-invoice integrations" but does not claim built-in Zomato/Swiggy, UPI, inventory, multi-outlet or e-invoicing — [flopos.com/restaurant-pos-india](https://flopos.com/restaurant-pos-india)

**Candidate C — Posnic (`Posnic/POS`)**
- Built by Posnic Innovations, Tamil Nadu, India; AGPL-3.0-only source, bundles MongoDB (SSPL) in packages, commercial licence available; 15 stars, 22 forks, 4,196 commits, 396 open issues; Electron + Node 22 + MongoDB, 925 REST endpoints; GST invoices with IGST/CGST/SGST, HSN, GST filing reports; restaurant KOT and table management, kiosk/customer display; multi-branch; offline-first; e-invoicing "research and design only, no live IRP submission"; till/branch sync only via paid Posnic Cloud — [GitHub Posnic/POS](https://github.com/Posnic/POS)

**Other 2025–2026 candidates checked and ruled out as "the" match**
- `amritmaurya1504/Restaurant_POS_System`: 316 stars, MERN, created 2025-02-27 but last push 2025-03-02 (dormant), licence "Other" — [gh search snapshot](https://github.com/amritmaurya1504/Restaurant_POS_System)
- POSR (`ahmedali5530/restaurant-pos`): 80 stars, 697 commits, React/SurrealDB/Tauri; licence is "POSR Source Available License (PSAL) v1.0", i.e. source-available, not OSI open source; Razorpay listed as a gateway; no aggregator integration — [GitHub](https://github.com/ahmedali5530/restaurant-pos); Product Hunt listing — [Product Hunt](https://www.producthunt.com/p/ahmed-ali/ahmed-ali)
- `satisfecho/pos`: AGPL-3.0, Python, created 2026-01-10, 66 stars, multi-tenant, Stripe + Revolut payments (EU-oriented) — [gh search snapshot](https://github.com/satisfecho/pos)
- `asif7774/Kitchen-POS`: MIT, Electron/React, created 2026-06-17, 6 stars, "GST-compliant billing, direct USB thermal printing, offline" — [gh search snapshot](https://github.com/asif7774/Kitchen-POS)
- Flutter "point_of_sale_system" (studentsdav): GPL-2.0, posted on DEV 2025-06-16 seeking contributors; billing, inventory, loyalty, attendance, expenses; no KOT/GST/offline/printing described; no maturity info — [DEV post](https://dev.to/devpointofsale/open-source-flutter-restaurant-pos-looking-for-contributors-5ga4)
- Several Indian hobby/assignment repos named "petpooja" exist (e.g. `AtulJamdar/PetpoojaClone`, `rahulsinha1139/pp_killer` "Petpooja alternative" with 0 stars, `codeashion-technologies/petpooja`, `Meet57/PetPooja-Sem_7_Project`), none substantial — [gh search snapshot](https://github.com/rahulsinha1139/pp_killer); [Meet57 project](https://github.com/Meet57/PetPooja-Sem_7_Project)
- A shutdown-and-open-source story was not found for India; the only recent restaurant-software shutdown surfaced was UAE's jalebi.io, with no open-sourcing mentioned — [MENA Startup Digest](https://menastartupdigest.com/?p=46700)

### Inferences
- OrderRestro is the most probable referent for "someone recently open-sourced a Petpooja-like software with only 2–3 features' difference": it is the only 2025–2026 project that (a) is Indian, (b) targets the full Petpooja surface (billing+KOT+KDS+inventory+payroll+CRM+reservations+QR ordering+multi-branch+accounting), (c) is publicly framed as a Petpooja replacement, and (d) has meaningful traction (275 stars/167 forks in ~3 months).
- The ROADMAP log ("Phases 0–3 finished the same day" the project started; "session log" entries; migration/tests not run) strongly suggests a largely AI-generated codebase by a single developer. The feature list is broad but depth and production hardening are unproven; no named production deployments exist.
- FloCafe is the more battle-tested desktop product (1,528 commits, store-distributed releases, 60+ changelog versions in 3 months) but is cafe/counter-oriented and has a thinner India feature set (no UPI QR, no multi-outlet, no aggregator).
- If the user's memory is of an MIT-licensed project, it is likely FloCafe; if of a "full restaurant ERP with GST+UPI+payroll", it is OrderRestro.

### Gaps
- Could not confirm an exact "open-sourcing date/announcement" for OrderRestro beyond the repo creation date (2026-08-03); no HN/Reddit/LinkedIn post found.
- Could not verify NodeDR Infotech Private Limited's registration or whether the company ever sold OrderRestro commercially before open-sourcing (search returned nothing).
- Could not fetch the GitHub stars/commit history via API (blocked), so figures are from `gh search` and repo pages on 2026-11-01.
- COMPLIANCE-INDIA.md and ROADMAP.md on `main` returned 404 (ROADMAP fetched from `master`); COMPLIANCE-INDIA.md contents not read.

## KQ2. Which features does the top candidate lack vs Petpooja, and are they major?

### Takeaway
Against Petpooja's advertised scope, OrderRestro's clear gaps are: (1) Zomato/Swiggy/aggregator order integration — MAJOR; (2) native payment-gateway (Razorpay/Paytm/PhonePe/Pine Labs) checkout with auto-confirmation — MAJOR for QSR/high-volume, minor for small dine-in; (3) GST e-invoicing (IRN) — major only for outlets above the e-invoice turnover threshold; plus smaller gaps (per-guest split bills, Tally/SAP connectors, Indian-language UI, native Android captain app, token management, call-centre module, marketplace ecosystem). It already covers GST billing, KOT/KDS, inventory, offline/LAN, payroll, CRM/loyalty, reservations, QR ordering and multi-branch.

### Cited Findings
**Petpooja's advertised feature set (reference)**
- Petpooja.com product lines: Poss (restaurant POS with table view/floor plan, mobile order app, KOT printing), Invoice (GST billing for retail), Attendo (attendance/payroll, biometric), Stepwise (staff tasks); "150k+ businesses" — [petpooja.com](https://www.petpooja.com/)
- SoftwareSuggest listing: plans from "Poss Lite" to "Electron Poss Scale"; Scale tier includes Captain App, Scan & Order, KDS, token management, digital display, self-ordering kiosk, waiter calling device, call centre, table reservations, API, Petpooja Loyalty, virtual wallet, feedback app, online order reconciliation, Tally, SAP/ERP, e-invoice; "90+ reports"; "aggregator integrations" in every plan; offline compatibility; unlimited users/terminals; integrations named: BUSY, Masters India, Razorpay, Reelo, Swiggy, Zoho Books, Zomato, Sodexo, PayTm, UPI, Dunzo, Lazypay, SAP, Mobikwik, UrbanPiper, Pinelabs, Worldline, Sunmi; 10 Indian languages; "Trusted by over 1,00,000 outlets" — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja)
- Petpooja "70+ / 80+ integrations" and a Marketplace of add-on services; CRM with feedback, SMS campaigns, loyalty — [GetApp](https://www.getapp.com/all-software/a/petpooja/); [Petpooja blog on invoice features](https://blog.petpooja.com/finance-compliance/petpooja-invoice-features/)

**OrderRestro — what is missing (from its own README/ROADMAP)**
- Delivery-platform connectors NOT built; Zomato/Swiggy never named; own-delivery (zones, driver assignment) is shipped; live GPS tracking planned — [ROADMAP.md](https://raw.githubusercontent.com/Raktim94/nodedr-restaurant-pos/master/ROADMAP.md); [GitHub repo](https://github.com/Raktim94/nodedr-restaurant-pos)
- Native payment-gateway checkout NOT built; UPI QR shipped but "cashier confirms manually" (no automatic confirmation) — [ROADMAP.md](https://raw.githubusercontent.com/Raktim94/nodedr-restaurant-pos/master/ROADMAP.md)
- E-invoicing not mentioned; GST exists as a per-rate summary report — [ROADMAP.md](https://raw.githubusercontent.com/Raktim94/nodedr-restaurant-pos/master/ROADMAP.md)
- Split billing partial: equal-share calculator is display-only; per-guest separate checks "would need a data-model change" — [ROADMAP.md](https://raw.githubusercontent.com/Raktim94/nodedr-restaurant-pos/master/ROADMAP.md)
- Accounting-software (Tally/Zoho) connectors not built; WhatsApp/SMS only via outbound `campaign.message` webhook; reservation reminders and stock alerts not built; petty cash/expense approvals, purchase returns, reorder suggestions, weighing scale/label printer, SQLite edition, native installers all planned — [ROADMAP.md](https://raw.githubusercontent.com/Raktim94/nodedr-restaurant-pos/master/ROADMAP.md)
- UI languages are English/Spanish/French only (guest QR page and staff nav) — no Hindi or other Indian languages, vs Petpooja's 10 — [GitHub repo](https://github.com/Raktim94/nodedr-restaurant-pos); [SoftwareSuggest](https://www.softwaresuggest.com/petpooja)
- Mobile apps not mentioned; multi-tenant SaaS mode not mentioned (multi-branch only); Windows client untested on physical hardware/printers — [GitHub repo](https://github.com/Raktim94/nodedr-restaurant-pos)
- The vendor-side comparison claims OrderRestro lacks nothing, but omits aggregator integration entirely — [Webotapp Academy](https://academy.webotapp.com/petpooja-billing-alternative-free-restaurant-pos)

**Why aggregator integration is hard to add (gating)**
- Zomato launched a POS Developer Platform in Sept 2024 with onboarding, integration guides and unified API docs for POS partners — [YourStory, Sept 2024](https://ts.yourstory.com/2024/09/zomato-pos-developer-platform-streamlined-faster-integrations)
- A community Zomato POS SDK states partner onboarding requires an NDA, IP whitelisting, and credentials issued by a Zomato contact; the partner API reference is not public; scope = menu, order, outlet management — [Packagist tims/zomato-pos-php-sdk](https://packagist.org/packages/tims/zomato-pos-php-sdk)
- Swiggy access goes through its partner onboarding (form, legal documentation, verification); a former Swiggy engineer describes API docs, staging test accounts and a Cloud Menu API for POS partners — [LimeTray guide](https://limetray.com/blog/zomato-swiggy-api-online-ordering-integrations-guide/); [Substack (secondhand)](https://asadabrar.substack.com/p/2-building-the-3rd-party-order-management)
- UrbanPiper is the common middleware; its docs list Swiggy constraints (e.g. 400-item store limit, cancellations relayed to Swiggy) — [UrbanPiper docs](https://api-docs.urbanpiper.com/downstream/aggregator-constraints/swiggy)
- Petpooja also publishes its own Online Ordering API for aggregators (profile by API Evangelist) — [api-evangelist/petpooja](https://github.com/api-evangelist/petpooja)

**FloCafe — what is missing vs Petpooja (for comparison)**
- No UPI QR, no Zomato/Swiggy, no e-invoice, no multi-outlet, no online ordering in README/changelog; India coverage limited to a tax pack + GSTIN validation; WhatsApp e-bill present — [GitHub repo](https://github.com/FreeOpenSourcePOS/FloCafe); [CHANGELOG.md](https://raw.githubusercontent.com/FreeOpenSourcePOS/FloCafe/main/CHANGELOG.md); [flopos.com](https://flopos.com/restaurant-pos-india)

### Inferences
- Feature-gap classification for OrderRestro vs Petpooja (Indian restaurant context):
  - Zomato/Swiggy order sync + menu push: MAJOR (every plan of Petpooja includes it; it is the #1 reason restaurants pick Petpooja). Requires partner approval + NDA, so cannot be shipped as open source in the normal way — must be built as a private connector by whoever runs the SaaS.
  - Payment-gateway auto-confirmation (Razorpay/Paytm/PhonePe/Pine Labs/Worldline terminals): MAJOR for QSR, moderate for dine-in (manual UPI confirm is an acceptable stopgap).
  - E-invoice (IRN via GSP such as Masters India): MAJOR only for outlets with turnover above the e-invoice threshold; minor for typical single outlets.
  - Per-guest split bills: MINOR–MODERATE (needs data-model change).
  - Tally/Zoho/BUSY export: MODERATE (accountants expect it); CSV export exists.
  - Indian-language UI, native Android captain app, token display, call-centre module, marketplace: MINOR–MODERATE each.
  - Offline, KOT, KDS, GST billing, inventory, payroll, CRM, reservations, QR ordering, multi-branch: PRESENT (depth unverified).
- So the "2–3 features' difference" framing is roughly right if one counts aggregator integration, payment gateway and e-invoicing — but the first is the single most business-critical feature for Indian restaurants.

### Gaps
- No independent review or production deployment of OrderRestro found; feature depth (e.g. KOT reprint, item-level cancellation with reasons, day-end reports, printer templates) could not be verified without running the software.
- COMPLIANCE-INDIA.md not read (404 on `main`), so exact GST invoice fields (FSSAI no., HSN per line, IGST) are unverified beyond the vendor article's claims.
- Petpooja's own feature page does not enumerate everything; plan details come from SoftwareSuggest (third-party, with internal pricing inconsistencies).

## KQ3. Licence implications for building a commercial SaaS on top

### Takeaway
OrderRestro, URY, Posnic and satisfecho/pos are AGPL-3.0: hosting a modified version as a SaaS obliges you to publish your modifications' source to users, so proprietary Zomato/Swiggy connectors would have to be kept as separate services or you would need a commercial licence from the author. FloCafe, TastyIgniter and OSPOS are MIT (no copyleft), Odoo Community is LGPL-3, ERPNext is GPL-3, Floreant uses the non-standard MRPL 1.2, uniCenta/Chromis are GPL-3; POSR is source-available (commercial use needs the author's licence).

### Cited Findings
- OrderRestro: AGPL-3.0; README states modified versions run as a network service must make source available under the same licence — [GitHub repo](https://github.com/Raktim94/nodedr-restaurant-pos)
- Posnic: AGPL-3.0-only; "a commercial license is available for companies that want to keep modifications private"; packages bundle MongoDB under SSPL; name/logo are trademarks — [GitHub Posnic/POS](https://github.com/Posnic/POS)
- A 2026 open-source POS comparison notes: "if you run a modified version as a network service, you owe your users the source" (AGPL network clause) — [OpenCals blog](https://opencals.com/blog/open-source-restaurant-reservation-system)
- URY: AGPL-3.0, built on Frappe/ERPNext — [GitHub ury-erp/ury](https://github.com/ury-erp/ury)
- FloCafe: MIT — [GitHub repo](https://github.com/FreeOpenSourcePOS/FloCafe)
- POSR: "POSR Source Available License (PSAL) v1.0"; commercial and white-label licensing via author email — [GitHub](https://github.com/ahmedali5530/restaurant-pos)
- OSPOS: MIT with two extra conditions (no ownership claims; footer signatures must remain visible on every page) — [OSPOS LICENSE](https://raw.githubusercontent.com/opensourcepos/opensourcepos/master/LICENSE)
- TastyIgniter: MIT, 3,819 stars — [gh search snapshot](https://github.com/tastyigniter/TastyIgniter)
- ERPNext: GPL-3.0; Frappe framework: MIT — [gh search snapshot](https://github.com/frappe/erpnext)
- Floreant POS: MRPL 1.2, maintained by OROCUBE LLC — [Zoftwarehub listing](https://zoftwarehub.com/en-sa/products/floreant-pos/product-details)
- uniCenta oPOS: GPL-3 (community v5.x) — [FitGap](https://us.fitgap.com/products/unicenta); Chromis POS: GPL-3 or later, Java 11 — [SourceForge](https://sourceforge.net/projects/gplpos/)
- SambaPOS-3 repo shows no licence file in metadata; last push 2022-06-22 — [gh search snapshot](https://github.com/emreeren/SambaPOS-3)

### Inferences
- For a multi-tenant commercial SaaS where the Zomato/Swiggy connector is a competitive moat and is built under NDA, an MIT base (FloCafe) or a clean-room own stack is legally simplest. An AGPL base (OrderRestro) is workable only if (a) you are willing to open-source every modification to the POS itself and keep aggregator/payment connectors as separate, API-coupled services (grey area; AGPL "corresponding source" arguments can still apply if tightly coupled), or (b) you negotiate a commercial licence from NodeDR Infotech (none advertised, unlike Posnic).
- AGPL may also deter future acquirers/investors; GPL-3 (ERPNext) is less restrictive for SaaS (no network clause) but still copyleft for distributed desktop/offline builds.

### Gaps
- No explicit commercial-licence offer from NodeDR Infotech found.
- Legal interpretation of AGPL "separate service" boundaries is not settled; a lawyer should review.

## KQ4. Established open-source restaurant POS fallbacks — catalogue and India-readiness

### Takeaway
Mature general-purpose bases exist (Odoo Community POS-restaurant, ERPNext + URY, TastyIgniter for ordering, OSPOS for retail), but none ships Zomato/Swiggy integration, Indian payment-terminal integration, or e-invoicing out of the box; the Java desktop POS lineage (Floreant, uniCenta, Chromis, SambaPOS v3) is largely stale and not India-aware.

### Cited Findings
| Project | Licence | Stars / activity | Stack | Restaurant scope | India-readiness | Missing vs Petpooja |
|---|---|---|---|---|---|---|
| Odoo Community (pos_restaurant) | Odoo Community is LGPL-3 (GitHub shows "other"); 55,468 stars, pushed 2026-11-01 — [gh](https://github.com/odoo/odoo) | very active | Python/JS | Floor plans, table status, move/merge orders, kitchen/bar preparation printers (IoT/Epson), preparation display, bill splitting by product, tips, eat-in vs take-out fiscal positions; self-ordering and online delivery documented separately — [Odoo docs](https://www.odoo.com/documentation/18.0/applications/sales/point_of_sale/restaurant.html) | Indian GST localisation exists via `l10n_in` and many paid/free add-ons (e.g. LGPL-3 Scriptonix GST tax display supporting SGST/CGST/IGST/CESS; Technaureus GST POS receipt; OE l10n_in pack is OPL-1 proprietary) — [Odoo apps](https://apps.odoo.com/apps/modules/19.0/spx_pos_tax_display); [tis_indian_pos_receipt](https://apps.odoo.com/apps/modules/18.0/tis_indian_pos_receipt) | No Zomato/Swiggy (a vendor YouTube video shows a custom connector, not public) — [YouTube](https://www.youtube.com/watch?v=yVVNhMwClpI); UPI QR, captain app, KDS polish, Indian languages, e-invoice need add-ons; heavy ERP for a small restaurant |
| ERPNext + URY | ERPNext GPL-3; URY AGPL-3 — [gh](https://github.com/frappe/erpnext); [URY](https://github.com/ury-erp/ury) | ERPNext 40,835 stars, pushed 2026-11-01; URY 403 stars/251 forks/993 commits, default branch version-2, v1 support ends Dec 2025 | Python/Frappe | URY: dine-in/takeaway/delivery POS, offline mode, printer mgmt, shift open/close, KOT printing, multi-kitchen routing, KDS (Mosaic), mobile order-taking (Serve), BOM recipes, combos/modifiers, inventory+accounting, alerts, P&L; "served 10+ outlets for 10 months"; built by Tridz Technologies Pvt Ltd with Frappe support — [URY](https://github.com/ury-erp/ury); [Frappe forum](https://discuss.frappe.io/t/restaurant-pos-is-this-github-repository-ready-for-production-deployment/79914) | ERPNext has mature India GST localisation (india_compliance app, e-invoice/e-way bill); URY has an "Aggregator" order type but no named Zomato/Swiggy connector; GST not mentioned in URY README | Aggregator sync, UPI dynamic QR, Indian payment terminals; README warns "backward compatibility not guaranteed until stable release" |
| TastyIgniter | MIT — [gh](https://github.com/tastyigniter/TastyIgniter) | 3,819 stars, pushed 2026-10-17 | PHP/Laravel | Online ordering, table reservations, restaurant management; API extension; it is an ordering platform, not a billing/KOT POS — [Capterra](https://www.capterra.in/alternatives/172163/petpooja-restaurant-management-platform) | No GST/UPI/India specifics; no aggregator | Core POS billing, KOT/KDS, inventory, offline |
| Open Source Point of Sale (OSPOS) | MIT + attribution footer clause — [LICENSE](https://raw.githubusercontent.com/opensourcepos/opensourcepos/master/LICENSE) | 4,472 stars, pushed 2026-11-01 | PHP/CodeIgniter | Retail POS; no tables/KOT | Generic tax config | Everything restaurant-specific |
| Floreant POS | MRPL 1.2 (OROCUBE) — [Zoftwarehub](https://zoftwarehub.com/en-sa/products/floreant-pos/product-details) | GitHub mirror `fat-tire/floreantpos` 64 stars, pushed 2026-07-23 (SVN mirror) — [gh](https://github.com/fat-tire/floreantpos) | Java Swing | Classic restaurant POS (tables, kitchen tickets) | None | Aggregators, UPI, GST invoice format, cloud/multi-outlet, modern UI |
| uniCenta oPOS | GPL-3 (community v5.x) — [FitGap](https://us.fitgap.com/products/unicenta) | SourceForge lists v5.0 community / 5.4.0 download, no date — [SourceForge](https://sourceforge.net/projects/gplpos/); GitHub forks last pushed 2015 — [gh](https://github.com/herbiehp/unicenta) | Java | Retail/hospitality POS | None | Same as Floreant; commercial direction unclear |
| Chromis POS | GPL-3+, Java 11 — [SourceForge](https://sourceforge.net/projects/gplpos/) | `ChromisPos/ChromisPOS` 20 stars, created/pushed 2025-08-01; kitchen screen add-on last pushed 2018 — [gh](https://github.com/ChromisPos/ChromisPOS) | Java | uniCenta fork with kitchen screen | None | Same as Floreant |
| SambaPOS v3 | no licence file in repo metadata; v4/v5 commercial — [gh](https://github.com/emreeren/SambaPOS-3) | 555 stars, last push 2022-06-22 | C#/WPF | Touch restaurant POS | None | Stale; Windows-only |
| Posnic | AGPL-3 (+commercial) — [gh](https://github.com/Posnic/POS) | 15 stars, 4,196 commits | Electron/Node/MongoDB | KOT, tables, kiosk; retail-first | GST (CGST/SGST/IGST, HSN, GST reports), Tamil Nadu team | UPI, aggregators, e-invoice (design only), sync paid |
| POSR | source-available (PSAL) — [gh](https://github.com/ahmedali5530/restaurant-pos) | 80 stars, 697 commits | React/SurrealDB/Tauri | Full restaurant stack incl. own delivery app, AI reports | Razorpay listed; Pakistan FBR/PRA fiscalisation | Aggregators; not open source |
| Kasirku | MIT — [gh](https://github.com/rezadrian01/Kasirku) | 60 stars, created 2025-08-17 | TypeScript | Digital menu, Midtrans payments, thermal printing (Indonesia) | None | India features, aggregators |
| `longnick/small-pos-open-source` | MIT | 93 stars, created 2026-08-12 | TypeScript | "Offline-first POS starter for small cafés" | None | Most of Petpooja |

- Zomato- or Swiggy-released open-source POS repos: none found; only unofficial wrappers (e.g. `skvrahul/SwiggyOrderHooks`, which warns it may breach Swiggy TOS) — [GitHub](https://github.com/skvrahul/SwiggyOrderHooks)
- Petpooja-adjacent open repos: `efeone/petpooja_integration` (MIT, Python, Frappe-side Petpooja connector, 1 star), `developeraspire001-glitch/petpooja-middleware` — [gh search snapshot](https://github.com/efeone/petpooja_integration); [GitHub](https://github.com/developeraspire001-glitch/petpooja-middleware)

### Inferences
- For an Indian Petpooja-equivalent, the realistic bases are (1) OrderRestro (closest feature surface, AGPL), (2) FloCafe (MIT, desktop/offline, needs cloud layer, UPI, multi-outlet), (3) ERPNext+URY (strongest GST/accounting compliance via India Compliance app, AGPL, heavy), (4) Odoo Community (LGPL, mature POS-restaurant, needs India/aggregator layer). The Java desktop lineage should be ignored.

### Gaps
- Current maintenance status of uniCenta and Floreant upstream (not GitHub mirrors) could not be verified for 2025–2026.
- Odoo's exact per-module licence (pos_restaurant is in Community, LGPL-3) was not confirmed from a primary page in this session (GitHub lists licence as "other").

## KQ5. How much effort would it realistically save vs building from scratch?

### Takeaway
Using OrderRestro or FloCafe as a base plausibly saves the bulk of commodity POS work (billing, tables, KOT/KDS, inventory, loyalty, reports, printing, offline) — the parts that are not Petpooja's moat — but the business-critical differentiators (approved Zomato/Swiggy connectors, payment-terminal integrations, e-invoicing, multi-tenant cloud, Indian-language UI, hardware certification) still have to be built and, more importantly, require partner approvals that are independent of code.

### Cited Findings
- OrderRestro ships ~20 modules (billing, KOT/KDS, inventory/procurement, payroll, CRM/loyalty, reservations, QR ordering, accounting, 18 reports, printing, webhooks, REST/Swagger API, MCP) with docs and a live demo — [GitHub repo](https://github.com/Raktim94/nodedr-restaurant-pos)
- Its roadmap lists what still needs building (gateway checkout, delivery/accounting connectors, split tender, GPS, petty cash, returns, reorder, scale/label printer, SQLite edition, installers) and notes untested Windows client and un-run migrations/tests — [ROADMAP.md](https://raw.githubusercontent.com/Raktim94/nodedr-restaurant-pos/master/ROADMAP.md); [GitHub repo](https://github.com/Raktim94/nodedr-restaurant-pos)
- FloCafe has store-distributed installers (Mac App Store, Microsoft Store, Snap), 1,528 commits, 60+ releases in three months, and optional cloud reporting — [GitHub repo](https://github.com/FreeOpenSourcePOS/FloCafe); [CHANGELOG.md](https://raw.githubusercontent.com/FreeOpenSourcePOS/FloCafe/main/CHANGELOG.md)
- Zomato/Swiggy POS integration requires partner onboarding (NDA, IP whitelisting, sandbox verification) — [Packagist SDK notes](https://packagist.org/packages/tims/zomato-pos-php-sdk); [LimeTray](https://limetray.com/blog/zomato-swiggy-api-online-ordering-integrations-guide/)
- Petpooja's integrations number 70–80+ and it claims 1,00,000+ outlets — [GetApp](https://www.getapp.com/all-software/a/petpooja/); [SoftwareSuggest](https://www.softwaresuggest.com/petpooja)

### Inferences
- Effort saved (rough, non-sourced estimate): a from-scratch Petpooja-class MVP (billing, KOT/KDS, tables, inventory, reports, offline, printing, CRM, multi-outlet) is typically many engineer-months; OrderRestro's breadth could cut the first 60–70% of that if its code quality holds up on audit. Expect to spend significant time hardening (tests, migrations, printer/hardware QA), replacing the single-tenant assumption with multi-tenancy (or running one container per outlet), and adding the India-critical connectors.
- The remaining ~30–40% (aggregators, gateways, e-invoice, languages, captain Android app, support/onboarding tooling) is exactly what Petpooja sells; it is partner-gated more than code-gated, so starting it in parallel with code evaluation is the critical path.
- Because of AGPL, if the plan is a closed SaaS, FloCafe (MIT) or Odoo (LGPL) is the safer base despite needing more India-specific work; if the plan is open-core/self-hosted with paid connectors as separate services, OrderRestro is the fastest start.

### Gaps
- No independent benchmarks, code audits, or user reports exist for OrderRestro or FloCafe; effort estimates above are inference, not sourced data.
- Petpooja's actual per-plan pricing in INR could not be confirmed from a primary source (SoftwareSuggest shows USD figures with internal inconsistencies; Webotapp's ₹3,000–₹8,000/month is vendor-sourced).
