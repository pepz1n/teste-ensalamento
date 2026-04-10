"""Repository para leitura de salas do Oracle."""
from app.db.connection import get_connection
from app.models.sala import Sala


def listar_salas(bloco_id: int | None = None) -> list[Sala]:
    """Retorna todas as salas, opcionalmente filtradas por bloco."""
    sql = """
        SELECT s.ID, s.NOME, s.CAPACIDADE, s.TIPO, s.BLOCO_ID, b.NOME AS BLOCO_NOME
        FROM SALA s
        JOIN BLOCO b ON b.ID = s.BLOCO_ID
        WHERE 1=1
    """
    params: dict = {}
    if bloco_id is not None:
        sql += " AND s.BLOCO_ID = :bloco_id"
        params["bloco_id"] = bloco_id
    sql += " ORDER BY b.NOME, s.NOME"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    return [
        Sala(
            id=row[0],
            nome=row[1],
            capacidade=row[2],
            tipo=row[3],
            bloco_id=row[4],
            bloco_nome=row[5],
        )
        for row in rows
    ]


def buscar_sala_por_id(sala_id: int) -> Sala | None:
    sql = """
        SELECT s.ID, s.NOME, s.CAPACIDADE, s.TIPO, s.BLOCO_ID, b.NOME AS BLOCO_NOME
        FROM SALA s
        JOIN BLOCO b ON b.ID = s.BLOCO_ID
        WHERE s.ID = :sala_id
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, {"sala_id": sala_id})
        row = cursor.fetchone()

    if row is None:
        return None
    return Sala(id=row[0], nome=row[1], capacidade=row[2], tipo=row[3], bloco_id=row[4], bloco_nome=row[5])
