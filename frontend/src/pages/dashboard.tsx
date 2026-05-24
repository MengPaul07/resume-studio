import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Folder, FolderArchive, PencilRuler, PenLine, Sparkles, Upload } from 'lucide-react';
import {
  deleteImportedFile,
  deleteRecentResume,
  importFileOnly,
  listImportedFiles,
  listRecentResumes,
  runAgentFromImport,
  saveRecentResume,
} from '../api';
import { StatusBadge } from '../components/ui/status-badge';
import type { ImportedFileRecord, RecentResumeRecord } from '../types';

const ACCEPTED_EXTS = ['.pdf', '.doc', '.docx'];

const iconMap = {
  purple: PenLine,
  blue: PencilRuler,
  green: Sparkles,
  orange: FolderArchive,
};

const workflowModules = [
  {
    title: 'Build',
    desc: 'Start from scratch — AI interviews you to build a resume.',
    to: '',
    tone: 'purple' as const,
    action: 'build' as const,
  },
  {
    title: 'Import',
    desc: 'Upload PDF/DOCX and let AI parse and structure it.',
    to: '',
    tone: 'orange' as const,
    action: 'import' as const,
  },
  {
    title: 'Structure',
    desc: 'Open builder and adjust layout/sections.',
    to: '/builder',
    tone: 'blue' as const,
    action: 'structure' as const,
  },
  {
    title: 'Tailor',
    desc: 'Open an existing resume and refine with AI.',
    to: '/tailor',
    tone: 'green' as const,
    action: 'tailor' as const,
  },
  {
    title: 'Interview',
    desc: 'Practice mock interviews with AI tailored to your resume.',
    to: '/interview',
    tone: 'blue' as const,
    action: 'interview' as const,
  },
];

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function DashboardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [importing, setImporting] = useState(false);
  const [importStatus, setImportStatus] = useState('');
  const [importError, setImportError] = useState('');
  const [importedFiles, setImportedFiles] = useState<ImportedFileRecord[]>([]);
  const [recentResumes, setRecentResumes] = useState<RecentResumeRecord[]>([]);

  const toResumeTitleFromFile = (fileName: string): string => {
    const base = (fileName || 'Imported Resume').replace(/\.[^.]+$/, '').trim();
    return base || 'Imported Resume';
  };

  useEffect(() => {
    listImportedFiles()
      .then(setImportedFiles)
      .catch((err) => {
        setImportError(getErrorMessage(err, 'Failed to load imported files'));
      });

    listRecentResumes()
      .then(setRecentResumes)
      .catch((err) => {
        setImportError(getErrorMessage(err, 'Failed to load recent resumes'));
      });
  }, []);

  const handlePickFile = () => {
    fileInputRef.current?.click();
  };

  const buildRecentFromImport = async (item: ImportedFileRecord) => {
    setImportStatus('Building resume and preparing AI Tailor...');

    const runResult = await runAgentFromImport({
      import_id: item.id,
      max_iterations: 2,
      use_llm: true,
    });

    const resumeObj =
      (runResult.refined_resume_obj && Object.keys(runResult.refined_resume_obj).length > 0
        ? runResult.refined_resume_obj
        : runResult.resume_obj) || {};

    if (!resumeObj || Object.keys(resumeObj).length === 0) {
      throw new Error('Build completed but resume_obj is empty.');
    }

    const saved = await saveRecentResume({
      title: toResumeTitleFromFile(item.file_name),
      status: 'ready',
      source: 'import',
      tags: ['import'],
      resume_obj: resumeObj,
      output_markdown: runResult.output_markdown || '',
      output_html: runResult.output_html || '',
    });

    setRecentResumes((prev) => [saved, ...prev.filter((x) => x.id !== saved.id)]);
    setImportStatus(`Ready: ${saved.title}. Opening AI Tailor...`);
    navigate(`/tailor?resumeId=${encodeURIComponent(saved.id)}`);
  };

  const handleFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    event.target.value = '';
    if (!selected) return;

    const lowerName = selected.name.toLowerCase();
    const supported = ACCEPTED_EXTS.some((ext) => lowerName.endsWith(ext));
    if (!supported) {
      setImportError(`Unsupported file type. Supported: ${ACCEPTED_EXTS.join(', ')}`);
      setImportStatus('');
      return;
    }

    setImporting(true);
    setImportError('');
    setImportStatus('Extracting raw text and saving import...');
    try {
      const item = await importFileOnly(selected);
      setImportedFiles((prev) => [item, ...prev]);
      setImportStatus('Import saved.');
      await buildRecentFromImport(item);
    } catch (error) {
      setImportError(getErrorMessage(error, 'Import failed'));
      setImportStatus('');
    } finally {
      setImporting(false);
    }
  };

  const handleRunImport = async (item: ImportedFileRecord) => {
    if (importing) return;
    setImporting(true);
    setImportError('');
    try {
      await buildRecentFromImport(item);
    } catch (error) {
      setImportError(getErrorMessage(error, 'Build from import failed'));
      setImportStatus('');
    } finally {
      setImporting(false);
    }
  };

  const handleDeleteImport = async (id: string) => {
    const yes = window.confirm('Delete this imported raw file record?');
    if (!yes) return;
    try {
      await deleteImportedFile(id);
      setImportedFiles((prev) => prev.filter((x) => x.id !== id));
    } catch (err) {
      setImportError(getErrorMessage(err, 'Delete import failed'));
    }
  };

  const handleDeleteRecent = async (id: string) => {
    const yes = window.confirm('Delete this generated resume record?');
    if (!yes) return;
    try {
      await deleteRecentResume(id);
      setRecentResumes((prev) => prev.filter((x) => x.id !== id));
    } catch (err) {
      setImportError(getErrorMessage(err, 'Delete recent resume failed'));
    }
  };

  return (
    <section className="min-h-screen px-4 py-8 md:px-8">
      <div className="mx-auto max-w-[88rem] rounded-2xl border border-[var(--brand-line)] bg-[var(--brand-paper)] shadow-sm">
        <header className="border-b border-[var(--brand-line)] p-6 md:p-8">
          <div className="grid gap-4 md:grid-cols-[1.6fr_1fr] md:items-end">
            <div>
              <p className="font-sans text-xs font-semibold tracking-[0.14em] text-[var(--brand-signal)]">
                {t('dashboard.workflowConsole')}
              </p>
              <h1 className="mt-2 font-sans text-3xl font-bold leading-tight tracking-tight md:text-5xl text-[var(--brand-ink)] dark:text-zinc-100">{t('dashboard.title')}</h1>
              <p className="mt-3 max-w-2xl font-sans text-sm text-[var(--brand-ink-muted)]">
                {t('dashboard.subtitle')}
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg border border-[var(--brand-line)] bg-[var(--brand-surface)] p-3">
                <p className="font-sans text-[11px] font-medium text-[var(--brand-ink-muted)]">{t('dashboard.imports')}</p>
                <p className="font-sans text-xl font-bold text-[var(--brand-ink)] dark:text-zinc-100">{importedFiles.length}</p>
              </div>
              <div className="rounded-lg border border-[var(--brand-line)] bg-[var(--brand-surface)] p-3">
                <p className="font-sans text-[11px] font-medium text-[var(--brand-ink-muted)]">{t('dashboard.resumes')}</p>
                <p className="font-sans text-xl font-bold text-[var(--brand-ink)] dark:text-zinc-100">{recentResumes.length}</p>
              </div>
              <div className="rounded-lg border border-[var(--brand-line)] bg-[var(--brand-surface)] p-3">
                <p className="font-sans text-[11px] font-medium text-[var(--brand-ink-muted)]">{t('dashboard.engine')}</p>
                <StatusBadge variant="success" className="mt-1">{t('dashboard.ready')}</StatusBadge>
              </div>
            </div>
          </div>
        </header>

        <main className="grid gap-4 lg:grid-cols-[1.2fr_1.8fr]">
          <section className="bg-[var(--brand-surface)] p-5 md:p-6">
            <h2 className="font-sans text-xs font-semibold tracking-wider text-[var(--brand-signal)]">{t('dashboard.studioFlow')}</h2>
            <div className="mt-4 space-y-3">
              {workflowModules.map((module, idx) => {
                const Icon = iconMap[module.tone];
                return (
                  <div key={module.title} className="relative border border-[var(--brand-line)] bg-[var(--brand-paper)] p-4">
                    <span className="absolute -left-2 -top-2 inline-flex h-6 w-6 items-center justify-center border border-[var(--brand-line)] bg-[var(--brand-signal)] font-mono text-[10px] text-white">
                      {idx + 1}
                    </span>
                    <div className="flex items-start gap-3">
                      <span className="inline-flex h-9 w-9 items-center justify-center border border-[var(--brand-line)] bg-[var(--brand-surface-soft)]">
                        <Icon className="size-4 text-[var(--brand-signal)]" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="font-sans text-lg font-semibold text-[var(--brand-ink)]">{t(`dashboard.${module.action}.title`)}</p>
                        <p className="mt-1 font-sans text-xs font-semibold tracking-wide text-[var(--brand-ink-muted)]">
                          {t(`dashboard.${module.action}.desc`)}
                        </p>
                      </div>
                    </div>
                    {module.action === 'build' ? (
                      <Link
                        to="/create"
                        className="mt-3 inline-flex items-center gap-1 border border-[var(--brand-line)] bg-[var(--brand-paper)] dark:bg-zinc-800 dark:text-zinc-100 px-2 py-1 font-sans text-[11px] font-medium tracking-wide hover:bg-[var(--brand-ink)] hover:text-white disabled:opacity-50"
                      >
                        <><Sparkles className="size-3" /> {t('dashboard.startBuild')}</>
                      </Link>
                    ) : module.action === 'import' ? (
                      <button
                        type="button"
                        onClick={handlePickFile}
                        className="mt-3 inline-flex items-center gap-1 border border-[var(--brand-line)] bg-[var(--brand-paper)] dark:bg-zinc-800 dark:text-zinc-100 px-2 py-1 font-sans text-[11px] font-medium tracking-wide hover:bg-[var(--brand-ink)] hover:text-white"
                      >
                        {t('dashboard.upload')} <Upload className="size-3" />
                      </button>
                    ) : module.to ? (
                      <Link
                        to={module.to}
                        className="mt-3 inline-flex items-center gap-1 border border-[var(--brand-line)] bg-[var(--brand-paper)] dark:bg-zinc-800 dark:text-zinc-100 px-2 py-1 font-sans text-[11px] font-medium tracking-wide hover:bg-[var(--brand-ink)] hover:text-white"
                      >
                        {t('dashboard.open')} <ArrowRight className="size-3" />
                      </Link>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </section>

          <section className="grid gap-4 md:grid-cols-2">
            <div className="bg-[var(--brand-paper)] p-5 md:p-6">
              <h2 className="font-sans text-xs font-semibold tracking-wider text-[var(--brand-signal)]">{t('dashboard.importedRawText')}</h2>
              <p className="mt-1 font-sans text-[11px] font-medium text-[var(--brand-ink-muted)]">{t('dashboard.importHint')}</p>
              <input ref={fileInputRef} type="file" className="hidden" accept={ACCEPTED_EXTS.join(',')} onChange={handleFileSelected} />
              <div className="mt-3 space-y-2 max-h-[50vh] overflow-auto pr-1">
                {importStatus ? <StatusBadge variant="success">{importStatus}</StatusBadge> : null}
                {importError ? <StatusBadge variant="error">{importError}</StatusBadge> : null}
                {importedFiles.length === 0 ? (
                  <div className="rounded-lg border border-[var(--brand-line)] bg-[var(--brand-surface)] p-3 font-sans text-sm text-[var(--brand-ink-muted)]">
                    {t('dashboard.noImports')}
                  </div>
                ) : null}
                {importedFiles.map((item) => (
                  <article key={item.id} className="border border-[var(--brand-line)] bg-[var(--brand-surface)]">
                    <div className="flex items-center justify-between border-b border-[var(--brand-line)] bg-[var(--brand-surface-soft)] px-3 py-2">
                      <span className="inline-flex items-center gap-1 font-sans text-[11px] font-medium tracking-wide text-[var(--brand-ink-muted)]">
                        <Folder className="size-3" />
                        {t('dashboard.importFolder')}
                      </span>
                      <span className="font-sans text-[11px] font-medium text-[var(--brand-ink-muted)]">{item.file_ext}</span>
                    </div>
                    <div className="p-3">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-sans text-xs font-semibold">{item.file_name}</p>
                      <div className="flex shrink-0 items-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleRunImport(item)}
                          disabled={importing}
                          className="rounded-md border border-[var(--brand-line)] bg-white dark:bg-gray-800 dark:text-zinc-200 px-2.5 py-1 font-sans text-xs font-medium hover:bg-[var(--brand-surface-soft)] dark:hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {t('dashboard.run')}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteImport(item.id)}
                          disabled={importing}
                          className="border border-[var(--status-failed)] px-2 py-0.5 font-sans text-[11px] font-medium text-[var(--status-failed)] hover:bg-[var(--status-failed)] hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {t('common.delete')}
                        </button>
                      </div>
                    </div>
                    <p className="mt-1 font-sans text-[11px] font-medium text-[var(--brand-ink-muted)]">
                      {item.file_ext} · {item.char_count} chars
                    </p>
                    <p className="mt-2 line-clamp-2 text-xs text-[var(--brand-ink-muted)]">{item.raw_text_preview || '-'}</p>
                    </div>
                  </article>
                ))}
              </div>
            </div>

            <div className="bg-[var(--brand-paper)] p-5 md:p-6">
              <h2 className="font-sans text-xs font-semibold tracking-wider text-[var(--brand-signal)]">{t('dashboard.recentResumes')}</h2>
              <p className="mt-1 font-sans text-[11px] font-medium text-[var(--brand-ink-muted)]">{t('dashboard.resumeHint')}</p>
              <div className="mt-3 space-y-2 max-h-[50vh] overflow-auto pr-1">
                {recentResumes.length === 0 ? (
                  <div className="rounded-lg border border-[var(--brand-line)] bg-[var(--brand-surface)] p-3 font-sans text-sm text-[var(--brand-ink-muted)]">
                    {t('dashboard.noResumes')}
                  </div>
                ) : null}
                {recentResumes.map((item) => (
                  <article key={item.id} className="border border-[var(--brand-line)] bg-[var(--brand-surface)]">
                    <div className="flex items-center justify-between border-b border-[var(--brand-line)] bg-[var(--brand-surface-soft)] px-3 py-2">
                      <span className="inline-flex items-center gap-1 font-sans text-[11px] font-medium tracking-wide text-[var(--brand-ink-muted)]">
                        <Folder className="size-3" />
                        {t('dashboard.resumeFolder')}
                      </span>
                      <span className="font-sans text-[11px] font-medium text-[var(--brand-ink-muted)]">{item.status}</span>
                    </div>
                    <div className="p-3">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-sans text-xs font-semibold text-[var(--brand-ink)] dark:text-zinc-100">{item.title}</p>
                      <button
                        type="button"
                        onClick={() => handleDeleteRecent(item.id)}
                        className="border border-[var(--status-failed)] px-2 py-0.5 font-sans text-[11px] font-medium text-[var(--status-failed)] hover:bg-[var(--status-failed)] hover:text-white"
                      >
                        {t('common.delete')}
                      </button>
                    </div>
                    <p className="mt-1 font-sans text-[11px] font-medium text-[var(--brand-ink-muted)]">
                      {item.source} · {item.status}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Link
                        to={`/tailor?resumeId=${encodeURIComponent(item.id)}`}
                        className="inline-flex items-center rounded-lg border border-[var(--brand-line)] px-3 py-1.5 font-sans text-xs font-medium bg-white dark:bg-gray-800 dark:text-zinc-200 hover:bg-[var(--brand-surface-soft)] dark:hover:bg-zinc-700 hover:text-[var(--brand-ink)]"
                      >
                        {t('dashboard.aiTailor')}
                      </Link>
                      <Link
                        to={`/builder?resumeId=${encodeURIComponent(item.id)}`}
                        className="inline-flex items-center rounded-lg border border-[var(--brand-line)] px-3 py-1.5 font-sans text-xs font-medium bg-white dark:bg-gray-800 dark:text-zinc-200 hover:bg-[var(--brand-surface-soft)] dark:hover:bg-zinc-700 hover:text-[var(--brand-ink)]"
                      >
                        {t('dashboard.resumeView')}
                      </Link>
                    </div>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </section>
        </main>
      </div>
    </section>
  );
}
