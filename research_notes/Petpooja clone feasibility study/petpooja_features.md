# Petpooja (Prayosha Food Services Pvt Ltd, Ahmedabad) — Complete Feature Inventory, as of late 2026

Research date: 1 Nov 2026. Primary sources are petpooja.com product pages and blog.petpooja.com (vendor marketing — self-reported claims), supplemented by App Store listings, third-party software directories (SoftwareSuggest, Techjockey, GetApp/Capterra, G2 — partly blocked), press (Entrackr, Free Press Journal, BW Disrupt, ANI), and one competitor review (DineOpen — treat as adversarial). Petpooja's help centre (help.petpooja.com) and G2 feature pages returned nothing/403, so some operational minutiae (shift close, cash drawer, e-invoice flow) are gaps.

**Legend used throughout:** `[CORE]` = included in base POS plan; `[ADD-ON]` = Petpooja-built marketplace add-on, bundled into higher tiers or sold per-outlet; `[3P]` = third-party marketplace integration; `[SIDE-PRODUCT]` = separate Petpooja product line (own pricing); `[UNCERTAIN]` = single/old source.

---

## Company, scale, platforms, plans & packaging (context for all modules)

### Takeaway
Petpooja is a 14-year-old (founded 2011) cloud restaurant POS with ~1,00,000+ outlets across India, UAE and South Africa, ~60 lakh bills/day, "200+ features in 9 modules", 94+ reports, 15 apps (4 desktop + 11 mobile), four POS builds (Electron, Local, Android, Lite) and a Base/Core → Growth → Scale tiering in which most add-ons are bundled by tier rather than priced individually.

