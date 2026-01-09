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

    // Generate source code
    async generateSource(model: any, platform?: string): Promise<Blob> {
        const url = platform ? `${API_BASE}/generate/source/${platform}` : `${API_BASE}/generate/source`;
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(model),
        });
        if (!response.ok) throw new Error('Failed to generate source code');
        return response.blob();
    },

    // Generate documentation
    async generateDocs(model: any): Promise<Blob> {
        const response = await fetch(`${API_BASE}/generate/docs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(model),
        });
        if (!response.ok) throw new Error('Failed to generate documentation');
        return response.blob();
    },

    // Generate SMAuto model
    async generateSMAuto(model: any): Promise<Blob> {
        const response = await fetch(`${API_BASE}/generate/smauto`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(model),
        });
        if (!response.ok) throw new Error('Failed to generate SMAuto model');
        return response.blob();
    },

    // Generate SVG diagrams
    async generateSVG(model: any): Promise<Blob> {
        const response = await fetch(`${API_BASE}/generate/svg`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(model),
        });
        if (!response.ok) throw new Error('Failed to generate SVG diagrams');
        return response.blob();
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
