import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { toolRollbackVersion } from '../api';
import { createDagNode, toJsonObject, hashContent } from '../lib/tailor/utils';
import type {
  DagPendingAction,
  ResumeDagEdge,
  ResumeDagGraph,
  ResumeDagNode,
} from '../lib/tailor/types';

export interface UseTailorDagReturn {
  dagGraph: ResumeDagGraph;
  dagWindowCollapsed: boolean;
  selectedDagNodeId: string;
  dagLayout: { positions: Record<string, { x: number; y: number }>; width: number; height: number };
  selectedDagNode: ResumeDagNode | null;
  dagGraphRef: React.MutableRefObject<ResumeDagGraph>;
  commitDag: (next: ResumeDagGraph) => void;
  ensureCurrentDagNode: (baseContent: Record<string, unknown>) => ResumeDagNode;
  startDagAction: (actionType: ResumeDagEdge['actionType'], note?: string) => DagPendingAction;
  finishDagAction: (
    pending: DagPendingAction,
    params: {
      actionType: ResumeDagEdge['actionType'];
      status: 'success' | 'failed';
      nextState?: ResumeDagNode['state'];
      nextContent?: Record<string, unknown>;
      note?: string;
    },
  ) => void;
  handleRollbackToDagNode: (nodeId: string) => Promise<void>;
}