### Cited Findings
- Claims "1,50,000+ businesses across the globe", "14+ years", "0% processing errors", 10-minute free demo; products: Poss (restaurant POS), Attendo (ex-Petpooja Payroll), Invoice (retail GST billing), Stepwise (ex-Petpooja Tasks); regional sites for India, UAE, Singapore, Malaysia, Thailand, South Africa, US, Canada — [Petpooja home](https://www.petpooja.com/)
- POSS page claims 1,00,000+ restaurants, 60 lakh+ bills/day, 150+ integrations, 80+ reports (billing section) / 100+ downloadable reports (analytics section), 10 outlet-type verticals (food court/canteen, cafe, fine dine, bar & brewery, pizzeria, QSR, ice cream, large chain, bakery, cloud kitchen) — [Petpooja POSS](https://www.petpooja.com/poss)
- Vendor blog (updated 28 Sep 2026): "over 200" features in 9 modules (Billing, KOT, Menu, Inventory, Online Order Management, CRM, Reports, Aggregator Centre, Dashboard); 94+ named reports; 120+ marketplace services; 70+ third-party integrations; 50 lakh+ raw-material catalogue; 18+ Indian languages; 15 Petpooja apps (4 desktop, 11 mobile); plans sold per outlet per year; tiers Basic/Growth/Scale (Growth = 5 marketplace services from a pool on Electron/Local; Scale = all reachable services + E-invoice credits); no free trial — [Petpooja blog: 200+ tools](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/)
- Four POS builds and their capability limits: Electron (full inventory, full reports, dynamic reports, multi-outlet); Local (offline-only inventory, full reports but no dynamic reports, multi-outlet); Android (inventory via connector, limited reports, no multi-outlet); Lite (no inventory, limited reports, no 5-day offline, no Purchase Manager, no call-centre) — [Petpooja blog: 200+ tools](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/)
- Official pricing page lists no rupee amounts ("local pricing may vary"); tiers Basic, Core, Growth (Popular), Scale; billed monthly or annually; comparison rows: Cloud Billing, Inventory Module, 80+ Reports, In-built CRM, Menu management, Unlimited terminals & user rights, Central kitchen module, Multi-terminal billing, add-ons (KDS, Captain app, Restaurant website, Petpooja loyalty, Token Management, Feedback App/QR, OOW website, QR Ordering/Digital menu), Dynamic reports, On-call/chat support, Dedicated POC; FAQ: one licence can run multiple billing stations; migration team moves CRM data and reinstalls aggregator setups; runs on iOS, Windows, Android (laptops, PCs, tablets, phones); supports A4 and thermal printers via WiFi, LAN, USB, Bluetooth, plus label printers — [Petpooja pricing](https://www.petpooja.com/poss/pricing)
- SoftwareSuggest plan table (USD/yr + 18% GST): Electron Poss Core $133 (cloud POS, inventory, menu, 90+ reports, aggregator integrations, unlimited users/terminals, multi-outlet, offline, 24x7 support); Growth $222 (+1 visit/yr, any 5 marketplace services); Scale $333 (+2 visits/yr, Captain App, Scan & Order, KDS, token mgmt, digital display, self-ordering kiosk, call-centre module, table reservations, API, loyalty, virtual wallet, feedback app, Tally and SAP/ERP integration); Android Poss $100 (standard menu, limited inventory, offline, aggregators, dynamic reports, purchase manager, call centre, website, feedback app, Tally/SAP, API); Poss Lite $67 (basic menu, limited reports, aggregators, website, reconciliation, limited Scan & Order); Local Poss Core $222 / Growth $333 / Scale $444 (data on local device, offline inventory, waiter-calling device AMC in Scale) — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja)
- Techjockey listing: Core ₹10,000 / Growth ₹20,000 / Scale ₹30,000 per outlet per year excl. GST; Growth add-ons = Scan & Order, Feedback, KDS, Token app, Captain app, Website, Virtual wallet; Scale add-ons = Invoice, Payroll, Tasks, Dynamic reports, Reservation manager; OS: Windows, iOS, Android, macOS (FAQ also mentions Linux); desktop app historically required Adobe AIR; hardware sold separately — [Techjockey](https://techjockey.com/detail/petpooja-pos)
- Competitor DineOpen (checked Petpooja pricing page 21 Oct 2026): POS Base ₹12,000; Operations Manager Growth ₹20,000 / Scale ₹30,000; Marketing Manager Core ₹20,000 / Growth ₹30,000 / Scale ₹40,000 (all "+taxes", billing period not stated); WhatsApp credits 4,000/8,000/10,000 by tier; 1,000 e-invoice credits in Ops Scale; KDS/Captain/QR ordering in Ops Growth; loyalty/CRM in Marketing Core; website in Marketing Growth — [DineOpen pricing 2026](https://www.dineopen.com/blog/petpooja-pricing-plans-2026.html); Base includes billing, inventory, reports, aggregator integrations, unlimited users/terminals, online installation & training, and "an AI agent" — [DineOpen review 2026](https://www.dineopen.com/blog/petpooja-review-2026)
- Series C: ₹137 Cr ($15.5M) led by Dharana Capital, announced 29 Sep 2025, est. post-money ~₹910 Cr; 1,00,000+ clients in India, UAE, South Africa; claims ~25% of Zomato/Swiggy online order volume flows through it; FY24 revenue ₹76 Cr (+43%), loss ₹13.4 Cr; proceeds for product portfolio, "AI-driven automation", support — [Entrackr](https://entrackr.com/news/petpooja-raises-155-mn-series-c-at-over-3x-valuation-premium-10512396)
- Languages: Arabic, Bengali, English, Gujarati, Hindi, Kannada, Malayalam, Punjabi, Tamil, Urdu (SoftwareSuggest); bills/POS in 15+ Indian languages (billing page) — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja); [Billing page](https://www.petpooja.com/poss/restaurant-billing-software)
- Apple developer roster (Prayosha Food Services): Petpooja – Merchant App, Petpooja Captain App, Attendo: Employee, Attendo: Admin, Petpooja Tasks, Purchase Scan, Stepwise – SOP Management — [App Store Merchant App](https://apps.apple.com/app/id1362012013)

### Inferences
- Pricing is packaged as Base + two parallel upgrade ladders ("Operations Manager" = Captain/KDS/QR/token/kiosk; "Marketing Manager" = CRM/loyalty/website/WhatsApp credits), so a clone's packaging should separate ops add-ons from marketing add-ons.
- Price points across sources (₹10–12k base; ₹20–40k upper tiers; ~$67–$444 international) are consistent in magnitude; exact rupee figures are not officially published and change.

### Gaps
- Official per-add-on rupee prices (Petpooja refers to account managers). Hardware price list not published anywhere found.
- Whether "Basic" (pricing page) equals "Base" (DineOpen) or Poss Lite is unclear.

---

## 1. Core billing / POS

### Takeaway
Core POS covers dine-in (table/area/floor plan), takeaway, delivery, QSR counter billing; station-wise KOT printing; split/merge/move bills; multi-tax and discount config; 5-day offline with sync; unlimited terminals synced to a master; multi-outlet with outlet-wise user rights; day-end summary; digital/e-bills and dynamic payment QR on bills. E-invoicing exists as credit-metered feature in Scale; shift/cash-drawer handling is only lightly documented.

### Cited Findings
- `[CORE]` "3-click" billing; KOT generation; bill splitting; table merging; discounts and coupons — [POSS page](https://www.petpooja.com/poss)
- `[CORE]` Customizable bill format (logo, bill break-ups, editable customer details, dynamic payment QR on bill); multi-terminal billing synced to one master station, captains can generate KOTs and settle bills; station-wise KOT printing (each cooking station its own printer, status synced to master); table & area management (each dine-in area own menu, own service-tax rate, customisable seating); multiple tax types/rates and discounts by service type/regional norms; works offline + cloud; "200+ integrable hardware devices"; keyboard and touchscreen views; QR scan-and-order; e-bill receipts; digital bill saved and messaged to customer's registered number; 15+ Indian languages; owner dashboard real-time sales — [Billing page](https://www.petpooja.com/poss/restaurant-billing-software)
- `[CORE]` Day End Summary (close the day in <5 min on one screen); User Rights per staff login incl. whether settled bills can be edited; Five Days Offline billing with sync on reconnect (not on POS Lite); Food Ready Reminder flags KOTs past a set time; food-ready tokens print at a named station — [Petpooja blog: 200+ tools](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/)
- `[CORE]` Floor plan with table status indicators, KOT and bill printing (home page Poss description) — [Petpooja home](https://www.petpooja.com/)
- `[CORE]` Techjockey checklist: split, merge, move and edit items on bills; category-wise KOTs; multi-terminal; role management with hierarchical roles; unlimited users and unlimited cash registers (Core plan); home delivery management; separate dine-in and takeaway menus; offline mode with cloud sync; 200+ printers supported — [Techjockey](https://techjockey.com/detail/petpooja-pos)
- `[CORE]` Split bill: table total divided among guests with separate payment entries at settlement; one guest UPI, another card, third cash, each logged separately — [Petpooja glossary: split bill](https://blog.petpooja.com/glossary/split-bill/)
- `[CORE]` Staff rights "to limit fraud and pilferage" (Restaurant Rights & Reports highlight) — [Billing page](https://www.petpooja.com/poss/restaurant-billing-software)
- Reports exist for bill modifications, discounted & cancelled orders, cash-drawer operations, staff scheduling, day-end — [Reports page](https://www.petpooja.com/poss/reports-and-analytics)
- `[ADD-ON, credit-metered]` E-invoice credits: 1,000 included in Ops Scale (DineOpen reading of pricing page); Scale tier includes "E-invoice credits" (vendor blog) — [DineOpen pricing](https://www.dineopen.com/blog/petpooja-pricing-plans-2026.html); [Petpooja blog](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/)
- Auto-settlement: once an integrated payment confirms, the order closes and the table is freed (Petpooja Finance) — [Petpooja Finance blog](https://blog.petpooja.com/industry-business-guides/petpooja-finance-money-layer-in-pos/)
- UAE edition: VAT auto-calculated, FTA-audit-ready invoices; split/merge bills; multi-branch from one login — [Petpooja UAE](https://www.petpooja.com/ae/poss)
- Merchant/Owner mobile app (iOS v2.1.0, updated 17 Oct 2025): real-time stats, sales and revenue per outlet, alerts on critical events — [App Store Merchant App](https://apps.apple.com/app/id1362012013)

### Inferences
- "Unlimited terminals & user rights" being a plan row implies per-terminal licensing is not used; a master-station + satellite architecture (LAN sync) is the model.
- QSR-specific flow = counter billing + token management add-on + kiosk; there is no distinct "QSR mode" named.

### Gaps
- No official documentation found on shift open/close, cash-in/cash-out, cash drawer reconciliation workflow, or tip handling (help.petpooja.com not reachable via search).
- Exact e-invoice (IRN) generation flow inside POSS not documented (only for the retail Invoice product).

---

## 2. Menu management

### Takeaway
Menu module (core) supports categories, variations, add-ons, combos, item shortcodes, per-area/per-channel menus and pricing, time-based availability, one-click item on/off across POS/aggregators/kiosk, and head-office menu push to selected outlets with per-outlet push tracking.

### Cited Findings
- `[CORE]` Item categories; variations with own settings; add-ons with separate prices; aggregator menu sync (edit items, prices, available hours from one place); item on/off from POS; item shortcodes for fast billing; multiple menus (one per dine-in area, separate pricing for physical vs online); multi-platform online menus for chains from owner dashboard; one-click full-menu update; per-platform menu toggle from billing screen; time-based open/close availability; "special menus, dynamic pricing, and offers" named without detail — [Menu page](https://www.petpooja.com/poss/restaurant-menu-management-software)
- `[CORE]` Head-Office Menu Push (one change to selected outlets via guided workflow); Pushed-Changes Tracking (per-outlet progress/log); Menu On/Off across counter, aggregator apps and kiosk at once — [Petpooja blog: 200+ tools](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/)
- `[CORE]` Combos, separate dine-in/takeaway menus, time-based menus, location-based pricing — [Techjockey](https://techjockey.com/detail/petpooja-pos)
- Menu with variations, combos, add-ons, multi-language menus (UAE) — [Petpooja UAE](https://www.petpooja.com/ae/poss)
- Online menu settings: store timings, packaging charges, discounts for online orders; packaging options and special offers pushed across platforms — [Online ordering page](https://www.petpooja.com/poss/online-order-management-software)
- Recipe upload service: Petpooja team uploads your full menu + ingredients — [Inventory page](https://www.petpooja.com/poss/restaurant-inventory-management-software)
- Android Poss has "standard menu management" only; Lite "basic menu" — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja)

### Inferences
- "Multiple price lists per channel" is realised as separate menus per area + separate online menu pricing + per-aggregator menu, rather than a single item with N price lists.

### Gaps
- No documentation found on item images at POS level, bulk CSV upload, nutritional/allergen tags, or menu versioning.

---

## 3. Inventory & recipe management

### Takeaway
Inventory (Electron full; Local offline-only; Android via connector; Lite none) includes raw-material stock, multi-stage recipes with auto-deduction, low-stock and expiry alerts, purchase orders/invoices/bill-payment tracking, supplier management, central-kitchen module with outlet stock requests, returns and route plans, e-way bills, COGS breakdown, a daily stock-closing accuracy tracker and (new 2026) an "AI Inventory Agent" that auto-updates stock.

### Cited Findings
- `[CORE on Electron/Local]` Raw-material management with restocking plans, low-stock alerts and menu-availability control; automated stock deduction ("stock-keeping in under 15 minutes"); stock transfer between outlets from one dashboard; online menu toggling by stock; offline inventory; multi-stage recipe management (consumption tracked at each stage); recipe upload service; central kitchen module supplying one or many outlets; stock requests/supply between CK and outlets; damaged stock returns to source; CK dashboard; PO raise/accept with suppliers or CK; frequent-order tracking by supplier/outlet/zone; supplier management; delivery routes for supplier deliveries; e-way bill generation for POs auto-uploaded to GST portal; raw material catalogue 50 lakh+ items — [Inventory page](https://www.petpooja.com/poss/restaurant-inventory-management-software)
- Low-Stock and Expiry Alerts; Purchase and Invoice Management (raise POs, record purchases, track purchase-bill payments); Purchase Manager (live supplier price compare, one-tap reorder, purchases sync to inventory in ~2 hours); Daily Stock Closing Tracker (scores closing-stock accuracy, shows days not closed); COGS Breakdown chart; AI Inventory Agent (auto-updates stock levels so manual counts become checks) — [Petpooja blog: 200+ tools](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/)
- Recipe management with multi-stage recipes and food-costing reports; supplier and central-kitchen modules; food wastage tracking; smart weighing-scale integration — [Techjockey](https://techjockey.com/detail/petpooja-pos)
- Reports page: item-wise consumption reports; recipe costs and raw-material price trends — [Reports page](https://www.petpooja.com/poss/reports-and-analytics)
- Chain page: CK supplies raw/semi-cooked items, per-outlet low-stock alerts, consolidated route plan when outlets raise POs — [Large chain page](https://www.petpooja.com/poss/large-chain-restaurant-pos-software)
- UAE: inventory with recipe costing and AI inventory agent updating stock as sales/purchases happen — [Petpooja UAE](https://www.petpooja.com/ae/poss)
- G2 reviewers single out inventory incl. low-stock alerts; some plans bundle inventory, others sell it as paid add-on — [G2 via search summary](https://www.g2.com/products/petpooja/features) `[UNCERTAIN: G2 page returned 403]`
- `[ADD-ON, free]` Purchase Manager: compares HyperPure, DMart and local suppliers (rate card via Excel); live prices/discounts; "Best Match" auto-picks lowest price per item into cart; multi-vendor single checkout; auto-updates POSS inventory; free with POSS, setup <3 min; more vendors "coming soon"; available on Electron/Local/Android not Lite — [Purchase Manager page](https://www.petpooja.com/poss/purchase-manager); [Petpooja blog](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/)
- Older "Petpooja Suppliers Hub" free add-on for buying supplies and kitchen equipment from verified suppliers `[UNCERTAIN: older post, likely superseded by Purchase Manager]` — [Suppliers Hub blog](https://blog.petpooja.com/poss/petpooja-suppliers-hub-your-one-stop-solution-for-all-restaurant-supplies/)

### Inferences
- "Consumption variance" is not named as a feature; the closest are the Daily Stock Closing Tracker (expected vs closed stock) and item-wise consumption reports.
- Wastage tracking is confirmed only by a third-party listing; official pages do not describe a wastage module.

### Gaps
- No official detail on physical stock audit/cycle count UI, batch/expiry FIFO, yield/conversion factors, or variance reports.

---

## 4. Online ordering & aggregator integration

### Takeaway
Aggregator Centre (core, no Petpooja commission) brings Zomato, Swiggy, Dineout (India) / Talabat, Deliveroo, Careem, Noon (UAE) orders to one screen with central menu sync, stock-linked item on/off, configurable auto-accept, packaging charges/timings, third-party rider dispatch (Dunzo, Shadowfax, Pidge), plus Petpooja-built "My Website" ordering, Scan & Order QR, a call-centre module and ONDC onboarding. There is no native Petpooja rider app and no native WhatsApp ordering bot (third-party only).

### Cited Findings
- `[CORE]` Integrates Swiggy, Zomato, Dineout "among others"; multiple aggregators on one POS; single-screen intake; central menu edits propagate to all aggregators; add items, packaging options, add-ons, offers, prices across platforms; online menu settings (timings, packaging charges, discounts); multi-outlet online menu control; stock-linked on/off; platform-wise commission/surplus/profit/tax reports; payout comparison; rider app integrations with "Duzno" [sic, Dunzo], Shadowfax, Pidge; business-website add-on with own payment gateway (e.g. Razorpay); Scan & Order and Scan & Pay QR add-ons; Petpooja charges no commission on aggregator orders — [Online ordering page](https://www.petpooja.com/poss/online-order-management-software)
- `[CORE]` Online-Order Auto-Accept within a set window with change logging; "My Website" Petpooja-built ordering site, orders flow into POS, no commission; Aggregator Centre is one of the nine modules — [Petpooja blog: 200+ tools](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/)
- From one screen: accept online orders, manage online menu, mark food ready, collect payment, track revenue, KOT view — [POSS page](https://www.petpooja.com/poss)
- Cloud-kitchen vertical: Virtual Brand Management (multiple brands in tabs on one POS, no extra charge), multi-channel order screen, CK management, KDS, reconciliation — [Cloud kitchen page](https://www.petpooja.com/poss/cloud-kitchen-pos-software)
- `[CORE on Electron/Local/Android]` Call-centre module: web app where a central team takes phone orders for all outlets, picks the outlet, order prints in that outlet's kitchen; known phone number pulls past orders and saved address; not on Lite; call recording not included — [Petpooja blog: call centre](https://blog.petpooja.com/industry-business-guides/restaurant-call-centre-software-phone-orders/)
- `[ADD-ON]` Online Order Token Management: Android TV app showing pickup orders with live status and token numbers; mark-ready from POS or KDS; Zomato/Swiggy rider OTP check-in; voice alert on food-ready; works online and offline; needs Android TV with Play Store on same network — [Token page](https://www.petpooja.com/poss/online-order-token-management)
- `[ADD-ON]` Online Order Reconciliation (Zomato, Swiggy): matched orders with IDs, status mismatches (delivered vs cancelled), amount variances (tax/discount/rounding), missing orders both directions, commission/discount breakdown per order, filter/search, outlet or chain roll-up; merchant shares payout reports each cycle; pricing via account manager — [Reconciliation page](https://www.petpooja.com/poss/online-order-reconciliation); shows net commission, gross profit after cancellations, TCS, discounts; upload aggregator payout reports — [Cloud kitchen page](https://www.petpooja.com/poss/cloud-kitchen-pos-software)
- ONDC: Petpooja ONDC landing page positions POSS as entry point to ONDC buyer apps — [Petpooja ONDC](https://www.petpooja.com/ondc); GrowthFalcons partnership pilot (live transaction 5 May 2022) to onboard SMB restaurants onto ONDC `[UNCERTAIN: 2022-era]` — [BW Disrupt](https://www.bwdisrupt.com/article/restaurant-software-provider-petpooja-expands-collaborates-with-ondc-439890); Finance reconciliation FAQ covers Swiggy, Zomato and ONDC orders — [Petpooja Finance blog](https://blog.petpooja.com/industry-business-guides/petpooja-finance-money-layer-in-pos/)
- UAE: Talabat, Deliveroo, Careem, Noon orders on one POS screen "directly, no middleware"; 15+ integrations — [Petpooja UAE](https://www.petpooja.com/ae/poss)
- Techjockey names Zomato, Swiggy, Dunzo, Uber Eats as online-ordering integrations — [Techjockey](https://techjockey.com/detail/petpooja-pos); Goodcall lists Zomato, Swiggy, Uber Eats, Dunzo, Paytm, Razorpay, Google Sheets, Zapier `[UNCERTAIN: aggregator page]` — [Goodcall](https://www.goodcall.com/business-productivity-ai/petpooja)
- `[3P]` Delivery dispatch: Jungleworks Tookan integration for dispatch — [Jungleworks](https://jungleworks.com/integrate-your-petpooja-account-with-tookan-for-smart-delivery-management); Yelo D2C storefront integration (categories/products sync, order push, status updates; add-ons and taxes not synced) — [Jungleworks help](https://help.jungleworks.com/yelo/petpooja-integration/)
- `[3P]` WhatsApp ordering: Edesy AI phone/WhatsApp order bot pushes orders into Petpooja POS — [Edesy](https://edesy.in/restaurant-order-bot/integrations/petpooja); Gallabox WhatsApp chatbot connector (setup "in development" ~500 days ago) — [Gallabox docs](https://docs.gallabox.com/bots/bot-connectors/send-your-whatsapp-data-to-petpooja-using-chatbot); OwnChat syncs POS customer/order data into WhatsApp marketing — [OwnChat](https://ownchat.app/blog/petpooja-whatsapp-marketing-with-ownchat)
- Competitor claims WhatsApp ordering, loyalty and advanced analytics require paid add-ons — [DineOpen review](https://www.dineopen.com/blog/petpooja-review-2026)
- Petpooja Online Ordering API (partner-facing): Apiary docs with groups Orders, Stores, Stock, Callbacks; lets partners sync menu, push orders into POS, receive status callbacks, toggle item stock and store availability; OpenAPI + Postman collection catalogued by third party — [API Evangelist GitHub](https://github.com/api-evangelist/petpooja); keys (access token, restaurant ID, app key, app secret) obtained from support@petpooja.com — [Jungleworks help](https://help.jungleworks.com/yelo/petpooja-integration/); Frappe/ERPNext app receives Petpooja order webhooks (POS, Zomato, Swiggy) and creates Sales Invoices — [Frappe marketplace](https://cloud.frappe.io/marketplace/apps/petpooja)

### Inferences
- "Petpooja Rider" does not exist as a product; delivery is handled via aggregator riders or 3P fleets (Dunzo/Shadowfax/Pidge/Porter-type) through the marketplace. A clone needs a rider-partner abstraction rather than a fleet app to match parity.
- WhatsApp is used by Petpooja for marketing credits, feedback requests and Tasks reminders, not for a native ordering bot.

### Gaps
- Official current list of supported Indian aggregators beyond Zomato/Swiggy/Dineout (e.g., Magicpin, EatSure, Thrive) not published on fetched pages.
- Porter integration not confirmed in any source found.

---

## 5. CRM & marketing

### Takeaway
In-built CRM (core) unifies customer records from POS, online, website and Captain app, with 100+ labels/segments, exports, promo opt-outs, points at billing and 7+ campaign types; loyalty wallet, SMS marketing, feedback app and restaurant website are marketplace add-ons bundled in "Marketing Manager" tiers, which also carry WhatsApp message credits (4k/8k/10k). Reservations/waitlist is a separate Table Reservation Manager add-on pulling Zomato Dining, District and EazyDiner bookings.

### Cited Findings
- `[CORE]` Customer database pooled from online orders, Captain app, website and in-house; behaviour tracking (sales, purchase history, notes); 100+ customer label types for marketing, feedback campaigns, group/corporate discounts; free unlimited data export; edit customer record for special discount/points; promotional-message control/opt-out; loyalty points awarded at billing; special-day SMS; 7+ campaign types (unnamed) — [CRM page](https://www.petpooja.com/poss/restaurant-customer-management-software)
- `[CORE]` One profile per customer across channels; Labels and Segments; three-step campaign builder (channel → segment → campaign) with default "All Users" segment; SMS marketing on builds that include it (birthdays, anniversaries) — [Petpooja blog: 200+ tools](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/)
- `[ADD-ON]` Loyalty Wallet: pre-defined loyalty/cashback points; time-regulated reward campaigns; point allocation and expiry; points on every POS bill incl. advance payments; wallet top-up by cash/card/UPI; OTP-verified redemption via POS; virtual cards; single dashboard of wallets; blacklist/block a customer's balance; SMS on credit — [Loyalty page](https://www.petpooja.com/poss/restaurant-loyalty-program)
- `[ADD-ON]` SMS marketing: personalised SMS for offers, menu updates, occasions from dashboard — [Marketplace page](https://www.petpooja.com/poss/restaurant-app-marketplace)
- `[ADD-ON]` Customer Feedback: Android feedback app, SMS links (unlimited), QR on tables/counters/printed on bill, feedback on 3P online orders, feedback without an order, custom questions and categorised messages, collects birthdays/anniversaries, dine-in/takeaway/delivery, negative-feedback notification to biller on POS — [Feedback page](https://www.petpooja.com/poss/customer-feedback-management)
- `[ADD-ON]` Business Website ("My Website"/OOW): brand site taking orders straight into POS, no aggregator commission, own gateway — [Marketplace page](https://www.petpooja.com/poss/restaurant-app-marketplace); [Online ordering page](https://www.petpooja.com/poss/online-order-management-software)
- `[ADD-ON]` Table Reservation Manager: multi-channel inbox (Zomato Dining, District, EazyDiner, own link, calls, walk-ins), auto cancellation alerts, party-size table assignment, live colour-coded floor view synced to POSS, queue/waitlist with pre-seating orders to KOT, shareable booking link (Instagram/WhatsApp/website) with optional refundable deposit per cover and auto-refunds, automated reminders, guest CRM profiles by phone with filters, WhatsApp post-visit rating requests, reservation calendar, daily reports (no-show rate, channel revenue), custom event forms, inquiry tracking, role-based users, offline mode; Windows/Android/Mac/web — [Reservation page](https://www.petpooja.com/poss/table-reservation-manager)
- Marketing Manager tiers: CRM/loyalty in Core ₹20k; website in Growth ₹30k; WhatsApp credits 4,000/8,000/10,000 — [DineOpen pricing](https://www.dineopen.com/blog/petpooja-pricing-plans-2026.html)
- Techjockey: in-built CRM with order history and reviews; loyalty program; schemes and offers; SMS and email integration — [Techjockey](https://techjockey.com/detail/petpooja-pos)
- Co-founder interview: owners approve AI-generated marketing campaigns over WhatsApp `[UNCERTAIN: podcast, secondary]` — [Analytics Insight](https://www.analyticsinsight.net/podcast/parthiv-patel-on-how-ai-is-transforming-indias-restaurant-industry)
- `[3P]` Loyalty/CRM partners named in directories: Reelo (SoftwareSuggest integrations list) — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja)

### Inferences
- Coupons are implemented as discounts/offers/schemes rather than a named coupon-code engine; no evidence of a customer-facing loyalty app (virtual cards + SMS/OTP instead).

### Gaps
- Names of the "7+ campaign types"; WhatsApp campaign UI specifics; Google-review redirect in feedback not found.

---

## 6. Kitchen (KDS, token display, order tracking)

### Takeaway
KDS (add-on, Android/Windows) shows per-ticket and aggregated item views, station-wise screens, mark-ready and mark-out-of-stock, for both dine-in and online orders; a separate Token Management Android-TV app shows pickup tokens with voice alerts; a Digital Display System add-on turns Android TVs into menu boards; KOT module has food-ready reminders and station-printed tokens.

### Cited Findings
- `[ADD-ON]` KDS: individual KOTs + aggregated item list; mark food ready; mark items out-of-stock (visible to captains/billers); station assignment with per-station running orders or one central screen; any Windows or Android device; multi-device sync with POS; shows online + dine-in orders; replaces paper KOT; "offline architecture" in image captions — [KDS page](https://www.petpooja.com/poss/kitchen-display-system)
- KOT module: Food Ready Reminder (flags unfinished orders past set time); food-ready tokens print at a named station — [Petpooja blog: 200+ tools](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/)
- `[ADD-ON]` Token Management (see §4) — [Token page](https://www.petpooja.com/poss/online-order-token-management)
- `[ADD-ON]` Digital Display System: add-on rotation, offer graphics, one-tap "today's special" pushed to all screens, full menu playback with photos/video loops, multiple screens each with own playlist/timing, plug-and-play via QR from Merchant app, remote price/sold-out/combo updates, managed from POS dashboard, offline continuity; Android TV 7.1.1+, 32"+ recommended — [Digital display page](https://www.petpooja.com/poss/digital-display-system)
- `[ADD-ON]` Wireless Calling Device: table button to call waiter/water/bill (hardware; AMC in Local Scale) — [Marketplace page](https://www.petpooja.com/poss/restaurant-app-marketplace); [SoftwareSuggest](https://www.softwaresuggest.com/petpooja)
- Techjockey: "food BOTs" and waiter-calling devices via marketplace — [Techjockey](https://techjockey.com/detail/petpooja-pos)

### Gaps
- No documented KDS timers/colour-coded ageing, course firing, or bump-bar hardware support.

---

## 7. Reports & analytics (incl. owner app, dashboards, AI)

### Takeaway
94+ named reports in 8 groups (80–100+ depending on page), including day-end, sales, item/category, tax/GST, bill-modification, discount/cancellation, cash-drawer, staff, online-order/commission, inventory consumption and recipe-cost reports; head-office multi-outlet dashboard grouped by zone/city/brand; automated emailed report alerts; Dynamic Reports (customisable dashboards, Excel import) is an add-on; new in Oct 2026 is the "Ask Me Anything" natural-language AI assistant in the dashboard plus an "AI Restaurant Report: Day Wise".

### Cited Findings
- `[CORE]` Single dashboard; tax reports for single/chain outlets; bill-modification, discounted/cancelled-order, cash-drawer-operation reports; head-office module (all outlets, grouped by city/zone); sales, item-wise consumption, online-order, staff-scheduling reports; everyday payment-status tracking; outlet-wise report rights; day-end reports in "5 min"; aggregator commission reports; recipe cost and raw-material price trend reports; automated report alerts by email; "50+" free reports — [Reports page](https://www.petpooja.com/poss/reports-and-analytics)
- 94-report catalogue in 8 groups (orders, items, categories, customers, discounts…); Dynamic Reports live dashboards (not on Local); "AI Restaurant Report: Day Wise"; Ask Me Anything in Dashboard module; inventory dashboard with stock-closing tracker and COGS chart — [Petpooja blog: 200+ tools](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/)
- "Ask Me Anything" launched Oct 2026 inside the POS dashboard: plain-language questions ("sales last month", "top-selling items yesterday", "yesterday's sales by hour", "item-wise P&L last week") answered from billing, orders, inventory and sales data — [Free Press Journal](https://www.freepressjournal.in/focused-view/no-reports-to-learn-petpoojas-ask-me-anything-answers-restaurant-questions-in-plain-language); vendor post — [Petpooja blog: AMA](https://blog.petpooja.com/operations-workflows/restaurant-ai-assistant-ask-me-anything/)
- `[ADD-ON]` Dynamic Reports: customisable formats, Excel import, downloads, graphical dashboard, unlimited users with owner-managed report rights, data back "decades"; marketplace cites 40+ reports — [Dynamic reports page](https://www.petpooja.com/poss/restaurant-analytics-insights); [Marketplace page](https://www.petpooja.com/poss/restaurant-app-marketplace)
- Owner app: Petpooja Merchant App (iOS/Android) — real-time outlet stats, sales, revenue, critical-event alerts — [App Store Merchant App](https://apps.apple.com/app/id1362012013); Android package com.petpooja.billing — [Google Play](https://play.google.com/store/apps/details?id=com.petpooja.billing&hl=en_IN) `[UNCERTAIN: listing text not retrievable]`
- Finance dashboard: payment mix (card/UPI/wallet/cash/online), distribution chart, monthly trends — [Petpooja Finance blog](https://blog.petpooja.com/industry-business-guides/petpooja-finance-money-layer-in-pos/)
- Techjockey: 80+ reports, item/category-wise, GST reporting, inventory, dynamic (Scale), chain-management reports; "reporting feature for fee calculation of your franchise" — [Techjockey](https://techjockey.com/detail/petpooja-pos)
- UAE: 90+ sales/cash/stock reports; AI assistant answering from outlet data — [Petpooja UAE](https://www.petpooja.com/ae/poss)

### Gaps
- WhatsApp-scheduled reports not confirmed (only email). The full list of 94 report names not retrieved.

---

## 8. Payments

### Takeaway
"Petpooja Finance" (2026) is the money layer: Pay+ integrated EDC/QR via partners Paytm, Razorpay, Pine Labs, Mosambee, BharatPe routed through a cloud ("Finance Cloud") so EDCs need only internet; soundbox voice confirmation; static-QR voice alerts; auto-settlement that frees tables; payout reconciliation incl. Swiggy/Zomato/ONDC; HDFC current-account application; "Petpooja Loans" working-capital placement (HDFC loan journey on roadmap). Captain app and kiosks take UPI, wallets, contactless cards; Scan & Pay add-on for pay-at-table.

### Cited Findings
- Petpooja Finance (3 Jul 2026): card/UPI/QR through connected EDC and QR devices; Pay+ routes through Finance Cloud (EDC needs only internet, not LAN with billing PC); soundbox announces integrated QR payments; static-QR voice alerts in English/Hindi; partners Paytm, Razorpay, Pine Labs, Mosambee, BharatPe ("more onboarding", Pay+ still rolling out); card vs UPI/Bharat QR split with provider shown; reconciliation vs provider payouts, flags missing invoices, provider charges next to payout; payment-mix dashboard; covers Swiggy/Zomato/ONDC; auto-settlement closes order and frees table; "Petpooja Loans" working-capital option shown across POSS; HDFC business-loan journey on roadmap (not live); HDFC current-account application via Finance Marketplace; no MDR figures — [Petpooja Finance blog](https://blog.petpooja.com/industry-business-guides/petpooja-finance-money-layer-in-pos/)
- Soundbox blog: voice confirmation for integrated QR; voice alerts for static QR in English/Hindi — [Soundbox blog](https://blog.petpooja.com/industry-business-guides/payment-soundbox-restaurants-cut-billing-mistakes/)
- "Petpooja Pay" and "Scan & Pay" listed as Operations / Customer-service add-ons on billing page — [Billing page](https://www.petpooja.com/poss/restaurant-billing-software); dynamic payment QR printed on bill — same page
- Captain app: UPI, wallets, single-tap contactless card under ₹5,000; settle by cash or QR — [Captain page](https://www.petpooja.com/poss/captain-ordering-app)
- Kiosk: UPI/UPI QR, debit/credit, pay-at-counter — [Kiosk page](https://www.petpooja.com/poss/self-service-kiosk)
- Partner-sold financial products: soundbox, EDC integrations, business current accounts, health insurance `[UNCERTAIN: employee LinkedIn post]` — [LinkedIn](https://www.linkedin.com/in/jatin-shah-04b4075b/)
- Older (2022) collaboration list included Paytm payment devices — [BW Disrupt](https://www.bwdisrupt.com/article/restaurant-software-provider-petpooja-expands-collaborates-with-ondc-439890)
- Directory-listed payment integrations: Razorpay, Pine Labs, Google Pay, Paytm, UrbanPiper, Sunmi — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja); [Capterra](https://www.capterra.com/p/172163/Petpooja-Restaurant-Management-Platform/)

### Inferences
- Petpooja is not itself a payment aggregator; it orchestrates partner EDC/QR and layers reconciliation + lending referrals on top (closer to "payments marketplace" than "Petpooja Pay gateway").

### Gaps
- Pay+ pricing/MDR, which devices are Petpooja-branded vs partner-branded, and whether "Petpooja Loans" is live with a named NBFC are unconfirmed (page /poss/petpooja-pay and /poss/scan-and-pay returned 404).

---

## 9. Add-ons / marketplace (Petpooja-built) and third-party integrations

### Takeaway
The marketplace page lists 15 Petpooja-built add-ons (FAQ says "11 exclusive services") in four buckets — Customer Service, Operations, CRM, Analytics — and claims 150+ (elsewhere 70+/120+/200+) third-party integrations, but Petpooja does not publish the partner list; named partners across sources total roughly 35.

### Cited Findings
**Petpooja-built add-ons (all `[ADD-ON]` unless noted)** — [Marketplace page](https://www.petpooja.com/poss/restaurant-app-marketplace); [POSS page](https://www.petpooja.com/poss); [Billing page](https://www.petpooja.com/poss/restaurant-billing-software)
- Customer Service: Wireless Calling Device (table call button); Self-Service Kiosk (touch + voice-enabled ordering); Scan & Order (per-table QR ordering); Purchase Manager (free; vendor price compare + ordering + inventory sync); Digital Display System (Android-TV menu boards); Scan & Pay (QR pay-at-table).
- Operations: Captain App (Android/iPad table ordering with AI upsell, offline, payments); Kitchen Display System; Token Management (Android TV pickup display); Table Reservation Manager; Petpooja Pay (payments).
- CRM: Business Website / My Website (commission-free ordering site); Loyalty Wallet; SMS Marketing; Customer Feedback (app/SMS/QR).
- Analytics: Online Order Reconciliation (Zomato/Swiggy payouts); Dynamic Reports (40+ custom reports/dashboards).
- Also listed as plan features: Call Centre Module; Central Kitchen Module; Head-office module; API access (Scale/Android plans); Tally and SAP/ERP integration (Scale) — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja)
- Captain app detail: multi-device sync; AI recommendation engine for upsell; offline; UPI/wallets; contactless card <₹5,000; any Android phone/tablet; captain-to-table/area assignment via POS; AI voice recognition to add items; works with Electron and Local only (not Lite/Android basic) — [Captain page](https://www.petpooja.com/poss/captain-ordering-app); iOS/iPadOS/macOS/visionOS build v15.1.0 — [App Store Captain](https://apps.apple.com/app/id6470435905); AI upsell toggled per outlet/chain from dashboard — [Petpooja blog: Captain upsell](https://blog.petpooja.com/industry-business-guides/petpooja-captain-ordering-reduces-order-errors/)
- Scan & Order detail: unique QR per table from Menu module; browser-based, no app; hide sold-out items; captain OTP-validates guest order before KOT fires; real-time POSS sync; multiple rounds on same table bill, per-guest ordering; pay at counter or online; toggle on/off from dashboard; needs internet both sides — [Scan & Order page](https://www.petpooja.com/poss/scan-and-order)
- Kiosk detail: cashier-less ordering with KOT print; photo-forward multi-language menu; upsell prompts (claims +28% AOV); parallel kiosks; UPI/cards/pay-at-counter; wall-mount or floor-mount steel cabinet, 22"/27"/32", WiFi+Bluetooth, built-in thermal printer, 1-yr onsite warranty; hardware partners Addsoft Technologies and Posbank; software pre-installed; offline; multi-brand routing in food courts — [Kiosk page](https://www.petpooja.com/poss/self-service-kiosk)

**Third-party integrations (`[3P]`) — names found, by category (no official list published):**
- Food aggregators (India): Zomato, Swiggy, Dineout — [Online ordering page](https://www.petpooja.com/poss/online-order-management-software); Uber Eats, Dunzo — [Techjockey](https://techjockey.com/detail/petpooja-pos); ONDC — [Petpooja ONDC](https://www.petpooja.com/ondc); UrbanPiper (middleware) — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja)
- Aggregators (UAE): Talabat, Deliveroo, Careem, Noon — [Petpooja UAE](https://www.petpooja.com/ae/poss)
- Rider/dispatch: Dunzo, Shadowfax, Pidge — [Online ordering page](https://www.petpooja.com/poss/online-order-management-software); Hyperzod, Pidge — GetApp via [search summary](https://www.getapp.com/all-software/a/petpooja/integrations/) `[UNCERTAIN: page 403]`; Tookan (Jungleworks) — [Jungleworks](https://jungleworks.com/integrate-your-petpooja-account-with-tookan-for-smart-delivery-management)
- D2C storefront / WhatsApp: Yelo (Jungleworks) — [Jungleworks help](https://help.jungleworks.com/yelo/petpooja-integration/); Edesy — [Edesy](https://edesy.in/restaurant-order-bot/integrations/petpooja); Gallabox — [Gallabox](https://docs.gallabox.com/bots/bot-connectors/send-your-whatsapp-data-to-petpooja-using-chatbot); OwnChat — [OwnChat](https://ownchat.app/blog/petpooja-whatsapp-marketing-with-ownchat); DotPe and "Menu QR Code" appear in marketplace screenshots — [search summary of marketplace](https://www.petpooja.com/poss/restaurant-app-marketplace) `[UNCERTAIN]`
- Reservations: Zomato Dining, District, EazyDiner — [Reservation page](https://www.petpooja.com/poss/table-reservation-manager)
- Payments: Paytm, Razorpay, Pine Labs, Mosambee, BharatPe — [Petpooja Finance blog](https://blog.petpooja.com/industry-business-guides/petpooja-finance-money-layer-in-pos/); Google Pay — Capterra via search; Sunmi (hardware/payment terminals) — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja)
- Accounting/ERP: Tally (daily sales, GST, expenses) — [Integrations page](https://www.petpooja.com/poss/restaurant-integrations); Zoho Books, BUSY Accounting, Masters India (GST/e-invoice), SAP — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja); Dynamics NAV, SAP, Tally via "data lake" — [Large chain page](https://www.petpooja.com/poss/large-chain-restaurant-pos-software); ERPNext (community app) — [Frappe](https://cloud.frappe.io/marketplace/apps/petpooja)
- Loyalty/CRM: Reelo — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja); Cxverse — [Partnerbase](https://www.partnerbase.com/petpooja)
- Supply: SupplyNote (GetApp user-rated) `[UNCERTAIN]` — [GetApp](https://www.getapp.com/all-software/a/petpooja/); HyperPure, DMart (Purchase Manager vendors) — [Purchase Manager page](https://www.petpooja.com/poss/purchase-manager)
- Automation/data: Zapier, Google Sheets `[UNCERTAIN: Goodcall]` — [Goodcall](https://www.goodcall.com/business-productivity-ai/petpooja)
- Messaging/telephony (2022 plans): Gupshup, Knowlarity, WhatsApp — [BW Disrupt](https://www.bwdisrupt.com/article/restaurant-software-provider-petpooja-expands-collaborates-with-ondc-439890) `[UNCERTAIN: old]`
- Counts conflict: 150+ (marketplace/POSS pages), 70+ integrations & 120+ marketplace services (blog), 200+ (integrations page headline, Techjockey, GetApp), 75+ (Elioplus), 15+ (UAE) — [Marketplace page](https://www.petpooja.com/poss/restaurant-app-marketplace); [Petpooja blog](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/); [Integrations page](https://www.petpooja.com/poss/restaurant-integrations)
- Note: a Constacloud "Pet Pooja integration list" page is that vendor's own connector catalog (Shopify, SAP, QuickBooks…), not Petpooja partners — [Constacloud](https://constacloud.com/commercium/pos/pet-pooja-pos-integration.html)

### Inferences
- Growth tier = "pick any 5" of the marketplace pool; Scale = everything, which means a clone's marketplace needs entitlement logic per outlet.

### Gaps
- The complete official partner directory (said to be reachable inside POSS) was not retrievable; Porter, Shadowfax (official), Zoho (official) and most HR/accounting partners are unconfirmed.

---

## 10. Hardware sold

### Takeaway
Petpooja sells/bundles hardware through partners rather than own-brand devices: Android POS terminals/handhelds (e.g., Sunmi), receipt/label printers, KDS screens, Android-TV token/menu displays, self-ordering kiosks (Addsoft, Posbank), wireless calling devices, soundboxes, EDCs via payment partners, biometric devices (Attendo), smart weighing scales; no public price list.

### Cited Findings
- POS runs on iOS/Windows/Android laptops, PCs, tablets, phones; A4 + thermal printers over WiFi/LAN/USB/Bluetooth; label printers — [Pricing page](https://www.petpooja.com/poss/pricing)
- 200+ compatible weighing scales, printers, barcode scanners; smart scale; kiosks; KDS screens; delivery dispatch devices; food BOTs; waiter-calling devices; hardware sold separately — [Techjockey](https://techjockey.com/detail/petpooja-pos)
- Kiosk hardware specs and partners Addsoft Technologies, Posbank — [Kiosk page](https://www.petpooja.com/poss/self-service-kiosk)
- KDS on any Windows/Android device; token and digital display on Android TV (7.1.1+, 32"+) — [KDS page](https://www.petpooja.com/poss/kitchen-display-system); [Digital display page](https://www.petpooja.com/poss/digital-display-system)
- Waiter calling device sold with AMC (Local Scale) — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja)
- UAE: Android POS terminals, tablets, receipt printers, KDS screens "sourced through partners" — [Petpooja UAE](https://www.petpooja.com/ae/poss)
- Biometric attendance hardware bundled with Attendo — [Petpooja home](https://www.petpooja.com/)
- Reseller indicative prices (not official): Sunmi V2s Pro ₹19,990, D2 Mini ₹25,500, V3 Mix Plus ₹28,500; Petpooja software ₹11,000/yr — [IndiaMART reseller](https://m.indiamart.com/spok-technocom/pos-software.html) `[UNCERTAIN]`

### Gaps
- No Petpooja hardware catalogue or price list found online.

---

## 11. Newer features 2024–2026 (AI, side products, franchise, cloud kitchen, supply, fintech, HR)

### Takeaway
2025–26 additions: Ask Me Anything AI assistant (Oct 2026), AI Inventory Agent, AI day-wise report, Captain AI upsell + voice entry, Purchase Manager (free AI price-comparison procurement), Petpooja Purchase (OCR accounts-payable with Tally sync, Purchase Scan app), Petpooja Finance/Pay+ with soundbox and lending/current-account marketplace (Jul 2026), Table Reservation Manager, Digital Display System, and rebranded side products Attendo (payroll/attendance) and Stepwise (AI-verified task/SOP management); plus a Franchise Conclave event (Jun 2026) but no dedicated franchise/royalty module.

### Cited Findings
- AI: Ask Me Anything (Oct 2026) — [Free Press Journal](https://www.freepressjournal.in/focused-view/no-reports-to-learn-petpoojas-ask-me-anything-answers-restaurant-questions-in-plain-language); AI Inventory Agent, AI Restaurant Report Day Wise, AI upsell in Captain app, Purchase Manager AI price compare — [Petpooja blog: 200+ tools](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/); Captain AI voice recognition — [Captain page](https://www.petpooja.com/poss/captain-ordering-app); Series C earmarked for "AI-driven automation" — [Entrackr](https://entrackr.com/news/petpooja-raises-155-mn-series-c-at-over-3x-valuation-premium-10512396)
- `[SIDE-PRODUCT]` Petpooja Purchase (accounts payable): mobile photo/PDF invoice OCR incl. handwritten and multi-page; reviewed data pushed to Tally (purchase entries, ledgers, inventory); syncs with POSS and Petpooja Invoice; "Purchase Scan" iPad app for automated ERP entries and vendor payouts; ~₹6,000/yr excl. GST (listing) — [Petpooja blog: Purchase](https://blog.petpooja.com/core-product/purchase/); [Purchase Scan App Store](https://apps.apple.com/us/app/-/id6740403231); [amd.petpooja.com/Purchase](https://amd.petpooja.com/Purchase) `[UNCERTAIN: price from listing]`
- `[SIDE-PRODUCT]` Petpooja Invoice (retail/B2B GST billing): CGST/SGST/IGST auto, GST reports, e-invoice + e-way bill from billing screen, credit notes with IRN, inventory, P&L, payment-mode-to-bank mapping; ₹8,500+GST/yr (blog) vs ₹5,000 (Techjockey) — [Petpooja Invoice](https://www.petpooja.com/invoice); [Petpooja blog: Invoice features](https://blog.petpooja.com/finance-compliance/petpooja-invoice-features/); AI virtual try-on for apparel stores — [ThePrint](https://theprint.in/brandit/petpooja-invoices-ai-try-on-gives-small-apparel-stores-a-trial-room-that-never-has-a-queue/3085288/)
- `[SIDE-PRODUCT]` Attendo (ex-Petpooja Payroll): punch-in, shift scheduling, multi-shift payroll, leave; Employee app in 11 languages (Apr 2026), force-logout, bulk holidays; ₹8,000–9,000/yr — [Petpooja blog: Payroll 2026](https://blog.petpooja.com/people-payroll/petpooja-payroll-features-updates/); [Attendo](https://attendohr.com/)
- `[SIDE-PRODUCT]` Stepwise (ex-Petpooja Tasks): task assignment/verification, AI photo/video proof verification, geofencing, 150+ templates, WhatsApp reminders, unlimited branches/users (Apr–May 2026) — [Petpooja blog: Tasks](https://blog.petpooja.com/operations-workflows/petpooja-tasks-features/); [Stepwise](https://www.gostepwise.ai/)
- Fintech: Petpooja Finance/Pay+, soundbox, Petpooja Loans, HDFC current account, HDFC loan journey on roadmap (Jul 2026) — [Petpooja Finance blog](https://blog.petpooja.com/industry-business-guides/petpooja-finance-money-layer-in-pos/)
- Supply: Purchase Manager with HyperPure/DMart (free) — [Purchase Manager page](https://www.petpooja.com/poss/purchase-manager)
- Franchise: Franchise Conclave 2026 (Ahmedabad, 20–21 Jun 2026, 50+ brands) — an event, not software — [ANI](https://www.aninews.in/news/business/petpooja-brings-franchise-conclave-2026-to-ahmedabad-creating-a-new-growth-platform-for-indias-fampb-industry20260618174038/); franchise handled via owner dashboard access control, zone grouping, head office, central kitchen, PO management, dynamic reports — [Petpooja blog: large chain](https://blog.petpooja.com/petpooja-pos-features-that-simplify-large-chain-management/); Jumboking franchise case study — [Petpooja blog: Jumboking](https://blog.petpooja.com/growth-scaling/petpooja-streamlining-jumbokings-restaurant-franchise-operations/)
- Cloud kitchen: virtual brand tabs, multi-channel screen, CK, KDS, reconciliation — [Cloud kitchen page](https://www.petpooja.com/poss/cloud-kitchen-pos-software)
- Staff hiring: no Petpooja hiring product found (Attendo/Stepwise cover HR ops only).
- "Petpooja Studio" named in Techjockey "other products" — [Techjockey](https://techjockey.com/detail/petpooja-pos) — but no corroboration anywhere `[UNCERTAIN/likely stale]`.

### Gaps
- No "Petpooja Food Sense/insights" product found under that name; no royalty/franchise-fee engine documented (one third-party line only); no staff-hiring marketplace found.

---

## 12. Platforms, API, international

### Takeaway
POSS ships as Electron (cross-platform desktop: Windows/macOS/Linux), Local (on-device Windows), Android POS, and Lite; mobile apps on Android and iOS (Merchant, Captain, Tasks, Attendo, Purchase Scan, Stepwise); Android-TV apps for token/display; web owner dashboard. A partner Online-Ordering API (menu/orders/stock/callbacks + webhooks) exists but keys are issued by support; API access is a Scale/Android plan line item. Active markets: India, UAE (AED 1,500/outlet/yr), South Africa; regional sites for SG, MY, TH, US, CA.

### Cited Findings
- Builds Electron, Local, Android, Lite with capability matrix; 4 desktop + 11 mobile apps — [Petpooja blog: 200+ tools](https://blog.petpooja.com/operations-workflows/must-try-features-petpooja-pos/)
- OS: Windows, iOS, Android, macOS (+Linux per FAQ); legacy Adobe AIR desktop — [Techjockey](https://techjockey.com/detail/petpooja-pos); iOS/Windows/Android — [Pricing page](https://www.petpooja.com/poss/pricing)
- API included in Scale and Android plans — [SoftwareSuggest](https://www.softwaresuggest.com/petpooja); partner Online Ordering API (Orders/Stores/Stock/Callbacks) — [API Evangelist](https://github.com/api-evangelist/petpooja); webhooks to ERPNext — [Frappe](https://cloud.frappe.io/marketplace/apps/petpooja); credentials from support — [Jungleworks](https://help.jungleworks.com/yelo/petpooja-integration/)
- UAE: from AED 1,500/outlet/yr, VAT/FTA-ready, Talabat/Deliveroo/Careem/Noon, support in English/Hindi/Arabic/Malayalam, go-live 3–5 days — [Petpooja UAE](https://www.petpooja.com/ae/poss)
- Operates in India, UAE, South Africa — [Entrackr](https://entrackr.com/news/petpooja-raises-155-mn-series-c-at-over-3x-valuation-premium-10512396); regional pages for SG/MY/TH/ZA/US/CA — [POSS page](https://www.petpooja.com/poss)
- Security/compliance portal trust.petpooja.com — [Petpooja home](https://www.petpooja.com/)

### Gaps
- No public developer portal; API scope beyond online-ordering (e.g., reports/CRM read APIs) undocumented. Depth of SG/MY/TH/US/CA operations unknown (pages exist; no customer counts).
