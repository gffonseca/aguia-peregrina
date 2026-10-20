# Playbook — Reclamatória trabalhista típica (defesa do empregador) — TRT-8 (PA/AP)

> **Versão para leitura.** Este documento reproduz em prosa e tabelas o arquivo `trabalhista-reclamatoria-trt8.playbook.yaml`, que é a **fonte da verdade** ingerida pela plataforma. Comentários e correções podem ser feitos aqui (ou no Word exportado deste Markdown); quem mantém o playbook transporta para o YAML e roda a validação. Se os dois divergirem, vale o YAML.
>
> **Estado: RASCUNHO (versão 1).** Nenhuma citação legal, súmula, OJ, número, prazo ou valor foi conferido. Tudo que está entre colchetes como **[A CONFERIR pelo advogado-dono]** precisa ser validado por **advogado trabalhista** antes da aprovação — CLT pós-Reforma, Súmulas/OJs do TST, IN 41/2018, ADI 5.766, ADC 58/59, Lei 14.905/2024, Temas do STF, CCTs/ACTs e orientação das Turmas do TRT-8. Este é um ponto de partida, não conteúdo jurídico final.
>
> **Diferença estrutural:** a defesa é **por pedido**, há **audiência** (briefing e scoring pós-audiência) e o **acordo é modelado financeiramente por pedido** (pior cenário / provável / ideal).

## 1. Identificação

| Campo | Valor |
|---|---|
| Tipologia | `trabalhista_reclamatoria_tipica` |
| Tribunal | TRT-8 (PA/AP) |
| Lado / réu-tipo | Defesa / empresa empregadora (foco: terceirizadas de serviços, mineração e cadeia, call center, varejo) — ou tomador, quando o cliente for o tomador |
| Peça padrão | Contestação (+ anexos internos: briefing de audiência e modelagem de acordo) |
| Versão | 1 (rascunho) |
| Autor (OAB) | Gustavo Fonseca — OAB/PA 12.724 — revisão própria até nomear advogado-dono (advogado trabalhista) |
| Aprovação | pendente |

**Escopo.** Reclamatórias individuais com os pedidos recorrentes: horas extras e reflexos, intervalo intrajornada, insalubridade/periculosidade, verbas rescisórias, equiparação salarial, dano moral (assédio), reversão de justa causa, responsabilidade subsidiária do tomador; mais prescrição, limitação aos valores da inicial, gratuidade/honorários e juros/correção.

**Fora do escopo:** acidente grave/morte, doença ocupacional com incapacidade, ACP, dissídio coletivo, pejotização de executivo (X07).

**Antes de aprovar:** (1) conferir cada súmula/OJ/artigo/tema; (2) conferir orientação do TRT-8 sobre limitação aos valores da inicial, intervalo pós-reforma, equiparação, dano moral; (3) calibrar a modelagem de acordo (pior/provável/ideal) com a carteira do cliente por pedido e vara; (4) confirmar com RH/DP os subsídios entregáveis em 5 dias; (5) definir o valor X acima do qual o sócio revisa.

## 2. Como a plataforma reconhece a tipologia

- **Assuntos CNJ (códigos a conferir):** horas extras; intervalo intrajornada; adicional de insalubridade; de periculosidade; verbas rescisórias; equiparação salarial; dano moral; reversão de justa causa; responsabilidade subsidiária/terceirização. Classes: rito ordinário e sumaríssimo.
- **Palavras-chave:** reclamação trabalhista; reclamatória; horas extras; intervalo intrajornada; insalubridade; periculosidade; verbas rescisórias; equiparação; assédio moral; justa causa; responsabilidade subsidiária; tomador; terceirizada; banco de horas; cartão de ponto; TRCT; FGTS; multa do art. 477.
- **Excluem:** acidente com morte; doença ocupacional com incapacidade permanente; ACP; dissídio coletivo; ação de cumprimento; pejotização de executivo; desconsideração/grupo econômico.
- **Confiança mínima:** 0,85.

