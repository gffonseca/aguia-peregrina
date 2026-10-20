# Playbook — Execução / recuperação de crédito bancário em massa — polo ativo (credor = Banco da Amazônia) — TJPA + TJAM

> **Versão para leitura.** Este documento reproduz em prosa e tabelas o arquivo `execucao-credito-basa-tjpa-tjam.playbook.yaml`, que é a **fonte da verdade** ingerida pela plataforma. Comentários e correções podem ser feitos aqui; quem mantém o playbook transporta para o YAML e roda a validação. Se os dois divergirem, vale o YAML.
>
> **Estado: EM REVISÃO (versão 1; sessão 1 de revisão em 20/10/2026).** Autor e revisor: Gustavo Fonseca (OAB/PA 12.724). Primeira tipologia de **polo ativo** da Águia Peregrina. A sessão 1 fixou as **decisões de processo** (seção 0.1); **nenhuma referência legal foi conferida ainda** — nenhuma citação legal, código CNJ, número de tema ou súmula foi validado (92 referências `conferido: false` no YAML); prazos, valores, pesos e faixas marcados **ilustrativo/provisório** seguem a calibrar com a carteira e com o BASA. Pendências que dependem do cliente (portal do BASA, política de alçadas, programas vigentes, piso de valor, SLA) estão marcadas **⏳ CLIENTE** e registradas em `metadata.piloto.pendencias_externas` (dono: Gustavo).

## 0. Por que esta tipologia é diferente da defesa

Os quatro playbooks anteriores (consignado, energia, aéreo, trabalhista) têm a mesma forma: o cliente é réu, a peça é a contestação, a tese é um argumento, o KPI é condenação evitada. Aqui tudo inverte:

| | Defesa (playbooks anteriores) | Polo ativo (este playbook) |
|---|---|---|
| Cliente | réu | **exequente** (BASA) — `metadata.polo: ativo`, `lado: autor` |
| Peça padrão | contestação (uma peça grande por processo) | **biblioteca de peças curtas e repetitivas** (impulso, Sisbajud, edital, suspensão…) + duas peças de mérito (impugnação a embargos, resposta a exceção) |
| "Tese" | argumento jurídico | **módulo de decisão**: o que fazer com o processo nesta fase |
| Primeira pergunta | "qual tese cabe?" | **"vale a pena gastar neste processo?"** (T01 — triagem de recuperabilidade) |
| KPI | condenação média, taxa de improcedência | **valor recuperado, prazo até penhora efetiva, % sem andamento > 90 dias** (KPIs do BASA) |
| Acordo | mitigação de condenação | **instrumento de recuperação**; a alçada é do banco |
| Antifraude | litigância predatória do autor | **qualidade de dados da carteira** (CNJ duplicado, moeda antiga, homônimo) + impenhorabilidades |
| Tempo de revisão | 15 min por contestação | **5 min** por impulso, **20 min** por impugnação a embargos |

O score de recuperabilidade (T01) é uma função de probabilidade × valor × prazo − custo, vista pelo lado do credor originário. Os módulos de triagem, calendário de prescrição intercorrente (T08/T08.1), carteira morta (T01.1) e qualidade de dados (M4) são reaproveitáveis em qualquer carteira de credor (Banpará, financeiras, concessionárias), assim como os módulos de impulso e resposta a embargos. **Cessão de crédito não é objeto deste playbook.**

**Ordem de prioridade decidida para a esteira (20/10/2026):** (1) triagem de recuperabilidade — separar carteira viva de carteira morta (T01); (2) peças repetitivas em massa — impulsos, Sisbajud/Renajud/Infojud, cumprimento de sentença, habilitação, suspensão art. 921 (T02–T05, T08, T12); (3) resposta a embargos e exceções de pré-executividade (T06, T07); (4) monitoramento de prazos/andamentos e priorização do que está parado (T08/T08.1 + métricas M03/M04/M11/M13).

### 0.1 Decisões da revisão (20/10/2026) — sessão 1

Sessão conduzida por Gustavo Fonseca (OAB/PA 12.724). Cada decisão está codificada no YAML onde indicado; status do playbook passa a `em_revisao`. As referências legais **continuam todas `conferido: false`** — a conferência é a próxima sessão.

