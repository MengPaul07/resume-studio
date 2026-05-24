interface Props {
  contentOverflows: boolean;
  totalPages: number;
  targetPages: number;
  suggestions: OverflowSuggestion[];
}

export interface OverflowSuggestion {
  label: string;
  action: () => void;
}

export function OverflowWarning({ contentOverflows, totalPages, targetPages, suggestions }: Props) {
  if (!contentOverflows) return null;

  return (
    <div className="border-2 border-amber-500 bg-amber-50 p-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-[14px]">&#9888;</span>
        <span className="font-mono text-[11px] font-bold uppercase tracking-wide text-amber-800">
          Content Exceeds {targetPages} Page{targetPages > 1 ? 's' : ''}
        </span>
        <span className="font-mono text-[10px] text-amber-600">
          ({totalPages} page{totalPages > 1 ? 's' : ''} detected)
        </span>
      </div>

      {suggestions.length > 0 && (
        <div className="space-y-1">
          <p className="font-mono text-[10px] uppercase text-amber-700">Quick Fixes:</p>
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((s) => (
              <button
                key={s.label}
                type="button"
                onClick={s.action}
                className="border border-amber-400 bg-white dark:bg-zinc-800 dark:text-zinc-100 px-2 py-0.5 font-mono text-[10px] text-amber-800 hover:bg-amber-100 dark:hover:bg-zinc-700"
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
