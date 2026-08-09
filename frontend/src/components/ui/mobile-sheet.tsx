import { useEffect, useId, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

interface MobileSheetProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  fullScreen?: boolean;
}

export function MobileSheet({ open, title, onClose, children, fullScreen = false }: MobileSheetProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      className={`mobile-sheet fixed inset-x-0 bottom-0 top-auto m-0 w-full max-w-none overflow-hidden border-0 bg-[var(--brand-surface)] p-0 text-[var(--brand-ink)] backdrop:bg-black/35 ${
        fullScreen
          ? 'h-[100dvh] max-h-[100dvh] rounded-none'
          : 'max-h-[82dvh] rounded-t-2xl shadow-[0_-12px_40px_rgba(0,0,0,0.14)]'
      }`}
    >
      <div className="flex h-full min-h-0 flex-col">
        <header className="flex min-h-14 shrink-0 items-center justify-between border-b border-[var(--brand-line)] px-4">
          <h2 id={titleId} className="text-base font-semibold text-[var(--brand-ink)]">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex size-11 items-center justify-center rounded-lg text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface-soft)]"
            aria-label="Close"
          >
            <X className="size-5" />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-auto overscroll-contain">{children}</div>
      </div>
    </dialog>
  );
}
