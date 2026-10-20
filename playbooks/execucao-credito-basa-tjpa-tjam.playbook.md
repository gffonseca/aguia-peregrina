# Playbook — Execução / recuperação de crédito bancário em massa — polo ativo (credor = Banco da Amazônia) — TJPA + TJAM

> **Versão para leitura.** Este documento reproduz em prosa e tabelas o arquivo `execucao-credito-basa-tjpa-tjam.playbook.yaml`, que é a **fonte da verdade** ingerida pela plataforma. Comentários e correções podem ser feitos aqui; quem mantém o playbook transporta para o YAML e roda a validação. Se os dois divergirem, vale o YAML.
>
> **Estado: RASCUNHO (versão 1, 20/10/2026).** Autor: Gustavo Fonseca (OAB/PA 12.724). Primeira tipologia de **polo ativo** da Águia Peregrina. **Nada conferido:** nenhuma citação legal, código CNJ, número de tema ou súmula foi validado; todos os prazos, valores, pesos e faixas são **ilustrativos**. Tudo que está como **[A CONFERIR pelo advogado-dono]** segue pendente (89 referências legais no YAML). Pendências que dependem do cliente (portal do BASA, política de alçadas, programas vigentes) estão marcadas **⏳ CLIENTE**.

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

O score de recuperabilidade (T01) é a mesma função que o **pricing engine do spinoff de compra de créditos judiciais** calcula do outro lado do balcão: probabilidade × valor × prazo − custo. Os módulos de triagem, calendário de prescrição intercorrente (T08), carteira morta/cessão (T01.1) e qualidade de dados (M4) são reaproveitáveis diretamente no spinoff; os módulos de impulso e resposta a embargos são reaproveitáveis em qualquer carteira de credor (Banpará, financeiras, concessionárias).

**Ordem de prioridade decidida para a esteira (20/10/2026):** (1) triagem de recuperabilidade — separar carteira viva de carteira morta (T01); (2) peças repetitivas em massa — impulsos, Sisbajud/Renajud/Infojud, cumprimento de sentença, habilitação, suspensão art. 921 (T02–T05, T08, T12); (3) resposta a embargos e exceções de pré-executividade (T06, T07); (4) monitoramento de prazos/andamentos e priorização do que está parado (T08 + métricas M03/M04/M11).

## 1. Identificação

