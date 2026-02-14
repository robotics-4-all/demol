from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import sys
import tarfile
import io

# Add project root to path to import demol
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from demol.lang import build_model, get_component_mm
from demol.transformations import (
    json_to_demol,
    demol_to_json,
    m2t_rpi,
    m2t_riot,
    m2t_docs,
    m2m_smauto,
    m2t_device_svg,
    m2t_infrastructure_svg,
)
from demol.definitions import BOARD_MODEL_REPO_PATH, PERIPHERAL_MODEL_REPO_PATH, POWER_SOURCE_MODEL_REPO_PATH
import tempfile

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
    status: Optional[str] = "essential"
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


class PowerSource(BaseModel):
    id: str
    name: str
    instanceName: Optional[str] = None
    nodeId: Optional[str] = None
    type: str
    pins: List[Pin]
    operational: Dict[str, Any]
    raw_content: Optional[str] = None


class Network(BaseModel):
    type: str  # 'WiFi' or 'Eth'
    ssid: Optional[str] = None
    password: Optional[str] = None
    address: Optional[str] = None
    channel: Optional[str] = None


class Broker(BaseModel):
    type: str  # 'MQTT', 'AMQP', 'Redis'
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
    powerSources: List[PowerSource] = []
    connections: List[Dict[str, Any]]
    network: Optional[Network] = None
    broker: Optional[Broker] = None


# Helper to load models
def load_hwd_model(path, mm):
    clear_validation_results()
    try:
        model = mm.model_from_file(path)
        return model
    except Exception:
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
                    with open(path, "r") as f:
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
                    with open(path, "r") as f:
                        periph_data["raw_content"] = f.read()
                    peripherals.append(periph_data)

    return peripherals


@app.get("/api/powersources", response_model=List[PowerSource])
async def get_powersources():
    mm = get_component_mm(skip_semantics=True)
    powersources = []

    if os.path.exists(POWER_SOURCE_MODEL_REPO_PATH):
        files = os.listdir(POWER_SOURCE_MODEL_REPO_PATH)
        for filename in files:
            if filename.endswith(".hwd"):
                path = os.path.join(POWER_SOURCE_MODEL_REPO_PATH, filename)
                model = load_hwd_model(path, mm)
                if model:
                    ps_data = demol_to_json(model)
                    ps_data["id"] = filename
                    with open(path, "r") as f:
                        ps_data["raw_content"] = f.read()
                    powersources.append(ps_data)

    return powersources


@app.post("/api/validate")
async def validate_model(model: DeviceModel):
    from demol.lang.semantics import get_validation_errors, get_validation_warnings, clear_validation_results
    import tempfile

    # 1. Generate DSL
    content = json_to_demol(model)

    # 2. Validate using DeMoL
    with tempfile.NamedTemporaryFile(suffix=".dev", mode="w", delete=False) as f:
        f.write(content)
        temp_path = f.name

    valid = False
    try:
        build_model(temp_path, skip_semantics=False)
        valid = True
    except Exception:
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
        formatted_errors.append("SyntaxError: The generated model is syntactically invalid.")

    return {
        "valid": valid and len(formatted_errors) == 0,
        "errors": formatted_errors,
        "warnings": formatted_warnings,
        "dsl": content,
    }


@app.post("/api/export")
async def export_model(model: DeviceModel):
    content = json_to_demol(model)
    return {"content": content}


def create_tarball(directory):
    """Create a tarball from a directory in memory"""
    file_obj = io.BytesIO()
    with tarfile.open(fileobj=file_obj, mode="w:gz") as tar:
        tar.add(directory, arcname=".")
    file_obj.seek(0)
    return file_obj


@app.post("/api/generate/docs")
async def generate_docs(model: DeviceModel):
    content = json_to_demol(model)
    with tempfile.TemporaryDirectory() as tmp_dir:
        with tempfile.NamedTemporaryFile(suffix=".dev", mode="w", delete=False) as f:
            f.write(content)
            temp_model_path = f.name
        try:
            dm = build_model(temp_model_path, skip_semantics=True)
            m2t_docs(dm, output_dir=tmp_dir)

            tarball = create_tarball(tmp_dir)
            filename = f"{dm.metadata.name}_docs.tar.gz"

            return StreamingResponse(
                tarball,
                media_type="application/x-gzip",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        except Exception:
            return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
        finally:
            if os.path.exists(temp_model_path):
                os.remove(temp_model_path)


@app.post("/api/generate/smauto")
async def generate_smauto(model: DeviceModel):
    content = json_to_demol(model)
    with tempfile.TemporaryDirectory() as tmp_dir:
        with tempfile.NamedTemporaryFile(suffix=".dev", mode="w", delete=False) as f:
            f.write(content)
            temp_model_path = f.name
        try:
            dm = build_model(temp_model_path, skip_semantics=True)
            m2m_smauto(dm, output_dir=tmp_dir)

            tarball = create_tarball(tmp_dir)
            filename = f"{dm.metadata.name}_smauto.tar.gz"

            return StreamingResponse(
                tarball,
                media_type="application/x-gzip",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        except Exception:
            return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
        finally:
            if os.path.exists(temp_model_path):
                os.remove(temp_model_path)


@app.post("/api/generate/svg")
async def generate_svg(model: DeviceModel):
    content = json_to_demol(model)
    with tempfile.TemporaryDirectory() as tmp_dir:
        with tempfile.NamedTemporaryFile(suffix=".dev", mode="w", delete=False) as f:
            f.write(content)
            temp_model_path = f.name
        try:
            dm = build_model(temp_model_path, skip_semantics=True)

            wiring_filename = os.path.join(tmp_dir, f"{dm.metadata.name}.svg")
            m2t_device_svg(dm, wiring_filename)

            infra_filename = os.path.join(tmp_dir, f"{dm.metadata.name}_infrastructure.svg")
            m2t_infrastructure_svg(dm, infra_filename)

            tarball = create_tarball(tmp_dir)
            filename = f"{dm.metadata.name}_svg.tar.gz"

            return StreamingResponse(
                tarball,
                media_type="application/x-gzip",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        except Exception:
            return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
        finally:
            if os.path.exists(temp_model_path):
                os.remove(temp_model_path)


@app.post("/api/generate/source")
@app.post("/api/generate/source/{platform}")
async def generate_source(model: DeviceModel, platform: Optional[str] = None):
    # 1. Determine platform
    if not platform:
        platform = model.os

    # Map OS to transformation
    platform_map = {"raspbian": "rpi", "riotos": "riot", "rpi": "rpi", "riot": "riot"}

    target_platform = platform_map.get(platform.lower())
    if not target_platform:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    # 2. Generate DSL
    content = json_to_demol(model)

    # 3. Create temp directory for generation
    with tempfile.TemporaryDirectory() as tmp_dir:
        with tempfile.NamedTemporaryFile(suffix=".dev", mode="w", delete=False) as f:
            f.write(content)
            temp_model_path = f.name

        try:
            # 4. Build model
            dm = build_model(temp_model_path, skip_semantics=True)

            # 5. Run transformation
            if target_platform == "rpi":
                m2t_rpi(dm, output_dir=tmp_dir)
            elif target_platform == "riot":
                m2t_riot(dm, output_dir=tmp_dir)

            tarball = create_tarball(tmp_dir)
            filename = f"{dm.metadata.name}_{target_platform}_source.tar.gz"

            return StreamingResponse(
                tarball,
                media_type="application/x-gzip",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        except Exception:
            return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
        finally:
            if os.path.exists(temp_model_path):
                os.remove(temp_model_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
