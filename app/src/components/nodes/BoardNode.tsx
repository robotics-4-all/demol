import { type FC } from 'react';
import { Handle, Position } from 'reactflow';
import { Cpu, Zap, Wifi } from 'lucide-react';
import { type Board } from '../../types';
import './BoardNode.css';

interface BoardNodeProps {
    data: Board;
    selected?: boolean;
}

export const BoardNode: FC<BoardNodeProps> = ({ data, selected }) => {
    return (
        <div className={`board-node ${selected ? 'selected' : ''}`}>
            <div className="node-header">
                <div className="node-icon">
                    <Cpu size={24} />
                </div>
                <div className="node-title">
                    <div className="node-name">{data.name}</div>
                    <div className="node-type">{data.type}</div>
                </div>
            </div>

            <div className="node-body">
                <div className="node-specs">
                    {data.operational.cpu && (
                        <div className="spec-item">
                            <Cpu size={14} />
                            <span>{data.operational.cpu.family}</span>
                        </div>
                    )}
                    {data.operational.memory && (
                        <div className="spec-item">
                            <Zap size={14} />
                            <span>{data.operational.memory.ram}</span>
                        </div>
                    )}
                    <div className="spec-item">
                        <Wifi size={14} />
                        <span>{data.operational.vcc}</span>
                    </div>
                </div>

                {data.inputPowerPins && data.inputPowerPins.length > 0 && (
                    <div className="node-input-power">
                        <div className="input-power-label">Input Power:</div>
                        <div className="input-power-pins">
                            {data.inputPowerPins.map(pin => (
                                <span key={pin} className="power-pin-badge">{pin}</span>
                            ))}
                        </div>
                    </div>
                )}

                <div className="node-pins">
                    <div className="pins-label">Pins: {data.pins.length}</div>
                </div>
            </div>

            {/* Connection handles (Outputs) */}
            <Handle
                type="source"
                position={Position.Right}
                id="power"
                className="handle-power"
                style={{ top: '30%' }}
                title="Power Output"
            />
            <Handle
                type="source"
                position={Position.Right}
                id="io"
                className="handle-io"
                style={{ top: '70%' }}
                title="IO / Data"
            />

            {/* Connection handles (Inputs) */}
            <Handle
                type="target"
                position={Position.Left}
                id="power"
                className="handle-power"
                style={{ top: '30%' }}
                title="Power Input"
            />
        </div>
    );
};
