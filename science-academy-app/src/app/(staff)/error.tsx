"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-3 px-6 pt-24 text-center">
      <h1 className="text-lg font-extrabold text-navy">Something went wrong</h1>
      <p className="text-sm text-muted">Please try again. If it keeps happening, tell the admin.</p>
      <button onClick={reset} className="btn btn-primary mt-2">
        Try again
      </button>
    </div>
  );
}
