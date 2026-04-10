"""Rotas FastAPI do sistema de ensalamento."""
import json

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.alocacao import Alocacao, ResultadoEnsalamento
from app.models.excecao import ExcecaoCreate, ExcecaoSemestre, InterpretarRequest
from app.models.sala import Sala
from app.models.turma import Turma
from app.repositories import alocacao_repo, excecao_repo, sala_repo, turma_repo
from app.services.interpretador_ia import interpretar_excecao
from app.services.scheduler import gerar_ensalamento

router = APIRouter()


# ---------------------------------------------------------------------------
# Salas
# ---------------------------------------------------------------------------

@router.get("/salas", response_model=list[Sala], summary="Listar salas")
def listar_salas(bloco_id: int | None = Query(default=None, description="Filtrar por bloco")):
    return sala_repo.listar_salas(bloco_id=bloco_id)


# ---------------------------------------------------------------------------
# Turmas
# ---------------------------------------------------------------------------

@router.get("/turmas", response_model=list[Turma], summary="Listar turmas do semestre")
def listar_turmas(semestre: str = Query(..., description="Ex: 2024.1")):
    return turma_repo.listar_turmas(semestre)


# ---------------------------------------------------------------------------
# Ensalamento
# ---------------------------------------------------------------------------

class GerарRequest(BaseModel):
    semestre: str
    limpar_anterior: bool = False


@router.post("/ensalamento/gerar", response_model=ResultadoEnsalamento, summary="Gerar ensalamento")
def gerar(req: GerарRequest):
    """
    Executa o algoritmo de ensalamento e insere os resultados em
    FINALIDADE_ESPACO_ALOCADO. Respeita as exceções cadastradas para o semestre.
    """
    return gerar_ensalamento(req.semestre, limpar_anterior=req.limpar_anterior)


@router.get("/ensalamento", response_model=list[Alocacao], summary="Grade do semestre")
def grade(semestre: str = Query(..., description="Ex: 2024.1")):
    return alocacao_repo.listar_alocacoes(semestre)


@router.get(
    "/ensalamento/conflitos",
    summary="Turmas sem sala alocada",
)
def conflitos(semestre: str = Query(..., description="Ex: 2024.1")):
    """
    Retorna turmas que não foram alocadas em nenhuma sala.
    Executa o algoritmo em modo simulação (sem persistir).
    """
    resultado = gerar_ensalamento(semestre, limpar_anterior=False)
    return {"semestre": semestre, "conflitos": resultado.turmas_sem_sala}


@router.delete("/ensalamento/{semestre}", summary="Limpar alocações do semestre")
def limpar(semestre: str):
    removidos = alocacao_repo.deletar_alocacoes(semestre)
    return {"semestre": semestre, "registros_removidos": removidos}


# ---------------------------------------------------------------------------
# Exceções por semestre
# ---------------------------------------------------------------------------

@router.get(
    "/excecoes",
    response_model=list[ExcecaoSemestre],
    summary="Listar exceções do semestre",
)
def listar_excecoes(semestre: str = Query(..., description="Ex: 2024.1")):
    return excecao_repo.listar_excecoes(semestre)


@router.post(
    "/excecoes",
    response_model=dict,
    summary="Cadastrar exceção",
    status_code=201,
)
def criar_excecao(exc: ExcecaoCreate):
    """
    Tipos disponíveis:
    - **SALA_INTERDITADA**: requer `sala_id`
    - **COMPARTILHAMENTO**: requer `turma_id` e `turma_parceira_id`
    - **CAPACIDADE_SALA**: requer `sala_id` e `nova_capacidade`
    """
    new_id = excecao_repo.criar_excecao(exc)
    return {"id": new_id, "mensagem": "Exceção cadastrada com sucesso"}


@router.delete("/excecoes/{excecao_id}", summary="Remover exceção")
def deletar_excecao(excecao_id: int):
    removido = excecao_repo.deletar_excecao(excecao_id)
    if not removido:
        raise HTTPException(status_code=404, detail="Exceção não encontrada")
    return {"mensagem": "Exceção removida"}


@router.post(
    "/excecoes/interpretar",
    summary="Interpretar exceção em linguagem natural via IA",
    status_code=201,
)
def interpretar(req: InterpretarRequest):
    """
    Recebe uma descrição em texto livre de uma exceção/restrição e usa IA
    (Claude) para converter em regra(s) JSON estruturada(s).

    Se `salvar=true`, persiste automaticamente na tabela EXCECAO_SEMESTRE.

    **Exemplos de descrição:**
    - "Salas do bloco B não podem ser usadas pelo curso de Medicina"
    - "A turma 42 deve obrigatoriamente usar o laboratório de química (sala 7)"
    - "Turmas com mais de 40 alunos não cabem nas salas do bloco A por questões acústicas"
    """
    resultado = interpretar_excecao(req.descricao, req.semestre)

    if resultado["status"] == "ERRO":
        raise HTTPException(status_code=502, detail=f"Erro na IA: {resultado['raw_response']}")

    ids_salvos: list[int] = []
    if req.salvar:
        for regra in resultado["regras"]:
            exc = ExcecaoCreate(
                semestre=req.semestre,
                tipo="GENERICA",
                descricao_livre=req.descricao,
                parametros_json=json.dumps(regra, ensure_ascii=False),
                status_interpretacao=resultado["status"],
            )
            ids_salvos.append(excecao_repo.criar_excecao(exc))

    return {
        "semestre": req.semestre,
        "descricao_original": req.descricao,
        "regras_interpretadas": resultado["regras"],
        "status": resultado["status"],
        "ids_salvos": ids_salvos,
        "aviso": (
            "Exceção marcada como PENDENTE_REVISAO — revise antes de gerar o ensalamento."
            if resultado["status"] == "PENDENTE_REVISAO" else None
        ),
    }


# ---------------------------------------------------------------------------
# Prioridades curso → bloco
# ---------------------------------------------------------------------------

@router.get("/prioridades", summary="Listar afinidades curso-bloco")
def listar_prioridades():
    return turma_repo.listar_prioridades_curso_bloco()


class PrioridadeRequest(BaseModel):
    curso_id: int
    bloco_id: int
    prioridade: int = 1


@router.post("/prioridades", summary="Configurar afinidade curso-bloco", status_code=201)
def configurar_prioridade(req: PrioridadeRequest):
    turma_repo.upsert_prioridade_curso_bloco(req.curso_id, req.bloco_id, req.prioridade)
    return {"mensagem": "Prioridade configurada"}
