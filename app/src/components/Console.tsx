import { type FC } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, X, Terminal } from 'lucide-react';
import './Console.css';

interface ConsoleProps {
    logs: { type: 'error' | 'warning' | 'success' | 'info'; message: string }[];
    onClear: () => void;
    onClose: () => void;
}

export const Console: FC<ConsoleProps> = ({ logs, onClear, onClose }) => {
    return (
        <div className="console-panel">
            <div className="console-header">
                <div className="header-left">
                    <Terminal size={16} />
                    <span>Validation Console</span>
                </div>
                <div className="header-actions">
                    <button className="console-btn" onClick={onClear}>Clear</button>
                    <button className="console-btn close" onClick={onClose}>
                        <X size={16} />
                    </button>
                </div>
            </div>
            <div className="console-content">
                {logs.length === 0 ? (
                    <div className="console-empty">
                        <p>No validation messages. Click "Validate" to check your model.</p>
                    </div>
                ) : (
                    logs.map((log, index) => (
                        <div key={index} className={`console-item ${log.type}`}>
                            <div className="item-icon">
                                {log.type === 'error' && <AlertCircle size={14} />}
                                {log.type === 'warning' && <AlertTriangle size={14} />}
                                {log.type === 'success' && <CheckCircle2 size={14} />}
                            </div>
                            <div className="item-message">{log.message}</div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};
