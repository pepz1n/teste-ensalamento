"""
Algoritmo de ensalamento com prioridades e exceções por semestre.

Prioridades:
  1. Turmas cujo curso tem afinidade de bloco definida (alocadas primeiro)
  2. Turmas com maior número de alunos (best-fit descendente)

Exceções suportadas:
  - SALA_INTERDITADA    : sala removida da pool neste semestre
  - CAPACIDADE_SALA     : capacidade efetiva da sala alterada
  - COMPARTILHAMENTO    : duas turmas dividem a mesma seção (num_alunos somados)
  - GENERICA            : regra JSON interpretada pelo motor de regras (regra_engine)
"""
from collections import defaultdict

from app.models.alocacao import Alocacao, ResultadoEnsalamento
from app.models.excecao import ExcecaoSemestre
from app.models.sala import Sala
from app.models.turma import Turma
from app.repositories import (
    alocacao_repo,
    excecao_repo,
    sala_repo,
    turma_repo,
)
from app.services.regra_engine import ContextoRegras, parsear_regras, sala_fixa_da_turma, sala_permitida_para_turma


def _aplicar_excecoes(
    salas: list[Sala],
    turmas: list[Turma],
    excecoes: list[ExcecaoSemestre],
) -> tuple[list[Sala], list[Turma]]:
    """
    Aplica as exceções do semestre sobre as listas de salas e turmas.
    Retorna as listas modificadas.
    """
    salas_interditadas: set[int] = set()
    capacidades_override: dict[int, int] = {}
    compartilhamentos: list[tuple[int, int]] = []

    for exc in excecoes:
        if exc.tipo == "SALA_INTERDITADA" and exc.sala_id:
            salas_interditadas.add(exc.sala_id)
        elif exc.tipo == "CAPACIDADE_SALA" and exc.sala_id and exc.nova_capacidade:
            capacidades_override[exc.sala_id] = exc.nova_capacidade
        elif exc.tipo == "COMPARTILHAMENTO" and exc.turma_id and exc.turma_parceira_id:
            compartilhamentos.append((exc.turma_id, exc.turma_parceira_id))

    # Remover salas interditadas e aplicar capacidades overrides
    salas_filtradas: list[Sala] = []
    for sala in salas:
        if sala.id in salas_interditadas:
            continue
        if sala.id in capacidades_override:
            sala = sala.model_copy(update={"capacidade_efetiva": capacidades_override[sala.id]})
        salas_filtradas.append(sala)

    # Aplicar compartilhamentos: somar alunos das turmas parceiras
    turma_por_id: dict[int, Turma] = {t.id: t for t in turmas}
    turmas_absorvidas: set[int] = set()

    for turma_id, parceira_id in compartilhamentos:
        if turma_id not in turma_por_id or parceira_id not in turma_por_id:
            continue
        turma_principal = turma_por_id[turma_id]
        turma_parceira = turma_por_id[parceira_id]
        soma = turma_principal.get_num_alunos_efetivo() + turma_parceira.get_num_alunos_efetivo()
        parceiras = list(turma_principal.turmas_parceiras_ids) + [parceira_id]
        turma_por_id[turma_id] = turma_principal.model_copy(
            update={"num_alunos_efetivo": soma, "turmas_parceiras_ids": parceiras}
        )
        turmas_absorvidas.add(parceira_id)

    turmas_efetivas = [t for tid, t in turma_por_id.items() if tid not in turmas_absorvidas]
    return salas_filtradas, turmas_efetivas


def _ordenar_turmas(turmas: list[Turma], cursos_com_prioridade: set[int]) -> list[Turma]:
    """
    Ordenação de prioridade:
      1. Turmas cujo curso tem afinidade de bloco (True > False)
      2. Número de alunos efetivo DESC (maiores primeiro)
    """
    return sorted(
        turmas,
        key=lambda t: (
            0 if t.curso_id in cursos_com_prioridade else 1,
            -t.get_num_alunos_efetivo(),
        ),
    )


def _melhor_sala(
    candidatas: list[Sala],
    turma: Turma,
    tipo_exigido: str | None,
    bloco_preferido: int | None,
    ctx_regras: ContextoRegras,
) -> Sala | None:
    """
    Best-fit: menor sala que ainda acomoda num_alunos, respeitando
    tipo, preferência de bloco e regras genéricas.
    """
    num_alunos = turma.get_num_alunos_efetivo()

    def _filtro(sala: Sala) -> bool:
        if sala.get_capacidade_efetiva() < num_alunos:
            return False
        if tipo_exigido and sala.tipo != tipo_exigido:
            return False
        permitida, _ = sala_permitida_para_turma(sala, turma, ctx_regras)
        return permitida

    aptas = [s for s in candidatas if _filtro(s)]
    if not aptas:
        return None

    # Priorizar salas no bloco preferido; dentro do grupo, menor capacidade
    aptas_no_bloco = [s for s in aptas if s.bloco_id == bloco_preferido] if bloco_preferido else []
    pool = aptas_no_bloco if aptas_no_bloco else aptas

    return min(pool, key=lambda s: s.get_capacidade_efetiva())


