import { useCallback, useEffect, useRef, useState } from 'react';
import { toDisplayText } from '../../lib/tailor/utils';
import { renderTemplateHtml } from '../../lib/template-engine/renderer';
import type { TemplateDefinition } from '../../lib/template-engine/types';
import type { PendingChange } from '../../lib/tailor/types';
// @ts-ignore — Vite JSON import
import swissSingle from '../../../../templates/swiss-single.json';

const TEMPLATE = swissSingle as TemplateDefinition;

interface Props {
  refinedResumeObj: Record<string, unknown>;
  pendingChanges?: PendingChange[];
  onEditField?: (path: string, newValue: string) => void;
}

function getValueAtPath(obj: unknown, path: string): string {
  const val = path.split('.').reduce((cur: unknown, key) => {
    const arrMatch = key.match(/^(\w+)\[(\d+)\]$/);
    if (arrMatch) {
      const arr = (cur as Record<string, unknown>)?.[arrMatch[1]];
      return Array.isArray(arr) ? arr[parseInt(arrMatch[2])] : '';
    }
    return (cur as Record<string, unknown>)?.[key] ?? '';
  }, obj);
  return typeof val === 'string' ? val : toDisplayText(val);
}

export function LivePreview({ refinedResumeObj, pendingChanges, onEditField }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [editingPath, setEditingPath] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [pos, setPos] = useState({ x: 200, y: 200 });
  const [size, setSize] = useState({ w: 400, h: 140 });
  const dragging = useRef<{ startX: number; startY: number; startPosX: number; startPosY: number } | null>(null);
  const resizing = useRef<{ startX: number; startY: number; startW: number; startH: number } | null>(null);

  const html = renderTemplateHtml(TEMPLATE, refinedResumeObj);

  const handleClick = useCallback((e: MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.closest('.inline-editor-overlay')) return;
    const el = target.closest('[data-path]') as HTMLElement | null;
    if (!el) return;
    const path = el.getAttribute('data-path');
    if (!path || !onEditField) return;
    e.stopPropagation();
    const rect = el.getBoundingClientRect();
    const containerRect = containerRef.current?.getBoundingClientRect();
    if (containerRect) {
      setPos({ x: rect.left - containerRect.left, y: rect.bottom - containerRect.top + 6 });
    }
    setEditValue(getValueAtPath(refinedResumeObj, path));
    setEditingPath(path);
    setTimeout(() => textareaRef.current?.focus(), 0);
  }, [refinedResumeObj, onEditField]);

  const handleSave = useCallback(() => {
    if (editingPath && onEditField) {
      onEditField(editingPath, editValue);
      setEditingPath(null);
    }
  }, [editingPath, editValue, onEditField]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSave(); }
    if (e.key === 'Escape') { setEditingPath(null); }
  }, [handleSave]);

  const onDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = { startX: e.clientX, startY: e.clientY, startPosX: pos.x, startPosY: pos.y };
  };
  const onResizeStart = (e: React.MouseEvent) => {
    e.preventDefault(); e.stopPropagation();
    resizing.current = { startX: e.clientX, startY: e.clientY, startW: size.w, startH: size.h };
  };

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (dragging.current) {
        setPos({
          x: dragging.current.startPosX + e.clientX - dragging.current.startX,
          y: dragging.current.startPosY + e.clientY - dragging.current.startY,
        });
      }
      if (resizing.current) {
        setSize({
          w: Math.max(240, resizing.current.startW + e.clientX - resizing.current.startX),
          h: Math.max(100, resizing.current.startH + e.clientY - resizing.current.startY),
        });
      }
    };
    const onUp = () => { dragging.current = null; resizing.current = null; };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, []);

  useEffect(() => { if (editingPath) setSize({ w: 400, h: 140 }); }, [editingPath]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener('click', handleClick);
    return () => el.removeEventListener('click', handleClick);
  }, [handleClick]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.querySelectorAll('.is-changed').forEach((n) => n.classList.remove('is-changed'));
    if (pendingChanges) {
      for (const c of pendingChanges) {
        el.querySelectorAll(`[data-path="${c.path}"], [data-path^="${c.path}["]`).forEach((n) => {
          n.classList.add('is-changed');
        });
      }
    }
  }, [html, pendingChanges]);

  return (
    <div className="live-preview" ref={containerRef}>
      <style>{`
        .resume-preview-content { font-family: 'Inter', system-ui, sans-serif; font-size: 13px; line-height: 1.6; color: #1a1a1a; }
        .resume-preview-content h1 { font-size: 24px; font-weight: 700; margin: 0 0 2px; }
        .resume-preview-content h2.section-title { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.14em; color: #888; margin: 18px 0 6px; border-bottom: 1px solid #e5e5e5; padding-bottom: 4px; }
        .resume-preview-content h3 { font-size: 14px; font-weight: 600; margin: 0; }
        .resume-preview-content .resume-item { margin-bottom: 12px; padding-left: 10px; border-left: 2px solid #eee; }
        .resume-preview-content .meta { font-size: 12px; color: #666; margin: 1px 0; }
        .resume-preview-content .bullet-list { margin: 4px 0 0 18px; padding: 0; list-style: disc; }
        .resume-preview-content .bullet-list li { margin-bottom: 2px; }
        .resume-preview-content .skill-cloud { display: flex; flex-wrap: wrap; gap: 6px; }
        .resume-preview-content .skill-tag { background: #f3f4f6; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .resume-preview-content [data-path] { cursor: text; border-radius: 2px; transition: background 0.15s; }
        .resume-preview-content [data-path]:hover { background: #f0f4ff; outline: 1px dashed #94a3b8; outline-offset: 1px; }
        .resume-preview-content .is-changed { background: #eff6ff; outline: 1px solid #3b82f6; outline-offset: 1px; border-radius: 2px; }
        .resume-preview-content .fw-bold { font-weight: 700; }
        .resume-preview-content .clr-muted { color: #666; }
        .resume-preview-content .tt-upper { text-transform: uppercase; }
        .resume-preview-content .track-wide { letter-spacing: 0.14em; }
        .live-preview { position: relative; }
        .inline-editor-overlay { position: absolute; z-index: 10; background: #fff; border: 2px solid #000; box-shadow: 4px 4px 0 #00000020; border-radius: 4px; min-width: 240px; display: flex; flex-direction: column; }
        .inline-editor-overlay .drag-handle { height: 22px; background: #f5f5f5; border-bottom: 1px solid #e5e5e5; cursor: move; display: flex; align-items: center; justify-content: space-between; padding: 0 6px; border-radius: 2px 2px 0 0; user-select: none; }
        .inline-editor-overlay .drag-handle span { font-size: 10px; color: #888; }
        .inline-editor-overlay .drag-handle .close-btn { cursor: pointer; font-size: 14px; color: #999; line-height: 1; padding: 0 4px; }
        .inline-editor-overlay .drag-handle .close-btn:hover { color: #333; }
        .inline-editor-overlay .editor-body { flex: 1; display: flex; flex-direction: column; padding: 6px; }
        .inline-editor-overlay textarea { flex: 1; border: 1px solid #ddd; padding: 6px 8px; font: inherit; resize: none; outline: none; }
        .inline-editor-actions { display: flex; gap: 6px; margin-top: 4px; justify-content: flex-end; }
        .inline-editor-actions button { padding: 2px 12px; border: 1px solid #000; background: #000; color: #fff; font-size: 11px; cursor: pointer; border-radius: 2px; }
        .inline-editor-actions button.ghost { background: #fff; color: #666; border-color: #ddd; }
        .resize-grip { position: absolute; bottom: 0; right: 0; width: 14px; height: 14px; cursor: nwse-resize; background: linear-gradient(135deg, transparent 50%, #ccc 50%, #ccc 60%, transparent 60%, transparent 70%, #ccc 70%, #ccc 80%, transparent 80%); }
      `}</style>
      <div dangerouslySetInnerHTML={{ __html: html }} />
      {editingPath && (
        <div className="inline-editor-overlay" style={{ left: pos.x, top: pos.y, width: size.w, height: size.h }}>
          <div className="drag-handle" onMouseDown={onDragStart}>
            <span>{editingPath}</span>
            <span className="close-btn" onClick={() => setEditingPath(null)}>&times;</span>
          </div>
          <div className="editor-body">
            <textarea
              ref={textareaRef}
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <div className="inline-editor-actions">
              <button className="ghost" onClick={() => setEditingPath(null)}>Cancel</button>
              <button onClick={handleSave}>Save</button>
            </div>
          </div>
          <div className="resize-grip" onMouseDown={onResizeStart} />
        </div>
      )}
    </div>
  );
}
