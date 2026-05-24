import type { SuggestionItem } from '../../types';

export type JDMatch = {
  id: string;
  text: string;
  metadata?: Record<string, unknown>;
};

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  text: string;
  thinking?: string;
  timestamp: string;
  showApplyAction?: boolean;
  applyFocusPath?: string;
  applySuggestionItems?: SuggestionItem[];
  jdMatches?: JDMatch[];
  threadSteps?: NodeThreadStep[];
  threadRunning?: boolean;
  threadTitle?: string;
};

export type NodeStatus = 'pending' | 'running' | 'done' | 'failed';

export type NodeThreadStep = {
  key: string;
  label: string;
  status: NodeStatus;
  ms?: number;
  error?: string;
  thinking?: string;
};

export type ThreadBubbleUpdate = {
  id: string;
  title: string;
  running: boolean;
  steps: NodeThreadStep[];
};

export type ResumeDagNode = {
  id: string;
  state: 'draft' | 'refined' | 'applied' | 'saved' | 'processing' | 'candidate';
  contentHash: string;
  createdAt: string;
  label: string;
  current: boolean;
  snapshot?: Record<string, unknown>;
  candidateMeta?: {
    path?: string;
    optionLabel?: string;
  };
};

export type ResumeDagEdge = {
  id: string;
  fromNodeId: string;
  toNodeId: string;
  actionType: 'apply' | 'save' | 'reject' | 'rollback' | 'candidate' | 'system' | 'chat';
  status: 'running' | 'success' | 'failed';
  createdAt: string;
  finishedAt?: string;
  note?: string;
};

export type ResumeDagGraph = {
  nodes: ResumeDagNode[];
  edges: ResumeDagEdge[];
  currentNodeId: string;
};

export type DagPendingAction = {
  edgeId: string;
  ghostNodeId: string;
  fromNodeId: string;
};

export type ToolEventLite = {
  id: number;
  tool: string;
  status: string;
  durationMs: number;
  error: string;
};

export type ResumeSessionListItem = {
  resumeId: string;
  title: string;
  updatedAt: string;
  hasDraft: boolean;
  isRunning: boolean;
  isApplying: boolean;
};

export type TailorPersistedState = {
  version: number;
  resumeId: string;
  messages: ChatMessage[];
  inputText: string;
  statusText: string;
  errorText: string;
  isRunning: boolean;
  isApplying: boolean;
  rawResumeObj: Record<string, unknown>;
  normalizedResumeObj: Record<string, unknown>;
  refinedResumeObj: Record<string, unknown>;
  pendingChanges: PendingChange[];
  showChangeToolbar: boolean;
  activeSuggestionPath: string;
  dagGraph: ResumeDagGraph;
  dagWindowCollapsed: boolean;
  updatedAt: string;
};

export type DiffChunk = {
  type: 'same' | 'add' | 'remove';
  text: string;
};

export type ChangeVariant = {
  suggested_value: string;
  reason: string;
  option_id: string;
  option_label: string;
  style_variant?: string;
};

export type PendingChange = {
  path: string;
  section?: string;
  current_value: string;
  item_key: string;
  op?: string;
  lowConfidence?: boolean;
  confidence?: number;
  confidenceReason?: string;
  diff_payload?: {
    before_text: string;
    after_text: string;
    chunks: DiffChunk[];
  };
  variants: ChangeVariant[];
};

export type TurnSnapshot = {
  nodeId: string;
  content: Record<string, unknown>;
};
