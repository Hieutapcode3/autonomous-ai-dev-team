"use client";

import React, { useMemo, useEffect } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  Edge,
  Node,
  useNodesState,
  useEdgesState,
  MarkerType,
  BackgroundVariant,
  Position,
} from "@xyflow/react";
import { SubTaskNode, SubTaskNodeData } from "./SubTaskNode";

interface DAGCanvasProps {
  tasks: Record<string, any>;
  executionOrder: string[][];
  onSelectTask?: (taskId: string) => void;
}

const nodeTypes = {
  subTask: SubTaskNode,
};

export function DAGCanvas({ tasks, executionOrder, onSelectTask }: DAGCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Layout calculation based on executionOrder (topological layers)
  useEffect(() => {
    if (!tasks || Object.keys(tasks).length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const calculatedNodes: Node[] = [];
    const calculatedEdges: Edge[] = [];

    const layerMap: Record<string, number> = {};
    executionOrder.forEach((batch, layerIndex) => {
      batch.forEach((tid) => {
        layerMap[tid] = layerIndex;
      });
    });

    const levelCounts: Record<number, number> = {};
    const taskIds = Object.keys(tasks);

    taskIds.forEach((tid) => {
      const layer = layerMap[tid] ?? 0;
      levelCounts[layer] = (levelCounts[layer] || 0) + 1;
    });

    const levelCurrentIndex: Record<number, number> = {};

    taskIds.forEach((tid) => {
      const task = tasks[tid];
      const layer = layerMap[tid] ?? 0;
      const countInLayer = levelCounts[layer] || 1;
      const indexInLayer = levelCurrentIndex[layer] || 0;
      levelCurrentIndex[layer] = indexInLayer + 1;

      // Coordinate positioning for Horizontal DAG Layout:
      // X = horizontal step along execution layer (Left -> Right)
      // Y = vertical spacing for concurrent parallel tasks in the same layer
      const x = layer * 380 + 80;
      const y = (indexInLayer - (countInLayer - 1) / 2) * 260 + 100;

      calculatedNodes.push({
        id: tid,
        type: "subTask",
        position: { x, y },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: {
          id: task.task_id,
          title: task.title,
          description: task.description,
          domain: task.domain,
          complexity: task.complexity,
          assignedModel: task.assigned_model,
          assignedAgent: task.assigned_agent,
          routingRationale: task.routing_rationale,
          status: task.status,
          retryOf: task.retry_of,
          costUsd: task.cost_usd,
          executionTimeMs: task.execution_time_ms,
          estimatedTimeSec: task.estimated_time_sec,
        },
      });

      // Construct edges from dependencies connecting Right -> Left
      if (task.dependencies && Array.isArray(task.dependencies)) {
        task.dependencies.forEach((depId: string) => {
          const isReplanEdge = !!task.retry_of;
          calculatedEdges.push({
            id: `e-${depId}-${tid}`,
            source: depId,
            target: tid,
            sourceHandle: "source-right",
            targetHandle: "target-left",
            type: "smoothstep",
            animated: task.status === "running" || isReplanEdge,
            style: {
              stroke: isReplanEdge ? "#f97316" : task.status === "completed" ? "#10b981" : "#06b6d4",
              strokeWidth: isReplanEdge ? 2.5 : 2,
              strokeDasharray: isReplanEdge ? "5,5" : undefined,
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: isReplanEdge ? "#f97316" : task.status === "completed" ? "#10b981" : "#06b6d4",
              width: 18,
              height: 18,
            },
          });
        });
      }
    });

    setNodes(calculatedNodes);
    setEdges(calculatedEdges);
  }, [tasks, executionOrder, setNodes, setEdges]);

  return (
    <div className="w-full h-full relative bg-slate-950/70 rounded-2xl border border-slate-800/80 overflow-hidden shadow-inner">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelectTask?.(node.id)}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1.5}
          color="#1e293b"
        />
        <Controls className="!bg-slate-900 !border-slate-800 !text-slate-300 !rounded-xl !shadow-2xl fill-white" />
      </ReactFlow>
    </div>
  );
}
