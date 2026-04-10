# Documentação do Sistema de Ensalamento Universitário

## Sumário

1. [Contexto e Motivação](#1-contexto-e-motivação)
2. [Fase de Planejamento](#2-fase-de-planejamento)
3. [Decisões de Arquitetura](#3-decisões-de-arquitetura)
4. [O que foi implementado](#4-o-que-foi-implementado)
5. [Estrutura de Arquivos](#5-estrutura-de-arquivos)
6. [Banco de Dados Oracle](#6-banco-de-dados-oracle)
7. [Algoritmo de Ensalamento](#7-algoritmo-de-ensalamento)
8. [Sistema de Exceções](#8-sistema-de-exceções)
9. [API REST](#9-api-rest)
10. [Interface de Linha de Comando (CLI)](#10-interface-de-linha-de-comando-cli)
11. [Integração com IA](#11-integração-com-ia)
12. [Como executar](#12-como-executar)

---

## 1. Contexto e Motivação

O projeto nasceu da necessidade de um sistema que automatize o **ensalamento universitário**, ou seja, a alocação de turmas em salas de aula. A faculdade possui:

- Múltiplos **blocos** (prédios/pavilhões)
- Diversas **salas** com diferentes capacidades e tipos (comum, laboratório, informática)
- Vários **cursos** e **disciplinas**
- **Turmas** com número variável de alunos e horários pré-definidos
- Um banco de dados **Oracle** já existente com essas informações

O sistema precisava:
1. Ler os dados do Oracle já existente
2. Aplicar um algoritmo de alocação inteligente com prioridades
3. Inserir os resultados diretamente na tabela `FINALIDADE_ESPACO_ALOCADO`
4. Suportar variações e exceções que ocorrem a cada semestre
5. Lidar com situações imprevisíveis que ainda não foram catalogadas

---

## 2. Fase de Planejamento

### 2.1 Levantamento de Requisitos

O planejamento começou com uma série de perguntas feitas ao responsável pelo projeto para entender o escopo real. As respostas definiram o caminho técnico:

**Linguagem:** Python foi escolhido pela facilidade com algoritmos de otimização e pela maturidade do driver Oracle (`python-oracledb`).

**Interface:** API REST + CLI. A API permite integração futura com frontends ou outros sistemas. A CLI permite uso direto no terminal por técnicos.

**Banco de dados:** As tabelas principais já existiam no Oracle. O sistema precisava apenas inserir na tabela `FINALIDADE_ESPACO_ALOCADO` usando o campo `ID_FINALIDADE` para indicar que a finalidade é "aula".

**Prioridades do algoritmo:**
- Turmas maiores alocadas primeiro (garantia de sala adequada)
- Cursos com afinidade a blocos específicos têm preferência

**Exceções por semestre:**
- Salas interditadas (reforma, problemas estruturais)
- Compartilhamento de disciplinas entre cursos (Curso X e Y na mesma turma)
- Capacidade de sala alterada temporariamente
- Situações imprevisíveis ainda não catalogadas

### 2.2 Descoberta da Tabela de Alocação

Durante o planejamento foi identificado que a tabela de destino se chama `FINALIDADE_ESPACO_ALOCADO` e possui um campo `ID_FINALIDADE` que referencia o tipo de uso do espaço — no caso do sistema de ensalamento, o valor aponta para o registro "aula" na tabela de finalidades.

### 2.3 Problema das Exceções Não Previstas

Em um segundo momento, surgiu a questão: *"Como o sistema pode lidar com exceções que ainda não foram mapeadas?"*

Isso levou ao desenho de uma segunda camada no sistema — um motor de regras genéricas com suporte a interpretação via Inteligência Artificial — descrita em detalhes na seção 8.

---

## 3. Decisões de Arquitetura

### Stack tecnológica

| Componente | Tecnologia | Justificativa |
|---|---|---|
| Linguagem | Python 3.10+ | Algoritmos, ecossistema Oracle, clareza |
| API REST | FastAPI | Documentação automática (Swagger), tipagem forte, async |
| Driver Oracle | python-oracledb | Substituto moderno do cx_Oracle, mantido pela Oracle |
| Validação | Pydantic v2 | Tipagem declarativa, validação automática |
| CLI | Click | Interface de terminal robusta e composável |
| IA | Anthropic Claude API | Interpretação de linguagem natural para regras |

### Padrão de projeto

O projeto segue o padrão **Repository + Service Layer**:

```
API / CLI
    └── Service (lógica de negócio, algoritmo)
            └── Repository (acesso ao banco Oracle)
                    └── Models (estruturas de dados Pydantic)
```

Isso garante que:
- A lógica de negócio fica isolada dos detalhes de banco
- É possível testar o algoritmo sem um Oracle real
- Futuras mudanças no schema Oracle afetam apenas os repositórios

---

## 4. O que foi implementado

### Commit 1 — Sistema base

Implementação completa do sistema de ensalamento com:

- Pool de conexão Oracle
- Modelos Pydantic para todas as entidades
- Repositórios para leitura/escrita no Oracle
- Algoritmo de ensalamento com prioridades
- 11 endpoints REST
- 7 comandos CLI
- DDL para as duas tabelas novas necessárias

### Commit 2 — Exceções genéricas + IA

Extensão do sistema para lidar com situações não previstas:

- Novo tipo de exceção `GENERICA` com JSON de regras
- Motor de regras com 7 tipos de restrições estruturadas
- Integração com Claude API para interpretar texto livre
- Endpoint e comando CLI para interpretação
- Script de migração para bancos já existentes

---

## 5. Estrutura de Arquivos

```
teste-ensalamento/
│
├── main.py                          # Entrypoint FastAPI (uvicorn main:app)
├── config.py                        # Leitura de variáveis de ambiente (.env)
├── requirements.txt                 # Dependências Python
├── .env.example                     # Template de configuração
│
├── app/
│   ├── db/
│   │   └── connection.py            # Pool de conexão Oracle (get_connection)
│   │
│   ├── models/                      # Estruturas de dados (Pydantic)
│   │   ├── sala.py                  # Sala: id, nome, capacidade, tipo, bloco_id
│   │   ├── turma.py                 # Turma + Horario: dados da turma e seus slots
│   │   ├── excecao.py               # ExcecaoSemestre, ExcecaoCreate, InterpretarRequest
│   │   └── alocacao.py              # Alocacao + ResultadoEnsalamento
│   │
│   ├── repositories/                # Acesso direto ao Oracle (SQL puro)
│   │   ├── sala_repo.py             # SELECT em SALA com JOIN em BLOCO
│   │   ├── turma_repo.py            # SELECT em TURMA + TURMA_HORARIO + prioridades
│   │   ├── excecao_repo.py          # CRUD em EXCECAO_SEMESTRE
│   │   └── alocacao_repo.py         # INSERT/SELECT/DELETE em FINALIDADE_ESPACO_ALOCADO
│   │
│   ├── services/                    # Lógica de negócio
│   │   ├── scheduler.py             # Algoritmo principal de ensalamento
│   │   ├── regra_engine.py          # Motor de regras para exceções genéricas
│   │   └── interpretador_ia.py      # Integração com Claude API
│   │
│   └── api/
│       └── routes.py                # Todos os endpoints FastAPI
│
├── cli/
│   └── commands.py                  # Todos os comandos Click
│
└── sql/
    ├── create_excecao_semestre.sql   # DDL completo (instalação nova)
    └── migration_add_generica.sql    # ALTER TABLE para bancos existentes
```

---

## 6. Banco de Dados Oracle

### Tabelas existentes (não modificadas)

O sistema lê dessas tabelas, que já existiam no Oracle da faculdade:

| Tabela | Uso no sistema |
|---|---|
| `SALA` | Salas com capacidade, tipo e bloco |
| `BLOCO` | Prédios/blocos do campus |
| `TURMA` | Turmas com disciplina, semestre e número de alunos |
| `DISCIPLINA` | Disciplinas vinculadas a cursos |
| `CURSO` | Cursos acadêmicos |
| `HORARIO` | Slots de horário (dia + hora início/fim) |
| `TURMA_HORARIO` | Relação N:N entre turma e horários |
| `FINALIDADE_ESPACO_ALOCADO` | **Destino das alocações geradas** |
| `FINALIDADE` | Tipos de uso do espaço (inclui "aula") |

### Tabelas criadas pelo sistema

**`EXCECAO_SEMESTRE`** — Variações e restrições por semestre:

```sql
CREATE TABLE EXCECAO_SEMESTRE (
    ID                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    SEMESTRE             VARCHAR2(10)  NOT NULL,     -- ex: '2024.1'
    TIPO                 VARCHAR2(30)  NOT NULL,     -- ver tipos abaixo
    SALA_ID              NUMBER,
    TURMA_ID             NUMBER,
    TURMA_PARCEIRA_ID    NUMBER,
    NOVA_CAPACIDADE      NUMBER,
    OBSERVACAO           VARCHAR2(500),
    DESCRICAO_LIVRE      VARCHAR2(1000),             -- texto livre (tipo GENERICA)
    PARAMETROS_JSON      CLOB,                       -- regra JSON estruturada
    STATUS_INTERPRETACAO VARCHAR2(20) DEFAULT 'OK',  -- OK | PENDENTE_REVISAO | ERRO
    CRIADO_EM            TIMESTAMP DEFAULT SYSTIMESTAMP
);
```

Tipos de exceção suportados:
- `SALA_INTERDITADA` — sala removida da pool de disponíveis
- `COMPARTILHAMENTO` — duas turmas fundidas (capacidade somada)
- `CAPACIDADE_SALA` — capacidade efetiva da sala alterada
- `GENERICA` — regra livre em JSON interpretada pelo motor de regras

**`CURSO_BLOCO_PRIORIDADE`** — Afinidade entre cursos e blocos:

```sql
CREATE TABLE CURSO_BLOCO_PRIORIDADE (
    CURSO_ID   NUMBER NOT NULL,
    BLOCO_ID   NUMBER NOT NULL,
    PRIORIDADE NUMBER DEFAULT 1,  -- 1=mais prioritário
    PRIMARY KEY (CURSO_ID, BLOCO_ID)
);
```

---

## 7. Algoritmo de Ensalamento

O núcleo do sistema está em `app/services/scheduler.py`. O algoritmo executa em 4 fases:

### Fase 1 — Carregar exceções e preparar contexto

```
1. Carregar todas as exceções do semestre do Oracle
2. Carregar todas as salas disponíveis
3. Carregar todas as turmas do semestre com seus horários
4. Carregar prioridades curso → bloco
5. Parsear as regras genéricas (tipo GENERICA) em ContextoRegras
```

### Fase 2 — Aplicar exceções estruturadas

As exceções dos tipos fixos são aplicadas diretamente sobre as listas:

- **SALA_INTERDITADA**: sala removida do conjunto de candidatas
- **CAPACIDADE_SALA**: `capacidade_efetiva` da sala sobrescrita
- **COMPARTILHAMENTO**: as duas turmas são fundidas em uma só, com `num_alunos_efetivo` = soma das duas. A turma absorvida é removida da lista.

### Fase 3 — Ordenar turmas por prioridade

As turmas são ordenadas por dois critérios sequenciais:

1. **Curso com afinidade de bloco definida** vem antes (prioridade `0` vs `1`)
2. **Número de alunos efetivo em ordem decrescente** (maiores primeiro)

Isso garante que turmas grandes de cursos com preferência de bloco são as primeiras a escolher sala, evitando que percam para turmas menores.

### Fase 4 — Alocação por best-fit

Para cada turma (na ordem de prioridade):
  Para cada horário da turma:

1. Verificar se a turma tem **sala fixa** por regra genérica (`TURMA_FIXADA_EM_SALA` ou `SALA_RESERVADA_PARA_TURMA`)
   - Se sim: tentar usar essa sala específica
2. Se não houver sala fixa, buscar candidatas:
   - Filtrar salas já ocupadas no horário (em memória + banco)
   - Filtrar por `capacidade_efetiva >= num_alunos_efetivo`
   - Filtrar por tipo de sala exigida pela disciplina (se houver)
   - Filtrar por regras genéricas (`sala_permitida_para_turma`)
   - Preferir salas no bloco de afinidade do curso
   - Aplicar **best-fit**: menor sala que ainda acomoda (minimiza desperdício)
3. Se nenhuma sala disponível → registrar conflito

### Fase 5 — Persistir

Todas as alocações válidas são inseridas em batch na tabela `FINALIDADE_ESPACO_ALOCADO` usando `executemany` do Oracle.

---

## 8. Sistema de Exceções

### Exceções estruturadas (tipos fixos)

São as situações previstas e mais comuns. Cadastradas diretamente com campos específicos:

```bash
# Sala em reforma
excecao adicionar --tipo SALA_INTERDITADA --sala-id 5 --semestre 2024.1

# Duas turmas compartilham a mesma aula
excecao adicionar --tipo COMPARTILHAMENTO --turma-id 10 --turma-parceira-id 11 --semestre 2024.1

# Sala perdeu cadeiras, comporta menos alunos
excecao adicionar --tipo CAPACIDADE_SALA --sala-id 3 --nova-capacidade 30 --semestre 2024.1
```

### Exceções genéricas — Motor de Regras

Para situações estruturadas mas não previstas nos tipos fixos. O usuário cadastra um JSON de regra diretamente:

```json
{
  "regra": "BLOCO_RESTRITO_PARA_CURSO",
  "bloco_id": 2,
  "curso_id": 5,
  "motivo": "Bloco B em manutenção para curso de Medicina"
}
```

Os 7 tipos de regras disponíveis no motor:

| Regra | Parâmetros | Efeito |
|---|---|---|
| `BLOCO_RESTRITO_PARA_CURSO` | `bloco_id`, `curso_id` | Curso não pode usar salas desse bloco |
| `BLOCO_RESTRITO_PARA_TODOS_EXCETO_CURSO` | `bloco_id`, `curso_id` | Somente esse curso pode usar o bloco |
| `SALA_RESERVADA_PARA_TURMA` | `sala_id`, `turma_id` | Sala exclusiva para uma turma |
| `LIMITE_ALUNOS_BLOCO` | `bloco_id`, `max_alunos` | Bloco não aceita turmas maiores que N |
| `TIPO_SALA_PROIBIDO_CURSO` | `curso_id`, `tipo_sala` | Curso não pode usar este tipo de sala |
| `TIPO_SALA_EXCLUSIVO_CURSO` | `curso_id`, `tipo_sala` | Curso só pode usar este tipo de sala |
| `TURMA_FIXADA_EM_SALA` | `turma_id`, `sala_id` | Turma obrigatoriamente nessa sala |

### Exceções genéricas — Interpretação por IA

Para situações completamente imprevisíveis, o usuário descreve a restrição em português e o sistema usa Claude para convertê-la automaticamente em uma regra JSON:

**Fluxo:**
```
Texto livre do usuário
        ↓
Claude recebe: descrição + contexto do banco (salas, blocos, cursos disponíveis)
        ↓
Claude retorna: JSON estruturado com tipo de regra e parâmetros
        ↓
Sistema avalia: OK (aplicar diretamente) ou PENDENTE_REVISAO (aguardar revisão humana)
        ↓
JSON salvo em EXCECAO_SEMESTRE.PARAMETROS_JSON
        ↓
Próxima execução do ensalamento aplica a regra automaticamente
```

**Status de interpretação:**
- `OK` — regra reconhecida e aplicada automaticamente no ensalamento
- `PENDENTE_REVISAO` — IA não teve certeza, admin deve revisar antes de gerar
- `ERRO` — falha na chamada à API da IA

---

## 9. API REST

Base URL: `http://localhost:8000/api/v1`
Documentação interativa: `http://localhost:8000/api/v1/docs` (Swagger UI)

### Endpoints disponíveis

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/salas?bloco_id=1` | Lista salas, opcionalmente filtrando por bloco |
| `GET` | `/turmas?semestre=2024.1` | Lista turmas do semestre com horários |
| `POST` | `/ensalamento/gerar` | Executa o algoritmo e persiste no Oracle |
| `GET` | `/ensalamento?semestre=2024.1` | Grade alocada do semestre |
| `GET` | `/ensalamento/conflitos?semestre=2024.1` | Turmas que não encontraram sala |
| `DELETE` | `/ensalamento/{semestre}` | Remove todas as alocações do semestre |
| `GET` | `/excecoes?semestre=2024.1` | Lista exceções cadastradas |
| `POST` | `/excecoes` | Cadastra exceção estruturada |
| `POST` | `/excecoes/interpretar` | Interpreta descrição livre via IA e salva |
| `DELETE` | `/excecoes/{id}` | Remove uma exceção |
| `GET` | `/prioridades` | Lista afinidades curso → bloco |
| `POST` | `/prioridades` | Configura afinidade curso → bloco |

### Exemplo — Gerar ensalamento via API

```json
POST /api/v1/ensalamento/gerar
{
  "semestre": "2024.1",
  "limpar_anterior": true
}
```

Resposta:
```json
{
  "semestre": "2024.1",
  "total_turmas": 120,
  "alocadas": 117,
  "conflitos": 3,
  "percentual_ocupacao": 97.5,
  "alocacoes": [...],
  "turmas_sem_sala": [...]
}
```

### Exemplo — Interpretar exceção via IA

```json
POST /api/v1/excecoes/interpretar
{
  "semestre": "2024.1",
  "descricao": "Turmas com mais de 40 alunos não cabem no bloco A por questões acústicas",
  "salvar": true
}
```

Resposta:
```json
{
  "semestre": "2024.1",
  "descricao_original": "Turmas com mais de 40 alunos...",
  "regras_interpretadas": [
    {
      "regra": "LIMITE_ALUNOS_BLOCO",
      "bloco_id": 1,
      "max_alunos": 40,
      "motivo": "questões acústicas"
    }
  ],
  "status": "OK",
  "ids_salvos": [42]
}
```

---

## 10. Interface de Linha de Comando (CLI)

Todos os comandos são acessados via:
```bash
python -m cli.commands <grupo> <comando> [opções]
```

### Ensalamento

```bash
# Gerar grade (remove a anterior e gera nova)
python -m cli.commands gerar --semestre 2024.1 --limpar-anterior

# Listar grade gerada (filtrando por bloco opcional)
python -m cli.commands listar --semestre 2024.1
python -m cli.commands listar --semestre 2024.1 --bloco "Bloco B"

# Ver turmas que não conseguiram sala
python -m cli.commands conflitos --semestre 2024.1

# Remover todas as alocações do semestre
python -m cli.commands limpar --semestre 2024.1
```

### Exceções

```bash
# Listar exceções do semestre
python -m cli.commands excecao listar --semestre 2024.1

# Sala interditada
python -m cli.commands excecao adicionar \
  --semestre 2024.1 --tipo SALA_INTERDITADA --sala-id 5

# Compartilhamento de disciplina entre cursos
python -m cli.commands excecao adicionar \
  --semestre 2024.1 --tipo COMPARTILHAMENTO \
  --turma-id 10 --turma-parceira-id 11

# Capacidade reduzida
python -m cli.commands excecao adicionar \
  --semestre 2024.1 --tipo CAPACIDADE_SALA \
  --sala-id 3 --nova-capacidade 30

# Interpretar exceção em linguagem natural via IA
python -m cli.commands excecao interpretar \
  --semestre 2024.1 \
  --descricao "O bloco C não pode receber cursos de engenharia este semestre"

# Remover exceção pelo ID
python -m cli.commands excecao remover --id 7
```

### Prioridades

```bash
# Configurar afinidade: Curso 3 tem preferência pelo Bloco 2 (nível 1 = mais alto)
python -m cli.commands prioridade --curso-id 3 --bloco-id 2 --nivel 1
```

---

## 11. Integração com IA

O arquivo `app/services/interpretador_ia.py` implementa a integração com o Claude (Anthropic API).

### Como funciona

1. **Contexto dinâmico**: antes de cada chamada, o sistema busca do Oracle a lista de blocos, salas e cursos disponíveis e envia junto com a descrição. Isso permite que o modelo use IDs reais do banco.

2. **Prompt de sistema**: define os 7 tipos de regras disponíveis em formato de tabela, com parâmetros obrigatórios de cada um.

3. **Retorno JSON**: o modelo é instruído a retornar exclusivamente JSON (objeto único ou array para múltiplas regras).

4. **Fallback**: se o modelo retornar texto não-JSON ou uma regra desconhecida, o status é marcado como `PENDENTE_REVISAO` e a exceção não é aplicada até revisão humana.

### Configuração necessária

Adicionar ao `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

A chave é lida automaticamente pelo SDK da Anthropic via variável de ambiente.

---

## 12. Como executar

### Pré-requisitos

- Python 3.10+
- Oracle Instant Client instalado (necessário para `python-oracledb`)
- Acesso ao banco Oracle da faculdade
- Chave da Anthropic API (somente para interpretação por IA)

### Instalação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar ambiente
cp .env.example .env
# Editar .env com as credenciais Oracle e a chave ANTHROPIC_API_KEY

# 3. Criar as tabelas novas no Oracle
# Se o banco está sendo criado do zero:
sqlplus usuario/senha@dsn @sql/create_excecao_semestre.sql

# Se a tabela EXCECAO_SEMESTRE já existia:
sqlplus usuario/senha@dsn @sql/migration_add_generica.sql
```

### Iniciar a API

```bash
uvicorn main:app --reload
# API disponível em http://localhost:8000
# Swagger UI em http://localhost:8000/api/v1/docs
```

### Uso típico por semestre

```bash
# 1. Configurar prioridades de blocos por curso (se necessário)
python -m cli.commands prioridade --curso-id 1 --bloco-id 3 --nivel 1

# 2. Cadastrar as exceções do semestre
python -m cli.commands excecao adicionar --semestre 2024.1 --tipo SALA_INTERDITADA --sala-id 12
python -m cli.commands excecao interpretar --semestre 2024.1 \
  --descricao "Turmas de pós-graduação têm prioridade exclusiva no bloco D"

# 3. Revisar exceções com status PENDENTE_REVISAO (se houver)
python -m cli.commands excecao listar --semestre 2024.1

# 4. Gerar o ensalamento
python -m cli.commands gerar --semestre 2024.1 --limpar-anterior

# 5. Verificar resultado
python -m cli.commands listar --semestre 2024.1
python -m cli.commands conflitos --semestre 2024.1
```

---

*Documentação gerada em 10/04/2026 — Branch: `claude/university-classroom-scheduler-Pb1cK`*
