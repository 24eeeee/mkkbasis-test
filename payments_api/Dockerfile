# pull official base image
FROM python:3.12-slim

# set working directory
WORKDIR /usr/src

# install system dependencies
RUN apt-get update && apt-get clean

# install python dependencies
RUN pip install --upgrade pip
RUN pip install poetry
COPY poetry.lock .
COPY pyproject.toml .
RUN poetry install --no-root

# add app
COPY payments_api ./payments_api
COPY shared ./payments_api