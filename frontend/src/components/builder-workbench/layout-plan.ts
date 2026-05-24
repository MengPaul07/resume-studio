import {
  clamp,
  type BuilderSectionDraft,
  type RenderGuidanceSettings,
} from './types';

export function toSectionMap(
  settings: RenderGuidanceSettings,
  sections: BuilderSectionDraft[],
): { left: string[]; right: string[] } {
  const visibleSections = sections.filter((item) => item.visible);

  const left = settings.columnMode === 'double'
    ? visibleSections.filter((s) => s.column === 'left').map((s) => s.key)
    : [];

  const right = settings.columnMode === 'double'
    ? visibleSections.filter((s) => s.column === 'right').map((s) => s.key)
    : visibleSections.map((s) => s.key);

  return { left, right };
}

export function buildLayoutPlanFromGuidance(
  settings: RenderGuidanceSettings,
  sections: BuilderSectionDraft[],
): Record<string, unknown> {
  const leftWidth = settings.columnMode === 'double' ? clamp(settings.leftWidthPercent, 24, 42) : 100;
  const rightWidth = settings.columnMode === 'double' ? 100 - leftWidth : 0;
  const sectionMap = toSectionMap(settings, sections);

  return {
    page: {
      format: 'a4',
      columns:
        settings.columnMode === 'double'
          ? [
              { id: 'left', width: `${leftWidth}%` },
              { id: 'right', width: `${rightWidth}%` },
            ]
          : [{ id: 'main', width: '100%' }],
      section_gap_px: clamp(settings.sectionGapPx, 10, 30),
      column_gap_px: clamp(settings.columnGapPx, 10, 28),
      item_gap_px: clamp(settings.itemGapPx, 6, 18),
      margins_mm: settings.margins,
      pagination_policy: {
        page_count_mode: settings.pageCountMode,
        target_pages: settings.pageCountMode === 'double-page' ? 2 : 1,
      },
    },
    section_map: sectionMap,
    sections: sections.map((item, index) => ({
      id: item.id,
      key: item.key,
      title: item.title,
      visible: item.visible,
      column: item.column,
      order: index,
    })),
  };
}
