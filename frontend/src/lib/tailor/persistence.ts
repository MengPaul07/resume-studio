import type { RecentResumeRecord } from '../../types';
import type {
  ChatMessage,
  PendingChange,
  ResumeDagEdge,
  ResumeDagGraph,
  ResumeDagNode,
  ResumeSessionListItem,
  TailorPersistedState,
} from './types';
import { TAILOR_PERSIST_VERSION, TAILOR_STORAGE_PREFIX } from './constants';
import { toJsonObject, sanitizePersistedMessage, isBootstrapSystemMessage } from './utils';

function getTailorStorageKey(resumeId: string): string {
  return `${TAILOR_STORAGE_PREFIX}${resumeId}`;
}

function migrateV1ToV2(parsed: Record<string, unknown>, resumeId: string): TailorPersistedState {
  return {
    version: 2,
    resumeId,
    messages: Array.isArray(parsed.messages) ? (parsed.messages as ChatMessage[]).slice(-120) : [],
    inputText: typeof parsed.inputText === 'string' ? parsed.inputText : '',
    statusText: typeof parsed.statusText === 'string' ? parsed.statusText : '',
    errorText: typeof parsed.errorText === 'string' ? parsed.errorText : '',
    isRunning: false,
    isApplying: false,
    rawResumeObj: toJsonObject(parsed.rawResumeObj || {}),
    normalizedResumeObj: toJsonObject(parsed.normalizedResumeObj || {}),
    refinedResumeObj: toJsonObject(parsed.refinedResumeObj || {}),
    pendingChanges: [],
    showChangeToolbar: false,
    activeSuggestionPath:
      typeof parsed.activeSuggestionPath === 'string' ? parsed.activeSuggestionPath : '',
    dagGraph: parseDagGraph(parsed.dagGraph),
    dagWindowCollapsed: Boolean(parsed.dagWindowCollapsed),
    updatedAt:
      typeof parsed.updatedAt === 'string' ? parsed.updatedAt : new Date().toISOString(),
  };
}

function parseDagGraph(raw: unknown): ResumeDagGraph {
  if (!raw || typeof raw !== 'object') {
    return { nodes: [], edges: [], currentNodeId: '' };
  }
  const obj = raw as Record<string, unknown>;
  return {
    nodes: Array.isArray(obj.nodes) ? (obj.nodes as ResumeDagNode[]) : [],
    edges: Array.isArray(obj.edges) ? (obj.edges as ResumeDagEdge[]) : [],
    currentNodeId: String(obj.currentNodeId || ''),
  };
}

export function readTailorPersistedState(resumeId: string): TailorPersistedState | null {
  if (!resumeId || typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(getTailorStorageKey(resumeId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (!parsed || typeof parsed !== 'object') return null;

    const storedVersion = Number(parsed.version || 0);

    if (storedVersion === 1) {
      return migrateV1ToV2(parsed, resumeId);
    }

    if (storedVersion !== TAILOR_PERSIST_VERSION) return null;
    if (parsed.resumeId !== resumeId) return null;

    return {
      version: TAILOR_PERSIST_VERSION,
      resumeId,
      messages: Array.isArray(parsed.messages) ? (parsed.messages as ChatMessage[]).slice(-120) : [],
      inputText: typeof parsed.inputText === 'string' ? parsed.inputText : '',
      statusText: typeof parsed.statusText === 'string' ? parsed.statusText : '',
      errorText: typeof parsed.errorText === 'string' ? parsed.errorText : '',
      isRunning: false,
      isApplying: false,
      rawResumeObj: toJsonObject(parsed.rawResumeObj || {}),
      normalizedResumeObj: toJsonObject(parsed.normalizedResumeObj || {}),
      refinedResumeObj: toJsonObject(parsed.refinedResumeObj || {}),
      pendingChanges: Array.isArray(parsed.pendingChanges)
        ? (parsed.pendingChanges as PendingChange[])
        : [],
      showChangeToolbar: Boolean(parsed.showChangeToolbar),
      activeSuggestionPath:
        typeof parsed.activeSuggestionPath === 'string' ? parsed.activeSuggestionPath : '',
      dagGraph: parseDagGraph(parsed.dagGraph),
      dagWindowCollapsed: Boolean(parsed.dagWindowCollapsed),
      updatedAt:
        typeof parsed.updatedAt === 'string' ? parsed.updatedAt : new Date().toISOString(),
    };
  } catch {
    return null;
  }
}

export function writeTailorPersistedState(
  resumeId: string,
  payload: TailorPersistedState,
): void {
  if (!resumeId || typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(getTailorStorageKey(resumeId), JSON.stringify(payload));
  } catch {
    // ignore persistence errors
  }
}

export function toSessionListItem(record: RecentResumeRecord): ResumeSessionListItem {
  const persisted = readTailorPersistedState(record.id);
  return {
    resumeId: record.id,
    title: record.title || 'Untitled Resume',
    updatedAt:
      persisted?.updatedAt || record.updated_at || record.created_at || new Date().toISOString(),
    hasDraft: Boolean(persisted),
    isRunning: Boolean(persisted?.isRunning),
    isApplying: Boolean(persisted?.isApplying),
  };
}
