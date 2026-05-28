# Multi-stage build for ParadoxEvoMQTT (paraevo daemon)
# Builds upstream tag v0.10 and packages a minimal runtime image.

FROM ubuntu:22.04 AS builder

ARG DEBIAN_FRONTEND=noninteractive
ARG PARAEVO_REF=main

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    make \
    gcc \
    libc6-dev \
    pkg-config \
    libzmq3-dev \
    libpaho-mqtt-dev \
    python3 \
    python3-yaml \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src

RUN git clone --depth 1 --branch ${PARAEVO_REF} https://github.com/darkusas/ParadoxEvoMQTT.git . \
 && make clean \
 && make BUILD='"RELEASE"'

FROM ubuntu:22.04 AS runtime

ARG DEBIAN_FRONTEND=noninteractive

ENV TZ=Europe/Vilnius
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    bash \
    libzmq5 \
    libpaho-mqtt1.3 \
    python3 \
    python3-yaml \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/paraevo

COPY --from=builder /src/paraevo /opt/paraevo/paraevo
COPY start_daemon.py /opt/paraevo/start_daemon.py

RUN chmod +x /opt/paraevo/start_daemon.py

ENTRYPOINT ["/opt/paraevo/start_daemon.py"]
