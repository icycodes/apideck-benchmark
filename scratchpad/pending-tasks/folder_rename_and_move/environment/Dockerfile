FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf apideck-unify requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user
RUN mkdir -p /home/user/apideck_task

LABEL Author="generate-harbor-tasks"
LABEL Description="Apideck File Storage folder rename-and-move task environment with the apideck-unify Python SDK preinstalled."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - apideck-unify Python SDK for calling the Apideck Unified File Storage API
#   - requests Python package used by the verifier to call https://unify.apideck.com directly
#   - /home/user/apideck_task: project directory where the agent writes output.log
