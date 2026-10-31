FROM python:3.13-slim

ARG SUPERCRONIC_VERSION=v0.2.49
ARG SUPERCRONIC_SHA1SUM=e63c11a9726b775a6a11801e81af4f3fb926aa68
ADD https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64 /usr/local/bin/supercronic
RUN echo "${SUPERCRONIC_SHA1SUM}  /usr/local/bin/supercronic" | sha1sum -c - \
    && chmod +x /usr/local/bin/supercronic

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY holger/ ./holger/
COPY crontab .

ENV PYTHONUNBUFFERED=1 \
    DATA_DIR=/data
VOLUME /data

# The reporter container overrides this with: supercronic /app/crontab
CMD ["python", "-m", "holger.collector"]
