# REST API

The DeMoL API provides REST endpoints for validating models and generating code. The API is built with FastAPI and secured with API keys.

## Running the API

### Docker (Recommended)

Start the full stack (API on port 8000 + Frontend on port 5173):

```sh
./start.sh
```

### From Source

```sh
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Authentication

All API requests must include a valid API key in the `X-API-Key` header.

## Endpoints

### `POST /validate`

Validates a DeMoL model file (`.dev` or `.hwd`).

- **Request:** `multipart/form-data`
  - `file`: The model file to validate.
- **Example Request:**
  ```bash
  curl -X POST "http://localhost:8000/validate" \
       -H "X-API-Key: YOUR_API_KEY" \
       -F "file=@/path/to/your/model.dev"
  ```
- **Success Response (`200 OK`):**
  ```json
  {
    "status": "success",
    "message": "Model validation successful"
  }
  ```
- **Error Response (`400 Bad Request`):**
  ```json
  {
    "detail": "Validation error: ..."
  }
  ```

### `POST /generate`

Generates code or documentation from a DeMoL model file.

- **Request:** `multipart/form-data`
  - `file`: The model file to generate code from.
  - `target`: The generation target.
- **Supported Targets:**
  - `plantuml`: Generates a PlantUML diagram of the device.
- **Example Request:**
  ```bash
  curl -X POST "http://localhost:8000/generate" \
       -H "X-API-Key: YOUR_API_KEY" \
       -F "file=@/path/to/your/model.dev" \
       -F "target=plantuml" \
       --output generated_code.zip
  ```
- **Success Response (`200 OK`):**
  A zip file containing the generated artifact(s) is returned.
- **Error Response:**
  - `400 Bad Request`: If the target is invalid.
  - `501 Not Implemented`: If the target is valid but not yet implemented (e.g., `rpi`, `docs`).
  - `500 Internal Server Error`: If code generation fails.
