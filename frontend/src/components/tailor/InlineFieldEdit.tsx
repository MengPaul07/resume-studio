import { useCallback, useRef, useState } from 'react';
import { isMultiLineField } from '../../lib/tailor/field-editor';

interface Props {
  path: string;
  value: string;
  as: 'p' | 'li' | 'div' | 'span' | 'h1' | 'h2' | 'h3' | 'h4';
  isChanged: boolean;
  showEmpty?: boolean;
  onSave: (path: string, newValue: string) => void;
  onTogglePopover?: () => void;
}

export function InlineFieldEdit({
  path,
  value,
  as,
  isChanged,
  showEmpty,
  onSave,
  onTogglePopover,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  const startEdit = useCallback(() => {
    if (isChanged) {
      onTogglePopover?.();
      return;
    }
    setDraft(value);
    setEditing(true);
    // Auto-focus after render
    requestAnimationFrame(() => {
      inputRef.current?.focus();
      inputRef.current?.select();
    });
  }, [isChanged, value, onTogglePopover]);

  const confirmEdit = useCallback(() => {
    const trimmed = draft.trim();
    if (trimmed !== value) {
      onSave(path, trimmed);
    }
    setEditing(false);
  }, [path, draft, value, onSave]);

  const cancelEdit = useCallback(() => {
    setDraft(value);
    setEditing(false);
  }, [value]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        cancelEdit();
      } else if (e.key === 'Enter' && !e.shiftKey) {
        if (isMultiLineField(path)) {
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            confirmEdit();
          }
        } else {
          e.preventDefault();
          confirmEdit();
        }
      }
    },
    [path, confirmEdit, cancelEdit],
  );

  const isInline = as === 'span';
  const isBlock = as === 'p' || as === 'li' || as === 'div';

  if (!editing) {
    const Tag = as;
    const displayText = value || (showEmpty ? '(empty)' : '');
    return (
      <Tag
        className={
          isInline
            ? 'cursor-text text-[15px] leading-7 text-gray-900 dark:text-zinc-100'
            : isBlock
              ? 'block whitespace-pre-wrap break-words text-[15px] leading-7 text-gray-900 dark:text-zinc-100 cursor-text'
              : 'whitespace-pre-wrap break-words text-[15px] leading-7 text-gray-900 dark:text-zinc-100 cursor-text'
        }
        onClick={(e: React.MouseEvent) => {
          e.stopPropagation();
          startEdit();
        }}
      >
        {displayText}
      </Tag>
    );
  }

  const multiLine = isMultiLineField(path);

  if (multiLine) {
    return (
      <textarea
        ref={inputRef as React.Ref<HTMLTextAreaElement>}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={confirmEdit}
        className="w-full min-h-[60px] resize-y rounded border border-blue-400 dark:border-blue-600 bg-white dark:bg-zinc-800 px-2 py-1 text-[15px] leading-7 text-gray-900 dark:text-zinc-100 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
        rows={Math.max(2, draft.split('\n').length)}
      />
    );
  }

  if (isInline) {
    return (
      <input
        ref={inputRef as React.Ref<HTMLInputElement>}
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={confirmEdit}
        className="inline-block min-w-[80px] rounded border border-blue-400 dark:border-blue-600 bg-white dark:bg-zinc-800 px-1.5 py-0.5 text-[15px] leading-7 text-gray-900 dark:text-zinc-100 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
        style={{ width: `${Math.max(80, draft.length * 10 + 20)}px` }}
      />
    );
  }

  return (
    <input
      ref={inputRef as React.Ref<HTMLInputElement>}
      type="text"
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onKeyDown={handleKeyDown}
      onBlur={confirmEdit}
      className="w-full rounded border border-blue-400 dark:border-blue-600 bg-white dark:bg-zinc-800 px-2 py-1 text-[15px] leading-7 text-gray-900 dark:text-zinc-100 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
    />
  );
}
