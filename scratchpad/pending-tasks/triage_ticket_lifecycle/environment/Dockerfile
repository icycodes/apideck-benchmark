FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --break-system-packages \
        pytest-json-ctrf \
        requests \
        apideck-unify && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user
RUN mkdir -p /home/user/apideck_task && chmod 0755 /home/user/apideck_task

LABEL Author="generate-harbor-tasks"
LABEL Description="Apideck Unify task environment with the apideck-unify Python SDK preinstalled for Issue Tracking operations against the configured GitHub connector."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - apideck-unify (official Apideck Unify Python SDK) for Issue Tracking calls
#   - requests for direct REST verification against unify.apideck.com
#   - /home/user/apideck_task: working directory for the task and the resulting output.log
