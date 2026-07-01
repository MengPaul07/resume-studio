const API_BASE = '/api/v1';
const JSON_HEADERS: Record<string, string> = { 'Content-Type': 'application/json' };

const USER_ID_KEY = 'resume_user_id';

function getUserId(): string {
  let uid = localStorage.getItem(USER_ID_KEY);
  if (!uid) {
    uid = crypto.randomUUID();
    localStorage.setItem(USER_ID_KEY, uid);
  }
  return uid;
}

export function getLang(): string {
  try { return localStorage.getItem('i18nextLng') || 'zh'; }
  catch { return 'zh'; }
}

export function withUserId(headers: Record<string, string> = {}): Record<string, string> {
  return { ...headers, 'X-User-Id': getUserId(), 'X-User-Lang': getLang() };
}

export function buildApiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export async function readErrorBody(resp: Response): Promise<string> {
  const text = (await resp.text()).trim();
  if (!text) return 'Empty response body';
  // Try to extract structured error
  try {
    const parsed = JSON.parse(text);
    if (parsed?.error?.code) {
      return `[${parsed.error.code}] ${parsed.error.detail || text}`;
    }
  } catch {}
  return text;
}

export async function ensureOk(resp: Response, messagePrefix: string): Promise<void> {
  if (resp.ok) return;
  throw new Error(`${messagePrefix} (${resp.status}): ${await readErrorBody(resp)}`);
}

export async function requestJson<T>(
  path: string,
  init: RequestInit,
  messagePrefix: string,
): Promise<T> {
  const resp = await fetch(buildApiUrl(path), { ...init, headers: withUserId(init.headers as Record<string, string> | undefined) });
  await ensureOk(resp, messagePrefix);
  return (await resp.json()) as T;
}

export async function postJson<T>(
  path: string,
  body: unknown,
  messagePrefix: string,
): Promise<T> {
  return requestJson<T>(
    path,
    {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    },
    messagePrefix,
  );
}

export async function postForm<T>(
  path: string,
  body: FormData,
  messagePrefix: string,
): Promise<T> {
  return requestJson<T>(
    path,
    { method: 'POST', body },
    messagePrefix,
  );
}

export async function deleteRequest(path: string, messagePrefix: string): Promise<void> {
  const resp = await fetch(buildApiUrl(path), { method: 'DELETE', headers: withUserId() });
  await ensureOk(resp, messagePrefix);
}
