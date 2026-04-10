from pydantic import BaseModel


class Sala(BaseModel):
    id: int
    nome: str
    capacidade: int
    tipo: str          # 'COMUM', 'LABORATORIO', 'INFORMATICA'
    bloco_id: int
    bloco_nome: str | None = None
    # Capacidade efetiva após aplicar exceção CAPACIDADE_SALA
    capacidade_efetiva: int | None = None

    def get_capacidade_efetiva(self) -> int:
        return self.capacidade_efetiva if self.capacidade_efetiva is not None else self.capacidade