## 3. O que o dossiê precisa ter ("Claimant Profile")

| Campo | Origem | O que é |
|---|---|---|
| vara, rito, valor_causa, **pedidos** (bloqueia — lista com valor por pedido), pedidos_liquidados, valor_dano_moral_pedido, dano_moral_fundamento, data_ajuizamento, data_audiencia | autos | identificação e pedidos |
| **cliente_e_tomador** (bloqueia) | cliente | empregador direto × tomador |
| reclamante_pede_gratuidade, reclamante_ultimo_salario | autos / cliente | T01 |
| jornada_alegada, paradigma_indicado, testemunhas_reclamante | autos | para T05, T09, briefing |
| **contrato_trabalho_localizado** (bloqueia), data_admissao, data_rescisao, funcao_registrada, centro_custo, modalidade_rescisao, holerites_periodo_completo, cct_act_vigentes_localizadas | cliente | contrato e registro |
| **controle_ponto_tipo** (bloqueia: REP / manual / britânico / inexistente / isento art. 62), cartoes_ponto_periodo_completo, ponto_com_variacao, horas_extras_pagas_holerite, banco_horas_previsto_norma, banco_horas_extratos_localizados, empregados_estabelecimento_n, cargo_confianca_art62, trabalho_externo_art62_i, intervalo_pre_assinalado, intervalo_reduzido_autorizado | cliente | jornada (T05, T05.1, T05.2, T06) |
| pgr_ppra_localizado, ltcat_localizado, pcmso_aso_localizados, ficha_epi_localizada, epi_com_ca_valido, laudo_anterior_mesmo_setor, adicional_pago_holerite | cliente | ambiente (T07, T07.1) |
| trct_homologado_ou_assinado, comprovante_pagamento_rescisao, rescisao_paga_no_prazo, fgts_extrato_localizado, justa_causa_documentada, justa_causa_dias_entre_fato_e_dispensa, justa_causa_tipo | cliente | rescisão (T08, T08.1) |
| paradigma_mesma_funcao, paradigma_diferenca_tempo_funcao_anos, paradigma_diferenca_tempo_empregador_anos, quadro_carreira_homologado | cliente | equiparação (T09) |
| canal_denuncia_existente, denuncia_interna_registrada, apuracao_interna_realizada | cliente | dano moral (T10) |
| contrato_prestacao_servicos_localizado, fiscalizacao_tomador_documentada, tomador_ente_publico | cliente | terceirização (T11) |
| organograma_localizado, testemunhas_empresa_disponiveis | cliente | audiência |
| valor_pior_cenario, valor_provavel, valor_ideal_acordo, custo_pericia_estimado | calculado | modelagem de acordo |
| litispendencia_cnj, coisa_julgada_cnj, acoes_mesmo_reclamante_grupo_n, acoes_mesmo_advogado_mes_n, testemunha_reciproca, pedidos_identicos_serie_n, atestados_repetidos, historico_laudos_centro_custo | antifraude | cruzamentos |
| indicio_passivo_real | calculado | sinais de que o passivo é real |

## 4. Árvore de teses — uma por pedido típico

### Preliminares e processuais

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T01** | Impugnação à gratuidade e honorários (ADI 5.766) | pede gratuidade **e** salário > 40 % do teto do RGPS [atualizar] | holerites; CTPS digital/CNIS | desemprego comprovado e salário abaixo | CLT 790 §§3º/4º, 791-A; **ADI 5.766**; Súmula 463 (risco) | indeferir gratuidade; honorários (exigibilidade suspensa se gratuito) |
| **T02** | Litispendência / coisa julgada / quitação por acordo | processo em curso ou acordo anterior | cópia da inicial/sentença/termo | períodos/pedidos distintos; quitação restrita | CPC 337/485 (CLT 769); CLT 831 § único; Súmula 259; OJ 132 SDI-2 | extinção |
| **T03** | Limitação aos valores da inicial (art. 840 §1º; IN 41) | pedidos liquidados | inicial | ressalva de "estimativa" + TRT-8 acatando | CLT 840 §1º; CPC 141/492; IN 41 art. 12 §2º; **SDI-1: valores estimativos [A CONFERIR] — manter como subsidiária** | limitar condenação; ao menos custas/honorários |

