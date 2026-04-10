"""Repository para CRUD de exceções por semestre."""
from app.db.connection import get_connection
from app.models.excecao import ExcecaoCreate, ExcecaoSemestre


def listar_excecoes(semestre: str) -> list[ExcecaoSemestre]:
    sql = """
        SELECT ID, SEMESTRE, TIPO, SALA_ID, TURMA_ID, TURMA_PARCEIRA_ID,
               NOVA_CAPACIDADE, OBSERVACAO, CRIADO_EM
        FROM EXCECAO_SEMESTRE
        WHERE SEMESTRE = :semestre
        ORDER BY TIPO, ID
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, {"semestre": semestre})
        rows = cursor.fetchall()

    return [
        ExcecaoSemestre(
            id=row[0],
            semestre=row[1],
            tipo=row[2],
            sala_id=row[3],
            turma_id=row[4],
            turma_parceira_id=row[5],
            nova_capacidade=row[6],
            observacao=row[7],
            criado_em=row[8],
        )
        for row in rows
    ]


def criar_excecao(exc: ExcecaoCreate) -> int:
    sql = """
        INSERT INTO EXCECAO_SEMESTRE
            (SEMESTRE, TIPO, SALA_ID, TURMA_ID, TURMA_PARCEIRA_ID, NOVA_CAPACIDADE, OBSERVACAO)
        VALUES
            (:semestre, :tipo, :sala_id, :turma_id, :turma_parceira_id, :nova_capacidade, :observacao)
        RETURNING ID INTO :new_id
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        new_id_var = cursor.var(int)
        cursor.execute(
            sql,
            {
                "semestre": exc.semestre,
                "tipo": exc.tipo,
                "sala_id": exc.sala_id,
                "turma_id": exc.turma_id,
                "turma_parceira_id": exc.turma_parceira_id,
                "nova_capacidade": exc.nova_capacidade,
                "observacao": exc.observacao,
                "new_id": new_id_var,
            },
        )
        return int(new_id_var.getvalue()[0])


def deletar_excecao(excecao_id: int) -> bool:
    sql = "DELETE FROM EXCECAO_SEMESTRE WHERE ID = :id"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, {"id": excecao_id})
        return cursor.rowcount > 0
