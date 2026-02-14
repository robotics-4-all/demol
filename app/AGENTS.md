# app/ — Visual Designer (React Frontend)

## OVERVIEW

React + Vite + React Flow visual designer for DeMoL. Drag-and-drop IoT device design with real-time validation and code generation via FastAPI backend on port 8000.

## STRUCTURE

```
app/
├── src/
│   ├── main.tsx              # React entry point
│   ├── App.tsx               # Main app component (React Flow canvas + panels)
│   ├── types.ts              # TypeScript type definitions
│   ├── components/
│   │   ├── Canvas.tsx        # React Flow canvas wrapper
│   │   ├── Sidebar.tsx       # Component library (boards, peripherals)
│   │   ├── Header.tsx        # Top bar with actions
│   │   ├── PropertiesPanel.tsx  # Selected node property editor
│   │   ├── DeviceSettings.tsx   # Device metadata editor
│   │   ├── Console.tsx       # Validation output display
│   │   ├── CodeViewer.tsx    # Generated code viewer
│   │   └── nodes/
│   │       ├── BoardNode.tsx       # Board visual node
│   │       ├── PeripheralNode.tsx  # Peripheral visual node
│   │       └── PowerSourceNode.tsx # Power source visual node
│   └── services/
│       └── api.ts            # API client (fetch calls to backend)
├── index.html
├── package.json              # React 19, Vite 7, React Flow, @xyflow/react
├── tsconfig.json             # TypeScript project references
├── vite.config.ts            # Vite config with API proxy to :8000
└── nginx.conf                # Production reverse proxy config
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Add node type | `src/components/nodes/` | Create `<Type>Node.tsx` + CSS, register in Canvas.tsx |
| Add panel/sidebar | `src/components/` | Follow existing pattern: component + CSS file |
| API calls | `src/services/api.ts` | All backend communication centralized here |
| Type definitions | `src/types.ts` | Shared types for device model, board, peripheral |
| Vite/proxy config | `vite.config.ts` | API proxy: `/api` → `http://localhost:8000` |

## CONVENTIONS

- TypeScript strict mode (`noUnusedLocals`, `noUnusedParameters`)
- Component + co-located CSS file (e.g., `Canvas.tsx` + `Canvas.css`)
- Node types follow React Flow custom node pattern
- API calls return JSON matching FastAPI response models
- Development: `npm run dev` (port 5173), Production: Nginx serves built assets

## ANTI-PATTERNS

- Do NOT call backend directly — use `services/api.ts`
- Do NOT add API keys in frontend code — backend handles auth
- Node components must register their `nodeTypes` in the React Flow provider