| Campo | Valor |
|---|---|
| Tipologia | `execucao_credito_bancario_basa` |
| Tribunal | TJPA (63,5 % da carteira) — TJAM (34,8 %) coberto pelo mesmo playbook (o schema aceita um tribunal por arquivo) |
| Polo / lado / réu-tipo | **Ativo** / autor / devedor PF ou PJ de crédito bancário |
| Peça padrão | petição de impulso da execução (biblioteca na seção 8) |
| Versão | 1 (rascunho) |
| Autor (OAB) | Gustavo Fonseca — PA 12724 |
| Revisões | nenhuma ainda |
| Aprovação | pendente |
| Piloto | **BASA** (carteira já patrocinada). Amostra de 200 processos: 100 TJPA interior (Tucuruí, Marabá, Rurópolis, Novo Progresso, Parauapebas, Altamira, Alenquer), 60 TJAM (Itacoatiara/Manaus), 40 Belém. Fase 1: T01 em replay (+200 encerrados para calibrar o score). Fase 2: impulsos. Fase 3: impugnações. Pré-requisito: mapear o portal do BASA em M3. |

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
**Subsídios:** portal do BASA (contratos/cédulas, garantias, extratos, saldo devedor e cálculo atualizado — acesso da FBS; detalhes a mapear ⏳ CLIENTE) + Legal One + DataJud.

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
| Título e valores | **titulo_tipo** (bloqueia), **titulo_localizado** (bloqueia), **titulo_requisitos_ok** (liquidez/certeza/exigibilidade — bloqueia), titulo_assinaturas_ok, valor_causa, **valor_divida_atualizado** (bloqueia), data_calculo_saldo, **memoria_calculo_disponivel** (bloqueia), valor_moeda_antiga_suspeito | **portal BASA ⏳ CLIENTE** |
| Encargos | taxa_juros_remuneratorios, encargos_capitalizacao_pactuada, encargos_comissao_permanencia, encargos_fno_programa | portal BASA |
| Garantias | garantia_tipo (hipoteca, penhor rural/mercantil, alienação fiduciária, aval, fiança, cessão de recebíveis), garantia_valor_estimado, garantia_registrada, garantia_matricula, avalistas_n, garantidor_terceiro_vulneravel | portal BASA / calculado |
| Datas do crédito | data_vencimento, data_inadimplemento, data_citacao, citacao_realizada, citacao_tentativas_n | portal BASA / andamentos |
| Executado | executado_tipo (PF/PJ), executado_cpf_cnpj_valido, executado_obito, executado_inventario_aberto, executado_recuperacao_judicial, executado_falencia, executado_homonimo_risco | autos / antifraude |
| Bens e diligências | bens_localizados, bens_tipos, sisbajud_tentativas_n / ultimo_resultado / ultima_data, renajud_consultado, infojud_consultado, cnib_consultado, matriculas_localizadas (SREI/DOI), penhora_conta_titularidade, penhora_verba_impenhoravel_indicio | andamentos / antifraude |
| Prescrição e suspensões | prescricao_titulo_data_limite (3 × 5 anos **[A CONFERIR]**), prescricao_intercorrente_risco, suspensao_921_data, arquivamento_data, suspensao_outra_causa (RJ, calamidade, Covid, convenção), programa_renegociacao_elegivel (Lei 13.340/2016, Lei 14.995/2024, PRONAF, securitização, Desenrola, política interna — **[A CONFERIR] quais vigentes** ⏳ CLIENTE), renegociacao_em_curso, cliente_orientou_suspender | calculado / portal BASA |
| Custos | custas_pendentes_valor, custo_diligencias_estimado (tabela por comarca — ilustrativa), honorarios_sucumbencia_fixados | andamentos / calculado |
| Triagem (T01) | score_recuperabilidade (0–1), recomendacao_triagem (viva_prioritaria / viva / observacao / morta_baixa / morta_cessao) | calculado |
| Incidentes defensivos | embargos_opostos, embargos_materia (excesso, iliquidez, capitalização, comissão de permanência, nulidade de citação, prescrição, renegociação rural…), embargos_planilha_apresentada, embargos_efeito_suspensivo, embargos_julgados_resultado, sentenca_embargos_transitada, excecao_pre_executividade_oposta, excecao_materia_cognoscivel_oficio, decisao_desfavoravel_transitada, indicio_fraude_cedula | autos / andamentos |
| Monitória | monitoria_embargos_opostos, monitoria_prazo_pagamento_decorrido | andamentos |
| Interior | carta_precatoria_necessaria, comarca_deprecada, correspondente_disponivel | calculado / FBS |
| Acordo | acordo_proposta_valor, acordo_desconto_pct | BASA / calculado |
| Qualidade de dados | cnj_duplicado, cadastro_cliente_id (3863 / 14574 / 15082 / 36641) | antifraude / Legal One |

## 4. Árvore de módulos de decisão ("teses")

Em polo ativo a "tese" raramente é um argumento de mérito: é a decisão do que fazer com o processo nesta fase. Cada módulo só dispara se **todas** as condições forem verdadeiras e as provas obrigatórias estiverem anexas; uma "prova que afasta" desativa o módulo e avisa o revisor.

### (1) Triagem

| Id | Módulo | Quando | Provas | Afastam | Fundamentação (a conferir) | Saída |
|---|---|---|---|---|---|---|
| **T01** | Triagem de recuperabilidade — score e carteira viva × morta | há saldo atualizado e fase conhecida | planilha do BASA; andamentos; garantias; relatório antifraude | saldo em moeda antiga (recalcular antes) | CPC 797/805; CPC 921; Res. CMN 2.682 e régua de baixa do BASA | score 0–1 + recomendação; **nenhuma peça** |
| **T01.1** | Carteira morta — baixa, arquivamento definitivo ou cessão em lote | recomendação morta_baixa / morta_cessao | relatório de triagem | garantia real não excutida | CPC 921 §§2º–5º; CC 286 (cessão); Res. CMN sobre cessão | relatório ao advogado da carteira e ao sócio (X03); alçada do BASA |

