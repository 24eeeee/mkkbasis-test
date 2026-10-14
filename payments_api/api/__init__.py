import toolz
from fastapi import FastAPI

from . import payments


def create_app() -> FastAPI:
    return toolz.pipe(
        FastAPI(),
        payments.bootstrap,
    )
