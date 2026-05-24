import { useEffect, useMemo, useRef, useState } from 'react';
import { ensureUtf8HtmlDocument } from '../../lib/html-encoding';
import { PageContainer } from './PageContainer';
import { usePagination } from './use-pagination';
import { clamp, mmToPx, PAGE_FORMAT_MM, type PageCountMode, type PageFormat, type PageMeta } from './types';

interface PaginatedPreviewProps {
  html: string;
  pageFormat: PageFormat;
  pageCountMode: PageCountMode;
  marginsMm: {
    top: number;
    right: number;
    bottom: number;
    left: number;
  };
  zoomPercent: number;
  showMarginGuide: boolean;
  onPageMetaChange?: (meta: PageMeta) => void;
}

// ── HTML extraction: strip .page wrapper dimensions, keep styles ──

function extractDisplayHtml(rawHtml: string): string {
  const html = ensureUtf8HtmlDocument(rawHtml);
  const doc = new DOMParser().parseFromString(html, 'text/html');

  const styles = Array.from(doc.head.querySelectorAll('style, link[rel="stylesheet"]'))
    .map((el) => el.outerHTML)
    .join('\n');

  const scopeFix = `<style>
.resume-display-scope {
  margin: 0;
  padding: 0;
}
.resume-display-scope .page {
  width: 100% !important;
  max-width: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
  min-height: auto !important;
  height: auto !important;
  box-shadow: none !important;
  border: none !important;
  overflow: visible !important;
}
.resume-display-scope .page * {
  max-width: 100% !important;
}
.resume-display-scope p,
.resume-display-scope li,
.resume-display-scope span,
.resume-display-scope a,
.resume-display-scope h1,
.resume-display-scope h2,
.resume-display-scope h3,
.resume-display-scope h4,
.resume-display-scope h5,
.resume-display-scope h6 {
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
}
</style>`;

  return `${scopeFix}\n${styles}\n<div class="resume-display-scope">${doc.body.innerHTML}</div>`;
}

function targetPageCount(pageCountMode: PageCountMode): number {
  return pageCountMode === 'double-page' ? 2 : 1;
}

