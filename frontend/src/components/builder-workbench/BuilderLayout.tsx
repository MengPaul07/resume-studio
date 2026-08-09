import { useState } from 'react';
import { ArrowLeft, Eye, SlidersHorizontal } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

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
  const [mobileMode, setMobileMode] = useState<'edit' | 'preview'>('edit');

  return (
    <section className="brand-grid-bg h-[calc(100dvh-8rem)] min-h-[32rem] w-full overflow-hidden md:h-[calc(100vh-3.5rem)] md:px-6 md:py-5">
      <div className="mx-auto flex h-full max-w-[96rem] flex-col overflow-hidden border-[var(--brand-line)] bg-[var(--brand-paper)] md:rounded-2xl md:border md:shadow-sm">
        <header className={`shrink-0 border-b px-3 md:px-6 ${compactHeader ? 'py-2 md:py-3' : 'py-3 md:py-5'}`}>
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
            <div className="flex min-w-0 flex-1 items-center justify-start gap-2 overflow-x-auto pb-1 [scrollbar-width:none] md:justify-end [&::-webkit-scrollbar]:hidden">{actions}</div>
          </div>
          <div className="mt-2 grid grid-cols-2 rounded-lg bg-[var(--brand-surface-soft)] p-1 lg:hidden">
            <button
              type="button"
              onClick={() => setMobileMode('edit')}
              className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md text-sm font-semibold ${mobileMode === 'edit' ? 'bg-[var(--brand-surface)] text-[var(--brand-signal)] shadow-sm' : 'text-[var(--brand-ink-muted)]'}`}
            >
              <SlidersHorizontal className="size-4" /> Edit
            </button>
            <button
              type="button"
              onClick={() => setMobileMode('preview')}
              className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md text-sm font-semibold ${mobileMode === 'preview' ? 'bg-[var(--brand-surface)] text-[var(--brand-signal)] shadow-sm' : 'text-[var(--brand-ink-muted)]'}`}
            >
              <Eye className="size-4" /> Preview
            </button>
          </div>
        </header>

        <main className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[24rem_1px_minmax(0,1fr)]">
          <div className={`${mobileMode === 'edit' ? 'block' : 'hidden'} min-h-0 overflow-y-auto bg-[var(--brand-paper)] p-3 md:p-5 lg:block`}>{editorPanel}</div>
          <div className="hidden bg-black dark:bg-zinc-600 lg:block" />
          <div className={`${mobileMode === 'preview' ? 'block' : 'hidden'} min-h-0 overflow-hidden bg-[var(--brand-surface-soft)] lg:block`}>{previewPanel}</div>
        </main>

        <footer className="hidden flex-wrap items-center justify-between gap-3 border-t px-4 py-3 font-mono text-[10px] tracking-[0.08em] text-[var(--brand-signal)] md:flex md:px-6">
          <span>{footerLeft}</span>
          <span>{footerRight}</span>
        </footer>
      </div>
    </section>
  );
}
