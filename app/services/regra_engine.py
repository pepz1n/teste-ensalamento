"""
Motor de regras para exceções genéricas (tipo GENERICA).

Cada exceção genérica armazena um JSON com o campo "regra" que define
o tipo de restrição, mais parâmetros específicos.

Regras disponíveis
------------------
BLOCO_RESTRITO_PARA_CURSO
    Turmas de um curso específico não podem usar salas de um bloco.
    params: bloco_id (int), curso_id (int)

BLOCO_RESTRITO_PARA_TODOS_EXCETO_CURSO
    Somente turmas de um curso específico podem usar salas de um bloco.
    params: bloco_id (int), curso_id (int)

SALA_RESERVADA_PARA_TURMA
    Uma sala fica exclusiva para uma turma específica (pré-reserva).
    params: sala_id (int), turma_id (int)

LIMITE_ALUNOS_BLOCO
    Salas de um bloco só podem receber turmas com até N alunos.
    params: bloco_id (int), max_alunos (int)

TIPO_SALA_PROIBIDO_CURSO
    Um curso não pode receber determinado tipo de sala.
    params: curso_id (int), tipo_sala (str)

TIPO_SALA_EXCLUSIVO_CURSO
    Um curso só pode receber um determinado tipo de sala.
    params: curso_id (int), tipo_sala (str)

TURMA_FIXADA_EM_SALA
    Uma turma deve obrigatoriamente ser alocada em uma sala específica.
    params: turma_id (int), sala_id (int)
"""
import json
import logging
from dataclasses import dataclass, field

from app.models.sala import Sala
from app.models.turma import Turma

logger = logging.getLogger(__name__)

# ── Tipos de regras reconhecidas ─────────────────────────────────────────────

REGRAS_CONHECIDAS = {
    "BLOCO_RESTRITO_PARA_CURSO",
    "BLOCO_RESTRITO_PARA_TODOS_EXCETO_CURSO",
    "SALA_RESERVADA_PARA_TURMA",
    "LIMITE_ALUNOS_BLOCO",
    "TIPO_SALA_PROIBIDO_CURSO",
    "TIPO_SALA_EXCLUSIVO_CURSO",
    "TURMA_FIXADA_EM_SALA",
}


@dataclass
class RegraGenerica:
    excecao_id: int
    tipo_regra: str
    params: dict
    descricao: str = ""


@dataclass
class ContextoRegras:
    """Pré-processado pelo motor a partir das regras genéricas."""
    # bloco_id → set de curso_id proibidos
    blocos_restritos_por_curso: dict[int, set[int]] = field(default_factory=dict)
    # bloco_id → curso_id exclusivo (apenas este curso pode usar o bloco)
    blocos_exclusivos_para_curso: dict[int, int] = field(default_factory=dict)
    # turma_id → sala_id reservada
    turmas_com_sala_reservada: dict[int, int] = field(default_factory=dict)
    # bloco_id → max_alunos
    limite_alunos_por_bloco: dict[int, int] = field(default_factory=dict)
    # curso_id → set de tipos de sala proibidos
    tipos_proibidos_por_curso: dict[int, set[str]] = field(default_factory=dict)
    # curso_id → tipo de sala exclusivo
    tipo_exclusivo_por_curso: dict[int, str] = field(default_factory=dict)
    # turma_id → sala_id fixa obrigatória
    turmas_fixadas: dict[int, int] = field(default_factory=dict)
    # regras não reconhecidas (para log/auditoria)
    desconhecidas: list[dict] = field(default_factory=list)


def parsear_regras(excecoes_json: list[tuple[int, str, str]]) -> ContextoRegras:
    """
    Recebe lista de (excecao_id, parametros_json, descricao_livre) e
    constrói o ContextoRegras.
    """
    ctx = ContextoRegras()

    for excecao_id, parametros_json, descricao in excecoes_json:
        try:
            params = json.loads(parametros_json) if parametros_json else {}
        except json.JSONDecodeError:
            logger.warning("Exceção %s tem JSON inválido — ignorada.", excecao_id)
            continue

        tipo_regra = params.get("regra", "").upper()

        if tipo_regra not in REGRAS_CONHECIDAS:
            ctx.desconhecidas.append({"excecao_id": excecao_id, "params": params, "descricao": descricao})
            logger.warning("Regra desconhecida '%s' na exceção %s.", tipo_regra, excecao_id)
            continue

        try:
            _aplicar_regra_no_contexto(ctx, tipo_regra, params, excecao_id)
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Erro ao processar exceção %s (%s): %s", excecao_id, tipo_regra, e)

    return ctx


