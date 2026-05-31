import { buildLayoutPlanFromGuidance } from './layout-plan';
import { mmToPx, PAGE_FORMAT_MM, type BuilderSectionDraft, type RenderGuidanceSettings } from './types';

function toText(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) return value.map(toText).filter(Boolean).join(', ');
  return '';
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function bulletsToHtml(
  items: unknown[],
  bulletStyle: RenderGuidanceSettings['bulletStyle'],
  layoutMode: 'vertical' | 'horizontal',
  basePath?: string,
): string {
  const rows = (Array.isArray(items) ? items : [])
    .map((item) => escapeHtml(toText(item).trim()))
    .filter(Boolean);
  if (!rows.length) return '';
  if (layoutMode === 'horizontal') {
    return `<div class="inline-tags">${rows.map((row, i) => `<span class="tag-item"${basePath ? ` data-path="${basePath}[${i}]"` : ''}>${row}</span>`).join('')}</div>`;
  }
  return `<ul class="bullet-${bulletStyle}">${rows.map((row, i) => `<li${basePath ? ` data-path="${basePath}[${i}]"` : ''}>${row}</li>`).join('')}</ul>`;
}

function sectionTitleMap(sections: BuilderSectionDraft[]): Record<string, string> {
  return sections.reduce<Record<string, string>>((acc, item) => {
    acc[item.key] = item.title;
    return acc;
  }, {});
}

