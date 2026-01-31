# Wiki Semantic Search MCP Server (HTTP/JSON-RPC)
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Expose HTTP port
EXPOSE 3000

# Run HTTP server
CMD ["python", "server.py"]
