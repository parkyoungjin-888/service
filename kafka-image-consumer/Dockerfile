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
FROM python:3.12-slim

ENV PATH="/service/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y vim libgl1 libglib2.0-0 pkg-config

WORKDIR /service/app

COPY --from=build /service/app /service/app

#CMD [ "/bin/bash" ]
CMD ["python3", "app.py"]
