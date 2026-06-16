FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep jq && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests apideck-unify && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user
RUN mkdir -p /home/user/myproject

LABEL Author="generate-harbor-tasks"
LABEL Description="Apideck Issue Tracking pagination task environment with the apideck-unify Python SDK preinstalled."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - extra apt packages: jq (handy for ad-hoc inspection of JSON responses during development)
#   - always required pip3 packages: pytest-json-ctrf
#   - requests: used by tests/test_final_state.py to verify the unified Issue Tracking API state
#   - apideck-unify: official Apideck Python SDK used by the executor to seed tickets and paginate
#   - /home/user/myproject: working directory where the executor places solution scripts and writes tickets.json
