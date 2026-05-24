import { useCallback, useEffect, useState } from 'react';
import { useRefSyncedState } from './useRefSyncedState';
import { useSearchParams } from 'react-router-dom';
import {
  getRecentResume,
  listRecentResumes,
  saveRecentResume,
  toolSessionStart,
} from '../api';
import { DEFAULT_PREFERENCES } from '../preferences';
import { TAILOR_PERSIST_VERSION } from '../lib/tailor/constants';
import {
  readTailorPersistedState,
  writeTailorPersistedState,
  toSessionListItem,
} from '../lib/tailor/persistence';
import { toJsonObject, sanitizePersistedMessage, isBootstrapSystemMessage, createDagNode } from '../lib/tailor/utils';
import type { RecentResumeRecord } from '../types';
import type {
  ChatMessage,
  PendingChange,
  ResumeDagGraph,
  ResumeSessionListItem,
  TailorPersistedState,
  TurnSnapshot,
} from '../lib/tailor/types';

export interface UseTailorSessionReturn {
  resumeRecord: RecentResumeRecord | null;
  sessionId: string;
  setSessionId: (id: string) => void;
  rawResumeObj: Record<string, unknown>;
  setRawResumeObj: React.Dispatch<React.SetStateAction<Record<string, unknown>>>;
  normalizedResumeObj: Record<string, unknown>;
  setNormalizedResumeObj: React.Dispatch<React.SetStateAction<Record<string, unknown>>>;
  refinedResumeObj: Record<string, unknown>;
  setRefinedResumeObj: React.Dispatch<React.SetStateAction<Record<string, unknown>>>;
  ragContext: Record<string, unknown>;
  setRagContext: React.Dispatch<React.SetStateAction<Record<string, unknown>>>;
  isBootstrapping: boolean;
  needsImport: boolean;
  isSaving: boolean;
  sessionListLoading: boolean;
  resumeSessions: ResumeSessionListItem[];
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  inputText: string;
  setInputText: React.Dispatch<React.SetStateAction<string>>;
  statusText: string;
  setStatusText: React.Dispatch<React.SetStateAction<string>>;
  errorText: string;
  setErrorText: React.Dispatch<React.SetStateAction<string>>;
  isRunning: boolean;
  setIsRunning: React.Dispatch<React.SetStateAction<boolean>>;
  isApplying: boolean;
  setIsApplying: React.Dispatch<React.SetStateAction<boolean>>;
  activeSuggestionPath: string;
  pendingChanges: PendingChange[];
  setPendingChanges: React.Dispatch<React.SetStateAction<PendingChange[]>>;
  showChangeToolbar: boolean;
  setShowChangeToolbar: React.Dispatch<React.SetStateAction<boolean>>;
  expandedChangePaths: Set<string>;
  setExpandedChangePaths: React.Dispatch<React.SetStateAction<Set<string>>>;
  preTurnSnapshot: TurnSnapshot | null;
  setPreTurnSnapshot: React.Dispatch<React.SetStateAction<TurnSnapshot | null>>;
  setActiveSuggestionPath: React.Dispatch<React.SetStateAction<string>>;
  dagGraph: ResumeDagGraph;
  setDagGraph: React.Dispatch<React.SetStateAction<ResumeDagGraph>>;
  dagWindowCollapsed: boolean;
  setDagWindowCollapsed: React.Dispatch<React.SetStateAction<boolean>>;
  persistTailorState: (
    resumeKey: string,
    overrides?: Partial<Omit<TailorPersistedState, 'version' | 'resumeId' | 'updatedAt'>>,
  ) => void;
  refreshResumeSessions: (preloaded?: RecentResumeRecord[], force?: boolean) => Promise<void>;
  handleSaveTailoredResume: () => Promise<void>;
  // Refs for latest state access in async callbacks
  messagesRef: React.MutableRefObject<ChatMessage[]>;
  rawResumeObjRef: React.MutableRefObject<Record<string, unknown>>;
  normalizedResumeObjRef: React.MutableRefObject<Record<string, unknown>>;
  refinedResumeObjRef: React.MutableRefObject<Record<string, unknown>>;
  inputTextRef: React.MutableRefObject<string>;
  statusTextRef: React.MutableRefObject<string>;
  errorTextRef: React.MutableRefObject<string>;
  isRunningRef: React.MutableRefObject<boolean>;
  isApplyingRef: React.MutableRefObject<boolean>;
  dagGraphRef: React.MutableRefObject<ResumeDagGraph>;
  pendingChangesRef: React.MutableRefObject<PendingChange[]>;
  showChangeToolbarRef: React.MutableRefObject<boolean>;
  preTurnSnapshotRef: React.MutableRefObject<TurnSnapshot | null>;
  activeSuggestionPathRef: React.MutableRefObject<string>;
}

