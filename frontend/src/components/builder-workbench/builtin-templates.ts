import {
  DEFAULT_GUIDANCE,
  DEFAULT_SECTIONS,
  type BuilderSectionDraft,
  type RenderGuidanceSettings,
} from './types';

export interface BuiltinBuilderTemplate {
  id: string;
  name: string;
  description: string;
  meta: string;
  swatch: string;
  guidance: RenderGuidanceSettings;
  sections: BuilderSectionDraft[];
}

function cloneGuidance(overrides: Partial<RenderGuidanceSettings>): RenderGuidanceSettings {
  return {
    ...DEFAULT_GUIDANCE,
    ...overrides,
    margins: {
      ...DEFAULT_GUIDANCE.margins,
      ...(overrides.margins || {}),
    },
  };
}

function cloneSections(overrides: Partial<Record<string, Partial<BuilderSectionDraft>>> = {}): BuilderSectionDraft[] {
  return DEFAULT_SECTIONS.map((section) => ({
    ...section,
    ...(overrides[section.key] || {}),
  }));
}

function sectionsInOrder(keys: string[], overrides: Partial<Record<string, Partial<BuilderSectionDraft>>> = {}): BuilderSectionDraft[] {
  const byKey = new Map(DEFAULT_SECTIONS.map((section) => [section.key, section]));
  return keys
    .map((key) => byKey.get(key))
    .filter(Boolean)
    .map((section) => ({
      ...section!,
      ...(overrides[section!.key] || {}),
    }));
}

