# =====================================================================
# Stage 1: Build dependencies in isolated environment
# =====================================================================
FROM python:3.13-slim AS builder

WORKDIR /build

# Install dependencies required to compile C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# =====================================================================
# Stage 2: Minimal runtime image running the FastAPI platform
# =====================================================================
FROM python:3.13-slim AS runner

WORKDIR /app

# Install curl for health check validation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies compiled in builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Copy source code files
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
