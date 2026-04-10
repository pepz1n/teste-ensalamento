"""Entrypoint FastAPI — uvicorn main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.db.connection import close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_pool()


app = FastAPI(
    title="Sistema de Ensalamento Universitário",
    description=(
        "API para alocação automática de turmas em salas de aula. "
        "Prioriza turmas maiores e cursos com afinidade de bloco. "
        "Suporta exceções por semestre (interdições, compartilhamentos, capacidades variáveis)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")