| # | Decisão | Onde está no YAML |
|---|---|---|
| 1 | **Carteira morta = três critérios objetivos**, qualquer um basta: (a) sem bens localizados após Sisbajud + Renajud + Infojud negativos **e** mais de 3 anos sem movimentação útil; (b) executado falecido sem herdeiros/inventário localizável; (c) valor atualizado abaixo do custo esperado de diligências + custas. **Prescrição intercorrente não é critério** de carteira morta — é gatilho de prioridade (decisão 10). | T01.1 (resumo, condições, provas, argumentos); campo `carteira_morta_criterios`; checagem `carteira_morta_criterio_a`; `recomendacao_triagem` passa a `viva_prioritaria / viva / observacao / morta` |
| 2 | **Piso de valor para não diligenciar: R$ 10.000** (valor atualizado) — `provisorio: true`, "definir com o BASA — política do banco". | checagem `valor_abaixo_piso_diligencia` (`piso_brl: 10000, provisorio: true`); campo `valor_abaixo_piso_diligencia`; T01.1 critério (c); pendência externa |
| 3 | **Baixa/suspensão (art. 921) de processo de carteira morta é decisão de SÓCIO, caso a caso** — não em lote, não pelo advogado da carteira. | X03 (condição `socio_decisao_carteira_morta == pendente`, `escalar_socio` + `nao_gerar_minuta`); `criterios_revisao.exige_segunda_revisao_se` (`recomendacao_triagem == morta`) e `exige_segunda_revisao_tambem`; checklist R13; campo `socio_decisao_carteira_morta` |
| 4 | **Cessão de carteira morta fica fora do playbook.** Removidas as menções a cessão/lote de cessão das ações, sinais e fundamentação; fica só a nota neutra em `metadata.observacoes`: "cessão de crédito não é objeto deste playbook". | `metadata.observacoes`; T01.1; X03; M07; `sinais_acordo.quando_acordar` |
| 5 | **Pisos de revisão:** peças de impulso padrão (Sisbajud/Renajud/Infojud — cumulado ou sequencial —, citação por edital, manifestação sobre penhora negativa, art. 921) = **300 s**, revisor = advogado da carteira, **processamento em lote diário**; peças intermediárias (cumprimento, habilitação, homologação) = 600 s; impugnação a embargos, exceção e IDPJ = 1.200 s. | `criterios_revisao` (comentário de pisos, `revisor_final`, `observacoes`); T02 resumo |
| 6 | **Ordem de diligências após citação sem pagamento: pedido CUMULADO Sisbajud + Renajud + Infojud em uma única peça**; se o juízo indeferir o cumulado, fallback sequencial e a esteira **registra a preferência por vara/juízo** (campo `preferencia_juizo_cumulado`; M10/M14 aprendem por órgão julgador). Depois: CNIB/SREI → avaliação/leilão. | T02 argumentos; T02.2 (renomeada; condição `preferencia_juizo_cumulado`; pedidos); T02.3 (CNIB/SREI); campos `preferencia_juizo_cumulado`, `diligencias_cumuladas_negativas`; `tipo_peca_prevista` ganha `requerimento_cumulado_sisbajud_renajud_infojud` e `requerimento_cnib_srei`; checklist R12; M14 |
| 7 | **Impugnação a embargos por excesso de execução: SEMPRE exigir a planilha do embargante (CPC 917 §§ 3º/4º) e pedir rejeição liminar da alegação sem planilha; recalcular o débito com saldo/memória do portal BASA** antes de impugnar. | T06.1 (renomeada; resumo, provas, argumentos, pedidos); seção 4 do modelo de peça; checklist R06; motivo de recusa |
| 8 | **Acordo/renegociação: a FBS propõe ATIVAMENTE nos casos de score médio com bens parciais**, dentro da política/programa do BASA. Fluxo mantido: FBS recomenda valor → BASA aprova (alçada do banco) → registro → peça. | T09 (condição `acordo_iniciativa != nenhuma`); **T09.1** nova (viva/observacao, `bens_cobertura_pct` entre 1 e 99 %); `sinais_acordo.politica`, `quando_acordar`, `fluxo_aprovacao`; campos `bens_cobertura_pct`, `acordo_iniciativa`, `acordo_aprovacao_basa_registrada`; M15 |
| 9 | **Processo parado: alerta + impulso automático para revisão aos 90 dias sem movimentação útil** — `provisorio: true`, "alinhar ao SLA do contrato BASA". | X12 (`alertar_revisor` + `escalar_advogado_carteira`); checagem `processo_parado_90_dias` (`dias: 90, provisorio: true`); T02/T08 argumentos; campo `impulso_automatico_90d_gerado`; M03 |
| 10 | **Prescrição intercorrente (CPC 921 §4º): calcular por processo; priorizar vencimentos < 12 meses; diligência útil OBRIGATÓRIA antes do vencimento** — ação da esteira, checklist do revisor e métrica própria. | **T08.1** nova; X11; campos `prescricao_intercorrente_data_limite`, `prescricao_intercorrente_meses_restantes`, `diligencia_util_antes_intercorrente`; checagem `prescricao_intercorrente_proxima` (`alerta_meses_antes: 12`); checklist R11 (bloqueante); **M13** "processos com intercorrente < 12 meses sem diligência útil" |
| 11 | **Amostra do piloto: os 200 processos de MAIOR valor atualizado COM bens localizados** (indício de bens = andamentos de penhora/arresto, Sisbajud positivo, Renajud com veículo, garantia real registrada), **excluindo** outliers de moeda antiga (> R$ 5 mi de 1992–94) e processos sem CNJ válido. "Bens localizados" depende dos andamentos (legalone_andamentos/DataJud); se insuficientes na data da seleção, fallback = garantia real registrada no título. A distribuição por tribunal (100/60/40) deixa de ser critério. | `metadata.piloto.amostra` (campo novo no schema); campo `indicio_bens_fonte` |
| 12 | **Portal BASA: pedir ao BASA documentação/API do portal** (contratos/cédulas, garantias, extratos, saldo devedor, cálculo atualizado). | `metadata.piloto.pendencias_externas` (dono: **Gustavo**, status aberta); 8 campos do dossiê com `disponibilidade: "a confirmar — portal BASA (documentação solicitada)"` |

**Mudanças de schema (aditivas):** `Piloto.amostra` (texto opcional) e `Piloto.pendencias_externas` (lista de `{descricao, dono, status, aberta_em}`) em `app/modules/m00_playbook/schema.py`; `playbook.schema.json` regenerado.

## 1. Identificação

| Campo | Valor |
|---|---|
| Tipologia | `execucao_credito_bancario_basa` |
| Tribunal | TJPA (63,5 % da carteira) — TJAM (34,8 %) coberto pelo mesmo playbook (o schema aceita um tribunal por arquivo) |
| Polo / lado / réu-tipo | **Ativo** / autor / devedor PF ou PJ de crédito bancário |
| Peça padrão | petição de impulso da execução (biblioteca na seção 8) |
| Versão | 1 (em revisão) |
| Autor (OAB) | Gustavo Fonseca — PA 12724 |
| Revisões | sessão 1 — 20/10/2026 (Gustavo Fonseca OAB/PA 12.724): triagem, impulso, embargos, acordo, monitoramento, amostra |
| Aprovação | pendente (referências legais ainda não conferidas) |
| Piloto | **BASA** (carteira já patrocinada). **Amostra: os 200 processos de maior valor atualizado com bens localizados** (penhora/arresto, Sisbajud positivo, Renajud com veículo ou garantia real registrada), excluindo outliers de moeda antiga e processos sem CNJ válido; fallback = garantia real registrada no título se os andamentos forem insuficientes. Fase 1: T01 em replay (+200 encerrados para calibrar o score). Fase 2: impulsos em lote diário. Fase 3: impugnações. Pré-requisito: documentação/API do portal do BASA (pendência externa — Gustavo). |

**Escopo.** Carteira de recuperação de crédito do Banco da Amazônia patrocinada pela FBS: execuções de título extrajudicial (CCB, cédulas e notas de crédito rural, contratos bancários), cumprimentos de sentença, monitórias e os incidentes defensivos do executado (embargos à execução, exceção de pré-executividade). O objetivo da esteira não é "vencer a ação": é recuperar valor no menor prazo e com o menor custo de diligência.

### 1.1 A carteira em números (radiografia Legal One/DataJud, 19–20/10/2026)

Fonte: `/reports/Legal One base FBS.md` (Postgres do Hub; backfill 87 % na BASA ativa; DataJud 51,9 % consultado).

