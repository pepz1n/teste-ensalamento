"""
CLI do sistema de ensalamento.

Uso:
    python -m cli.commands <comando> [opções]
"""
import json
import sys

import click

from app.models.excecao import ExcecaoCreate
from app.repositories import alocacao_repo, excecao_repo, sala_repo, turma_repo
from app.services.interpretador_ia import interpretar_excecao
from app.services.scheduler import gerar_ensalamento


@click.group()
def cli():
    """Sistema de Ensalamento Universitário."""


# ---------------------------------------------------------------------------
# Ensalamento
# ---------------------------------------------------------------------------

@cli.command("gerar")
@click.option("--semestre", required=True, help="Semestre (ex: 2024.1)")
@click.option("--limpar-anterior", is_flag=True, default=False, help="Remove alocações existentes antes de gerar")
def cmd_gerar(semestre: str, limpar_anterior: bool):
    """Executa o algoritmo de ensalamento e persiste no Oracle."""
    click.echo(f"Gerando ensalamento para {semestre}...")
    resultado = gerar_ensalamento(semestre, limpar_anterior=limpar_anterior)
    click.echo(f"\n{'='*50}")
    click.echo(f"  Semestre          : {resultado.semestre}")
    click.echo(f"  Total de turmas   : {resultado.total_turmas}")
    click.echo(f"  Alocadas          : {resultado.alocadas}")
    click.echo(f"  Conflitos         : {resultado.conflitos}")
    click.echo(f"  Aproveitamento    : {resultado.percentual_ocupacao}%")
    click.echo(f"{'='*50}")
    if resultado.turmas_sem_sala:
        click.echo("\nTurmas sem sala:")
        for c in resultado.turmas_sem_sala:
            click.echo(f"  - Turma {c['turma_id']} ({c.get('disciplina', 'N/A')}): {c['motivo']}")


@cli.command("listar")
@click.option("--semestre", required=True, help="Semestre (ex: 2024.1)")
@click.option("--bloco", default=None, help="Filtrar por nome do bloco")
def cmd_listar(semestre: str, bloco: str | None):
    """Lista a grade de ensalamento do semestre."""
    alocacoes = alocacao_repo.listar_alocacoes(semestre)
    if bloco:
        alocacoes = [a for a in alocacoes if a.bloco_nome and bloco.upper() in a.bloco_nome.upper()]

    if not alocacoes:
        click.echo("Nenhuma alocação encontrada.")
        return

    click.echo(f"\n{'Disciplina':<35} {'Curso':<20} {'Sala':<15} {'Bloco':<10} {'Dia':<5} {'Início':<8} {'Fim':<8} {'Alunos':>6} {'Cap':>5}")
    click.echo("-" * 115)
    for a in alocacoes:
        click.echo(
            f"{(a.disciplina_nome or ''):<35} "
            f"{(a.curso_nome or ''):<20} "
            f"{(a.sala_nome or ''):<15} "
            f"{(a.bloco_nome or ''):<10} "
            f"{(a.dia_semana or ''):<5} "
            f"{(a.hora_inicio or ''):<8} "
            f"{(a.hora_fim or ''):<8} "
            f"{(a.num_alunos or 0):>6} "
            f"{(a.capacidade_sala or 0):>5}"
        )
    click.echo(f"\nTotal: {len(alocacoes)} alocações")


@cli.command("conflitos")
@click.option("--semestre", required=True, help="Semestre (ex: 2024.1)")
def cmd_conflitos(semestre: str):
    """Mostra turmas que não conseguiram ser alocadas."""
    resultado = gerar_ensalamento(semestre, limpar_anterior=False)
    if not resultado.turmas_sem_sala:
        click.echo("Nenhum conflito encontrado.")
        return
    click.echo(f"\nConflitos no semestre {semestre}:")
    for c in resultado.turmas_sem_sala:
        click.echo(f"  Turma {c['turma_id']} ({c.get('disciplina', 'N/A')}) — {c['motivo']}")


@cli.command("limpar")
@click.option("--semestre", required=True, help="Semestre (ex: 2024.1)")
@click.confirmation_option(prompt=f"Isso removerá todas as alocações do semestre. Continuar?")
def cmd_limpar(semestre: str):
    """Remove todas as alocações de aula do semestre."""
    removidos = alocacao_repo.deletar_alocacoes(semestre)
    click.echo(f"{removidos} alocações removidas para o semestre {semestre}.")


# ---------------------------------------------------------------------------
# Exceções
# ---------------------------------------------------------------------------

@cli.group("excecao")
def cmd_excecao():
    """Gerenciar exceções por semestre."""


@cmd_excecao.command("listar")
@click.option("--semestre", required=True)
def exc_listar(semestre: str):
    """Lista as exceções cadastradas para o semestre."""
    excecoes = excecao_repo.listar_excecoes(semestre)
    if not excecoes:
        click.echo("Nenhuma exceção cadastrada.")
        return
    for e in excecoes:
        partes = [f"[{e.id}] {e.tipo}"]
        if e.sala_id:
            partes.append(f"sala_id={e.sala_id}")
        if e.turma_id:
            partes.append(f"turma_id={e.turma_id}")
        if e.turma_parceira_id:
            partes.append(f"parceira_id={e.turma_parceira_id}")
        if e.nova_capacidade:
            partes.append(f"nova_cap={e.nova_capacidade}")
        if e.observacao:
            partes.append(f'obs="{e.observacao}"')
        click.echo("  " + " | ".join(partes))


