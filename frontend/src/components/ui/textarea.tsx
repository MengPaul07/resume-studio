import * as React from 'react';
import { cn } from '../../lib/utils';

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({ className, ...props }, ref) => {
  return (
    <textarea
      ref={ref}
      className={cn(
        'min-h-[160px] w-full rounded-lg border border-[var(--brand-line)] bg-[var(--brand-paper)] px-4 py-3 text-sm font-sans text-[var(--brand-ink)]',
        'placeholder:text-[var(--brand-ink-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-signal)] focus-visible:ring-offset-2',
        className
      )}
      {...props}
    />
  );
});

Textarea.displayName = 'Textarea';

export { Textarea };
