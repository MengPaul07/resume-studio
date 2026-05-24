import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronUp, GitCompare } from 'lucide-react';
import { computeInlineDiff } from '../../lib/tailor/diff';
import { toDisplayText, truncateValue } from '../../lib/tailor/utils';
import type { PendingChange } from '../../lib/tailor/types';

interface Props {
  changes: PendingChange[];
}

const OP_LABELS: Record<string, { text: string; color: string }> = {
  update: { text: 'update', color: 'bg-blue-100 text-blue-700' },
  upsert: { text: 'upsert', color: 'bg-green-100 text-green-700' },
  delete: { text: 'delete', color: 'bg-red-100 text-red-700' },
};

export function AutoApplyDiff({ changes }: Props) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  if (!changes.length) return null;

  return (
    <div className="mx-4 border-2 border-black dark:border-zinc-600 bg-white dark:bg-zinc-900 shadow-[4px_4px_0px_0px_#000000] dark:shadow-none">
      {/* Header */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 border-b-2 border-black bg-green-100 px-4 py-3 text-left hover:bg-green-200/50 transition-colors"
      >
        <GitCompare className="size-4 text-green-700 shrink-0" />
        <span className="font-serif text-base font-bold text-slate-900">
          {t('autoApply.appliedCount', { count: changes.length })}
        </span>
        <span className="ml-auto text-slate-500">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </span>
      </button>

      {expanded && (
        <div className="divide-y divide-slate-100 max-h-[50vh] overflow-y-auto">
          {changes.map((change, idx) => (
            <DiffRow key={change.item_key || idx} change={change} />
          ))}
        </div>
      )}
    </div>
  );
}

function DiffRow({ change }: { change: PendingChange }) {
  const { t } = useTranslation();
  const variant = change.variants[0];
  if (!variant) return null;

  const beforeText = toDisplayText(change.current_value) || '(空)';
  const afterText = toDisplayText(variant.suggested_value) || '(空)';
  const op = change.op || 'update';
  const opMeta = OP_LABELS[op] || OP_LABELS.update;
  const isUpdate = op === 'update';
  const diffChunks = isUpdate ? computeInlineDiff(beforeText, afterText) : [];

  return (
    <div className="border-l-4 border-l-green-500 px-4 py-3">
      {/* Path + badges */}
      <div className="flex items-center gap-2 mb-2">
        <code className="font-mono text-[11px] font-bold text-slate-600 truncate max-w-[60%]">
          {change.path}
        </code>
        <span className={`shrink-0 font-mono text-[9px] px-1.5 py-0.5 rounded ${opMeta.color}`}>
          {opMeta.text}
        </span>
        {change.lowConfidence && (
          <span className="shrink-0 font-mono text-[9px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">
            需确认
          </span>
        )}
      </div>

      {/* Before/After */}
      {isUpdate ? (
        <div className="grid gap-1.5">
          <div className="border-2 border-diff-before-border bg-diff-before-bg px-2.5 py-1.5">
            <p className="font-mono text-[9px] uppercase text-text-secondary mb-0.5">Before</p>
            <p className="font-sans text-[12px] leading-5 text-diff-before-text">
              {diffChunks.length > 0
                ? diffChunks.map((chunk, i) => {
                    if (chunk.type === 'add') return null;
                    return (
                      <span key={`bb-${i}`} className={chunk.type === 'remove' ? 'bg-[#fbcfe8] text-[#9d174d] line-through' : ''}>
                        {chunk.text}
                      </span>
                    );
                  })
                : beforeText}
            </p>
          </div>
          <div className="border-2 border-diff-after-border bg-diff-after-bg px-2.5 py-1.5">
            <p className="font-mono text-[9px] uppercase text-text-secondary mb-0.5">After</p>
            <p className="font-sans text-[12px] leading-5 text-diff-after-text">
              {diffChunks.length > 0
                ? diffChunks.map((chunk, i) => {
                    if (chunk.type === 'remove') return null;
                    return (
                      <span key={`ba-${i}`} className={chunk.type === 'add' ? 'bg-[#bfdbfe] text-[#1e3a8a]' : ''}>
                        {chunk.text}
                      </span>
                    );
                  })
                : afterText}
            </p>
          </div>
        </div>
      ) : (
        <div className="border-2 border-diff-after-border bg-diff-after-bg px-2.5 py-1.5">
          <p className="font-mono text-[9px] uppercase text-text-secondary mb-0.5">
            {op === 'upsert' ? t('autoApply.newContent') : t('autoApply.after')}
          </p>
          <p className="font-sans text-[12px] leading-5 text-diff-after-text whitespace-pre-wrap">
            {truncateValue(afterText, 300)}
          </p>
        </div>
      )}

      {/* Reason */}
      {variant.reason ? (
        <p className="mt-1.5 font-mono text-[10px] text-slate-400">{variant.reason}</p>
      ) : null}
    </div>
  );
}
