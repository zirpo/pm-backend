# Use a lightweight Python base image
FROM python:3.11-slim-bookworm

# Set working directory inside the container
WORKDIR /app

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the application with Uvicorn
# Using --host 0.0.0.0 makes the server accessible from outside the container
# The --workers parameter can be adjusted based on CPU cores
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]