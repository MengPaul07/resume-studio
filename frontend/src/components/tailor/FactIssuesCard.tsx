import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import { Button } from '../ui/button';

export type FactIssueItem = {
  path: string;
  reason: string;
  current_value: string;
  suggested_value: string;
  op: string;
  confirmation_hint: string;
};

export function FactIssuesCard({
  items,
  onSkip,
  onSubmit,
}: {
  items: FactIssueItem[];
  onSkip: () => void;
  onSubmit: (data: Record<string, string>) => void;
}) {
  const { t } = useTranslation();
  const [inputs, setInputs] = useState<Record<string, string>>({});

  useEffect(() => {
    const initial: Record<string, string> = {};
    for (const item of items) {
      initial[item.path] = item.suggested_value || '';
    }
    setInputs(initial);
  }, [items]);

  const handleSubmit = () => {
    const data: Record<string, string> = {};
    for (const item of items) {
      data[item.path] = (inputs[item.path] ?? item.suggested_value ?? '').trim();
    }
    onSubmit(data);
  };

  return (
    <div className="mx-4 border-2 border-black bg-white shadow-[4px_4px_0px_0px_#000000] dark:border-zinc-600 dark:bg-zinc-900 dark:shadow-none">
      <div className="flex items-start justify-between gap-2 border-b-2 border-black bg-amber-100 px-4 py-3">
        <div>
          <h3 className="font-serif text-base font-bold text-slate-900">{t('factIssues.title')}</h3>
          <p className="mt-0.5 font-sans text-[11px] text-slate-500">
            {t('factIssues.description')}
          </p>
        </div>
        <button type="button" onClick={onSkip} className="shrink-0 p-1 text-slate-400 hover:text-slate-700" title={t('common.skip')}>
          <X size={16} />
        </button>
      </div>

      <div className="max-h-[40vh] overflow-auto divide-y divide-slate-100">
        {items.map((item, index) => {
          const inputKey = `${item.path}::${index}`;
          const inputValue = inputs[item.path] ?? item.suggested_value ?? '';
          return (
            <div key={inputKey} className="border-l-4 border-l-amber-500 bg-white px-4 py-3 dark:bg-zinc-900">
              <div className="flex items-center justify-between gap-3">
                <code className="break-all font-mono text-[11px] font-bold text-slate-600 dark:text-zinc-300">{item.path}</code>
                <span className="shrink-0 font-mono text-[10px] text-amber-600">
                  {item.op === 'upsert' ? t('factIssues.aiSuggestionNew') : t('common.edit')}
                </span>
              </div>
              <p className="mt-1 font-sans text-[12px] text-slate-700 dark:text-zinc-300">
                {item.reason || item.confirmation_hint}
              </p>

              <div className="mt-2 grid gap-1.5">
                {item.current_value ? (
                  <div className="border border-diff-before-border bg-diff-before-bg px-2.5 py-1.5">
                    <p className="mb-0.5 font-mono text-[9px] uppercase text-text-secondary">{t('factIssues.before')}</p>
                    <p className="whitespace-pre-wrap break-words font-sans text-[12px] leading-5 text-diff-before-text">{item.current_value}</p>
                  </div>
                ) : null}

                <div className="border-2 border-blue-400 bg-diff-after-bg px-2.5 py-1.5">
                  <p className="mb-0.5 font-mono text-[9px] uppercase text-text-secondary">
                    {t('factIssues.aiSuggestion')} {item.current_value ? `(${t('factIssues.canConfirm')})` : `(${t('factIssues.aiSuggestionNew')})`}
                  </p>
                  <p className="whitespace-pre-wrap break-words font-sans text-[13px] font-medium leading-5 text-diff-after-text">
                    {item.suggested_value || t('factIssues.inputPlaceholder')}
                  </p>
                </div>
              </div>

              <label className="mt-2 block">
                <span className="mb-1 block font-sans text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                  {t('factIssues.editManually')}
                </span>
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputs((prev) => ({ ...prev, [item.path]: e.target.value }))}
                  placeholder={t('factIssues.inputPlaceholder')}
                  className="min-h-16 w-full resize-y border-2 border-black bg-white p-2 font-sans text-[12px] text-slate-900 placeholder:text-slate-300 focus:border-amber-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-950 dark:text-zinc-100"
                  rows={2}
                />
              </label>
            </div>
          );
        })}
      </div>

      <div className="flex gap-2 border-t-2 border-black px-4 py-3">
        <Button onClick={handleSubmit} className="flex-1">
          {t('factIssues.confirmAll')}
        </Button>
        <Button variant="outline" onClick={onSkip}>
          {t('common.skip')}
        </Button>
      </div>
    </div>
  );
}