### Prejudicial

| Id | Tese | Quando aplicar | Provas | Afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T04** | Prescrição bienal/quinquenal e FGTS | há datas de ajuizamento e admissão | ficha de registro/CTPS; TRCT | ação anterior arquivada (Súmula 268) / protesto | CF 7º XXIX; CLT 11; Súmulas 308, 362 (ARE 709.212), 268, 294 | total (CPC 487 II) ou parcial |

### Mérito — jornada

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T05** | Horas extras — ponto válido com variação (Súmula 338) e pagamento/compensação | ponto REP/manual **e** período completo **e** com variação | **cartões de todo o período**; **holerites com HE**; demonstrativo ponto × pagamento; escalas e norma | registros britânicos (338 III); períodos sem cartão com > 20 empregados (338 I); horas registradas não pagas | CLT 58, 59, 59-A/B, 74 §2º; CPC 373 I / CLT 818 I; Portaria 671; **Súmula 338**; 85; 444; 366; TRT-8 | improcedência; subsidiário: dedução (OJ 415), divisor (431), base (264), reflexos sem bis (OJ 394) |
| **T05.1** | Banco de horas / compensação por norma coletiva (subtese) | previsto em norma **e** extratos localizados | ACT/CCT; **extratos e quitação do saldo**; acordo individual | saldo não compensado/pago; habitualidade (85 IV/V) | CLT 59 §§2º/5º/6º, 611-A II; Súmula 85; **Tema 1.046 STF** | improcedência; subsidiário: só adicional (85 III/IV) |
| **T05.2** | Exceções do art. 62 — cargo de confiança / atividade externa (subtese) | controle_ponto_tipo = isento_art62 | registro com anotação e gratificação; **organograma com subordinados**; procurações/alçadas; para externos: ausência de rastreamento | gratificação < 40 %; existe ponto/GPS/roteiro | CLT 62 I, II, § único; TST (fidúcia especial) | improcedência; subsidiário: só além da 8ª/44ª |
| **T06** | Intervalo intrajornada — pré-assinalação e regime pós-reforma | intervalo_pre_assinalado = true | cartões com pré-assinalação; norma de redução; escala de refeição | intervalos < 1h sem norma; pré-assinalação com extras habituais | CLT 71 §4º (Lei 13.467), 74 §2º, 611-A III; Súmula 437 (só pré-reforma); Tema 1.046; TRT-8 | improcedência; subsidiário: só minutos suprimidos, indenizatório, sem reflexos |

**Erro mais grave em jornada:** afirmar ponto válido com registros britânicos anexos — inverte o ônus e dá credibilidade à jornada da inicial.

### Mérito — ambiente

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T07** | Insalubridade — ausência de agente / neutralização por EPI | LTCAT **e** fichas de EPI localizados | **PGR/PPRA**; **LTCAT com medições por função**; **fichas de EPI assinadas com CA**; PCMSO/ASOs; laudos judiciais anteriores favoráveis no setor; treinamentos | laudos anteriores desfavoráveis; fichas sem assinatura/CA/lacunas; laudo próprio reconhece agente acima do limite (ruído > 85 dB; biológico em limpeza hospitalar — Anexo 14); adicional já pago em grau menor | CLT 189–192, 195; NR-15, NR-6, NR-1, NR-7, **NR-22 (mineração)**, NR-17 Anexo II (call center); Súmulas 80, 289, 448, 47, 139, 228 / SV 4 | improcedência; subsidiário: grau do laudo, base no SM, período sem EPI, dedução, honorários periciais pelo reclamante (790-B) |
| **T07.1** | Periculosidade — fora da área de risco / exposição eventual (subtese) | LTCAT localizado | laudo com delimitação de áreas (NR-16/NR-20); descrição de atividades e layout; laudos anteriores | laudo próprio inclui o posto na área de risco; vigilante (Lei 12.740) ou motocicleta | CLT 193; NR-16; NR-20; Súmula 364; 361 e OJs 324/385 (riscos) | improcedência; subsidiário: 30 % do básico; não cumular |