export function PaginatedPreview({
  html,
  pageFormat,
  pageCountMode,
  marginsMm,
  zoomPercent,
  showMarginGuide,
  onPageMetaChange,
}: PaginatedPreviewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const measureRef = useRef<HTMLDivElement | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  // Derived dimensions
  const pageSize = PAGE_FORMAT_MM[pageFormat];
  const pageWidthPx = mmToPx(pageSize.width);
  const pageHeightPx = mmToPx(pageSize.height);
  const marginsPx = useMemo(
    () => ({
      top: mmToPx(marginsMm.top),
      right: mmToPx(marginsMm.right),
      bottom: mmToPx(marginsMm.bottom),
      left: mmToPx(marginsMm.left),
    }),
    [marginsMm.bottom, marginsMm.left, marginsMm.right, marginsMm.top],
  );
  const contentWidth = pageWidthPx - marginsPx.left - marginsPx.right;
  const contentHeight = pageHeightPx - marginsPx.top - marginsPx.bottom;

  // Extract display HTML once
  const displayHtml = useMemo(() => extractDisplayHtml(html), [html]);

  // ── Pagination hook (Resume Matcher port) ──
  const { pages: rawPages } = usePagination({
    pageSize: pageFormat,
    marginsPx,
    measurementRef: measureRef,
  });

  // Cap displayed pages based on pageCountMode, but track true total
  const fullPageCount = rawPages.length;
  const displayPages = useMemo(() => {
    const maxDisplay = targetPageCount(pageCountMode);
    const capped = rawPages.slice(0, maxDisplay);
    return capped.map((p, i) => ({
      key: `${i}-${Math.round(p.contentOffset)}`,
      pageNumber: i + 1,
      totalPages: fullPageCount,
      contentOffset: p.contentOffset,
      contentEnd: p.contentEnd,
    }));
  }, [rawPages, pageCountMode, fullPageCount]);

  // ── Page meta for overflow detection ──
  useEffect(() => {
    if (!onPageMetaChange) return;
    const displayTotal = Math.max(1, displayPages.length);
    onPageMetaChange({
      current: clamp(currentPage, 1, displayTotal),
      total: Math.max(1, fullPageCount),
    });
  }, [currentPage, onPageMetaChange, displayPages.length, fullPageCount]);

  // ── Scroll-based page tracking ──
  const handleScroll = () => {
    const container = containerRef.current;
    if (!container || displayPages.length <= 1) return;
    const scrollCenter = container.scrollTop + container.clientHeight * 0.5;
    const elements = Array.from(
      container.querySelectorAll<HTMLElement>('[data-page-index]'),
    );
    let nextPage = 1;
    let bestDistance = Number.POSITIVE_INFINITY;
    for (const el of elements) {
      const top = el.offsetTop;
      const center = top + el.offsetHeight * 0.5;
      const distance = Math.abs(center - scrollCenter);
      if (distance < bestDistance) {
        bestDistance = distance;
        nextPage = Number(el.dataset.pageIndex || 1);
      }
    }
    setCurrentPage(nextPage);
  };

  // ── Thumbnail scale ──
  const thumbScale = 38 / pageWidthPx;
  const thumbMarginTop = marginsPx.top * thumbScale;
  const thumbMarginLeft = marginsPx.left * thumbScale;

  return (
    <div className="relative flex h-full min-h-0">
      {/* Hidden measurement container — renders full HTML at content width */}
      <div
        ref={measureRef}
        className="absolute -left-[99999px] top-0 opacity-0 pointer-events-none"
        style={{ width: `${contentWidth}px` }}
        aria-hidden="true"
      >
        <div dangerouslySetInnerHTML={{ __html: displayHtml }} />
      </div>

      {/* Visible pages */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 min-w-0 overflow-auto px-3 py-4"
      >
        <div className="space-y-0">
          {displayPages.map((page) => (
            <div key={page.key} data-page-index={page.pageNumber}>
              <PageContainer
                html={displayHtml}
                pageNumber={page.pageNumber}
                totalPages={page.totalPages}
                widthPx={pageWidthPx}
                heightPx={pageHeightPx}
                zoomPercent={zoomPercent}
                showMarginGuide={showMarginGuide}
                marginsPx={marginsPx}
                contentOffset={page.contentOffset}
                contentEnd={page.contentEnd}
                maxContentHeight={contentHeight}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Page Thumbnail Rail — mini page previews */}
      {displayPages.length > 1 && (
        <div className="z-10 flex w-[52px] shrink-0 flex-col items-center gap-2 overflow-auto border-l border-black/10 dark:border-zinc-700 bg-white/60 dark:bg-zinc-900/60 px-1.5 py-3">
          {displayPages.map((page) => (
            <button
              key={`thumb-${page.key}`}
              type="button"
              onClick={() => {
                const el = containerRef.current?.querySelector(
                  `[data-page-index="${page.pageNumber}"]`,
                );
                el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }}
              title={`Page ${page.pageNumber} of ${page.totalPages}`}
              className={`relative w-full overflow-hidden rounded border transition-shadow ${
                page.pageNumber === currentPage
                  ? 'border-black dark:border-zinc-300 shadow-[2px_2px_0px_0px_rgba(0,0,0,0.3)]'
                  : 'border-gray-300 dark:border-zinc-700 hover:border-black dark:hover:border-zinc-400'
              }`}
              style={{ height: `${pageHeightPx * thumbScale}px` }}
            >
              {/* Mini page preview — clipped slice */}
              <div
                className="absolute overflow-hidden bg-white"
                style={{
                  top: thumbMarginTop,
                  left: thumbMarginLeft,
                  width: contentWidth * thumbScale,
                  height: contentHeight * thumbScale,
                }}
              >
                <div
                  className="absolute left-0 w-full"
                  style={{
                    top: `${-page.contentOffset}px`,
                    width: `${contentWidth}px`,
                    transform: `scale(${thumbScale})`,
                    transformOrigin: 'top left',
                    pointerEvents: 'none' as const,
                  }}
                >
                  <div dangerouslySetInnerHTML={{ __html: displayHtml }} />
                </div>
              </div>
              {/* Active indicator bar */}
              <div
                className={`absolute top-0 left-0 w-[3px] h-full transition-colors ${
                  page.pageNumber === currentPage
                    ? 'bg-black dark:bg-zinc-300'
                    : 'bg-transparent'
                }`}
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
