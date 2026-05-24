import { Check, RotateCcw, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '../ui/button';

interface Props {
  changeCount: number;
  isExpanded: boolean;
  onKeep: () => void;
  onUndo: () => void;
  onToggleDetails: () => void;
  disabled?: boolean;
}

export function ChangeToolbar({
  changeCount,
  isExpanded,
  onKeep,
  onUndo,
  onToggleDetails,
  disabled,
}: Props) {
  if (changeCount === 0) return null;

  return (
    <div className="sticky bottom-0 border-t border-black dark:border-zinc-600 bg-white dark:bg-zinc-900 px-3 py-2 shadow-[0_-2px_8px_rgba(0,0,0,0.06)] dark:shadow-none">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] text-gray-600 dark:text-zinc-400">
          {changeCount} change{changeCount !== 1 ? 's' : ''} applied
        </span>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={onToggleDetails}
            disabled={disabled}
          >
            {isExpanded ? (
              <ChevronUp className="size-3" />
            ) : (
              <ChevronDown className="size-3" />
            )}
            Details
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onUndo}
            disabled={disabled}
          >
            <RotateCcw className="size-3" />
            Undo
          </Button>
          <Button
            size="sm"
            variant="default"
            onClick={onKeep}
            disabled={disabled}
          >
            <Check className="size-3" />
            Keep
          </Button>
        </div>
      </div>
    </div>
  );
}
