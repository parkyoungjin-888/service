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
FROM python:3.12-slim as runtime

ENV PATH="/service/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    libgl1-mesa-glx \
    libglib2.0-0 \
    pkg-config \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /service/app

COPY --from=build /service/app /service/app

#CMD [ "/bin/bash" ]
CMD ["python3", "app.py"]
