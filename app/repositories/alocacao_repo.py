"""Repository para INSERT e consulta de FINALIDADE_ESPACO_ALOCADO."""
from app.db.connection import get_connection
from app.models.alocacao import Alocacao
from config import settings


def inserir_alocacoes(alocacoes: list[Alocacao]) -> int:
    """Insere em batch na tabela FINALIDADE_ESPACO_ALOCADO. Retorna qtd inserida."""
    if not alocacoes:
        return 0

    sql = """
        INSERT INTO FINALIDADE_ESPACO_ALOCADO
            (ID_FINALIDADE, TURMA_ID, SALA_ID, HORARIO_ID, SEMESTRE)
        VALUES
            (:id_finalidade, :turma_id, :sala_id, :horario_id, :semestre)
    """
    data = [
        {
            "id_finalidade": settings.id_finalidade_aula,
            "turma_id": a.turma_id,
            "sala_id": a.sala_id,
            "horario_id": a.horario_id,
            "semestre": a.semestre,
        }
        for a in alocacoes
    ]

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(sql, data)
        return cursor.rowcount


def listar_alocacoes(semestre: str) -> list[Alocacao]:
    """Retorna grade completa do semestre com dados de exibição."""
    sql = """
        SELECT
            fea.ID,
            fea.TURMA_ID,
            fea.SALA_ID,
            fea.HORARIO_ID,
            fea.SEMESTRE,
            d.NOME      AS DISCIPLINA_NOME,
            c.NOME      AS CURSO_NOME,
            s.NOME      AS SALA_NOME,
            b.NOME      AS BLOCO_NOME,
            h.DIA_SEMANA,
            h.HORA_INICIO,
            h.HORA_FIM,
            t.NUM_ALUNOS,
            s.CAPACIDADE
        FROM FINALIDADE_ESPACO_ALOCADO fea
        JOIN TURMA t      ON t.ID      = fea.TURMA_ID
        JOIN DISCIPLINA d ON d.ID      = t.DISCIPLINA_ID
        JOIN CURSO c      ON c.ID      = d.CURSO_ID
        JOIN SALA s       ON s.ID      = fea.SALA_ID
        JOIN BLOCO b      ON b.ID      = s.BLOCO_ID
        JOIN HORARIO h    ON h.ID      = fea.HORARIO_ID
        WHERE fea.SEMESTRE = :semestre
          AND fea.ID_FINALIDADE = :id_finalidade
        ORDER BY b.NOME, s.NOME, h.DIA_SEMANA, h.HORA_INICIO
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, {"semestre": semestre, "id_finalidade": settings.id_finalidade_aula})
        rows = cursor.fetchall()

    return [
        Alocacao(
            id=row[0],
            turma_id=row[1],
            sala_id=row[2],
            horario_id=row[3],
            semestre=row[4],
            disciplina_nome=row[5],
            curso_nome=row[6],
            sala_nome=row[7],
            bloco_nome=row[8],
            dia_semana=str(row[9]) if row[9] else None,
            hora_inicio=str(row[10]) if row[10] else None,
            hora_fim=str(row[11]) if row[11] else None,
            num_alunos=row[12],
            capacidade_sala=row[13],
        )
        for row in rows
    ]


def deletar_alocacoes(semestre: str) -> int:
    """Remove todas as alocações de 'aula' do semestre. Retorna qtd removida."""
    sql = """
        DELETE FROM FINALIDADE_ESPACO_ALOCADO
        WHERE SEMESTRE = :semestre
          AND ID_FINALIDADE = :id_finalidade
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, {"semestre": semestre, "id_finalidade": settings.id_finalidade_aula})
        return cursor.rowcount


def salas_ocupadas_no_horario(semestre: str, horario_id: int) -> set[int]:
    """Retorna IDs das salas já alocadas para um dado horário/semestre."""
    sql = """
        SELECT SALA_ID FROM FINALIDADE_ESPACO_ALOCADO
        WHERE SEMESTRE = :semestre AND HORARIO_ID = :horario_id
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, {"semestre": semestre, "horario_id": horario_id})
        return {row[0] for row in cursor.fetchall()}
