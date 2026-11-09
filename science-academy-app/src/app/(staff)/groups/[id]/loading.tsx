export default function Loading() {
  return (
    <div className="mx-auto max-w-4xl space-y-2 px-4 pt-6 lg:px-8">
      <div className="h-8 w-56 animate-shimmer rounded-field bg-line" />
      <div className="h-[60vh] animate-shimmer rounded-card bg-chat" />
    </div>
  );
}
