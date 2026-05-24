export type ResumeGenerationPreferences = {
  schema_version?: "v1";
  target?: {
    role?: string;
    seniority?: string;
    industry?: string;
    job_family?: string;
  };
  locale?: {
    language?: string;
    region?: string;
  };
  content?: {
    tone?: string;
    focus_areas?: string[];
    highlight_keywords?: string[];
    avoid_keywords?: string[];
  };
  formatting?: {
    length_limit?: number;
    section_order?: string[];
    bullet_style?: string;
    date_style?: string;
  };
  ats?: {
    optimize_for_ats?: boolean;
    keyword_density?: "low" | "balanced" | "high";
  };
  generation?: {
    strict_factuality?: boolean;
    allow_inference?: boolean;
  };
  compliance?: {
    exclude_sensitive_info?: boolean;
    redact_fields?: string[];
  };
  presentation?: {
    theme?: string;
    density?: "compact" | "standard" | "comfortable";
  };
  metadata?: Record<string, unknown>;
  theme?: string;
  language?: string;
  tone?: string;
  section_order?: string[];
  length_limit?: number;
};

export type DocumentType = "resume";

export type AgentRunResponse = {
  raw_resume_obj: Record<string, unknown>;
  suggestion_resume_obj: {
    items: Array<{
      section?: string;
      path: string;
      current_value: string;
      suggested_value: string;
      reason: string;
    }>;
  };
  refined_resume_obj: Record<string, unknown>;
  resume_obj: Record<string, unknown>;
  quality_report?: Record<string, unknown>;
  section_quality_map?: Record<string, unknown>;
  applied_changes?: Array<Record<string, unknown>>;
  design_spec: Record<string, unknown>;
  output_markdown: string;
  output_html: string;
};

export type ImportedFileRecord = {
  id: string;
  file_name: string;
  file_ext: string;
  char_count: number;
  raw_text_preview: string;
  raw_text_path: string;
  created_at: string;
  raw_text?: string;
};

export type JobDescriptionRecord = {
  id: string;
  title: string;
  char_count: number;
  content_preview: string;
  content_path: string;
  created_at: string;
  updated_at: string;
  content?: string;
};

export type RecentResumeRecord = {
  id: string;
  title: string;
  status: string;
  source: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  resume_obj_path: string;
  output_markdown_path: string;
  output_html_path: string;
  template_name?: string;
  doc_type?: DocumentType;
  design_spec?: Record<string, unknown>;
  layout_preferences?: ResumeGenerationPreferences;
  resume_obj?: Record<string, unknown>;
  output_markdown?: string;
  output_html?: string;
};

export type SuggestionItem = {
  section?: string;
  path: string;
  op?: string;
  item_key?: string;
  status?: 'pending' | 'applied' | 'rejected';
  current_value: string;
  suggested_value: string;
  reason: string;
  current_value_raw?: unknown;
  suggested_value_raw?: unknown;
  refined_text?: string;
  refined_value_raw?: unknown;
  suggestion?: string;
  option_id?: string;
  option_label?: string;
  actionability?: 'apply_ready' | 'confirm_required';
  requires_confirmation?: boolean;
  confirmation_hint?: string;
  confidence?: number;
  confidence_reason?: string;
  low_confidence?: boolean;
  style_variant?: 'conservative' | 'impact' | string;
  reason_meta?: {
    change_type?: string;
    expected_effect?: string;
  };
  diff_payload?: {
    diff_type: 'text' | string;
    before_text: string;
    after_text: string;
    chunks: Array<{
      type: 'same' | 'add' | 'remove' | string;
      text: string;
    }>;
  };
};

export type LowConfidenceItem = {
  path: string;
  item_key: string;
  confidence: number;
  confidence_reason: string;
  reason: string;
  refined_text: string;
};


export type SessionNodeEvent = {
  id: number;
  session_id: string;
  turn_id: string;
  node_name: string;
  status: string;
  duration_ms: number;
  payload: Record<string, unknown>;
  error: string;
  created_at: string;
};

export type V3SessionStartResponse = {
  session_id: string;
  doc_type: DocumentType;
  title: string;
  status: string;
  window_size: number;
  created_at: string;
  updated_at: string;
  state: {
    raw_document_obj: Record<string, unknown>;
    normalized_document_obj: Record<string, unknown>;
    refined_document_obj: Record<string, unknown>;
    rag_context_by_path: Record<string, unknown>;
    suggestion_document_obj: {
      items: SuggestionItem[];
    };
    review_payload: {
      items: Array<{
        id?: number;
        section?: string;
        path?: string;
        current_value?: string;
        suggested_value?: string;
        reason?: string;
        status?: string;
      }>;
      summary?: Record<string, unknown>;
    };
    quality_report: Record<string, unknown>;
    section_quality_map: Record<string, unknown>;
    updated_at: string;
  };
};


