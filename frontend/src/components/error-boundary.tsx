import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-[var(--brand-surface)] px-4">
          <div className="w-full max-w-lg border-2 border-black dark:border-zinc-600 bg-white dark:bg-zinc-900 p-8 shadow-[6px_6px_0px_0px_#000000] dark:shadow-none">
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-[var(--brand-signal)]">
              Runtime Error
            </p>
            <h1 className="mt-2 font-serif text-3xl uppercase">Something went wrong</h1>
            <pre className="mt-4 max-h-40 overflow-auto border border-black/20 bg-[var(--brand-surface-soft)] p-3 font-mono text-[11px] leading-relaxed text-gray-800 dark:text-zinc-200">
              {this.state.error.message}
            </pre>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-6 inline-flex items-center gap-2 border border-black dark:border-zinc-600 bg-[var(--brand-paper)] px-4 py-2 font-mono text-xs uppercase hover:bg-[var(--brand-ink)] hover:text-white"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
