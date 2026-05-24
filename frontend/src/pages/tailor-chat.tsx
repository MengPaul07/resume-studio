import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Layout, Loader2, MessageCircleQuestion, Send, WandSparkles } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { PageTransition } from '../components/layout/page-transition';
import {
  toolChat,
  toolGetSessionContent,
  toolResumeTurn,
} from '../api';
import { DEFAULT_PREFERENCES } from '../preferences';
import { useTailorSession } from '../hooks/useTailorSession';
import { useTailorDag } from '../hooks/useTailorDag';
import { useInputHistory } from '../hooks/useInputHistory';
import { SessionListPanel } from '../components/tailor/SessionListPanel';
import { ChatBubble } from '../components/tailor/ChatBubble';
import { QuickPrompts } from '../components/tailor/QuickPrompts';
import { TemplatePreview } from '../components/tailor/TemplatePreview';
import { ChangeToolbar } from '../components/tailor/ChangeToolbar';
import { LowConfidenceCard } from '../components/tailor/LowConfidenceCard';
import { AutoApplyDiff } from '../components/tailor/AutoApplyDiff';
import { FactIssuesCard, type FactIssueItem } from '../components/tailor/FactIssuesCard';
import { InterviewModal } from '../components/tailor/InterviewModal';
import { TargetJDPanel } from '../components/tailor/TargetJDPanel';
import { toDisplayText, truncateValue, isPathMatch, setByPathLocal } from '../lib/tailor/utils';
import {
  getSuggestionItemsFromTurn,
  suggestionItemsToPendingChanges,
  buildAssistantReplyText,
} from '../lib/tailor/suggestions';
import {
  extractToolEventsFromSessionContent,
  buildLiveStepsFromEvents,
  buildRunningSteps,
  buildToolChainStepsFromTurn,
  inferPendingChain,
} from '../lib/tailor/thread-steps';
import type {
  ChatMessage,
  NodeThreadStep,
  PendingChange,
  ThreadBubbleUpdate,
  TurnSnapshot,
} from '../lib/tailor/types';

