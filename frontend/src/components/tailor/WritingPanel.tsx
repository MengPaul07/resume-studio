import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-c';
import 'prismjs/components/prism-cpp';
import 'prismjs/components/prism-go';
import 'prismjs/themes/prism.css';
import { Check, Code2, Play, X, ChevronDown, Maximize2, Minimize2, Pencil } from 'lucide-react';
import { renderProblemMarkdown } from '../../lib/tailor/markdown';

// ── Language config ────────────────────────────────────────────────────

export interface EditorQuestion {
  problem: string;
  language?: string;
  difficulty?: string;
  time_limit?: number;
}

export type EditorMode = 'code' | 'write';

interface Props {
  mode?: EditorMode;
  question: EditorQuestion;
  initialCode?: string;
  onCodeChange?: (code: string) => void;
  onSubmit: (text: string, language?: string) => void;
  onClose: () => void;
  placeholder?: string;
  submitLabel?: string;
  title?: string;
}

// ── Language config ────────────────────────────────────────────────────

const LANGUAGES = [
  { id: 'python', label: 'Python', ext: '.py', prism: languages.python },
  { id: 'javascript', label: 'JavaScript', ext: '.js', prism: languages.javascript },
  { id: 'java', label: 'Java', ext: '.java', prism: languages.java },
  { id: 'cpp', label: 'C++', ext: '.cpp', prism: languages.cpp },
  { id: 'c', label: 'C', ext: '.c', prism: languages.c },
  { id: 'go', label: 'Go', ext: '.go', prism: languages.go },
] as const;

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  medium: 'text-amber-600 bg-amber-50 border-amber-200',
  hard: 'text-red-600 bg-red-50 border-red-200',
};

// ── Component ──────────────────────────────────────────────────────────