**Score (pesos ILUSTRATIVOS, soma 1,0 — calibrar por replay, métrica M10):** garantia real registrada ≥ 50 % da dívida 0,25 · bens localizados 0,20 · executado vivo e sem RJ/falência 0,15 · última diligência útil < 180 dias 0,10 · processo < 5 anos 0,10 · valor líquido ≥ R$ 30 mil 0,10 · CPF/CNPJ válido sem homonímia 0,10. **Faixas:** ≥ 0,70 viva_prioritaria · 0,45–0,69 viva · 0,25–0,44 observacao (só diligência barata periódica) · < 0,25 morta (baixa ou cessão). O score nunca extingue nada sozinho.

### (2) Impulso padrão por fase

| Id | Módulo | Quando | Provas | Afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T02** | Impulso padrão (tese-mãe) | carteira viva/observação; cliente não suspendeu; memória de cálculo disponível | planilha; andamentos | despacho recente já determinou a diligência | CPC 797, 798 I b, 829, 835, 854; STJ: Sisbajud sem esgotamento | diligência da fase (subteses) |
| **T02.1** | Citação pendente → endereços, hora certa, edital, arresto | não citado | certidões negativas | < 2 tentativas em endereços distintos (edital prematuro) | CPC 252–257, 256 §3º, 830; STJ nulidade de edital | consultas; hora certa/edital; arresto se há bens |
| **T02.2** | Citado sem pagamento → Sisbajud (+ teimosinha) | citado, prazo decorrido | certidão de decurso; saldo ≤ 30 dias | pagamento nos autos | CPC 829, 835 I, 854, 833 IV/X; STJ teimosinha; EREsp 1.582.475 | bloqueio contra todos os executados com reiteração |
| **T02.3** | Penhora frustrada → Renajud, Infojud, CNIB, SREI, outros bens | Sisbajud ≥ 1 negativo | detalhamento Sisbajud | Renajud/Infojud já cumpridos sem fato novo | CPC 835 II–XIII, 866, 139 IV, 772–773; Lei 8.009 art. 3º V; CF 5º XXVI; STJ Infojud e medidas atípicas | sequência de custo crescente; atípicas só com indício (sócio) |
| **T02.4** | Bens penhorados → avaliação, intimações, leilão/adjudicação | penhora formalizada | auto de penhora; matrícula | embargos de terceiro pendentes | CPC 838–844, 870–876, 879–903, 842, 889; Res. CNJ 236; preço vil 50 % | avaliação, registro, intimações, leilão eletrônico |
| **T03** | Penhora de safra, penhor rural, CPR; alienação fiduciária (rito próprio) | título rural com penhor | cédula com o bem; registro | bem pereceu | DL 167/67; Lei 8.929/94; Lei 13.986/2020; CC 1.438–1.446, 1.473; Lei 9.514/97; DL 911/69; CPC 833 VIII; Súmula 93 STJ | constatação/penhora do bem empenhado, depositário, percentual da safra |
| **T04** | IDPJ / redirecionamento a sócios | PJ, penhora frustrada, sem bens | QSA/Junta; diligências negativas; encerramento irregular | sócios já são avalistas (executar o aval) | CPC 133–137, 790 VII; CC 50; Súmula 435 (controversa na civil); REsp 1.526.287 | incidente — **sócio** |
| **T04.1** | Óbito → habilitação de espólio/herdeiros | óbito + inventário localizado | certidão de óbito; dados do inventário | inventário negativo | CPC 110, 313 I, 687–692, 779 II, 642; CC 1.792/1.997 | suspensão e habilitação; alternativa: habilitar crédito no inventário |
| **T05** | Cumprimento de sentença (embargos improcedentes, monitória, honorários) | sentença transitada favorável | sentença + trânsito; planilha com honorários | recurso com efeito suspensivo | CPC 523–525, 513 §2º, 85 §§1º/13; Tema 410 / Súmula 517 | intimação para pagar em 15 dias; multa e honorários 10 % |
| **T08** | Suspensão art. 921 III e prescrição intercorrente | suspensa/arquivada/penhora frustrada **e** > 90 dias sem andamento | decisão de suspensão; última diligência útil | prazo já consumado | CPC 921 §§1º–7º (Lei 14.195/2021), 1.056; IAC 1 STJ (REsp 1.604.412); Súmula 150 STF; tema sobre diligências infrutíferas **[A CONFERIR]** | viva: diligência útil antes do termo; morta: aceitar e relatório de baixa |
| **T10** | Carta precatória, interior, correspondentes | ato fora da comarca | despacho | — | CPC 237 III, 255, 260–268, 845 §2º, 848; Res. CNJ 354; normas TJPA/TJAM | precatória ou ato eletrônico/termo nos autos |
| **T12** | Monitória e conversão em execução | classe monitória | contrato + extratos; andamentos | há título executivo (via errada) | CPC 700–702; Súmulas 247, 384, 503/504 | constituição do título e cumprimento (T05) ou impugnação aos embargos monitórios |

