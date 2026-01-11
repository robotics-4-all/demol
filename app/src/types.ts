export interface Pin {
    name: string;
    type: 'power' | 'io' | 'vcc' | 'gnd';
    number: number;
    status: 'essential' | 'optional';
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
    inputPowerPins?: string[];
    raw_content?: string;
}

export interface Peripheral {
    id: string;
    name: string;
    instanceName?: string;
    type: string;
    category: 'sensor' | 'actuator';
    pins: Pin[];
    operational: OperationalSpecs;
    attributes?: Record<string, any>;
    raw_content?: string;
}

export interface PowerSource {
    id: string;
    name: string;
    instanceName?: string;
    nodeId?: string;
    type: string;
    pins: Pin[];
    operational: {
        voltage: string;
        capacity?: string;
        max_current?: string;
    };
    raw_content?: string;
}

export interface PinMapping {
    function?: string; // e.g. sda, scl, mosi, miso
    fromPin: string;   // Peripheral Pin
    toPin: string;     // Board Pin
}

export interface Connection {
    id: string;
    peripheralId: string;
    fromName: string;
    toName: string;
    type: 'power' | 'io' | 'gpio' | 'i2c' | 'spi' | 'uart';
    mappings: PinMapping[];
    props?: Record<string, any>;
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
    powerSources: PowerSource[];
    connections: Connection[];
    network?: Network;
    broker?: Broker;
}

export interface CanvasNodeData extends Board, Peripheral {
    // Union of Board and Peripheral for convenience in nodes
}