def _aplicar_regra_no_contexto(
    ctx: ContextoRegras, tipo_regra: str, params: dict, excecao_id: int
) -> None:
    if tipo_regra == "BLOCO_RESTRITO_PARA_CURSO":
        bloco_id = int(params["bloco_id"])
        curso_id = int(params["curso_id"])
        ctx.blocos_restritos_por_curso.setdefault(bloco_id, set()).add(curso_id)

    elif tipo_regra == "BLOCO_RESTRITO_PARA_TODOS_EXCETO_CURSO":
        bloco_id = int(params["bloco_id"])
        curso_id = int(params["curso_id"])
        ctx.blocos_exclusivos_para_curso[bloco_id] = curso_id

    elif tipo_regra == "SALA_RESERVADA_PARA_TURMA":
        sala_id = int(params["sala_id"])
        turma_id = int(params["turma_id"])
        ctx.turmas_com_sala_reservada[turma_id] = sala_id

    elif tipo_regra == "LIMITE_ALUNOS_BLOCO":
        bloco_id = int(params["bloco_id"])
        max_alunos = int(params["max_alunos"])
        # Se já há limite, usa o mais restritivo
        if bloco_id not in ctx.limite_alunos_por_bloco or ctx.limite_alunos_por_bloco[bloco_id] > max_alunos:
            ctx.limite_alunos_por_bloco[bloco_id] = max_alunos

    elif tipo_regra == "TIPO_SALA_PROIBIDO_CURSO":
        curso_id = int(params["curso_id"])
        tipo_sala = str(params["tipo_sala"]).upper()
        ctx.tipos_proibidos_por_curso.setdefault(curso_id, set()).add(tipo_sala)

    elif tipo_regra == "TIPO_SALA_EXCLUSIVO_CURSO":
        curso_id = int(params["curso_id"])
        tipo_sala = str(params["tipo_sala"]).upper()
        ctx.tipo_exclusivo_por_curso[curso_id] = tipo_sala

    elif tipo_regra == "TURMA_FIXADA_EM_SALA":
        turma_id = int(params["turma_id"])
        sala_id = int(params["sala_id"])
        ctx.turmas_fixadas[turma_id] = sala_id


def sala_permitida_para_turma(
    sala: Sala,
    turma: Turma,
    ctx: ContextoRegras,
) -> tuple[bool, str | None]:
    """
    Verifica se uma sala pode ser usada por uma turma segundo as regras genéricas.
    Retorna (permitida, motivo_da_rejeicao).
    """
    # 1. Sala reservada para outra turma
    if sala.id in ctx.turmas_com_sala_reservada.values():
        turma_dona = next(
            (tid for tid, sid in ctx.turmas_com_sala_reservada.items() if sid == sala.id),
            None,
        )
        if turma_dona != turma.id:
            return False, f"sala reservada para turma {turma_dona}"

    # 2. Bloco restrito para o curso desta turma
    proibidos = ctx.blocos_restritos_por_curso.get(sala.bloco_id, set())
    if turma.curso_id in proibidos:
        return False, f"bloco {sala.bloco_id} restrito para curso {turma.curso_id}"

    # 3. Bloco exclusivo para outro curso
    exclusivo_curso = ctx.blocos_exclusivos_para_curso.get(sala.bloco_id)
    if exclusivo_curso is not None and exclusivo_curso != turma.curso_id:
        return False, f"bloco {sala.bloco_id} exclusivo para curso {exclusivo_curso}"

    # 4. Limite de alunos no bloco
    max_alunos = ctx.limite_alunos_por_bloco.get(sala.bloco_id)
    if max_alunos is not None and turma.get_num_alunos_efetivo() > max_alunos:
        return False, f"bloco {sala.bloco_id} limita {max_alunos} alunos, turma tem {turma.get_num_alunos_efetivo()}"

    # 5. Tipo de sala proibido para o curso
    tipos_proibidos = ctx.tipos_proibidos_por_curso.get(turma.curso_id, set())
    if sala.tipo in tipos_proibidos:
        return False, f"tipo '{sala.tipo}' proibido para curso {turma.curso_id}"

    # 6. Tipo de sala exclusivo para o curso
    tipo_exclusivo = ctx.tipo_exclusivo_por_curso.get(turma.curso_id)
    if tipo_exclusivo is not None and sala.tipo != tipo_exclusivo:
        return False, f"curso {turma.curso_id} só aceita salas do tipo '{tipo_exclusivo}'"

    return True, None


def sala_fixa_da_turma(turma: Turma, ctx: ContextoRegras) -> int | None:
    """Retorna sala_id fixa obrigatória para a turma, ou None."""
    return ctx.turmas_fixadas.get(turma.id) or ctx.turmas_com_sala_reservada.get(turma.id)
