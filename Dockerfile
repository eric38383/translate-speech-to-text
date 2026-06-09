FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Note: All project files (including translate_transcripts.py and credentials)
# will be mounted via docker-compose volume at /app

# Default command (bash for interactive use)
CMD ["/bin/bash"]
