"""
Integração com Claude (Anthropic API) para interpretar exceções em texto livre
e convertê-las em regras JSON estruturadas para o motor de regras.

Fluxo:
  1. Usuário descreve a exceção em linguagem natural
  2. O sistema fornece contexto (salas, cursos, blocos disponíveis)
  3. Claude retorna JSON estruturado com a(s) regra(s) correspondente(s)
  4. O resultado é salvo em EXCECAO_SEMESTRE.PARAMETROS_JSON
"""
import json
import logging

import anthropic

from app.repositories import sala_repo, turma_repo

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Você é um assistente especializado em sistemas de ensalamento universitário.
Sua tarefa é converter descrições em linguagem natural de exceções/regras de
alocação de salas em um JSON estruturado.

## Regras disponíveis

Você deve retornar um objeto JSON com o campo "regra" sendo UMA das opções abaixo,
mais os parâmetros obrigatórios de cada regra. Retorne APENAS o JSON, sem explicações.

| regra | parâmetros obrigatórios |
|-------|------------------------|
| BLOCO_RESTRITO_PARA_CURSO | bloco_id (int), curso_id (int) |
| BLOCO_RESTRITO_PARA_TODOS_EXCETO_CURSO | bloco_id (int), curso_id (int) |
| SALA_RESERVADA_PARA_TURMA | sala_id (int), turma_id (int) |
| LIMITE_ALUNOS_BLOCO | bloco_id (int), max_alunos (int) |
| TIPO_SALA_PROIBIDO_CURSO | curso_id (int), tipo_sala (COMUM|LABORATORIO|INFORMATICA) |
| TIPO_SALA_EXCLUSIVO_CURSO | curso_id (int), tipo_sala (COMUM|LABORATORIO|INFORMATICA) |
| TURMA_FIXADA_EM_SALA | turma_id (int), sala_id (int) |

## Regras extras opcionais
- Inclua sempre o campo "motivo" (string curta) explicando a regra.
- Se a descrição gerar MÚLTIPLAS regras, retorne um array JSON de objetos.
- Se não for possível mapear para nenhuma regra conhecida, retorne:
  {"regra": "DESCONHECIDA", "descricao_original": "...", "motivo": "não mapeável"}

## Exemplo
Entrada: "Salas do bloco B não podem ser usadas pelo curso de medicina (id=3)"
Saída:
{"regra": "BLOCO_RESTRITO_PARA_CURSO", "bloco_id": 2, "curso_id": 3, "motivo": "curso de medicina não usa bloco B"}
"""


def _construir_contexto(semestre: str) -> str:
    """Monta texto com IDs de salas, blocos e cursos para guiar o modelo."""
    try:
        salas = sala_repo.listar_salas()
        prioridades = turma_repo.listar_prioridades_curso_bloco()

        blocos: dict[int, str] = {}
        for s in salas:
            blocos[s.bloco_id] = s.bloco_nome or str(s.bloco_id)

        linhas = [f"Semestre: {semestre}\n"]

        linhas.append("## Blocos disponíveis")
        for bid, bnome in sorted(blocos.items()):
            linhas.append(f"  id={bid}  nome={bnome}")

        linhas.append("\n## Salas disponíveis (amostra)")
        for s in salas[:30]:
            linhas.append(
                f"  id={s.id}  nome={s.nome}  bloco_id={s.bloco_id}"
                f"  tipo={s.tipo}  cap={s.capacidade}"
            )
        if len(salas) > 30:
            linhas.append(f"  ... e mais {len(salas) - 30} salas")

        cursos: dict[int, str] = {}
        for p in prioridades:
            cursos[p["curso_id"]] = p["curso_nome"]

        if cursos:
            linhas.append("\n## Cursos com prioridade cadastrada")
            for cid, cnome in sorted(cursos.items()):
                linhas.append(f"  id={cid}  nome={cnome}")

        return "\n".join(linhas)
    except Exception as e:
        logger.warning("Não foi possível carregar contexto do banco: %s", e)
        return f"Semestre: {semestre}\n(contexto de banco não disponível)"


def interpretar_excecao(
    descricao: str,
    semestre: str,
    model: str = "claude-opus-4-6",
) -> dict:
    """
    Envia a descrição em linguagem natural para Claude e retorna
    o(s) JSON(s) de regra(s) estruturado(s).

    Retorna um dict com:
        regras: list[dict]   → lista de regras (mesmo que seja uma só)
        status: str          → 'OK' | 'PENDENTE_REVISAO' | 'ERRO'
        raw_response: str    → resposta bruta do modelo
    """
    contexto = _construir_contexto(semestre)
    user_message = (
        f"Contexto do sistema:\n{contexto}\n\n"
        f"Exceção a mapear:\n{descricao}"
    )

    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
    except Exception as e:
        logger.error("Erro ao chamar Claude API: %s", e)
        return {
            "regras": [],
            "status": "ERRO",
            "raw_response": str(e),
        }

    # Tentar parsear o JSON retornado
    try:
        parsed = json.loads(raw)
        # Normalizar: sempre lista
        regras = parsed if isinstance(parsed, list) else [parsed]
        status = _avaliar_status(regras)
        return {"regras": regras, "status": status, "raw_response": raw}
    except json.JSONDecodeError:
        logger.warning("Claude retornou resposta não-JSON: %s", raw)
        return {
            "regras": [{"regra": "DESCONHECIDA", "descricao_original": descricao}],
            "status": "PENDENTE_REVISAO",
            "raw_response": raw,
        }


def _avaliar_status(regras: list[dict]) -> str:
    """Determina se as regras precisam de revisão humana."""
    from app.services.regra_engine import REGRAS_CONHECIDAS

    for r in regras:
        tipo = r.get("regra", "").upper()
        if tipo == "DESCONHECIDA" or tipo not in REGRAS_CONHECIDAS:
            return "PENDENTE_REVISAO"
    return "OK"
