import Link from "next/link";
import { ShieldOff } from "lucide-react";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-3 px-6 pt-24 text-center">
      <ShieldOff size={36} className="text-faint" />
      <h1 className="text-lg font-extrabold text-navy">Not available</h1>
      <p className="text-sm text-muted">This page does not exist, or your login does not have access to it. Admin can change access.</p>
      <Link href="/" className="btn btn-primary mt-2">
        Go home
      </Link>
    </div>
  );
}
