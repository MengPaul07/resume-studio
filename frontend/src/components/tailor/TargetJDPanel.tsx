import { useState } from 'react';
import { useTranslation } from 'react-i18next';

interface JDLike { text: string; [key: string]: unknown }
interface Props {
  targetJd: JDLike;
  onUpdate: (jd: JDLike) => void;
  onClear: () => void;
}

export function TargetJDPanel({ targetJd, onUpdate, onClear }: Props) {
  const { t } = useTranslation();
  const [editRaw, setEditRaw] = useState(!targetJd.text);
  const jdLines = (targetJd.text || '').split('\n').filter(Boolean);
  const title = jdLines[0] || t('tailor.pasteJd');
  const body = jdLines.slice(1).join('\n');

  return (
    <div className="mx-4 mb-2 overflow-hidden border-2 border-black dark:border-[var(--brand-line-strong)] bg-white dark:bg-[var(--brand-surface)] shadow-[6px_6px_0px_0px_#000000] dark:shadow-none">
      <div className="flex items-center justify-between border-b-2 border-black dark:border-[var(--brand-line-strong)] bg-blue-50 dark:bg-blue-900/30 px-4 py-2">
        <span className="font-mono text-[11px] font-semibold uppercase text-blue-800 dark:text-blue-300">{t('tailor.targetJdLabel')}</span>
        <div className="flex items-center gap-2">
          <button className="font-mono text-[10px] text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300" onClick={() => setEditRaw(!editRaw)}>
            {editRaw ? t('common.preview') : t('common.edit')}
          </button>
          <button className="font-mono text-[10px] text-red-400 dark:text-red-300 hover:text-red-600 dark:hover:text-red-400" onClick={onClear}>
            {t('common.clear')}
          </button>
        </div>
      </div>
      {editRaw ? (
        <textarea
          className="w-full resize-y bg-white dark:bg-[var(--brand-surface)] px-4 py-3 font-mono text-[11px] leading-relaxed text-gray-700 dark:text-zinc-300 outline-none"
          rows={12}
          value={targetJd.text}
          onChange={(e) => onUpdate({ ...targetJd, text: e.target.value })}
        />
      ) : (
        <div className="px-4 py-3">
          <h4 className="font-sans text-sm font-semibold text-gray-900 dark:text-[var(--brand-ink)] leading-snug">{title}</h4>
          {body && (
            <div className="mt-2 font-sans text-[12px] leading-6 text-gray-700 dark:text-zinc-300 whitespace-pre-line">{body}</div>
          )}
        </div>
      )}
    </div>
  );
}
