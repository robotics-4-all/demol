import { useState, useCallback, useEffect } from 'react';
import type { Node, Edge } from 'reactflow';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { Canvas } from './components/Canvas';
import { PropertiesPanel } from './components/PropertiesPanel';
import { CodeViewer } from './components/CodeViewer';
import { Console } from './components/Console';
import { DeviceSettings } from './components/DeviceSettings';
import { api } from './services/api';
import type { DeviceModel } from './types';
import './App.css';

const STORAGE_KEY = 'demol-designer-state';

function App() {
  const [model, setModel] = useState<DeviceModel>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const { model: savedModel } = JSON.parse(saved);
      return savedModel;
    }
    return {
      name: 'MyDevice',
      description: 'A new IoT device',
      author: 'User',
      os: 'riotos',
      board: null,
      peripherals: [],
      powerSources: [],
      connections: [],
    };
  });

  const [nodes, setNodes] = useState<Node[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const { nodes: savedNodes } = JSON.parse(saved);
      return savedNodes || [];
    }
    return [];
  });

  const [edges, setEdges] = useState<Edge[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const { edges: savedEdges } = JSON.parse(saved);
      return savedEdges || [];
    }
    return [];
  });

  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<Edge | null>(null);
  const [consoleLogs, setConsoleLogs] = useState<{ type: 'error' | 'warning' | 'success' | 'info'; message: string }[]>([]);
  const [showConsole, setShowConsole] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // Save to localStorage
  useEffect(() => {
    const state = {
      nodes,
      edges,
      model: {
        name: model.name,
        description: model.description,
        author: model.author,
        os: model.os,
        board: model.board,
        peripherals: model.peripherals,
        powerSources: model.powerSources,
        connections: model.connections,
      }
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [nodes, edges, model]);

  // Synchronize model with nodes and edges
  useEffect(() => {
    const boardNode = nodes.find(n => n.type === 'board');
    const peripheralNodes = nodes.filter(n => n.type === 'peripheral');
    const powerSourceNodes = nodes.filter(n => n.type === 'powersource');

    const connections = edges.map(edge => {
      const sourceNode = nodes.find(n => n.id === edge.source);
      const targetNode = nodes.find(n => n.id === edge.target);

      let peripheralNode = targetNode;
      let boardNode = sourceNode;

      // If source is peripheral or powersource, it's the "from" side
      if (sourceNode?.type === 'peripheral' || sourceNode?.type === 'powersource') {
        peripheralNode = sourceNode;
        boardNode = targetNode;
      }

      return {
        id: edge.id,
        peripheralId: peripheralNode?.data.id,
        peripheralNodeId: peripheralNode?.id,
        peripheralName: peripheralNode?.data.instanceName || peripheralNode?.data.name,
        fromName: peripheralNode?.data.instanceName || peripheralNode?.data.name,
        toName: boardNode?.data.instanceName || boardNode?.data.name || 'board',
        type: edge.data?.type || (edge.sourceHandle === 'power' ? 'power' : 'gpio'),
        mappings: edge.data?.mappings || [],
      };
    });

    setModel(prev => ({
      ...prev,
      board: boardNode ? boardNode.data : null,
      peripherals: peripheralNodes.map(n => ({
        ...n.data,
        nodeId: n.id // Add node ID to distinguish instances
      })),
      powerSources: powerSourceNodes.map(n => ({
        ...n.data,
        nodeId: n.id
      })),
      connections: connections as any,
    }));
  }, [nodes, edges]);

  const handleDragStart = (_item: any, _type: any) => {
    // Handled by Sidebar
  };

  const handleNodesChange = useCallback((newNodes: Node[]) => {
    setNodes(newNodes);
  }, []);

  const handleEdgesChange = useCallback((newEdges: Edge[]) => {
    setEdges(newEdges);
  }, []);

  const handleSelectionChange = useCallback((node: Node | null, edge: Edge | null) => {
    setSelectedNode(node);
    setSelectedEdge(edge);
    // If both are null, the properties panel will close due to the rendering condition
  }, []);

  const handleUpdateNode = useCallback((id: string, data: any) => {
    setNodes(nds => nds.map(node => node.id === id ? { ...node, data } : node));
    if (selectedNode?.id === id) {
      setSelectedNode(prev => prev ? { ...prev, data } : null);
    }
  }, [selectedNode]);

  const handleUpdateEdge = useCallback((id: string, data: any) => {
    setEdges(eds => eds.map(edge => edge.id === id ? { ...edge, data } : edge));
    if (selectedEdge?.id === id) {
      setSelectedEdge(prev => prev ? { ...prev, data } : null);
    }
  }, [selectedEdge]);

  const handleUpdateModel = useCallback((updates: Partial<DeviceModel>) => {
    setModel(prev => ({ ...prev, ...updates }));
  }, []);

  const handleSave = async () => {
    try {
      // The useEffect already saves to localStorage on every change,
      // but we can provide visual feedback here.
      const state = {
        nodes,
        edges,
        model
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      console.log('Saved state to localStorage:', state);
      alert('Design saved to local storage!');
    } catch (error) {
      console.error('Failed to save model:', error);
      alert('Failed to save model');
    }
  };

  const handleValidate = async () => {
    try {
      setShowConsole(true);
      setConsoleLogs([{ type: 'info', message: 'Starting validation...' }]);

      const result = await api.validateModel(model);

      const newLogs: any[] = [];
      if (result.valid) {
        newLogs.push({ type: 'success', message: 'Model is valid!' });
      } else {
        newLogs.push({ type: 'error', message: 'Model validation failed.' });
      }

      result.errors.forEach((err: string) => newLogs.push({ type: 'error', message: err }));
      result.warnings.forEach((warn: string) => newLogs.push({ type: 'warning', message: warn }));

      setConsoleLogs(newLogs);
    } catch (error) {
      console.error('Validation failed:', error);
      setConsoleLogs([{ type: 'error', message: `Validation failed: ${error}` }]);
    }
  };

  const triggerDownload = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const handleGenerate = async () => {
    try {
      setShowConsole(true);
      setConsoleLogs([{ type: 'info', message: `Starting code generation for ${model.os}...` }]);

      const blob = await api.generateSource(model);
      setConsoleLogs(prev => [...prev, { type: 'success', message: 'Code generated successfully!' }]);
      triggerDownload(blob, `${model.name}_source.tar.gz`);
      alert('Code generated successfully! Download started.');
    } catch (error) {
      console.error('Generation error:', error);
      setConsoleLogs(prev => [...prev, { type: 'error', message: `Generation failed: ${error}` }]);
      alert('Failed to generate code');
    }
  };

  const handleGenerateDocs = async () => {
    try {
      setShowConsole(true);
      setConsoleLogs([{ type: 'info', message: 'Starting documentation generation...' }]);

      const blob = await api.generateDocs(model);
      setConsoleLogs(prev => [...prev, { type: 'success', message: 'Documentation generated successfully!' }]);
      triggerDownload(blob, `${model.name}_docs.tar.gz`);
      alert('Documentation generated successfully! Download started.');
    } catch (error) {
      console.error('Generation error:', error);
      setConsoleLogs(prev => [...prev, { type: 'error', message: `Generation failed: ${error}` }]);
      alert('Failed to generate documentation');
    }
  };

  const handleGenerateSMAuto = async () => {
    try {
      setShowConsole(true);
      setConsoleLogs([{ type: 'info', message: 'Starting SMAuto model generation...' }]);

      const blob = await api.generateSMAuto(model);
      setConsoleLogs(prev => [...prev, { type: 'success', message: 'SMAuto model generated successfully!' }]);
      triggerDownload(blob, `${model.name}_smauto.tar.gz`);
      alert('SMAuto model generated successfully! Download started.');
    } catch (error) {
      console.error('Generation error:', error);
      setConsoleLogs(prev => [...prev, { type: 'error', message: `Generation failed: ${error}` }]);
      alert('Failed to generate SMAuto model');
    }
  };

  const handleGenerateSVG = async () => {
    try {
      setShowConsole(true);
      setConsoleLogs([{ type: 'info', message: 'Starting SVG generation...' }]);

      const blob = await api.generateSVG(model);
      setConsoleLogs(prev => [...prev, { type: 'success', message: 'SVG diagrams generated successfully!' }]);
      triggerDownload(blob, `${model.name}_svg.tar.gz`);
      alert('SVG diagrams generated successfully! Download started.');
    } catch (error) {
      console.error('Generation error:', error);
      setConsoleLogs(prev => [...prev, { type: 'error', message: `Generation failed: ${error}` }]);
      alert('Failed to generate SVG diagrams');
    }
  };

  const handleExport = async () => {
    try {
      const content = await api.exportModel(model);
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${model.name}.dev`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export error:', error);
      alert('Failed to export model');
    }
  };

  const [viewingDeviceCode, setViewingDeviceCode] = useState(false);
  const [deviceCode, setDeviceCode] = useState('');

  const handleViewModel = async () => {
    try {
      const content = await api.exportModel(model);
      setDeviceCode(content);
      setViewingDeviceCode(true);
    } catch (error) {
      console.error('Failed to fetch device model:', error);
      alert('Failed to fetch device model');
    }
  };

  const handleClear = useCallback(() => {
    if (window.confirm('Are you sure you want to clear the current design? This cannot be undone.')) {
      setNodes([]);
      setEdges([]);
      setModel({
        name: 'MyDevice',
        description: 'A new IoT device',
        author: 'User',
        os: 'riotos',
        board: null,
        peripherals: [],
        powerSources: [],
        connections: [],
      });
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  return (
    <div className="app">
      <Header
        onSave={handleSave}
        onValidate={handleValidate}
        onGenerate={handleGenerate}
        onGenerateDocs={handleGenerateDocs}
        onGenerateSMAuto={handleGenerateSMAuto}
        onGenerateSVG={handleGenerateSVG}
        onExport={handleExport}
        onViewModel={handleViewModel}
        onSettings={() => setShowSettings(true)}
        onClear={handleClear}
      />
      <div className="main-content">
        <Sidebar onDragStart={handleDragStart} />
        <Canvas
          nodes={nodes}
          edges={edges}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          onSelectionChange={handleSelectionChange}
        />
        {(selectedNode || selectedEdge) && (
          <PropertiesPanel
            selectedNode={selectedNode}
            selectedEdge={selectedEdge}
            nodes={nodes}
            board={model.board}
            onUpdateNode={handleUpdateNode}
            onUpdateEdge={handleUpdateEdge}
            onClose={() => {
              setSelectedNode(null);
              setSelectedEdge(null);
            }}
          />
        )}

        {viewingDeviceCode && (
          <CodeViewer
            title={`${model.name} Device Model`}
            code={deviceCode}
            language="DeMoL (DEV)"
            onClose={() => setViewingDeviceCode(false)}
          />
        )}

        {showConsole && (
          <Console
            logs={consoleLogs}
            onClear={() => setConsoleLogs([])}
            onClose={() => setShowConsole(false)}
          />
        )}

        {showSettings && (
          <DeviceSettings
            model={model}
            onUpdate={handleUpdateModel}
            onClose={() => setShowSettings(false)}
          />
        )}
      </div>
    </div>
  );
}

export default App;
