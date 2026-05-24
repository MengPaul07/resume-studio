import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ClipboardCopy, Download, ExternalLink, FileText, Save, WandSparkles, X } from 'lucide-react';
import { buildApiUrl, getRecentResume, listRecentResumes, saveRecentResume } from '../api';
import { BuilderLayout } from '../components/builder-workbench/BuilderLayout';
import { EditorPanel } from '../components/builder-workbench/EditorPanel';
import { TemplateSidebar, type StoredTemplate } from '../components/builder-workbench/TemplateSidebar';
import { renderResumeHtmlFromLayout } from '../components/builder-workbench/html-renderer';
import { PreviewPanel } from '../components/builder-workbench/PreviewPanel';
import { ensureUtf8HtmlDocument } from '../lib/html-encoding';
import {
  DEFAULT_GUIDANCE,
  DEFAULT_SECTIONS,
  type BuilderSectionDraft,
  type RenderGuidanceSettings,
} from '../components/builder-workbench/types';
import {
  BUILTIN_BUILDER_TEMPLATES,
  getBuiltinBuilderTemplate,
  type BuiltinBuilderTemplate,
} from '../components/builder-workbench/builtin-templates';
import { PageTransition } from '../components/layout/page-transition';
import { Button } from '../components/ui/button';
import { DEFAULT_PREFERENCES } from '../preferences';
import type { RecentResumeRecord } from '../types';

const CUSTOM_TEMPLATE_STORAGE_KEY = 'builder_custom_templates';
const DEFAULT_TEMPLATE_ID = 'swiss-single';

function normalizeGuidance(value: unknown): RenderGuidanceSettings | null {
  if (!value || typeof value !== 'object') return null;
  const candidate = value as Partial<RenderGuidanceSettings>;
  return {
    ...DEFAULT_GUIDANCE,
    ...candidate,
    margins: {
      ...DEFAULT_GUIDANCE.margins,
      ...(candidate.margins || {}),
    },
  };
}

function mergeCustomSectionsFromJson(
  resumeObj: Record<string, unknown>,
  existingSections: BuilderSectionDraft[],
): BuilderSectionDraft[] {
  const customSections = (resumeObj.customSections || {}) as Record<string, unknown>;
  const keys = Object.keys(customSections);
  if (!keys.length) return existingSections;
  const existingKeys = new Set(existingSections.map((s) => s.key));
  const newSections = keys
    .filter((key) => !existingKeys.has(key))
    .map((key) => ({
      id: `custom-${key}`,
      key,
      title: key.replace(/([A-Z])/g, ' $1').replace(/^./, (s) => s.toUpperCase()),
      visible: true,
      column: 'right' as const,
    }));
  if (!newSections.length) return existingSections;
  return [...existingSections, ...newSections];
}

function normalizeSections(value: unknown): BuilderSectionDraft[] | null {
  if (!Array.isArray(value)) return null;
  const rows = value
    .map((item, index) => {
      const row = (item || {}) as Record<string, unknown>;
      const key = String(row.key || '').trim();
      if (!key) return null;
      const matched = DEFAULT_SECTIONS.find((section) => section.key === key);
      const title = String(row.title || matched?.title || key);
      const id = String(row.id || matched?.id || key);
      const visible = typeof row.visible === 'boolean' ? row.visible : (matched?.visible ?? true);
      const order = Number.isFinite(Number(row.order)) ? Number(row.order) : index;
      const columnRaw = row.column;
      const column: 'left' | 'right' =
        columnRaw === 'left' || columnRaw === 'right' ? columnRaw : (matched?.column ?? 'right');
      return { id, key, title, visible, column, order };
    })
    .filter(Boolean) as Array<BuilderSectionDraft & { order: number }>;

  if (rows.length <= 0) return null;
  rows.sort((a, b) => a.order - b.order);
  return rows.map(({ order: _order, ...section }) => section);
}

