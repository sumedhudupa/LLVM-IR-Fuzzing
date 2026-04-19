# ─────────────────────────────────────────────────────
# llm-mutator/Dockerfile
# Source: CONTEXT.json → folder_structure.backend.containers.llm-mutator
# Base: Python 3.11-slim; adding LLVM for validity filtering
# ─────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Install LLVM-17 and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        ca-certificates \
        gnupg \
        lsb-release \
    && wget -qO- https://apt.llvm.org/llvm-snapshot.gpg.key | gpg --dearmor -o /etc/apt/trusted.gpg.d/llvm.gpg \
    && echo "deb http://apt.llvm.org/bookworm/ llvm-toolchain-bookworm-17 main" \
       > /etc/apt/sources.list.d/llvm-17.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        clang-17 \
        llvm-17 \
        llvm-17-tools \
    && ln -sf /usr/bin/clang-17 /usr/bin/clang \
    && ln -sf /usr/bin/opt-17 /usr/bin/opt \
    && ln -sf /usr/bin/llvm-as-17 /usr/bin/llvm-as \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /workspace

# Install deps first (cache-friendly layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# Default: run the FastAPI server for API endpoints (Step 8 from CONTEXT tasks)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