| Dimensão | Números |
|---|---|
| Volume | **16.656 processos ativos** (42 % do acervo ativo da FBS); 323 encerrados |
| Tribunal | TJPA 9.833 (63,5 %) · TJAM 5.395 (34,8 %) · TRT-8 134 · TRF-1 55 · TJAP 25 |
| TJPA — foros | Belém só 13,9 % (1.367); interior: Tucuruí 552, Marabá 422, Ananindeua 380, Rurópolis 356, Novo Progresso 345, Parauapebas 344, Altamira 312, Alenquer 303, Novo Repartimento 288, Itaituba 286 |
| TJAM — foros | **Itacoatiara 1.674 (31 %)** — a 3ª Vara de Itacoatiara é o órgão com mais processos BASA em toda a base; Manaus 993 (18 %); Boca do Acre 402; Humaitá 139; Manacapuru 214 |
| Classe (DataJud) | **Execução de Título Extrajudicial 71,0 %** · Cumprimento de sentença 5,6 % · Embargos à Execução 4,5 % · Procedimento Comum 4,3 % · Carta Precatória 3,8 % (6,1 % no TJAM) · Monitória 3,4 % |
| Assunto | **CCB 43,8 %** (59,5 % no TJAM) · Contratos Bancários 9,7 % · Cédula de Crédito Rural 8,7 % · Nota de Crédito Rural 2,6 % · Crédito Rural 1,0 % (crédito rural ≈ 11,3 % somado, concentrado no TJPA) |
| Executado | **80,3 % só pessoa física**; 19,5 % com ao menos uma PJ |
| Valor | mediana **R$ 57,5 mil**; p90 **R$ 276 mil**; carteira sem outliers (> R$ 5 mi) = 15.070 processos, **R$ 1,95 bi**; 1.458 sem valor (8,8 %) |
| Idade | três ondas de distribuição: **2015–16** (2.846), **2019–21** (3.357), **2024–25** (2.678) |
| Vida | **85 % tiveram movimento em 2026** — carteira viva, não acervo morto |
| Equipe | 12 pessoas com 1.500–1.950 processos cada |
| Qualidade de dados | 771 CNJs repetidos em 1.638 pastas; 235 sem número + 928 fora do padrão (3.765 na base toda); 4 cadastros para o mesmo cliente; 966 datas de distribuição 01/01/1900; 128 valores > R$ 5 mi (12 > R$ 100 mi, execuções de 1992–94 em moeda antiga); "OLIVEIRA, ROCHA & REZENDE" como advogado da outra parte em 13.175 processos (ex-escritório do banco — artefato) |

**KPIs do cliente:** valor recuperado e prazo; SLA de impulso / processos sem andamento.
**Subsídios:** portal do BASA (contratos/cédulas, garantias, extratos, saldo devedor e cálculo atualizado — documentação/API solicitada ao banco ⏳ CLIENTE, dono Gustavo) + Legal One + DataJud.

## 2. Como a plataforma reconhece a tipologia

- **Classes CNJ (códigos a conferir):** Execução de Título Extrajudicial (12154?), Cumprimento de sentença (156?), Embargos à Execução (172?), Monitória (40?), Carta Precatória Cível (261?), Execução de Título Judicial (1118?), Embargos de Terceiro (37?). **Exceção de pré-executividade** não é classe própria no TPU — detectar por petição/andamento. Todos **[A CONFERIR pelo advogado-dono]**.
- **Assuntos CNJ (códigos a conferir):** Cédula de Crédito Bancário (11806?), Contratos Bancários (9607?), Cédula de Crédito Rural, Nota de Crédito Rural, Crédito Rural, Cédula de Crédito Industrial, Cédula Hipotecária, Penhora/Depósito/Avaliação, Efeito Suspensivo/Impugnação/Embargos, Alienação Fiduciária. Todos **[A CONFERIR]**.
- **Palavras-chave:** execução de título extrajudicial; cédula de crédito bancário/rural; nota de crédito rural; cédula rural pignoratícia/hipotecária; CPR; Banco da Amazônia; BASA; FNO; penhora; Sisbajud/Bacenjud; Renajud; Infojud; citação do executado; embargos à execução; exceção de pré-executividade; cumprimento de sentença; monitória; excesso de execução; prescrição intercorrente; art. 921.
- **Excluem:** consignado; RMC; inexistência de débito; reclamação trabalhista; execução fiscal; dívida ativa.
- **Confiança mínima:** 0,85.

## 3. O que o dossiê precisa ter

Campos que M3 (portal BASA / Legal One), M5 (autos), M9 (DataJud/andamentos) e M4 (cruzamentos) preenchem. **Bloqueia** = sem o campo não sai peça.

| Grupo | Campos | Origem |
|---|---|---|
| Identificação | **numero_cnj** (bloqueia), tribunal e comarca (pelo CNJ — mais confiável que o Legal One), **classe_cnj** (bloqueia), **fase_execucao** (bloqueia; derivada dos andamentos), data_ajuizamento (ano do CNJ), data_ultima_movimentacao_util, dias_sem_andamento, prazo_fatal, tipo_peca_prevista | autos / DataJud / calculado |
| Título e valores | **titulo_tipo** (bloqueia), **titulo_localizado** (bloqueia), **titulo_requisitos_ok** (liquidez/certeza/exigibilidade — bloqueia), titulo_assinaturas_ok, valor_causa, **valor_divida_atualizado** (bloqueia), data_calculo_saldo, **memoria_calculo_disponivel** (bloqueia), valor_moeda_antiga_suspeito | **portal BASA — "a confirmar — portal BASA (documentação solicitada)" ⏳ CLIENTE** |
| Encargos | taxa_juros_remuneratorios, encargos_capitalizacao_pactuada, encargos_comissao_permanencia, encargos_fno_programa | portal BASA |
| Garantias | garantia_tipo (hipoteca, penhor rural/mercantil, alienação fiduciária, aval, fiança, cessão de recebíveis), garantia_valor_estimado, garantia_registrada, garantia_matricula, avalistas_n, garantidor_terceiro_vulneravel | portal BASA / calculado |
| Datas do crédito | data_vencimento, data_inadimplemento, data_citacao, citacao_realizada, citacao_tentativas_n | portal BASA / andamentos |
| Executado | executado_tipo (PF/PJ), executado_cpf_cnpj_valido, executado_obito, executado_inventario_aberto, executado_recuperacao_judicial, executado_falencia, executado_homonimo_risco | autos / antifraude |
| Bens e diligências | bens_localizados, bens_tipos, **indicio_bens_fonte** (penhora / arresto / Sisbajud positivo / Renajud veículo / garantia real registrada — critério da amostra), **bens_cobertura_pct** (bens parciais = 1–99 %), sisbajud_tentativas_n / ultimo_resultado / ultima_data, renajud_consultado, infojud_consultado, **diligencias_cumuladas_negativas**, **preferencia_juizo_cumulado** (cumulado / sequencial / desconhecida — aprendido por vara), cnib_consultado, matriculas_localizadas (SREI/DOI), penhora_conta_titularidade, penhora_verba_impenhoravel_indicio | andamentos / antifraude / calculado |
| Prescrição e suspensões | prescricao_titulo_data_limite (3 × 5 anos **[A CONFERIR]**), prescricao_intercorrente_risco, **prescricao_intercorrente_data_limite** e **prescricao_intercorrente_meses_restantes** (calculadas por processo; < 12 meses = T08.1), **diligencia_util_antes_intercorrente**, suspensao_921_data, arquivamento_data, suspensao_outra_causa (RJ, calamidade, Covid, convenção), programa_renegociacao_elegivel (Lei 13.340/2016, Lei 14.995/2024, PRONAF, securitização, Desenrola, política interna — **[A CONFERIR] quais vigentes** ⏳ CLIENTE), renegociacao_em_curso, cliente_orientou_suspender | calculado / portal BASA |
| Custos | custas_pendentes_valor, custo_diligencias_estimado (tabela por comarca — ilustrativa), honorarios_sucumbencia_fixados | andamentos / calculado |
| Triagem (T01) | score_recuperabilidade (0–1), recomendacao_triagem (viva_prioritaria / viva / observacao / **morta**), **carteira_morta_criterios** (sem_bens_e_3_anos_parado / falecido_sem_herdeiros / valor_abaixo_custo), **valor_abaixo_piso_diligencia** (R$ 10 mil provisório), **socio_decisao_carteira_morta** (pendente / manter / aceitar suspensão 921 / requerer baixa), impulso_automatico_90d_gerado | calculado |
| Incidentes defensivos | embargos_opostos, embargos_materia (excesso, iliquidez, capitalização, comissão de permanência, nulidade de citação, prescrição, renegociação rural…), embargos_planilha_apresentada, embargos_efeito_suspensivo, embargos_julgados_resultado, sentenca_embargos_transitada, excecao_pre_executividade_oposta, excecao_materia_cognoscivel_oficio, decisao_desfavoravel_transitada, indicio_fraude_cedula | autos / andamentos |
| Monitória | monitoria_embargos_opostos, monitoria_prazo_pagamento_decorrido | andamentos |
| Interior | carta_precatoria_necessaria, comarca_deprecada, correspondente_disponivel | calculado / FBS |
| Acordo | acordo_proposta_valor, acordo_desconto_pct, **acordo_iniciativa** (executado / fbs_proativa / basa), acordo_aprovacao_basa_registrada | BASA / calculado |
| Qualidade de dados | cnj_duplicado, cadastro_cliente_id (3863 / 14574 / 15082 / 36641) | antifraude / Legal One |

