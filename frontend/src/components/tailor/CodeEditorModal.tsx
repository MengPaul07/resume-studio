import { useCallback, useEffect, useRef, useState } from 'react';
import { Play, X } from 'lucide-react';

interface CodingQuestion {
  problem: string;
  language: string;
  difficulty: string;
  time_limit?: number;
}

interface Props {
  question: CodingQuestion;
  onSubmit: (code: string, language: string) => void;
  onClose: () => void;
}

const LANG_TEMPLATES: Record<string, string> = {
  python: 'def solve():\n    # Your code here\n    pass\n\nif __name__ == "__main__":\n    solve()',
  java: 'class Solution {\n    public static void main(String[] args) {\n        // Your code here\n    }\n}',
  cpp: '#include <iostream>\n#include <vector>\nusing namespace std;\n\nint main() {\n    // Your code here\n    return 0;\n}',
  javascript: 'function solve() {\n    // Your code here\n}\n\nsolve();',
  golang: 'package main\n\nimport "fmt"\n\nfunc main() {\n    // Your code here\n    fmt.Println("Hello")\n}',
};

const LANG_LABELS: Record<string, string> = {
  python: 'Python', java: 'Java', cpp: 'C++', javascript: 'JavaScript', golang: 'Go',
};

export function CodeEditorModal({ question, onSubmit, onClose }: Props) {
  const [code, setCode] = useState(LANG_TEMPLATES[question.language] || '');
  const [lang, setLang] = useState(question.language);
  const [lines, setLines] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineNumRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setCode(LANG_TEMPLATES[question.language] || '');
    setLang(question.language);
  }, [question]);

  useEffect(() => {
    setLines(code.split('\n'));
  }, [code]);

  const handleSubmit = useCallback(() => {
    onSubmit(code, lang);
    onClose();
  }, [code, lang, onSubmit, onClose]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit();
    }
    // Tab → spaces
    if (e.key === 'Tab') {
      e.preventDefault();
      const ta = e.currentTarget as HTMLTextAreaElement;
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      setCode(code.substring(0, start) + '    ' + code.substring(end));
      setTimeout(() => {
        ta.selectionStart = ta.selectionEnd = start + 4;
      }, 0);
    }
  }, [code, handleSubmit]);

  // Sync scroll between textarea and line numbers
  const handleScroll = () => {
    if (textareaRef.current && lineNumRef.current) {
      lineNumRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  const diffLabel = question.difficulty === 'hard' ? 'text-red-600 bg-red-50 border-red-200'
    : question.difficulty === 'medium' ? 'text-amber-600 bg-amber-50 border-amber-200'
    : 'text-green-600 bg-green-50 border-green-200';

  return (
    <div className="fixed inset-0 z-50 flex bg-[#1e1e1e]">
      {/* Left: problem */}
      <div className="flex w-[38%] min-w-[300px] max-w-[480px] flex-col border-r border-gray-700">
        <div className="flex shrink-0 items-center justify-between border-b border-gray-700 px-5 py-3">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[11px] font-bold uppercase tracking-wide text-blue-400">
              Coding Problem
            </span>
            <span className={`rounded border px-2 py-0.5 font-mono text-[10px] font-medium ${diffLabel}`}>
              {question.difficulty.toUpperCase()}
            </span>
            <span className="font-mono text-[11px] text-gray-500">
              {question.time_limit || 15}min
            </span>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white">
            <X className="size-5" />
          </button>
        </div>
        <div className="flex-1 overflow-auto px-5 py-4">
          <div className="font-sans text-[13px] leading-relaxed text-gray-200 whitespace-pre-wrap">
            {question.problem}
          </div>
        </div>
      </div>

      {/* Right: editor */}
      <div className="flex flex-1 flex-col">
        <div className="flex shrink-0 items-center justify-between border-b border-gray-700 px-5 py-3">
          <select
            value={lang}
            onChange={(e) => {
              const newLang = e.target.value;
              setLang(newLang);
              setCode(LANG_TEMPLATES[newLang] || '');
            }}
            className="border border-gray-600 bg-[#2d2d2d] px-3 py-1.5 font-mono text-xs text-gray-200 outline-none focus:border-gray-400"
          >
            {Object.entries(LANG_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <div className="flex items-center gap-3">
            <span className="font-mono text-[10px] text-gray-500">Ctrl+Enter to submit</span>
            <button
              onClick={handleSubmit}
              className="flex items-center gap-1.5 rounded bg-green-600 px-4 py-1.5 font-mono text-[11px] font-bold uppercase text-white hover:bg-green-500"
            >
              <Play className="size-3.5" />
              Submit
            </button>
          </div>
        </div>
        <div className="flex flex-1 overflow-hidden">
          {/* Line numbers */}
          <div
            ref={lineNumRef}
            className="w-12 shrink-0 overflow-hidden border-r border-gray-700 bg-[#252526] py-3 text-right font-mono text-[12px] leading-[1.6] text-gray-500 select-none"
          >
            {lines.map((_, i) => (
              <div key={i} className="pr-3">{i + 1}</div>
            ))}
          </div>
          {/* Editor */}
          <textarea
            ref={textareaRef}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            onKeyDown={handleKeyDown}
            onScroll={handleScroll}
            spellCheck={false}
            className="flex-1 resize-none border-0 bg-transparent px-4 py-3 font-mono text-[13px] leading-[1.6] text-gray-100 outline-none placeholder-gray-600"
            placeholder="Write your solution..."
          />
        </div>
      </div>
    </div>
  );
}
