import type { ToolEventLite, NodeThreadStep } from './types';
import { TOOL_LABELS } from './constants';
import { truncateValue } from './utils';

export function extractToolEventsFromSessionContent(
  content: Record<string, unknown>,
  baselineEventId: number,
): ToolEventLite[] {
  const rawEvents = Array.isArray(content.node_events) ? content.node_events : [];
  const out: ToolEventLite[] = [];
  rawEvents.forEach((eventLike) => {
    if (!eventLike || typeof eventLike !== 'object') return;
    const event = eventLike as Record<string, unknown>;
    const id = Number(event.id || 0);
    const nodeName = String(event.node_name || '');
    if (!Number.isFinite(id) || id <= baselineEventId || !nodeName.startsWith('tool:')) return;
    const tool = nodeName.slice(5).trim();
    if (!tool) return;
    out.push({
      id,
      tool,
      status: String(event.status || ''),
      durationMs: Math.max(0, Number(event.duration_ms || 0)),
      error: String(event.error || ''),
    });
  });
  out.sort((a, b) => a.id - b.id);
  return out;
}

export function buildLiveStepsFromEvents(
  events: ToolEventLite[],
  chainHint: string[],
): NodeThreadStep[] {
  const orderedTools: string[] = [];
  const seenTool = new Set<string>();
  chainHint.forEach((tool) => {
    const name = String(tool || '').trim();
    if (!name || seenTool.has(name)) return;
    seenTool.add(name);
    orderedTools.push(name);
  });
  events.forEach((event) => {
    if (seenTool.has(event.tool)) return;
    seenTool.add(event.tool);
    orderedTools.push(event.tool);
  });
  if (!orderedTools.length) return [];

  const latestByTool = new Map<string, ToolEventLite>();
  events.forEach((event) => latestByTool.set(event.tool, event));

  const steps: NodeThreadStep[] = orderedTools.map((tool, index) => {
    const latest = latestByTool.get(tool);
    if (!latest) {
      return {
        key: `${index}-${tool}`,
        label: TOOL_LABELS[tool] || tool,
        status: 'pending',
      };
    }
    const status = String(latest.status || '').toLowerCase();
    if (status === 'success' || status === 'completed' || status === 'done') {
      return {
        key: `${index}-${tool}`,
        label: TOOL_LABELS[tool] || tool,
        status: 'done',
        ms: Math.max(1, Number(latest.durationMs || 0)),
      };
    }
    if (status === 'failed' || status === 'error' || status === 'cancelled') {
      return {
        key: `${index}-${tool}`,
        label: TOOL_LABELS[tool] || tool,
        status: 'failed',
        error: truncateValue(latest.error || 'failed', 80),
      };
    }
    return {
      key: `${index}-${tool}`,
      label: TOOL_LABELS[tool] || tool,
      status: 'running',
    };
  });

  if (!steps.some((step) => step.status === 'running')) {
    const nextPending = steps.findIndex((step) => step.status === 'pending');
    if (nextPending >= 0) {
      steps[nextPending] = { ...steps[nextPending], status: 'running' };
    }
  }
  return steps;
}

export function buildRunningSteps(chain: string[], runningIndex: number): NodeThreadStep[] {
  return chain.map((tool, index) => {
    if (index < runningIndex) {
      return {
        key: `${index}-${tool}`,
        label: TOOL_LABELS[tool] || tool,
        status: 'done',
      };
    }
    if (index === runningIndex) {
      return {
        key: `${index}-${tool}`,
        label: TOOL_LABELS[tool] || tool,
        status: 'running',
      };
    }
    return {
      key: `${index}-${tool}`,
      label: TOOL_LABELS[tool] || tool,
      status: 'pending',
    };
  });
}

export function buildToolChainStepsFromTurn(
  turn: {
    selected_steps?: Array<{
      step_id?: string;
      tool?: string;
      status?: string;
      duration_ms?: number;
      reason_brief?: string;
    }>;
    selected_tool_chain?: string[];
    node_events?: Array<{
      node_name?: string;
      status?: string;
      duration_ms?: number;
      error?: string;
    }>;
  },
): NodeThreadStep[] {
  const selectedSteps = Array.isArray(turn.selected_steps) ? turn.selected_steps : [];

  if (selectedSteps.length) {
    return selectedSteps.map((step, index) => {
      const stepId = String(step.step_id || `${index}-${String(step.tool || 'step')}`);
      const tool = String(step.tool || 'step');
      const reason = String(step.reason_brief || '').trim();
      const label = reason
        ? `${TOOL_LABELS[tool] || tool} · ${reason}`
        : TOOL_LABELS[tool] || tool;
      const statusRaw = String(step.status || '').toLowerCase();
      if (statusRaw === 'success' || statusRaw === 'completed' || statusRaw === 'done') {
        return {
          key: stepId,
          label,
          status: 'done' as const,
          ms: Math.max(1, Number(step.duration_ms || 0)),
        };
      }
      if (statusRaw === 'failed' || statusRaw === 'error') {
        return { key: stepId, label, status: 'failed' as const };
      }
      return { key: stepId, label, status: 'running' as const };
    });
  }

  const selectedChain = Array.isArray(turn.selected_tool_chain) ? turn.selected_tool_chain : [];
  const toolEvents = (turn.node_events || []).filter((event) =>
    String(event.node_name || '').startsWith('tool:'),
  );
  if (!selectedChain.length || !toolEvents.length) {
    return [];
  }

  return selectedChain.map((tool, index) => {
    const event = toolEvents.find((item) => item.node_name === `tool:${tool}`);
    if (!event) {
      return { key: `${index}-${tool}`, label: TOOL_LABELS[tool] || tool, status: 'pending' };
    }
    if (event.status === 'success') {
      return {
        key: `${index}-${tool}`,
        label: TOOL_LABELS[tool] || tool,
        status: 'done',
        ms: Math.max(1, Number(event.duration_ms || 0)),
      };
    }
    return {
      key: `${index}-${tool}`,
      label: TOOL_LABELS[tool] || tool,
      status: 'failed',
      error: truncateValue(event.error || 'failed', 80),
    };
  });
}

export function inferPendingChain(prompt: string): string[] {
  const text = (prompt || '').toLowerCase();
  const looksLikeAnalyzeOnly =
    /(analy|review|assess|explain|点评|分析|评估|解释)/.test(text) &&
    /(don't modify|do not modify|不修改|别修改|不要修改)/.test(text);
  if (looksLikeAnalyzeOnly) {
    return ['observe_content', 'compose_unified_output', 'self_check_turn'];
  }
  void text;
  return [
    'observe_content',
    'propose_suggest',
    'propose_refine',
    'compose_unified_output',
    'self_check_turn',
  ];
}