**T08 — regra prática:** pedido genérico de "vista"/"prazo" não interrompe a intercorrente; só efetiva localização de bens (921 §4º-A). Processo em observação: 1 diligência útil a cada 10–11 meses (ilustrativo) enquanto houver prazo; processo morto: não gastar. A onda de 2015–16 é a primeira a passar pelo crivo.

### (3) Resposta a embargos e exceção de pré-executividade

| Id | Módulo | Quando | Provas | Afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T06** | Impugnação aos embargos (tese-mãe) | embargos pendentes; título e planilha disponíveis | petição de embargos; cédula; memória de cálculo | perícia já apontou excesso relevante | CPC 914–920; 783, 784 III/XII; Lei 10.931 art. 28; DL 167 art. 41; Súmulas 300, 233/247, 381 | rejeição liminar/improcedência; prosseguimento; honorários |
| **T06.1** | Excesso de execução — planilha do embargante (917 §§3º/4º) | matéria "excesso" | memória de cálculo | erro aritmético evidente | CPC 917 III, §§2º–4º; STJ rejeição sem planilha | rejeição liminar sem planilha; critério a critério com planilha |
| **T06.2** | Iliquidez — CCB/cédula rural são líquidas com a planilha | matéria "iliquidez" | cédula; planilha | abertura de crédito em conta sem CCB (Súmula 233) | Lei 10.931 art. 28 §2º; DL 167 arts. 10/41; CPC 783; Tema 576 STJ (REsp 1.291.575); Súmulas 233/247 | improcedência; subsidiário: fungibilidade para monitória |
| **T06.3** | Encargos — capitalização e comissão de permanência | matéria "capitalização" | cláusula destacada | cálculo cumula comissão de permanência; sem cláusula expressa | MP 2.170-36 art. 5º; DL 167 art. 5º; Lei 10.931 art. 28 §1º I; Res. CMN; Súmulas 539, 541, 472, 93, 382 STJ; 596 STF; Temas 246/247 | improcedência; subsidiário: recálculo sem comissão de permanência |
| **T06.4** | Nulidade de citação (edital/hora certa) | matéria "nulidade de citação" | certidões e consultas prévias | edital sem tentativa no endereço do título | CPC 239 §1º, 256 §3º, 257, 280; STJ comparecimento espontâneo | rejeição; subsidiário: aproveitamento dos atos |
| **T06.5** | Prescrição da pretensão executiva — 3 × 5 anos ⏳ PENDENTE | matéria "prescrição" | vencimento; data do ajuizamento/despacho | ajuizamento fora do prazo sem causa suspensiva | CC 206 §3º VIII / §5º I, 202; CPC 240 §§1º–3º; Lei 10.931 art. 44; DL 167 art. 60; Súmulas 503/504; jurisprudência sobre CCB **[A CONFERIR — risco de 3 anos]** | rejeição |
| **T06.6** | Renegociação/moratória rural — Lei 13.340/2016, Lei 14.995/2024, PRONAF, securitização ⏳ CLIENTE | matéria "renegociação rural" | cédula (fonte/data/valor); parecer do BASA | contrato enquadrável com pedido tempestivo não processado | Lei 13.340/2016; Lei 14.995/2024; Lei 11.775/2008; Lei 12.844/2013; MCR; Lei 14.690/2023; Leis 13.606/13.729/2018; tema repetitivo STJ **[A CONFERIR]** | improcedência por falta de enquadramento; se enquadra → acordo (T09) |
| **T07** | Resposta à exceção de pré-executividade | exceção pendente | petição; título e planilha | matéria de ordem pública evidente (óbito anterior, pagamento integral) | CPC 803 p.ú., 525 §11, 518; Súmula 393 STJ (analogia); STJ excesso não cabe em exceção | não conhecimento (via inadequada) + rejeição do que for de ordem pública |

