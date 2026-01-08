# DeMoL Designer

A visual web-based designer for the DeMoL (Device Modeling Language) DSL. This application allows you to visually design IoT devices, validate them, and generate code for various platforms.

## Features

- **Visual Drag-and-Drop Interface**: Design devices by dragging boards and peripherals onto a canvas.
- **Component Library**: Access a library of supported boards and peripherals.
- **Real-time Validation**: Validate your device model against DeMoL semantic rules.
- **Code Generation**: Generate RiotOS or Raspberry Pi code directly from the visual model.
- **DSL Export**: Export your visual design to the `.dev` DSL format.

## Architecture

The application consists of two main services:

1.  **Frontend**: A React + Vite application using React Flow for the visual interface.
2.  **Backend**: A FastAPI service that interfaces with the DeMoL DSL engine for validation and generation.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.10+ (for local development)

### Running with Docker Compose (Recommended)

To build and run the entire application stack using Docker Compose:

1.  Navigate to the `app` directory:
    ```bash
    cd app
    ```

2.  Start the services:
    ```bash
    docker-compose up --build
    ```

3.  Access the application at [http://localhost:5173](http://localhost:5173).

The frontend service will automatically proxy API requests to the backend service.

### Local Development

If you prefer to run the services locally for development:

1.  **Backend**:
    ```bash
    cd api
    pip install -r ../requirements.txt
    python main.py
    ```
    The API will run on http://localhost:8000.

2.  **Frontend**:
    ```bash
    cd app
    npm install
    npm run dev
    ```
    The frontend will run on http://localhost:5173 and proxy API requests to port 8000.
