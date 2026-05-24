import { toDisplayText } from '../../lib/tailor/utils';
import { ChangeDetailPopover } from './ChangeDetailPopover';
import type { PendingChange } from '../../lib/tailor/types';

interface Props {
  refinedResumeObj: Record<string, unknown>;
  pendingChanges: PendingChange[];
  changedPathSet: Set<string>;
  focusedChangePath: string;
  expandedChangePaths: Set<string>;
  changeVariantIndex: Record<string, number>;
  onToggleChangeDetail: (path: string) => void;
  onSwitchVariant: (path: string, variantIdx: number) => void;
  previewAnchorRefs: React.MutableRefObject<Record<string, HTMLDivElement | null>>;
}

export function JsonPreview({
  refinedResumeObj,
  pendingChanges,
  changedPathSet,
  focusedChangePath,
  expandedChangePaths,
  changeVariantIndex,
  onToggleChangeDetail,
  onSwitchVariant,
  previewAnchorRefs,
}: Props) {
  const findChangeForPath = (path: string): PendingChange | null => {
    if (!path) return null;
    return pendingChanges.find((c) => c.path === path) || null;
  };

  const renderPreviewNode = (value: unknown, path = '', depth = 0): JSX.Element => {
    const isRoot = path === '';
    const isChanged = path ? changedPathSet.has(path) : false;
    const isActive = path ? path === focusedChangePath : false;
    const isExpanded = path ? expandedChangePaths.has(path) : false;
    const change = isChanged ? findChangeForPath(path) : null;

    const containerClass = isActive
      ? 'border-l-2 border-black bg-[var(--brand-surface-soft)]'
      : isChanged
        ? 'border-l-2 border-blue-400 bg-blue-50'
        : 'border-l-2 border-transparent bg-transparent';

    if (
      value === null ||
      value === undefined ||
      typeof value === 'string' ||
      typeof value === 'number' ||
      typeof value === 'boolean'
    ) {
      return (
        <div>
          <div
            ref={(el) => {
              if (path) previewAnchorRefs.current[path] = el;
            }}
            data-path={path}
            onClick={() => {
              if (isChanged && change) onToggleChangeDetail(change.path);
            }}
            className={`px-2 py-1.5 ${containerClass} ${isChanged ? 'cursor-pointer' : ''}`}
          >
            {isChanged ? (
              <span className="inline-block mr-1.5 size-2 rounded-full bg-blue-500 align-middle" />
            ) : null}
            <span className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-900">
              {toDisplayText(value) || '(empty)'}
            </span>
          </div>
          {isChanged && isExpanded && change ? (
            <ChangeDetailPopover
              change={change}
              activeVariantIndex={changeVariantIndex[change.path] ?? 0}
              onSwitchVariant={onSwitchVariant}
            />
          ) : null}
        </div>
      );
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return (
          <div
            ref={(el) => {
              if (path) previewAnchorRefs.current[path] = el;
            }}
            data-path={path}
            className={`px-2 py-1.5 text-sm text-slate-700 ${containerClass}`}
          >
            []
          </div>
        );
      }
      return (
        <div
          ref={(el) => {
            if (path) previewAnchorRefs.current[path] = el;
          }}
          data-path={path}
          className={`space-y-2 px-2 py-1.5 ${containerClass}`}
          style={{ marginLeft: isRoot ? 0 : Math.min(depth * 10, 30) }}
        >
          <ul className="space-y-2">
            {value.map((item, index) => {
              const childPath = `${path}[${index}]`;
              return (
                <li key={childPath} className="list-none">
                  {renderPreviewNode(item, childPath, depth + 1)}
                </li>
              );
            })}
          </ul>
        </div>
      );
    }

    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj);
    return (
      <div
        ref={(el) => {
          if (path) previewAnchorRefs.current[path] = el;
        }}
        data-path={path}
        className={`space-y-2 px-2 py-1.5 ${containerClass}`}
        style={{ marginLeft: isRoot ? 0 : Math.min(depth * 10, 30) }}
      >
        {keys.map((key) => {
          const childPath = path ? `${path}.${key}` : key;
          const childValue = obj[key];
          const childIsNested = childValue !== null && typeof childValue === 'object';
          return (
            <section key={childPath} className="space-y-1">
              {childIsNested ? (
                <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-700">
                  {key}
                </h4>
              ) : null}
              {renderPreviewNode(childValue, childPath, depth + 1)}
            </section>
          );
        })}
      </div>
    );
  };

  return (
    <article className="mx-auto w-full min-h-[980px] max-w-[860px] border border-black bg-white px-6 py-6">
      <h3 className="mb-4 font-mono text-xs uppercase tracking-wide text-slate-600">
        Refined Document JSON
      </h3>
      {renderPreviewNode(refinedResumeObj)}
    </article>
  );
}
