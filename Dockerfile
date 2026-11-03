FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt pyproject.toml ./
COPY demol/ ./demol/
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .[api]

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health').status==200 else 1)"

CMD ["uvicorn", "demol.api:app", "--host", "0.0.0.0", "--port", "8080"]
