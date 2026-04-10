from datetime import datetime

from pydantic import BaseModel


class Alocacao(BaseModel):
    id: int | None = None
    turma_id: int
    sala_id: int
    horario_id: int
    semestre: str
    criado_em: datetime | None = None
    # Campos de exibição (joins)
    disciplina_nome: str | None = None
    curso_nome: str | None = None
    sala_nome: str | None = None
    bloco_nome: str | None = None
    dia_semana: str | None = None
    hora_inicio: str | None = None
    hora_fim: str | None = None
    num_alunos: int | None = None
    capacidade_sala: int | None = None


class ResultadoEnsalamento(BaseModel):
    semestre: str
    total_turmas: int
    alocadas: int
    conflitos: int
    percentual_ocupacao: float
    alocacoes: list[Alocacao]
    turmas_sem_sala: list[dict]