### Mérito — rescisão

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T08** | Verbas rescisórias — TRCT, pagamento no prazo, FGTS, multas indevidas | TRCT assinado **e** comprovante de pagamento | **TRCT**; **comprovante bancário datado**; **extrato FGTS/GRRF**; aviso prévio | pagamento após 10 dias; competências de FGTS faltantes; base de cálculo sem médias | CLT 477 §§6º/8º/10, 467, 487; Lei 12.506; Lei 8.036 art. 18; Súmulas 330, 462 | improcedência de diferenças e multas; subsidiário: dedução, multa limitada, FGTS só faltante |
| **T08.1** | Justa causa — gradação, imediatidade, prova (subtese) | rescisão por justa causa **e** documentada | **advertências/suspensões**; **sindicância** (relatório, imagens, depoimentos, BO); comunicação com alínea; regulamento | lapso > 30 dias [A CONFERIR] (perdão tácito); dupla punição; prova só por preposto | CLT 482, 818 II; TST (requisitos); Súmula 32; TRT-8 | improcedência da reversão; subsidiário: verbas da imotivada sem dano moral; dedução |

### Mérito — equiparação

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T09** | Equiparação — fatos impeditivos do art. 461 | há paradigma indicado | **fichas de registro de ambos**; descrições de cargo; plano de cargos; avaliações | mesma função, mesmo estabelecimento, diferença de tempo abaixo dos limites, sem plano | CLT 461 §§1º–6º (Lei 13.467), 818 II; Súmula 6 (itens vigentes) | improcedência; subsidiário: só a partir dos requisitos; contemporaneidade; dedução |

### Mérito — dano moral

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T10** | Dano moral (assédio, revista, metas) — ausência de prova; canal de denúncia | há pedido de dano moral | **política e canal de denúncia com ciência**; **registro de ausência de denúncia ou apuração**; organograma; avaliações | denúncia registrada e não apurada / apuração confirmou; prints/áudios ofensivos; afastamento CID F contemporâneo | CLT 223-A a 223-G (ADI 6.050), 818 I; CC 186/927/944; CLT 2º; Lei 14.457/2022; TST (reiteração; metas; revista impessoal); TRT-8 (faixa) | improcedência; subsidiário: grau leve (223-G) |

**Sempre segunda revisão por sócio** em assédio (X04). Nunca minimizar o relato.

### Mérito — terceirização

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T11** | Responsabilidade subsidiária — licitude, fiscalização, limites (Súmula 331; Temas 725/246) | cliente é tomador **e** contrato localizado | **contrato de prestação**; **comprovantes de fiscalização** (retenção de notas, certidões, guias, folha, ponto); registro pela prestadora | nenhuma fiscalização; ordens diretas de prepostos do tomador | Lei 6.019 arts. 4º-A, 5º-A, 5º-D; Lei 8.666 art. 71 §1º / 14.133 art. 121; Súmula 331; **Temas 725, 246, 1.118**; limites (multas personalíssimas, período, benefício de ordem) | exclusão; subsidiário: limitação temporal/material, benefício de ordem |

### Subsidiária

| Id | Tese | Fundamentação (a conferir) | Pedido |
|---|---|---|---|
| **T12** | Parâmetros de liquidação — dedução, juros/correção (ADC 58/59 + Lei 14.905/2024), IR/INSS, perícia | CLT 879 §7º, 883, 790-B; Lei 8.177 art. 39; Lei 14.905; ADC 58/59; Súmula 368; OJs 400 e 415 | dedução global; IPCA-E pré-judicial + SELIC da citação, com a Lei 14.905 a partir da vigência [A CONFERIR]; retenções |

### Sinal (não é argumento autônomo)

