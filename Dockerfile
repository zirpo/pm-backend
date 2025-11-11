# Use a lightweight Python base image
FROM python:3.11-slim-bookworm

# Set working directory inside the container
WORKDIR /app

# Set default port
# Use ARG to allow build-time override, and ENV to set the runtime default
ARG DEFAULT_PORT=8000
ENV PORT=${DEFAULT_PORT}

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port defined by the environment variable
EXPOSE $PORT

# Command to run the application with Uvicorn
# This uses sh -c to allow the $PORT environment variable to be expanded
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1"]