# Python version
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application (using uvicorn for FastAPI)
# This will be overridden by the command in docker-compose.yml for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 