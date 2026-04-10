-- DDL: Tabela de exceções por semestre
-- Execute este script no Oracle antes de usar o sistema de ensalamento.

CREATE TABLE EXCECAO_SEMESTRE (
    ID                NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    SEMESTRE          VARCHAR2(10)  NOT NULL,
    TIPO              VARCHAR2(30)  NOT NULL,
    SALA_ID           NUMBER,
    TURMA_ID          NUMBER,
    TURMA_PARCEIRA_ID NUMBER,
    NOVA_CAPACIDADE   NUMBER,
    OBSERVACAO        VARCHAR2(500),
    -- Campos para exceções genéricas (tipo GENERICA)
    DESCRICAO_LIVRE   VARCHAR2(1000),        -- Texto livre descrevendo a exceção
    PARAMETROS_JSON   CLOB,                  -- Regra estruturada em JSON
    STATUS_INTERPRETACAO VARCHAR2(20) DEFAULT 'OK',  -- OK | PENDENTE_REVISAO | ERRO
    CRIADO_EM         TIMESTAMP DEFAULT SYSTIMESTAMP,
    CONSTRAINT CHK_EXCECAO_TIPO CHECK (
        TIPO IN ('SALA_INTERDITADA', 'COMPARTILHAMENTO', 'CAPACIDADE_SALA', 'GENERICA')
    ),
    CONSTRAINT CHK_STATUS_INTERP CHECK (
        STATUS_INTERPRETACAO IN ('OK', 'PENDENTE_REVISAO', 'ERRO')
    )
);

COMMENT ON TABLE  EXCECAO_SEMESTRE                       IS 'Exceções e variações por semestre que afetam o ensalamento';
COMMENT ON COLUMN EXCECAO_SEMESTRE.SEMESTRE               IS 'Semestre no formato AAAA.N (ex: 2024.1)';
COMMENT ON COLUMN EXCECAO_SEMESTRE.TIPO                   IS 'SALA_INTERDITADA | COMPARTILHAMENTO | CAPACIDADE_SALA | GENERICA';
COMMENT ON COLUMN EXCECAO_SEMESTRE.SALA_ID                IS 'Sala afetada (SALA_INTERDITADA e CAPACIDADE_SALA)';
COMMENT ON COLUMN EXCECAO_SEMESTRE.TURMA_ID               IS 'Turma principal do compartilhamento';
COMMENT ON COLUMN EXCECAO_SEMESTRE.TURMA_PARCEIRA_ID      IS 'Segunda turma que compartilha a mesma aula';
COMMENT ON COLUMN EXCECAO_SEMESTRE.NOVA_CAPACIDADE        IS 'Capacidade efetiva da sala neste semestre (CAPACIDADE_SALA)';
COMMENT ON COLUMN EXCECAO_SEMESTRE.DESCRICAO_LIVRE        IS 'Texto livre original (input humano para tipo GENERICA)';
COMMENT ON COLUMN EXCECAO_SEMESTRE.PARAMETROS_JSON        IS 'Regra estruturada em JSON gerada pela IA ou manualmente';
COMMENT ON COLUMN EXCECAO_SEMESTRE.STATUS_INTERPRETACAO   IS 'OK=aplicada | PENDENTE_REVISAO=IA não teve certeza | ERRO=falha';

-- Tabela de afinidade curso → bloco (prioridade de alocação)
CREATE TABLE CURSO_BLOCO_PRIORIDADE (
    CURSO_ID   NUMBER NOT NULL,
    BLOCO_ID   NUMBER NOT NULL,
    PRIORIDADE NUMBER DEFAULT 1,
    PRIMARY KEY (CURSO_ID, BLOCO_ID)
);

COMMENT ON TABLE  CURSO_BLOCO_PRIORIDADE            IS 'Define qual bloco um curso deve ter prioridade ao alocar salas';
COMMENT ON COLUMN CURSO_BLOCO_PRIORIDADE.PRIORIDADE IS '1=mais prioritário; valores maiores = menor prioridade';
