import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.DEV) {
      console.error('[ErrorBoundary]', error, info.componentStack);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-[#f5f5f7] p-8">
          <div className="max-w-md rounded-2xl bg-white dark:bg-zinc-900 p-8 text-center shadow-sm ring-1 ring-gray-200/50">
            <h2 className="font-sans text-lg font-semibold text-gray-900 dark:text-zinc-100">Something went wrong</h2>
            <p className="mt-2 text-sm text-gray-500 dark:text-zinc-400">
              An unexpected error occurred. Try refreshing the page.
            </p>
            {import.meta.env.DEV && this.state.error && (
              <pre className="mt-4 max-h-40 overflow-auto rounded bg-gray-100 dark:bg-zinc-800 p-3 text-left text-xs text-gray-700 dark:text-zinc-300">
                {this.state.error.message}
              </pre>
            )}
            <button
              onClick={() => window.location.reload()}
              className="mt-6 rounded-lg bg-gray-900 dark:bg-zinc-700 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 dark:hover:bg-zinc-600"
            >
              Reload page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
