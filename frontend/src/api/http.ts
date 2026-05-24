const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';
const JSON_HEADERS: Record<string, string> = { 'Content-Type': 'application/json' };

export function buildApiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export async function readErrorBody(resp: Response): Promise<string> {
  const text = (await resp.text()).trim();
  return text || 'Empty response body';
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
  const resp = await fetch(buildApiUrl(path), init);
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
  const resp = await fetch(buildApiUrl(path), { method: 'DELETE' });
  await ensureOk(resp, messagePrefix);
}
