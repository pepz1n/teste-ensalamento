from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator


TipoExcecao = Literal["SALA_INTERDITADA", "COMPARTILHAMENTO", "CAPACIDADE_SALA", "GENERICA"]
StatusInterpretacao = Literal["OK", "PENDENTE_REVISAO", "ERRO"]


class ExcecaoSemestre(BaseModel):
    id: int | None = None
    semestre: str
    tipo: TipoExcecao
    sala_id: int | None = None
    turma_id: int | None = None
    turma_parceira_id: int | None = None
    nova_capacidade: int | None = None
    observacao: str | None = None
    # Campos para tipo GENERICA
    descricao_livre: str | None = None
    parametros_json: str | None = None          # JSON string da(s) regra(s)
    status_interpretacao: StatusInterpretacao = "OK"
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
        if self.tipo == "GENERICA" and self.descricao_livre is None and self.parametros_json is None:
            raise ValueError("GENERICA requer descricao_livre ou parametros_json")
        return self


class ExcecaoCreate(BaseModel):
    semestre: str
    tipo: TipoExcecao
    sala_id: int | None = None
    turma_id: int | None = None
    turma_parceira_id: int | None = None
    nova_capacidade: int | None = None
    observacao: str | None = None
    # Campos para tipo GENERICA
    descricao_livre: str | None = None
    parametros_json: str | None = None
    status_interpretacao: StatusInterpretacao = "OK"


class InterpretarRequest(BaseModel):
    semestre: str
    descricao: str
    salvar: bool = True   # Se True, persiste automaticamente após interpretar
