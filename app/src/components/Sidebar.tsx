import { useState, useEffect } from 'react';
import { Search, ChevronDown, ChevronRight, Cpu, Thermometer, Lightbulb } from 'lucide-react';
import { type Board, type Peripheral } from '../types';
import { api } from '../services/api';
import './Sidebar.css';

interface SidebarProps {
    onDragStart: (item: Board | Peripheral, type: 'board' | 'peripheral') => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onDragStart }) => {
    const [boards, setBoards] = useState<Board[]>([]);
    const [peripherals, setPeripherals] = useState<Peripheral[]>([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [expandedSections, setExpandedSections] = useState({
        boards: true,
        sensors: true,
        actuators: true,
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadComponents();
    }, []);

    const loadComponents = async () => {
        try {
            setLoading(true);
            const [boardsData, peripheralsData] = await Promise.all([
                api.getBoards(),
                api.getPeripherals(),
            ]);
            setBoards(boardsData);
            setPeripherals(peripheralsData);
        } catch (error) {
            console.error('Failed to load components:', error);
        } finally {
            setLoading(false);
        }
    };

    const toggleSection = (section: keyof typeof expandedSections) => {
        setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
    };

    const filteredBoards = boards.filter(b =>
        b.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const sensors = peripherals.filter(p => p.category === 'sensor');
    const actuators = peripherals.filter(p => p.category === 'actuator');

    const filteredSensors = sensors.filter(s =>
        s.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const filteredActuators = actuators.filter(a =>
        a.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const handleDragStart = (e: React.DragEvent, item: Board | Peripheral, type: 'board' | 'peripheral') => {
        e.dataTransfer.effectAllowed = 'copy';
        e.dataTransfer.setData('application/json', JSON.stringify({ item, type }));
        onDragStart(item, type);
    };

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <h2>Components</h2>
                <div className="search-box">
                    <Search size={16} />
                    <input
                        type="text"
                        placeholder="Search components..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            <div className="sidebar-content">
                {loading ? (
                    <div className="loading-state">
                        <div className="spinner" />
                        <p>Loading components...</p>
                    </div>
                ) : (
                    <>
                        {/* Boards Section */}
                        <div className="component-section">
                            <div className="section-header" onClick={() => toggleSection('boards')}>
                                {expandedSections.boards ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                <Cpu size={18} />
                                <span>Boards</span>
                                <span className="count">{filteredBoards.length}</span>
                            </div>
                            {expandedSections.boards && (
                                <div className="component-list">
                                    {filteredBoards.map((board) => (
                                        <div
                                            key={board.id}
                                            className="component-item board-item"
                                            draggable
                                            onDragStart={(e) => handleDragStart(e, board, 'board')}
                                        >
                                            <div className="component-icon">
                                                <Cpu size={20} />
                                            </div>
                                            <div className="component-info">
                                                <div className="component-name">{board.name}</div>
                                                <div className="component-meta">{board.type}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Sensors Section */}
                        <div className="component-section">
                            <div className="section-header" onClick={() => toggleSection('sensors')}>
                                {expandedSections.sensors ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                <Thermometer size={18} />
                                <span>Sensors</span>
                                <span className="count">{filteredSensors.length}</span>
                            </div>
                            {expandedSections.sensors && (
                                <div className="component-list">
                                    {filteredSensors.map((sensor) => (
                                        <div
                                            key={sensor.id}
                                            className="component-item sensor-item"
                                            draggable
                                            onDragStart={(e) => handleDragStart(e, sensor, 'peripheral')}
                                        >
                                            <div className="component-icon">
                                                <Thermometer size={20} />
                                            </div>
                                            <div className="component-info">
                                                <div className="component-name">{sensor.name}</div>
                                                <div className="component-meta">{sensor.type}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Actuators Section */}
                        <div className="component-section">
                            <div className="section-header" onClick={() => toggleSection('actuators')}>
                                {expandedSections.actuators ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                <Lightbulb size={18} />
                                <span>Actuators</span>
                                <span className="count">{filteredActuators.length}</span>
                            </div>
                            {expandedSections.actuators && (
                                <div className="component-list">
                                    {filteredActuators.map((actuator) => (
                                        <div
                                            key={actuator.id}
                                            className="component-item actuator-item"
                                            draggable
                                            onDragStart={(e) => handleDragStart(e, actuator, 'peripheral')}
                                        >
                                            <div className="component-icon">
                                                <Lightbulb size={20} />
                                            </div>
                                            <div className="component-info">
                                                <div className="component-name">{actuator.name}</div>
                                                <div className="component-meta">{actuator.type}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </>
                )}
            </div>
        </aside>
    );
};