@cmd_excecao.command("adicionar")
@click.option("--semestre", required=True)
@click.option("--tipo", required=True, type=click.Choice(["SALA_INTERDITADA", "COMPARTILHAMENTO", "CAPACIDADE_SALA"]))
@click.option("--sala-id", type=int, default=None)
@click.option("--turma-id", type=int, default=None)
@click.option("--turma-parceira-id", type=int, default=None)
@click.option("--nova-capacidade", type=int, default=None)
@click.option("--observacao", default=None)
def exc_adicionar(
    semestre: str,
    tipo: str,
    sala_id: int | None,
    turma_id: int | None,
    turma_parceira_id: int | None,
    nova_capacidade: int | None,
    observacao: str | None,
):
    """Cadastra uma exceção para o semestre."""
    try:
        exc = ExcecaoCreate(
            semestre=semestre,
            tipo=tipo,
            sala_id=sala_id,
            turma_id=turma_id,
            turma_parceira_id=turma_parceira_id,
            nova_capacidade=nova_capacidade,
            observacao=observacao,
        )
        new_id = excecao_repo.criar_excecao(exc)
        click.echo(f"Exceção cadastrada com ID {new_id}.")
    except ValueError as e:
        click.echo(f"Erro de validação: {e}", err=True)
        sys.exit(1)


@cmd_excecao.command("remover")
@click.option("--id", "excecao_id", required=True, type=int)
def exc_remover(excecao_id: int):
    """Remove uma exceção pelo ID."""
    removido = excecao_repo.deletar_excecao(excecao_id)
    if removido:
        click.echo(f"Exceção {excecao_id} removida.")
    else:
        click.echo(f"Exceção {excecao_id} não encontrada.", err=True)
        sys.exit(1)


@cmd_excecao.command("interpretar")
@click.option("--semestre", required=True, help="Semestre (ex: 2024.1)")
@click.option(
    "--descricao",
    required=True,
    help='Descreva a exceção em português (ex: "Salas do bloco B não podem ter turmas de medicina")',
)
@click.option(
    "--salvar/--nao-salvar",
    default=True,
    help="Salvar automaticamente no banco após interpretar",
)
def exc_interpretar(semestre: str, descricao: str, salvar: bool):
    """
    Usa IA (Claude) para interpretar uma exceção em linguagem natural
    e convertê-la em regra JSON estruturada.

    Exemplos:
    \b
    excecao interpretar --semestre 2024.1 \\
        --descricao "Salas do bloco B não podem ser usadas pelo curso de Medicina"

    excecao interpretar --semestre 2024.1 \\
        --descricao "A turma 42 deve obrigatoriamente usar a sala 7 (lab de química)"

    excecao interpretar --semestre 2024.1 \\
        --descricao "Turmas com mais de 40 alunos não cabem no bloco A" \\
        --nao-salvar
    """
    click.echo(f"Interpretando exceção para {semestre}...")
    resultado = interpretar_excecao(descricao, semestre)

    if resultado["status"] == "ERRO":
        click.echo(f"Erro na IA: {resultado['raw_response']}", err=True)
        sys.exit(1)

    click.echo(f"\nStatus: {resultado['status']}")
    click.echo("\nRegras interpretadas:")
    for i, regra in enumerate(resultado["regras"], 1):
        click.echo(f"  [{i}] {json.dumps(regra, ensure_ascii=False, indent=4)}")

    if resultado["status"] == "PENDENTE_REVISAO":
        click.echo(
            "\nAVISO: A IA nao teve certeza sobre o mapeamento. "
            "Revise as regras antes de gerar o ensalamento."
        )

    if salvar:
        ids: list[int] = []
        for regra in resultado["regras"]:
            exc = ExcecaoCreate(
                semestre=semestre,
                tipo="GENERICA",
                descricao_livre=descricao,
                parametros_json=json.dumps(regra, ensure_ascii=False),
                status_interpretacao=resultado["status"],
            )
            new_id = excecao_repo.criar_excecao(exc)
            ids.append(new_id)
        click.echo(f"\nSalvo com ID(s): {ids}")
    else:
        click.echo("\nNão salvo (use --salvar para persistir).")


# ---------------------------------------------------------------------------
# Prioridades
# ---------------------------------------------------------------------------

@cli.command("prioridade")
@click.option("--curso-id", required=True, type=int)
@click.option("--bloco-id", required=True, type=int)
@click.option("--nivel", default=1, type=int, help="1=alta, maior=menor prioridade")
def cmd_prioridade(curso_id: int, bloco_id: int, nivel: int):
    """Configura afinidade de um curso para um bloco."""
    turma_repo.upsert_prioridade_curso_bloco(curso_id, bloco_id, nivel)
    click.echo(f"Prioridade configurada: curso {curso_id} → bloco {bloco_id} (nível {nivel}).")


if __name__ == "__main__":
    cli()
