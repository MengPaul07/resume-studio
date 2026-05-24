import { useState } from 'react';
import { toDisplayText, setByPathLocal } from '../../lib/tailor/utils';

interface Props {
  resumeObj: Record<string, unknown>;
  onChange: (obj: Record<string, unknown>) => void;
  disabled?: boolean;
}

interface EditableField {
  path: string;
  label: string;
  value: unknown;
}

/** Flatten resumeObj into a list of leaf fields with display paths. */
function flattenFields(obj: Record<string, unknown>, prefix = ''): EditableField[] {
  const fields: EditableField[] = [];
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value === null || value === undefined) continue;
    if (Array.isArray(value)) {
      value.forEach((item, idx) => {
        if (typeof item === 'object' && item !== null) {
          // Array of objects: title field shows as label, rest as sub-fields
          const itemObj = item as Record<string, unknown>;
          const titleKey = ['title', 'name', 'institution', 'company'].find(k => k in itemObj);
          const titleVal = titleKey ? itemObj[titleKey] : `Item ${idx + 1}`;
          fields.push({ path: `${path}[${idx}]`, label: `${toDisplayText(titleVal)}`, value: '__SECTION__' });
          for (const [ik, iv] of Object.entries(itemObj)) {
            if (ik === 'id') continue;
            if (typeof iv === 'string' || typeof iv === 'number') {
              fields.push({ path: `${path}[${idx}].${ik}`, label: `  ${ik}`, value: iv });
            } else if (Array.isArray(iv)) {
              iv.forEach((line, li) => {
                fields.push({ path: `${path}[${idx}].${ik}[${li}]`, label: `  ${ik} #${li + 1}`, value: line });
              });
            }
          }
        } else {
          fields.push({ path: `${path}[${idx}]`, label: `${key}[${idx}]`, value });
        }
      });
    } else if (typeof value === 'object') {
      fields.push(...flattenFields(value as Record<string, unknown>, path));
    } else {
      fields.push({ path, label: key, value });
    }
  }
  return fields;
}

const SECTION_ORDER = ['personalInfo', 'summary', 'workExperience', 'education', 'personalProjects', 'research', 'additional'];
const SECTION_LABELS: Record<string, string> = {
  personalInfo: 'Personal Info', summary: 'Summary', workExperience: 'Work',
  education: 'Education', personalProjects: 'Projects', research: 'Research', additional: 'Additional',
};

export function LayoutEditor({ resumeObj, onChange, disabled }: Props) {
  const [editingPath, setEditingPath] = useState<string | null>(null);
  const [draft, setDraft] = useState('');

  const startEdit = (path: string, value: unknown) => {
    if (disabled) return;
    setEditingPath(path);
    setDraft(typeof value === 'string' ? value : toDisplayText(value));
  };

  const confirmEdit = () => {
    if (!editingPath) return;
    const next = JSON.parse(JSON.stringify(resumeObj));
    setByPathLocal(next, editingPath, draft);
    onChange(next);
    setEditingPath(null);
  };

  const grouped: Record<string, EditableField[]> = {};
  const allFields = flattenFields(resumeObj);
  for (const field of allFields) {
    const section = field.path.split('.')[0].replace(/\[\d+\]/, '');
    if (!grouped[section]) grouped[section] = [];
    if (field.value !== '__SECTION__') grouped[section].push(field);
  }

  const orderedSections = [
    ...SECTION_ORDER.filter(s => grouped[s]),
    ...Object.keys(grouped).filter(s => !SECTION_ORDER.includes(s)),
  ];

  return (
    <div className="shrink-0 space-y-3 max-h-[45vh] overflow-auto">
      {orderedSections.map(section => (
        <div key={section} className="rounded-xl border border-[var(--brand-line)] bg-white dark:bg-zinc-900 overflow-hidden">
          <div className="border-b border-[var(--brand-line)] bg-[var(--brand-surface-soft)] px-3 py-2">
            <p className="font-sans text-[11px] font-semibold text-[var(--brand-ink)]">
              {SECTION_LABELS[section] || section}
            </p>
          </div>
          <div className="divide-y divide-[var(--brand-line)]">
            {grouped[section].map(f => (
              <div key={f.path}
                className="flex items-start gap-3 px-3 py-2 hover:bg-[var(--brand-surface-soft)]/50 transition-colors group"
              >
                <span className="shrink-0 w-28 font-sans text-[10px] font-medium text-[var(--brand-ink-muted)] pt-0.5 truncate">
                  {f.label}
                </span>
                {editingPath === f.path ? (
                  <input
                    autoFocus
                    value={draft}
                    onChange={e => setDraft(e.target.value)}
                    onBlur={confirmEdit}
                    onKeyDown={e => {
                      if (e.key === 'Enter') { e.preventDefault(); confirmEdit(); }
                      if (e.key === 'Escape') setEditingPath(null);
                    }}
                    className="flex-1 min-w-0 rounded-md border border-[var(--brand-signal)] bg-white dark:bg-zinc-800 px-2 py-0.5 font-sans text-[13px] text-[var(--brand-ink)] outline-none ring-1 ring-[var(--brand-signal)]"
                  />
                ) : (
                  <span
                    onClick={() => startEdit(f.path, f.value)}
                    className={`flex-1 min-w-0 font-sans text-[13px] leading-5 text-[var(--brand-ink)] cursor-text rounded px-1 -mx-1 hover:bg-[var(--brand-signal-soft)] transition-colors ${
                      typeof f.value === 'string' && !(f.value as string).trim() ? 'italic text-[var(--brand-ink-muted)]' : ''
                    }`}
                  >
                    {toDisplayText(f.value) || '(empty)'}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
