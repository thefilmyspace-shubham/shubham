// Central access to configuration so a missing variable fails with a clear message.

function required(name: string, value: string | undefined): string {
  if (!value) throw new Error(`Missing environment variable ${name}. See .env.example.`);
  return value;
}

// NEXT_PUBLIC_* values must be read with literal property access so Next.js
// can inline them into the browser bundle.
export function supabaseUrl(): string {
  return required("NEXT_PUBLIC_SUPABASE_URL", process.env.NEXT_PUBLIC_SUPABASE_URL);
}

export function supabaseAnonKey(): string {
  return required("NEXT_PUBLIC_SUPABASE_ANON_KEY", process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
}

export function serviceRoleKey(): string {
  return required("SUPABASE_SERVICE_ROLE_KEY", process.env.SUPABASE_SERVICE_ROLE_KEY);
}

export function appUrl(): string {
  return (process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000").replace(/\/$/, "");
}

export function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

/** What is printed on every bill. Placeholders until the owner supplies the real details. */
export function academyDetails() {
  return {
    name: "Science Academy",
    tagline: "We believe in quality",
    city: "Ratlam, Madhya Pradesh",
    address: process.env.ACADEMY_ADDRESS || "[ADDRESS LINE]",
    phone: process.env.ACADEMY_PHONE || "[PHONE]",
    upiId: process.env.ACADEMY_UPI_ID || "[YOUR UPI ID]",
    bankName: process.env.ACADEMY_BANK_NAME || "[BANK NAME]",
    accountNumber: process.env.ACADEMY_ACCOUNT_NUMBER || "[ACCOUNT NUMBER]",
    ifsc: process.env.ACADEMY_IFSC || "[IFSC]",
    accountName: process.env.ACADEMY_ACCOUNT_NAME || "Science Academy",
  };
}

export type AcademyDetails = ReturnType<typeof academyDetails>;

/** True while the UPI ID is still the placeholder, so no payable QR code is printed. */
export function upiIsPlaceholder(upiId: string): boolean {
  return !/^[\w.-]+@[\w.-]+$/.test(upiId);
}
