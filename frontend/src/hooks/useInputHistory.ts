import { useRef, useState } from 'react';

interface UseInputHistoryOptions {
  getInputText: () => string;
  setInputText: (text: string) => void;
}

interface UseInputHistoryReturn {
  addToHistory: (prompt: string) => void;
  handleInputKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  handleInputChange: (text: string) => void;
}

export function useInputHistory({
  getInputText,
  setInputText,
}: UseInputHistoryOptions): UseInputHistoryReturn {
  const [inputHistory, setInputHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const draftRef = useRef('');

  function addToHistory(prompt: string) {
    setInputHistory((prev) => {
      const next = prev.filter((m) => m !== prompt);
      next.push(prompt);
      return next.slice(-20);
    });
    setHistoryIdx(-1);
  }

  function handleInputKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      return;
    }
    if (e.key === 'ArrowUp' && !getInputText().trim() && inputHistory.length > 0) {
      e.preventDefault();
      const idx = historyIdx === -1 ? inputHistory.length - 1 : Math.max(0, historyIdx - 1);
      setHistoryIdx(idx);
      setInputText(inputHistory[idx]);
      return;
    }
    if (e.key === 'ArrowDown' && historyIdx >= 0) {
      e.preventDefault();
      const idx = historyIdx + 1;
      if (idx >= inputHistory.length) {
        setHistoryIdx(-1);
        setInputText(draftRef.current);
      } else {
        setHistoryIdx(idx);
        setInputText(inputHistory[idx]);
      }
      return;
    }
    if (historyIdx >= 0 && e.key !== 'ArrowUp' && e.key !== 'ArrowDown') {
      setHistoryIdx(-1);
    }
  }

  function handleInputChange(text: string) {
    if (historyIdx < 0) {
      draftRef.current = text;
    }
    setInputText(text);
  }

  return { addToHistory, handleInputKeyDown, handleInputChange };
}
