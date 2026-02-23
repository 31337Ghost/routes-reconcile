FROM python:3.12-alpine

ARG SUPERCRONIC_VERSION=v0.2.33
ARG TARGETARCH

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk add --no-cache ca-certificates curl bind-tools libc6-compat

RUN case "${TARGETARCH}" in \
        amd64) arch="amd64" ;; \
        arm64) arch="arm64" ;; \
        *) echo "Unsupported architecture: ${TARGETARCH}" && exit 1 ;; \
    esac \
    && curl -fsSLo /usr/local/bin/supercronic "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${arch}" \
    && chmod +x /usr/local/bin/supercronic \
    && /usr/local/bin/supercronic -version

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY crontab /etc/crontab

CMD ["/usr/local/bin/supercronic", "/etc/crontab"]