## 4. Árvore de módulos de decisão ("teses")

Em polo ativo a "tese" raramente é um argumento de mérito: é a decisão do que fazer com o processo nesta fase. Cada módulo só dispara se **todas** as condições forem verdadeiras e as provas obrigatórias estiverem anexas; uma "prova que afasta" desativa o módulo e avisa o revisor.

### (1) Triagem

| Id | Módulo | Quando | Provas | Afastam | Fundamentação (a conferir) | Saída |
|---|---|---|---|---|---|---|
| **T01** | Triagem de recuperabilidade — score e carteira viva × morta | há saldo atualizado e fase conhecida | planilha do BASA; andamentos; garantias; relatório antifraude | saldo em moeda antiga (recalcular antes) | CPC 797/805; CPC 921; Res. CMN 2.682 e régua de baixa do BASA | score 0–1 + recomendação; **nenhuma peça**; "morta" só com critério objetivo de T01.1 |
| **T01.1** | **Carteira morta — três critérios objetivos** (decisão 1): (a) Sisbajud + Renajud + Infojud negativos **e** > 3 anos sem movimentação útil; (b) falecido sem herdeiros/inventário localizável; (c) valor atualizado < custo de diligências + custas (piso **R$ 10 mil, provisório** ⏳ CLIENTE). Intercorrente **não** entra. | recomendação morta + ao menos um critério | relatório de triagem; andamentos (a); antifraude (b); saldo × custo (c) | garantia real não excutida; qualquer indício de bens nos andamentos | CPC 921 III §§1º–5º; CPC 797/805/775 | relatório **por processo** ao advogado da carteira e ao **sócio, que decide caso a caso** (manter / aceitar suspensão 921 / requerer baixa) — nunca em lote (X03, R13) |

**Score (pesos ILUSTRATIVOS, soma 1,0 — calibrar por replay, métrica M10):** garantia real registrada ≥ 50 % da dívida 0,25 · bens localizados 0,20 · executado vivo e sem RJ/falência 0,15 · última diligência útil < 180 dias 0,10 · processo < 5 anos 0,10 · valor líquido ≥ R$ 30 mil 0,10 · CPF/CNPJ válido sem homonímia 0,10. **Faixas:** ≥ 0,70 viva_prioritaria · 0,45–0,69 viva · 0,25–0,44 observacao (só diligência barata periódica) · < 0,25 **e** critério objetivo de T01.1 → morta. Score médio (viva/observacao) com **bens parciais** = faixa de proposta ativa de acordo (T09.1). O score nunca extingue nada sozinho; prescrição intercorrente próxima não rebaixa a morta — prioriza (T08.1).

### (2) Impulso padrão por fase

