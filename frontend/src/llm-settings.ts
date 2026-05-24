export type LLMConfig = {
  model: string;
  api_key: string;
  api_base: string;
};

export type LLMProvider = {
  id: string;
  name: string;
  api_base: string;
  models: string[];
};

export const LLM_PROVIDERS: LLMProvider[] = [
  {
    id: 'openai', name: 'OpenAI',
    api_base: 'https://api.openai.com/v1',
    models: ['gpt-5.5', 'gpt-5.4-pro', 'gpt-5.4', 'gpt-5.4-mini', 'gpt-5.4-high', 'gpt-5.3-codex', 'gpt-5.2', 'gpt-4.1'],
  },
  {
    id: 'anthropic', name: 'Anthropic',
    api_base: 'https://api.anthropic.com/v1',
    models: ['claude-opus-4-7', 'claude-opus-4-6', 'claude-opus-4-5-20251101', 'claude-opus-4-1-20250805', 'claude-sonnet-4-6', 'claude-sonnet-4-5-20250929', 'claude-haiku-4-5-20251001'],
  },
  {
    id: 'google', name: 'Google Gemini',
    api_base: 'https://generativelanguage.googleapis.com/v1beta',
    models: ['gemini-3.1-pro-preview', 'gemini-3-pro-preview', 'gemini-3-flash-preview', 'gemini-2.5-pro', 'gemini-2.5-flash'],
  },
  {
    id: 'deepseek', name: 'DeepSeek',
    api_base: 'https://api.deepseek.com/v1',
    models: ['deepseek-v4-pro', 'deepseek-v4-flash'],
  },
  {
    id: 'zhipu', name: 'Zhipu GLM',
    api_base: 'https://open.bigmodel.cn/api/paas/v4',
    models: ['glm-5', 'glm-4-plus', 'glm-4-flash'],
  },
  {
    id: 'minimax', name: 'MiniMax',
    api_base: 'https://api.minimax.chat/v1',
    models: ['MiniMax-M2.7', 'minimax-m2.5'],
  },
  {
    id: 'moonshot', name: 'Moonshot (Kimi)',
    api_base: 'https://api.moonshot.cn/v1',
    models: ['kimi-k2.5', 'moonshot-v1-128k'],
  },
  {
    id: 'qwen', name: 'Qwen (DashScope)',
    api_base: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: ['qwen3.6-max-preview', 'qwen3.6-plus', 'qwen3.5-plus', 'qwen3.5-flash', 'qwen3-max', 'qwen3-coder-next', 'qwen3-vl-flash'],
  },
];

export const DEFAULT_LLM_CONFIG: LLMConfig = {
  model: 'deepseek-v4-pro',
  api_key: '',
  api_base: 'https://api.deepseek.com/v1',
};

const LLM_CONFIG_STORAGE_KEY = 'resume.llm_config';

function sanitizeLLMConfig(raw: unknown): LLMConfig {
  const input = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>;
  return {
    model: String(input.model ?? DEFAULT_LLM_CONFIG.model),
    api_key: String(input.api_key ?? DEFAULT_LLM_CONFIG.api_key),
    api_base: String(input.api_base ?? DEFAULT_LLM_CONFIG.api_base),
  };
}

export function loadLLMConfig(): LLMConfig {
  if (typeof window === 'undefined') return DEFAULT_LLM_CONFIG;
  const raw = window.localStorage.getItem(LLM_CONFIG_STORAGE_KEY);
  if (!raw) return DEFAULT_LLM_CONFIG;
  try {
    return sanitizeLLMConfig(JSON.parse(raw));
  } catch {
    return DEFAULT_LLM_CONFIG;
  }
}

export function loadSavedLLMConfig(): LLMConfig | null {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(LLM_CONFIG_STORAGE_KEY);
  if (!raw) return null;
  try {
    return sanitizeLLMConfig(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function saveLLMConfig(config: LLMConfig): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(LLM_CONFIG_STORAGE_KEY, JSON.stringify(sanitizeLLMConfig(config)));
}

export function resetLLMConfig(): LLMConfig {
  if (typeof window !== 'undefined') window.localStorage.removeItem(LLM_CONFIG_STORAGE_KEY);
  return DEFAULT_LLM_CONFIG;
}

export function findProviderByBase(apiBase: string): LLMProvider | undefined {
  return LLM_PROVIDERS.find(p => p.api_base === apiBase);
}

// ── Preset helpers ──────────────────────────────────────────────

export type Preset = {
  id: string;
  name: string;
  provider: string;
  model: string;
  api_base: string;
};

function buildAllPresets(): Preset[] {
  const presets: Preset[] = [];
  for (const provider of LLM_PROVIDERS) {
    for (const model of provider.models) {
      presets.push({
        id: `${provider.id}:${model}`,
        name: model,
        provider: provider.name,
        model,
        api_base: provider.api_base,
      });
    }
  }
  return presets;
}

const ALL_PRESETS: Preset[] = buildAllPresets();

export function getPresetById(id: string): Preset | undefined {
  return ALL_PRESETS.find(p => p.id === id);
}

export function findPresetIdByConfig(config: LLMConfig): string {
  const match = ALL_PRESETS.find(
    p => p.model === config.model && p.api_base === config.api_base,
  );
  return match?.id ?? '';
}

export type PresetGroup = {
  provider: string;
  items: Preset[];
};

export function groupPresetsByProvider(): PresetGroup[] {
  const map = new Map<string, Preset[]>();
  for (const preset of ALL_PRESETS) {
    const list = map.get(preset.provider) || [];
    list.push(preset);
    map.set(preset.provider, list);
  }
  return Array.from(map.entries()).map(([provider, items]) => ({ provider, items }));
}
