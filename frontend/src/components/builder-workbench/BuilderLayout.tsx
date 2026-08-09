import { useRef, useState } from 'react';
import { ArrowLeft, ChevronDown, Eye, SlidersHorizontal } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface BuilderLayoutProps {
  title: string;
  statusText: string;
  unsavedLabel?: string;
  compactHeader?: boolean;
  actions: ReactNode;
  editorPanel: ReactNode;
  previewPanel: ReactNode;
  footerLeft: string;
  footerRight: string;
}

export function BuilderLayout({
  title,
  statusText,
  unsavedLabel,
  compactHeader = false,
  actions,
  editorPanel,
  previewPanel,
  footerLeft,
  footerRight,
}: BuilderLayoutProps) {
  const { t, i18n } = useTranslation();
  const [mobileMode, setMobileMode] = useState<'edit' | 'preview'>('edit');
  const mobileActionsRef = useRef<HTMLDetailsElement | null>(null);
  const isZh = i18n.language.startsWith('zh');

  return (
    <section className="brand-grid-bg w-full overflow-hidden md:h-[calc(100vh-3.5rem)] md:px-6 md:py-5">
      <div className="flex h-[calc(100dvh-3.5rem)] flex-col bg-[var(--brand-paper)] md:hidden">
        <header className="shrink-0 border-b border-[var(--brand-line)] bg-[var(--brand-surface)] px-4 py-3">
          <div className="flex min-h-11 items-center gap-3">
            <Link
              to="/dashboard"
              aria-label="Back"
              className="inline-flex size-11 shrink-0 items-center justify-center rounded-lg bg-[var(--brand-surface-soft)] text-[var(--brand-ink)]"
            >
              <ArrowLeft className="size-5" />
            </Link>
            <div className="min-w-0 flex-1">
              <h1 className="truncate font-sans text-lg font-semibold leading-tight text-[var(--brand-ink)]">{title || t('nav.layoutBuilder')}</h1>
              <p className="mt-0.5 truncate text-xs text-[var(--brand-ink-muted)]">
                {statusText || (mobileMode === 'edit'
                  ? isZh ? '调整版式与内容' : 'Edit layout and content'
                  : isZh ? '检查最终页面' : 'Check the final page')}
              </p>
            </div>
            {unsavedLabel ? (
              <span className="shrink-0 rounded-md bg-[var(--status-warning)] px-2 py-1 text-[10px] font-semibold text-white">
                {unsavedLabel}
              </span>
            ) : null}
          </div>
          <details ref={mobileActionsRef} className="mobile-disclosure mt-3">
            <summary className="flex min-h-11 cursor-pointer list-none items-center gap-3 rounded-lg bg-[var(--brand-surface-soft)] px-3 text-sm font-semibold [&::-webkit-details-marker]:hidden">
              <SlidersHorizontal className="size-4 text-[var(--brand-signal)]" />
              <span className="flex-1">{isZh ? '简历与导出选项' : 'Resume and export options'}</span>
              <ChevronDown className="mobile-disclosure-chevron size-4 text-[var(--brand-ink-muted)]" />
            </summary>
            <div className="mobile-action-grid mt-2 grid grid-cols-2 gap-2 rounded-lg border border-[var(--brand-line)] bg-[var(--brand-surface)] p-2">
              {actions}
            </div>
          </details>
        </header>

        <main className="min-h-0 flex-1 overflow-hidden">
          <div className={`${mobileMode === 'edit' ? 'block' : 'hidden'} h-full overflow-y-auto overscroll-contain bg-[var(--brand-paper)] p-3`}>
            {editorPanel}
          </div>
          <div className={`${mobileMode === 'preview' ? 'block' : 'hidden'} h-full overflow-hidden bg-[var(--brand-surface-soft)]`}>
            {previewPanel}
          </div>
        </main>

        <nav aria-label="Builder workspace" className="grid shrink-0 grid-cols-2 gap-1 border-t border-[var(--brand-line)] bg-[var(--brand-surface)] p-2">
          <button
            type="button"
            onClick={() => setMobileMode('edit')}
            className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg text-sm font-semibold ${
              mobileMode === 'edit' ? 'bg-[var(--brand-signal)] text-white' : 'text-[var(--brand-ink-muted)]'
            }`}
          >
            <SlidersHorizontal className="size-4" /> {t('common.edit')}
          </button>
          <button
            type="button"
            onClick={() => {
              if (mobileActionsRef.current) mobileActionsRef.current.open = false;
              setMobileMode('preview');
            }}
            className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg text-sm font-semibold ${
              mobileMode === 'preview' ? 'bg-[var(--brand-signal)] text-white' : 'text-[var(--brand-ink-muted)]'
            }`}
          >
            <Eye className="size-4" /> {t('common.preview')}
          </button>
        </nav>
      </div>

      <div className="mx-auto hidden h-full max-w-[96rem] flex-col overflow-hidden rounded-2xl border border-[var(--brand-line)] bg-[var(--brand-paper)] shadow-sm md:flex">
        <header className={`shrink-0 border-b px-6 ${compactHeader ? 'py-3' : 'py-5'}`}>
          <div className="flex items-center justify-between gap-3">
            <div className="shrink-0">
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-1 font-mono text-[11px] tracking-[0.08em] text-[var(--brand-signal)] underline-offset-4 hover:underline"
              >
                <ArrowLeft className="size-3.5" />
                Back
              </Link>
              {!compactHeader ? (
                <>
                  <h1 className="mt-2 font-serif text-4xl leading-none tracking-tight md:text-5xl">
                    Builder
                  </h1>
                  <p className="mt-2 flex flex-wrap items-center gap-2 font-mono text-[11px] tracking-[0.08em] text-[var(--brand-signal)]">
                    <span>{statusText}</span>
                    {unsavedLabel ? (
                      <span className="rounded-md border bg-[#fce6a3] px-2 py-0.5 text-black dark:text-zinc-900">{unsavedLabel}</span>
                    ) : null}
                  </p>
                  <p className="mt-1 font-serif text-base tracking-tight">{title}</p>
                </>
              ) : null}
            </div>
            <div className="flex min-w-0 flex-1 items-center justify-end gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">{actions}</div>
          </div>
        </header>

        <main className="grid min-h-0 flex-1 grid-cols-[24rem_1px_minmax(0,1fr)]">
          <div className="min-h-0 overflow-y-auto bg-[var(--brand-paper)] p-5">{editorPanel}</div>
          <div className="bg-black dark:bg-zinc-600" />
          <div className="min-h-0 overflow-hidden bg-[var(--brand-surface-soft)]">{previewPanel}</div>
        </main>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t px-6 py-3 font-mono text-[10px] tracking-[0.08em] text-[var(--brand-signal)]">
          <span>{footerLeft}</span>
          <span>{footerRight}</span>
        </footer>
      </div>
    </section>
  );
}