| Id | Módulo | Quando | Provas | Afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T02** | Impulso padrão (tese-mãe) — **lote diário, 300 s, advogado da carteira**; gatilho de **90 dias** sem movimentação útil = alerta + minuta automática (provisório ⏳ SLA BASA) | carteira viva/observação; cliente não suspendeu; memória de cálculo disponível | planilha; andamentos | despacho recente já determinou a diligência | CPC 797, 798 I b, 829, 835, 854; STJ: Sisbajud sem esgotamento | diligência da fase (subteses), na ordem: cumulado → CNIB/SREI → avaliação/leilão |
| **T02.1** | Citação pendente → endereços, hora certa, edital, arresto | não citado | certidões negativas | < 2 tentativas em endereços distintos (edital prematuro) | CPC 252–257, 256 §3º, 830; STJ nulidade de edital | consultas; hora certa/edital; arresto se há bens |
| **T02.2** | Citado sem pagamento → **pedido CUMULADO Sisbajud (+ teimosinha) + Renajud + Infojud em uma peça**; se o juízo indeferir, **fallback sequencial** e registro de `preferencia_juizo_cumulado` por vara (decisão 6) | citado, prazo decorrido; preferência do juízo | certidão de decurso; saldo ≤ 30 dias | pagamento nos autos | CPC 829, 835 I, 854, 833 IV/X; STJ teimosinha; EREsp 1.582.475; Infojud após frustração **[A CONFERIR]** | peça cumulada contra todos os executados; subsidiário: ao menos Sisbajud, depois Renajud e Infojud em sequência |
| **T02.3** | Diligências cumuladas negativas → **CNIB, SREI/matrículas**, penhora de imóvel/quotas/recebíveis/faturamento | Sisbajud + Renajud + Infojud negativos | detalhamento das três diligências | CNIB/SREI já cumpridos sem fato novo | CPC 835 II–XIII, 866, 139 IV, 772–773; Lei 8.009 art. 3º V; CF 5º XXVI; STJ medidas atípicas | CNIB → SREI → penhora → avaliação/leilão (T02.4); atípicas só com indício (sócio); 3 anos sem bens → critério (a) de T01.1 |
| **T02.4** | Bens penhorados → avaliação, intimações, leilão/adjudicação | penhora formalizada | auto de penhora; matrícula | embargos de terceiro pendentes | CPC 838–844, 870–876, 879–903, 842, 889; Res. CNJ 236; preço vil 50 % | avaliação, registro, intimações, leilão eletrônico |
| **T03** | Penhora de safra, penhor rural, CPR; alienação fiduciária (rito próprio) | título rural com penhor | cédula com o bem; registro | bem pereceu | DL 167/67; Lei 8.929/94; Lei 13.986/2020; CC 1.438–1.446, 1.473; Lei 9.514/97; DL 911/69; CPC 833 VIII; Súmula 93 STJ | constatação/penhora do bem empenhado, depositário, percentual da safra |
| **T04** | IDPJ / redirecionamento a sócios | PJ, penhora frustrada, sem bens | QSA/Junta; diligências negativas; encerramento irregular | sócios já são avalistas (executar o aval) | CPC 133–137, 790 VII; CC 50; Súmula 435 (controversa na civil); REsp 1.526.287 | incidente — **sócio** |
| **T04.1** | Óbito → habilitação de espólio/herdeiros | óbito + inventário localizado | certidão de óbito; dados do inventário | inventário negativo | CPC 110, 313 I, 687–692, 779 II, 642; CC 1.792/1.997 | suspensão e habilitação; alternativa: habilitar crédito no inventário |
| **T05** | Cumprimento de sentença (embargos improcedentes, monitória, honorários) | sentença transitada favorável | sentença + trânsito; planilha com honorários | recurso com efeito suspensivo | CPC 523–525, 513 §2º, 85 §§1º/13; Tema 410 / Súmula 517 | intimação para pagar em 15 dias; multa e honorários 10 % |
| **T08** | Suspensão art. 921 III e prescrição intercorrente — **data-limite calculada por processo**; gatilho de 90 dias (provisório ⏳ SLA BASA) | suspensa/arquivada/penhora frustrada **e** > 90 dias sem andamento | decisão de suspensão; última diligência útil | prazo já consumado | CPC 921 §§1º–7º (Lei 14.195/2021), 1.056; IAC 1 STJ (REsp 1.604.412); Súmula 150 STF; tema sobre diligências infrutíferas **[A CONFERIR]** | viva: diligência útil antes do termo; morta: ciência da suspensão só após decisão do sócio |
| **T08.1** | **Intercorrente a vencer em < 12 meses — prioridade da fila e diligência útil OBRIGATÓRIA** antes do vencimento (decisão 10); não é critério de carteira morta | meses restantes < 12; carteira viva/observação; sem diligência útil após o alerta | andamentos + cálculo da data-limite; saldo | diligência útil já protocolada; causa interruptiva reconhecida | CPC 921 §§4º, 4º-A, 5º; IAC 1 STJ; tema repetitivo **[A CONFERIR]** | diligência útil (cumulado com fato novo, CNIB/SREI, penhora de bem conhecido) protocolada antes da data-limite; R11; M13 |
| **T10** | Carta precatória, interior, correspondentes | ato fora da comarca | despacho | — | CPC 237 III, 255, 260–268, 845 §2º, 848; Res. CNJ 354; normas TJPA/TJAM | precatória ou ato eletrônico/termo nos autos |
| **T12** | Monitória e conversão em execução | classe monitória | contrato + extratos; andamentos | há título executivo (via errada) | CPC 700–702; Súmulas 247, 384, 503/504 | constituição do título e cumprimento (T05) ou impugnação aos embargos monitórios |

**T08 — regra prática:** pedido genérico de "vista"/"prazo" não interrompe a intercorrente; só efetiva localização de bens (921 §4º-A). A esteira calcula **por processo** `prescricao_intercorrente_data_limite` (termo inicial [A CONFERIR — regime do 921 e transição do art. 1.056] + prazo do título [3 × 5 anos, A CONFERIR]) e ordena a fila por meses restantes; **< 12 meses = diligência útil obrigatória (T08.1, X11, R11, M13)**. Processo em observação: 1 diligência útil a cada 10–11 meses (ilustrativo) enquanto houver prazo; processo morto: a decisão de não gastar é do sócio, caso a caso. **90 dias sem movimentação útil** (provisório — alinhar ao SLA do contrato BASA): alerta + minuta de impulso automática no lote diário (X12, M03). A onda de 2015–16 é a primeira a passar pelo crivo.

### (3) Resposta a embargos e exceção de pré-executividade

| Id | Módulo | Quando | Provas | Afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T06** | Impugnação aos embargos (tese-mãe) | embargos pendentes; título e planilha disponíveis | petição de embargos; cédula; memória de cálculo | perícia já apontou excesso relevante | CPC 914–920; 783, 784 III/XII; Lei 10.931 art. 28; DL 167 art. 41; Súmulas 300, 233/247, 381 | rejeição liminar/improcedência; prosseguimento; honorários |
| **T06.1** | Excesso de execução — **SEMPRE exigir a planilha do embargante (917 §§3º/4º), pedir rejeição liminar sem ela e recalcular pelo portal BASA** (decisão 7) | matéria "excesso" | memória de cálculo do portal BASA recalculada; petição de embargos (há planilha?) | erro aritmético evidente no cálculo do BASA (reconhecer a parte, não defender) | CPC 917 III, §§2º–4º; STJ rejeição sem planilha | pedido principal: rejeição liminar por falta de planilha/valor; subsidiário: improcedência critério a critério com o recálculo; perícia só se não resolvível por documentos |
| **T06.2** | Iliquidez — CCB/cédula rural são líquidas com a planilha | matéria "iliquidez" | cédula; planilha | abertura de crédito em conta sem CCB (Súmula 233) | Lei 10.931 art. 28 §2º; DL 167 arts. 10/41; CPC 783; Tema 576 STJ (REsp 1.291.575); Súmulas 233/247 | improcedência; subsidiário: fungibilidade para monitória |
| **T06.3** | Encargos — capitalização e comissão de permanência | matéria "capitalização" | cláusula destacada | cálculo cumula comissão de permanência; sem cláusula expressa | MP 2.170-36 art. 5º; DL 167 art. 5º; Lei 10.931 art. 28 §1º I; Res. CMN; Súmulas 539, 541, 472, 93, 382 STJ; 596 STF; Temas 246/247 | improcedência; subsidiário: recálculo sem comissão de permanência |
| **T06.4** | Nulidade de citação (edital/hora certa) | matéria "nulidade de citação" | certidões e consultas prévias | edital sem tentativa no endereço do título | CPC 239 §1º, 256 §3º, 257, 280; STJ comparecimento espontâneo | rejeição; subsidiário: aproveitamento dos atos |
| **T06.5** | Prescrição da pretensão executiva — 3 × 5 anos ⏳ PENDENTE | matéria "prescrição" | vencimento; data do ajuizamento/despacho | ajuizamento fora do prazo sem causa suspensiva | CC 206 §3º VIII / §5º I, 202; CPC 240 §§1º–3º; Lei 10.931 art. 44; DL 167 art. 60; Súmulas 503/504; jurisprudência sobre CCB **[A CONFERIR — risco de 3 anos]** | rejeição |
| **T06.6** | Renegociação/moratória rural — Lei 13.340/2016, Lei 14.995/2024, PRONAF, securitização ⏳ CLIENTE | matéria "renegociação rural" | cédula (fonte/data/valor); parecer do BASA | contrato enquadrável com pedido tempestivo não processado | Lei 13.340/2016; Lei 14.995/2024; Lei 11.775/2008; Lei 12.844/2013; MCR; Lei 14.690/2023; Leis 13.606/13.729/2018; tema repetitivo STJ **[A CONFERIR]** | improcedência por falta de enquadramento; se enquadra → acordo (T09) |
| **T07** | Resposta à exceção de pré-executividade | exceção pendente | petição; título e planilha | matéria de ordem pública evidente (óbito anterior, pagamento integral) | CPC 803 p.ú., 525 §11, 518; Súmula 393 STJ (analogia); STJ excesso não cabe em exceção | não conhecimento (via inadequada) + rejeição do que for de ordem pública |

