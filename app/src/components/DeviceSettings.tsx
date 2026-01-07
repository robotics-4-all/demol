import React, { useState } from 'react';
import { X, Save, Wifi, Database, Settings, User, FileText, Cpu } from 'lucide-react';
import type { DeviceModel, Network, Broker } from '../types';
import './DeviceSettings.css';

interface DeviceSettingsProps {
    model: DeviceModel;
    onUpdate: (updates: Partial<DeviceModel>) => void;
    onClose: () => void;
}

export const DeviceSettings: React.FC<DeviceSettingsProps> = ({ model, onUpdate, onClose }) => {
    const [activeTab, setActiveTab] = useState<'general' | 'network' | 'broker'>('general');
    const [localModel, setLocalModel] = useState<DeviceModel>(model);

    const handleGeneralChange = (field: keyof DeviceModel, value: string) => {
        setLocalModel(prev => ({ ...prev, [field]: value }));
    };

    const handleNetworkChange = (field: keyof Network, value: string) => {
        setLocalModel(prev => ({
            ...prev,
            network: {
                ...(prev.network || { type: 'WiFi' }),
                [field]: value
            } as Network
        }));
    };

    const handleBrokerChange = (field: keyof Broker, value: any) => {
        setLocalModel(prev => ({
            ...prev,
            broker: {
                ...(prev.broker || { type: 'MQTT', name: 'my_broker', host: 'localhost', port: 1883 }),
                [field]: value
            } as Broker
        }));
    };

    const handleSave = () => {
        onUpdate(localModel);
        onClose();
    };

    return (
        <div className="settings-overlay">
            <div className="settings-modal">
                <div className="settings-header">
                    <div className="header-title">
                        <Settings size={20} />
                        <span>Device Configuration</span>
                    </div>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="settings-body">
                    <div className="settings-tabs">
                        <button
                            className={`tab-btn ${activeTab === 'general' ? 'active' : ''}`}
                            onClick={() => setActiveTab('general')}
                        >
                            <FileText size={18} />
                            <span>General</span>
                        </button>
                        <button
                            className={`tab-btn ${activeTab === 'network' ? 'active' : ''}`}
                            onClick={() => setActiveTab('network')}
                        >
                            <Wifi size={18} />
                            <span>Network</span>
                        </button>
                        <button
                            className={`tab-btn ${activeTab === 'broker' ? 'active' : ''}`}
                            onClick={() => setActiveTab('broker')}
                        >
                            <Database size={18} />
                            <span>Broker</span>
                        </button>
                    </div>

                    <div className="tab-content">
                        {activeTab === 'general' && (
                            <div className="settings-section">
                                <h3>General Information</h3>
                                <div className="form-group">
                                    <label>Device Name</label>
                                    <input
                                        type="text"
                                        value={localModel.name}
                                        onChange={(e) => handleGeneralChange('name', e.target.value)}
                                        placeholder="e.g. MySmartHome"
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Description</label>
                                    <textarea
                                        value={localModel.description}
                                        onChange={(e) => handleGeneralChange('description', e.target.value)}
                                        placeholder="Describe your device..."
                                    />
                                </div>
                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Author</label>
                                        <div className="input-with-icon">
                                            <User size={16} />
                                            <input
                                                type="text"
                                                value={localModel.author}
                                                onChange={(e) => handleGeneralChange('author', e.target.value)}
                                            />
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label>Target OS</label>
                                        <div className="input-with-icon">
                                            <Cpu size={16} />
                                            <select
                                                value={localModel.os}
                                                onChange={(e) => handleGeneralChange('os', e.target.value)}
                                            >
                                                <option value="riotos">RIOT OS</option>
                                                <option value="raspbian">Raspberry Pi (Linux)</option>
                                                <option value="zephyr">Zephyr OS</option>
                                                <option value="arduino">Arduino</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {activeTab === 'network' && (
                            <div className="settings-section">
                                <h3>Network Configuration</h3>
                                <div className="form-group">
                                    <label>Network Type</label>
                                    <select
                                        value={localModel.network?.type || 'WiFi'}
                                        onChange={(e) => handleNetworkChange('type', e.target.value as any)}
                                    >
                                        <option value="WiFi">WiFi</option>
                                        <option value="Eth">Ethernet</option>
                                    </select>
                                </div>

                                {localModel.network?.type === 'WiFi' && (
                                    <>
                                        <div className="form-group">
                                            <label>SSID</label>
                                            <input
                                                type="text"
                                                value={localModel.network?.ssid || ''}
                                                onChange={(e) => handleNetworkChange('ssid', e.target.value)}
                                                placeholder="Network Name"
                                            />
                                        </div>
                                        <div className="form-group">
                                            <label>Password</label>
                                            <input
                                                type="password"
                                                value={localModel.network?.password || ''}
                                                onChange={(e) => handleNetworkChange('password', e.target.value)}
                                                placeholder="WiFi Password"
                                            />
                                        </div>
                                    </>
                                )}

                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Static IP (Optional)</label>
                                        <input
                                            type="text"
                                            value={localModel.network?.address || ''}
                                            onChange={(e) => handleNetworkChange('address', e.target.value)}
                                            placeholder="192.168.1.100"
                                        />
                                    </div>
                                    {localModel.network?.type === 'WiFi' && (
                                        <div className="form-group">
                                            <label>Channel</label>
                                            <input
                                                type="text"
                                                value={localModel.network?.channel || ''}
                                                onChange={(e) => handleNetworkChange('channel', e.target.value)}
                                                placeholder="Auto"
                                            />
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {activeTab === 'broker' && (
                            <div className="settings-section">
                                <h3>Message Broker</h3>
                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Broker Type</label>
                                        <select
                                            value={localModel.broker?.type || 'MQTT'}
                                            onChange={(e) => handleBrokerChange('type', e.target.value as any)}
                                        >
                                            <option value="MQTT">MQTT</option>
                                            <option value="AMQP">AMQP (RabbitMQ)</option>
                                            <option value="Redis">Redis</option>
                                        </select>
                                    </div>
                                    <div className="form-group">
                                        <label>Broker Name</label>
                                        <input
                                            type="text"
                                            value={localModel.broker?.name || ''}
                                            onChange={(e) => handleBrokerChange('name', e.target.value)}
                                            placeholder="my_broker"
                                        />
                                    </div>
                                </div>

                                <div className="form-row">
                                    <div className="form-group flex-2">
                                        <label>Host</label>
                                        <input
                                            type="text"
                                            value={localModel.broker?.host || ''}
                                            onChange={(e) => handleBrokerChange('host', e.target.value)}
                                            placeholder="broker.hivemq.com"
                                        />
                                    </div>
                                    <div className="form-group flex-1">
                                        <label>Port</label>
                                        <input
                                            type="number"
                                            value={localModel.broker?.port || 1883}
                                            onChange={(e) => handleBrokerChange('port', parseInt(e.target.value))}
                                        />
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label className="checkbox-label">
                                        <input
                                            type="checkbox"
                                            checked={localModel.broker?.ssl || false}
                                            onChange={(e) => handleBrokerChange('ssl', e.target.checked)}
                                        />
                                        <span>Use SSL/TLS</span>
                                    </label>
                                </div>

                                <div className="auth-section">
                                    <h4>Authentication (Optional)</h4>
                                    <div className="form-row">
                                        <div className="form-group">
                                            <label>Username</label>
                                            <input
                                                type="text"
                                                value={localModel.broker?.username || ''}
                                                onChange={(e) => handleBrokerChange('username', e.target.value)}
                                            />
                                        </div>
                                        <div className="form-group">
                                            <label>Password</label>
                                            <input
                                                type="password"
                                                value={localModel.broker?.password || ''}
                                                onChange={(e) => handleBrokerChange('password', e.target.value)}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                <div className="settings-footer">
                    <button className="cancel-btn" onClick={onClose}>Cancel</button>
                    <button className="save-btn" onClick={handleSave}>
                        <Save size={18} />
                        Save Configuration
                    </button>
                </div>
            </div>
        </div>
    );
};
