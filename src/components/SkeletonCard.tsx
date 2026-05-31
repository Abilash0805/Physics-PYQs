export default function SkeletonCard() {
  return (
    <div className="rounded-xl border bg-white dark:bg-gray-900 shadow-sm overflow-hidden animate-pulse">
      <div className="h-0.5 bg-gray-200 dark:bg-gray-700 rounded-t-xl" />
      <div className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <div className="h-5 w-12 rounded-full bg-gray-200 dark:bg-gray-700" />
          <div className="h-5 w-16 rounded-full bg-gray-200 dark:bg-gray-700" />
          <div className="h-5 w-24 rounded-full bg-gray-200 dark:bg-gray-700" />
        </div>
        <div className="space-y-2 mb-4">
          <div className="h-4 w-full rounded bg-gray-200 dark:bg-gray-700" />
          <div className="h-4 w-4/5 rounded bg-gray-200 dark:bg-gray-700" />
          <div className="h-4 w-3/5 rounded bg-gray-200 dark:bg-gray-700" />
        </div>
        <div className="h-8 w-28 rounded-lg bg-gray-200 dark:bg-gray-700" />
      </div>
    </div>
  );
}
