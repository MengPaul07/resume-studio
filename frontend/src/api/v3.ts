import type {
  DocumentType,
  SuggestionItem,
  V3SessionApplyDecisionResponse,
  V3SessionStartResponse,
  V3SessionTurnResponse,
  V3RollbackResponse,
  ResumeGenerationPreferences,
} from '../types';
import { getEffectiveLLMConfig, type LLMConfigPayload } from './llm';
import { postJson, requestJson } from './http';
import { postSSEAndCollectFinal } from './sse';

export async function toolChat(params: {
  doc_type?: DocumentType;
  session_id: string;
  message: string;
  allow_mutation?: boolean;
  approved_tool_chain?: Array<{ tool: string; arguments?: Record<string, unknown> }>;
  llm_config?: LLMConfigPayload;
  layout_preferences?: ResumeGenerationPreferences;
  target_jd?: string;
  mode?: string;
  interview_config?: Record<string, unknown>;
  onEvent?: (event: string, data: Record<string, unknown>) => void;
}): Promise<V3SessionTurnResponse> {
  return postSSEAndCollectFinal<V3SessionTurnResponse>({
    path: `/agent/v3/sessions/${encodeURIComponent(params.session_id)}/turns:run`,
    body: {
      doc_type: params.doc_type ?? 'resume',
      message: params.message,
      allow_mutation: params.allow_mutation ?? false,
      approved_tool_chain: params.approved_tool_chain ?? [],
      llm_config: getEffectiveLLMConfig(params.llm_config),
      layout_preferences: params.layout_preferences ?? {},
      target_jd: params.target_jd ?? '',
      mode: params.mode ?? 'refine',
      interview_config: params.interview_config ?? {},
    },
    messagePrefix: 'Tool chat failed',
    onEvent: params.onEvent,
  });
}

export async function toolResumeTurn(params: {
  session_id: string;
  turn_id: string;
  user_response?: string;
  llm_config?: LLMConfigPayload;
}): Promise<Record<string, unknown>> {
  return postJson<Record<string, unknown>>(
    `/agent/v3/sessions/${encodeURIComponent(params.session_id)}/turns:resume`,
    {
      llm_config: getEffectiveLLMConfig(params.llm_config),
      turn_id: params.turn_id,
      user_response: params.user_response ?? 'Confirmed.',
    },
    'Resume turn failed',
  );
}

export async function toolActionsApply(params: {
  doc_type?: DocumentType;
  session_id: string;
  human_review_decision: {
    apply_all?: boolean;
    accepted_item_keys?: string[];
    overrides?: Array<{ path: string; value: unknown }>;
  };
  suggestion_document_obj?: {
    items: SuggestionItem[];
  };
  llm_config?: LLMConfigPayload;
}): Promise<V3SessionApplyDecisionResponse> {
  return postJson<V3SessionApplyDecisionResponse>(
    `/agent/v3/sessions/${encodeURIComponent(params.session_id)}/actions:apply`,
    {
      doc_type: params.doc_type ?? 'resume',
      llm_config: getEffectiveLLMConfig(params.llm_config),
      human_review_decision: params.human_review_decision,
      suggestion_document_obj: params.suggestion_document_obj ?? {},
    },
    'Tool actions apply failed',
  );
}

export async function toolActionsReject(params: {
  doc_type?: DocumentType;
  session_id: string;
  rejected_item_keys?: string[];
  reject_all?: boolean;
  suggestion_document_obj?: {
    items: SuggestionItem[];
  };
  llm_config?: LLMConfigPayload;
}): Promise<V3SessionApplyDecisionResponse> {
  return postJson<V3SessionApplyDecisionResponse>(
    `/agent/v3/sessions/${encodeURIComponent(params.session_id)}/actions:reject`,
    {
      doc_type: params.doc_type ?? 'resume',
      llm_config: getEffectiveLLMConfig(params.llm_config),
      rejected_item_keys: params.rejected_item_keys ?? [],
      reject_all: Boolean(params.reject_all),
      suggestion_document_obj: params.suggestion_document_obj ?? {},
    },
    'Tool actions reject failed',
  );
}

export async function toolSessionStart(params: {
  doc_type?: DocumentType;
  resume_id?: string;
  title?: string;
  window_size?: number;
  raw_document_obj?: Record<string, unknown>;
  normalized_document_obj?: Record<string, unknown>;
  refined_document_obj?: Record<string, unknown>;
  raw_resume_obj?: Record<string, unknown>;
  normalized_resume_obj?: Record<string, unknown>;
  refined_resume_obj?: Record<string, unknown>;
  llm_config?: LLMConfigPayload;
  layout_preferences?: ResumeGenerationPreferences;
}): Promise<V3SessionStartResponse> {
  return postJson<V3SessionStartResponse>(
    '/agent/v3/sessions',
    {
      resume_id: params.resume_id ?? '',
      doc_type: params.doc_type ?? 'resume',
      title: params.title ?? 'Tailor Session',
      window_size: params.window_size ?? 10,
      raw_document_obj: params.raw_document_obj ?? params.raw_resume_obj ?? {},
      normalized_document_obj: params.normalized_document_obj ?? params.normalized_resume_obj ?? {},
      refined_document_obj: params.refined_document_obj ?? params.refined_resume_obj ?? {},
      raw_resume_obj: params.raw_resume_obj ?? {},
      normalized_resume_obj: params.normalized_resume_obj ?? {},
      refined_resume_obj: params.refined_resume_obj ?? {},
      llm_config: getEffectiveLLMConfig(params.llm_config),
      layout_preferences: params.layout_preferences ?? {},
    },
    'Tool start session failed',
  );
}

export async function toolGetSessionContent(params: {
  session_id: string;
  message_limit?: number;
  event_limit?: number;
}): Promise<Record<string, unknown>> {
  const messageLimit = params.message_limit ?? 50;
  const eventLimit = params.event_limit ?? 200;
  return requestJson<Record<string, unknown>>(
    `/agent/v3/sessions/${encodeURIComponent(params.session_id)}?message_limit=${encodeURIComponent(String(messageLimit))}&event_limit=${encodeURIComponent(String(eventLimit))}`,
    { method: 'GET' },
    'Tool get session content failed',
  );
}

export async function toolRollbackVersion(params: {
  session_id: string;
  version_id: string;
  note?: string;
}): Promise<V3RollbackResponse> {
  return postJson<V3RollbackResponse>(
    `/agent/v3/sessions/${encodeURIComponent(params.session_id)}/rollback`,
    {
      version_id: params.version_id,
      note: params.note ?? '',
    },
    'Tool rollback failed',
  );
}
