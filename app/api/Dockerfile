FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install fastapi uvicorn

# Copy the demol package
COPY demol /app/demol

# Copy the API code
COPY app/api /app/api

# Set PYTHONPATH to include the root /app so imports work
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run the API
CMD ["python", "api/main.py"]