### Sinais e subsidiária

| Id | Módulo | Quando | Fundamentação (a conferir) | Saída |
|---|---|---|---|---|
| **T09** | Acordo/renegociação — sinal por faixa, garantia e programa ⏳ CLIENTE | há proposta (do executado) **ou** iniciativa da FBS (T09.1) | CPC 3º §3º, 139 V, 190, 487 III b, 515 II, 922; política do BASA; leis rurais | **FBS recomenda valor → BASA aprova (alçada) → registro** → homologação com suspensão (922) e cláusula de retomada |
| **T09.1** | **Proposta ATIVA da FBS — score médio com bens parciais** (decisão 8), dentro da política/programa do BASA ⏳ CLIENTE | viva/observação; `bens_cobertura_pct` entre 1 e 99 %; sem renegociação em curso; sem indício de fraude | CPC 3º §3º, 139 V, 922; política do BASA | valor recomendado ≈ o que os bens cobrem + custas, saldo parcelado no programa (ilustrativo); desconto só sobre encargos; proposta sai em nome do BASA só após aprovação registrada; se recusada → expropriação (T02.4) |
| **T11** | Honorários, custas e despesas — recuperar; quem adianta | sempre que há valor | CPC 82 §2º, 85 §§1º/2º/13, 827; leis de custas TJPA/TJAM | inclusão na planilha; definir com o BASA quem adianta custas (contrato) |

## 5. Exceções — quando a esteira para

| Id | Situação | Ação |
|---|---|---|
| X01 | Executado falecido **sem** inventário localizado | escalar advogado da carteira (+ alerta) — suspensão 313 I; sem herdeiros/inventário localizável = critério (b) de carteira morta; decisão do sócio |
| X02 | Executado em recuperação judicial ou falência | **sócio** — Lei 11.101 arts. 6º/49; habilitação no juízo universal [A CONFERIR regras de crédito rural/fiduciário] |
| X03 | Carteira morta (T01.1: sem bens + 3 anos / falecido sem herdeiros / valor abaixo do custo) com decisão do sócio pendente | **sócio, caso a caso** (não em lote, não o advogado da carteira); nenhuma peça até `socio_decisao_carteira_morta`; relatório por processo (T01.1) |
| X04 | Indício de fraude na cédula | não gerar peça + sócio; comunicar compliance do BASA; flag, não rótulo |
| X05 | Garantidor terceiro vulnerável | alerta ao revisor + advogado da carteira |
| X06 | Decisão desfavorável ao exequente transitada | não gerar peça; advogado da carteira avalia ação autônoma ou baixa |
| X07 | Cliente orientou suspender | não gerar peça; sai do SLA de impulso enquanto durar |
| X08 | Renegociação administrativa em curso | sinalizar acordo (T09); não impulsionar penhora |
| X09 | Dados inconsistentes (CNJ duplicado, sem CPF/CNPJ, moeda antiga, saldo sem memória) | pedir subsídio + alerta; consolidar pastas antes de qualquer peça |
| X10 | Embargos/exceção com prazo fatal próximo | prioridade máxima na fila de revisão (15 dias — CPC 920 [A CONFERIR]) |
| X11 | **Prescrição intercorrente < 12 meses sem diligência útil** | alerta + advogado da carteira; topo da fila de impulso; diligência útil obrigatória (T08.1) — não para a esteira, não é carteira morta |
| X12 | **Processo viva/observação parado > 90 dias sem movimentação útil** (provisório — SLA BASA) | alerta + advogado da carteira; a esteira gera a minuta de impulso da fase para o lote diário sem esperar despacho (decisão 9) |

## 6. Sinais de acordo / renegociação

**Política (ILUSTRATIVA — a real é do BASA, por faixa de dívida e programa ⏳ CLIENTE).** Em polo ativo, acordo é instrumento de recuperação. Sem garantia real e sem bens: aceitar proposta que recupere mais que o valor presente esperado da execução (score × saldo − custos). Com garantia real excutível ou Sisbajud positivo: só desconto de encargos e parcelamento curto. Programas legais (Lei 13.340/2016 e sucessoras, PRONAF, securitização, Desenrola) prevalecem quando o contrato se enquadra. **Decisão 8 (20/10/2026): em score médio com bens parciais a FBS propõe ativamente (T09.1).**

- **Acordar:** carteira em observação/morta com proposta; **score médio (viva/observação) com bens parciais → proposta ativa da FBS**; programa legal aplicável; sem garantia, sem aval e sem bens.
- **Não acordar:** hipoteca registrada com desconto > 30 % (ilustrativo); título sob suspeita de fraude.
- **Faixas (aqui = faixa de DÍVIDA ATUALIZADA em que a plataforma sinaliza acordo por padrão sem garantia/bens; todas `provisorio: true`, recalibrar em 90 dias):**

| Grupo de comarcas | Faixa (R$) | Base |
|---|---|---|
| Belém e RMB (TJPA) | 0 – 60 mil | ≈ mediana da carteira (R$ 57,5 mil) |
| Interior do Pará — polos (Tucuruí, Marabá, Rurópolis, Novo Progresso, Parauapebas, Altamira, Alenquer…) | 0 – 100 mil | custo de diligência maior (precatória, correspondente) |
| TJAM — Itacoatiara e Manaus | 0 – 60 mil | CCB pequena (59,5 %); mediana R$ 55,6 mil |
| TJAM — interior (Boca do Acre, Humaitá, Manacapuru, Pauini…) | 0 – 100 mil | comarcas de difícil acesso |

