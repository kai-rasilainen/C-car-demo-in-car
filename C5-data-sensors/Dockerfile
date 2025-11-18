FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache gcc musl-dev

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S python && \
    adduser -S sensors -u 1001 -G python

# Change ownership of app directory
RUN chown -R sensors:python /app
USER sensors

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import redis; r = redis.Redis(host='redis', port=6379); r.ping()"

# Start the sensor simulator
CMD ["python", "sensor_simulator.py"]