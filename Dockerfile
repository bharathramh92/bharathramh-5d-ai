FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Copy dependencies manifest
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir --extra-index-url https://pypi.org/simple -r requirements.txt

# Copy project source code
COPY . .

# Expose port 8000
EXPOSE 8000

# Entrypoint command
CMD ["python", "main.py"]
