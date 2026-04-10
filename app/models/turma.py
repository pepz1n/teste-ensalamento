from pydantic import BaseModel


class Horario(BaseModel):
    id: int
    dia_semana: str      # 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB'
    hora_inicio: str     # 'HH:MM'
    hora_fim: str        # 'HH:MM'


class Turma(BaseModel):
    id: int
    disciplina_id: int
    disciplina_nome: str | None = None
    curso_id: int
    curso_nome: str | None = None
    semestre: str
    num_alunos: int
    tipo_sala_exigida: str | None = None   # None = qualquer; 'LABORATORIO'; 'INFORMATICA'
    horarios: list[Horario] = []
    # Campos preenchidos ao aplicar exceção COMPARTILHAMENTO
    turmas_parceiras_ids: list[int] = []
    num_alunos_efetivo: int | None = None

    def get_num_alunos_efetivo(self) -> int:
        return self.num_alunos_efetivo if self.num_alunos_efetivo is not None else self.num_alunos
