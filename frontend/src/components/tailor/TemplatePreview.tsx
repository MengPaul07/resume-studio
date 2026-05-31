import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toDisplayText, displayLines, isPathMatch } from '../../lib/tailor/utils';
import { resolveFieldValue } from '../../lib/tailor/section-defs';
import { ChangeDetailPopover } from './ChangeDetailPopover';
import { isMultiLineField } from '../../lib/tailor/field-editor';
import type { PendingChange } from '../../lib/tailor/types';

interface Props {
  refinedResumeObj: Record<string, unknown>;
  pendingChanges: PendingChange[];
  changedPathSet: Set<string>;
  focusedChangePath: string;
  expandedChangePaths: Set<string>;
  changeVariantIndex: Record<string, number>;
  onToggleChangeDetail: (path: string) => void;
  onSwitchVariant: (path: string, variantIdx: number) => void;
  onFocusPath: (path: string) => void;
  onEditField?: (path: string, newValue: string) => void;
  previewAnchorRefs: React.MutableRefObject<Record<string, HTMLElement | null>>;
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-3 font-sans text-[11px] font-semibold tracking-[0.16em] text-gray-400 dark:text-gray-500 uppercase">
      {children}
    </h2>
  );
}

export function TemplatePreview({
  refinedResumeObj, pendingChanges, changedPathSet, focusedChangePath,
  expandedChangePaths, changeVariantIndex,
  onToggleChangeDetail, onSwitchVariant, onFocusPath, onEditField,
  previewAnchorRefs,
}: Props) {
  const { t } = useTranslation();
  // ── Inline edit state ────────────────────────────────────────────
  const [editingPath, setEditingPath] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState('');

  const startEdit = (path: string, currentText: string) => {
    setEditingPath(path);
    setEditingValue(currentText);
  };
  const saveEdit = () => {
    if (editingPath !== null && editingValue.trim() && onEditField) {
      onEditField(editingPath, editingValue.trim());
    }
    setEditingPath(null);
  };
  const cancelEdit = () => {
    setEditingPath(null);
  };

  const fc = (path: string) => path ? pendingChanges.find(c => isPathMatch(c.path, path)) || null : null;

  const RF = (path: string, value: unknown, as: 'p' | 'li' | 'div' | 'span' | 'h1' | 'h2' | 'h3' | 'h4' = 'p') => {
    const change = fc(path);
    const isC = Boolean(change);
    const isA = Boolean(change && focusedChangePath && isPathMatch(change.path, focusedChangePath));
    const isE = path ? expandedChangePaths.has(path) : false;
    const Tag = as;
    const displayText = toDisplayText(value) || t('resume.empty');

    const handleClick = () => {
      if (isC && change) {
        onToggleChangeDetail(change.path);
        onFocusPath(change.path);
      }
    };

    // ── Inline edit mode ─────────────────────────────────────────────
    if (editingPath === path) {
      const multiline = isMultiLineField(path);
      return (
        <div className="relative border-l-[3px] border-blue-400 dark:border-blue-600 pl-3 py-0.5 bg-blue-50/40 dark:bg-blue-900/20 rounded-r-md">
          {multiline ? (
            <textarea
              value={editingValue}
              onChange={e => setEditingValue(e.target.value)}
              onBlur={saveEdit}
              onKeyDown={e => {
                if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); }
              }}
              className="w-full resize-none rounded border border-blue-300 dark:border-blue-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm leading-relaxed text-gray-800 dark:text-gray-200 outline-none focus:ring-1 focus:ring-blue-400"
              rows={Math.max(2, editingValue.split('\n').length)}
              autoFocus
            />
          ) : (
            <input
              value={editingValue}
              onChange={e => setEditingValue(e.target.value)}
              onBlur={saveEdit}
              onKeyDown={e => {
                if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); }
                if (e.key === 'Enter') { e.preventDefault(); saveEdit(); }
              }}
              className="w-full rounded border border-blue-300 dark:border-blue-600 bg-white dark:bg-zinc-800 px-2 py-0.5 text-sm leading-relaxed text-gray-800 dark:text-zinc-100 outline-none focus:ring-1 focus:ring-blue-400"
              autoFocus
            />
          )}
          <span className="mt-1 block text-[10px] text-blue-400 dark:text-blue-300">{t('resume.editHint')}</span>
        </div>
      );
    }

    // ── Display mode ─────────────────────────────────────────────────
    return (
      <div>
        <div ref={el => { if (path) previewAnchorRefs.current[path] = el; }} data-path={path}
          onClick={handleClick}
          onDoubleClick={(e) => {
            e.stopPropagation();
            if (onEditField) startEdit(path, displayText === t('resume.empty') ? '' : displayText);
          }}
          className={`relative border-l-[3px] pl-3 py-0.5 transition-all duration-200 ${
            isA ? 'border-blue-500 dark:border-blue-400 bg-blue-50/60 dark:bg-blue-900/30 rounded-r-md' :
            isC ? 'border-blue-300 dark:border-blue-600 bg-blue-50/30 dark:bg-blue-900/15 rounded-r-md cursor-pointer' :
            'border-transparent'
          } ${onEditField ? 'group' : ''}`}>
          {isC && <span className={`absolute -top-0.5 -right-0.5 flex size-2.5 items-center justify-center rounded-full text-[7px] font-bold text-white ${isA ? 'bg-blue-600' : 'bg-blue-400'}`}>&bull;</span>}
          <Tag className="text-sm leading-relaxed text-gray-800 dark:text-gray-200">
            {displayText}
          </Tag>
          {onEditField && (
            <span className="ml-2 hidden text-[10px] text-gray-300 dark:text-gray-600 group-hover:inline">{t('resume.doubleClickEdit')}</span>
          )}
        </div>
        {isC && isE && change && <ChangeDetailPopover change={change} activeVariantIndex={changeVariantIndex[change.path] ?? 0} onSwitchVariant={onSwitchVariant} />}
      </div>
    );
  };

  // ── Additional badge renderer ────────────────────────────────────
  const BADGE_MAX_LEN = 40; // items longer than this switch to list mode
  const anyItemLong = (items: string[]) => items.some(it => it.length >= BADGE_MAX_LEN);

  const renderAdditionalBadges = (key: string, items: string[]) => {
    return (
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => {
          const path = `additional.${key}[${i}]`;
          const change = fc(path);
          // Only match exact path or children — skip if change targets the array root
          const isC = Boolean(change) && !change!.path.endsWith(key);
          const isA = isC && focusedChangePath && isPathMatch(change!.path, focusedChangePath);
          const isE = expandedChangePaths.has(path);

          // Edit mode for individual badge
          if (editingPath === path) {
            return (
              <span key={i} className="inline-flex items-center">
                <input
                  value={editingValue}
                  onChange={e => setEditingValue(e.target.value)}
                  onBlur={saveEdit}
                  onKeyDown={e => {
                    if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); }
                    if (e.key === 'Enter') { e.preventDefault(); saveEdit(); }
                  }}
                  className="w-28 rounded border border-blue-300 dark:border-blue-600 bg-white dark:bg-gray-800 px-2 py-0.5 text-xs text-gray-800 dark:text-gray-200 outline-none focus:ring-1 focus:ring-blue-400"
                  autoFocus
                />
              </span>
            );
          }

          return (
            <span key={i} className="relative inline-flex">
              <span
                ref={el => { previewAnchorRefs.current[path] = el; }}
                data-path={path}
                onClick={() => {
                  if (isC && change) {
                    onToggleChangeDetail(change.path);
                    onFocusPath(change.path);
                  }
                }}
                onDoubleClick={(e) => {
                  e.stopPropagation();
                  if (onEditField) startEdit(path, item || '');
                }}
                className={`relative inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-all ${
                  isA ? 'border-blue-400 dark:border-blue-600 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 shadow-sm' :
                  isC ? 'border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900/40' :
                  'border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300'
                } ${onEditField && !isC ? 'cursor-default' : ''}`}
              >
                {isC && <span className={`size-1.5 rounded-full ${isA ? 'bg-blue-600' : 'bg-blue-400'}`} />}
                {item}
              </span>
              {isC && isE && change && (
                <ChangeDetailPopover change={change} activeVariantIndex={changeVariantIndex[change.path] ?? 0} onSwitchVariant={onSwitchVariant} />
              )}
            </span>
          );
        })}
      </div>
    );
  };

  // ── Long-item list renderer (for entries that don't fit in badges) ─
  const renderAdditionalList = (key: string, items: string[]) => {
    return (
      <div className="space-y-1.5">
        {items.map((item, i) => {
          const path = `additional.${key}[${i}]`;
          const change = fc(path);
          // Only match exact path or children — skip if change targets the array root
          const isC = Boolean(change) && !change!.path.endsWith(key);
          const isA = isC && focusedChangePath && isPathMatch(change!.path, focusedChangePath);
          const isE = expandedChangePaths.has(path);

          // Edit mode
          if (editingPath === path) {
            return (
              <div key={i} className="relative border-l-[3px] border-blue-400 dark:border-blue-600 pl-3 py-0.5 bg-blue-50/40 rounded-r-md">
                <textarea
                  value={editingValue}
                  onChange={e => setEditingValue(e.target.value)}
                  onBlur={saveEdit}
                  onKeyDown={e => {
                    if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); }
                  }}
                  className="w-full resize-none rounded border border-blue-300 dark:border-blue-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm leading-relaxed text-gray-800 dark:text-gray-200 outline-none focus:ring-1 focus:ring-blue-400"
                  rows={Math.max(2, editingValue.split('\n').length)}
                  autoFocus
                />
                <span className="mt-1 block text-[10px] text-blue-400 dark:text-blue-300">{t('resume.editHint')}</span>
              </div>
            );
          }

          return (
            <div key={i}>
              <div
                ref={el => { previewAnchorRefs.current[path] = el; }}
                data-path={path}
                onClick={() => {
                  if (isC && change) {
                    onToggleChangeDetail(change.path);
                    onFocusPath(change.path);
                  }
                }}
                onDoubleClick={(e) => {
                  e.stopPropagation();
                  if (onEditField) startEdit(path, item || '');
                }}
                className={`relative border-l-[3px] pl-3 py-1 transition-all ${
                  isA ? 'border-blue-500 dark:border-blue-400 bg-blue-50/60 dark:bg-blue-900/30 rounded-r-md' :
                  isC ? 'border-blue-300 dark:border-blue-600 bg-blue-50/30 dark:bg-blue-900/15 rounded-r-md cursor-pointer' :
                  'border-gray-200 dark:border-gray-700'
                } ${onEditField && !isC ? 'group cursor-default' : ''}`}
              >
                {isC && <span className={`absolute -top-0.5 -right-0.5 flex size-2.5 items-center justify-center rounded-full text-[7px] font-bold text-white ${isA ? 'bg-blue-600' : 'bg-blue-400'}`}>&bull;</span>}
                <p className="text-sm leading-relaxed text-gray-800 dark:text-gray-200">{item}</p>
                {onEditField && !isC && (
                  <span className="ml-2 hidden text-[10px] text-gray-300 dark:text-gray-600 group-hover:inline">{t('resume.doubleClickEdit')}</span>
                )}
              </div>
              {isC && isE && change && (
                <ChangeDetailPopover change={change} activeVariantIndex={changeVariantIndex[change.path] ?? 0} onSwitchVariant={onSwitchVariant} />
              )}
            </div>
          );
        })}
      </div>
    );
  };

  // ── Inline-editable sub-field for dates, locations, titles ────────
  const ET = (path: string, value: string | undefined | null, tag: 'strong' | 'span' = 'span') => {
    const display = value || '';
    if (editingPath === path) {
      return (
        <input
          value={editingValue}
          onChange={e => setEditingValue(e.target.value)}
          onBlur={saveEdit}
          onKeyDown={e => {
            if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); }
            if (e.key === 'Enter') { e.preventDefault(); saveEdit(); }
          }}
          className={`inline-block rounded border border-blue-300 dark:border-blue-600 bg-white dark:bg-zinc-800 px-1.5 py-0.5 text-xs leading-relaxed text-gray-800 dark:text-zinc-100 outline-none focus:ring-1 focus:ring-blue-400 ${
            tag === 'strong' ? 'font-semibold text-sm' : ''
          }`}
          style={{ width: `${Math.max(60, editingValue.length * 7 + 24)}px` }}
          autoFocus
        />
      );
    }
    if (!display && !onEditField) return null;
    if (!display) return <span className="text-gray-300 dark:text-zinc-600 italic cursor-text" onDoubleClick={(e) => {
      e.stopPropagation();
      if (onEditField) startEdit(path, '');
    }}>{t('resume.empty')}</span>;
    if (tag === 'strong') {
      return <strong className="cursor-text hover:bg-gray-50 dark:hover:bg-zinc-800/50 rounded px-0.5 -mx-0.5 transition-colors" onDoubleClick={(e) => {
        e.stopPropagation();
        if (onEditField) startEdit(path, display);
      }}>{display}</strong>;
    }
    return <span className="cursor-text hover:bg-gray-50 dark:hover:bg-zinc-800/50 rounded px-0.5 -mx-0.5 transition-colors" onDoubleClick={(e) => {
      e.stopPropagation();
      if (onEditField) startEdit(path, display);
    }}>{display}</span>;
  };

  // ── data ──
  const pi = (refinedResumeObj.personalInfo as Record<string, unknown> | undefined) || {};
  const s = refinedResumeObj.summary;
  const we = Array.isArray(refinedResumeObj.workExperience) ? refinedResumeObj.workExperience as Record<string, unknown>[] : [];
  const pp = Array.isArray(refinedResumeObj.personalProjects) ? refinedResumeObj.personalProjects as Record<string, unknown>[] : [];
  const rs = Array.isArray(refinedResumeObj.research) ? refinedResumeObj.research as Record<string, unknown>[] : [];
  const ed = Array.isArray(refinedResumeObj.education) ? refinedResumeObj.education as Record<string, unknown>[] : [];
  const ad = (refinedResumeObj.additional as Record<string, unknown> | undefined) || {};

  const name = toDisplayText(pi.name) || toDisplayText(refinedResumeObj.name) || 'Resume';
  const title = toDisplayText(pi.title) || toDisplayText(refinedResumeObj.title) || '';
  const contact1 = [pi.email, pi.phone, pi.location].map(x => toDisplayText(x)).filter(Boolean);
  const contact2 = [pi.website, pi.linkedin, pi.github].map(x => toDisplayText(x)).filter(Boolean);

  return (
    <article className="mx-auto w-full max-w-[780px] rounded-xl bg-white dark:bg-gray-900 px-10 py-8 shadow-[0_1px_12px_rgba(0,0,0,0.05)] dark:shadow-[0_1px_12px_rgba(0,0,0,0.3)] ring-1 ring-gray-200/50 dark:ring-gray-700/50">

      <header className="mb-6 border-b border-gray-200 dark:border-gray-700 pb-4">
        {editingPath === 'personalInfo.name' ? (
          <div className="relative border-l-[3px] border-blue-400 dark:border-blue-600 pl-3 py-0.5 bg-blue-50/40 dark:bg-blue-900/20 rounded-r-md">
            <input
              value={editingValue}
              onChange={e => setEditingValue(e.target.value)}
              onBlur={saveEdit}
              onKeyDown={e => { if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); } if (e.key === 'Enter') { e.preventDefault(); saveEdit(); }}}
              className="w-full rounded border border-blue-300 dark:border-blue-600 bg-white dark:bg-zinc-800 px-2 py-0.5 text-xl font-semibold text-gray-800 dark:text-zinc-100 outline-none focus:ring-1 focus:ring-blue-400"
              autoFocus
            />
            <span className="mt-1 block text-[10px] text-blue-400 dark:text-blue-300">{t('resume.editHint')}</span>
          </div>
        ) : (
          <h1 className="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100 group cursor-text" onDoubleClick={(e) => {
            e.stopPropagation();
            if (onEditField) startEdit('personalInfo.name', toDisplayText(pi.name) || toDisplayText(refinedResumeObj.name) || '');
          }}>
            {name}
            {onEditField && <span className="ml-2 hidden text-[10px] text-gray-300 dark:text-gray-600 group-hover:inline">{t('resume.doubleClickEdit')}</span>}
          </h1>
        )}
        {editingPath === 'personalInfo.title' ? (
          <div className="relative border-l-[3px] border-blue-400 dark:border-blue-600 pl-3 py-0.5 bg-blue-50/40 dark:bg-blue-900/20 rounded-r-md mt-0.5">
            <input
              value={editingValue}
              onChange={e => setEditingValue(e.target.value)}
              onBlur={saveEdit}
              onKeyDown={e => { if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); } if (e.key === 'Enter') { e.preventDefault(); saveEdit(); }}}
              className="w-full rounded border border-blue-300 dark:border-blue-600 bg-white dark:bg-zinc-800 px-2 py-0.5 text-sm text-gray-800 dark:text-zinc-100 outline-none focus:ring-1 focus:ring-blue-400"
              autoFocus
            />
            <span className="mt-1 block text-[10px] text-blue-400 dark:text-blue-300">{t('resume.editHint')}</span>
          </div>
        ) : title ? (
          <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400 group cursor-text" onDoubleClick={(e) => {
            e.stopPropagation();
            if (onEditField) startEdit('personalInfo.title', toDisplayText(pi.title) || toDisplayText(refinedResumeObj.title) || '');
          }}>
            {title}
            {onEditField && <span className="ml-2 hidden text-[10px] text-gray-300 dark:text-gray-600 group-hover:inline">{t('resume.doubleClickEdit')}</span>}
          </p>
        ) : null}
        {contact1.length > 0 && <p className="mt-2 text-xs text-gray-400 dark:text-gray-500 flex flex-wrap gap-x-3">
          {[pi.email, pi.phone, pi.location].map((val, ci) => {
            const display = toDisplayText(val);
            if (!display) return null;
            const fieldKeys = ['email', 'phone', 'location'];
            const path = `personalInfo.${fieldKeys[ci]}`;
            return ET(path, display);
          })}
        </p>}
        {contact2.length > 0 && <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500 flex flex-wrap gap-x-3">
          {[pi.website, pi.linkedin, pi.github].map((val, ci) => {
            const display = toDisplayText(val);
            if (!display) return null;
            const fieldKeys = ['website', 'linkedin', 'github'];
            const path = `personalInfo.${fieldKeys[ci]}`;
            return ET(path, display);
          })}
        </p>}
      </header>

      {toDisplayText(s) && (
        <section className="mb-5">
          <SectionTitle>{t('resume.summary')}</SectionTitle>
          {RF('summary', s, 'div')}
        </section>
      )}

      {we.length > 0 && (
        <section className="mb-5">
          <SectionTitle>{t('resume.experience')}</SectionTitle>
          <div className="space-y-4">
            {we.map((exp, i) => {
              const b = `workExperience[${i}]`;
              const dLines = displayLines(resolveFieldValue(exp, 'workExperience', 'description'));
              const titleVal = toDisplayText(resolveFieldValue(exp, 'workExperience', 'title')) || '';
              const companyVal = toDisplayText(resolveFieldValue(exp, 'workExperience', 'company')) || '';
              const locationVal = toDisplayText(resolveFieldValue(exp, 'workExperience', 'location')) || '';
              const yearsVal = toDisplayText(resolveFieldValue(exp, 'workExperience', 'years')) || '';
              return (
                <div key={b} className="border-l-[3px] border-gray-200 dark:border-gray-700 pl-3">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{ET(`${b}.title`, titleVal, 'strong')}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 flex flex-wrap gap-x-1">
                    {companyVal && <>{ET(`${b}.company`, companyVal)}</>}
                    {locationVal && <><span className="text-gray-300 dark:text-zinc-600">·</span> {ET(`${b}.location`, locationVal)}</>}
                    {yearsVal && <><span className="text-gray-300 dark:text-zinc-600">·</span> {ET(`${b}.years`, yearsVal)}</>}
                  </p>
                  {dLines.length > 0 && <div className="mt-1 space-y-0.5">{dLines.map((l, li) => RF(`${b}.description[${li}]`, l, 'p'))}</div>}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {pp.length > 0 && (
        <section className="mb-5">
          <SectionTitle>{t('resume.projects')}</SectionTitle>
          <div className="space-y-4">
            {pp.map((p, i) => {
              const b = `personalProjects[${i}]`;
              const dLines = displayLines(resolveFieldValue(p, 'personalProjects', 'description'));
              const nameVal = toDisplayText(resolveFieldValue(p, 'personalProjects', 'name')) || '';
              const roleVal = toDisplayText(resolveFieldValue(p, 'personalProjects', 'role')) || '';
              const yearsVal = toDisplayText(resolveFieldValue(p, 'personalProjects', 'years')) || '';
              return (
                <div key={b} className="border-l-[3px] border-gray-200 dark:border-gray-700 pl-3">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{ET(`${b}.name`, nameVal, 'strong')}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 flex flex-wrap gap-x-1">
                    {roleVal && <>{ET(`${b}.role`, roleVal)}</>}
                    {yearsVal && <><span className="text-gray-300 dark:text-zinc-600">·</span> {ET(`${b}.years`, yearsVal)}</>}
                  </p>
                  {dLines.length > 0 && <div className="mt-1 space-y-0.5">{dLines.map((l, li) => RF(`${b}.description[${li}]`, l, 'p'))}</div>}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {rs.length > 0 && (
        <section className="mb-5">
          <SectionTitle>{t('resume.research')}</SectionTitle>
          <div className="space-y-4">
            {rs.map((r, i) => {
              const b = `research[${i}]`;
              const dLines = displayLines(resolveFieldValue(r, 'research', 'description'));
              const nameVal = toDisplayText(resolveFieldValue(r, 'research', 'name')) || '';
              const roleVal = toDisplayText(resolveFieldValue(r, 'research', 'role')) || '';
              const instVal = toDisplayText(resolveFieldValue(r, 'research', 'institution')) || '';
              const yearsVal = toDisplayText(resolveFieldValue(r, 'research', 'years')) || '';
              return (
                <div key={b} className="border-l-[3px] border-gray-200 dark:border-gray-700 pl-3">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{ET(`${b}.name`, nameVal, 'strong')}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 flex flex-wrap gap-x-1">
                    {roleVal && <>{ET(`${b}.role`, roleVal)}</>}
                    {instVal && <><span className="text-gray-300 dark:text-zinc-600">·</span> {ET(`${b}.institution`, instVal)}</>}
                    {yearsVal && <><span className="text-gray-300 dark:text-zinc-600">·</span> {ET(`${b}.years`, yearsVal)}</>}
                  </p>
                  {dLines.length > 0 && <div className="mt-1 space-y-0.5">{dLines.map((l, li) => RF(`${b}.description[${li}]`, l, 'p'))}</div>}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {ed.length > 0 && (
        <section className="mb-5">
          <SectionTitle>{t('resume.education')}</SectionTitle>
          <div className="space-y-2.5">
            {ed.map((e, i) => {
              const b = `education[${i}]`;
              const instVal = toDisplayText(resolveFieldValue(e, 'education', 'institution')) || '';
              const degreeVal = toDisplayText(resolveFieldValue(e, 'education', 'degree')) || '';
              const yearsVal = toDisplayText(resolveFieldValue(e, 'education', 'years')) || '';
              const gpaVal = toDisplayText(resolveFieldValue(e, 'education', 'gpa')) || '';
              const descLines = displayLines(resolveFieldValue(e, 'education', 'description'));
              return (
                <div key={b} className="border-l-[3px] border-gray-200 dark:border-gray-700 pl-3">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{ET(`${b}.institution`, instVal, 'strong')}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 flex flex-wrap gap-x-1">
                    {degreeVal && <>{ET(`${b}.degree`, degreeVal)}</>}
                    {yearsVal && <><span className="text-gray-300 dark:text-zinc-600">·</span> {ET(`${b}.years`, yearsVal)}</>}
                    {gpaVal && <><span className="text-gray-300 dark:text-zinc-600">·</span> GPA: {ET(`${b}.gpa`, gpaVal)}</>}
                  </p>
                  {descLines.length > 0 && (
                    <ul className="mt-1.5 list-disc space-y-0.5 pl-4">
                      {descLines.map((line, li) => (
                        <li key={li} className="text-[12px] text-gray-600 dark:text-gray-400 leading-relaxed">
                          {ET(`${b}.description[${li}]`, line)}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {(['technicalSkills', 'languages', 'certificationsTraining', 'awards'] as const).some(k => {
        const v = ad[k]; return (Array.isArray(v) && v.length > 0) || (typeof v === 'string' && v);
      }) && (
        <section className="mb-5">
          <SectionTitle>{t('resume.additional')}</SectionTitle>
          <div className="space-y-3">
            {(['technicalSkills', 'languages', 'certificationsTraining', 'awards'] as const).map(key => {
              const val = ad[key];
              if (Array.isArray(val) && val.length > 0) {
                const items = val.map(v => typeof v === 'object' ? toDisplayText(v) : String(v ?? ''));
                const label = key.replace(/([A-Z])/g, ' $1').trim();
                const useList = anyItemLong(items);
                return (
                  <div key={key} className={useList ? '' : 'flex gap-3'}>
                    <span className={`text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 shrink-0 pt-0.5 ${useList ? 'block mb-1.5' : 'w-28'}`}>{label}</span>
                    {useList ? renderAdditionalList(key, items) : renderAdditionalBadges(key, items)}
                  </div>
                );
              }
              if (typeof val === 'string' && val) {
                // String fallback: split by comma/semicolon/newline and render as badges
                const parts = val.split(/[,;，；\n]\s*/).filter(Boolean);
                if (parts.length > 1) {
                  const label = key.replace(/([A-Z])/g, ' $1').trim();
                  const useList = anyItemLong(parts);
                  return (
                    <div key={key} className={useList ? '' : 'flex gap-3'}>
                      <span className={`text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 shrink-0 pt-0.5 ${useList ? 'block mb-1.5' : 'w-28'}`}>{label}</span>
                      {useList ? renderAdditionalList(key, parts) : renderAdditionalBadges(key, parts)}
                    </div>
                  );
                }
                return RF(`additional.${key}`, val, 'p');
              }
              return null;
            })}
          </div>
        </section>
      )}

      {(() => {
        const cs = (refinedResumeObj.customSections as Record<string, unknown> | undefined) || {};
        return Object.entries(cs).map(([sk, sv]) => {
          const sec = sv as Record<string, unknown> | undefined;
          if (!sec) return null;
          const items = Array.isArray(sec.items) ? sec.items as unknown[] : [];
          const text = String(sec.text || '');
          return (
            <section key={sk} className="mb-5">
              <SectionTitle>{sk}</SectionTitle>
              {items.length > 0 ? <ul className="space-y-0.5 pl-4 list-disc">{items.map((it, i) => RF(`customSections.${sk}.items[${i}]`, it, 'li'))}</ul>
               : text ? RF(`customSections.${sk}.text`, text, 'p') : null}
            </section>
          );
        });
      })()}
    </article>
  );
}
