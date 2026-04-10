"""Repository para CRUD de exceções por semestre."""
from app.db.connection import get_connection
from app.models.excecao import ExcecaoCreate, ExcecaoSemestre


def listar_excecoes(semestre: str) -> list[ExcecaoSemestre]:
    sql = """
        SELECT ID, SEMESTRE, TIPO, SALA_ID, TURMA_ID, TURMA_PARCEIRA_ID,
               NOVA_CAPACIDADE, OBSERVACAO, DESCRICAO_LIVRE,
               PARAMETROS_JSON, STATUS_INTERPRETACAO, CRIADO_EM
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
            descricao_livre=row[8],
            parametros_json=row[9].read() if row[9] is not None else None,
            status_interpretacao=row[10] or "OK",
            criado_em=row[11],
        )
        for row in rows
    ]


def listar_excecoes_genericas(semestre: str) -> list[tuple[int, str, str]]:
    """Retorna (id, parametros_json, descricao_livre) apenas das exceções GENERICA com status OK."""
    sql = """
        SELECT ID, PARAMETROS_JSON, DESCRICAO_LIVRE
        FROM EXCECAO_SEMESTRE
        WHERE SEMESTRE = :semestre
          AND TIPO = 'GENERICA'
          AND STATUS_INTERPRETACAO = 'OK'
          AND PARAMETROS_JSON IS NOT NULL
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, {"semestre": semestre})
        rows = cursor.fetchall()

    return [
        (row[0], row[1].read() if row[1] is not None else "", row[2] or "")
        for row in rows
    ]


def criar_excecao(exc: ExcecaoCreate) -> int:
    sql = """
        INSERT INTO EXCECAO_SEMESTRE
            (SEMESTRE, TIPO, SALA_ID, TURMA_ID, TURMA_PARCEIRA_ID, NOVA_CAPACIDADE,
             OBSERVACAO, DESCRICAO_LIVRE, PARAMETROS_JSON, STATUS_INTERPRETACAO)
        VALUES
            (:semestre, :tipo, :sala_id, :turma_id, :turma_parceira_id, :nova_capacidade,
             :observacao, :descricao_livre, :parametros_json, :status_interpretacao)
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
                "descricao_livre": exc.descricao_livre,
                "parametros_json": exc.parametros_json,
                "status_interpretacao": exc.status_interpretacao,
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