export function useTailorDag(
  sessionId: string,
  contentRef: React.MutableRefObject<Record<string, unknown>>,
  onRefinedChange: (obj: Record<string, unknown>) => void,
  onSuggestionClear: () => void,
  persistTailorState: (resumeKey: string, overrides?: Record<string, unknown>) => void,
  getResumeId: () => string,
): UseTailorDagReturn {
  const [dagGraph, setDagGraph] = useState<ResumeDagGraph>({
    nodes: [],
    edges: [],
    currentNodeId: '',
  });
  const dagGraphRef = useRef(dagGraph);
  useEffect(() => { dagGraphRef.current = dagGraph; }, [dagGraph]);

  const [selectedDagNodeId, setSelectedDagNodeId] = useState('');

  // Auto-select when DAG changes
  useEffect(() => {
    if (!dagGraph.nodes.length) {
      setSelectedDagNodeId('');
      return;
    }
    if (selectedDagNodeId && dagGraph.nodes.some((node) => node.id === selectedDagNodeId)) return;
    setSelectedDagNodeId(dagGraph.currentNodeId || dagGraph.nodes[dagGraph.nodes.length - 1]?.id || '');
    // Only depend on dagGraph
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dagGraph]);

  const commitDag = useCallback(
    (next: ResumeDagGraph) => {
      dagGraphRef.current = next;
      setDagGraph(next);
      const persistResumeId = getResumeId();
      if (persistResumeId) {
        persistTailorState(persistResumeId, { dagGraph: next });
      }
    },
    [getResumeId, persistTailorState],
  );

  const ensureCurrentDagNode = useCallback(
    (baseContent: Record<string, unknown>): ResumeDagNode => {
      const existing = dagGraphRef.current.nodes.find(
        (node) => node.id === dagGraphRef.current.currentNodeId,
      );
      if (existing) return existing;
      const created = createDagNode('draft', baseContent, true);
      const graph: ResumeDagGraph = {
        nodes: [created],
        edges: [],
        currentNodeId: created.id,
      };
      commitDag(graph);
      return created;
    },
    [commitDag],
  );

  const startDagAction = useCallback(
    (actionType: ResumeDagEdge['actionType'], note?: string): DagPendingAction => {
      const prevContent = contentRef.current;
      const current = ensureCurrentDagNode(prevContent);
      const ghostNodeId = `n-ghost-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
      const edgeId = `e-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
      const createdAt = new Date().toISOString();
      const ghostNode: ResumeDagNode = {
        id: ghostNodeId,
        state: 'processing',
        contentHash: current.contentHash,
        createdAt,
        label: 'PROCESSING',
        current: false,
      };
      const edge: ResumeDagEdge = {
        id: edgeId,
        fromNodeId: current.id,
        toNodeId: ghostNodeId,
        actionType,
        status: 'running',
        createdAt,
        note,
      };
      const graph = dagGraphRef.current;
      const next: ResumeDagGraph = {
        nodes: [...graph.nodes, ghostNode],
        edges: [...graph.edges, edge],
        currentNodeId: graph.currentNodeId,
      };
      commitDag(next);
      return { edgeId, ghostNodeId, fromNodeId: current.id };
    },
    [commitDag, ensureCurrentDagNode, contentRef],
  );

  const finishDagAction = useCallback(
    (
      pending: DagPendingAction,
      params: {
        actionType: ResumeDagEdge['actionType'];
        status: 'success' | 'failed';
        nextState?: ResumeDagNode['state'];
        nextContent?: Record<string, unknown>;
        note?: string;
      },
    ) => {
      const now = new Date().toISOString();
      const graph = dagGraphRef.current;
      const fromNode = graph.nodes.find((node) => node.id === pending.fromNodeId);
      if (!fromNode) return;
      const content = params.nextContent || contentRef.current;
      const nextHash = hashContent(content);
      const shouldCreateNode =
        params.status === 'success' &&
        ((params.nextState && params.nextState !== fromNode.state) ||
          nextHash !== fromNode.contentHash);

      const nextNode = shouldCreateNode
        ? createDagNode(params.nextState || fromNode.state, content, true, now)
        : null;
      const finalToId =
        params.status === 'success' ? (nextNode?.id || pending.fromNodeId) : pending.fromNodeId;

      const mappedNodes = graph.nodes
        .filter((node) => node.id !== pending.ghostNodeId)
        .map((node) => ({ ...node, current: node.id === finalToId }));
      if (nextNode) mappedNodes.push(nextNode);

      const mappedEdges = graph.edges.map((edge) => {
        if (edge.id !== pending.edgeId) return edge;
        return {
          ...edge,
          toNodeId: finalToId,
          status: params.status,
          finishedAt: now,
          note: params.note || edge.note,
        };
      });

      const next: ResumeDagGraph = {
        nodes: mappedNodes,
        edges: mappedEdges,
        currentNodeId: finalToId,
      };
      commitDag(next);
    },
    [commitDag, contentRef],
  );

  const handleRollbackToDagNode = useCallback(
    async (nodeId: string) => {
      if (!nodeId || !sessionId) return;
      try {
        const result = await toolRollbackVersion({
          session_id: sessionId,
          version_id: nodeId,
          note: 'rollback from dag panel',
        });
        const refined = toJsonObject(
          result.refined_document_obj || result.refined_resume_obj || {},
        );
        onRefinedChange(refined);
        onSuggestionClear();
      } catch {
        // error handled by caller
      }
    },
    [sessionId, onRefinedChange, onSuggestionClear],
  );

  // ── Layout Computation ─────────────────────────────────────────

  const dagLayout = useMemo(() => {
    const nodes = dagGraph.nodes || [];
    const edges = dagGraph.edges || [];
    if (!nodes.length) {
      return { positions: {} as Record<string, { x: number; y: number }>, width: 420, height: 240 };
    }

    const indexMap = new Map(nodes.map((node, index) => [node.id, index]));
    const incoming = new Map<string, number>();
    const outgoing = new Map<string, string[]>();
    nodes.forEach((node) => {
      incoming.set(node.id, 0);
      outgoing.set(node.id, []);
    });
    edges.forEach((edge) => {
      if (edge.fromNodeId === edge.toNodeId) return;
      incoming.set(edge.toNodeId, (incoming.get(edge.toNodeId) || 0) + 1);
      const next = outgoing.get(edge.fromNodeId) || [];
      next.push(edge.toNodeId);
      outgoing.set(edge.fromNodeId, next);
    });

    const roots = nodes
      .filter((node) => (incoming.get(node.id) || 0) === 0)
      .sort((a, b) => (indexMap.get(a.id) || 0) - (indexMap.get(b.id) || 0));
    const queue = roots.map((node) => node.id);
    const depth = new Map<string, number>();
    const maxDepth = Math.max(1, nodes.length);
    roots.forEach((node) => depth.set(node.id, 0));
    while (queue.length) {
      const id = queue.shift() || '';
      const currentDepth = depth.get(id) || 0;
      const nextIds = outgoing.get(id) || [];
      nextIds.forEach((targetId) => {
        if (targetId === id) return;
        const nextDepth = Math.max(depth.get(targetId) || 0, currentDepth + 1);
        if (nextDepth > maxDepth) return;
        if (!depth.has(targetId) || nextDepth > (depth.get(targetId) || 0)) {
          depth.set(targetId, nextDepth);
          queue.push(targetId);
        }
      });
    }
    nodes.forEach((node) => {
      if (!depth.has(node.id)) depth.set(node.id, 0);
    });

    const groups = new Map<number, ResumeDagNode[]>();
    nodes.forEach((node) => {
      const d = depth.get(node.id) || 0;
      const rows = groups.get(d) || [];
      rows.push(node);
      groups.set(d, rows);
    });

    const positions: Record<string, { x: number; y: number }> = {};
    const sortedDepths = Array.from(groups.keys()).sort((a, b) => a - b);
    sortedDepths.forEach((d) => {
      const rows = (groups.get(d) || []).sort(
        (a, b) => (indexMap.get(a.id) || 0) - (indexMap.get(b.id) || 0),
      );
      rows.forEach((node, rowIndex) => {
        positions[node.id] = { x: 80 + d * 170, y: 70 + rowIndex * 96 };
      });
    });

    const maxX = Math.max(...Object.values(positions).map((item) => item.x), 300);
    const maxY = Math.max(...Object.values(positions).map((item) => item.y), 180);
    return { positions, width: Math.max(420, maxX + 120), height: Math.max(240, maxY + 80) };
  }, [dagGraph]);

  const selectedDagNode = useMemo(() => {
    if (!selectedDagNodeId) return null;
    return dagGraph.nodes.find((node) => node.id === selectedDagNodeId) || null;
  }, [dagGraph.nodes, selectedDagNodeId]);

  return {
    dagGraph,
    dagWindowCollapsed: false,
    selectedDagNodeId,
    dagLayout,
    selectedDagNode,
    dagGraphRef,
    commitDag,
    ensureCurrentDagNode,
    startDagAction,
    finishDagAction,
    handleRollbackToDagNode,
  };
}
