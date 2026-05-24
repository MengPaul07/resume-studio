import type { SuggestionItem } from '../../types';
import type { DiffChunk } from './types';
import { toDisplayText } from './utils';

export function normalizeDiffPayload(
  payload: SuggestionItem['diff_payload'] | undefined,
): { beforeText: string; afterText: string; chunks: DiffChunk[] } | null {
  if (!payload || typeof payload !== 'object') return null;
  const beforeText = toDisplayText(payload.before_text);
  const afterText = toDisplayText(payload.after_text);
  const rawChunks = Array.isArray(payload.chunks) ? payload.chunks : [];
  const chunks: DiffChunk[] = rawChunks
    .map((chunk) => ({
      type:
        chunk && typeof chunk.type === 'string' && ['same', 'add', 'remove'].includes(chunk.type)
          ? (chunk.type as DiffChunk['type'])
          : 'same',
      text: toDisplayText(chunk?.text ?? ''),
    }))
    .filter((chunk) => chunk.text.length > 0);
  if (!chunks.length && !beforeText && !afterText) return null;
  return { beforeText, afterText, chunks };
}

export function tokenizeDiffText(source: string): string[] {
  const tokens: string[] = [];
  const isCJK = (ch: string) => /[぀-ヿ㐀-䶿一-鿿豈-﫿]/.test(ch);
  let buffer = '';
  for (let index = 0; index < source.length; index += 1) {
    const ch = source[index];
    if (isCJK(ch) || /\s/.test(ch)) {
      if (buffer) tokens.push(buffer);
      buffer = '';
      tokens.push(ch);
      continue;
    }
    buffer += ch;
  }
  if (buffer) tokens.push(buffer);
  return tokens;
}

export function computeInlineDiff(oldText: string, newText: string): DiffChunk[] {
  const a = tokenizeDiffText(oldText || '');
  const b = tokenizeDiffText(newText || '');
  const n = a.length;
  const m = b.length;
  const dp: number[][] = Array.from({ length: n + 1 }, () =>
    Array.from({ length: m + 1 }, () => 0),
  );
  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const result: DiffChunk[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      result.push({ type: 'same', text: a[i] });
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      result.push({ type: 'remove', text: a[i] });
      i += 1;
    } else {
      result.push({ type: 'add', text: b[j] });
      j += 1;
    }
  }
  while (i < n) {
    result.push({ type: 'remove', text: a[i] });
    i += 1;
  }
  while (j < m) {
    result.push({ type: 'add', text: b[j] });
    j += 1;
  }
  const merged: DiffChunk[] = [];
  for (const item of result) {
    const last = merged[merged.length - 1];
    if (last && last.type === item.type) {
      last.text += item.text;
    } else {
      merged.push({ ...item });
    }
  }
  return merged;
}
