# Stage 1: Build stage
FROM python:3.12-slim as build

# Install dependencies for building
RUN apt-get update && apt-get install -y vim

# Configure Poetry
ENV POETRY_VERSION=1.8.2
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache

# Install poetry separated from system interpreter
RUN python3 -m venv $POETRY_VENV \
	&& $POETRY_VENV/bin/pip install -U pip setuptools \
	&& $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

# Add `poetry` to PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

WORKDIR /service/app

# Install dependencies
COPY ./common /common
COPY . /service/app
RUN rm -rf ./common
RUN poetry install --no-interaction --no-cache --no-root

# Stage 2: Runtime stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y vim

# Copy the poetry environment and the application
COPY --from=build /opt/poetry-venv /opt/poetry-venv
COPY --from=build /service/app /service/app

# Add `poetry` to PATH
ENV PATH="${PATH}:/opt/poetry-venv/bin"

# Set the PYTHONPATH to use the poetry venv
ENV PYTHONPATH="/opt/poetry-venv/lib/python3.12/site-packages"

WORKDIR /service/app

# Set the CMD to run the application
# CMD [ "/bin/bash" ]
CMD [ "/opt/poetry-venv/bin/poetry", "run", "python3", "app.py" ]
