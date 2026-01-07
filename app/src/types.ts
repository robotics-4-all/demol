export interface Pin {
    name: string;
    type: 'power' | 'io' | 'vcc' | 'gnd';
    number: number;
    functions?: string[];
}

export interface OperationalSpecs {
    vcc: string;
    ioVcc?: string;
    cpu?: {
        family: string;
    };
    memory?: {
        ram: string;
    };
    power?: {
        min?: string;
        max?: string;
        avg?: string;
    };
}

export interface Board {
    id: string;
    name: string;
    type: string;
    pins: Pin[];
    operational: OperationalSpecs;
    raw_content?: string;
}

export interface Peripheral {
    id: string;
    name: string;
    type: string;
    category: 'sensor' | 'actuator';
    pins: Pin[];
    operational: OperationalSpecs;
    attributes?: Record<string, any>;
    raw_content?: string;
}

export interface PinMapping {
    boardPin: string;
    peripheralPin: string;
}

export interface Connection {
    id: string;
    peripheralId: string;
    type: 'power' | 'io';
    mappings: PinMapping[];
}

export interface Network {
    type: 'WiFi' | 'Eth';
    ssid?: string;
    password?: string;
    address?: string;
    channel?: string;
}

export interface Broker {
    type: 'MQTT' | 'AMQP' | 'Redis';
    name: string;
    host: string;
    port: number;
    vhost?: string;
    topicExchange?: string;
    rpcExchange?: string;
    ssl?: boolean;
    basePath?: string;
    webPath?: string;
    webPort?: number;
    db?: number;
    username?: string;
    password?: string;
    key?: string;
}

export interface DeviceModel {
    name: string;
    description: string;
    author: string;
    os: string;
    board: Board | null;
    peripherals: Peripheral[];
    connections: Connection[];
    network?: Network;
    broker?: Broker;
}

export interface CanvasNodeData extends Board, Peripheral {
    // Union of Board and Peripheral for convenience in nodes
}