function readStoredTemplates(): StoredTemplate[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(CUSTOM_TEMPLATE_STORAGE_KEY) || '[]');
    return Array.isArray(parsed)
      ? parsed.map((item) => ({ ...item, sections: Array.isArray(item?.sections) ? item.sections : [] }))
      : [];
  } catch {
    return [];
  }
}

function normalizeTemplateId(templateName?: string): string {
  const raw = String(templateName || '').trim();
  if (!raw) return DEFAULT_TEMPLATE_ID;
  return raw.replace(/\.html$/i, '').replace(/_/g, '-');
}

function withSectionOrder(sections: BuilderSectionDraft[]) {
  return sections.map((section, order) => ({
    ...section,
    order,
  }));
}

function readBuilderPayload(record: RecentResumeRecord): {
  guidance?: unknown;
  sections?: unknown;
  template_id?: unknown;
} {
  const metadata = record.layout_preferences?.metadata;
  const payload = metadata?.layout_builder_payload;
  return payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : {};
}

function buildLayoutPreferences(
  base: RecentResumeRecord['layout_preferences'],
  guidance: RenderGuidanceSettings,
  sections: BuilderSectionDraft[],
  templateId: string,
) {
  const basePreferences = {
    ...DEFAULT_PREFERENCES,
    ...(base || {}),
  };
  const baseMetadata = {
    ...((basePreferences.metadata || {}) as Record<string, unknown>),
  };
  return {
    ...basePreferences,
    metadata: {
      ...baseMetadata,
      layout_builder_payload: {
        guidance,
        sections: withSectionOrder(sections),
        template_id: templateId,
      },
    },
  };
}

