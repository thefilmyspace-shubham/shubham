// Fees, billing and call log texts in English, Hindi (Devanagari) and Hinglish (Roman).
// Every key in `en` must be in `hi` and `hinglish` too (TypeScript checks it).

export const en = {
  "fees.status.paid": "Paid",
  "fees.status.partial": "Partial",
  "fees.status.pending": "Pending",
  "fees.status.overdue": "Overdue",
  "fees.plan.monthly": "Monthly",
  "fees.plan.one_time": "One time (full payment)",
  "fees.plan.installments": "Installments",
  "fees.plan.manual": "Manual schedule",
  "fees.mode.upi": "UPI",
  "fees.mode.bank": "Bank transfer",
  "fees.mode.cash": "Cash",
} satisfies Record<string, string>;

export const hi: Record<keyof typeof en, string> = {
  "fees.status.paid": "जमा",
  "fees.status.partial": "आंशिक",
  "fees.status.pending": "बाकी",
  "fees.status.overdue": "देरी",
  "fees.plan.monthly": "मासिक",
  "fees.plan.one_time": "एक बार (पूरी फीस)",
  "fees.plan.installments": "किस्तें",
  "fees.plan.manual": "अपनी सूची",
  "fees.mode.upi": "UPI",
  "fees.mode.bank": "बैंक ट्रांसफर",
  "fees.mode.cash": "नकद",
};

export const hinglish: Record<keyof typeof en, string> = {
  "fees.status.paid": "Paid",
  "fees.status.partial": "Thoda jama",
  "fees.status.pending": "Baaki",
  "fees.status.overdue": "Late",
  "fees.plan.monthly": "Har mahine",
  "fees.plan.one_time": "Ek baar (poori fees)",
  "fees.plan.installments": "Kishton mein",
  "fees.plan.manual": "Apni list",
  "fees.mode.upi": "UPI",
  "fees.mode.bank": "Bank transfer",
  "fees.mode.cash": "Cash",
};
