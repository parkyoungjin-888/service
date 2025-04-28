# Stage 1: Build stage
FROM bitnami/spark:3.5.5 as build

USER root

RUN apt-get update && apt-get install -y vim

RUN pip install poetry==1.8.2

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /service/app

COPY . /service/app

RUN poetry install --no-interaction --no-cache --no-root

# Stage 2: Runtime stage
FROM bitnami/spark:3.5.5

USER root

ENV PATH="/opt/bitnami/spark/.venv/bin:$PATH"
COPY --from=build /service/app/.venv /opt/bitnami/spark/.venv

COPY app.py /opt/bitnami/spark/submit/app.py

RUN adduser --disabled-password --gecos '' --uid 1000 sparkuser && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl vim && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/bitnami/spark/tmp /opt/bitnami/spark/add_jars && \
    cd /opt/bitnami/spark/add_jars && \
    curl -LO https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.12.1/commons-pool2-2.12.1.jar && \
    curl -LO https://repo1.maven.org/maven2/org/mongodb/spark/mongo-spark-connector_2.12/10.2.1/mongo-spark-connector_2.12-10.2.1.jar && \
    curl -LO https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.5/spark-sql-kafka-0-10_2.12-3.5.5.jar && \
    curl -LO https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.5.1/kafka-clients-3.5.1.jar && \
    curl -LO https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.5/spark-token-provider-kafka-0-10_2.12-3.5.5.jar

RUN chown -R sparkuser:sparkuser /opt/bitnami/spark

USER sparkuser