### Sinais e subsidiária

| Id | Módulo | Quando | Fundamentação (a conferir) | Saída |
|---|---|---|---|---|
| **T09** | Acordo/renegociação — sinal por faixa, garantia e programa ⏳ CLIENTE | há proposta | CPC 3º §3º, 139 V, 190, 487 III b, 515 II, 922; política do BASA; leis rurais | recomendação FBS → aprovação BASA → homologação com suspensão (922) e cláusula de retomada |
| **T11** | Honorários, custas e despesas — recuperar; quem adianta | sempre que há valor | CPC 82 §2º, 85 §§1º/2º/13, 827; leis de custas TJPA/TJAM | inclusão na planilha; definir com o BASA quem adianta custas (contrato) |

## 5. Exceções — quando a esteira para

| Id | Situação | Ação |
|---|---|---|
| X01 | Executado falecido **sem** inventário localizado | escalar advogado da carteira (+ alerta) — suspensão 313 I; provável carteira morta |
| X02 | Executado em recuperação judicial ou falência | **sócio** — Lei 11.101 arts. 6º/49; habilitação no juízo universal [A CONFERIR regras de crédito rural/fiduciário] |
| X03 | Carteira morta (valor líquido < custo de diligências) | **sócio**; nenhuma peça; relatório de baixa/cessão (T01.1) |
| X04 | Indício de fraude na cédula | não gerar peça + sócio; comunicar compliance do BASA; flag, não rótulo |
| X05 | Garantidor terceiro vulnerável | alerta ao revisor + advogado da carteira |
| X06 | Decisão desfavorável ao exequente transitada | não gerar peça; advogado da carteira avalia ação autônoma ou baixa |
| X07 | Cliente orientou suspender | não gerar peça; sai do SLA de impulso enquanto durar |
| X08 | Renegociação administrativa em curso | sinalizar acordo (T09); não impulsionar penhora |
| X09 | Dados inconsistentes (CNJ duplicado, sem CPF/CNPJ, moeda antiga, saldo sem memória) | pedir subsídio + alerta; consolidar pastas antes de qualquer peça |
| X10 | Embargos/exceção com prazo fatal próximo | prioridade máxima na fila de revisão (15 dias — CPC 920 [A CONFERIR]) |

## 6. Sinais de acordo / renegociação

**Política (ILUSTRATIVA — a real é do BASA, por faixa de dívida e programa ⏳ CLIENTE).** Em polo ativo, acordo é instrumento de recuperação. Sem garantia real e sem bens: aceitar proposta que recupere mais que o valor presente esperado da execução (score × saldo − custos). Com garantia real excutível ou Sisbajud positivo: só desconto de encargos e parcelamento curto. Programas legais (Lei 13.340/2016 e sucessoras, PRONAF, securitização, Desenrola) prevalecem quando o contrato se enquadra.

- **Acordar:** carteira em observação/morta com proposta; programa legal aplicável; sem garantia, sem aval e sem bens.
- **Não acordar:** hipoteca registrada com desconto > 30 % (ilustrativo); título sob suspeita de fraude.
- **Faixas (aqui = faixa de DÍVIDA ATUALIZADA em que a plataforma sinaliza acordo por padrão sem garantia/bens; todas `provisorio: true`, recalibrar em 90 dias):**