| Id | Tese | Quando aplicar | Fundamentação (a conferir) | Providências |
|---|---|---|---|---|
| **T13** | Litigância em série / troca de favores | testemunha_reciproca = true **e** flags confirmados por advogado | CLT 793-A a 793-D, 829; CPC 447 §3º, 457; **Súmula 357 (limite da contradita)**; Recomendação CNJ; CIJ/Corregedoria TRT-8 | contradita **em audiência** com prova da reciprocidade (atas das duas ações); depoimento pessoal; exibição; comunicação institucional **sem imputar conduta a pessoa** |

## 5. Exceções — quando a esteira para

| Id | Situação | Ação |
|---|---|---|
| X01 | Contrato/registro/ponto/holerites não entregues | pedir subsídio |
| X02 | Sem ponto em estabelecimento > 20 empregados [A CONFERIR] | sinalizar acordo (jornada presumida — 338 I) |
| X03 | Indício de passivo real (sem EPI, rescisão fora do prazo, laudo anterior desfavorável, denúncia não apurada) | sinalizar acordo nos pedidos expostos |
| X04 | Dano moral por assédio moral/sexual | escalar ao sócio — segunda revisão obrigatória |
| X05 | Insalubridade/periculosidade com laudo anterior desfavorável no mesmo centro de custo | sinalizar acordo no pedido |
| X06 | Valor da causa > X do cliente (R$ 100 mil ilustrativo) [A CONFERIR] | alertar revisor; segunda revisão |
| X07 | Fora da tipologia (acidente/doença ocupacional grave etc.) | não gerar minuta |
| X08 | Justa causa sem documentação | sinalizar acordo (conversão em imotivada) |
| X09 | Audiência próxima sem organograma/testemunhas | alertar revisor — briefing incompleto |
| X10 | Tomador ente público (Tema 246/1.118) | alertar revisor |

## 6. Sinais de acordo — modelagem financeira por pedido

**Política.** O acordo é modelado **por pedido**: para cada um, a plataforma calcula

| Coluna | Como |
|---|---|
| **Pior cenário** | procedência total com reflexos, INSS/IR, honorários (5–15 %) e perícia, limitada aos valores da inicial |
| **Provável** | pior cenário × probabilidade de êxito do reclamante (taxa histórica da tese × vara × laudos do centro de custo — M04/M10) |
| **Ideal de acordo** | provável × fator de antecipação [A CONFERIR — ex.: 0,6–0,8], descontados custo de perícia, honorários e tempo |

Defender os pedidos com prova documental forte (ponto válido, EPI completo, TRCT no prazo) e acordar cedo — na audiência inicial, quando o cliente autorizar — os pedidos expostos. A plataforma apresenta a tabela e registra a decisão; **quem decide é o advogado/cliente.**

**Acordar quando:** passivo real · ponto inexistente/britânico · laudo anterior desfavorável · rescisão fora do prazo (pagar o incontroverso em audiência — art. 467) · rito sumaríssimo com ideal calculado.

**Não acordar quando:** REP com variação + HE pagas · laudo anterior favorável + EPI completo · reclamante com ≥ 2 ações contra o grupo · troca de favores detectada (instruir e contraditar antes).

**Faixas ilustrativas (sanity check — o valor que vale é o `valor_ideal_acordo` por pedido):**

| Grupo de varas | Faixa (R$) |
|---|---|
| Belém e RM (Belém, Ananindeua, Castanhal) | 3.000 – 25.000 |
| Sudeste — mineração e cadeia (Marabá, Parauapebas, Canaã dos Carajás, Tucuruí) | 8.000 – 60.000 |
| Oeste do PA e Amapá (Santarém, Altamira, Itaituba, Macapá, Santana) | 4.000 – 35.000 |
| Demais varas do TRT-8 | 3.000 – 30.000 |

**Alçadas [A CONFERIR]:** até R$ 10 mil, advogado trabalhista da carteira · até R$ 50 mil, sócio FBS + RH/jurídico do cliente · acima, comitê do cliente.

