import { useState } from 'react';
import { ChevronDown, Loader2 } from 'lucide-react';
import { formatSessionTimeLabel } from '../../lib/tailor/utils';
import type { ResumeSessionListItem } from '../../lib/tailor/types';

interface Props {
  sessions: ResumeSessionListItem[];
  activeResumeId: string;
  onSelectSession: (resumeId: string) => void;
  loading: boolean;
  onRefresh: () => void;
}

export function SessionListPanel({
  sessions,
  activeResumeId,
  onSelectSession,
  loading,
  onRefresh,
}: Props) {
  const [open, setOpen] = useState(false);
  const active = sessions.find((s) => s.resumeId === activeResumeId);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => { setOpen(!open); if (!open) onRefresh(); }}
        className="flex items-center gap-2 border border-black dark:border-zinc-600 bg-white dark:bg-zinc-800 dark:text-zinc-100 px-3 py-1.5 font-mono text-[11px] hover:bg-gray-50 dark:hover:bg-zinc-700"
      >
        {loading ? <Loader2 className="size-3 animate-spin" /> : null}
        <span className="max-w-[140px] truncate">{active?.title || 'Select resume'}</span>
        <ChevronDown className={`size-3 transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full z-20 mt-1 w-72 border-2 border-black dark:border-zinc-600 bg-white dark:bg-zinc-900 shadow-[4px_4px_0px_0px_#000000] dark:shadow-none">
            <div className="max-h-56 overflow-auto">
              {sessions.length === 0 ? (
                <p className="px-3 py-4 font-mono text-xs text-gray-500 dark:text-zinc-400">No sessions</p>
              ) : (
                sessions.map((item) => {
                  const isActive = item.resumeId === activeResumeId;
                  return (
                    <button
                      key={item.resumeId}
                      type="button"
                      onClick={() => {
                        if (item.resumeId !== activeResumeId) onSelectSession(item.resumeId);
                        setOpen(false);
                      }}
                      className={`flex w-full items-center justify-between border-b px-3 py-2 text-left last:border-b-0 ${
                        isActive ? 'bg-gray-100 dark:bg-zinc-800' : 'hover:bg-gray-50 dark:hover:bg-zinc-700'
                      }`}
                    >
                      <div className="min-w-0">
                        <p className="truncate font-mono text-xs">{item.title}</p>
                        <p className="font-mono text-[10px] text-gray-500 dark:text-zinc-400">
                          {formatSessionTimeLabel(item.updatedAt)}
                          {item.hasDraft ? ' · Draft' : ''}
                        </p>
                      </div>
                      {isActive && (
                        <span className="ml-2 shrink-0 font-mono text-[10px] text-emerald-700 dark:text-emerald-400">Active</span>
                      )}
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
