# ─────────────────────────────────────────────────────
# llvm-tester/Dockerfile
# Source: CONTEXT.json → folder_structure.backend.containers.containers.llvm-tester
# Base: Ubuntu 22.04 with LLVM-17 (clang, opt, llc, llvm-as)
# ─────────────────────────────────────────────────────
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        wget \
        ca-certificates \
        gnupg \
        lsb-release \
    && wget -qO- https://apt.llvm.org/llvm-snapshot.gpg.key | gpg --dearmor -o /etc/apt/trusted.gpg.d/llvm.gpg \
    && echo "deb http://apt.llvm.org/jammy/ llvm-toolchain-jammy-17 main" \
       > /etc/apt/sources.list.d/llvm-17.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        clang-17 \
        llvm-17 \
        llvm-17-tools \
    && ln -sf /usr/bin/clang-17 /usr/bin/clang \
    && ln -sf /usr/bin/opt-17 /usr/bin/opt \
    && ln -sf /usr/bin/llc-17 /usr/bin/llc \
    && ln -sf /usr/bin/llvm-as-17 /usr/bin/llvm-as \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY docker-run.sh /workspace/docker-run.sh
RUN chmod +x /workspace/docker-run.sh

CMD ["/workspace/docker-run.sh"]