## 7. Antifraude específico da tipologia

> Nenhuma checagem produz rótulo de "fraudador"; só **flags com evidência**. Apenas decisão humana registrada com OAB confirma um flag.

| Código | O que verifica | Severidade | Já existe no M4? |
|---|---|---|---|
| procuracao_presente | procuração juntada | alta | sim |
| reclamante_multiplas_acoes_grupo | ≥ 2 ações contra empresas do mesmo grupo/tomador em 3 anos | média | não |
| testemunha_reciproca | testemunha do reclamante é autora de ação em que ele é testemunha, mesmo objeto | alta | não |
| pedidos_identicos_serie | ≥ 5 iniciais do mesmo escritório com pedidos/jornada/valores idênticos [a conferir] | média | não |
| atestados_repetidos | atestados idênticos (médico, texto, CID) entre reclamantes | média | não |
| jornada_inverossimil | jornada > 16h/dia por anos ou idêntica a outras iniciais | baixa | não |
| concentracao_advogado_mes | mesmo escritório > 20 ações/mês [calibrar] | baixa | não |
| concentracao_autor | mesmo reclamante com 3+ ações | média | sim |
| litispendencia | duplicidade ou acordo anterior com quitação | alta | sim |
| gratuidade_x_salario | gratuidade × salário > 40 % do teto / novo emprego | média | não |
| paradigma_em_serie | mesmo paradigma em ≥ 3 ações do mesmo escritório | baixa | não |
| laudo_centro_custo_historico | (a favor e contra) histórico de laudos no mesmo centro de custo — alimenta T07 e X05 | info | não |
| indicio_passivo_real | **a favor do reclamante**: sem ponto/EPI/TRCT no prazo, laudo desfavorável, denúncia não apurada | alta | não |

## 8. Modelo da contestação e anexos internos (seções, na ordem)

1. Endereçamento, qualificação, preposto e tempestividade
2. Síntese da reclamatória (contrato e pedidos com valores) — *com página*
3. Preliminares e questões processuais — T01, T02, T03 — *com página*
4. Prejudicial — prescrição — T04 — *com página*
5. Do contrato de trabalho — fatos (admissão → função/setor → jornada/escala → salário/adicionais → EPIs → afastamentos → punições → rescisão) — *cada evento com página*
6. Do mérito — jornada — T05, T05.1, T05.2, T06 — *com página*
7. Do mérito — insalubridade e periculosidade — T07, T07.1 (protesto por perícia com quesitos e assistente) — *com página*
8. Do mérito — rescisão — T08, T08.1 — *com página*
9. Do mérito — equiparação — T09 — *com página*
10. Do mérito — dano moral — T10 — *com página*
11. Do mérito — responsabilidade do tomador — T11 — *com página*
12. Parâmetros de liquidação — T12 — *com página*
13. Providências processuais — T13 (contradita fica para a audiência) — *com página*
14. Das provas (depoimento pessoal; testemunhas — 3 no ordinário / 2 no sumaríssimo; perícia; ofícios CNIS/CTPS digital)
15. Dos pedidos — por pedido da inicial, na mesma ordem
16. Rol de documentos
17. **ANEXO INTERNO — Briefing de audiência (não protocolar):** perguntas ao reclamante por pedido; perguntas às testemunhas e pontos de contradita (só com flag confirmado); testemunhas da empresa sugeridas a partir do organograma (gestor direto, colega do turno, técnico de segurança) e o que cada uma prova; o que o preposto precisa saber (art. 843 §1º); tabela de acordo por pedido com alçada; **campos de scoring pós-audiência** (qualidade do depoimento do reclamante 1–5, das testemunhas 1–5, postura do juízo, probabilidade revisada por pedido, nova faixa de acordo)
18. **ANEXO INTERNO — Modelagem financeira do acordo por pedido (não protocolar):** pedido × valor da inicial × pior cenário × probabilidade × provável × ideal; total; recomendação defender × acordar por pedido; natureza das parcelas (indenizatória × salarial) para INSS/IR

