FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* ./
RUN uv pip install --system --no-cache . || uv pip install --system --no-cache \
    fastapi "uvicorn[standard]" sqlalchemy pydantic pydantic-settings jinja2 \
    apscheduler httpx python-multipart

COPY app ./app
COPY scripts ./scripts

# o banco vive em /data, que precisa existir antes de o SQLAlchemy tentar abrir o arquivo
RUN mkdir -p /data
VOLUME ["/data"]

# banco fica fora da imagem; em PaaS o volume ou o servico gerenciado prove
ENV DATABASE_URL=sqlite:////data/radar.db
ENV LINK_TIMEOUT_MS=5000

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