export function useTailorSession(): UseTailorSessionReturn {
  const [searchParams, setSearchParams] = useSearchParams();
  const resumeId = searchParams.get('resumeId') || '';

  // State
  const [resumeRecord, setResumeRecord] = useState<RecentResumeRecord | null>(null);
  const [sessionId, setSessionId] = useState('');
  const [messages, setMessages, messagesRef] = useRefSyncedState<ChatMessage[]>([
    { id: 'sys-1', role: 'system', text: 'V3 CLI-style Tailor Chat is ready.', timestamp: new Date().toISOString() },
  ]);
  const [rawResumeObj, setRawResumeObj, rawResumeObjRef] = useRefSyncedState<Record<string, unknown>>({});
  const [normalizedResumeObj, setNormalizedResumeObj, normalizedResumeObjRef] = useRefSyncedState<Record<string, unknown>>({});
  const [refinedResumeObj, setRefinedResumeObj, refinedResumeObjRef] = useRefSyncedState<Record<string, unknown>>({});
  const [ragContext, setRagContext] = useState<Record<string, unknown>>({});
  const [pendingChanges, setPendingChanges, pendingChangesRef] = useRefSyncedState<PendingChange[]>([]);
  const [showChangeToolbar, setShowChangeToolbar, showChangeToolbarRef] = useRefSyncedState(false);
  const [expandedChangePaths, setExpandedChangePaths] = useState<Set<string>>(new Set());
  const [preTurnSnapshot, setPreTurnSnapshot, preTurnSnapshotRef] = useRefSyncedState<TurnSnapshot | null>(null);
  const [activeSuggestionPath, setActiveSuggestionPath, activeSuggestionPathRef] = useRefSyncedState('');
  const [inputText, setInputText, inputTextRef] = useRefSyncedState('');
  const [statusText, setStatusText, statusTextRef] = useRefSyncedState('');
  const [errorText, setErrorText, errorTextRef] = useRefSyncedState('');
  const [isRunning, setIsRunning, isRunningRef] = useRefSyncedState(false);
  const [isApplying, setIsApplying, isApplyingRef] = useRefSyncedState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [needsImport, setNeedsImport] = useState(false);
  const [sessionListLoading, setSessionListLoading] = useState(false);
  const [resumeSessions, setResumeSessions] = useState<ResumeSessionListItem[]>([]);
  const [dagGraph, setDagGraph, dagGraphRef] = useRefSyncedState<ResumeDagGraph>({ nodes: [], edges: [], currentNodeId: '' });
  const [dagWindowCollapsed, setDagWindowCollapsed] = useState(false);

  // ── Persistence ────────────────────────────────────────────────

  const persistTailorState = useCallback(
    (
      resumeKey: string,
      overrides?: Partial<Omit<TailorPersistedState, 'version' | 'resumeId' | 'updatedAt'>>,
    ) => {
      if (!resumeKey) return;
      const payload: TailorPersistedState = {
        version: TAILOR_PERSIST_VERSION,
        resumeId: resumeKey,
        messages: (overrides?.messages ?? messagesRef.current)
          .map((msg) => sanitizePersistedMessage(msg))
          .filter((msg) => !isBootstrapSystemMessage(msg))
          .slice(-120),
        inputText: overrides?.inputText ?? inputTextRef.current,
        statusText: overrides?.statusText ?? statusTextRef.current,
        errorText: overrides?.errorText ?? errorTextRef.current,
        isRunning: false,
        isApplying: false,
        rawResumeObj: toJsonObject(overrides?.rawResumeObj ?? rawResumeObjRef.current),
        normalizedResumeObj: toJsonObject(overrides?.normalizedResumeObj ?? normalizedResumeObjRef.current),
        refinedResumeObj: toJsonObject(overrides?.refinedResumeObj ?? refinedResumeObjRef.current),
        pendingChanges: Array.isArray(overrides?.pendingChanges)
          ? overrides.pendingChanges
          : pendingChangesRef.current,
        showChangeToolbar: Boolean(overrides?.showChangeToolbar ?? showChangeToolbarRef.current),
        activeSuggestionPath: overrides?.activeSuggestionPath ?? activeSuggestionPathRef.current,
        dagGraph: (overrides?.dagGraph ?? dagGraphRef.current) as ResumeDagGraph,
        dagWindowCollapsed: Boolean(overrides?.dagWindowCollapsed ?? dagWindowCollapsed),
        updatedAt: new Date().toISOString(),
      };
      writeTailorPersistedState(resumeKey, payload);
      setResumeSessions((prev) =>
        prev.map((item) =>
          item.resumeId === resumeKey
            ? { ...item, updatedAt: payload.updatedAt, hasDraft: true, isRunning: payload.isRunning, isApplying: payload.isApplying }
            : item,
        ),
      );
    },
    [dagWindowCollapsed],
  );

  const applyRecentRecordsToSessionList = useCallback((records: RecentResumeRecord[]) => {
    const items = (records || [])
      .map((record) => toSessionListItem(record))
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
    setResumeSessions(items);
  }, []);

  const refreshResumeSessions = useCallback(
    async (preloaded?: RecentResumeRecord[], force = false) => {
      setSessionListLoading(true);
      try {
        const records = Array.isArray(preloaded) ? preloaded : await listRecentResumes(20, force);
        applyRecentRecordsToSessionList(records);
      } finally {
        setSessionListLoading(false);
      }
    },
    [applyRecentRecordsToSessionList],
  );

  const startSessionForCurrentDocType = useCallback(
    async (base: Record<string, unknown>, title: string) => {
      const session = await toolSessionStart({
        resume_id: resumeId,
        doc_type: 'resume',
        title: title || 'Tailor Session',
        window_size: 10,
        raw_document_obj: base,
        normalized_document_obj: base,
        refined_document_obj: base,
        raw_resume_obj: base,
        normalized_resume_obj: base,
        refined_resume_obj: base,
        layout_preferences: DEFAULT_PREFERENCES,
      });
      setSessionId(session.session_id || '');
      setPendingChanges([]);
      setShowChangeToolbar(false);
      setExpandedChangePaths(new Set());
      setPreTurnSnapshot(null);
      setActiveSuggestionPath('');
      return session;
    },
    [resumeId],
  );

  // ── Bootstrap ──────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;
    async function bootstrapTailor() {
      setErrorText('');
      setNeedsImport(false);
      setIsBootstrapping(true);
      try {
        const recent = await listRecentResumes(20);
        if (cancelled) return;
        applyRecentRecordsToSessionList(recent);

        if (!resumeId) {
          if (recent.length > 0 && recent[0]?.id) {
            const next = new URLSearchParams();
            next.set('resumeId', recent[0].id);
            setSearchParams(next, { replace: true });
            return;
          }
          setResumeRecord(null);
          setSessionId('');
          setRawResumeObj({});
          setNormalizedResumeObj({});
          setRefinedResumeObj({});
          setPendingChanges([]);
          setShowChangeToolbar(false);
          setExpandedChangePaths(new Set());
          setPreTurnSnapshot(null);
          setActiveSuggestionPath('');
          setDagGraph({ nodes: [], edges: [], currentNodeId: '' });
          setNeedsImport(true);
          setStatusText('暂无可用简历，请先导入后再进入 Tailor。');
          return;
        }

        const record = await getRecentResume(resumeId);
        if (cancelled) return;
        setResumeRecord(record);
        const persisted = readTailorPersistedState(resumeId);
        const rawBase = toJsonObject(record.resume_obj || {});
        const persistedRaw = toJsonObject(persisted?.rawResumeObj || {});
        const persistedNormalized = toJsonObject(persisted?.normalizedResumeObj || {});
        const persistedRefined = toJsonObject(persisted?.refinedResumeObj || {});
        // Guard: detect corrupted localStorage data (struct arrays containing strings
        // instead of objects — caused by LLM passing pipe-delimited text to edit_field).
        // If corrupted, discard and use clean file data instead.
        const _structSections = ['workExperience', 'education', 'personalProjects', 'research'];
        const _isCorrupted = _structSections.some((key) => {
          const arr = persistedRefined[key];
          return Array.isArray(arr) && arr.length > 0 && arr.some(
            (item: unknown) => typeof item === 'string'
          );
        });
        const base = (!_isCorrupted && Object.keys(persistedRefined).length)
          ? persistedRefined : rawBase;
        setRawResumeObj(Object.keys(persistedRaw).length ? persistedRaw : rawBase);
        setNormalizedResumeObj(Object.keys(persistedNormalized).length ? persistedNormalized : base);
        setRefinedResumeObj(base);
        setPendingChanges(Array.isArray(persisted?.pendingChanges) ? persisted!.pendingChanges : []);
        setShowChangeToolbar(Boolean(persisted?.showChangeToolbar));
        setExpandedChangePaths(new Set());
        setPreTurnSnapshot(null);
        setActiveSuggestionPath(persisted?.activeSuggestionPath || '');
        const persistedDag = persisted?.dagGraph;
        const baseNode = createDagNode('draft', base, true, new Date().toISOString());
        const persistedCurrentNodeId =
          (persistedDag?.currentNodeId || '') ||
          (Array.isArray(persistedDag?.nodes) && persistedDag?.nodes?.length
            ? persistedDag.nodes[persistedDag.nodes.length - 1]?.id || ''
            : '');
        const safePersistedDag =
          persistedDag &&
          Array.isArray(persistedDag.nodes) &&
          persistedDag.nodes.length > 0 &&
          persistedDag.nodes.length <= 300 &&
          Array.isArray(persistedDag.edges) &&
          persistedDag.edges.length <= 800
            ? persistedDag
            : null;
        const nextDag: ResumeDagGraph = safePersistedDag
          ? {
              nodes: safePersistedDag.nodes.map((node) => ({
                ...node,
                current: node.id === persistedCurrentNodeId,
                snapshot:
                  node && typeof node.snapshot === 'object' && node.snapshot
                    ? toJsonObject(node.snapshot)
                    : node.id === persistedCurrentNodeId
                      ? base
                      : undefined,
              })),
              edges: safePersistedDag.edges.filter((edge) => edge.fromNodeId !== edge.toNodeId),
              currentNodeId: persistedCurrentNodeId,
            }
          : { nodes: [baseNode], edges: [], currentNodeId: baseNode.id };
        setDagGraph(nextDag);
        setDagWindowCollapsed(Boolean(persisted?.dagWindowCollapsed));
        setInputText(persisted?.inputText || '');
        setErrorText(persisted?.errorText || '');
        if (persisted?.statusText) setStatusText(persisted.statusText);
        if (Array.isArray(persisted?.messages) && persisted.messages.length > 0) {
          setMessages(
            persisted.messages
              .filter((msg) => !isBootstrapSystemMessage(msg))
              .map((msg) => sanitizePersistedMessage(msg)),
          );
        }
        await startSessionForCurrentDocType(base, record.title || 'Tailor Session');
        if (cancelled) return;
      } catch (err) {
        if (cancelled) return;
        setErrorText(err instanceof Error ? err.message : 'Failed to load resume');
      } finally {
        if (!cancelled) setIsBootstrapping(false);
      }
    }
    bootstrapTailor();
    return () => {
      cancelled = true;
    };
  }, [resumeId, setSearchParams, applyRecentRecordsToSessionList, startSessionForCurrentDocType]);

  // BeforeUnload
  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (!isRunningRef.current && !isApplyingRef.current) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', beforeUnload);
    return () => {
      window.removeEventListener('beforeunload', beforeUnload);
      if (isRunningRef.current || isApplyingRef.current) {
        window.alert('AI 正在处理中，离开页面会中断当前进程。');
      }
    };
  }, []);

  // ── Save Handler ────────────────────────────────────────────────

  const handleSaveTailoredResume = useCallback(async () => {
    const record = resumeRecord;
    if (!record?.id) {
      setErrorText('当前没有可保存的简历。');
      return;
    }
    const refined = refinedResumeObjRef.current;
    if (!refined || Object.keys(refined).length === 0) {
      setErrorText('当前内容为空，无法保存。');
      return;
    }

    setIsSaving(true);
    setErrorText('');
    setStatusText('Saving tailored resume...');
    try {
      const saved = await saveRecentResume({
        resume_id: record.id,
        title: record.title || 'Untitled Resume',
        status: record.status || 'ready',
        source: record.source || 'tailor',
        tags: Array.isArray(record.tags) ? record.tags : [],
        resume_obj: refined,
        output_markdown: record.output_markdown || '',
        output_html: record.output_html || '',
        template_name: record.template_name || 'swiss-single',
        layout_preferences: DEFAULT_PREFERENCES,
      });
      setResumeRecord(saved);
      const savedObj = toJsonObject(saved.resume_obj || refined);
      setRawResumeObj(savedObj);
      setNormalizedResumeObj(savedObj);
      setRefinedResumeObj(savedObj);
      setStatusText(`Saved: ${saved.title}`);
      setMessages((prev) => [
        ...prev,
        {
          id: `sys-save-${Date.now()}`,
          role: 'system',
          text: `Saved current tailored content to "${saved.title}".`,
          timestamp: new Date().toISOString(),
        },
      ]);
      const persistResumeId = saved.id || record.id;
      persistTailorState(persistResumeId, {
        rawResumeObj: savedObj,
        normalizedResumeObj: savedObj,
        refinedResumeObj: savedObj,
        statusText: `Saved: ${saved.title}`,
        errorText: '',
      });
      await refreshResumeSessions(undefined, true);
    } catch (err) {
      setErrorText(err instanceof Error ? err.message : 'Save failed');
      setStatusText('Save failed');
    } finally {
      setIsSaving(false);
    }
  }, [resumeRecord, persistTailorState, refreshResumeSessions]);

  return {
    resumeRecord,
    sessionId,
    setSessionId,
    rawResumeObj,
    setRawResumeObj,
    normalizedResumeObj,
    setNormalizedResumeObj,
    refinedResumeObj,
    setRefinedResumeObj,
    ragContext,
    setRagContext,
    isBootstrapping,
    needsImport,
    isSaving,
    sessionListLoading,
    resumeSessions,
    messages,
    setMessages,
    inputText,
    setInputText,
    statusText,
    setStatusText,
    errorText,
    setErrorText,
    isRunning,
    setIsRunning,
    isApplying,
    setIsApplying,
    activeSuggestionPath,
    pendingChanges,
    setPendingChanges,
    showChangeToolbar,
    setShowChangeToolbar,
    expandedChangePaths,
    setExpandedChangePaths,
    preTurnSnapshot,
    setPreTurnSnapshot,
    setActiveSuggestionPath,
    dagGraph,
    setDagGraph,
    dagWindowCollapsed,
    setDagWindowCollapsed,
    persistTailorState,
    refreshResumeSessions,
    handleSaveTailoredResume,
    messagesRef,
    rawResumeObjRef,
    normalizedResumeObjRef,
    refinedResumeObjRef,
    inputTextRef,
    statusTextRef,
    errorTextRef,
    isRunningRef,
    isApplyingRef,
    dagGraphRef,
    pendingChangesRef,
    showChangeToolbarRef,
    preTurnSnapshotRef,
    activeSuggestionPathRef,
  };
}
