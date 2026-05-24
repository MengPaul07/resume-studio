import { ChevronLeft, ChevronRight } from 'lucide-react';
import { normalizeDiffPayload, computeInlineDiff } from '../../lib/tailor/diff';
import { toDisplayText } from '../../lib/tailor/utils';
import type { PendingChange } from '../../lib/tailor/types';

interface Props {
  change: PendingChange;
  activeVariantIndex: number;
  onSwitchVariant: (path: string, variantIdx: number) => void;
}

export function ChangeDetailPopover({ change, activeVariantIndex, onSwitchVariant }: Props) {
  const variant = change.variants[activeVariantIndex];
  if (!variant) return null;

  const currentText = toDisplayText(change.current_value) || '(empty)';
  const candidateText = toDisplayText(variant.suggested_value) || '(empty)';
  const backendDiff = normalizeDiffPayload(change.diff_payload as any);
  const diffChunks =
    backendDiff?.chunks.length
      ? backendDiff.chunks
      : computeInlineDiff(currentText, candidateText);

  const hasVariants = change.variants.length > 1;

  return (
    <div className="border border-black bg-[#fffdf7] p-2 mt-1">
      <div className="flex items-center justify-between gap-2">
        <p className="font-mono text-[10px] uppercase text-gray-500 dark:text-zinc-400">{change.path}</p>
        {hasVariants ? (
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => {
                const prev = activeVariantIndex === 0
                  ? change.variants.length - 1
                  : activeVariantIndex - 1;
                onSwitchVariant(change.path, prev);
              }}
              className="inline-flex size-5 items-center justify-center border border-black dark:border-zinc-600 bg-white dark:bg-zinc-800 dark:text-zinc-100 hover:bg-gray-100 dark:hover:bg-zinc-700"
            >
              <ChevronLeft className="size-3" />
            </button>
            <span className="font-mono text-[10px] tabular-nums text-gray-600 dark:text-zinc-400">
              {activeVariantIndex + 1}/{change.variants.length}
            </span>
            <button
              type="button"
              onClick={() => {
                const next = (activeVariantIndex + 1) % change.variants.length;
                onSwitchVariant(change.path, next);
              }}
              className="inline-flex size-5 items-center justify-center border border-black dark:border-zinc-600 bg-white dark:bg-zinc-800 dark:text-zinc-100 hover:bg-gray-100 dark:hover:bg-zinc-700"
            >
              <ChevronRight className="size-3" />
            </button>
          </div>
        ) : null}
        {variant.option_label ? (
          <span className="font-mono text-[10px] text-gray-500 dark:text-zinc-400">{variant.option_label}</span>
        ) : null}
      </div>

      <div className="mt-1 grid gap-1.5">
        <div className="border border-[#d9d2bf] bg-[#f7f2e5] px-2 py-1">
          <p className="font-mono text-[9px] uppercase text-[#7a6f53]">Before</p>
          <p className="whitespace-pre-wrap text-[11px] leading-5 text-[#403620]">
            {diffChunks.length > 0
              ? diffChunks.map((chunk, idx) => {
                  if (chunk.type === 'add') return null;
                  return (
                    <span
                      key={`before-${idx}`}
                      className={
                        chunk.type === 'remove'
                          ? 'bg-[#fbcfe8] text-[#9d174d] line-through'
                          : ''
                      }
                    >
                      {chunk.text}
                    </span>
                  );
                })
              : currentText}
          </p>
        </div>
        <div className="border border-[#bfc9d9] bg-[#edf3ff] px-2 py-1">
          <p className="font-mono text-[9px] uppercase text-[#334155]">After</p>
          <p className="whitespace-pre-wrap text-[11px] leading-5 text-[#1e293b]">
            {diffChunks.length > 0
              ? diffChunks.map((chunk, idx) => {
                  if (chunk.type === 'remove') return null;
                  return (
                    <span
                      key={`after-${idx}`}
                      className={
                        chunk.type === 'add'
                          ? 'bg-[#bfdbfe] text-[#1e3a8a]'
                          : ''
                      }
                    >
                      {chunk.text}
                    </span>
                  );
                })
              : candidateText}
          </p>
        </div>
      </div>

      {variant.reason ? (
        <p className="mt-1.5 font-mono text-[10px] text-gray-500 dark:text-zinc-400 italic">
          {variant.reason}
        </p>
      ) : null}

      {variant.style_variant ? (
        <p className="mt-0.5 font-mono text-[9px] uppercase text-gray-400 dark:text-zinc-500">
          style: {variant.style_variant}
        </p>
      ) : null}
    </div>
  );
}
