# Stage 1: Build stage
FROM python:3.12-slim as build

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
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y software-properties-common \
 && add-apt-repository ppa:deadsnakes/ppa -y \
 && apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tzdata \
    vim \
 && ln -sf /usr/bin/python3.12 /usr/bin/python3 \
 && ln -sf /usr/bin/python3.12 /usr/bin/python

RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

ENV PATH="/service/app/.venv/bin:$PATH"

WORKDIR /service/app

COPY --from=build /service/app /service/app

#CMD [ "/bin/bash" ]
CMD ["/service/app/.venv/bin/python", "app.py"]
