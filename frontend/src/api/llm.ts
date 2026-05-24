import { loadSavedLLMConfig } from '../llm-settings';
import { postJson } from './http';

export type LLMConfigPayload = Record<string, unknown>;

export type LLMConnectivityResponse = {
  ok: boolean;
  model: string;
  latency_ms: number;
  message: string;
  provider_response_preview: string;
};

export function getEffectiveLLMConfig(input?: LLMConfigPayload): LLMConfigPayload {
  const saved = loadSavedLLMConfig();
  return {
    ...(saved || {}),
    ...(input || {}),
  };
}

export async function testLLMConnectivity(params?: {
  llm_config?: LLMConfigPayload;
}): Promise<LLMConnectivityResponse> {
  const llm_config = getEffectiveLLMConfig(params?.llm_config);
  return postJson<LLMConnectivityResponse>(
    '/agent/test-llm',
    { llm_config },
    'Connectivity test failed',
  );
}
