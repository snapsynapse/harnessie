FROM python:3.12-slim

# curl fetches uv for the in-sandbox verifier form; bubblewrap is the OS
# sandbox `harnessie verify` needs to run its checks confined inside this
# container. Whether the container runtime lets bubblewrap create namespaces
# decides if that form can score; see the example README.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates bubblewrap \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
