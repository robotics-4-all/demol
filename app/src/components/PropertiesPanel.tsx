import { type FC, useState, useEffect } from 'react';
import { X, Save, Settings, Link as LinkIcon, Code } from 'lucide-react';
import type { Board, PinMapping } from '../types';
import { CodeViewer } from './CodeViewer';
import './PropertiesPanel.css';

interface PropertiesPanelProps {
    selectedNode: any | null;
    selectedEdge: any | null;
    board: Board | null;
    onUpdateNode: (id: string, data: any) => void;
    onUpdateEdge: (id: string, data: any) => void;
    onClose: () => void;
    nodes?: any[];
}

export const PropertiesPanel: FC<PropertiesPanelProps> = ({
    selectedNode,
    selectedEdge,
    board,
    onUpdateNode,
    onUpdateEdge,
    onClose,
    nodes = [],
}) => {
    const [attributes, setAttributes] = useState<Record<string, any>>({});
    const [mappings, setMappings] = useState<PinMapping[]>([]);
    const [viewingCode, setViewingCode] = useState<{ title: string; code: string; language: string } | null>(null);

    useEffect(() => {
        if (selectedNode && (selectedNode.type === 'peripheral' || selectedNode.type === 'powersource')) {
            setAttributes(selectedNode.data.attributes || {});
        }
    }, [selectedNode]);

    useEffect(() => {
        if (selectedEdge) {
            setMappings(selectedEdge.data?.mappings || []);
        }
    }, [selectedEdge]);

    if (!selectedNode && !selectedEdge) return null;

    const handleAttributeChange = (key: string, value: any) => {
        setAttributes(prev => ({ ...prev, [key]: value }));
    };

    const saveAttributes = () => {
        if (selectedNode) {
            onUpdateNode(selectedNode.id, {
                ...selectedNode.data,
                attributes,
            });
        }
    };

    const addMapping = () => {
        setMappings(prev => [...prev, { fromPin: '', toPin: '' }]);
    };

    const updateMapping = (index: number, field: keyof PinMapping, value: string) => {
        const newMappings = [...mappings];
        newMappings[index][field] = value;
        setMappings(newMappings);
    };

    const removeMapping = (index: number) => {
        setMappings(prev => prev.filter((_, i) => i !== index));
    };

    const saveMappings = () => {
        if (selectedEdge) {
            onUpdateEdge(selectedEdge.id, {
                ...selectedEdge.data,
                mappings,
            });
        }
    };

    const viewNodeCode = () => {
        if (selectedNode) {
            setViewingCode({
                title: `${selectedNode.data.name} Model`,
                code: selectedNode.data.raw_content || '// No content available',
                language: 'DeMoL (HWD)'
            });
        }
    };

    const viewEdgeCode = () => {
        if (selectedEdge) {
            const fromName = selectedEdge.data?.fromName || 'Peripheral';
            const toName = selectedEdge.data?.toName || 'Board';
            const type = selectedEdge.data?.type || 'io';

            let code = `CONNECT ${fromName}${toName !== 'Board' && toName !== board?.name ? ` : ${toName}` : ''} WITH\n`;

            if (type === 'power') {
                code += '    POWER ';
                code += mappings.map(m => `${m.fromPin} -- ${m.toPin}`).join(', ');
            } else {
                code += '    DATA gpio ';
                code += mappings.map(m => `${m.fromPin} -- ${m.toPin}`).join(', ');
            }

            code += '\n;';

            setViewingCode({
                title: 'Connection Model',
                code: code,
                language: 'DeMoL (DEV)'
            });
        }
    };

    return (
        <aside className="properties-panel">
            <div className="panel-header">
                <div className="header-title">
                    {selectedNode ? (
                        <>
                            <Settings size={18} />
                            <span>{selectedNode.data.name} Properties</span>
                        </>
                    ) : (
                        <>
                            <LinkIcon size={18} />
                            <span>Connection Mapping</span>
                        </>
                    )}
                </div>
                <button className="close-btn" onClick={onClose}>
                    <X size={18} />
                </button>
            </div>

            <div className="panel-content">
                {selectedNode && (selectedNode.type === 'peripheral' || selectedNode.type === 'powersource') && (
                    <>
                        <div className="section">
                            <h3>General</h3>
                            <div className="field">
                                <label>Instance Name</label>
                                <input
                                    type="text"
                                    value={selectedNode.data.instanceName || selectedNode.data.name}
                                    onChange={(e) => onUpdateNode(selectedNode.id, { ...selectedNode.data, instanceName: e.target.value })}
                                />
                            </div>
                        </div>
                        {selectedNode.type === 'peripheral' && (
                            <div className="section">
                                <h3>Attributes</h3>
                                <div className="attributes-list">
                                    {selectedNode.data.attributes && Object.entries(selectedNode.data.attributes).map(([key, attr]: [string, any]) => (
                                        <div key={key} className="field">
                                            <label>{key} ({attr.type})</label>
                                            <input
                                                type={attr.type === 'int' || attr.type === 'float' ? 'number' : 'text'}
                                                value={attributes[key] !== undefined ? attributes[key] : (attr.default !== null ? attr.default : '')}
                                                onChange={(e) => handleAttributeChange(key, e.target.value)}
                                                placeholder={attr.default !== null ? `Default: ${attr.default}` : ''}
                                            />
                                        </div>
                                    ))}
                                    {(!selectedNode.data.attributes || Object.keys(selectedNode.data.attributes).length === 0) && (
                                        <p className="no-data">No configurable attributes defined for this peripheral.</p>
                                    )}
                                </div>
                                {selectedNode.data.attributes && Object.keys(selectedNode.data.attributes).length > 0 && (
                                    <button className="save-btn" onClick={saveAttributes}>
                                        <Save size={16} />
                                        Save Attributes
                                    </button>
                                )}
                            </div>
                        )}
                    </>
                )}

                {selectedEdge && (
                    <div className="section">
                        <h3>Pin Mappings</h3>
                        <p className="section-hint">
                            <span className={`type-badge ${selectedEdge.data?.type}`}>
                                {selectedEdge.data?.type === 'power' ? 'Power Connection' : 'IO Connection'}
                            </span>
                            Map pins between <strong>{board?.name || 'Board'}</strong> and{' '}
                            <strong>{selectedEdge.data?.targetNodeData?.name || 'Peripheral'}</strong>
                        </p>

                        <div className="mappings-list">
                            {mappings.map((mapping, index) => (
                                <div key={index} className="mapping-item">
                                    <select
                                        value={mapping.fromPin}
                                        onChange={(e) => updateMapping(index, 'fromPin', e.target.value)}
                                    >
                                        <option value="">Select Board Pin</option>
                                        {board?.pins
                                            .filter((p: any) => selectedEdge.data?.type === 'power' ? p.type !== 'io' : p.type === 'io')
                                            .map((p: any) => (
                                                <option key={p.name} value={p.name}>{p.name} ({p.type})</option>
                                            ))
                                        }
                                    </select>
                                    <span className="arrow">→</span>
                                    <select
                                        value={mapping.toPin}
                                        onChange={(e) => updateMapping(index, 'toPin', e.target.value)}
                                    >
                                        <option value="">Select Peripheral Pin</option>
                                        {(() => {
                                            const peripheralNode = nodes?.find(n =>
                                                (n.id === selectedEdge.source && (n.type === 'peripheral' || n.type === 'powersource')) ||
                                                (n.id === selectedEdge.target && (n.type === 'peripheral' || n.type === 'powersource'))
                                            );
                                            // Fallback to targetNodeData if nodes not available or not found (legacy)
                                            const pins = peripheralNode?.data?.pins || selectedEdge.data?.targetNodeData?.pins || [];

                                            return pins
                                                .filter((p: any) => selectedEdge.data?.type === 'power' ? p.type !== 'io' : p.type === 'io')
                                                .map((p: any) => (
                                                    <option key={p.name} value={p.name}>{p.name} ({p.type})</option>
                                                ));
                                        })()}
                                    </select>
                                    <button className="remove-btn" onClick={() => removeMapping(index)}>
                                        <X size={14} />
                                    </button>
                                </div>
                            ))}
                        </div>

                        <div className="panel-actions">
                            <button className="add-btn" onClick={addMapping}>
                                Add Mapping
                            </button>
                            <button className="save-btn" onClick={saveMappings}>
                                <Save size={16} />
                                Save Mappings
                            </button>
                        </div>
                    </div>
                )}
            </div>

            <div className="panel-footer">
                {selectedNode && (
                    <button className="view-code-btn" onClick={viewNodeCode}>
                        <Code size={16} />
                        View HWD Model
                    </button>
                )}
                {selectedEdge && (
                    <button className="view-code-btn" onClick={viewEdgeCode}>
                        <Code size={16} />
                        View Connection DSL
                    </button>
                )}
            </div>

            {viewingCode && (
                <CodeViewer
                    title={viewingCode.title}
                    code={viewingCode.code}
                    language={viewingCode.language}
                    onClose={() => setViewingCode(null)}
                />
            )}
        </aside>
    );
};
