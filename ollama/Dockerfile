FROM ollama/ollama:latest

# Pre-download DeepSeek-Coder-V2 at build time
# This ensures the model is ready immediately on container start
# Build: docker build -t ollama:coderabbit -f ollama/Dockerfile ./ollama

WORKDIR /app

# Start Ollama server, wait for startup, pull model, then stop
# The model will be cached in the volume for runtime
RUN ollama serve & \
    sleep 15 && \
    ollama pull deepseek-coder-v2 && \
    ollama pull qwen2.5-coder && \
    pkill -f "ollama serve"

EXPOSE 11434

CMD ["serve"]