**Fluxo de aprovação (mantido):** a **FBS recomenda o valor** (desconto %, parcelas, racional com score, bens e custo; OAB do advogado da carteira — vale para proposta recebida e para proposta ativa) → o **BASA aprova** dentro da alçada interna (gestor/comitê, por faixa e programa — [A CONFERIR]) → a **plataforma registra** (quem, quando, valor, desconto, programa, iniciativa); a proposta ao executado e a petição de homologação só são geradas após o registro. Homologar e **suspender** (CPC 922), não extinguir: descumprido, retoma pelo saldo com a cláusula penal.

## 7. Antifraude e qualidade de dados específicos

Regra inviolável: nenhuma checagem rotula executado ou garantidor; só flags com evidência; só advogado com OAB confirma (`human_decide`).

| Código | O que detecta | Parâmetro / base | Severidade |
|---|---|---|---|
| `cnj_invalido_ou_duplicado` | número fora do padrão, ausente ou repetido em várias pastas | 3.765 na base; 771 CNJs em 1.638 pastas BASA | alta |
| `cliente_duplicado_cadastro` | BASA em 4 contatos | 3863, 14574, 15082, 36641 | média |
| `valor_moeda_antiga_outlier` | > R$ 5 mi, sobretudo 1990–95 | 128 processos; 12 > R$ 100 mi ≈ R$ 13 bi | alta |
| `distribution_date_placeholder` | 01/01/1900 | 966 processos — usar ano do CNJ | baixa |
| `processo_sem_valor` | valor 0/nulo | 1.458 (8,8 %) | média |
| `advogado_outra_parte_artefato` | OLIVEIRA, ROCHA & REZENDE como patrono adverso | 13.175 — ex-escritório do banco | info |
| `executado_homonimo` | sem CPF/CNPJ confirmado + nome frequente | só 1.357 contatos têm documento; Sisbajud exige CPF | alta |
| `executado_obito` | indício de óbito | autos, oficial, base pública, portal | alta |
| `executado_rj_falencia` | RJ/falência no DataJud | classes [A CONFERIR] | alta |
| `penhora_conta_terceiro_ou_salario` | bloqueio em conta de terceiro/conjunta ou verba impenhorável (CPC 833) | poupança ≤ 40 SM | alta |
| `titulo_indicio_fraude` | assinatura divergente, emitente nega, BO, cédula repetida | sinal visual/documental | alta |
| `garantidor_vulneravel` | idade ≥ 70, assinatura a rogo, sem outorga conjugal, PRONAF familiar | critério [A CONFERIR] | média |
| `diligencia_repetida_sem_fato_novo` | mesmo pedido em < 180 dias | ilustrativo | média |
| `prescricao_intercorrente_proxima` | data-limite da intercorrente **calculada por processo** a < **12 meses** sem diligência útil após o alerta (T08.1) | termo inicial e prazo do título [A CONFERIR] | alta |
| `valor_abaixo_piso_diligencia` | valor atualizado < **R$ 10.000** — critério (c) de carteira morta | `provisorio: true` — definir com o BASA (política do banco) | média |
| `processo_parado_90_dias` | processo viva/observação > **90 dias** sem movimentação útil → alerta + minuta de impulso automática | `provisorio: true` — alinhar ao SLA do contrato BASA | média |
| `carteira_morta_criterio_a` | Sisbajud + Renajud + Infojud negativos **e** > 3 anos sem movimentação útil | ambos os requisitos; intercorrente não entra | média |

## 8. Biblioteca de peças (M6)

Uma única estrutura de seções serve toda a biblioteca; `tipo_peca_prevista` escolhe o corpo. **Regra de citação:** saldo e data-base → página da planilha do BASA; fase/andamento → página do andamento/decisão; título → página da cédula. Sem página, sem afirmação.

Peças de impulso padrão (300 s) são processadas em **lote diário** e revisadas pelo **advogado da carteira** (decisão 5).

| Peça (`draft_type`) | Módulos | Piso de revisão |
|---|---|---|
| petição de impulso | T02 | 5 min |
| **requerimento cumulado Sisbajud (+ teimosinha) + Renajud + Infojud** (peça padrão após citação) | T02.2 | 5 min |
| requerimento Sisbajud / Renajud-Infojud (fallback sequencial, por juízo) | T02.2 | 5 min |
| requerimento CNIB / SREI | T02.3 | 5 min |
| manifestação sobre penhora negativa | T02.3 / T08 | 5 min |
| pedido de citação por edital / hora certa | T02.1 | 5 min |
| pedido de suspensão art. 921 (ou manifestação prévia §5º) | T08 / T01.1 | 5 min — em carteira morta só após decisão do **sócio** |
| cumprimento de sentença | T05 / T12 | 10 min |
| habilitação de herdeiros / espólio | T04.1 | 10 min — **sócio** |
| homologação de acordo | T09 / T09.1 | 10 min — após aprovação do BASA registrada |
| impugnação a embargos à execução | T06.x | **20 min** |
| resposta a exceção de pré-executividade | T07 | 20 min |
| incidente de desconsideração (IDPJ) | T04 | 20 min — **sócio** |

**Seções (na ordem):** 1 endereçamento e identificação · 2 situação processual (página; ≤ 10 linhas em impulso) · 3 do crédito exequendo (título, saldo, data-base, honorários — página da planilha do portal BASA; em impugnação, recálculo na data-base) · 4 fundamento do requerimento / da impugnação (impulso: um parágrafo — na peça cumulada, um parágrafo para o conjunto; impugnação: uma subseção por matéria alegada, nenhuma não alegada; em excesso de execução a primeira subseção é sempre a exigência da planilha com pedido de rejeição liminar) · 5 requerimentos (numerados, com valor e CPF/CNPJ em ordens a sistema; na cumulada os três pedidos em sequência + subsidiário de ao menos o Sisbajud; intimações do art. 889) · 6 registro de acordo (só após aprovação registrada; também para proposta ativa) · 7 rol de documentos.

**Estilo:** impulso em no máximo 1 página; nunca repetir pedido sem fato novo (e dizer qual é); valores sempre com data-base e página; executado e garantidor tratados com respeito; impenhorabilidades evidentes reconhecidas de plano; nenhuma referência legal não conferida.

## 9. Revisão (M7)

