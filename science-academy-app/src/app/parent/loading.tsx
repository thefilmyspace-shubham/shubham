export default function Loading() {
  return (
    <div className="mx-auto max-w-5xl space-y-3 px-4 pt-6 lg:px-8">
      <div className="h-8 w-48 animate-shimmer rounded-field bg-line" />
      <div className="h-24 animate-shimmer rounded-card bg-card" />
      <div className="h-40 animate-shimmer rounded-card bg-card" />
    </div>
  );
}
