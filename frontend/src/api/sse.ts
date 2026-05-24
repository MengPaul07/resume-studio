import { buildApiUrl } from './http';
import { ensureOk } from './http';

const JSON_HEADERS = { 'Content-Type': 'application/json' };

export async function postSSEAndCollectFinal<T>(params: {
  path: string;
  body: unknown;
  messagePrefix: string;
  onEvent?: (event: string, data: Record<string, unknown>) => void;
}): Promise<T> {
  const resp = await fetch(buildApiUrl(params.path), {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(params.body),
  });
  await ensureOk(resp, params.messagePrefix);

  if (!resp.body) {
    throw new Error(`${params.messagePrefix}: empty stream`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let finalPayload: T | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split('\n\n');
    buffer = chunks.pop() ?? '';
    for (const chunk of chunks) {
      const lines = chunk.split('\n');
      let eventName = 'message';
      let dataText = '';
      for (const line of lines) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim();
        if (line.startsWith('data:')) dataText += line.slice(5).trim();
      }
      if (!dataText) continue;
      let parsed: Record<string, unknown> = {};
      try {
        parsed = JSON.parse(dataText) as Record<string, unknown>;
      } catch {
        parsed = { raw: dataText };
      }
      params.onEvent?.(eventName, parsed);
      if (eventName === 'turn.completed') {
        if (typeof parsed.error === 'string' && parsed.error.trim()) {
          throw new Error(`Tool chat failed: ${parsed.error}`);
        }
        finalPayload = parsed as T;
      }
    }
  }

  if (!finalPayload) {
    throw new Error(`${params.messagePrefix}: stream completed without turn.completed`);
  }
  return finalPayload;
}
