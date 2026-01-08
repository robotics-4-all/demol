import { type Board, type Peripheral } from '../types';

const API_BASE = '/api';

export const api = {
    // Get available boards
    async getBoards(): Promise<Board[]> {
        const response = await fetch(`${API_BASE}/boards`);
        if (!response.ok) throw new Error('Failed to fetch boards');
        return response.json();
    },

    // Get available peripherals
    async getPeripherals(): Promise<Peripheral[]> {
        const response = await fetch(`${API_BASE}/peripherals`);
        if (!response.ok) throw new Error('Failed to fetch peripherals');
        return response.json();
    },

    // Get available power sources
    async getPowerSources(): Promise<any[]> {
        const response = await fetch(`${API_BASE}/powersources`);
        if (!response.ok) throw new Error('Failed to fetch power sources');
        return response.json();
    },

    // Validate device model
    async validateModel(model: any): Promise<{ valid: boolean; errors: string[]; warnings: string[]; dsl?: string }> {
        const response = await fetch(`${API_BASE}/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(model),
        });
        if (!response.ok) throw new Error('Failed to validate model');
        return response.json();
    },

    // Generate code
    async generateCode(model: any, platform: 'rpi' | 'riot'): Promise<{ success: boolean; files?: any; error?: string }> {
        const response = await fetch(`${API_BASE}/generate/${platform}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(model),
        });
        if (!response.ok) throw new Error('Failed to generate code');
        return response.json();
    },

    // Export model as .dev file
    async exportModel(model: any): Promise<string> {
        const response = await fetch(`${API_BASE}/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(model),
        });
        if (!response.ok) throw new Error('Failed to export model');
        const data = await response.json();
        return data.content;
    },
};