export type V3RollbackResponse = {
  session_id: string;
  rolled_back_to_version_id: string;
  new_current_version_id: string;
  refined_document_obj: Record<string, unknown>;
  refined_resume_obj?: Record<string, unknown>;
};

export type TurnOutputBundle = {
  assistant_message: string;
  suggestion_document_obj: {
    items: SuggestionItem[];
  };
  actionability_summary: {
    total: number;
    apply_ready: number;
    confirm_required: number;
  };
  fact_issues: Array<{
    path?: string;
    item_key?: string;
    confirmation_hint?: string;
    reason?: string;
  }>;
  low_confidence_items: Array<{
    path: string;
    item_key: string;
    confidence: number;
    confidence_reason: string;
    reason: string;
    refined_text: string;
  }>;
  step_reason_summary: Array<{
    step_id: string;
    tool: string;
    reason_brief: string;
  }>;
  self_check_result: {
    result: 'pass' | 'retry_once' | 'fail_soft';
    reason: string;
  };
  planner_decision_trace?: Array<{
    step_index?: number;
    intent_class?: string;
    tool?: string;
    reason_brief?: string;
  }>;
  thought_summary?: string[];
  content_assessment?: {
    candidate_count?: number;
    changed_count?: number;
    material_change_count?: number;
    fact_issue_count?: number;
    style_variants?: string[];
  };
  intent_state?: {
    intent_class?: string;
    active_scope?: string;
    goal?: string;
    confidence?: number;
    requires_fact_confirmation?: boolean;
    reason_brief?: string;
  };
  interview?: {
    ended?: boolean;
    tools?: string[];
    phase?: string;
    attitude?: 'neutral' | 'waiting' | 'interested' | 'skeptical' | 'impatient' | 'satisfied';
    message_blocks?: string[];
    next_wait_seconds?: number;
    silence_threshold_sec?: number;
  };
};

export type V3SessionTurnResponse = {
  session_id: string;
  doc_type?: DocumentType;
  turn_id: string;
  selected_steps?: Array<{
    step_id: string;
    tool: string;
    status?: string;
    duration_ms?: number;
    reason_brief?: string;
  }>;
  selected_tool_chain?: string[];
  step_outputs_summary?: {
    count: number;
    keys: string[];
  };
  termination_reason?: string;
  turn_output_bundle?: TurnOutputBundle;
  assistant_message: string;
  suggestion_document_obj: {
    items: SuggestionItem[];
  };
  suggestion_resume_obj?: {
    items: SuggestionItem[];
  };
  actionability_summary?: {
    total?: number;
    apply_ready?: number;
    confirm_required?: number;
  };
  fact_issues?: Array<Record<string, unknown>>;
  step_reason_summary?: Array<Record<string, unknown>>;
  self_check_result?: Record<string, unknown>;
  planner_decision_trace?: Array<Record<string, unknown>>;
  thought_summary?: string[];
  content_assessment?: Record<string, unknown>;
  intent_state?: Record<string, unknown>;
  vague_actions?: Array<{ label: string; text: string; reason: string }>;
  rag_context_by_path: Record<string, unknown>;
  refined_document_obj: Record<string, unknown>;
  refined_resume_obj?: Record<string, unknown>;
  execution_policy?: string;
  quality_report: Record<string, unknown>;
  section_quality_map: Record<string, unknown>;
  node_events: SessionNodeEvent[];
};

export type V3SessionApplyDecisionResponse = {
  session_id: string;
  turn_id: string;
  assistant_message: string;
  document_obj: Record<string, unknown>;
  resume_obj?: Record<string, unknown>;
  refined_document_obj?: Record<string, unknown>;
  applied_changes: Array<Record<string, unknown>>;
  suggestion_document_obj: {
    items: SuggestionItem[];
  };
  actionability_summary?: {
    total?: number;
    apply_ready?: number;
    confirm_required?: number;
  };
  termination_reason?: string;
  turn_output_bundle?: TurnOutputBundle;
  validation_report?: Record<string, unknown>;
  decision_meta?: Record<string, unknown>;
  node_events: SessionNodeEvent[];
};
