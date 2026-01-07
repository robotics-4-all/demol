import { type FC } from 'react';
import { Handle, Position } from 'reactflow';
import { Thermometer, Lightbulb, Zap } from 'lucide-react';
import { type Peripheral } from '../../types';
import './PeripheralNode.css';

interface PeripheralNodeProps {
    data: Peripheral;
    selected?: boolean;
}

export const PeripheralNode: FC<PeripheralNodeProps> = ({ data, selected }) => {
    const isSensor = data.category === 'sensor';
    const Icon = isSensor ? Thermometer : Lightbulb;

    return (
        <div className={`peripheral-node ${data.category}-node ${selected ? 'selected' : ''}`}>
            <div className="node-header">
                <div className={`node-icon ${data.category}-icon`}>
                    <Icon size={20} />
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
                        <span>{data.operational.vcc}</span>
                    </div>
                    {data.operational.power && (
                        <div className="spec-item">
                            <span className="spec-label">Power:</span>
                            <span>{data.operational.power.avg || data.operational.power.max}</span>
                        </div>
                    )}
                </div>

                <div className="node-pins">
                    <div className="pins-label">Pins: {data.pins.length}</div>
                </div>
            </div>

            {/* Connection handles */}
            <Handle
                type="target"
                position={Position.Left}
                id="power"
                className="handle-power"
                style={{ top: '30%' }}
            />
            <Handle
                type="target"
                position={Position.Left}
                id="io"
                className="handle-io"
                style={{ top: '70%' }}
            />
        </div>
    );
};
