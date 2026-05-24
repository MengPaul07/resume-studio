import { useState, useEffect, useCallback, useRef } from 'react';
import { mmToPx, PAGE_FORMAT_MM } from './types';
import type { PageFormat } from './types';

export interface PageBreak {
  pageNumber: number;
  contentOffset: number; // Where this page starts (px)
  contentEnd: number; // Where this page ends (px)
}

interface MarginPx {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

interface UsePaginationOptions {
  pageSize: PageFormat;
  marginsPx: MarginPx;
  measurementRef: React.RefObject<HTMLDivElement | null>;
  debounceMs?: number;
}

interface UsePaginationResult {
  pages: PageBreak[];
  totalContentHeight: number;
  isCalculating: boolean;
}

type ItemBounds = { top: number; bottom: number; element: Element };

/**
 * Custom hook for calculating page breaks from a hidden measurement container.
 * Waits for fonts, respects item/header boundaries, and auto-recalculates
 * on content changes via ResizeObserver.
 *
 * Ported from Resume Matcher's usePagination.
 */
export function usePagination({
  pageSize,
  marginsPx,
  measurementRef,
  debounceMs = 150,
}: UsePaginationOptions): UsePaginationResult {
  const [pages, setPages] = useState<PageBreak[]>([
    { pageNumber: 1, contentOffset: 0, contentEnd: 0 },
  ]);
  const [totalContentHeight, setTotalContentHeight] = useState(0);
  const [isCalculating, setIsCalculating] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const observerRef = useRef<ResizeObserver | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const calculatePageBreaks = useCallback(() => {
    const container = measurementRef.current;
    if (!container) {
      if (mountedRef.current) {
        setPages([{ pageNumber: 1, contentOffset: 0, contentEnd: 0 }]);
      }
      return;
    }

    setIsCalculating(true);

    // Wait for fonts to load before measuring
    document.fonts.ready.then(() => {
      if (!mountedRef.current || container !== measurementRef.current) {
        setIsCalculating(false);
        return;
      }

      const pageDims = PAGE_FORMAT_MM[pageSize];
      const pageHeightPx = mmToPx(pageDims.height) - marginsPx.top - marginsPx.bottom;
      const contentHeight = container.scrollHeight;

      setTotalContentHeight(contentHeight);

      // Content fits on one page
      if (contentHeight <= pageHeightPx) {
        setPages([{ pageNumber: 1, contentOffset: 0, contentEnd: contentHeight }]);
        setIsCalculating(false);
        return;
      }

      // ── Find items that should NOT be split ──
      const items = container.querySelectorAll('.resume-item, [data-resume-item], [data-no-break]');
      const containerRect = container.getBoundingClientRect();
      const itemBounds: ItemBounds[] = [];

      items.forEach((item) => {
        const rect = item.getBoundingClientRect();
        itemBounds.push({
          top: rect.top - containerRect.top,
          bottom: rect.bottom - containerRect.top,
          element: item,
        });
      });

      // ── Prevent section header orphans ──
      const sectionTitles = container.querySelectorAll(
        '.resume-section-title, .resume-section-title-sm, [data-section] h2, [data-section] h3, .section-title, section > h2, section > h3',
      );
      sectionTitles.forEach((title) => {
        const titleRect = title.getBoundingClientRect();
        const section = title.closest('[data-section], .resume-section, section');
        if (section) {
          const firstContent =
            section.querySelector('.resume-item') ||
            section.querySelector('[data-resume-item]') ||
            section.querySelector('.resume-items > *:first-child') ||
            (title.nextElementSibling !== title ? title.nextElementSibling : null);

          if (firstContent && firstContent !== title) {
            const firstContentRect = firstContent.getBoundingClientRect();
            itemBounds.push({
              top: titleRect.top - containerRect.top,
              bottom: firstContentRect.bottom - containerRect.top,
              element: title,
            });
          } else {
            // No content found, just protect the title with a small buffer
            itemBounds.push({
              top: titleRect.top - containerRect.top,
              bottom: titleRect.bottom - containerRect.top + 50,
              element: title,
            });
          }
        }
      });

      // Also protect bullet items from being split
      const listItems = container.querySelectorAll('li');
      listItems.forEach((li) => {
        const rect = li.getBoundingClientRect();
        itemBounds.push({
          top: rect.top - containerRect.top,
          bottom: rect.bottom - containerRect.top,
          element: li,
        });
      });

      // Sort by top position
      itemBounds.sort((a, b) => a.top - b.top);

      // ── Calculate page breaks ──
      const breakPoints: number[] = [0];
      let currentOffset = 0;

      while (currentOffset + pageHeightPx < contentHeight) {
        let nextBreak = currentOffset + pageHeightPx;

        // Check if this break would split an item
        for (const bound of itemBounds) {
          if (bound.top < nextBreak && bound.bottom > nextBreak) {
            const proposedBreak = bound.top;
            // Only move break if it doesn't leave too much empty space
            if (proposedBreak > currentOffset + pageHeightPx * 0.5) {
              nextBreak = proposedBreak;
              break;
            }
          }
        }

        // Safety: ensure we make progress (at least 100px per page)
        if (nextBreak <= currentOffset + 100) {
          nextBreak = currentOffset + pageHeightPx;
        }

        currentOffset = nextBreak;

        if (currentOffset < contentHeight) {
          const lastBreak = breakPoints[breakPoints.length - 1];
          if (currentOffset - lastBreak > 1) {
            breakPoints.push(currentOffset);
          }
        }
      }

      // Convert break points to page objects
      const newPages: PageBreak[] = breakPoints.map((offset, index) => ({
        pageNumber: index + 1,
        contentOffset: offset,
        contentEnd:
          index < breakPoints.length - 1
            ? breakPoints[index + 1]
            : contentHeight,
      }));

      // Filter out empty pages (contentEnd <= contentOffset + 1)
      const nonEmptyPages = newPages.filter(
        (p, i) => p.contentEnd - p.contentOffset > 1 || i === 0,
      );

      if (mountedRef.current) {
        setPages(nonEmptyPages.length > 0 ? nonEmptyPages : newPages.slice(0, 1));
        setIsCalculating(false);
      }
    });
  }, [pageSize, marginsPx, measurementRef]);

  const debouncedCalculate = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      calculatePageBreaks();
    }, debounceMs);
  }, [calculatePageBreaks, debounceMs]);

  // Set up ResizeObserver on measurement container
  useEffect(() => {
    const container = measurementRef.current;
    if (!container) return;

    // Initial calculation (fonts.ready is handled inside calculatePageBreaks)
    calculatePageBreaks();

    const ro = new ResizeObserver(() => {
      debouncedCalculate();
    });
    ro.observe(container);
    observerRef.current = ro;

    return () => {
      ro.disconnect();
      observerRef.current = null;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [calculatePageBreaks, debouncedCalculate, measurementRef]);

  // Recalculate when dimensions change
  useEffect(() => {
    calculatePageBreaks();
  }, [pageSize, marginsPx, calculatePageBreaks]);

  return { pages, totalContentHeight, isCalculating };
}