export const BUILTIN_BUILDER_TEMPLATES: BuiltinBuilderTemplate[] = [
  {
    id: 'swiss-single',
    name: 'Swiss Two Column',
    description: 'Balanced sidebar layout for modern software and product resumes.',
    meta: 'A4 | Double column | Tags',
    swatch: '#31457f',
    guidance: cloneGuidance({}),
    sections: cloneSections(),
  },
  {
    id: 'classic-editorial',
    name: 'Classic Editorial',
    description: 'A calm single-column layout with serif headings and traditional section rhythm.',
    meta: 'A4 | Single column | Serif',
    swatch: '#5b4636',
    guidance: cloneGuidance({
      columnMode: 'single',
      headerLayout: 'center',
      headerFont: 'serif',
      bodyFont: 'serif',
      sectionHeadingStyle: 'bar',
      sectionHeadingCase: 'title',
      dateStyle: 'inline',
      bulletStyle: 'disc',
      skillsLayout: 'horizontal',
      languagesLayout: 'horizontal',
      certificationsLayout: 'horizontal',
      awardsLayout: 'horizontal',
      accentColor: '#5b4636',
      headerDividerColor: '#d8d0c4',
      tagBgColor: '#fbfaf7',
      tagBorderColor: '#d8d0c4',
      leftSidebarBg: '#ffffff',
      sectionGapPx: 16,
      itemGapPx: 9,
      bodyFontSizePx: 13,
      lineHeightPercent: 150,
      margins: { top: 14, bottom: 14, left: 15, right: 15 },
    }),
    sections: sectionsInOrder([
      'summary',
      'workExperience',
      'education',
      'personalProjects',
      'research',
      'technicalSkills',
      'certifications',
      'awards',
      'languages',
    ]),
  },
  {
    id: 'compact-engineer',
    name: 'Compact Engineer',
    description: 'Dense one-page engineering resume with tighter spacing and fast-scanning tags.',
    meta: 'A4 | Compact | Technical',
    swatch: '#0f766e',
    guidance: cloneGuidance({
      compactLevel: 2,
      leftWidthPercent: 32,
      columnGapPx: 12,
      sectionGapPx: 12,
      itemGapPx: 6,
      bodyFontSizePx: 12,
      lineHeightPercent: 136,
      headingMarginBottomPx: 5,
      sectionUnderlineGapPx: 2,
      bulletListTopGapPx: 2,
      bulletItemGapPx: 3,
      bulletIndentPx: 16,
      tagFontSizePx: 9,
      tagGapPx: 4,
      tagPaddingXPx: 6,
      tagPaddingYPx: 1,
      tagRadiusPx: 6,
      dateStyle: 'bottom-inline',
      accentColor: '#0f766e',
      headerDividerColor: '#cbd5e1',
      leftSidebarBg: '#f8fafc',
      tagBgColor: '#ecfdf5',
      tagBorderColor: '#99f6e4',
      margins: { top: 10, bottom: 10, left: 10, right: 10 },
    }),
    sections: sectionsInOrder(
      ['summary', 'technicalSkills', 'languages', 'certifications', 'awards', 'workExperience', 'personalProjects', 'education', 'research'],
      {
        summary: { column: 'left' },
        technicalSkills: { column: 'left' },
        languages: { column: 'left' },
        certifications: { column: 'left' },
        awards: { column: 'left' },
        workExperience: { column: 'right' },
        personalProjects: { column: 'right' },
        education: { column: 'right' },
        research: { column: 'right', visible: false },
      },
    ),
  },
  {
    id: 'executive-profile',
    name: 'Executive Profile',
    description: 'Spacious profile-led layout for senior candidates, leadership, and consulting roles.',
    meta: 'A4 | Split header | Polished',
    swatch: '#1f2937',
    guidance: cloneGuidance({
      columnMode: 'single',
      headerLayout: 'split',
      headerFont: 'serif',
      bodyFont: 'sans-serif',
      nameFontSizePx: 38,
      roleFontSizePx: 15,
      bodyFontSizePx: 13,
      lineHeightPercent: 148,
      sectionHeadingStyle: 'underline',
      sectionHeadingCase: 'uppercase',
      dateStyle: 'inline',
      bulletStyle: 'dash',
      contactLayout: 'stacked',
      accentColor: '#1f2937',
      headerBgColor: '#f8fafc',
      headerDividerColor: '#94a3b8',
      tagRadiusPx: 2,
      tagBgColor: '#f8fafc',
      tagBorderColor: '#cbd5e1',
      sectionGapPx: 18,
      itemGapPx: 10,
      headerPaddingBottomPx: 14,
      headerMarginBottomPx: 18,
      margins: { top: 12, bottom: 13, left: 16, right: 16 },
    }),
    sections: sectionsInOrder([
      'summary',
      'workExperience',
      'personalProjects',
      'education',
      'technicalSkills',
      'certifications',
      'awards',
      'languages',
      'research',
    ]),
  },
  {
    id: 'academic-research',
    name: 'Academic Research',
    description: 'Research-first layout for professors, PhD candidates, labs, and publications-heavy profiles.',
    meta: 'A4 | Research-first | Two pages',
    swatch: '#6d28d9',
    guidance: cloneGuidance({
      pageCountMode: 'double-page',
      columnMode: 'single',
      headerLayout: 'left',
      headerFont: 'serif',
      bodyFont: 'serif',
      sectionHeadingStyle: 'boxed',
      sectionHeadingCase: 'title',
      dateStyle: 'muted',
      bulletStyle: 'disc',
      skillsLayout: 'vertical',
      certificationsLayout: 'vertical',
      awardsLayout: 'vertical',
      nameFontSizePx: 34,
      bodyFontSizePx: 13,
      lineHeightPercent: 152,
      accentColor: '#6d28d9',
      headerDividerColor: '#ddd6fe',
      tagBgColor: '#faf5ff',
      tagBorderColor: '#ddd6fe',
      sectionGapPx: 17,
      itemGapPx: 10,
      margins: { top: 14, bottom: 14, left: 15, right: 15 },
    }),
    sections: sectionsInOrder(
      ['summary', 'research', 'education', 'workExperience', 'personalProjects', 'technicalSkills', 'awards', 'certifications', 'languages'],
      {
        research: { visible: true, title: 'Research Experience', page: 1 },
        education: { page: 1 },
        workExperience: { page: 1 },
        personalProjects: { title: 'Selected Projects', page: 2 },
        technicalSkills: { title: 'Methods & Skills', page: 2 },
        awards: { page: 2 },
        certifications: { page: 2 },
        languages: { page: 2 },
      },
    ),
  },
];

export function getBuiltinBuilderTemplate(id: string): BuiltinBuilderTemplate | undefined {
  return BUILTIN_BUILDER_TEMPLATES.find((template) => template.id === id);
}
