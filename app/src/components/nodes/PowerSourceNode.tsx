import { type FC } from 'react';
import { Handle, Position } from 'reactflow';
import { Battery, Zap } from 'lucide-react';
import { type PowerSource } from '../../types';
import './PeripheralNode.css'; // Reuse peripheral styles
import './PowerSourceNode.css';

interface PowerSourceNodeProps {
    data: PowerSource;
    selected?: boolean;
}

export const PowerSourceNode: FC<PowerSourceNodeProps> = ({ data, selected }) => {
    return (
        <div className={`peripheral-node powersource-node ${selected ? 'selected' : ''}`}>
            <div className="node-header">
                <div className="node-icon powersource-icon">
                    <Battery size={20} />
                </div>
                <div className="node-title">
                    <div className="node-name">{data.name}</div>
                    <div className="node-type">{data.type}</div>
                </div>
            </div>

            <div className="node-body">
                <div className="node-specs">
                    <div className="spec-item">
                        <Zap size={12} />
                        <span>{data.operational.voltage}</span>
                    </div>
                    {data.operational.capacity && (
                        <div className="spec-item">
                            <span className="spec-label">Capacity:</span>
                            <span>{data.operational.capacity}</span>
                        </div>
                    )}
                    {data.operational.max_current && (
                        <div className="spec-item">
                            <span className="spec-label">Max Current:</span>
                            <span>{data.operational.max_current}</span>
                        </div>
                    )}
                </div>

                <div className="node-pins">
                    <div className="pins-label">Pins: {data.pins.length}</div>
                </div>
            </div>

            {/* Power source only has output handles (source) */}
            <Handle
                type="source"
                position={Position.Right}
                id="power"
                className="handle-power"
            />
        </div>
    );
};
