# ------------------------------------------------------------
# Build stage: compile the mobotix thermal binary
# ------------------------------------------------------------
FROM ubuntu:focal-20211006 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libboost-all-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy SDK and build
ADD mobotix_sdk /build

RUN cd /build/eventstreamclient/lib/Linux && \
    ln -s libeventstreamclient.$(uname -m).a libeventstreamclient.a

RUN make -C /build/eventstreamclient/plugin-client/thermal-raw

# Strip the compiled binary to reduce size
RUN strip /build/eventstreamclient/plugin-client/thermal-raw/build/thermal-raw


# ------------------------------------------------------------
# Runtime stage: lightweight image with only runtime deps
# ------------------------------------------------------------
FROM waggle/plugin-base:1.1.1-base

ENV DEBIAN_FRONTEND=noninteractive

# Install only the runtime libraries and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    libboost-filesystem1.71.0 \
    libboost-program-options1.71.0 \
    curl \
 && apt-get clean && apt-get autoremove && apt-get autoclean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy the compiled binary from the builder stage
COPY --from=builder /build/eventstreamclient/plugin-client/thermal-raw/build/thermal-raw /thermal-raw

# Copy application source
COPY app /app/

ENTRYPOINT ["python3", "/app/main.py"]
