import type { ChatMessage, ResumeDagNode } from './types';

export function toJsonObject(input: unknown): Record<string, unknown> {
  return typeof input === 'object' && input !== null ? (input as Record<string, unknown>) : {};
}

export function truncateValue(value: string, max = 140): string {
  if (value.length <= max) return value;
  return `${value.slice(0, max)}...`;
}

export function toDisplayText(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function flattenJsonTextEntries(
  value: unknown,
  path = '',
): Array<{ path: string; text: string }> {
  if (value === null || value === undefined) return [];
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    const text = toDisplayText(value).trim();
    return text ? [{ path: path || 'root', text }] : [];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => flattenJsonTextEntries(item, `${path}[${index}]`));
  }
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) =>
      flattenJsonTextEntries(child, path ? `${path}.${key}` : key),
    );
  }
  return [];
}

export function displayLines(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (item !== null && typeof item === 'object') {
          return flattenJsonTextEntries(item)
            .map((entry) => entry.text)
            .filter(Boolean)
            .join(' | ');
        }
        return toDisplayText(item);
      })
      .map((item) => item.trim())
      .filter(Boolean);
  }
  if (value !== null && typeof value === 'object') {
    const text = flattenJsonTextEntries(value)
      .map((entry) => entry.text)
      .filter(Boolean)
      .join(' | ');
    return text ? [text] : [];
  }
  const text = toDisplayText(value).trim();
  return text ? [text] : [];
}

export function stableStringify(input: unknown): string {
  const normalize = (value: unknown): unknown => {
    if (Array.isArray(value)) return value.map((item) => normalize(item));
    if (value && typeof value === 'object') {
      const obj = value as Record<string, unknown>;
      const keys = Object.keys(obj).sort();
      const out: Record<string, unknown> = {};
      keys.forEach((key) => {
        out[key] = normalize(obj[key]);
      });
      return out;
    }
    return value;
  };
  try {
    return JSON.stringify(normalize(input));
  } catch {
    return String(input);
  }
}

export function hashContent(input: unknown): string {
  const text = stableStringify(input);
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
  }
  return `h${(hash >>> 0).toString(16)}`;
}

export function tokenizePath(path: string): Array<string | number> {
  const tokens: Array<string | number> = [];
  const text = String(path || '');
  if (!text.trim()) return tokens;
  const parts = text.split('.');
  for (const part of parts) {
    const re = /([^\[\]]+)|\[(\d+)\]/g;
    let match: RegExpExecArray | null;
    while ((match = re.exec(part)) !== null) {
      if (match[1]) tokens.push(match[1]);
      else if (match[2]) tokens.push(Number(match[2]));
    }
  }
  return tokens;
}

export function setByPathLocal(root: unknown, path: string, value: unknown): boolean {
  const tokens = tokenizePath(path);
  if (!tokens.length || !root || typeof root !== 'object') return false;
  let cursor: any = root;
  for (let i = 0; i < tokens.length - 1; i += 1) {
    const token = tokens[i];
    const nextToken = tokens[i + 1];
    if (typeof token === 'number') {
      if (!Array.isArray(cursor) || token < 0 || token > cursor.length) return false;
      if (token === cursor.length) {
        cursor.push(typeof nextToken === 'number' ? [] : {});
      } else if (cursor[token] === null || typeof cursor[token] !== 'object') {
        cursor[token] = typeof nextToken === 'number' ? [] : {};
      }
      cursor = cursor[token];
    } else {
      if (!cursor || typeof cursor !== 'object') return false;
      if (!(token in cursor) || cursor[token] === null || typeof cursor[token] !== 'object') {
        cursor[token] = typeof nextToken === 'number' ? [] : {};
      }
      cursor = cursor[token];
    }
  }
  const last = tokens[tokens.length - 1];
  if (typeof last === 'number') {
    if (!Array.isArray(cursor) || last < 0 || last > cursor.length) return false;
    if (last === cursor.length) {
      cursor.push(value);
      return true;
    }
    cursor[last] = value;
    return true;
  }
  if (!cursor || typeof cursor !== 'object') return false;
  cursor[last] = value;
  return true;
}

export function isThreadMessage(msg: ChatMessage): boolean {
  return Array.isArray(msg.threadSteps) && msg.threadSteps.length > 0;
}

export function isBootstrapSystemMessage(msg: ChatMessage): boolean {
  if (msg.role !== 'system') return false;
  const text = String(msg.text || '');
  return text.startsWith('Loaded resume:') || text.startsWith('Session started (');
}

export function sanitizePersistedMessage(msg: ChatMessage): ChatMessage {
  return {
    ...msg,
    threadRunning: false,
    threadSteps: Array.isArray(msg.threadSteps)
      ? msg.threadSteps.map((step) => ({
          ...step,
          status: step.status === 'running' ? 'failed' : step.status,
          error: step.status === 'running' ? (step.error || 'Interrupted after leaving page') : step.error,
        }))
      : msg.threadSteps,
  };
}

export function formatSessionTimeLabel(isoText: string): string {
  const dt = new Date(isoText);
  if (Number.isNaN(dt.getTime())) return '';
  return dt.toLocaleString(undefined, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function isPathMatch(a: string, b: string): boolean {
  if (!a || !b) return false;
  return (
    a === b ||
    a.startsWith(`${b}.`) ||
    a.startsWith(`${b}[`) ||
    b.startsWith(`${a}.`) ||
    b.startsWith(`${a}[`)
  );
}

export function buildDagNodeLabel(state: ResumeDagNode['state'], createdAt: string): string {
  const t = formatSessionTimeLabel(createdAt);
  return `${state.toUpperCase()}${t ? ` · ${t}` : ''}`;
}

export function createDagNode(
  state: ResumeDagNode['state'],
  content: unknown,
  current = false,
  createdAt = new Date().toISOString(),
): ResumeDagNode {
  const snapshot = toJsonObject(content);
  return {
    id: `n-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    state,
    contentHash: hashContent(snapshot),
    createdAt,
    label: buildDagNodeLabel(state, createdAt),
    current,
    snapshot: state === 'processing' ? undefined : snapshot,
  };
}