export function WritingPanel({
  mode = 'code', question, initialCode, onCodeChange,
  onSubmit, onClose, placeholder, submitLabel, title,
}: Props) {
  const { t } = useTranslation();
  const defaultLang = LANGUAGES.find(l => l.id === (question.language || 'python'))?.id || 'python';
  const [language, setLanguage] = useState(defaultLang);
  const [currentMode, setCurrentMode] = useState<EditorMode>(mode);
  const [text, setText] = useState(initialCode || '');
  const [submitted, setSubmitted] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [showLangMenu, setShowLangMenu] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Load KaTeX CSS for math rendering in problem display
  useEffect(() => {
    if (document.getElementById('katex-css')) return;
    const link = document.createElement('link');
    link.id = 'katex-css';
    link.rel = 'stylesheet';
    link.href = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css';
    document.head.appendChild(link);
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js';
    document.head.appendChild(script);
  }, []);

  // Intercept the textarea to make it transparent for syntax highlighting overlay
  useEffect(() => {
    const el = document.getElementById('writing-editor-textarea') as HTMLTextAreaElement | null;
    if (el && currentMode === 'code') {
      el.style.color = 'transparent';
      el.style.caretColor = '#1e293b';
      el.style.setProperty('color', 'transparent', 'important');
    }
  }, [currentMode]);

  const handleChange = useCallback((newText: string) => {
    setText(newText);
    onCodeChange?.(newText);
  }, [onCodeChange]);

  const handleSubmit = useCallback(() => {
    if (!text.trim() || submitted) return;
    setSubmitted(true);
    onSubmit(text.trim(), currentMode === 'code' ? language : undefined);
  }, [text, submitted, onSubmit, language, currentMode]);

  const highlightCode = useCallback((c: string) => {
    if (currentMode !== 'code') return c.replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]!));
    const lang = LANGUAGES.find(l => l.id === language);
    try { return highlight(c, lang?.prism || languages.python, language); }
    catch { return c.replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]!)); }
  }, [language, currentMode]);

  const lineCount = useMemo(() => text.split('\n').length, [text]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); handleSubmit(); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleSubmit]);

  const langObj = LANGUAGES.find(l => l.id === language)!;
  const isCode = currentMode === 'code';

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/20 dark:bg-black/50 backdrop-blur-sm"
      onClick={onClose}>
      <div
        className={`flex flex-col overflow-hidden rounded-xl border border-zinc-200 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] shadow-xl transition-all ${
          fullscreen ? 'inset-4 m-4 h-[calc(100vh-2rem)] w-[calc(100vw-2rem)]' : 'h-[88vh] w-[920px]'
        }`}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-zinc-100 dark:border-[var(--brand-line)] px-5 py-2.5">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-md bg-zinc-100 dark:bg-[var(--brand-surface-soft)] px-2.5 py-1">
              {isCode ? <Code2 className="size-3.5 text-zinc-500 dark:text-zinc-400" /> : <Pencil className="size-3.5 text-zinc-500 dark:text-zinc-400" />}
              <span className="font-sans text-[11px] font-medium text-zinc-600 dark:text-zinc-400">{title || (isCode ? t('editor.code') : t('editor.writing'))}</span>
            </div>
            {isCode && question.difficulty && (
              <span className={`rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold capitalize ${DIFFICULTY_COLORS[question.difficulty] || DIFFICULTY_COLORS.medium}`}>
                {question.difficulty}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button onClick={() => setFullscreen(!fullscreen)}
              className="rounded-md p-1.5 text-zinc-400 dark:text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-700 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors">
              {fullscreen ? <Minimize2 className="size-3.5" /> : <Maximize2 className="size-3.5" />}
            </button>
            <button onClick={onClose}
              className="rounded-md p-1.5 text-zinc-400 dark:text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-700 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors">
              <X className="size-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left: Problem */}
          <div className="w-[340px] shrink-0 overflow-auto border-r border-zinc-100 dark:border-[var(--brand-line)] bg-zinc-50/50 dark:bg-[var(--brand-surface-soft)]/50">
            <div className="p-4">
              <h3 className="mb-2 font-sans text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wide">
                {isCode ? t('editor.problem') : t('editor.prompt')}
              </h3>
              {renderProblemMarkdown(question.problem)}
            </div>
          </div>

          {/* Right: Editor */}
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Toolbar */}
            <div className="flex shrink-0 items-center justify-between border-b border-zinc-100 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] px-4 py-1.5">
              <div className="flex items-center gap-2">
                {isCode ? (
                  <div className="relative">
                    <button onClick={() => setShowLangMenu(!showLangMenu)}
                      className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-700 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors">
                      <span className="font-mono font-medium">{langObj.label}</span>
                      <ChevronDown className="size-3" />
                    </button>
                    {showLangMenu && (
                      <>
                        <div className="fixed inset-0 z-10" onClick={() => setShowLangMenu(false)} />
                        <div className="absolute left-0 top-full z-20 mt-1 w-36 rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-800 py-1 shadow-lg dark:shadow-none">
                          {LANGUAGES.map(l => (
                            <button key={l.id} onClick={() => { setLanguage(l.id); setShowLangMenu(false); }}
                              className={`flex w-full items-center gap-2 px-3 py-2 text-left text-[11px] transition-colors ${
                                language === l.id ? 'bg-zinc-100 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 font-medium' : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-700 hover:text-zinc-700 dark:hover:text-zinc-200'
                              }`}>
                              <span className="font-mono">{l.label}</span>
                              <span className="font-mono text-[10px] text-zinc-400 dark:text-zinc-500">{l.ext}</span>
                            </button>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                ) : (
                  <span className="font-sans text-[11px] text-zinc-400 dark:text-zinc-500">{t('editor.plainText')}</span>
                )}
                <button
                  onClick={() => setCurrentMode(isCode ? 'write' : 'code')}
                  className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-zinc-400 dark:text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-700 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
                  title={isCode ? t('editor.switchToWrite') : t('editor.switchToCode')}
                >
                  {isCode ? <Pencil className="size-3" /> : <Code2 className="size-3" />}
                </button>
              </div>
              <span className="font-mono text-[10px] text-zinc-400 dark:text-zinc-500">
                {t('editor.linesAndSubmit', {n: lineCount})}
              </span>
            </div>

            {/* Editor */}
            <div className="flex-1 overflow-auto">
              <Editor
                value={text}
                onValueChange={handleChange}
                highlight={highlightCode}
                padding={16}
                disabled={submitted}
                textareaId="writing-editor-textarea"
                style={{
                  minHeight: '100%',
                  fontFamily: isCode
                    ? "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', 'Consolas', monospace"
                    : "'Georgia', 'Times New Roman', serif",
                  fontSize: isCode ? '13px' : '15px',
                  lineHeight: isCode ? '1.7' : '1.8',
                  background: '#fafbfc',
                }}
                textareaClassName="focus:outline-none"
                preClassName="!bg-transparent"
                placeholder={placeholder || (isCode ? t('editor.codePlaceholder') : t('editor.writePlaceholder'))}
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex shrink-0 items-center justify-between border-t border-zinc-100 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] px-5 py-2.5">
          <p className="font-sans text-[11px] text-zinc-400 dark:text-zinc-500">
            {submitted ? t('editor.submitted') : t('editor.preservedHint')}
          </p>
          <div className="flex items-center gap-2">
            <button onClick={onClose}
              className="rounded-lg border border-zinc-200 dark:border-[var(--brand-line)] px-4 py-2 font-sans text-xs font-medium text-zinc-600 dark:text-[var(--brand-ink-muted)] hover:bg-zinc-50 dark:hover:bg-[var(--brand-surface-soft)] transition-colors">
              {t('common.close')}
            </button>
            <button onClick={handleSubmit}
              disabled={!text.trim() || submitted}
              className="flex items-center gap-2 rounded-lg bg-[var(--brand-signal)] px-5 py-2 font-sans text-xs font-semibold text-white transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed">
              {submitted ? (<><Check className="size-3.5" /> {t('editor.submitted')}</>) : (<><Play className="size-3.5" /> {submitLabel || t('editor.submit')}</>)}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