**Regra de citação:** toda afirmação de fato cita página ou documento anexo; jornada, pagamento e EPI identificados **por mês/competência**.

**Estilo:** impugnação específica pedido a pedido (CLT 841; CPC 341) — nunca negativa geral; súmulas/OJs só as conferidas, com redação pós-Reforma indicada quando houver diferença temporal; anexos internos nunca são protocolados.

## 9. Revisão (M7)

- **Tempo mínimo:** 25 minutos.
- **Revisor mínimo:** advogado trabalhista; **segunda revisão por sócio** se valor da causa > X [A CONFERIR], dano moral por assédio, indício de passivo real, justa causa, ou tomador ente público.

**Checklist do revisor** (B = bloqueia):

| Id | Item | |
|---|---|---|
| R01 | Cada fato tem citação de página/documento por competência | B |
| R02 | Súmulas, OJs, artigos e temas conferidos; redação pós-Reforma indicada | B |
| R03 | Impugnação específica de todos os pedidos (sem confissão ficta parcial) | B |
| R04 | T05 só com cartões completos, com variação, e holerites/demonstrativo | B |
| R05 | T07/T07.1 só com PGR/LTCAT + fichas de EPI com CA; laudos anteriores verificados | B |
| R06 | T08 só com TRCT + comprovante datado + FGTS; T08.1 só com advertências/sindicância | B |
| R07 | T11 só com contrato + fiscalização; limites pedidos | B |
| R08 | Nenhuma imputação de fraude sem flag confirmado; contradita não antecipada | B |
| R09 | Parâmetros de liquidação atualizados (ADC 58/59, Lei 14.905, OJ 415, Súmula 368, 790-B) | B |
| R10 | Briefing de audiência completo (preposto, testemunhas, perguntas, tabela de acordo) | B |
| R11 | Modelagem de acordo revisada; decisão defender × acordar registrada por pedido | B |
| R12 | Assédio: sócio revisou tom, exposição e canal de denúncia | B |
| R13 | Anexos internos separados da peça a protocolar | B |
| R14 | Tom respeitoso; sem minimizar relato de assédio ou condições em mineração/limpeza | |

**Motivos de recusa padrão:** fato sem prova · pedido sem impugnação específica · tese sem prova (jornada sem ponto; insalubridade sem EPI/laudo; justa causa sem gradação) · referência não conferida/superada/pré-Reforma aplicada a período posterior · parâmetros de liquidação ausentes · linguagem imputa fraude · briefing/modelagem ausentes · caso deveria ir para acordo em pedidos específicos.

## 10. Métricas

| Id | Métrica | Meta (a conferir) |
|---|---|---|
| M01 | Tempo médio de revisão | < 45 min |
| M02 | Aprovação sem alteração substancial | > 50 % após 200 casos |
| M03 | Subsídios faltantes detectados antes da defesa | > 90 % |
| M04 | Êxito por pedido × tese × vara (alimenta a probabilidade da modelagem) | ≥ baseline + 10 p.p. |
| M05 | Condenação média por pedido e vara | −20 % vs. baseline |
| M06 | Custo de tokens por processo (contestação + briefing + modelagem) | < US$ 4 |
| M07 | Concordância modelo × revisor sênior | > 0,85 |
| M08 | Flags confirmados por humano | recalibrar se < 50 % |
| M09 | Acordo realizado × ideal modelado; % fechados na audiência inicial | razão 0,8–1,2; > 40 % |
| M10 | Calibração da probabilidade por pedido (Brier) | < 0,20 após 300 pedidos |
| M11 | Scoring pós-audiência × resultado | monitorar; ajustar briefing |
| M12 | Perícias: resultado × histórico do centro de custo | > 75 % |

---

*Rascunho gerado em 19/10/2026 para validação por advogado trabalhista (advogado-dono). Fonte da verdade: `playbooks/trabalhista-reclamatoria-trt8.playbook.yaml`.*
