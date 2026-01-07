import { useCallback, useState } from 'react';
import ReactFlow, {
    type Node,
    type Edge,
    type Connection,
    addEdge,
    applyNodeChanges,
    applyEdgeChanges,
    Background,
    Controls,
    MiniMap,
    BackgroundVariant,
} from 'reactflow';
import 'reactflow/dist/style.css';
// import { Board, Peripheral } from '../types';
import { BoardNode } from './nodes/BoardNode';
import { PeripheralNode } from './nodes/PeripheralNode';
import './Canvas.css';

const nodeTypes = {
    board: BoardNode,
    peripheral: PeripheralNode,
};

interface CanvasProps {
    nodes: Node[];
    edges: Edge[];
    onNodesChange: (nodes: Node[]) => void;
    onEdgesChange: (edges: Edge[]) => void;
    onSelectionChange: (node: Node | null, edge: Edge | null) => void;
}

export const Canvas: React.FC<CanvasProps> = ({
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onSelectionChange
}) => {
    const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

    const onConnect = useCallback(
        (params: Connection) => {
            const targetNode = nodes.find(n => n.id === params.target);
            const newEdges = addEdge(
                {
                    ...params,
                    type: 'smoothstep',
                    animated: true,
                    style: { stroke: params.sourceHandle === 'power' ? '#ef4444' : '#6366f1', strokeWidth: 2 },
                    data: {
                        mappings: [],
                        targetNodeData: targetNode?.data,
                        type: params.sourceHandle
                    }
                },
                edges
            );
            onEdgesChange(newEdges);
        },
        [edges, nodes, onEdgesChange]
    );

    const onNodesChangeInternal = useCallback((changes: any) => {
        onNodesChange(applyNodeChanges(changes, nodes));
    }, [nodes, onNodesChange]);

    const onEdgesChangeInternal = useCallback((changes: any) => {
        onEdgesChange(applyEdgeChanges(changes, edges));
    }, [edges, onEdgesChange]);

    const onSelectionChangeInternal = useCallback(({ nodes: selectedNodes, edges: selectedEdges }: { nodes: Node[], edges: Edge[] }) => {
        onSelectionChange(
            selectedNodes.length > 0 ? selectedNodes[0] : null,
            selectedEdges.length > 0 ? selectedEdges[0] : null
        );
    }, [onSelectionChange]);

    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'copy';
    }, []);

    const onDrop = useCallback(
        (event: React.DragEvent) => {
            event.preventDefault();

            if (!reactFlowInstance) return;

            const data = event.dataTransfer.getData('application/json');
            if (!data) return;

            const { item, type } = JSON.parse(data);
            const position = reactFlowInstance.screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
            });

            const count = nodes.filter(n => n.data.id === item.id).length + 1;
            const instanceName = type === 'board' ? item.name : `${item.name}_${count}`;

            const newNode: Node = {
                id: `${type}-${Date.now()}`,
                type,
                position,
                data: { ...item, instanceName },
            };

            onNodesChange([...nodes, newNode]);
        },
        [reactFlowInstance, nodes, onNodesChange]
    );

    const onNodesDelete = useCallback(
        (deleted: Node[]) => {
            const remainingNodes = nodes.filter((n) => !deleted.find((d) => d.id === n.id));
            onNodesChange(remainingNodes);
        },
        [nodes, onNodesChange]
    );

    const onEdgesDelete = useCallback(
        (deleted: Edge[]) => {
            const remainingEdges = edges.filter((e) => !deleted.find((d) => d.id === e.id));
            onEdgesChange(remainingEdges);
        },
        [edges, onEdgesChange]
    );

    return (
        <div className="canvas-container">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChangeInternal}
                onEdgesChange={onEdgesChangeInternal}
                onConnect={onConnect}
                onInit={setReactFlowInstance}
                onDrop={onDrop}
                onDragOver={onDragOver}
                onNodesDelete={onNodesDelete}
                onEdgesDelete={onEdgesDelete}
                onSelectionChange={onSelectionChangeInternal}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-left"
            >
                <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#334155" />
                <Controls className="flow-controls" />
                <MiniMap
                    className="flow-minimap"
                    nodeColor={(node) => {
                        if (node.type === 'board') return '#6366f1';
                        if (node.data.category === 'sensor') return '#10b981';
                        return '#f59e0b';
                    }}
                />
            </ReactFlow>

            {nodes.length === 0 && (
                <div className="canvas-empty-state">
                    <div className="empty-state-content">
                        <div className="empty-state-icon">📦</div>
                        <h3>Start Building Your Device</h3>
                        <p>Drag and drop a board from the sidebar to begin</p>
                    </div>
                </div>
            )}
        </div>
    );
};
