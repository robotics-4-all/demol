from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import sys
import json
from textx import metamodel_from_file

# Add project root to path to import demol
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from demol.lang import build_model, get_device_mm, get_component_mm
from demol.transformations import json_to_demol, demol_to_json
from demol.definitions import BOARD_MODEL_REPO_PATH, PERIPHERAL_MODEL_REPO_PATH

app = FastAPI(title="DeMoL Designer API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# Models
class Pin(BaseModel):
    name: str
    type: str
    number: int
    functions: Optional[List[str]] = None

class OperationalSpecs(BaseModel):
    vcc: str
    ioVcc: Optional[str] = None
    cpu: Optional[Dict[str, Any]] = None
    memory: Optional[Dict[str, Any]] = None
    power: Optional[Dict[str, Any]] = None

class Board(BaseModel):
    id: str
    name: str
    type: str
    pins: List[Pin]
    operational: OperationalSpecs
    raw_content: Optional[str] = None

class Peripheral(BaseModel):
    id: str
    name: str
    instanceName: Optional[str] = None
    nodeId: Optional[str] = None
    type: str
    category: str
    pins: List[Pin]
    operational: OperationalSpecs
    attributes: Optional[Dict[str, Any]] = None
    raw_content: Optional[str] = None

class Network(BaseModel):
    type: str # 'WiFi' or 'Eth'
    ssid: Optional[str] = None
    password: Optional[str] = None
    address: Optional[str] = None
    channel: Optional[str] = None

class Broker(BaseModel):
    type: str # 'MQTT', 'AMQP', 'Redis'
    name: str
    host: str
    port: int
    vhost: Optional[str] = None
    topicExchange: Optional[str] = None
    rpcExchange: Optional[str] = None
    ssl: Optional[bool] = False
    basePath: Optional[str] = None
    webPath: Optional[str] = None
    webPort: Optional[int] = None
    db: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    key: Optional[str] = None

class DeviceModel(BaseModel):
    name: str
    description: str
    author: str
    os: str
    board: Optional[Board]
    peripherals: List[Peripheral]
    connections: List[Dict[str, Any]]
    network: Optional[Network] = None
    broker: Optional[Broker] = None

from demol.lang.semantics import clear_validation_results

# Helper to load models
def load_hwd_model(path, mm):
    clear_validation_results()
    try:
        model = mm.model_from_file(path)
        return model
    except Exception as e:
        return None


@app.get("/api/boards", response_model=List[Board])
async def get_boards():
    mm = get_component_mm(skip_semantics=True)
    boards = []
    
    if os.path.exists(BOARD_MODEL_REPO_PATH):
        files = os.listdir(BOARD_MODEL_REPO_PATH)
        for filename in files:
            if filename.endswith(".hwd"):
                path = os.path.join(BOARD_MODEL_REPO_PATH, filename)
                model = load_hwd_model(path, mm)
                if model:
                    board_data = demol_to_json(model)
                    board_data["id"] = filename
                    with open(path, 'r') as f:
                        board_data["raw_content"] = f.read()
                    boards.append(board_data)
    
    return boards

@app.get("/api/peripherals", response_model=List[Peripheral])
async def get_peripherals():
    mm = get_component_mm(skip_semantics=True)
    peripherals = []
    
    if os.path.exists(PERIPHERAL_MODEL_REPO_PATH):
        files = os.listdir(PERIPHERAL_MODEL_REPO_PATH)
        for filename in files:
            if filename.endswith(".hwd"):
                path = os.path.join(PERIPHERAL_MODEL_REPO_PATH, filename)
                model = load_hwd_model(path, mm)
                if model:
                    periph_data = demol_to_json(model)
                    periph_data["id"] = filename
                    with open(path, 'r') as f:
                        periph_data["raw_content"] = f.read()
                    peripherals.append(periph_data)
    
    return peripherals


@app.post("/api/validate")
async def validate_model(model: DeviceModel):
    from demol.lang.semantics import get_validation_errors, get_validation_warnings, clear_validation_results
    import tempfile
    
    # 1. Generate DSL
    content = json_to_demol(model)
    
    # 2. Validate using DeMoL
    with tempfile.NamedTemporaryFile(suffix='.dev', mode='w', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    valid = False
    try:
        build_model(temp_path, skip_semantics=False)
        valid = True
    except Exception as e:
        print(f"Validation error: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    errors = get_validation_errors()
    warnings = get_validation_warnings()
    
    # Format results for frontend
    formatted_errors = [f"{e['type']}: {e['msg']}" for e in errors]
    formatted_warnings = [f"{w['type']}: {w['msg']}" for w in warnings]
    
    # If model_from_file failed but no semantic errors were collected, 
    # it might be a syntax error
    if not valid and not formatted_errors:
        formatted_errors.append(f"SyntaxError: The generated model is syntactically invalid.")

    return {
        "valid": valid and len(formatted_errors) == 0,
        "errors": formatted_errors,
        "warnings": formatted_warnings,
        "dsl": content
    }

@app.post("/api/export")
async def export_model(model: DeviceModel):
    content = json_to_demol(model)
    return {"content": content}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