| Item | Regra |
|---|---|
| Piso de tempo (decisão 5) | **300 s (5 min)** para peças de impulso padrão (Sisbajud/Renajud/Infojud cumulado ou sequencial, citação por edital, manifestação sobre penhora negativa, art. 921) — peças de 1 página cujo risco está nos dados (saldo, CPF, fase), conferíveis em minutos contra a planilha e o andamento; **processamento em lote diário**; piso maior inviabiliza a carga (12 advogados × 1.500–1.950 processos). **600 s** para peças intermediárias (cumprimento, habilitação, homologação de acordo). **1.200 s (20 min)** para impugnação a embargos, resposta a exceção e IDPJ — peça de mérito com várias matérias, cálculo e risco de sucumbência. Medir nas primeiras 100 peças de cada tipo; ajustar só para cima. |
| Revisor | advogado com OAB responsável pela carteira BASA (peças padrão em lote diário) |
| Sócio (segunda revisão) | IDPJ e habilitação de herdeiros; acordo > R$ 100 mil (≈ p75, ilustrativo) ou desconto > 30 %; **carteira morta — toda decisão de parar / aceitar suspensão ou arquivamento 921 / requerer baixa, processo a processo, nunca em lote nem pelo advogado da carteira (decisão 3)**; dívida > R$ 276 mil (≈ p90); garantidor vulnerável; indício de fraude; medidas atípicas do 139 IV; primeira impugnação de cada subtese T06.x; primeira peça cumulada em cada órgão julgador |
| Checklist bloqueante | saldo/data-base/honorários = planilha (página); fase e último andamento conferidos, sem repetição; CPF/CNPJ válido em ordens a sistema; referências conferidas; nenhuma exceção aberta sem decisão humana; impugnação enfrenta só e todas as matérias alegadas **e, em excesso, exigiu planilha / pediu rejeição liminar / recalculou pelo portal BASA (R06)**; impenhorabilidades evidentes não atacadas; acordo com aprovação do BASA registrada; **R11 — intercorrente < 12 meses: a peça é diligência útil e sai antes da data-limite**; **R12 — peça cumulada só em juízo sem preferência sequencial**; **R13 — carteira morta: nenhuma ciência de suspensão/baixa sem decisão do sócio para este processo** |
| Checklist não bloqueante | impulso em 1 página com pedido específico e prazo; score/recomendação de triagem coerentes com a peça |
| Motivos de recusa | saldo divergente; diligência repetida; CPF ausente/homônimo; referência não conferida; exceção aberta; impugnação incompleta ou excessiva; excesso impugnado sem exigir planilha / sem rejeição liminar / sem recálculo; ataque a bem impenhorável; acordo sem aprovação; pedido genérico em processo com intercorrente < 12 meses; pedido cumulado em juízo que já o indeferiu |

## 10. Métricas (alinhadas aos KPIs do BASA)

| Id | Métrica | Meta (a confirmar) |
|---|---|---|
| M01 | **Valor recuperado por mês** (bloqueios, pagamentos, acordos cumpridos, arrematações) por tribunal/comarca/módulo | baseline 3 meses; depois +15 % |
| M02 | **Prazo médio até penhora efetiva** (citação → primeiro bloqueio > 0) | −30 % vs. baseline |
| M03 | **% processos vivos sem andamento útil > 90 dias** (gatilho de alerta + impulso automático — provisório, SLA do BASA) e % com minuta gerada no lote seguinte | < 5 %; 100 % com minuta em 1 dia útil |
| M04 | SLA de impulso após despacho | mediana ≤ 5 dias úteis; 95 % no prazo legal |
| M05 | **Custo por diligência e por R$ recuperado** (custas + correspondente + tokens) | < 10 % do recuperado |
| M06 | **Taxa de êxito em embargos/exceções** por subtese e comarca | ≥ baseline + 10 p.p. |
| M07 | **Carteira morta identificada** (nº e R$ por critério a/b/c; decisão do sócio registrada por processo; nº suspensos/baixados) | 100 % triada em 6 meses; relatório mensal ao BASA |
| M08 | Tempo médio de revisão por tipo de peça | impulso < 10 min; impugnação < 40 min |
| M09 | Aprovação sem alteração substancial | > 80 % impulsos; > 50 % impugnações |
| M10 | **Brier do score de recuperabilidade** (replay + prospectivo, horizonte 24 meses) | < 0,20; recalibrar trimestralmente |
| M11 | Prescrição intercorrente evitada × consumada (alerta < 12 meses) | 0 em processos vivos/observação |
| M12 | Qualidade de dados (CNJ válido e único, CPF/CNPJ, valor plausível, memória de cálculo) | > 95 % até o fim do piloto (hoje 93 % CNJ válido; 771 duplicados; 8,8 % sem valor) |
| M13 | **Processos com intercorrente < 12 meses sem diligência útil** (por comarca e faixa 0–3 / 3–6 / 6–12 meses — painel diário da fila T08.1) | 0 na faixa 0–3 meses; 3–12 zerada em 30 dias |
| M14 | Deferimento do pedido cumulado por órgão julgador (alimenta `preferencia_juizo_cumulado`) | mapa de 100 % dos juízos da amostra em 90 dias |
| M15 | Acordos propostos ativamente pela FBS (T09.1): recomendados → aprovados → aceitos → cumpridos | baseline no piloto; aceitação ≥ 30 % (ilustrativo) |

## 11. O que falta antes de `aprovado`

1. **Conferir** cada uma das 92 referências legais e os códigos CNJ (classes e assuntos) — abrir texto vigente, número do tema, ementa, modulação, jurisprudência atual do TJPA e do TJAM (sessão 2).
2. **Fixar** o prazo prescricional da CCB e da cédula rural (3 × 5 anos) — T06.5/T08/T08.1 —, o termo inicial da intercorrente (regime do 921 e transição do art. 1.056) e o tema repetitivo sobre diligências infrutíferas; sem isso o cálculo por processo da decisão 10 fica ilustrativo.
3. **Portal do BASA** ⏳ CLIENTE (dono: Gustavo): documentação/API solicitada — campos estruturados (título, garantias, saldo, memória de cálculo, fonte do recurso), quem acessa, frequência de atualização. Bloqueia o piloto.
4. **Obter do BASA** ⏳ CLIENTE (dono: Gustavo): política de alçadas e descontos por faixa/programa (necessária para a proposta ativa T09.1); programas de renegociação vigentes; régua contábil de baixa; **piso de valor para não diligenciar (hipótese R$ 10.000)**; **SLA contratual de impulso (hipótese 90 dias)**; quem adianta custas.
5. **Calibrar o score** (pesos e faixas) por replay sobre 200 processos encerrados; medir Brier (M10).
6. **Consolidar dados** antes do piloto: unificar os 4 cadastros do cliente, resolver os 771 CNJs duplicados e os 1.163 sem número/fora do padrão, recalcular os 128 valores > R$ 5 mi — e verificar se os andamentos (Legal One/DataJud) bastam para detectar "bens localizados" na seleção da amostra top-200; se não, aplicar o fallback (garantia real registrada no título).
7. **Confirmar** a preferência cumulado × sequencial dos principais órgãos julgadores (3ª Vara de Itacoatiara, varas de Tucuruí/Marabá/Belém) nas primeiras peças cumuladas (M14).