function renderSectionByKey(
  key: string,
  resumeObj: Record<string, unknown>,
  titleMap: Record<string, string>,
  guidance: RenderGuidanceSettings,
): string {
  const title = escapeHtml(titleMap[key] || key);
  if (key === 'summary') {
    const summary = escapeHtml(toText(resumeObj.summary));
    return summary ? `<section><h2>${title}</h2><p data-path="summary">${summary}</p></section>` : '';
  }
  if (key === 'workExperience') {
    const rows = (Array.isArray(resumeObj.workExperience) ? resumeObj.workExperience : [])
      .map((item, idx) => {
        const row = (item || {}) as Record<string, unknown>;
        const role = escapeHtml(toText(row.title));
        const company = escapeHtml(toText(row.company));
        const location = escapeHtml(toText(row.location));
        const years = escapeHtml(toText(row.years));
        const isBottom = guidance.dateStyle === 'bottom-inline';
        const header = [role, company].filter(Boolean).join(' · ');
        const bullets = bulletsToHtml(row.description as unknown[], guidance.bulletStyle, 'vertical', `workExperience[${idx}].description`);
        if (!header && !years && !bullets && !location) return '';
        // Company + location on one line, years on the right in bottom-inline
        const companyLine = [company, location].filter(Boolean).join(' · ');
        const metaLine = isBottom && years
          ? `<p class="meta">${companyLine || ''}<span class="meta" data-path="workExperience[${idx}].years">${years}</span></p>`
          : isBottom && companyLine
            ? `<p class="meta">${companyLine}</p>`
            : !isBottom
              ? [companyLine ? `<p class="meta">${companyLine}</p>` : '', years ? `<p class="meta" data-path="workExperience[${idx}].years">${years}</p>` : ''].filter(Boolean).join('')
              : '';
        return `<article class="resume-item"><div class="item-head"><h3 data-path="workExperience[${idx}].title">${role || 'Role'}</h3>${metaLine}</div>${bullets}</article>`;
      })
      .filter(Boolean)
      .join('');
    return rows ? `<section><h2>${title}</h2>${rows}</section>` : '';
  }
  if (key === 'personalProjects') {
    const rows = (Array.isArray(resumeObj.personalProjects) ? resumeObj.personalProjects : [])
      .map((item, idx) => {
        const row = (item || {}) as Record<string, unknown>;
        const name = escapeHtml(toText(row.name) || toText(row.title));
        const role = escapeHtml(toText(row.role));
        const years = escapeHtml(toText(row.years));
        const isBottom = guidance.dateStyle === 'bottom-inline';
        const bullets = bulletsToHtml(row.description as unknown[], guidance.bulletStyle, 'vertical', `personalProjects[${idx}].description`);
        if (!name && !role && !years && !bullets) return '';
        if (isBottom) {
          const metaLine = `<p class="meta">${role || ''}${years ? `<span class="meta" data-path="personalProjects[${idx}].years">${years}</span>` : ''}</p>`;
          return `<article class="resume-item"><div class="item-head"><h3 data-path="personalProjects[${idx}].name">${name || 'Project'}</h3>${metaLine}</div>${bullets}</article>`;
        }
        return `<article class="resume-item"><div class="item-head"><h3 data-path="personalProjects[${idx}].name">${name || 'Project'}</h3><p class="meta" data-path="personalProjects[${idx}].role">${role || ''}</p>${years ? `<p class="meta" data-path="personalProjects[${idx}].years">${years}</p>` : ''}</div>${bullets}</article>`;
      })
      .filter(Boolean)
      .join('');
    return rows ? `<section><h2>${title}</h2>${rows}</section>` : '';
  }
  if (key === 'education') {
    const rows = (Array.isArray(resumeObj.education) ? resumeObj.education : [])
      .map((item, idx) => {
        const row = (item || {}) as Record<string, unknown>;
        const institution = escapeHtml(toText(row.institution));
        const degree = escapeHtml(toText(row.degree));
        const years = escapeHtml(toText(row.years));
        const gpa = escapeHtml(toText(row.gpa));
        const isBottom = guidance.dateStyle === 'bottom-inline';
        const desc = bulletsToHtml(row.description as unknown[], guidance.bulletStyle, 'vertical', `education[${idx}].description`);
        if (!institution && !degree && !years && !gpa && !desc) return '';
        if (isBottom) {
          const metaLine = `<p class="meta">${degree || ''}${years ? `<span class="meta" data-path="education[${idx}].years">${years}</span>` : ''}</p>${gpa ? `<p class="meta" data-path="education[${idx}].gpa">GPA: ${gpa}</p>` : ''}`;
          return `<article class="resume-item"><div class="item-head"><h3 data-path="education[${idx}].institution">${institution || 'Institution'}</h3>${metaLine}</div>${desc}</article>`;
        }
        return `<article class="resume-item"><div class="item-head"><h3 data-path="education[${idx}].institution">${institution || 'Institution'}</h3><p class="meta" data-path="education[${idx}].degree">${degree || ''}</p>${years ? `<p class="meta" data-path="education[${idx}].years">${years}</p>` : ''}${gpa ? `<p class="meta" data-path="education[${idx}].gpa">GPA: ${gpa}</p>` : ''}</div>${desc}</article>`;
      })
      .filter(Boolean)
      .join('');
    return rows ? `<section><h2>${title}</h2>${rows}</section>` : '';
  }
  if (key === 'research') {
    const rows = (Array.isArray(resumeObj.research) ? resumeObj.research : [])
      .map((item, idx) => {
        const row = (item || {}) as Record<string, unknown>;
        const name = escapeHtml(toText(row.name));
        const role = escapeHtml(toText(row.role));
        const institution = escapeHtml(toText(row.institution));
        const years = escapeHtml(toText(row.years));
        const isBottom = guidance.dateStyle === 'bottom-inline';
        const bullets = bulletsToHtml(row.description as unknown[], guidance.bulletStyle, 'vertical', `research[${idx}].description`);
        if (!name && !role && !institution && !years && !bullets) return '';
        if (isBottom) {
          const metaLine = `<p class="meta">${institution || ''}${years ? `<span class="meta" data-path="research[${idx}].years">${years}</span>` : ''}</p>`;
          return `<article class="resume-item"><div class="item-head"><h3 data-path="research[${idx}].name">${name || 'Research'}</h3><p class="meta" data-path="research[${idx}].role">${role || ''}</p>${metaLine}</div>${bullets}</article>`;
        }
        return `<article class="resume-item"><div class="item-head"><h3 data-path="research[${idx}].name">${name || 'Research'}</h3><p class="meta" data-path="research[${idx}].role">${role || ''}</p><p class="meta" data-path="research[${idx}].institution">${institution || ''}</p>${years ? `<p class="meta" data-path="research[${idx}].years">${years}</p>` : ''}</div>${bullets}</article>`;
      })
      .filter(Boolean)
      .join('');
    return rows ? `<section><h2>${title}</h2>${rows}</section>` : '';
  }
  // Normalize: coerce flat strings to arrays for additional fields
  const ensureArray = (val: unknown): unknown[] => {
    if (Array.isArray(val)) return val;
    if (typeof val === 'string' && val.trim()) {
      return val.split(/[,;，；\n]+/).map(s => s.trim()).filter(Boolean);
    }
    return [];
  };

  if (key === 'technicalSkills') {
    const skills = ensureArray((resumeObj.additional as Record<string, unknown> | undefined)?.technicalSkills);
    const html = bulletsToHtml(skills, guidance.bulletStyle, guidance.skillsLayout);
    return html ? `<section><h2>${title}</h2>${html}</section>` : '';
  }
  if (key === 'languages') {
    const langs = ensureArray((resumeObj.additional as Record<string, unknown> | undefined)?.languages);
    const html = bulletsToHtml(langs, guidance.bulletStyle, guidance.languagesLayout);
    return html ? `<section><h2>${title}</h2>${html}</section>` : '';
  }
  if (key === 'certifications') {
    const certs = ensureArray((resumeObj.additional as Record<string, unknown> | undefined)?.certificationsTraining);
    const html = bulletsToHtml(certs, guidance.bulletStyle, guidance.certificationsLayout);
    return html ? `<section><h2>${title}</h2>${html}</section>` : '';
  }
  if (key === 'awards') {
    const awards = ensureArray((resumeObj.additional as Record<string, unknown> | undefined)?.awards);
    const html = bulletsToHtml(awards, guidance.bulletStyle, guidance.awardsLayout);
    return html ? `<section><h2>${title}</h2>${html}</section>` : '';
  }
  // Generic fallback: look up the key directly from resumeObj, additional, or customSections
  const fromRoot = resumeObj[key];
  if (fromRoot !== undefined) {
    if (Array.isArray(fromRoot)) {
      const html = bulletsToHtml(fromRoot as unknown[], guidance.bulletStyle, 'vertical');
      return html ? `<section><h2>${title}</h2>${html}</section>` : '';
    }
    const text = escapeHtml(toText(fromRoot));
    return text ? `<section><h2>${title}</h2><p>${text}</p></section>` : '';
  }
  const fromAdditional = (resumeObj.additional as Record<string, unknown> | undefined)?.[key];
  if (fromAdditional !== undefined) {
    if (Array.isArray(fromAdditional)) {
      const html = bulletsToHtml(fromAdditional as unknown[], guidance.bulletStyle, 'vertical');
      return html ? `<section><h2>${title}</h2>${html}</section>` : '';
    }
    const text = escapeHtml(toText(fromAdditional));
    return text ? `<section><h2>${title}</h2><p>${text}</p></section>` : '';
  }
  const customSections = (resumeObj.customSections as Record<string, unknown> | undefined) || {};
  const customSection = customSections[key] as Record<string, unknown> | undefined;
  if (customSection) {
    const sectionType = String(customSection.sectionType || 'text');
    const items = Array.isArray(customSection.items) ? customSection.items as unknown[] : [];
    const text = String(customSection.text || '');
    if (sectionType === 'list' && items.length) {
      const html = bulletsToHtml(items, guidance.bulletStyle, 'vertical');
      return html ? `<section><h2>${title}</h2>${html}</section>` : '';
    }
    if (text) {
      return `<section><h2>${title}</h2><p>${escapeHtml(text)}</p></section>`;
    }
  }
  return '';
}

