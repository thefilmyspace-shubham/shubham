"use client";

import type { FeeStatus } from "@/lib/fees";
import { Chip, type Tone } from "@/components/ui";
import { useT } from "@/components/I18nProvider";

const FEE_STATUS_TONE: Record<FeeStatus, Tone> = {
  paid: "ok",
  partial: "warn",
  pending: "navy",
  overdue: "danger",
};

/** Paid / Partial / Pending / Overdue in the reader's language. */
export function FeeStatusChip({ status }: { status: FeeStatus }) {
  const t = useT();
  return <Chip tone={FEE_STATUS_TONE[status]}>{t(`fees.status.${status}`)}</Chip>;
}
