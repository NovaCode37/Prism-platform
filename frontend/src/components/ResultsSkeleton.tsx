'use client';

export function ResultsSkeleton() {
  return (
    <div className="flex flex-col h-[calc(100vh-48px)] animate-fade-in">
      <div className="px-4 sm:px-5 py-3 border-b border-border-1 bg-surface-1">
        <div className="flex items-center gap-3">
          <div className="h-5 w-40 bg-surface-3 rounded animate-pulse" />
          <div className="h-5 w-16 bg-surface-3 rounded animate-pulse" />
        </div>
        <div className="flex items-center gap-2 mt-2">
          <div className="h-4 w-12 bg-surface-3 rounded animate-pulse" />
          <div className="h-4 w-32 bg-surface-3 rounded animate-pulse" />
        </div>
      </div>

      <div className="px-4 sm:px-5 py-2.5 bg-surface-2 border-b border-border-1 flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 bg-surface-3 rounded animate-pulse" />
          <div className="space-y-1">
            <div className="h-3 w-20 bg-surface-3 rounded animate-pulse" />
            <div className="h-3 w-16 bg-surface-3 rounded animate-pulse" />
          </div>
        </div>
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="hidden sm:flex items-center gap-2">
            <div className="h-3 w-16 bg-surface-3 rounded animate-pulse" />
            <div className="w-20 h-1.5 bg-surface-3 rounded-full animate-pulse" />
          </div>
        ))}
      </div>

      <div className="border-b border-border-1 bg-surface-1 flex gap-1 px-2 py-1">
        {[1, 2, 3, 4, 5, 6, 7].map(i => (
          <div key={i} className="h-8 w-20 bg-surface-3 rounded animate-pulse" />
        ))}
      </div>

      <div className="flex-1 p-5 space-y-3">
        {[1, 2, 3].map(i => (
          <div key={i} className="card">
            <div className="card-head">
              <div className="h-4 w-32 bg-surface-3 rounded animate-pulse" />
            </div>
            <div className="p-4 space-y-3">
              {[1, 2, 3, 4].map(j => (
                <div key={j} className="flex justify-between">
                  <div className="h-3 bg-surface-3 rounded animate-pulse" style={{ width: `${30 + Math.random() * 30}%` }} />
                  <div className="h-3 bg-surface-3 rounded animate-pulse" style={{ width: `${15 + Math.random() * 20}%` }} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
