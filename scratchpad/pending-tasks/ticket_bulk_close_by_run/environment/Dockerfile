FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep jq && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages pytest-json-ctrf requests apideck-unify && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user
RUN mkdir -p /home/user/apideck_task && chmod 0755 /home/user/apideck_task

LABEL Author="generate-harbor-tasks"
LABEL Description="Apideck Issue Tracking bulk-close task environment with Python HTTP tooling for the unified API."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - extra apt packages: jq for shell-based JSON processing
#   - always required pip3 packages: pytest-json-ctrf
#   - extra pip3 packages: requests (used by initial- and final-state tests), apideck-unify (Python SDK)
#   - /home/user/apideck_task: working directory for the agent; logs are written to /home/user/apideck_task/output.log
