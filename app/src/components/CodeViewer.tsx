import { type FC } from 'react';
import { X, Copy } from 'lucide-react';
import './CodeViewer.css';

interface CodeViewerProps {
    title: string;
    code: string;
    language: string;
    onClose: () => void;
}

export const CodeViewer: FC<CodeViewerProps> = ({ title, code, language, onClose }) => {
    const copyToClipboard = () => {
        navigator.clipboard.writeText(code);
        alert('Copied to clipboard!');
    };

    return (
        <div className="code-viewer-overlay">
            <div className="code-viewer-container">
                <div className="code-viewer-header">
                    <div className="header-title">
                        <h3>{title}</h3>
                        <span className="language-tag">{language}</span>
                    </div>
                    <div className="header-actions">
                        <button className="action-btn" onClick={copyToClipboard} title="Copy to clipboard">
                            <Copy size={18} />
                        </button>
                        <button className="action-btn close" onClick={onClose}>
                            <X size={18} />
                        </button>
                    </div>
                </div>
                <div className="code-viewer-content">
                    <pre>
                        <code>{code}</code>
                    </pre>
                </div>
            </div>
        </div>
    );
};
