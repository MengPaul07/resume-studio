import type { TemplateDefinition, TemplateField, TemplateSection, TypeScale } from './types';

function esc(text: string): string {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function tv(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return '';
}

function resolve(root: Record<string, unknown>, path: string): unknown {
  const parts = path.split('.');
  let cur: unknown = root;
  for (const part of parts) {
    const arr = part.match(/^(\w+)\[(\d+)\]$/);
    if (arr) {
      if (cur && typeof cur === 'object') cur = (cur as Record<string, unknown>)[arr[1]];
      cur = Array.isArray(cur) ? cur[parseInt(arr[2])] : undefined;
    } else {
      cur = cur && typeof cur === 'object' ? (cur as Record<string, unknown>)[part] : undefined;
    }
    if (cur === undefined || cur === null) return '';
  }
  return cur;
}

function tierClass(scale: TypeScale, tier: string): string {
  const t = scale[tier];
  if (!t) return '';
  const parts: string[] = [];
  if (t.weight === 'bold') parts.push('fw-bold');
  if (t.color === 'muted') parts.push('clr-muted');
  if (t.case === 'uppercase') parts.push('tt-upper');
  if (t.tracking === 'wide') parts.push('track-wide');
  return parts.join(' ');
}

function renderField(
  f: TemplateField,
  value: unknown,
  dataPath: string,
  scale: TypeScale,
): string {
  const cls = tierClass(scale, f.tier);
  const dp = dataPath ? ` data-path="${dataPath}"` : '';

  if (f.bullet && Array.isArray(value)) {
    const items = value
      .map((item, i) => `<li${dp && f.path ? ` data-path="${dataPath}[${i}]"` : ''}>${esc(tv(item))}</li>`)
      .join('');
    return items ? `<ul class="bullet-list">${items}</ul>` : '';
  }

  const prefix = f.prefix || '';
  const text = esc(tv(value));
  if (!text && f.hide_empty !== false) return '';

  if (f.inline) {
    return `<span class="${cls}"${dp}>${esc(prefix)}${text}</span>`;
  }
  return `<div class="${cls}"${dp}>${esc(prefix)}${text}</div>`;
}

function renderSingleSection(
  section: TemplateSection,
  resumeObj: Record<string, unknown>,
  scale: TypeScale,
): string {
  const parts: string[] = [];
  for (const f of section.fields) {
    const val = resolve(resumeObj, f.path);
    parts.push(renderField(f, val, f.path, scale));
  }
  return parts.filter(Boolean).join('');
}

function renderArraySection(
  section: TemplateSection,
  resumeObj: Record<string, unknown>,
  scale: TypeScale,
): string {
  const data = resolve(resumeObj, section.key);
  if (!Array.isArray(data) || !data.length) return '';

  const fields = section.item?.fields || section.fields;
  const spacing = section.item_spacing || 'md';
  const gap = { sm: 10, md: 14, lg: 20 }[spacing];

  const items = data.map((row, idx) => {
    const parts: string[] = [];
    for (const f of fields) {
      const val = resolve(row as Record<string, unknown>, f.path);
      const dp = section.key ? `${section.key}[${idx}].${f.path}` : '';
      parts.push(renderField(f, val, dp, scale));
    }
    const inner = parts.filter(Boolean).join('');
    return inner ? `<article class="resume-item" style="margin-bottom:${gap}px">${inner}</article>` : '';
  }).filter(Boolean);

  return items.length ? items.join('') : '';
}

function renderKeyValueSection(
  section: TemplateSection,
  resumeObj: Record<string, unknown>,
  scale: TypeScale,
): string {
  const layout = section.layout || 'list';
  const parts: string[] = [];
  for (const f of section.fields) {
    const val = resolve(resumeObj, f.path);
    if (layout === 'inline_tags' && Array.isArray(val)) {
      const tags = (val as unknown[]).map((item, i) =>
        `<span class="skill-tag" data-path="${f.path}[${i}]">${esc(tv(item))}</span>`).join('');
      if (tags) parts.push(`<div class="skill-cloud">${tags}</div>`);
    } else {
      parts.push(renderField(f, val, f.path, scale));
    }
  }
  return parts.filter(Boolean).join('');
}

function renderSection(
  section: TemplateSection,
  resumeObj: Record<string, unknown>,
  scale: TypeScale,
): string {
  let body = '';
  switch (section.type) {
    case 'single':
      body = renderSingleSection(section, resumeObj, scale);
      break;
    case 'array':
      body = renderArraySection(section, resumeObj, scale);
      break;
    case 'key_value':
      body = renderKeyValueSection(section, resumeObj, scale);
      break;
  }
  if (!body) return '';

  const title = section.title;
  const titleHtml = title
    ? `<h2 class="section-title ${tierClass(scale, section.title_tier || 'heading')}">${esc(title)}</h2>`
    : '';
  return `<section>${titleHtml}${body}</section>`;
}

export function renderTemplateHtml(
  template: TemplateDefinition,
  resumeObj: Record<string, unknown>,
): string {
  const sections = template.sections
    .map((s) => renderSection(s, resumeObj, template.type_scale))
    .filter(Boolean)
    .join('');
  return `<div class="resume-preview-content">${sections}</div>`;
}

export function buildTypeScaleCss(scale: TypeScale): string {
  return Object.entries(scale).map(([_tier, t]) => {
    const rules: string[] = [];
    // We apply tier classes to elements directly in HTML — this is for fallback
    return '';
  }).join('');
}