export function ResumeViewPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const queryResumeId = searchParams.get('resumeId') || '';
  const activeResumeId = id || queryResumeId;

  const [resume, setResume] = useState<RecentResumeRecord | null>(null);
  const [recentResumes, setRecentResumes] = useState<RecentResumeRecord[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [savingHtml, setSavingHtml] = useState(false);
  const [savingPdf, setSavingPdf] = useState(false);
  const [savingTex, setSavingTex] = useState(false);
  const [showOverleafModal, setShowOverleafModal] = useState(false);
  const [contentOverflows, setContentOverflows] = useState(false);
  const [guidance, setGuidance] = useState<RenderGuidanceSettings>(DEFAULT_GUIDANCE);
  const [sections, setSections] = useState<BuilderSectionDraft[]>(DEFAULT_SECTIONS);
  const [htmlDraft, setHtmlDraft] = useState('');
  const [layoutPreviewLinked, setLayoutPreviewLinked] = useState(true);
  const [activeTemplateId, setActiveTemplateId] = useState(DEFAULT_TEMPLATE_ID);

  const handleSelectBuiltin = (tpl: BuiltinBuilderTemplate) => {
    setActiveTemplateId(tpl.id);
    setGuidance(normalizeGuidance(tpl.guidance) || DEFAULT_GUIDANCE);
    const templateSections = normalizeSections(tpl.sections) || DEFAULT_SECTIONS;
    setSections(mergeCustomSectionsFromJson((resume?.resume_obj || {}) as Record<string, unknown>, templateSections));
  };

  const handleSelectCustom = (tpl: StoredTemplate) => {
    setActiveTemplateId(tpl.id);
    setGuidance(normalizeGuidance(tpl.guidance) || DEFAULT_GUIDANCE);
    const templateSections = normalizeSections(tpl.sections) || DEFAULT_SECTIONS;
    setSections(mergeCustomSectionsFromJson((resume?.resume_obj || {}) as Record<string, unknown>, templateSections));
  };

  useEffect(() => {
    listRecentResumes(30)
      .then((items) => {
        setRecentResumes(items);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load recent resumes');
      });
  }, []);

  useEffect(() => {
    if (id) return;
    if (queryResumeId) return;
    if (recentResumes.length <= 0) return;
    setSearchParams({ resumeId: recentResumes[0].id }, { replace: true });
  }, [id, queryResumeId, recentResumes, setSearchParams]);

  useEffect(() => {
    if (!activeResumeId) {
      setResume(null);
      return;
    }

    setLoading(true);
    setError('');
    getRecentResume(activeResumeId)
      .then((record) => {
        setResume(record);
        const builderPayload = readBuilderPayload(record);
        const payloadGuidance = normalizeGuidance(builderPayload.guidance);
        const payloadSections = normalizeSections(builderPayload.sections);
        const payloadTemplateId =
          typeof builderPayload.template_id === 'string' ? normalizeTemplateId(builderPayload.template_id) : '';
        const templateId = normalizeTemplateId(record.template_name);
        const storedTemplate = readStoredTemplates().find((tpl) => tpl.id === templateId);
        const builtinTemplate = getBuiltinBuilderTemplate(templateId) || BUILTIN_BUILDER_TEMPLATES[0];
        const effectiveTemplateId = storedTemplate ? storedTemplate.id : builtinTemplate.id;
        const effectiveGuidance = payloadGuidance || normalizeGuidance(storedTemplate?.guidance || builtinTemplate.guidance) || DEFAULT_GUIDANCE;
        const baseSections = payloadSections || normalizeSections(storedTemplate?.sections || builtinTemplate.sections) || DEFAULT_SECTIONS;
        const resumeObj = (record.resume_obj || {}) as Record<string, unknown>;
        const effectiveSections = mergeCustomSectionsFromJson(resumeObj, baseSections);
        setActiveTemplateId(payloadGuidance || payloadSections ? (payloadTemplateId || effectiveTemplateId) : effectiveTemplateId);
        setGuidance(effectiveGuidance);
        setSections(effectiveSections);

        const existingHtml = ensureUtf8HtmlDocument(String(record.output_html || '').trim());
        const fallbackHtml = renderResumeHtmlFromLayout({
          resumeObj: (record.resume_obj || {}) as Record<string, unknown>,
          guidance: effectiveGuidance,
          sections: effectiveSections,
        });
        setHtmlDraft(existingHtml || fallbackHtml);
        setLayoutPreviewLinked(true);

        setRecentResumes((prev) => {
          const exists = prev.some((item) => item.id === record.id);
          return exists ? prev : [record, ...prev];
        });
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load resume');
      })
      .finally(() => setLoading(false));
  }, [activeResumeId]);

  const viewTitle = resume?.title || 'Layout Builder';
  const profileRole = String(
    (resume?.resume_obj?.personalInfo as Record<string, unknown> | undefined)?.title || 'Select a resume to begin',
  );
  const persistedHtml = useMemo(
    () => ensureUtf8HtmlDocument(String(resume?.output_html || '').trim()),
    [resume?.output_html],
  );
  const dirtyHtml = useMemo(() => htmlDraft !== persistedHtml, [htmlDraft, persistedHtml]);

  const buildFileName = (): string => {
    const raw = String(resume?.title || 'resume').toLowerCase();
    const safe = raw.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'resume';
    return safe;
  };

  const handleDownload = () => {
    const html = htmlDraft || persistedHtml;
    if (!html) {
      setError('No rendered HTML available to download. Click Render first.');
      return;
    }
    // Pre-build consistency check
    const pageMatches = html.match(/<div[^>]*class=["'][^"']*page["'][^>]*>/g);
    const pageCount = pageMatches?.length || 1;
    const targetPages = guidance.pageCountMode === 'single-page' ? 1 : 2;
    if (pageCount > targetPages && !window.confirm(
      `Content spans ${pageCount} pages (target: ${targetPages}).\nExcess content may be clipped. Continue?`
    )) {
      return;
    }
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${buildFileName()}.html`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  const handleDownloadPdf = async () => {
    if (!htmlDraft) {
      setError('No HTML preview to export.');
      return;
    }
    setSavingPdf(true);
    setError('');
    try {
      const printWindow = window.open('', '_blank', 'noopener,noreferrer');
      if (!printWindow) {
        throw new Error('Browser blocked the print window. Allow popups and try again.');
      }
      printWindow.document.open();
      printWindow.document.write(htmlDraft);
      printWindow.document.close();
      printWindow.document.title = `${buildFileName()}.pdf`;
      printWindow.focus();
      window.setTimeout(() => {
        printWindow.print();
      }, 250);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'PDF export failed';
      setError(msg);
    } finally {
      setSavingPdf(false);
    }
  };

  const handleDownloadTex = async () => {
    if (!resume?.resume_obj) {
      setError('No resume data to export.');
      return;
    }
    setSavingTex(true);
    setError('');
    try {
      const resp = await fetch(buildApiUrl('/latex/tex'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_obj: resume.resume_obj,
          guidance,
          sections: withSectionOrder(sections),
          personal_info: (resume.resume_obj as Record<string, unknown>).personalInfo || {},
          html_source: htmlDraft,
        }),
      });
      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(errText || `TeX generation failed (${resp.status})`);
      }
      const data = await resp.json();
      const texSource: string = data.tex || '';
      await navigator.clipboard.writeText(texSource);
      setShowOverleafModal(true);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'TeX generation failed';
      setError(msg);
    } finally {
      setSavingTex(false);
    }
  };

  const handleSaveHtml = async () => {
    if (!resume?.id) return;
    setSavingHtml(true);
    setError('');
    try {
      const savedTemplateId = activeTemplateId || 'custom-builder';
      const layoutPreferences = buildLayoutPreferences(resume.layout_preferences, guidance, sections, savedTemplateId);
      const updated = await saveRecentResume({
        resume_id: resume.id,
        title: resume.title || 'Untitled Resume',
        status: resume.status || 'ready',
        source: resume.source || 'builder',
        tags: Array.isArray(resume.tags) ? resume.tags : [],
        resume_obj: (resume.resume_obj || {}) as Record<string, unknown>,
        output_markdown: resume.output_markdown || '',
        output_html: htmlDraft,
        template_name: savedTemplateId,
        layout_preferences: layoutPreferences,
      });
      setResume({
        ...updated,
        template_name: savedTemplateId,
        layout_preferences: layoutPreferences,
      });
      setHtmlDraft(ensureUtf8HtmlDocument(String(updated.output_html || '').trim()));
      setRecentResumes((prev) => prev.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save HTML failed');
    } finally {
      setSavingHtml(false);
    }
  };

  const handleGuidanceChange = (next: RenderGuidanceSettings) => {
    setActiveTemplateId('');
    setGuidance(next);
  };

  const handleSectionsChange = (next: BuilderSectionDraft[]) => {
    setActiveTemplateId('');
    setSections(next);
  };

  useEffect(() => {
    if (!layoutPreviewLinked) return;
    if (!resume?.resume_obj || Object.keys(resume.resume_obj).length === 0) return;
    const resumeObj = resume.resume_obj as Record<string, unknown>;
    const dynamicSections = mergeCustomSectionsFromJson(resumeObj, sections);
    const rebuilt = ensureUtf8HtmlDocument(
      renderResumeHtmlFromLayout({
        resumeObj,
        guidance,
        sections: dynamicSections,
      }),
    );
    if (rebuilt !== htmlDraft) {
      setHtmlDraft(rebuilt);
    }
  }, [guidance, sections, resume?.id, resume?.resume_obj, layoutPreviewLinked, htmlDraft]);

  const footerTimestamp = useMemo(() => new Date().toLocaleString(), []);

  return (
    <>
    <PageTransition>
      <BuilderLayout
        title=""
        statusText=""
        unsavedLabel={undefined}
        compactHeader
        actions={
          <>
            <select
              value={resume?.id || activeResumeId}
              onChange={(event) => {
                const nextId = event.target.value;
                if (!nextId) return;
                if (id) {
                  navigate(`/resumes/${nextId}`);
                } else {
                  setSearchParams({ resumeId: nextId }, { replace: true });
                }
              }}
              className="h-10 min-w-[14rem] border border-black dark:border-gray-600 bg-[var(--brand-paper)] px-3 font-mono text-xs uppercase tracking-wide outline-none focus:border-[var(--brand-signal)]"
            >
              {recentResumes.length === 0 ? <option value="">{t('dashboard.noResumes')}</option> : null}
              {recentResumes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
            <Link
              to={`/tailor?resumeId=${resume?.id || activeResumeId}`}
              className="inline-flex items-center gap-1.5 rounded border border-black dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wide hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <WandSparkles className="size-3.5" />
              {t('nav.tailor')}
            </Link>
            <Button onClick={() => void handleSaveHtml()} disabled={savingHtml || !resume?.id}>
              <Save />
              {savingHtml ? t('common.saving') : t('common.save')}
            </Button>
            <Button variant="outline" onClick={handleDownload} disabled={!resume?.id}>
              <Download />
              {t('resume.exportHtml')}
            </Button>
            <Button variant="outline" onClick={() => void handleDownloadPdf()} disabled={savingPdf || !resume?.resume_obj}>
              <FileText />
              {savingPdf ? t('common.generating') : t('resume.exportPdf')}
            </Button>
            <Button variant="outline" onClick={() => void handleDownloadTex()} disabled={savingTex || !resume?.resume_obj}>
              <ClipboardCopy />
              {savingTex ? t('common.generating') : t('resume.copyLatex')}
            </Button>
          </>
        }
        editorPanel={
          <div className="flex h-full flex-col">
            <div className="shrink-0" style={{ maxHeight: '40%', overflow: 'auto' }}>
              <TemplateSidebar
                activeTemplateId={activeTemplateId}
                onSelectBuiltin={handleSelectBuiltin}
                onSelectCustom={handleSelectCustom}
              />
            </div>
            <div className="flex-1 overflow-auto border-t border-[var(--brand-line)]">
              <EditorPanel
                guidance={guidance}
                onGuidanceChange={handleGuidanceChange}
                sections={sections}
                onSectionsChange={handleSectionsChange}
                contentOverflows={contentOverflows}
              />
            </div>
          </div>
        }
        previewPanel={
          <PreviewPanel
            htmlDraft={htmlDraft}
            dirtyHtml={dirtyHtml}
            loading={loading}
            error={error}
            savingHtml={savingHtml}
            guidance={guidance}
            onGuidanceChange={handleGuidanceChange}
            onOverflowChange={setContentOverflows}
            onResetHtml={() => {
              const fallbackHtml = renderResumeHtmlFromLayout({
                resumeObj: (resume?.resume_obj || {}) as Record<string, unknown>,
                guidance,
                sections,
              });
              setHtmlDraft(persistedHtml || fallbackHtml);
              setLayoutPreviewLinked(true);
            }}
          />
        }
        footerLeft={`Resume ID: ${resume?.id || 'N/A'}`}
        footerRight={`Workbench Updated: ${footerTimestamp}`}
      />

    </PageTransition>

    {/* Overleaf modal */}
    {showOverleafModal && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setShowOverleafModal(false)}>
        <div className="mx-4 w-full max-w-sm overflow-hidden border-2 border-black bg-white shadow-[8px_8px_0px_0px_#000000]" onClick={e => e.stopPropagation()}>
          <div className="flex items-center justify-between border-b-2 border-black bg-green-50 px-4 py-3">
            <h3 className="font-serif text-base font-bold text-green-900">{t('resume.overleafTitle')}</h3>
            <button onClick={() => setShowOverleafModal(false)} className="text-green-700 hover:text-green-900">
              <X className="size-4" />
            </button>
          </div>
          <div className="px-4 py-4">
            <p className="font-sans text-[13px] leading-6 text-gray-700">{t('resume.overleafBody')}</p>
            <a
              href="https://www.overleaf.com/project"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded border-2 border-black bg-black px-4 py-2.5 font-mono text-[13px] font-semibold text-white transition-all hover:bg-gray-800 hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-none"
              onClick={() => setShowOverleafModal(false)}
            >
              <ExternalLink className="size-4" />
              {t('resume.overleafButton')}
            </a>
          </div>
        </div>
      </div>
    )}
    </>
  );
}
