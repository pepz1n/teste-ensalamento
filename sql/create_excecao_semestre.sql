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
    CRIADO_EM         TIMESTAMP DEFAULT SYSTIMESTAMP,
    CONSTRAINT CHK_EXCECAO_TIPO CHECK (
        TIPO IN ('SALA_INTERDITADA', 'COMPARTILHAMENTO', 'CAPACIDADE_SALA')
    )
);

COMMENT ON TABLE  EXCECAO_SEMESTRE                 IS 'Exceções e variações por semestre que afetam o ensalamento';
COMMENT ON COLUMN EXCECAO_SEMESTRE.SEMESTRE         IS 'Semestre no formato AAAA.N (ex: 2024.1)';
COMMENT ON COLUMN EXCECAO_SEMESTRE.TIPO             IS 'SALA_INTERDITADA | COMPARTILHAMENTO | CAPACIDADE_SALA';
COMMENT ON COLUMN EXCECAO_SEMESTRE.SALA_ID          IS 'Sala afetada (SALA_INTERDITADA e CAPACIDADE_SALA)';
COMMENT ON COLUMN EXCECAO_SEMESTRE.TURMA_ID         IS 'Turma principal do compartilhamento';
COMMENT ON COLUMN EXCECAO_SEMESTRE.TURMA_PARCEIRA_ID IS 'Segunda turma que compartilha a mesma aula';
COMMENT ON COLUMN EXCECAO_SEMESTRE.NOVA_CAPACIDADE  IS 'Capacidade efetiva da sala neste semestre (CAPACIDADE_SALA)';

-- Tabela de afinidade curso → bloco (prioridade de alocação)
CREATE TABLE CURSO_BLOCO_PRIORIDADE (
    CURSO_ID   NUMBER NOT NULL,
    BLOCO_ID   NUMBER NOT NULL,
    PRIORIDADE NUMBER DEFAULT 1,
    PRIMARY KEY (CURSO_ID, BLOCO_ID)
);

COMMENT ON TABLE  CURSO_BLOCO_PRIORIDADE            IS 'Define qual bloco um curso deve ter prioridade ao alocar salas';
COMMENT ON COLUMN CURSO_BLOCO_PRIORIDADE.PRIORIDADE IS '1=mais prioritário; valores maiores = menor prioridade';
