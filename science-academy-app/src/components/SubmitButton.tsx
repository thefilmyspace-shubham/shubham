"use client";

import { useFormStatus } from "react-dom";
import { LoaderCircle } from "lucide-react";

/**
 * A form's submit button that shows a spinner and cannot be pressed again
 * while the form is being saved (no double tests, bills or posts).
 */
export function SubmitButton({
  className,
  children,
  disabled,
  title,
}: {
  className?: string;
  children: React.ReactNode;
  disabled?: boolean;
  title?: string;
}) {
  const { pending } = useFormStatus();
  return (
    <button type="submit" className={className} disabled={disabled || pending} aria-busy={pending} title={title}>
      {pending && <LoaderCircle size={15} className="animate-spin" aria-hidden />}
      {children}
    </button>
  );
}
