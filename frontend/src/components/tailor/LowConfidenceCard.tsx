import { useTranslation } from 'react-i18next';
import { Check, X } from 'lucide-react';
import type { LowConfidenceItem } from '../../types';

interface Props {
  items: LowConfidenceItem[];
  confirmedKeys: Set<string>;
  onToggleConfirm: (itemKey: string) => void;
  onDismiss: () => void;
}

export function LowConfidenceCard({ items, confirmedKeys, onToggleConfirm, onDismiss }: Props) {
  const { t } = useTranslation();
  const allConfirmed = items.every((item) => confirmedKeys.has(item.item_key));

  return (
    <div className="mx-4 border-2 border-black dark:border-zinc-600 bg-white dark:bg-zinc-900 shadow-[4px_4px_0px_0px_#000000] dark:shadow-none">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 border-b-2 border-black dark:border-zinc-600 bg-orange-100 dark:bg-orange-900/50 px-4 py-3">
        <div>
          <h3 className="font-serif text-base font-bold text-slate-900 dark:text-slate-100">{t('lowConfidence.title')}</h3>
          <p className="mt-0.5 font-sans text-[11px] text-slate-500 dark:text-slate-400">
            {t('lowConfidence.description')}
          </p>
        </div>
        <button onClick={onDismiss} className="shrink-0 p-1 text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300" title="关闭">
          <X size={16} />
        </button>
      </div>

      {/* Items */}
      <div className="divide-y divide-slate-100 dark:divide-slate-700">
        {items.map((item) => {
          const isConfirmed = confirmedKeys.has(item.item_key);
          const pct = Math.round((item.confidence ?? 0.5) * 100);
          const barColor = pct >= 60 ? 'bg-amber-400' : pct >= 40 ? 'bg-orange-400' : 'bg-red-400';

          return (
            <div
              key={item.item_key}
              className={`border-l-4 px-4 py-3 transition-colors ${
                isConfirmed ? 'border-l-green-500 dark:border-l-green-400 bg-green-50/50 dark:bg-green-900/30' : 'border-l-orange-400 dark:border-l-orange-500 bg-white dark:bg-zinc-900'
              }`}
            >
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={isConfirmed}
                  onChange={() => onToggleConfirm(item.item_key)}
                  className="mt-0.5 size-4 accent-green-600 dark:accent-green-400 shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <code className="font-mono text-[11px] font-bold text-slate-600 dark:text-slate-400">{item.path}</code>
                  <p className="mt-1 font-sans text-[12px] text-slate-700 dark:text-slate-300">{item.reason}</p>
                  <p className="mt-0.5 font-sans text-[11px] text-slate-400 dark:text-slate-500 truncate">{item.refined_text.slice(0, 100)}</p>
                  {item.confidence_reason ? (
                    <p className="mt-0.5 font-sans text-[11px] italic text-orange-600 dark:text-orange-400">{item.confidence_reason}</p>
                  ) : null}
                  <div className="mt-2 flex items-center gap-2">
                    <div className="h-1.5 w-20 rounded-full bg-slate-200 dark:bg-slate-700">
                      <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
                    </div>
                    <span className="font-mono text-[10px] text-slate-400 dark:text-slate-500">{pct}%</span>
                  </div>
                </div>
                {isConfirmed ? (
                  <span className="shrink-0 inline-flex items-center gap-1 font-mono text-[10px] font-bold text-green-600 dark:text-green-400">
                    <Check size={12} /> 已确认
                  </span>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      {/* Actions */}
      <div className="flex gap-2 border-t-2 border-black dark:border-zinc-600 px-4 py-3">
        <button
          type="button"
          onClick={onDismiss}
          disabled={!allConfirmed}
          className={`flex-1 px-4 py-2 font-sans text-[12px] font-bold border-2 border-black transition-colors ${
            allConfirmed
              ? 'bg-black dark:bg-zinc-600 text-white hover:bg-gray-800 dark:hover:bg-zinc-500'
              : 'bg-gray-200 dark:bg-zinc-700 text-gray-400 dark:text-zinc-500 cursor-not-allowed'
          }`}
        >
          {allConfirmed ? '已全部确认' : '请勾选确认所有修改项'}
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="px-4 py-2 font-sans text-[12px] font-bold border-2 border-black dark:border-zinc-600 bg-white dark:bg-zinc-800 dark:text-zinc-100 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors"
        >
          稍后确认
        </button>
      </div>
    </div>
  );
}
