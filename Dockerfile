# Local CodeRabbit - Docker Image
# AI-powered code review server

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    openai \
    fastapi \
    uvicorn[standard] \
    pydantic \
    watchdog \
    chromadb \
    sentence-transformers

# Copy application code
COPY scripts/ ./scripts/
COPY prompts.json ./prompts.json
COPY config.json ./config.json

# Copy .agent folder if exists (for context rules)
COPY .agent/ ./.agent/

# Expose API port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8765/api/health || exit 1

# Run the API server
CMD ["python", "scripts/api_server.py"]