// Compact spacing multipliers: 0=off 1=slight 2=moderate 3=tight 4=ultra
const COMPACT_SP = [1, 0.85, 0.70, 0.55, 0.40] as const;
const COMPACT_LH = [1, 0.97, 0.92, 0.88, 0.85] as const;

function fontStack(key: 'headerFont' | 'bodyFont', value: string): string {
  if (value === 'serif') return 'Georgia, serif';
  if (value === 'mono') return '"Space Grotesk", monospace';
  return '"Inter", "Segoe UI", sans-serif';
}

interface CssVarInput {
  raw: RenderGuidanceSettings;
  pagePadding: number;
  contentWidthPx: number;
  columnGapPx: number;
  leftBasisPx: number;
}

function buildCssVariables(inp: CssVarInput): string {
  const r = inp.raw;
  const csp = COMPACT_SP[r.compactLevel];
  const clh = COMPACT_LH[r.compactLevel];
  const sp = (px: number) => Math.round(px * csp);
  const lp = (pct: number) => Math.round(pct * clh);

  const headingCase = r.sectionHeadingCase === 'uppercase' ? 'uppercase' : 'none';
  const headingLs = r.sectionHeadingCase === 'uppercase' ? '.08em' : '.02em';
  const photoRadius = r.photoShape === 'circle' ? '50%' : r.photoShape === 'rounded' ? '8px' : '0';
  const photoPreset = r.photoPreset || 'one-inch';
  const photoWidth = photoPreset === 'custom-square' ? `${r.photoSize}px` : `${r.photoWidthMm || 25}mm`;
  const photoHeight = photoPreset === 'custom-square' ? `${r.photoSize}px` : `${r.photoHeightMm || 35}mm`;

  return [
    `--r-page-padding: ${inp.pagePadding}px;`,
    `--r-body-font: ${fontStack('bodyFont', r.bodyFont)};`,
    `--r-header-font: ${fontStack('headerFont', r.headerFont)};`,
    `--r-body-color: ${r.bodyTextColor};`,
    `--r-meta-color: ${r.metaTextColor};`,
    `--r-accent: ${r.accentColor};`,
    `--r-accent-muted: #e5e5e5;`,
    `--r-header-bg: ${r.headerBgColor};`,
    `--r-header-color: ${r.headerTextColor};`,
    `--r-sidebar-bg: ${r.leftSidebarBg};`,
    `--r-divider-color: ${r.headerDividerColor};`,
    `--r-divider-thick: ${r.headerDividerThicknessPx}px;`,
    `--r-tag-border: ${r.tagBorderColor};`,
    `--r-tag-bg: ${r.tagBgColor};`,
    `--r-name-size: ${r.nameFontSizePx}px;`,
    `--r-name-weight: ${r.nameFontWeight};`,
    `--r-role-size: ${r.roleFontSizePx}px;`,
    `--r-meta-size: ${r.metaFontSizePx}px;`,
    `--r-body-size: ${r.bodyFontSizePx}px;`,
    `--r-line-height: ${lp(r.lineHeightPercent) / 100};`,
    `--r-section-gap: ${sp(r.sectionGapPx)}px;`,
    `--r-item-gap: ${sp(r.itemGapPx)}px;`,
    `--r-heading-size: ${r.sectionHeadingSizePx}px;`,
    `--r-heading-margin: ${sp(r.headingMarginBottomPx)}px;`,
    `--r-heading-rule-gap: ${sp(r.sectionUnderlineGapPx)}px;`,
    `--r-heading-rule-thick: ${r.sectionUnderlineThicknessPx}px;`,
    `--r-heading-case: ${headingCase};`,
    `--r-heading-ls: ${headingLs};`,
    `--r-header-margin: ${sp(r.headerMarginBottomPx)}px;`,
    `--r-header-pad: ${sp(r.headerPaddingBottomPx)}px;`,
    `--r-role-mt: ${sp(r.roleMarginTopPx)}px;`,
    `--r-contact-gap: ${sp(r.contactGapPx)}px;`,
    `--r-col-gap: ${sp(inp.columnGapPx)}px;`,
    `--r-left-basis: ${inp.leftBasisPx}px;`,
    `--r-bullet-top-gap: ${sp(r.bulletListTopGapPx)}px;`,
    `--r-bullet-gap: ${sp(r.bulletItemGapPx)}px;`,
    `--r-bullet-indent: ${r.bulletIndentPx}px;`,
    `--r-tag-gap: ${sp(r.tagGapPx)}px;`,
    `--r-tag-size: ${r.tagFontSizePx}px;`,
    `--r-tag-pad-x: ${r.tagPaddingXPx}px;`,
    `--r-tag-pad-y: ${r.tagPaddingYPx}px;`,
    `--r-tag-radius: ${r.tagRadiusPx}px;`,
    `--r-tag-border-width: ${r.tagBorderWidthPx}px;`,
    `--r-sidebar-pad: ${sp(r.sidebarPaddingPx)}px;`,
    `--r-sidebar-radius: ${r.sidebarRadiusPx}px;`,
    `--r-photo-width: ${photoWidth};`,
    `--r-photo-height: ${photoHeight};`,
    `--r-photo-radius: ${photoRadius};`,
  ].join('\n    ');
}