| Grupo de comarcas | Faixa (R$) | Base |
|---|---|---|
| Belém e RMB (TJPA) | 0 – 60 mil | ≈ mediana da carteira (R$ 57,5 mil) |
| Interior do Pará — polos (Tucuruí, Marabá, Rurópolis, Novo Progresso, Parauapebas, Altamira, Alenquer…) | 0 – 100 mil | custo de diligência maior (precatória, correspondente) |
| TJAM — Itacoatiara e Manaus | 0 – 60 mil | CCB pequena (59,5 %); mediana R$ 55,6 mil |
| TJAM — interior (Boca do Acre, Humaitá, Manacapuru, Pauini…) | 0 – 100 mil | comarcas de difícil acesso |

**Fluxo de aprovação:** a **FBS recomenda** (valor, desconto %, parcelas, racional com score e custo; OAB do advogado da carteira) → o **BASA aprova** dentro da alçada interna (gestor/comitê, por faixa e programa — [A CONFERIR]) → a **plataforma registra** (quem, quando, valor, desconto, programa); a petição de homologação só é gerada após o registro. Homologar e **suspender** (CPC 922), não extinguir: descumprido, retoma pelo saldo com a cláusula penal.

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
| `prescricao_intercorrente_proxima` | suspensão > 1 ano e prazo a vencer em < 180 dias | prazo do título [A CONFERIR] | alta |

## 8. Biblioteca de peças (M6)

Uma única estrutura de seções serve toda a biblioteca; `tipo_peca_prevista` escolhe o corpo. **Regra de citação:** saldo e data-base → página da planilha do BASA; fase/andamento → página do andamento/decisão; título → página da cédula. Sem página, sem afirmação.

| Peça (`draft_type`) | Módulos | Piso de revisão |
|---|---|---|
| petição de impulso | T02 | 5 min |
| requerimento Sisbajud (+ teimosinha) | T02.2 | 5 min |
| requerimento Renajud / Infojud / CNIB / SREI | T02.3 | 5 min |
| manifestação sobre penhora negativa | T02.3 / T08 | 5 min |
| pedido de suspensão art. 921 (ou manifestação prévia §5º) | T08 | 5 min |
| pedido de citação por edital / hora certa | T02.1 | 10 min |
| cumprimento de sentença | T05 / T12 | 10 min |
| habilitação de herdeiros / espólio | T04.1 | 10 min — **sócio** |
| impugnação a embargos à execução | T06.x | **20 min** |
| resposta a exceção de pré-executividade | T07 | 20 min |
| incidente de desconsideração (IDPJ) | T04 | 20 min — **sócio** |
| homologação de acordo | T09 | 20 min — após aprovação do BASA registrada |

**Seções (na ordem):** 1 endereçamento e identificação · 2 situação processual (página; ≤ 10 linhas em impulso) · 3 do crédito exequendo (título, saldo, data-base, honorários — página da planilha) · 4 fundamento do requerimento / da impugnação (impulso: um parágrafo; impugnação: uma subseção por matéria alegada, nenhuma não alegada) · 5 requerimentos (numerados, com valor e CPF/CNPJ em ordens a sistema; intimações do art. 889) · 6 registro de acordo (só após aprovação registrada) · 7 rol de documentos.

**Estilo:** impulso em no máximo 1 página; nunca repetir pedido sem fato novo (e dizer qual é); valores sempre com data-base e página; executado e garantidor tratados com respeito; impenhorabilidades evidentes reconhecidas de plano; nenhuma referência legal não conferida.

## 9. Revisão (M7)

