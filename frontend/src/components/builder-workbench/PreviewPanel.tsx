import { Eye, EyeOff, Minus, Plus } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/button';
import { OverflowWarning, type OverflowSuggestion } from './OverflowWarning';
import { PaginatedPreview } from './PaginatedPreview';
import { clamp, mmToPx, PAGE_FORMAT_MM, type PageMeta, type RenderGuidanceSettings } from './types';

interface PreviewPanelProps {
  htmlDraft: string;
  dirtyHtml: boolean;
  loading: boolean;
  error: string;
  savingHtml: boolean;
  guidance: RenderGuidanceSettings;
  onResetHtml: () => void;
  onGuidanceChange: (next: RenderGuidanceSettings) => void;
  onOverflowChange?: (overflows: boolean) => void;
  sections?: { key: string; title: string; visible: boolean }[];
  onSectionsChange?: (next: { key: string; title: string; visible: boolean }[]) => void;
}

export function PreviewPanel({
  htmlDraft,
  dirtyHtml,
  loading,
  error,
  savingHtml,
  guidance,
  onResetHtml,
  onGuidanceChange,
  onOverflowChange,
}: PreviewPanelProps) {
  const { t } = useTranslation();
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const [showMarginGuide, setShowMarginGuide] = useState(true);
  const [zoomPercent, setZoomPercent] = useState(75);
  const [zoomMode, setZoomMode] = useState<'auto' | 'manual'>('auto');
  const [pageMeta, setPageMeta] = useState<PageMeta>({ current: 1, total: 1 });

  const pageWidthPx = mmToPx(PAGE_FORMAT_MM[guidance.pageFormat].width);
  const targetPages = guidance.pageCountMode === 'single-page' ? 1 : 2;
  const contentOverflows = pageMeta.total > targetPages;

  const overflowSuggestions = useMemo((): OverflowSuggestion[] => {
    if (!contentOverflows) return [];
    const s: OverflowSuggestion[] = [];
    if (guidance.bodyFontSizePx > 12) {
      s.push({
        label: `Reduce Body ${guidance.bodyFontSizePx}px → ${guidance.bodyFontSizePx - 1}px`,
        action: () => onGuidanceChange({ ...guidance, bodyFontSizePx: guidance.bodyFontSizePx - 1 }),
      });
    }
    if (guidance.sectionGapPx > 12) {
      s.push({
        label: `Tighten Section Gap ${guidance.sectionGapPx}px → 12px`,
        action: () => onGuidanceChange({ ...guidance, sectionGapPx: 12 }),
      });
    }
    return s;
  }, [contentOverflows, guidance, onGuidanceChange]);

  // Notify parent when content overflows, and auto-switch to double-page
  const forcedRef = useRef(false);
  useEffect(() => {
    onOverflowChange?.(contentOverflows);
    if (contentOverflows && guidance.pageCountMode === 'single-page' && !forcedRef.current) {
      forcedRef.current = true;
      onGuidanceChange({ ...guidance, pageCountMode: 'double-page' });
    }
    if (!contentOverflows) {
      forcedRef.current = false;
    }
  }, [contentOverflows, guidance, onGuidanceChange, onOverflowChange]);

  useEffect(() => {
    const node = viewportRef.current;
    if (!node) return;
    const computeAutoZoom = () => {
      if (zoomMode !== 'auto') return;
      const available = Math.max(320, node.clientWidth - 42);
      const fit = clamp(Math.floor((available / pageWidthPx) * 100), 40, 75);
      setZoomPercent(fit);
    };

    computeAutoZoom();
    const observer = new ResizeObserver(computeAutoZoom);
    observer.observe(node);
    return () => observer.disconnect();
  }, [pageWidthPx, zoomMode]);

  const htmlDisplay = useMemo(() => htmlDraft.trim(), [htmlDraft]);

  const setManualZoom = (next: number) => {
    setZoomMode('manual');
    setZoomPercent(clamp(next, 40, 150));
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--brand-line)] bg-[var(--brand-surface-soft)] px-4 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setManualZoom(zoomPercent - 5)}
            className="inline-flex h-8 w-8 items-center justify-center border border-[var(--brand-line)] bg-white dark:bg-zinc-800 dark:text-zinc-100 transition-all hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-none"
          >
            <Minus className="size-3.5" />
          </button>
          <button
            type="button"
            onClick={() => {
              setZoomMode('auto');
            }}
            className={`border border-[var(--brand-line)] px-3 py-1.5 font-sans text-xs font-medium ${
              zoomMode === 'auto' ? 'bg-[var(--brand-signal)] text-white shadow-[2px_2px_0px_0px_#000000]' : 'bg-white dark:bg-zinc-800 dark:text-zinc-100'
            }`}
          >
            {zoomPercent}%
          </button>
          <button
            type="button"
            onClick={() => setManualZoom(zoomPercent + 5)}
            className="inline-flex h-8 w-8 items-center justify-center border border-[var(--brand-line)] bg-white dark:bg-zinc-800 dark:text-zinc-100 transition-all hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-none"
          >
            <Plus className="size-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setShowMarginGuide((prev) => !prev)}
            className="inline-flex items-center gap-1 border border-[var(--brand-line)] bg-white dark:bg-zinc-800 dark:text-zinc-100 px-3 py-1.5 font-sans text-xs font-medium hover:bg-gray-50 dark:hover:bg-zinc-700"
          >
            {showMarginGuide ? <Eye className="size-3.5" /> : <EyeOff className="size-3.5" />}
            {t('editorPanel.margins')}
          </button>
        </div>
        <div className="font-sans text-xs font-medium text-gray-700 dark:text-zinc-300">
          Page {pageMeta.current} / {pageMeta.total}
        </div>
      </div>

      <OverflowWarning
        contentOverflows={contentOverflows}
        totalPages={pageMeta.total}
        targetPages={targetPages}
        suggestions={overflowSuggestions}
      />

      <div className="border-b border-[var(--brand-line)] bg-[var(--brand-surface-soft)] px-4 py-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="font-mono text-[11px] uppercase tracking-wider text-gray-600 dark:text-zinc-400">Preview</p>
          <div className="flex items-center gap-2">
            {dirtyHtml ? (
              <span className="border border-[var(--brand-line)] bg-[#fce6a3] px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-black dark:text-zinc-900">
                unsaved changes
              </span>
            ) : (
              <span className="font-mono text-[10px] uppercase tracking-wider text-gray-500 dark:text-zinc-400">synced</span>
            )}
            <Button size="sm" variant="outline" onClick={onResetHtml} disabled={savingHtml}>
              Reset
            </Button>
          </div>
        </div>
      </div>

      <div
        ref={viewportRef}
        className="relative min-h-0 flex-1 overflow-hidden bg-[var(--brand-surface)]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(120,120,120,0.14) 1px, transparent 1px), linear-gradient(90deg, rgba(120,120,120,0.14) 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        }}
      >
        {loading ? (
          <div className="flex h-full items-center justify-center font-sans text-xs font-medium text-gray-600 dark:text-zinc-400">
            Loading Resume...
          </div>
        ) : null}

        {error ? (
          <div className="absolute left-4 top-4 z-10 border border-[var(--brand-line)] bg-[#ffe9e5] px-3 py-2 font-sans text-xs font-medium text-[var(--status-failed)]">
            {error}
          </div>
        ) : null}

        {htmlDisplay ? (
          <PaginatedPreview
            html={htmlDisplay}
            pageFormat={guidance.pageFormat}
            pageCountMode={guidance.pageCountMode}
            marginsMm={guidance.margins}
            zoomPercent={zoomPercent}
            showMarginGuide={showMarginGuide}
            onPageMetaChange={setPageMeta}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center px-6 text-center">
            <p className="font-serif text-4xl uppercase">Unrendered</p>
            <p className="mt-3 font-sans text-xs font-medium text-gray-600 dark:text-zinc-400">
              暂无可预览内容，请先点击 Rebuild Layout。
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
