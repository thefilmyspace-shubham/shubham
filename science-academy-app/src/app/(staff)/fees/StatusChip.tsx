import { FEE_STATUS_LABEL, type FeeStatus } from "@/lib/fees";
import { Chip, type Tone } from "@/components/ui";

export const FEE_STATUS_TONE: Record<FeeStatus, Tone> = {
  paid: "ok",
  partial: "warn",
  pending: "navy",
  overdue: "danger",
};

export function FeeStatusChip({ status }: { status: FeeStatus }) {
  return <Chip tone={FEE_STATUS_TONE[status]}>{FEE_STATUS_LABEL[status]}</Chip>;
}