| Item | Regra |
|---|---|
| Piso de tempo | **300 s (5 min)** para peças de impulso — peças de 1 página cujo risco está nos dados (saldo, CPF, fase), conferíveis em minutos contra a planilha e o andamento; piso maior inviabiliza a carga (12 advogados × 1.500–1.950 processos). **600 s** para edital, cumprimento, habilitação. **1.200 s (20 min)** para impugnação a embargos, resposta a exceção, IDPJ e homologação de acordo — peça de mérito com várias matérias, cálculo e risco de sucumbência. Medir nas primeiras 100 peças de cada tipo; ajustar só para cima. |
| Revisor | advogado com OAB responsável pela carteira BASA |
| Sócio (segunda revisão) | IDPJ e habilitação de herdeiros; acordo > R$ 100 mil (≈ p75, ilustrativo) ou desconto > 30 %; baixa/arquivamento/cessão de carteira; dívida > R$ 276 mil (≈ p90); garantidor vulnerável; indício de fraude; medidas atípicas do 139 IV; relatório de baixa em lote; primeira impugnação de cada subtese T06.x |
| Checklist bloqueante | saldo/data-base/honorários = planilha (página); fase e último andamento conferidos, sem repetição; CPF/CNPJ válido em ordens a sistema; referências conferidas; nenhuma exceção aberta sem decisão humana; impugnação enfrenta só e todas as matérias alegadas; impenhorabilidades evidentes não atacadas; acordo com aprovação do BASA registrada |
| Checklist não bloqueante | impulso em 1 página com pedido específico e prazo; score/recomendação de triagem coerentes com a peça |
| Motivos de recusa | saldo divergente; diligência repetida; CPF ausente/homônimo; referência não conferida; exceção aberta; impugnação incompleta ou excessiva; ataque a bem impenhorável; acordo sem aprovação |

## 10. Métricas (alinhadas aos KPIs do BASA)

| Id | Métrica | Meta (a confirmar) |
|---|---|---|
| M01 | **Valor recuperado por mês** (bloqueios, pagamentos, acordos cumpridos, arrematações) por tribunal/comarca/módulo | baseline 3 meses; depois +15 % |
| M02 | **Prazo médio até penhora efetiva** (citação → primeiro bloqueio > 0) | −30 % vs. baseline |
| M03 | **% processos vivos sem andamento útil > 90 dias** (SLA do BASA) | < 5 % |
| M04 | SLA de impulso após despacho | mediana ≤ 5 dias úteis; 95 % no prazo legal |
| M05 | **Custo por diligência e por R$ recuperado** (custas + correspondente + tokens) | < 10 % do recuperado |
| M06 | **Taxa de êxito em embargos/exceções** por subtese e comarca | ≥ baseline + 10 p.p. |
| M07 | **Carteira morta identificada** (nº e R$ confirmados por sócio; nº baixados/cedidos) | 100 % triada em 6 meses; relatório mensal ao BASA |
| M08 | Tempo médio de revisão por tipo de peça | impulso < 10 min; impugnação < 40 min |
| M09 | Aprovação sem alteração substancial | > 80 % impulsos; > 50 % impugnações |
| M10 | **Brier do score de recuperabilidade** (replay + prospectivo, horizonte 24 meses) | < 0,20; recalibrar trimestralmente |
| M11 | Prescrição intercorrente evitada × consumada | 0 em processos vivos |
| M12 | Qualidade de dados (CNJ válido e único, CPF/CNPJ, valor plausível, memória de cálculo) | > 95 % até o fim do piloto (hoje 93 % CNJ válido; 771 duplicados; 8,8 % sem valor) |

## 11. O que falta antes de `em_revisao`

1. **Conferir** cada uma das 89 referências legais e os códigos CNJ (classes e assuntos) — abrir texto vigente, número do tema, ementa, modulação, jurisprudência atual do TJPA e do TJAM.
2. **Fixar** o prazo prescricional da CCB e da cédula rural (3 × 5 anos) — T06.5/T08 — e o tema repetitivo sobre diligências infrutíferas e intercorrente.
3. **Mapear o portal do BASA** (M3): campos estruturados disponíveis (título, garantias, saldo, memória de cálculo, fonte do recurso), quem acessa, frequência de atualização.
4. **Obter do BASA:** política de alçadas e descontos por faixa/programa; lista de programas de renegociação vigentes (Lei 13.340/2016, Lei 14.995/2024, PRONAF, securitização, Desenrola); régua contábil de baixa; quem adianta custas.
5. **Calibrar o score** (pesos e faixas) por replay sobre 200 processos encerrados; medir Brier (M10).
6. **Consolidar dados** antes do piloto: unificar os 4 cadastros do cliente, resolver os 771 CNJs duplicados e os 1.163 sem número/fora do padrão, recalcular os 128 valores > R$ 5 mi.
7. **Decidir** com o cliente o SLA contratual de impulso (90 dias é hipótese) e a amostra do piloto (200 processos: 100 TJPA interior, 60 TJAM, 40 Belém).
