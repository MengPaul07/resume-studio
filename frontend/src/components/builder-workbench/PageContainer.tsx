import { useMemo } from 'react';

interface PageContainerProps {
  html: string;
  pageNumber: number;
  totalPages: number;
  widthPx: number;
  heightPx: number;
  zoomPercent: number;
  showMarginGuide: boolean;
  marginsPx: {
    top: number;
    right: number;
    bottom: number;
    left: number;
  };
  contentOffset: number;
  contentEnd: number;
  maxContentHeight: number;
}

export function PageContainer({
  html,
  pageNumber,
  totalPages,
  widthPx,
  heightPx,
  zoomPercent,
  showMarginGuide,
  marginsPx,
  contentOffset,
  contentEnd,
  maxContentHeight,
}: PageContainerProps) {
  const scale = zoomPercent / 100;

  const contentWidth = widthPx - marginsPx.left - marginsPx.right;
  const actualContentHeight = Math.min(maxContentHeight, contentEnd - contentOffset);

  // PDF-style zoom: page always laid out at full size, CSS transform scales the visual.
  // marginBottom compensates for the transform so page spacing looks natural.
  const marginBottomPx = heightPx * scale - heightPx + 16;

  const guideStyle = useMemo(
    () => ({
      top: `${marginsPx.top}px`,
      right: `${marginsPx.right}px`,
      bottom: `${marginsPx.bottom}px`,
      left: `${marginsPx.left}px`,
    }),
    [marginsPx.bottom, marginsPx.left, marginsPx.right, marginsPx.top],
  );

  return (
    // No outer flex wrapper — we need margin-bottom on the page itself
    <div className="flex flex-col items-center" style={{ marginBottom: `${marginBottomPx}px` }}>
      {/* ── Page: rendered at full logical size, scaled visually ── */}
      <div
        className="relative overflow-hidden border border-[var(--brand-line)] bg-white dark:bg-zinc-900 shadow-md dark:shadow-none"
        style={{
          width: `${widthPx}px`,
          height: `${heightPx}px`,
          transform: `scale(${scale})`,
          transformOrigin: 'top',
        }}
      >
        {/* ── Margin guides (unscaled — part of the page) ── */}
        {showMarginGuide ? (
          <>
            <div className="pointer-events-none absolute border border-dashed border-blue-700/90" style={guideStyle} />
            <span className="pointer-events-none absolute left-1 top-1 h-2 w-2 border-l border-t border-blue-700/90" />
            <span className="pointer-events-none absolute right-1 top-1 h-2 w-2 border-r border-t border-blue-700/90" />
            <span className="pointer-events-none absolute bottom-1 left-1 h-2 w-2 border-b border-l border-blue-700/90" />
            <span className="pointer-events-none absolute bottom-1 right-1 h-2 w-2 border-b border-r border-blue-700/90" />
          </>
        ) : null}

        {/* ── Content area: positioned in unscaled coords, clipped ── */}
        <div
          className="absolute overflow-hidden"
          style={{
            top: `${marginsPx.top}px`,
            left: `${marginsPx.left}px`,
            width: `${contentWidth}px`,
            height: `${actualContentHeight}px`,
          }}
        >
          <div
            className="absolute left-0"
            style={{
              top: `${-contentOffset}px`,
              width: `${contentWidth}px`,
            }}
          >
            <div
              style={{ width: `${contentWidth}px` }}
              dangerouslySetInnerHTML={{ __html: html }}
            />
          </div>
        </div>

        {/* ── Page number (inverse-scaled to stay readable) ── */}
        <div
          className="pointer-events-none absolute bottom-2 right-2 border border-black dark:border-zinc-600 bg-[#f5f5f5] dark:bg-zinc-800 px-2 py-0.5 font-sans text-[11px] font-medium text-gray-700 dark:text-zinc-300"
          style={{
            transform: `scale(${1 / scale})`,
            transformOrigin: 'bottom right',
          }}
        >
          Page {pageNumber} of {totalPages}
        </div>
      </div>

      {/* ── Page break separator ── */}
      {pageNumber < totalPages ? (
        <div className="mt-4 w-[min(92%,40rem)] border-t border-dashed border-black/60 dark:border-white/20 pt-1 text-center font-mono text-[10px] uppercase tracking-[0.12em] text-gray-600 dark:text-zinc-400">
          Page Break
        </div>
      ) : null}
    </div>
  );
}
