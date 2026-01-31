# Qdrant Init Container
# Runs once to populate the vector database with embeddings
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy init script
COPY init_collection.py .

# Default command
CMD ["python", "init_collection.py"]
