import { ArrowLeft } from 'lucide-react';
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
  return (
    <section className="brand-grid-bg h-screen w-full overflow-hidden px-3 py-3 md:px-6 md:py-5">
      <div className="mx-auto flex h-full max-w-[96rem] flex-col rounded-2xl border border-[var(--brand-line)] bg-[var(--brand-paper)] shadow-sm">
        <header className={`border-b px-4 md:px-6 ${compactHeader ? 'py-2.5 md:py-3' : 'py-4 md:py-5'}`}>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
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
            <div className="flex flex-wrap items-center gap-2">{actions}</div>
          </div>
        </header>

        <main className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[24rem_1px_minmax(0,1fr)]">
          <div className="min-h-0 overflow-y-auto bg-[var(--brand-paper)] p-4 md:p-5">{editorPanel}</div>
          <div className="hidden bg-black dark:bg-zinc-600 lg:block" />
          <div className="min-h-0 overflow-hidden bg-[var(--brand-surface-soft)]">{previewPanel}</div>
        </main>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3 font-mono text-[10px] tracking-[0.08em] text-[var(--brand-signal)] md:px-6">
          <span>{footerLeft}</span>
          <span>{footerRight}</span>
        </footer>
      </div>
    </section>
  );
}
