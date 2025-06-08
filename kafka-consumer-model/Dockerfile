# Stage 1: Build stage
FROM python:3.12-slim as build

RUN apt-get update && apt-get install -y vim

RUN pip install poetry==1.8.2

ENV POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /service/app

COPY . /service/app

RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-cache --no-root

# Stage 2: Runtime stage
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    vim && \
    ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /service/app

COPY --from=build /service/app /service/app

CMD ["python", "app.py"]
