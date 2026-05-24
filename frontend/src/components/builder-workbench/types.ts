export type PageFormat = 'A4';
export type ColumnMode = 'single' | 'double';
export type PageCountMode = 'single-page' | 'double-page';
export type SectionHeadingStyle = 'underline' | 'bar' | 'boxed';
export type SectionHeadingCase = 'uppercase' | 'title';
export type BulletStyle = 'disc' | 'square' | 'dash';
export type DateStyle = 'muted' | 'inline' | 'bottom-inline';
export type ListLayoutMode = 'vertical' | 'horizontal';
export type HeaderAlign = 'left' | 'center';
export type HeaderLayout = 'left' | 'center' | 'split';

export type ContactLayout = 'inline' | 'stacked';
export type PhotoPosition = 'left' | 'right';
export type PhotoShape = 'circle' | 'square' | 'rounded';
export type PhotoPreset = 'one-inch' | 'two-inch' | 'custom-square';

export interface GuidanceMargins {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

export interface RenderGuidanceSettings {
  pageFormat: PageFormat;
  columnMode: ColumnMode;
  pageCountMode: PageCountMode;
  headerFont: 'serif' | 'sans-serif' | 'mono';
  bodyFont: 'serif' | 'sans-serif' | 'mono';
  headerLayout: HeaderLayout;
  nameFontSizePx: number;
  roleFontSizePx: number;
  metaFontSizePx: number;
  leftWidthPercent: number;
  sectionGapPx: number;
  bodyFontSizePx: number;
  lineHeightPercent: number;
  sectionHeadingSizePx: number;
  sectionHeadingStyle: SectionHeadingStyle;
  sectionHeadingCase: SectionHeadingCase;
  bulletStyle: BulletStyle;
  dateStyle: DateStyle;
  columnGapPx: number;
  itemGapPx: number;
  showHeaderDivider: boolean;
  skillsLayout: ListLayoutMode;
  languagesLayout: ListLayoutMode;
  certificationsLayout: ListLayoutMode;
  awardsLayout: ListLayoutMode;
  tagFontSizePx: number;
  headingMarginBottomPx: number;
  sectionUnderlineGapPx: number;
  sectionUnderlineThicknessPx: number;
  contactGapPx: number;
  accentColor: string;
  headerDividerColor: string;
  headerDividerThicknessPx: number;
  headerMarginBottomPx: number;
  headerPaddingBottomPx: number;
  roleMarginTopPx: number;
  bulletIndentPx: number;
  bulletListTopGapPx: number;
  bulletItemGapPx: number;
  tagGapPx: number;
  tagPaddingXPx: number;
  tagPaddingYPx: number;
  tagRadiusPx: number;
  tagBorderWidthPx: number;
  tagBorderColor: string;
  tagBgColor: string;
  sidebarPaddingPx: number;
  sidebarRadiusPx: number;
  leftSidebarBg: string;
  headerBgColor: string;
  headerTextColor: string;
  bodyTextColor: string;
  metaTextColor: string;
  nameFontWeight: number;
  contactLayout: ContactLayout;
  showPhoto: boolean;
  photoUrl: string;
  photoPreset: PhotoPreset;
  photoSize: number;
  photoWidthMm: number;
  photoHeightMm: number;
  photoPosition: PhotoPosition;
  photoShape: PhotoShape;
  compactLevel: 0 | 1 | 2 | 3 | 4;
  margins: GuidanceMargins;
}

export interface BuilderSectionDraft {
  id: string;
  key: string;
  title: string;
  visible: boolean;
  column: 'left' | 'right';
  page?: number;
}

export interface PageMeta {
  current: number;
  total: number;
}

export const DEFAULT_GUIDANCE: RenderGuidanceSettings = {
  pageFormat: 'A4',
  columnMode: 'double',
  pageCountMode: 'single-page',
  headerFont: 'serif',
  bodyFont: 'sans-serif',
  headerLayout: 'left',
  nameFontSizePx: 32,
  roleFontSizePx: 14,
  metaFontSizePx: 12,
  leftWidthPercent: 36,
  sectionGapPx: 18,
  bodyFontSizePx: 13,
  lineHeightPercent: 155,
  sectionHeadingSizePx: 12,
  sectionHeadingStyle: 'underline',
  sectionHeadingCase: 'uppercase',
  bulletStyle: 'disc',
  dateStyle: 'muted',
  columnGapPx: 16,
  itemGapPx: 10,
  showHeaderDivider: true,
  skillsLayout: 'horizontal',
  languagesLayout: 'horizontal',
  certificationsLayout: 'horizontal',
  awardsLayout: 'horizontal',
  tagFontSizePx: 10,
  headingMarginBottomPx: 8,
  sectionUnderlineGapPx: 4,
  sectionUnderlineThicknessPx: 1,
  contactGapPx: 4,
  accentColor: '#31457f',
  headerDividerColor: '#d1d1d1',
  headerDividerThicknessPx: 1,
  headerMarginBottomPx: 14,
  headerPaddingBottomPx: 8,
  roleMarginTopPx: 6,
  bulletIndentPx: 18,
  bulletListTopGapPx: 3,
  bulletItemGapPx: 6,
  tagGapPx: 6,
  tagPaddingXPx: 8,
  tagPaddingYPx: 2,
  tagRadiusPx: 12,
  tagBorderWidthPx: 1,
  tagBorderColor: '#e5e5e5',
  tagBgColor: '#f5f5f5',
  sidebarPaddingPx: 8,
  sidebarRadiusPx: 4,
  leftSidebarBg: '#fafafa',
  headerBgColor: '#ffffff',
  headerTextColor: '#1d1d1f',
  bodyTextColor: '#1d1d1f',
  metaTextColor: '#5f6b7a',
  nameFontWeight: 700,
  contactLayout: 'inline',
  showPhoto: false,
  photoUrl: '',
  photoPreset: 'one-inch',
  photoSize: 64,
  photoWidthMm: 25,
  photoHeightMm: 35,
  photoPosition: 'left',
  photoShape: 'rounded',
  compactLevel: 0,
  margins: { top: 12, bottom: 12, left: 12, right: 12 },
};

export const DEFAULT_SECTIONS: BuilderSectionDraft[] = [
  { id: 'summary', key: 'summary', title: 'Summary', visible: true, column: 'left', page: 1 },
  { id: 'workExperience', key: 'workExperience', title: 'Work Experience', visible: true, column: 'right', page: 1 },
  { id: 'education', key: 'education', title: 'Education', visible: true, column: 'right', page: 1 },
  { id: 'personalProjects', key: 'personalProjects', title: 'Projects', visible: true, column: 'right', page: 1 },
  { id: 'technicalSkills', key: 'technicalSkills', title: 'Skills', visible: true, column: 'left', page: 1 },
  { id: 'languages', key: 'languages', title: 'Languages', visible: true, column: 'left', page: 1 },
  { id: 'certifications', key: 'certifications', title: 'Certifications', visible: true, column: 'left', page: 1 },
  { id: 'awards', key: 'awards', title: 'Awards', visible: true, column: 'left', page: 1 },
];

export const PAGE_FORMAT_MM: Record<PageFormat, { width: number; height: number }> = {
  A4: { width: 210, height: 297 },
};

export const PX_PER_MM = 96 / 25.4;

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function mmToPx(mm: number): number {
  return mm * PX_PER_MM;
}
