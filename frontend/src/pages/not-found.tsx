import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <main className="min-h-screen grid place-items-center bg-background px-4">
      <div className="border border-black dark:border-zinc-600 bg-[var(--brand-surface)] p-10 shadow-[6px_6px_0px_0px_#000] dark:shadow-none text-center">
        <h1 className="font-serif text-6xl uppercase">404</h1>
        <p className="font-mono text-xs uppercase text-[var(--brand-ink-muted)] mt-3">Page not found</p>
        <Link to="/dashboard" className="inline-block mt-6 border border-black dark:border-zinc-600 px-4 py-2 font-mono text-xs uppercase bg-[var(--brand-paper)] hover:bg-[var(--brand-ink)] hover:text-white transition-colors">
          Back to Dashboard
        </Link>
      </div>
    </main>
  );
}
