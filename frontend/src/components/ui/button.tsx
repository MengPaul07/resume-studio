import * as React from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'success' | 'warning' | 'running' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    const baseStyles = cn(
      'inline-flex items-center justify-center gap-2 whitespace-nowrap font-sans font-medium',
      'transition-all duration-150 ease-out rounded-lg',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-signal)] focus-visible:ring-offset-2',
      'disabled:pointer-events-none disabled:opacity-50',
      "[&_svg:not([class*='size-'])]:size-4 [&_svg]:shrink-0"
    );

    const variants = {
      default:
        'bg-[var(--brand-signal)] text-white border border-transparent shadow-sm hover:brightness-110 active:brightness-95',
      destructive:
        'bg-[var(--status-failed)] text-white border border-transparent shadow-sm hover:brightness-110 active:brightness-95',
      success:
        'bg-[var(--status-done)] text-white border border-transparent shadow-sm hover:brightness-110 active:brightness-95',
      warning:
        'bg-[var(--status-warning)] text-white border border-transparent shadow-sm hover:brightness-110 active:brightness-95',
      running:
        'bg-[var(--status-running)] text-white border border-transparent shadow-sm hover:brightness-110 active:brightness-95',
      outline:
        'bg-[var(--brand-paper)] text-[var(--brand-ink)] border border-[var(--brand-line)] shadow-sm hover:bg-[var(--brand-surface-soft)] active:bg-white dark:active:bg-zinc-700',
      secondary:
        'bg-[var(--brand-surface-soft)] text-[var(--brand-ink)] border border-transparent shadow-sm hover:bg-[#ebebeb] active:bg-white dark:active:bg-zinc-700',
      ghost: 'bg-transparent text-[var(--brand-ink)] border-none shadow-none hover:bg-[var(--brand-signal-soft)] active:bg-[var(--brand-surface-soft)]',
      link: 'bg-transparent text-[var(--brand-signal)] border-none shadow-none underline-offset-4 hover:underline p-0 h-auto',
    };

    const sizes = {
      default: 'h-10 px-6 py-2 text-sm font-medium',
      sm: 'h-8 px-4 py-1 text-xs font-medium',
      lg: 'h-12 px-8 py-3 text-base font-semibold',
      icon: 'h-10 w-10 p-0',
    };

    return <button ref={ref} className={cn(baseStyles, variants[variant], sizes[size], className)} {...props} />;
  }
);

Button.displayName = 'Button';

export { Button };
