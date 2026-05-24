import { useEffect, useState } from 'react';
import { Check, Save } from 'lucide-react';
import type { BuilderSectionDraft, RenderGuidanceSettings } from './types';
import { BUILTIN_BUILDER_TEMPLATES, type BuiltinBuilderTemplate } from './builtin-templates';

const STORAGE_KEY = 'builder_custom_templates';

export interface StoredTemplate {
  id: string;
  name: string;
  guidance: RenderGuidanceSettings;
  sections: BuilderSectionDraft[];
  createdAt: string;
  updatedAt?: string;
}

function loadCustomTemplates(): StoredTemplate[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    return Array.isArray(parsed)
      ? parsed.map((item) => ({ ...item, sections: Array.isArray(item?.sections) ? item.sections : [] }))
      : [];
  } catch { return []; }
}

function saveCustomTemplates(list: StoredTemplate[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
}

interface Props {
  activeTemplateId: string;
  onSelectBuiltin: (tpl: BuiltinBuilderTemplate) => void;
  onSelectCustom: (tpl: StoredTemplate) => void;
}

export function TemplateSidebar({
  activeTemplateId,
  onSelectBuiltin,
  onSelectCustom,
}: Props) {
  const [customList, setCustomList] = useState<StoredTemplate[]>(loadCustomTemplates);

  // Refresh list when parent changes (e.g. after save from outside)
  useEffect(() => {
    setCustomList(loadCustomTemplates());
  }, [activeTemplateId]);

  const handleDelete = (id: string) => {
    const next = customList.filter((t) => t.id !== id);
    setCustomList(next);
    saveCustomTemplates(next);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-[var(--brand-line)] px-4 py-3">
        <h3 className="font-mono text-[11px] font-bold uppercase tracking-wider text-gray-600 dark:text-zinc-400">Templates</h3>
      </div>

      <div className="flex-1 overflow-auto">
        {/* Built-in templates */}
        <div className="px-3 py-2">
          <p className="mb-1 px-1 font-sans text-[10px] text-gray-400 dark:text-zinc-500">Built-in</p>
          {BUILTIN_BUILDER_TEMPLATES.map((tpl) => {
            const isActive = activeTemplateId === tpl.id;
            return (
              <button
                key={tpl.id}
                type="button"
                onClick={() => onSelectBuiltin(tpl)}
                title={tpl.description}
                className={`flex w-full items-center gap-3 rounded px-3 py-2.5 text-left transition-colors ${
                  isActive ? 'bg-black dark:bg-zinc-700 text-white dark:text-white' : 'hover:bg-gray-100 dark:hover:bg-zinc-700'
                }`}
              >
                <div className="flex h-10 w-8 shrink-0 items-center justify-center rounded border bg-white dark:bg-zinc-800">
                  <span className="h-5 w-3 rounded-sm" style={{ backgroundColor: tpl.swatch }} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className={`truncate font-sans text-xs font-medium ${isActive ? 'text-white dark:text-white' : 'text-gray-900 dark:text-zinc-100'}`}>
                    {tpl.name}
                  </p>
                  <p className={`truncate font-mono text-[10px] ${isActive ? 'text-gray-300 dark:text-zinc-600' : 'text-gray-500 dark:text-zinc-400'}`}>
                    {tpl.meta}
                  </p>
                </div>
                {isActive && <Check className="size-3.5 shrink-0 text-white" />}
              </button>
            );
          })}
        </div>

        {/* Custom saved templates */}
        {customList.length > 0 && (
          <div className="border-t border-[var(--brand-line)] px-3 py-2">
            <p className="mb-1 px-1 font-sans text-[10px] text-gray-400 dark:text-zinc-500">Saved</p>
            {customList.map((tpl) => {
              const isActive = activeTemplateId === tpl.id;
              return (
                <div key={tpl.id} className="group relative">
                  <button
                    type="button"
                    onClick={() => onSelectCustom(tpl)}
                    className={`flex w-full items-center gap-3 rounded px-3 py-2.5 text-left transition-colors ${
                      isActive ? 'bg-black dark:bg-zinc-700 text-white dark:text-white' : 'hover:bg-gray-100 dark:hover:bg-zinc-700'
                    }`}
                  >
                    <div className="flex h-10 w-8 shrink-0 items-center justify-center rounded border bg-white dark:bg-zinc-800">
                      <Save className="size-3 text-gray-400 dark:text-zinc-500" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className={`truncate font-sans text-xs font-medium ${isActive ? 'text-white dark:text-white' : 'text-gray-900 dark:text-zinc-100'}`}>
                        {tpl.name}
                      </p>
                      <p className={`truncate font-mono text-[10px] ${isActive ? 'text-gray-300 dark:text-zinc-600' : 'text-gray-500 dark:text-zinc-400'}`}>
                        {new Date(tpl.createdAt).toLocaleDateString()}
                      </p>
                    </div>
                    {isActive && <Check className="size-3.5 shrink-0 text-white" />}
                  </button>
                  <button
                    onClick={() => handleDelete(tpl.id)}
                    className="absolute right-2 top-1/2 hidden -translate-y-1/2 rounded p-1 text-gray-400 dark:text-zinc-500 hover:text-red-500 group-hover:block"
                    title="Delete"
                  >
                    &times;
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}
