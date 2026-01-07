import uuid
import os
import shutil
import io
import zipfile

from fastapi import FastAPI, File, UploadFile, status, HTTPException, Security, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from demol.lang import build_model
from demol.transformations import demol_to_json

API_KEY = os.getenv("API_KEY", "API_KEY")

api_keys = [
    API_KEY
]

api = FastAPI()

api_key_header = APIKeyHeader(name="X-API-Key")

def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    if api_key_header in api_keys:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )


api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMP_DIR = '/tmp/smauto'


if not os.path.exists(TMP_DIR):
    os.mkdir(TMP_DIR)


@api.post("/validate")
async def validate_model(file: UploadFile = File(...),
                         api_key: str = Security(get_api_key)):
    """
    Validates a DeMoL model file (.dev or .hwd).
    """
    u_id = uuid.uuid4().hex[0:8]
    _, ext = os.path.splitext(file.filename)
    if not ext:
        ext = ".dev" # Default extension
    fpath = os.path.join(TMP_DIR, f'model-{u_id}{ext}')

    try:
        with open(fpath, 'wb') as f:
            shutil.copyfileobj(file.file, f)

        build_model(fpath)
        return {"status": "success", "message": "Model validation successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    finally:
        if os.path.exists(fpath):
            os.remove(fpath)


@api.post("/generate")
async def generate_code(file: UploadFile = File(...),
                        target: str = Form(...),
                        api_key: str = Security(get_api_key)):
    """
    Generates code or documentation from a DeMoL model file.
    Supported targets: 'plantuml', 'json'.
    'rpi' and 'docs' are not yet implemented.
    """
    if target not in ['plantuml', 'json', 'rpi', 'docs']:
        raise HTTPException(status_code=400,
                            detail="Invalid target. Supported: 'plantuml', 'json', 'rpi', 'docs'")

    if target in ['rpi', 'docs']:
        raise HTTPException(status_code=501,
                            detail=f"Generation for target '{target}' is not implemented yet.")

    u_id = uuid.uuid4().hex[0:8]
    _, ext = os.path.splitext(file.filename)
    if not ext:
        ext = ".dev" # Default extension
    model_path = os.path.join(TMP_DIR, f'model-{u_id}{ext}')
    output_dir = os.path.join(TMP_DIR, f'output-{u_id}')
    os.makedirs(output_dir, exist_ok=True)

    try:
        with open(model_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)

        model = build_model(model_path)

        file_extension = ""
        content = ""

        if target == 'plantuml':
            # content = m2t_device_plantuml(model)
            # file_extension = "puml"
            raise HTTPException(status_code=501, detail="PlantUML generation not implemented")
        elif target == 'json':
            import json
            content = json.dumps(demol_to_json(model), indent=4)
            file_extension = "json"

        model_name = model.metadata.name.strip('"')
        output_filename = f"{model_name}.{file_extension}"
        with open(os.path.join(output_dir, output_filename), "w") as f:
            f.write(content)

        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(os.path.join(output_dir, output_filename), arcname=output_filename)

        zip_io.seek(0)

        return StreamingResponse(zip_io,
                                 media_type="application/zip",
                                 headers={"Content-Disposition": f"attachment; filename=generated_{target}_{model_name}.zip"})

    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Code generation failed: {str(e)}")
    finally:
        if os.path.exists(model_path):
            os.remove(model_path)
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
