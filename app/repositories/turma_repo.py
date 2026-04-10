"""Repository para leitura de turmas e horários do Oracle."""
from app.db.connection import get_connection
from app.models.turma import Horario, Turma


def listar_turmas(semestre: str) -> list[Turma]:
    """Retorna turmas do semestre com seus horários."""
    sql_turmas = """
        SELECT
            t.ID,
            t.DISCIPLINA_ID,
            d.NOME      AS DISCIPLINA_NOME,
            d.CURSO_ID,
            c.NOME      AS CURSO_NOME,
            t.SEMESTRE,
            t.NUM_ALUNOS,
            t.TIPO_SALA_EXIGIDA
        FROM TURMA t
        JOIN DISCIPLINA d ON d.ID = t.DISCIPLINA_ID
        JOIN CURSO c      ON c.ID = d.CURSO_ID
        WHERE t.SEMESTRE = :semestre
        ORDER BY t.NUM_ALUNOS DESC
    """
    sql_horarios = """
        SELECT th.HORARIO_ID, h.DIA_SEMANA, h.HORA_INICIO, h.HORA_FIM
        FROM TURMA_HORARIO th
        JOIN HORARIO h ON h.ID = th.HORARIO_ID
        WHERE th.TURMA_ID = :turma_id
        ORDER BY h.DIA_SEMANA, h.HORA_INICIO
    """

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql_turmas, {"semestre": semestre})
        turma_rows = cursor.fetchall()

        turmas: list[Turma] = []
        for row in turma_rows:
            cursor.execute(sql_horarios, {"turma_id": row[0]})
            horario_rows = cursor.fetchall()
            horarios = [
                Horario(id=h[0], dia_semana=h[1], hora_inicio=str(h[2]), hora_fim=str(h[3]))
                for h in horario_rows
            ]
            turmas.append(
                Turma(
                    id=row[0],
                    disciplina_id=row[1],
                    disciplina_nome=row[2],
                    curso_id=row[3],
                    curso_nome=row[4],
                    semestre=row[5],
                    num_alunos=row[6],
                    tipo_sala_exigida=row[7],
                    horarios=horarios,
                )
            )

    return turmas


def listar_prioridades_curso_bloco() -> list[dict]:
    """Retorna mapeamento curso_id → bloco_id com prioridade."""
    sql = """
        SELECT cbp.CURSO_ID, c.NOME AS CURSO_NOME,
               cbp.BLOCO_ID, b.NOME AS BLOCO_NOME,
               cbp.PRIORIDADE
        FROM CURSO_BLOCO_PRIORIDADE cbp
        JOIN CURSO c ON c.ID = cbp.CURSO_ID
        JOIN BLOCO b ON b.ID = cbp.BLOCO_ID
        ORDER BY cbp.PRIORIDADE, c.NOME
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()

    return [
        {
            "curso_id": row[0],
            "curso_nome": row[1],
            "bloco_id": row[2],
            "bloco_nome": row[3],
            "prioridade": row[4],
        }
        for row in rows
    ]


def upsert_prioridade_curso_bloco(curso_id: int, bloco_id: int, prioridade: int = 1) -> None:
    sql = """
        MERGE INTO CURSO_BLOCO_PRIORIDADE dst
        USING (SELECT :curso_id AS CURSO_ID, :bloco_id AS BLOCO_ID FROM DUAL) src
        ON (dst.CURSO_ID = src.CURSO_ID AND dst.BLOCO_ID = src.BLOCO_ID)
        WHEN MATCHED THEN UPDATE SET dst.PRIORIDADE = :prioridade
        WHEN NOT MATCHED THEN INSERT (CURSO_ID, BLOCO_ID, PRIORIDADE)
             VALUES (:curso_id, :bloco_id, :prioridade)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, {"curso_id": curso_id, "bloco_id": bloco_id, "prioridade": prioridade})