export function TailorChatPage() {
  const { t, i18n } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const resumeId = searchParams.get('resumeId') || '';

  const session = useTailorSession();
  const [targetJd, setTargetJdRaw] = useState<import('../lib/tailor/types').JDMatch | null>(() => {
    try {
      const saved = localStorage.getItem('tailor_target_jd');
      return saved ? JSON.parse(saved) : null;
    } catch { return null; }
  });
  const setTargetJd = (jd: import('../lib/tailor/types').JDMatch | null) => {
    if (jd) localStorage.setItem('tailor_target_jd', JSON.stringify(jd));
    else localStorage.removeItem('tailor_target_jd');
    setTargetJdRaw(jd);
  };
  const [showJdPanel, setShowJdPanel] = useState(false);
  const [showInterview, setShowInterview] = useState(false);
  const mode = showInterview ? 'interview' as const : 'refine' as const;

  const dag = useTailorDag(
    session.sessionId,
    session.refinedResumeObjRef,
    (obj) => session.setRefinedResumeObj(obj),
    () => {
      session.setPendingChanges([]);
      session.setShowChangeToolbar(false);
      session.setExpandedChangePaths(new Set());
      session.setPreTurnSnapshot(null);
      session.setActiveSuggestionPath('');
    },
    (key: string, overrides?: Record<string, unknown>) => session.persistTailorState(key, overrides as any),
    () => session.resumeRecord?.id || resumeId,
  );

  const chatScrollRef = useRef<HTMLDivElement | null>(null);
  const chatAutoScrolledKeyRef = useRef('');
  const previewScrollRef = useRef<HTMLDivElement | null>(null);
  const previewAnchorRefs = useRef<Record<string, HTMLElement | null>>({});
  const threadBubbleSignatureRef = useRef<Record<string, string>>({});

  const [changeVariantIndex, setChangeVariantIndex] = useState<Record<string, number>>({});

  // 鈹€鈹€ Input history 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
  const inputHistory = useInputHistory({
    getInputText: () => session.inputText,
    setInputText: (text: string) => session.setInputText(text),
  });

  // 鈹€鈹€ Fact-issues pause card 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
  const [factIssues, setFactIssues] = useState<{
    items: FactIssueItem[];
    onResolve: ((filledData: Record<string, string>) => void) | null;
  } | null>(null);

  // 鈹€鈹€ Auto-apply state 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
  const [autoApplyEnabled, setAutoApplyEnabled] = useState(true);
  const [autoAppliedDiffs, setAutoAppliedDiffs] = useState<PendingChange[]>([]);

  // 鈹€鈹€ Streaming thinking state 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
  const [thinkingText, setThinkingText] = useState('');

  // 鈹€鈹€ Low-confidence review card 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
  const [lowConfItems, setLowConfItems] = useState<Array<{
    path: string;
    item_key: string;
    confidence: number;
    confidence_reason: string;
    reason: string;
    refined_text: string;
  }> | null>(null);
  const [confirmedLowConfKeys, setConfirmedLowConfKeys] = useState<Set<string>>(new Set());

  // 鈹€鈹€ Vague action suggestions 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
  const [vagueActions, setVagueActions] = useState<Array<{ label: string; text: string; reason: string }> | null>(null);
  const [dynamicGuides, setDynamicGuides] = useState<Array<{ label: string; text: string }>>([]);

  // 鈹€鈹€ Hint from URL (pre-populate input for fresh sessions) 鈹€鈹€鈹€鈹€鈹€

  const hintParam = searchParams.get('hint') || '';

  useEffect(() => {
    if (!hintParam) return;
    if (session.isBootstrapping) return;
    if (!session.sessionId) return;
    if (session.inputText.trim()) return;
    session.setInputText(hintParam);
    const next = new URLSearchParams(searchParams);
    next.delete('hint');
    setSearchParams(next, { replace: true });
  }, [hintParam, session.isBootstrapping, session.sessionId]);

  // 鈹€鈹€ Derived values 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

  const changedPathSet = useMemo(
    () => new Set(session.pendingChanges.map((c) => c.path)),
    [session.pendingChanges],
  );

  const focusedChangePath = session.activeSuggestionPath;

  const activeChange = useMemo(() => {
    if (!focusedChangePath) return null;
    return session.pendingChanges.find((c) => c.path === focusedChangePath) || null;
  }, [focusedChangePath, session.pendingChanges]);

  const visibleMessages = useMemo(() => session.messages, [session.messages]);

  // 鈹€鈹€ Scroll helpers 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

  function scrollChatToBottom(behavior: ScrollBehavior = 'smooth') {
    const raf = window.requestAnimationFrame(() => {
      const container = chatScrollRef.current;
      if (!container) return;
      container.scrollTo({ top: container.scrollHeight, behavior });
    });
    return () => window.cancelAnimationFrame(raf);
  }

  useEffect(() => {
    if (session.isBootstrapping || !resumeId) return;
    if (!session.messages.length) return;
    const autoScrollKey = `${resumeId}:${session.sessionId || 'session'}`;
    if (chatAutoScrolledKeyRef.current === autoScrollKey) return;
    chatAutoScrolledKeyRef.current = autoScrollKey;
    const raf = window.requestAnimationFrame(() => {
      const container = chatScrollRef.current;
      if (!container) return;
      container.scrollTop = container.scrollHeight;
    });
    return () => window.cancelAnimationFrame(raf);
  }, [resumeId, session.sessionId, session.isBootstrapping, session.messages.length]);

  useEffect(() => {
    if (session.isBootstrapping || !resumeId) return;
    if (!session.messages.length) return;
    const last = session.messages[session.messages.length - 1];
    if (!last) return;
    const behavior: ScrollBehavior = last.role === 'user' ? 'smooth' : 'auto';
    return scrollChatToBottom(behavior);
  }, [session.messages, session.isBootstrapping, resumeId]);

  // 鈹€鈹€ Suggestion 鈫?preview scroll 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

  function findChangeForPath(path: string): PendingChange | null {
    if (!path) return null;
    return session.pendingChanges.find((c) => isPathMatch(c.path, path)) || null;
  }

  function getAnchorByPath(path: string): HTMLElement | null {
    if (!path) return null;
    const exact = previewAnchorRefs.current[path];
    if (exact) return exact;
    const matched = Object.entries(previewAnchorRefs.current).find(
      ([key, el]) => Boolean(el) && isPathMatch(key, path),
    );
    return matched?.[1] || null;
  }

  useEffect(() => {
    if (!focusedChangePath) return;
    const target = getAnchorByPath(focusedChangePath);
    if (target) {
      target.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
    const raf1 = window.requestAnimationFrame(() => {
      target?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    });
    return () => window.cancelAnimationFrame(raf1);
  }, [focusedChangePath, session.refinedResumeObj]);

  // 鈹€鈹€ Persist on changes 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

  useEffect(() => {
    if (!session.resumeRecord?.id || session.isBootstrapping || session.needsImport) return;
    session.persistTailorState(session.resumeRecord.id);
  }, [
    session.resumeRecord?.id,
    session.isBootstrapping,
    session.needsImport,
    session.messages,
    session.inputText,
    session.statusText,
    session.errorText,
    session.isRunning,
    session.isApplying,
    session.rawResumeObj,
    session.normalizedResumeObj,
    session.refinedResumeObj,
    session.pendingChanges,
    session.showChangeToolbar,
    session.activeSuggestionPath,
    session.dagGraph,
    session.dagWindowCollapsed,
  ]);

  // 鈹€鈹€ Thread bubble 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

  function upsertChatMessage(message: ChatMessage) {
    session.setMessages((prev) => {
      const idx = prev.findIndex((x) => x.id === message.id);
      if (idx < 0) return [...prev, message];
      const next = [...prev];
      next[idx] = message;
      return next;
    });
  }

  function updateThreadBubble(update: ThreadBubbleUpdate) {
    const existing = session.messagesRef.current.find((msg) => msg.id === update.id);

    // Merge incoming steps with existing steps (preserve full list, no collapse)
    const existingSteps = existing?.threadSteps || [];
    const existingMap = new Map(existingSteps.map((s) => [s.key, s]));

    const mergedSteps: NodeThreadStep[] = update.steps.map((incoming) => {
      const prev = existingMap.get(incoming.key);
      // Preserve thinking from previous step if incoming doesn't have it
      const thinking = incoming.thinking || prev?.thinking || '';
      // If running is done but step still says running, mark it done
      const status = (!update.running && incoming.status === 'running')
        ? ('done' as const)
        : incoming.status;
      return {
        ...incoming,
        status,
        thinking,
        ms: incoming.ms || prev?.ms || 0,
        error: incoming.error || prev?.error || '',
      } as NodeThreadStep;
    });

    // Keep any existing steps not in the update (e.g. from SSE that polling missed)
    for (const prev of existingSteps) {
      if (!mergedSteps.some((s) => s.key === prev.key)) {
        mergedSteps.push({
          ...prev,
          status: (!update.running && prev.status === 'running') ? ('done' as const) : prev.status,
        });
      }
    }

    // Stable sort by step order
    const stepOrder = mergedSteps.map((s) => s.key);

    const signature = JSON.stringify({
      title: update.title,
      running: update.running,
      steps: mergedSteps.map((step) => ({
        key: step.key, label: step.label, status: step.status,
        ms: step.ms || 0, error: step.error || '',
      })),
      thinking: mergedSteps.map((s) => s.thinking || '').join('|'),
    });
    if (threadBubbleSignatureRef.current[update.id] === signature) return;
    threadBubbleSignatureRef.current[update.id] = signature;

    // Preserve message-level thinking (set by 'thinking' SSE event)
    const preservedThinking = existing?.thinking || '';
    upsertChatMessage({
      id: update.id,
      role: 'assistant',
      text: existing?.text || '',
      thinking: preservedThinking,
      timestamp: existing?.timestamp || new Date().toISOString(),
      threadTitle: update.title,
      threadSteps: mergedSteps,
      threadRunning: update.running,
    });
  }

  // 鈹€鈹€ Send handler 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

  async function handleFactIssueResume({
    turnId,
    factIssuesList,
    filledData,
    threadMessageId,
    prompt,
    persistResumeId,
    preSnapshot,
  }: {
    turnId: string;
    factIssuesList: FactIssueItem[];
    filledData: Record<string, string>;
    threadMessageId: string;
    prompt: string;
    persistResumeId: string;
    preSnapshot: TurnSnapshot;
  }) {
    if (!session.sessionId) return;
    setFactIssues(null);
    session.setIsRunning(true);
    session.setStatusText(t('tailor.toolChainRunning'));
    updateThreadBubble({
      id: threadMessageId,
      title: t('tailor.toolChainRunning'),
      steps: [{ key: 'resume-confirmation', label: 'resume after confirmation', status: 'running' }],
      running: true,
    });

    const confirmedLines = factIssuesList.map((item) => {
      const value = (filledData[item.path] || item.suggested_value || '').trim();
      return `- ${item.path}: ${value}`;
    });
    const userResponse = [
      'User confirmed the fact-sensitive changes below.',
      'Continue from the paused tool call, apply only these confirmed values, then compose a natural response.',
      confirmedLines.join('\n'),
    ].join('\n');

    try {
      const turn = (await toolResumeTurn({
        session_id: session.sessionId,
        turn_id: turnId,
        user_response: userResponse,
      })) as any;
      const toolChainSteps = buildToolChainStepsFromTurn(turn);
      updateThreadBubble({
        id: threadMessageId,
        title: t('tailor.toolChainCompleted'),
        steps: toolChainSteps.length
          ? toolChainSteps
          : [{ key: 'resume-confirmation', label: 'resume after confirmation', status: 'done' }],
        running: false,
      });

      const backendRefined = turn.refined_document_obj || turn.refined_resume_obj || {};
      const displayObj = Object.keys(backendRefined).length > 0
        ? JSON.parse(JSON.stringify(backendRefined))
        : JSON.parse(JSON.stringify(session.refinedResumeObjRef.current));
      const rawItems = getSuggestionItemsFromTurn(turn);
      const pendingChanges = suggestionItemsToPendingChanges(rawItems);
      for (const change of pendingChanges) {
        const firstVariant = change.variants[0];
        if (firstVariant) setByPathLocal(displayObj, change.path, firstVariant.suggested_value);
      }

      session.refinedResumeObjRef.current = displayObj;
      session.setRefinedResumeObj(displayObj);
      session.setPendingChanges([]);
      session.setShowChangeToolbar(false);
      setAutoAppliedDiffs(pendingChanges);
      if (pendingChanges.length > 0) {
        await session.handleSaveTailoredResume();
      }

      const assistantText =
        turn.turn_output_bundle?.assistant_message ||
        turn.assistant_message ||
        t('tailor.factIssueApplied', { count: pendingChanges.length });
      const assistantMessage: ChatMessage = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        text: buildAssistantReplyText(prompt, assistantText, []),
        thinking: turn.turn_output_bundle?.thinking || undefined,
        timestamp: new Date().toISOString(),
      };
      session.setMessages((prev) => [...prev, assistantMessage]);
      session.setStatusText(t('tailor.factIssueApplied', { count: pendingChanges.length }));
      session.setInputText('');
      session.persistTailorState(persistResumeId, {
        messages: [...session.messagesRef.current, assistantMessage],
        statusText: t('tailor.factIssueApplied', { count: pendingChanges.length }),
        isRunning: false,
      } as any);
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('tailor.executionFailed');
      session.setErrorText(msg);
      updateThreadBubble({
        id: threadMessageId,
        title: t('tailor.toolChainFailed'),
        steps: [{ key: 'resume-confirmation', label: 'resume after confirmation', status: 'failed', error: truncateValue(msg, 80) }],
        running: false,
      });
      if (preSnapshot.content && Object.keys(preSnapshot.content).length > 0) {
        session.setRefinedResumeObj(JSON.parse(JSON.stringify(preSnapshot.content)));
      }
    } finally {
      session.setIsRunning(false);
    }
  }

  async function handleSendMessage(forcePrompt?: string, forceMode?: string) {
    const prompt = (forcePrompt || session.inputText).trim();
    const currentMode = forceMode || mode;
    if (!prompt || session.isRunning) return;
    if (!session.rawResumeObj || Object.keys(session.rawResumeObj).length === 0) {
      session.setErrorText(t('tailor.noResumeError'));
      return;
    }
    if (!session.sessionId) {
      session.setErrorText(t('tailor.sessionNotReady'));
      return;
    }

    // Dismiss stale change toolbar from previous turn
    if (session.showChangeToolbar) {
      session.setPendingChanges([]);
      session.setShowChangeToolbar(false);
      session.setExpandedChangePaths(new Set());
    }

    session.setErrorText('');
    session.setStatusText(t('tailor.planningChain'));
    session.setIsRunning(true);
    setAutoAppliedDiffs([]);
    setThinkingText('');
    setLowConfItems(null);
    const persistResumeId = session.resumeRecord?.id || resumeId;
    session.persistTailorState(persistResumeId, {
      errorText: '',
      statusText: t('tailor.planningChain'),
      isRunning: true,
    } as any);

    const threadMessageId = `thread-${Date.now()}`;
    const pendingChain = inferPendingChain(prompt);

    updateThreadBubble({
      id: threadMessageId,
      title: t('tailor.toolChainRunning'),
      steps: buildRunningSteps(pendingChain, 0),
      running: true,
    });

    // Snapshot pre-turn state for potential rollback
    const preSnapshot: TurnSnapshot = {
      nodeId: session.dagGraphRef.current?.currentNodeId || dag.dagGraphRef.current?.currentNodeId || '',
      content: JSON.parse(JSON.stringify(session.refinedResumeObjRef.current)),
    };
    session.setPreTurnSnapshot(preSnapshot);

    let progressTimer: number | null = null;
    let pollCancelled = false;
    let baselineEventId = 0;
    let pollInFlight = false;
    try {
      const beforeContent = await toolGetSessionContent({
        session_id: session.sessionId,
        message_limit: 1,
        event_limit: 1,
      });
      const baselineEvents = extractToolEventsFromSessionContent(beforeContent, -1);
      baselineEventId = baselineEvents.length ? baselineEvents[baselineEvents.length - 1].id : 0;
    } catch {
      baselineEventId = 0;
    }

    const pollProgress = async () => {
      if (pollCancelled || pollInFlight) return;
      pollInFlight = true;
      try {
        const content = await toolGetSessionContent({
          session_id: session.sessionId,
          message_limit: 1,
          event_limit: 200,
        });
        if (pollCancelled) return;
        const liveEvents = extractToolEventsFromSessionContent(content, baselineEventId);
        const liveSteps = buildLiveStepsFromEvents(liveEvents, pendingChain);
        if (!liveSteps.length) return;
        const runningLabel = liveSteps.find((step) => step.status === 'running')?.label || 'tool';
        session.setStatusText(`Running: ${runningLabel}`);
        updateThreadBubble({
          id: threadMessageId,
          title: t('tailor.toolChainRunning'),
          steps: liveSteps,
          running: true,
        });
      } catch {
        // ignore polling errors
      } finally {
        pollInFlight = false;
      }
    };
    progressTimer = window.setInterval(() => { void pollProgress(); }, 1000);
    void pollProgress();

    const userMessage: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: prompt,
      timestamp: new Date().toISOString(),
    };
    const pendingMessages = [...session.messagesRef.current, userMessage];
    session.setMessages((prev) => [...prev, userMessage]);
    session.persistTailorState(persistResumeId, {
      messages: pendingMessages,
      isRunning: true,
    } as any);

    try {
      const turn = await toolChat({
        doc_type: 'resume',
        session_id: session.sessionId,
        message: prompt,
        allow_mutation: true,
        layout_preferences: DEFAULT_PREFERENCES,
        target_jd: targetJd?.text || '',
        mode: currentMode,
        onEvent: (eventName, data) => {
          if (
            eventName === 'turn.started' ||
            eventName === 'plan.updated' ||
            eventName === 'plan.step' ||
            eventName === 'step.started' ||
            eventName === 'step.succeeded' ||
            eventName === 'step.failed' ||
            eventName === 'selfcheck.started' ||
            eventName === 'selfcheck.completed' ||
            eventName === 'thinking' ||
            eventName === 'reasoning' ||
            eventName === 'turn.completed'
          ) {
            if (import.meta.env.DEV) console.log('[tailor][sse]', eventName, data);
          }
          if (eventName === 'turn.started') {
            updateThreadBubble({
              id: threadMessageId,
              title: t('tailor.toolChainRunning'),
              running: true,
              steps: [{ key: 'observe_content', label: 'observe_content', status: 'running' }],
            });
            return;
          }
          if (eventName === 'plan.step') {
            const stepId = String(data.step_id || `step-${Date.now()}`);
            const tool = String(data.tool || 'step');
            const reasonBrief = String(data.reason_brief || '').trim();
            const label = reasonBrief ? `${tool} 路 ${reasonBrief}` : tool;
            session.setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id !== threadMessageId) return msg;
                const current = Array.isArray(msg.threadSteps) ? msg.threadSteps : [];
                const next = current.some((step) => step.key === stepId)
                  ? current.map((step) =>
                      step.key === stepId
                        ? { ...step, label, status: step.status === 'done' ? ('done' as const) : ('running' as const) }
                        : step,
                    )
                  : [...current, { key: stepId, label, status: 'running' as const }];
                return { ...msg, threadTitle: t('tailor.toolChainRunning'), threadRunning: true, threadSteps: next };
              }),
            );
            return;
          }
          if (eventName === 'step.started') {
            const stepId = String(data.step_id || `step-${Date.now()}`);
            const tool = String(data.tool || 'step');
            session.setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id !== threadMessageId) return msg;
                const current = Array.isArray(msg.threadSteps) ? msg.threadSteps : [];
                const existing = current.find((step) => step.key === stepId);
                const next = current.some((step) => step.key === stepId)
                  ? current.map((step) =>
                      step.key === stepId
                        ? { ...step, label: existing?.label || tool, status: 'running' as const }
                        : step,
                    )
                  : [...current, { key: stepId, label: tool, status: 'running' as const }];
                return { ...msg, threadTitle: t('tailor.toolChainRunning'), threadRunning: true, threadSteps: next };
              }),
            );
            return;
          }
          if (eventName === 'step.succeeded' || eventName === 'step.failed') {
            const stepId = String(data.step_id || '');
            const tool = String(data.tool || 'step');
            const duration = Number(data.duration_ms || 0);
            const isFailed = eventName === 'step.failed';
            const thinking = typeof data.thinking === 'string' ? data.thinking.trim() : '';
            session.setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id !== threadMessageId) return msg;
                const current = Array.isArray(msg.threadSteps) ? msg.threadSteps : [];
                const next = current.some((step) => step.key === stepId)
                  ? current.map((step) =>
                      step.key === stepId
                        ? { ...step, label: tool || step.label, status: isFailed ? ('failed' as const) : ('done' as const), ms: isFailed ? step.ms : Math.max(1, duration || 1), ...(thinking ? { thinking } : {}) }
                        : step,
                    )
                  : [...current, { key: stepId || tool, label: tool, status: isFailed ? ('failed' as const) : ('done' as const), ms: isFailed ? undefined : Math.max(1, duration || 1), ...(thinking ? { thinking } : {}) }];
                return { ...msg, threadRunning: !isFailed, threadSteps: next };
              }),
            );
            return;
          }
          if (eventName === 'selfcheck.started') {
            session.setStatusText(t('tailor.selfChecking'));
            return;
          }
          if (eventName === 'selfcheck.completed') {
            const result = String((data.self_check_result as { result?: string } | undefined)?.result || '');
            if (result) session.setStatusText(`Self-check: ${result}`);
            return;
          }
          if (eventName === 'tool.executed') {
            const toolName = typeof data.tool_name === 'string' ? data.tool_name : '';
            if (toolName) {
              session.setStatusText(toolName);
              session.setMessages((prev) =>
                prev.map((msg) => {
                  if (msg.id !== threadMessageId) return msg;
                  const currentTools = (msg as any)._tools || [];
                  // Deduplicate 鈥?only add new tool names
                  if (currentTools[currentTools.length - 1] !== toolName) {
                    return { ...msg, _tools: [...currentTools, toolName] };
                  }
                  return msg;
                }),
              );
            }
            return;
          }
          if (eventName === 'thinking' || eventName === 'reasoning') {
            const text = typeof data.text === 'string' ? data.text : '';
            if (text) {
              setThinkingText((prev) => (prev ? prev + '\n' + text : text));
              session.setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === threadMessageId
                    ? { ...msg, thinking: msg.thinking ? `${msg.thinking}\n\n${text}` : text }
                    : msg,
                ),
              );
            }
            return;
          }
          if (eventName === 'turn.composed') {
            pollCancelled = true;
            if (progressTimer !== null) {
              window.clearInterval(progressTimer);
              progressTimer = null;
            }
            session.setMessages((prev) =>
              prev.map((msg) =>
                msg.id === threadMessageId
                  ? { ...msg, threadTitle: t('tailor.toolChainCompleted'), threadRunning: false }
                  : msg,
              ),
            );
          }
        },
      });

      if (import.meta.env.DEV) console.log('[tailor][turn.result]', { turnId: turn.turn_id });

      pollCancelled = true;
      if (progressTimer !== null) window.clearInterval(progressTimer);

      const toolChainSteps = buildToolChainStepsFromTurn(turn);
      let steps: NodeThreadStep[] = toolChainSteps;
      if (!steps.length) {
        const stepByNode = new Map(turn.node_events.map((event) => [event.node_name, event]));
        steps = [
          { key: 'rag', label: 'rag_retrieve' },
          { key: 'refine', label: 'refine' },
          { key: 'suggest', label: 'suggest' },
          { key: 'review', label: 'prepare_review_payload' },
        ].map((template) => {
          const event = stepByNode.get(template.key);
          if (!event) return { key: template.key, label: template.label, status: 'pending' as const };
          if (event.status === 'success') {
            return { key: template.key, label: template.label, status: 'done' as const, ms: Math.max(1, Number(event.duration_ms || 0)) };
          }
          return { key: template.key, label: template.label, status: 'failed' as const, error: truncateValue(event.error || 'failed', 80) };
        });
      }

      updateThreadBubble({ id: threadMessageId, title: t('tailor.toolChainCompleted'), steps, running: false });

      session.setRagContext(turn.rag_context_by_path || {});
      const backendRefined = turn.refined_document_obj || turn.refined_resume_obj || {};
      const displayObj = Object.keys(backendRefined).length > 0
        ? JSON.parse(JSON.stringify(backendRefined))
        : JSON.parse(JSON.stringify(session.refinedResumeObjRef.current));

      const assistantMessageText2 =
        (turn as { turn_output_bundle?: { assistant_message?: string; thinking?: string } }).turn_output_bundle
          ?.assistant_message || turn.assistant_message || '';
      const thinkingText =
        (turn as { turn_output_bundle?: { thinking?: string } }).turn_output_bundle?.thinking || '';
      const guidePrompts =
        (turn as { guide_prompts?: Array<{ label: string; text: string }> }).guide_prompts || [];

      // Update dynamic guides for QuickPrompts
      if (guidePrompts.length > 0) {
        setDynamicGuides(guidePrompts);
      }

      // 鈹€鈹€ Pause for fact issues if present 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
      const factIssuesList: FactIssueItem[] = (Array.isArray(turn.fact_issues) ? turn.fact_issues : [])
        .map((fi: any) => ({
          path: String(fi.path || ''),
          reason: String(fi.reason || ''),
          current_value: String(fi.current_value || ''),
          suggested_value: String(fi.suggested_value || ''),
          op: String(fi.op || 'update'),
          confirmation_hint: String(fi.confirmation_hint || fi.reason || ''),
        }));
      // 鈹€鈹€ Vague action suggestions: show options when intent is edit but 0 tasks 鈹€鈹€
      const vagueActionsList = (turn as { vague_actions?: Array<{ label: string; text: string; reason: string }> }).vague_actions || [];

      // 鈹€鈹€ Low-confidence items review 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
      const lowConfItemsList: Array<{
        path: string; item_key: string; confidence: number;
        confidence_reason: string; reason: string; refined_text: string;
      }> = (Array.isArray((turn as any).low_confidence_items) ? (turn as any).low_confidence_items : [])
        .map((li: any) => ({
          path: String(li.path || ''),
          item_key: String(li.item_key || ''),
          confidence: Number(li.confidence ?? 0.5),
          confidence_reason: String(li.confidence_reason || ''),
          reason: String(li.reason || ''),
          refined_text: String(li.refined_text || ''),
        }));

      if (lowConfItemsList.length > 0 && factIssuesList.length === 0) {
        setLowConfItems(lowConfItemsList);
        setConfirmedLowConfKeys(new Set());
      }

      if (factIssuesList.length > 0) {
        updateThreadBubble({ id: threadMessageId, title: t('tailor.toolChainPaused'), steps, running: false });
        const assistantMsg: ChatMessage = {
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: assistantMessageText2 || t('tailor.needConfirmFact'),
          timestamp: new Date().toISOString(),
        };
        const pausedMessages = [...session.messagesRef.current, assistantMsg];
        session.setMessages(pausedMessages);
        session.setIsRunning(false);
        session.setStatusText(t('tailor.waitingForInput'));
        session.persistTailorState(persistResumeId, {
          messages: pausedMessages,
          statusText: t('tailor.waitingForInput'),
          isRunning: false,
        } as any);

        return new Promise<void>((resolve) => {
          setFactIssues({
            items: factIssuesList,
            onResolve: (filledData: Record<string, string>) => {
              void handleFactIssueResume({
                turnId: String((turn as { turn_id?: string }).turn_id || ''),
                factIssuesList,
                filledData,
                threadMessageId,
                prompt,
                persistResumeId,
                preSnapshot,
              }).finally(resolve);
            },
          });
        });
      }

      // 鈹€鈹€ Show vague action suggestions if present 鈹€鈹€
      if (vagueActionsList.length > 0) {
        setVagueActions(vagueActionsList);
      } else {
        setVagueActions(null);
      }

      // Auto-apply all apply-ready suggestions client-side to the preview (first variant)
      const rawItems = getSuggestionItemsFromTurn(turn);
      const pendingChanges = suggestionItemsToPendingChanges(rawItems);
      for (const change of pendingChanges) {
        const firstVariant = change.variants[0];
        if (firstVariant) {
          setByPathLocal(displayObj, change.path, firstVariant.suggested_value);
        }
      }

      session.setRefinedResumeObj(displayObj);
      session.setPendingChanges(pendingChanges);

      // 鈹€鈹€ Auto-apply high-confidence items 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
      let autoAppliedCount = 0;
      if (autoApplyEnabled && pendingChanges.length > 0) {
        const autoItems = pendingChanges.filter((c) => !c.lowConfidence);
        const reviewItems = pendingChanges.filter((c) => c.lowConfidence);
        if (autoItems.length > 0) {
          autoAppliedCount = autoItems.length;
          setAutoAppliedDiffs(autoItems);
          session.setPendingChanges(reviewItems);
          // Snapshot pre-save state in case persistence fails
          const preSaveContent = preSnapshot?.content
            ? JSON.parse(JSON.stringify(preSnapshot.content))
            : null;
          // Sync ref synchronously before save (useEffect hasn't fired yet)
          session.refinedResumeObjRef.current = displayObj;
          // Persist auto-applied changes to backend
          try {
            await session.handleSaveTailoredResume();
          } catch (saveErr) {
            // Revert in-memory state to pre-turn snapshot so UI matches backend
            autoAppliedCount = 0;
            setAutoAppliedDiffs([]);
            session.setPendingChanges(pendingChanges);
            if (preSaveContent && Object.keys(preSaveContent).length > 0) {
              session.setRefinedResumeObj(preSaveContent);
              session.refinedResumeObjRef.current = preSaveContent;
            }
            const errMsg = saveErr instanceof Error ? saveErr.message : t('tailor.saveFailed');
            session.setErrorText(`Auto-save failed: ${errMsg}. Changes shown in preview may be out of sync.`);
            session.setStatusText(t('tailor.autoSaveFailed'));
          }
        }
        session.setShowChangeToolbar(reviewItems.length > 0);
        session.setActiveSuggestionPath(reviewItems[0]?.path || autoItems[0]?.path || '');
      } else {
        session.setShowChangeToolbar(pendingChanges.length > 0);
        session.setActiveSuggestionPath(pendingChanges[0]?.path || '');
      }
      setChangeVariantIndex({});

      const assistantMessageText =
        (turn as { turn_output_bundle?: { assistant_message?: string } }).turn_output_bundle
          ?.assistant_message || turn.assistant_message || '';
      const remainingChanges = session.pendingChanges;
      const replyText = buildAssistantReplyText(
        prompt,
        assistantMessageText || (
          autoAppliedCount > 0
            ? `Applied ${autoAppliedCount} change${autoAppliedCount === 1 ? '' : 's'} automatically${remainingChanges.length > 0 ? `, ${remainingChanges.length} pending review` : ''}.`
            : t('tailor.changesApplied', { count: pendingChanges.length })
        ),
        remainingChanges,
      );
      const jdMatches = (
        (turn as { turn_output_bundle?: { jd_matches?: ChatMessage['jdMatches'] } }).turn_output_bundle
          ?.jd_matches
      ) || undefined;
      const assistantMessage: ChatMessage = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        text: replyText,
        thinking: thinkingText || undefined,
        jdMatches,
        timestamp: new Date().toISOString(),
      };
      const successMessages = [
        ...session.messagesRef.current.map((msg) =>
          Array.isArray(msg.applySuggestionItems) && msg.applySuggestionItems.length > 0
            ? { ...msg, applySuggestionItems: undefined }
            : msg,
        ),
        assistantMessage,
      ];
      session.setMessages(successMessages);
      updateThreadBubble({
        id: threadMessageId,
        title: t('tailor.toolChainCompleted'),
        steps,
        running: false,
      });
      const doneLabel =
        Array.isArray(turn.selected_tool_chain) && turn.selected_tool_chain.length
          ? `Done: ${turn.selected_tool_chain.join(' -> ')}`
          : t('tailor.doneLabel', { count: pendingChanges.length });
      const policySuffix = turn.execution_policy ? ` [${turn.execution_policy}]` : '';
      session.setStatusText(`${doneLabel}${policySuffix}`);
      session.setInputText('');
      inputHistory.addToHistory(prompt);
      session.persistTailorState(persistResumeId, {
        messages: successMessages,
        statusText: `${doneLabel}${policySuffix}`,
        inputText: '',
        refinedResumeObj: displayObj,
        pendingChanges,
        showChangeToolbar: pendingChanges.length > 0,
        activeSuggestionPath: pendingChanges[0]?.path || '',
        isRunning: false,
      } as any);
    } catch (err) {
      pollCancelled = true;
      if (progressTimer !== null) window.clearInterval(progressTimer);
      const msg = err instanceof Error ? err.message : t('tailor.executionFailed');
      updateThreadBubble({
        id: threadMessageId,
        title: t('tailor.toolChainFailed'),
        steps: [{ key: 'session_turn_failed', label: 'session_turn', status: 'failed', error: truncateValue(msg, 80) }],
        running: false,
      });
      session.setErrorText(msg);
      const errorMessage: ChatMessage = {
        id: `a-err-${Date.now()}`,
        role: 'assistant',
        text: t('tailor.executionFailedMsg', { error: msg }),
        timestamp: new Date().toISOString(),
      };
      const failedMessages = [...session.messagesRef.current, errorMessage];
      session.setMessages((prev) => [...prev, errorMessage]);
      session.setStatusText(t('tailor.executionFailed'));
      session.persistTailorState(persistResumeId, {
        messages: failedMessages,
        errorText: msg,
        statusText: t('tailor.executionFailed'),
        isRunning: false,
      } as any);
    } finally {
      if (progressTimer !== null) window.clearInterval(progressTimer);
      session.setIsRunning(false);
      session.persistTailorState(persistResumeId, { isRunning: false } as any);
    }
  }

  // 鈹€鈹€ Change toolbar handlers 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

  function handleToggleChangeDetail(path: string) {
    session.setExpandedChangePaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }

  function handleSwitchVariant(path: string, variantIdx: number) {
    setChangeVariantIndex((prev) => ({ ...prev, [path]: variantIdx }));
    const change = session.pendingChanges.find((c) => c.path === path);
    if (!change) return;
    const variant = change.variants[variantIdx];
    if (!variant) return;
    const next = JSON.parse(JSON.stringify(session.refinedResumeObjRef.current));
    setByPathLocal(next, path, variant.suggested_value);
    session.setRefinedResumeObj(next);
  }

  function handleInlineEdit(path: string, newValue: string) {
    const next = JSON.parse(JSON.stringify(session.refinedResumeObj));
    setByPathLocal(next, path, newValue);
    session.setRefinedResumeObj(next);
  }

  async function handleKeepChanges() {
    const persistResumeId = session.resumeRecord?.id || resumeId;
    session.setPendingChanges([]);
    session.setShowChangeToolbar(false);
    session.setExpandedChangePaths(new Set());
    session.setPreTurnSnapshot(null);
    setChangeVariantIndex({});
    session.setStatusText(t('common.saving'));
    session.persistTailorState(persistResumeId, {
      pendingChanges: [],
      showChangeToolbar: false,
      statusText: t('common.saving'),
    } as any);

    // Persist to backend so changes survive refresh
    try {
      await session.handleSaveTailoredResume();
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('tailor.saveFailed');
      session.setErrorText(msg);
      session.setStatusText(t('tailor.saveFailed'));
      session.persistTailorState(persistResumeId, {
        errorText: msg,
        statusText: t('tailor.saveFailed'),
        pendingChanges: [],
        showChangeToolbar: false,
      } as any);
      return;
    }

    session.setStatusText(t('tailor.changesSaved'));
    session.persistTailorState(persistResumeId, {
      pendingChanges: [],
      showChangeToolbar: false,
      statusText: t('tailor.changesSaved'),
    } as any);
  }

  async function handleUndoChanges() {
    const snapshot = session.preTurnSnapshot;
    if (!snapshot || !snapshot.nodeId) return;
    const targetNodeId = snapshot.nodeId;

    session.setIsApplying(true);
    session.setStatusText(t('tailor.reverting'));
    const persistResumeId = session.resumeRecord?.id || resumeId;
    session.persistTailorState(persistResumeId, { isApplying: true, statusText: t('tailor.reverting') } as any);

    try {
      await dag.handleRollbackToDagNode(targetNodeId);
      session.setPendingChanges([]);
      session.setShowChangeToolbar(false);
      session.setExpandedChangePaths(new Set());
      session.setPreTurnSnapshot(null);
      setChangeVariantIndex({});
      session.setStatusText(t('tailor.reverted'));
      session.persistTailorState(persistResumeId, {
        pendingChanges: [],
        showChangeToolbar: false,
        statusText: t('tailor.reverted'),
        isApplying: false,
      } as any);
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('tailor.undoFailed');
      session.setErrorText(msg);
      session.setStatusText(t('tailor.undoFailed'));
      session.persistTailorState(persistResumeId, { errorText: msg, statusText: t('tailor.undoFailed'), isApplying: false } as any);
    } finally {
      session.setIsApplying(false);
    }
  }


  // 鈹€鈹€ Input keyboard handler 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

  function handleInputKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSendMessage();
      return;
    }
    inputHistory.handleInputKeyDown(e);
  }

  function handleInputChange(text: string) {
    inputHistory.handleInputChange(text);
  }

  // 鈹€鈹€ Render 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

  return (
    <>
    <PageTransition>
      <section className="px-4 py-10 md:px-8">
        <div className="mx-auto w-full max-w-[86rem] space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 border border-black dark:border-zinc-600 bg-canvas px-3 py-2 font-mono text-xs uppercase"
            >
              <ArrowLeft className="size-4" />
              {t('nav.back')}
            </Link>
            <div className="flex items-center gap-3">
              <Button
                size="sm"
                variant="outline"
                onClick={session.handleSaveTailoredResume}
                disabled={
                  session.isSaving ||
                  session.isBootstrapping ||
                  !session.resumeRecord ||
                  Object.keys(session.refinedResumeObj).length === 0
                }
              >
              {session.isSaving ? <Loader2 className="animate-spin" /> : <WandSparkles />}
                {session.isSaving ? t('common.saving') : t('tailor.saveTailor')}
              </Button>
              <Link
                to={`/builder?resumeId=${resumeId}`}
                className="inline-flex items-center gap-1.5 rounded border border-black dark:border-zinc-600 bg-white dark:bg-[var(--brand-surface)] dark:text-zinc-200 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wide hover:bg-gray-50 dark:hover:bg-[var(--brand-surface-soft)]"
              >
                <Layout className="size-3.5" />
                {t('tailor.layout')}
              </Link>
              <div className="border border-black dark:border-zinc-600 bg-canvas px-2 py-1 font-mono text-xs uppercase">
                resume
              </div>
              <div className="font-mono text-xs uppercase text-gray-700 dark:text-zinc-300">
                {session.resumeRecord
                  ? t('tailor.resumeLabel', { title: session.resumeRecord.title })
                  : t('tailor.noResumeLoaded')}
              </div>
            </div>
          </div>

          {/* Session List */}
          <SessionListPanel
            sessions={session.resumeSessions}
            activeResumeId={resumeId}
            onSelectSession={(newId) => {
              const next = new URLSearchParams(searchParams);
              next.set('resumeId', newId);
              setSearchParams(next);
            }}
            loading={session.sessionListLoading}
            onRefresh={() => session.refreshResumeSessions(undefined, true)}
          />

          {/* Needs Import Banner */}
          {session.needsImport ? (
            <div className="flex items-center justify-between rounded-xl border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950 px-4 py-3">
              <p className="font-mono text-xs text-amber-900 dark:text-amber-400">
                No resume is available yet. Please import or create one from the dashboard.
              </p>
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-2 border border-black dark:border-zinc-600 bg-white dark:bg-[var(--brand-surface)] px-3 py-1 font-mono text-xs uppercase"
              >
                {t('tailor.goImport')}</Link>
            </div>
          ) : null}

          {/* Main Grid */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1.25fr] xl:h-[calc(100vh-8rem)]">
            {/* Chat Panel */}
            <div className="flex flex-col overflow-hidden border-2 border-black dark:border-zinc-600 bg-white dark:bg-[var(--brand-surface)] shadow-[6px_6px_0px_0px_#000000] dark:shadow-none dark:border dark:border-[var(--brand-line)]">
              <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b-2 border-black bg-[var(--brand-surface-soft)] px-4 py-3 dark:border-zinc-600">
                <h1 className="font-serif text-2xl uppercase">{t('tailor.chatTitle')}</h1>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    className="inline-flex items-center gap-2 rounded-full border-2 border-black bg-[var(--brand-signal)] px-4 py-2 font-mono text-[11px] font-bold uppercase tracking-wide text-white shadow-[3px_3px_0px_0px_#000000] transition-all hover:-translate-y-0.5 hover:brightness-110 hover:shadow-[5px_5px_0px_0px_#000000] active:translate-y-0 active:shadow-[2px_2px_0px_0px_#000000] dark:border-zinc-200 dark:bg-zinc-100 dark:text-zinc-950 dark:shadow-none dark:ring-2 dark:ring-zinc-100/20"
                    onClick={() => setShowInterview(true)}
                  >
                    <MessageCircleQuestion className="size-4" />
                    {t('tailor.mockInterview')}
                  </button>
                  <button
                    className="rounded border border-blue-400 dark:border-blue-600 bg-blue-50 dark:bg-blue-950 px-2.5 py-1 text-[11px] text-blue-700 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900"
                    onClick={() => setShowJdPanel(!showJdPanel)}
                  >
                    {showJdPanel ? t('tailor.hideJd') : t('tailor.viewJd')}
                  </button>
                  {targetJd && (
                    <button
                      className="rounded border border-black/20 dark:border-zinc-600/20 px-2.5 py-1 text-[11px] text-gray-500 dark:text-[var(--brand-ink-muted)] hover:bg-gray-100 dark:hover:bg-[var(--brand-surface-soft)]"
                      onClick={() => setTargetJd(null)}
                    >
                      {t('tailor.clearJd')}
                    </button>
                  )}

                </div>
              </div>

              {showJdPanel && (
                <TargetJDPanel
                  targetJd={targetJd || { text: '' }}
                  onUpdate={(jd) => setTargetJd(jd as any)}
                  onClear={() => { setTargetJd(null); setShowJdPanel(false); }}
                />
              )}

              <div ref={chatScrollRef} className="flex-1 min-h-0 space-y-3 overflow-auto p-4">
                {visibleMessages.map((msg) => (
                  <ChatBubble
                    key={msg.id}
                    message={msg}
                    thinkingText={msg.threadRunning ? thinkingText : msg.thinking}
                    onTargetJd={(jd) => setTargetJd(jd)}
                  />
                ))}
              </div>

              {/* 鈹€鈹€ Fact Issues Pause Card 鈹€鈹€ */}
              {factIssues && (
                <FactIssuesCard
                  items={factIssues.items}
                  onSkip={() => {
                    const cb = factIssues.onResolve;
                    setFactIssues(null);
                    cb?.({});
                  }}
                  onSubmit={(filledData: Record<string, string>) => {
                    const cb = factIssues.onResolve;
                    setFactIssues(null);
                    cb?.(filledData);
                  }}
                />
              )}

              {/* 鈹€鈹€ Auto-Applied Diff 鈹€鈹€ */}
              {autoAppliedDiffs.length > 0 && !factIssues && (
                <AutoApplyDiff changes={autoAppliedDiffs} />
              )}

              {/* 鈹€鈹€ Low Confidence Review Card 鈹€鈹€ */}
              {lowConfItems && lowConfItems.length > 0 && !factIssues && (
                <LowConfidenceCard
                  items={lowConfItems}
                  confirmedKeys={confirmedLowConfKeys}
                  onToggleConfirm={(itemKey: string) => {
                    setConfirmedLowConfKeys((prev) => {
                      const next = new Set(prev);
                      if (next.has(itemKey)) next.delete(itemKey);
                      else next.add(itemKey);
                      return next;
                    });
                  }}
                  onDismiss={() => {
                    setLowConfItems(null);
                  }}
                />
              )}

              {/* Vague action suggestions 鈥?shown when intent is edit but 0 tasks */}
              {vagueActions && vagueActions.length > 0 && (
                <div className="mx-3 mb-2 space-y-2 border-2 border-blue-400 dark:border-blue-600 bg-blue-50 dark:bg-blue-950 p-3 shadow-[3px_3px_0px_0px_#3b82f6] dark:shadow-none dark:border dark:border-[var(--brand-line)]">
                  <p className="font-sans text-[11px] font-semibold text-blue-800 dark:text-blue-400">
                    {t('tailor.vagueActionsHint')}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {vagueActions.map((action, i) => (
                      <button
                        key={i}
                        type="button"
                        disabled={session.isRunning}
                        onClick={() => {
                          session.setInputText(action.text);
                          setVagueActions(null);
                          const ta = document.querySelector<HTMLTextAreaElement>('.chat-input-area');
                          ta?.focus();
                        }}
                        title={action.reason}
                        className="inline-flex items-center gap-1 rounded-full border border-blue-300 dark:border-blue-700 bg-white dark:bg-[var(--brand-surface)] px-3 py-1 text-[11px] text-blue-700 dark:text-blue-400 transition-colors hover:border-blue-500 dark:hover:border-blue-500 hover:bg-blue-100 dark:hover:bg-blue-900 hover:text-blue-900 dark:hover:text-blue-300 disabled:pointer-events-none disabled:opacity-40"
                      >
                        {action.label}
                      </button>
                    ))}
                    <button
                      type="button"
                      disabled={session.isRunning}
                      onClick={() => setVagueActions(null)}
                      className="inline-flex items-center rounded-full border border-blue-200 dark:border-blue-700 bg-transparent px-2.5 py-1 text-[10px] text-blue-400 dark:text-blue-400 hover:text-blue-600 dark:hover:text-blue-300"
                    >
                      {t('tailor.vagueActionsClose')}
                    </button>
                  </div>
                </div>
              )}

              {/* Dynamic quick prompts */}
                <QuickPrompts
                  resumeObj={session.refinedResumeObj}
                  dynamicPrompts={dynamicGuides}
                  language={i18n.language}
                  onSelect={(text) => {
                    session.setInputText(text);
                    const ta = document.querySelector<HTMLTextAreaElement>('.chat-input-area');
                    ta?.focus();
                  }}
                  disabled={session.isRunning}
                />

                <div className="space-y-2 border-t-2 border-black dark:border-zinc-600 p-4">
                  <Textarea
                    value={session.inputText}
                    onChange={(e) => handleInputChange(e.target.value)}
                    onKeyDown={handleInputKeyDown}
                    placeholder={t('tailor.inputPlaceholder')}
                    className="chat-input-area min-h-[100px]"
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      onClick={() => handleSendMessage()}
                      disabled={
                        session.isRunning ||
                        session.isBootstrapping ||
                        session.needsImport ||
                        !session.inputText.trim()
                      }
                    >
                      {session.isRunning ? <Loader2 className="animate-spin" /> : <Send />}
                      {session.isRunning ? t('common.running') : t('common.send')}
                    </Button>
                    <button
                      type="button"
                      onClick={() => setAutoApplyEnabled((v) => !v)}
                      className={`inline-flex items-center gap-1.5 rounded border-2 px-2.5 py-1.5 text-[11px] font-bold transition-colors ${
                        autoApplyEnabled
                          ? 'border-green-600 dark:border-green-500 bg-green-100 dark:bg-green-950 text-green-800 dark:text-green-400'
                          : 'border-gray-300 dark:border-zinc-600 bg-white dark:bg-[var(--brand-surface)] text-gray-500 dark:text-[var(--brand-ink-muted)]'
                      }`}
                      title={autoApplyEnabled ? t('tailor.autoApplyTitle') : t('tailor.manualConfirmTitle')}
                    >
                      <span className={`size-2 rounded-full ${autoApplyEnabled ? 'bg-green-600 dark:bg-green-400' : 'bg-gray-400 dark:bg-zinc-500'}`} />
                      {autoApplyEnabled ? t('tailor.autoApply') : t('tailor.manual')}
                    </button>
                    <span className="ml-auto font-mono text-[10px] text-slate-400 dark:text-zinc-400">
                      {session.inputText.length}/2000
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      {session.statusText ? (
                        <p className="font-mono text-xs text-green-700 dark:text-green-400">{session.statusText}</p>
                      ) : null}
                      {session.errorText ? (
                        <p className="font-mono text-xs text-red-700 dark:text-red-400">{session.errorText}</p>
                      ) : null}
                    </div>
                    <p className="font-mono text-[10px] text-slate-300 dark:text-zinc-500">
                      {t('tailor.keyboardHint')}
                    </p>
                  </div>
                </div>
            </div>

            {/* Preview Panel */}
            <div className="flex flex-col overflow-hidden rounded-2xl bg-[#f5f5f7] dark:bg-[var(--brand-surface-soft)] shadow-[0_4px_24px_rgba(0,0,0,0.04)] dark:shadow-none dark:border dark:border-[var(--brand-line)]">
              <div className="shrink-0 border-b border-gray-200 dark:border-[var(--brand-line)] bg-white/80 dark:bg-[var(--brand-surface)]/80 backdrop-blur px-5 py-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="font-sans text-lg font-semibold tracking-tight text-gray-900 dark:text-[var(--brand-ink)]"
                    style={{ fontFamily: "'Inter', 'SF Pro Display', system-ui, sans-serif" }}>
                    {t('tailor.resumePreview')}
                  </h2>
                </div>
                <p className="mt-1.5 font-sans text-xs text-gray-400 dark:text-zinc-500"
                  style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>
                  {activeChange
                    ? `${activeChange.section || 'section'} / ${activeChange.path}`
                    : session.pendingChanges.length
                      ? `${session.pendingChanges.length} change${session.pendingChanges.length !== 1 ? 's' : ''} highlighted`
                      : t('tailor.clickToEdit')}
                </p>
              </div>

              <div ref={previewScrollRef}
                className="relative flex-1 min-h-0 overflow-auto bg-[#f5f5f7] dark:bg-[var(--brand-surface-soft)] p-6 lg:p-8"
              >
                {Object.keys(session.refinedResumeObj).length === 0 ? (
                  <div className="mx-auto w-full min-h-[400px] max-w-[820px] rounded-2xl bg-white dark:bg-[var(--brand-surface)] px-10 py-20 shadow-sm dark:shadow-none dark:border dark:border-[var(--brand-line)] flex items-center justify-center">
                    <p className="font-sans text-sm text-gray-400 dark:text-zinc-500">{t('tailor.emptyPreview')}</p>
                  </div>
                ) : (
                  <TemplatePreview
                    refinedResumeObj={session.refinedResumeObj}
                    pendingChanges={session.pendingChanges}
                    changedPathSet={changedPathSet}
                    focusedChangePath={focusedChangePath}
                    expandedChangePaths={session.expandedChangePaths}
                    changeVariantIndex={changeVariantIndex}
                    onToggleChangeDetail={handleToggleChangeDetail}
                    onSwitchVariant={handleSwitchVariant}
                    onFocusPath={session.setActiveSuggestionPath}
                    onEditField={handleInlineEdit}
                    previewAnchorRefs={previewAnchorRefs}
                  />
                )}
                {session.showChangeToolbar && session.pendingChanges.length > 0 ? (
                  <ChangeToolbar
                    changeCount={session.pendingChanges.length}
                    isExpanded={session.expandedChangePaths.size > 0}
                    onKeep={() => void handleKeepChanges()}
                    onUndo={handleUndoChanges}
                    onToggleDetails={() => {
                      if (session.expandedChangePaths.size > 0) {
                        session.setExpandedChangePaths(new Set());
                      } else {
                        session.setExpandedChangePaths(
                          new Set(session.pendingChanges.map((c) => c.path)),
                        );
                      }
                    }}
                    disabled={session.isApplying}
                  />
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </section>
    </PageTransition>

    {showInterview && (
      <InterviewModal
        resumeObj={session.refinedResumeObj}
        resumeId={resumeId}
        targetJd={targetJd?.text}
        onClose={() => setShowInterview(false)}
      />
    )}
    </>
  );
}

