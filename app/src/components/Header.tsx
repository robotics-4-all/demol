import React from 'react';
import { Cpu, Zap, Database, Download, Code, Wifi, Settings } from 'lucide-react';
import './Header.css';

interface HeaderProps {
    onSave: () => void;
    onValidate: () => void;
    onGenerate: () => void;
    onExport: () => void;
    onViewModel: () => void;
    onSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onSave, onValidate, onGenerate, onExport, onViewModel, onSettings }) => {
    return (
        <header className="app-header">
            <div className="header-left">
                <div className="logo">
                    <Cpu className="logo-icon" />
                    <span className="logo-text">DeMoL Designer</span>
                </div>
                <div className="header-subtitle">Visual IoT Device Modeler</div>
            </div>

            <div className="header-center">
                <div className="status-indicators">
                    <div className="status-item">
                        <Zap size={16} />
                        <span>Ready</span>
                    </div>
                </div>
            </div>

            <div className="header-right">
                <button className="action-btn secondary" onClick={onValidate} title="Validate Model">
                    <Database size={18} />
                    <span>Validate</span>
                </button>
                <button className="action-btn secondary" onClick={onSettings} title="Device Settings">
                    <Settings size={18} />
                    <span>Settings</span>
                </button>
                <button className="action-btn secondary" onClick={onViewModel} title="View DeMoL Code">
                    <Code size={18} />
                    <span>View Model</span>
                </button>
                <button className="action-btn secondary" onClick={onGenerate} title="Generate Code">
                    <Wifi size={18} />
                    <span>Generate</span>
                </button>
                <button className="action-btn secondary" onClick={onExport} title="Export as .dev file">
                    <Download size={18} />
                    <span>Export</span>
                </button>
                <button className="action-btn primary" onClick={onSave} title="Save Project">
                    <Zap size={18} />
                    <span>Save</span>
                </button>
            </div>
        </header>
    );
};