def gerar_ensalamento(semestre: str, limpar_anterior: bool = False) -> ResultadoEnsalamento:
    """
    Ponto de entrada principal do algoritmo.

    1. Carrega exceções → aplica sobre salas e turmas
    2. Ordena turmas por prioridade
    3. Aloca turma a turma via best-fit
    4. Persiste em FINALIDADE_ESPACO_ALOCADO
    5. Retorna ResultadoEnsalamento com sumário
    """
    if limpar_anterior:
        alocacao_repo.deletar_alocacoes(semestre)

    # --- Carregar dados ---
    excecoes = excecao_repo.listar_excecoes(semestre)
    salas_raw = sala_repo.listar_salas()
    turmas_raw = turma_repo.listar_turmas(semestre)
    prioridades = turma_repo.listar_prioridades_curso_bloco()

    # Mapas auxiliares
    curso_para_bloco: dict[int, int] = {p["curso_id"]: p["bloco_id"] for p in prioridades}
    cursos_com_prioridade: set[int] = set(curso_para_bloco.keys())

    # --- Aplicar exceções estruturadas (tipos fixos) ---
    salas, turmas = _aplicar_excecoes(salas_raw, turmas_raw, excecoes)

    # --- Carregar e parsear regras genéricas ---
    excecoes_genericas = excecao_repo.listar_excecoes_genericas(semestre)
    ctx_regras = parsear_regras(excecoes_genericas)

    # --- Ordenar turmas ---
    turmas = _ordenar_turmas(turmas, cursos_com_prioridade)

    # --- Mapear sala por id para lookup rápido ---
    sala_por_id: dict[int, Sala] = {s.id: s for s in salas}

    # --- Alocar ---
    ocupacao: dict[int, set[int]] = defaultdict(set)

    alocacoes: list[Alocacao] = []
    conflitos: list[dict] = []

    for turma in turmas:
        if not turma.horarios:
            conflitos.append({"turma_id": turma.id, "motivo": "sem horários cadastrados"})
            continue

        turma_totalmente_alocada = True

        # Verificar se a turma tem sala fixa por regra genérica
        sala_fixa_id = sala_fixa_da_turma(turma, ctx_regras)

        for horario in turma.horarios:
            if horario.id not in ocupacao:
                ocupacao[horario.id] = alocacao_repo.salas_ocupadas_no_horario(semestre, horario.id)

            # Se sala fixa, verificar disponibilidade antes de buscar
            if sala_fixa_id is not None:
                if sala_fixa_id in ocupacao[horario.id]:
                    turma_totalmente_alocada = False
                    conflitos.append(
                        {
                            "turma_id": turma.id,
                            "disciplina": turma.disciplina_nome,
                            "horario_id": horario.id,
                            "motivo": f"sala fixa {sala_fixa_id} já ocupada neste horário",
                        }
                    )
                    continue
                escolhida = sala_por_id.get(sala_fixa_id)
                if escolhida is None:
                    turma_totalmente_alocada = False
                    conflitos.append(
                        {
                            "turma_id": turma.id,
                            "disciplina": turma.disciplina_nome,
                            "horario_id": horario.id,
                            "motivo": f"sala fixa {sala_fixa_id} não encontrada ou interditada",
                        }
                    )
                    continue
            else:
                disponiveis = [s for s in salas if s.id not in ocupacao[horario.id]]
                bloco_pref = curso_para_bloco.get(turma.curso_id)
                escolhida = _melhor_sala(
                    disponiveis,
                    turma,
                    turma.tipo_sala_exigida,
                    bloco_pref,
                    ctx_regras,
                )

            if escolhida is None:
                turma_totalmente_alocada = False
                conflitos.append(
                    {
                        "turma_id": turma.id,
                        "disciplina": turma.disciplina_nome,
                        "horario_id": horario.id,
                        "motivo": "nenhuma sala disponível (capacidade, tipo ou regra genérica)",
                    }
                )
                continue

            ocupacao[horario.id].add(escolhida.id)
            alocacoes.append(
                Alocacao(
                    turma_id=turma.id,
                    sala_id=escolhida.id,
                    horario_id=horario.id,
                    semestre=semestre,
                )
            )

    # --- Persistir ---
    alocacao_repo.inserir_alocacoes(alocacoes)

    total_turmas = len(turmas)
    turmas_com_conflito = len({c["turma_id"] for c in conflitos})
    alocadas = total_turmas - turmas_com_conflito
    percentual = round(alocadas / total_turmas * 100, 1) if total_turmas else 0.0

    return ResultadoEnsalamento(
        semestre=semestre,
        total_turmas=total_turmas,
        alocadas=alocadas,
        conflitos=turmas_com_conflito,
        percentual_ocupacao=percentual,
        alocacoes=alocacoes,
        turmas_sem_sala=conflitos,
    )
