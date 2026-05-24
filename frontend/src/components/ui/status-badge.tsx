import { cn } from '../../lib/utils';
import type { ReactNode } from 'react';

export type StatusVariant = 'default' | 'running' | 'success' | 'error' | 'warning';

export function StatusBadge({
  variant = 'default',
  children,
  className,
}: {
  variant?: StatusVariant;
  children: ReactNode;
  className?: string;
}) {
  const variants: Record<StatusVariant, string> = {
    default: 'bg-[var(--brand-surface)] text-[var(--brand-ink)] border-[var(--brand-line-strong)]',
    running: 'bg-[var(--brand-signal-soft)] text-[var(--status-running)] border-[var(--status-running)]',
    success: 'bg-[#e9f8ef] text-[var(--status-done)] border-[var(--status-done)]',
    error: 'bg-[#ffe9e5] text-[var(--status-failed)] border-[var(--status-failed)]',
    warning: 'bg-[#fff2df] text-[var(--status-warning)] border-[var(--status-warning)]',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide',
        'rounded-lg',
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
