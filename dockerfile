# This Dockerfile installs system dependencies (including git),
# copies your requirements.txt, installs Python dependencies,
# then copies your source code.

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]