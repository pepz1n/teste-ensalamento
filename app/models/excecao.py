from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator


TipoExcecao = Literal["SALA_INTERDITADA", "COMPARTILHAMENTO", "CAPACIDADE_SALA"]


class ExcecaoSemestre(BaseModel):
    id: int | None = None
    semestre: str
    tipo: TipoExcecao
    sala_id: int | None = None
    turma_id: int | None = None
    turma_parceira_id: int | None = None
    nova_capacidade: int | None = None
    observacao: str | None = None
    criado_em: datetime | None = None

    @model_validator(mode="after")
    def validar_campos_por_tipo(self) -> "ExcecaoSemestre":
        if self.tipo == "SALA_INTERDITADA" and self.sala_id is None:
            raise ValueError("SALA_INTERDITADA requer sala_id")
        if self.tipo == "COMPARTILHAMENTO" and (
            self.turma_id is None or self.turma_parceira_id is None
        ):
            raise ValueError("COMPARTILHAMENTO requer turma_id e turma_parceira_id")
        if self.tipo == "CAPACIDADE_SALA" and (
            self.sala_id is None or self.nova_capacidade is None
        ):
            raise ValueError("CAPACIDADE_SALA requer sala_id e nova_capacidade")
        return self


class ExcecaoCreate(BaseModel):
    semestre: str
    tipo: TipoExcecao
    sala_id: int | None = None
    turma_id: int | None = None
    turma_parceira_id: int | None = None
    nova_capacidade: int | None = None
    observacao: str | None = None