export function renderResumeHtmlFromLayout(params: {
  resumeObj: Record<string, unknown>;
  guidance: RenderGuidanceSettings;
  sections: BuilderSectionDraft[];
}): string {
  const { resumeObj, sections, guidance: raw } = params;
  const titleMap = sectionTitleMap(sections);
  const layout = buildLayoutPlanFromGuidance(raw, sections) as Record<string, unknown>;
  const page = (layout.page || {}) as Record<string, unknown>;
  const sectionMap = (layout.section_map || {}) as { left?: string[]; right?: string[] };
  const isDouble = raw.columnMode === 'double';
  const leftWidth = raw.leftWidthPercent;

  const personalInfo = (resumeObj.personalInfo || {}) as Record<string, unknown>;
  const name = escapeHtml(toText(personalInfo.name) || 'Your Name');
  const role = escapeHtml(toText(personalInfo.title));
  const email = escapeHtml(toText(personalInfo.email));
  const phone = escapeHtml(toText(personalInfo.phone));
  const location = escapeHtml(toText(personalInfo.location));
  const website = escapeHtml(toText(personalInfo.website));
  const linkedin = escapeHtml(toText(personalInfo.linkedin));
  const github = escapeHtml(toText(personalInfo.github));
  const contacts = [email, phone, location].filter(Boolean);
  const links = [website, linkedin, github].filter(Boolean);
  const stackedMeta = raw.contactLayout === 'stacked'
    ? [...contacts, ...links].map(t => `<p class="meta">${t}</p>`).join('\n      ')
    : '';
  const inlineMeta = raw.contactLayout === 'inline'
    ? [
        contacts.length ? `<p class="meta">${contacts.join(' · ')}</p>` : '',
        links.length ? `<p class="meta">${links.join(' · ')}</p>` : '',
      ].filter(Boolean).join('\n      ')
    : '';
  const metaHtml = raw.contactLayout === 'stacked' ? stackedMeta : inlineMeta;

  const photoPlaceholder = 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="133" fill="none"><rect width="100" height="133" rx="4" fill="#e8e8e8"/><circle cx="50" cy="52" r="24" fill="#bbb"/><path d="M14 133 Q14 97 50 97 Q86 97 86 133" fill="#bbb"/></svg>'
  );
  const photoSrc = raw.showPhoto ? (raw.photoUrl || photoPlaceholder) : '';
  const headerHasPhoto = raw.showPhoto;
  const headerFlexClass = headerHasPhoto ? 'header-with-photo' : '';
  const headerLayout = raw.headerLayout;
  const isSplitHeader = headerLayout === 'split';

  const headerHtml = isSplitHeader
    ? `<header class="header-split">
      <div class="header-left">
        ${headerHasPhoto && raw.photoPosition === 'left' ? `<img class="header-photo" src="${escapeHtml(photoSrc)}" alt="photo" />` : ''}
        <h1>${name}</h1>
        ${role ? `<p class="role">${role}</p>` : ''}
      </div>
      <div class="header-right">
        ${contacts.map(t => `<p class="meta">${t}</p>`).join('\n        ')}
        ${links.map(t => `<p class="meta">${t}</p>`).join('\n        ')}
      </div>
    </header>`
    : `<header class="${headerFlexClass}">
      ${headerHasPhoto && raw.photoPosition === 'left' ? `<img class="header-photo photo-${raw.photoPosition}" src="${escapeHtml(photoSrc)}" alt="photo" />` : ''}
      <div class="header-text">
        <h1>${name}</h1>
        ${role ? `<p class="role">${role}</p>` : ''}
        ${metaHtml}
      </div>
      ${headerHasPhoto && raw.photoPosition === 'right' ? `<img class="header-photo photo-${raw.photoPosition}" src="${escapeHtml(photoSrc)}" alt="photo" />` : ''}
    </header>`;

  const orderedVisible = sections.filter((item) => item.visible).map((item) => item.key);
  const leftKeys = isDouble ? (sectionMap.left || []) : [];
  const rightKeys = isDouble ? (sectionMap.right || []) : orderedVisible;
  const allKeys = isDouble ? [] : orderedVisible;

  const renderSectionsWithKeys = (keys: string[]) =>
    keys
      .map((key) => ({
        key,
        html: renderSectionByKey(key, resumeObj, titleMap, raw),
      }))
      .filter((s) => s.html);

  const leftSections = renderSectionsWithKeys(leftKeys);
  const rightSections = renderSectionsWithKeys(rightKeys);
  const singleSections = renderSectionsWithKeys(allKeys);

  const dateClass = raw.dateStyle === 'inline' ? 'is-inline-date'
    : raw.dateStyle === 'bottom-inline' ? 'is-bottom-inline' : '';

  const pagePadding = Math.round(mmToPx(Math.min(raw.margins.top, raw.margins.left)));
  const pageWidthPx = mmToPx(PAGE_FORMAT_MM[raw.pageFormat].width);
  const contentWidthPx = Math.max(320, pageWidthPx - pagePadding * 2);
  const columnGapPx = raw.columnGapPx;
  const leftBasisPx = Math.max(120, Math.round(((contentWidthPx - columnGapPx) * leftWidth) / 100));

  const headingStyleClass = `r-sec-${raw.sectionHeadingStyle}`;
  const headerBorderStyle = raw.showHeaderDivider
    ? `border-bottom: var(--r-divider-thick) solid var(--r-divider-color);`
    : 'border-bottom: none;';
  const headerJustify = headerLayout === 'center' ? 'center' : 'flex-start';
  const headerTextAlign = headerLayout === 'center' ? 'center' : 'left';
  const pageClass = (extra = '') => [headingStyleClass, extra].filter(Boolean).join(' ');

  // Group sections by page number (default 1), then render one <main> per page
  const groupByPage = (items: { key: string; html: string }[]) => {
    const map = new Map<number, string[]>();
    for (const item of items) {
      const p = sections.find(s => s.key === item.key)?.page ?? 1;
      if (!map.has(p)) map.set(p, []);
      map.get(p)!.push(item.html);
    }
    return map;
  };

  let bodyHtml: string;
  if (isDouble) {
    const leftMap = groupByPage(leftSections);
    const rightMap = groupByPage(rightSections);
    const allPages = new Set([...leftMap.keys(), ...rightMap.keys()]);
    bodyHtml = [...allPages]
      .sort((a, b) => a - b)
      .map((p, i) => {
        const left = (leftMap.get(p) || []).join('\n');
        const right = (rightMap.get(p) || []).join('\n');
        return `<main class="page ${headingStyleClass}">${i === 0 ? headerHtml : ''}
    <section class="layout-double ${dateClass}"><aside>${left}</aside><section>${right}</section></section>
  </main>`;
      })
      .join('\n');
  } else {
    const map = groupByPage(singleSections);
    bodyHtml = [...map.keys()]
      .sort((a, b) => a - b)
      .map((p, i) => `<main class="page ${pageClass(dateClass)}">${i === 0 ? headerHtml : ''}${(map.get(p) || []).join('\n')}</main>`)
      .join('\n');
  }

  const cssVars = buildCssVariables({ raw, pagePadding, contentWidthPx, columnGapPx, leftBasisPx });

  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${name} - Resume</title>
  <style>
    :root {
    ${cssVars}
    }
    @page { size: A4; margin: 0; }
    * { box-sizing: border-box; }
    body { margin: 0; color: var(--r-body-color); background: #fafafa; font-family: var(--r-body-font); }
    .page { width: 210mm; min-height: 297mm; margin: 0 auto 12px; background: #ffffff; padding: var(--r-page-padding); overflow-wrap: anywhere; }
    @media print { .page { margin: 0; page-break-after: always; } .page:last-child { page-break-after: auto; } }
    header { ${headerBorderStyle} position: relative; box-sizing: content-box; margin: 0 calc(-1 * var(--r-page-padding)) var(--r-header-margin); padding: calc(var(--r-page-padding) / 2) var(--r-page-padding); text-align: ${headerTextAlign}; background: var(--r-header-bg); color: var(--r-header-color); }
    .header-photo { width: var(--r-photo-width); height: var(--r-photo-height); border-radius: var(--r-photo-radius); object-fit: cover; }
    .header-photo.photo-left { position: absolute; left: var(--r-page-padding); top: 50%; transform: translateY(-50%); }
    .header-photo.photo-right { position: absolute; right: var(--r-page-padding); top: 50%; transform: translateY(-50%); }
    .header-text { }
    .header-split { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding-bottom: var(--r-header-pad); }
    .header-split .header-left { flex: 0 1 auto; }
    .header-split .header-right { flex: 0 0 auto; text-align: right; }
    h1 { margin: 0; font-size: var(--r-name-size); line-height: 1.2; font-weight: var(--r-name-weight); font-family: var(--r-header-font); }
    .role { margin: var(--r-role-mt) 0 0; font-size: var(--r-role-size); color: var(--r-header-color); opacity: 0.7; }
    .meta { margin: var(--r-contact-gap) 0 0; font-size: var(--r-meta-size); color: var(--r-meta-color); }
    h2 { margin: 0 0 var(--r-heading-margin); font-size: var(--r-heading-size); letter-spacing: var(--r-heading-ls); text-transform: var(--r-heading-case); color: var(--r-accent); }
    .r-sec-underline h2 { border-bottom: var(--r-heading-rule-thick) solid var(--r-accent-muted); padding-bottom: var(--r-heading-rule-gap); }
    .r-sec-bar h2 { border-left: 3px solid var(--r-accent); padding-left: 8px; }
    .r-sec-boxed h2 { border: 1px solid var(--r-accent-muted); padding: 3px 6px; background: #f5f5f5; }
    h3 { margin: 0; font-size: 14px; line-height: 1.4; }
    section { margin-bottom: var(--r-section-gap); }
    article { margin-bottom: var(--r-item-gap); }
    p, li { margin: 0; font-size: var(--r-body-size); line-height: var(--r-line-height); }
    ul { margin: var(--r-bullet-top-gap) 0 0 var(--r-bullet-indent); padding: 0; list-style-type: disc; }
    li + li { margin-top: var(--r-bullet-gap); }
    ul.bullet-square { list-style-type: square; }
    ul.bullet-dash { list-style: none; margin-left: 0; }
    ul.bullet-dash li { position: relative; padding-left: 14px; }
    ul.bullet-dash li::before { content: '—'; position: absolute; left: 0; color: var(--r-accent); }
    .inline-tags { display: flex; flex-wrap: wrap; gap: var(--r-tag-gap); }
    .tag-item { display: inline-flex; align-items: center; border: var(--r-tag-border-width) solid var(--r-tag-border); background: var(--r-tag-bg); padding: var(--r-tag-pad-y) var(--r-tag-pad-x); border-radius: var(--r-tag-radius); font-size: var(--r-tag-size); }
    .item-head { display: block; }
    .is-inline-date .item-head { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }
    .is-inline-date .item-head .meta { margin: 0; white-space: nowrap; }
    .is-bottom-inline .item-head { display: block; }
    .is-bottom-inline .item-head > .meta { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
    .is-bottom-inline .item-head > .meta > .meta { margin: 0; white-space: nowrap; }
    .layout-double { display: flex; align-items: flex-start; gap: var(--r-col-gap); }
    .layout-double > aside { flex: 0 0 var(--r-left-basis); min-width: 0; background: var(--r-sidebar-bg); padding: var(--r-sidebar-pad); border-radius: var(--r-sidebar-radius); }
    .layout-double > section { flex: 1 1 0; min-width: 0; }
  </style>
</head>
<body>
${
  bodyHtml
}
</body>
</html>`;
}
