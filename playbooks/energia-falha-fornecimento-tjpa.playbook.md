# Playbook — Energia elétrica: interrupção, danos em equipamentos, TOI e negativação (defesa de distribuidora) — TJPA

> **Versão para leitura.** Este documento reproduz em prosa e tabelas o arquivo `energia-falha-fornecimento-tjpa.playbook.yaml`, que é a **fonte da verdade** ingerida pela plataforma. Comentários e correções podem ser feitos aqui (ou no Word exportado deste Markdown); quem mantém o playbook transporta para o YAML e roda a validação. Se os dois divergirem, vale o YAML.
>
> **Estado: RASCUNHO (versão 1).** Nenhuma citação legal, número, prazo ou valor foi conferido. Tudo que está entre colchetes como **[A CONFERIR pelo advogado-dono]** precisa ser validado antes da aprovação — em especial a numeração dos artigos da Res. Normativa ANEEL 1.000/2021 (versão consolidada), os Temas do STJ e a orientação das Câmaras Cíveis e Turmas Recursais do TJPA. Este é um ponto de partida, não conteúdo jurídico final.

## 1. Identificação

| Campo | Valor |
|---|---|
| Tipologia | `energia_falha_fornecimento` |
| Tribunal | TJPA |
| Lado / réu-tipo | Defesa / concessionária de distribuição de energia (foco: Equatorial Pará; Norte Energia e permissionárias em menor escala) |
| Peça padrão | Contestação |
| Versão | 1 (rascunho) |
| Autor (OAB) | Gustavo Fonseca — OAB/PA 12.724 — revisão própria até nomear advogado-dono da tipologia |
| Aprovação | pendente (nome, OAB e data/hora serão registrados no YAML) |

**Escopo.** Ações de consumidor por interrupção ou oscilação de fornecimento, queima de equipamentos, cobrança por recuperação de consumo (TOI/fatura de diferença), demora na religação, suspensão indevida e negativação. Pedidos típicos: inexigibilidade do débito, ressarcimento de equipamentos, repetição em dobro, dano moral, tutela de urgência (religação/baixa de negativação).

**Fora do escopo:** acidentes com rede elétrica, choque, morte, servidão/desapropriação, ações coletivas (exceção X08 — não gerar minuta).

**Antes de aprovar:** (1) conferir cada referência; (2) conferir artigos da Res. 1.000/2021 sobre ressarcimento de danos (prazo de 90 dias do pedido), TOI, DIC/FIC/DMIC e suspensão; (3) calibrar faixas de acordo por comarca separando capital e polos do interior (Santarém, Marabá, Castanhal); (4) confirmar com o cliente quais subsídios ele entrega em 5 dias úteis.

## 2. Como a plataforma reconhece a tipologia

- **Assuntos CNJ (códigos a conferir):** fornecimento de energia elétrica; dano moral/material — consumidor; inexigibilidade de débito; inclusão indevida em cadastro; cobrança indevida/recuperação de consumo.
- **Palavras-chave:** interrupção/falta/queda de energia; oscilação; apagão; queima de equipamento; eletrodoméstico; ressarcimento de danos; TOI; termo de ocorrência e inspeção; recuperação de consumo; fatura de diferença; irregularidade no medidor; religação; corte indevido; suspensão do fornecimento; unidade consumidora; Equatorial; Celpa; negativação.
- **Excluem:** servidão administrativa; desapropriação; linha de transmissão; tarifa social — ação coletiva; ACP; acidente com rede; choque elétrico; morte.
- **Confiança mínima:** 0,85.

## 3. O que o dossiê precisa ter

| Campo | Origem | O que é |
|---|---|---|
| comarca, juizado_especial, valor_causa, valores pedidos (moral/material), data_ajuizamento | autos | identificação básica |
| **subtipo** (bloqueia) | autos | interrupção / oscilação-equipamento / TOI / religação / suspensão / negativação / misto |
| **data_evento** (bloqueia) | autos | data do evento alegado |
| autor_pede_gratuidade, renda_declarada_autor, autor_pede_tutela_urgencia, tutela_deferida | autos | para T01 e X09 |
| autor_alega_dano_equipamento, equipamento_nota_fiscal_juntada, equipamento_nota_fiscal_hash, laudo_autor_generico | autos / antifraude | para T07 e antifraude |
| comprovante_endereco_titular, data_procuracao | autos | cruzamentos |
| **uc_numero** (bloqueia), uc_titular_e_autor, uc_classe | cliente | identificação da UC |
| historico_interrupcoes_uc, interrupcao_registrada_na_data, interrupcao_duracao_horas, causa_interrupcao, evento_climatico_registrado, evento_rede_basica, manutencao_programada_avisada | cliente | causa e duração (T06, T09) |
| compensacoes_dic_fic_pagas, compensacoes_valor_total | cliente | compensações regulatórias (T08) |
| ordens_servico, protocolo_reclamacao_autor, pedido_ressarcimento_formulado, pedido_ressarcimento_prazo_dias, vistoria_realizada, laudo_vistoria_conclusao, ressarcimento_administrativo_pago | cliente | procedimento de ressarcimento de danos (T07) |
| toi_lavrado, toi_assinado_ou_recusa, toi_pericia_medidor, toi_consumidor_notificado_pericia, toi_criterio_calculo, toi_contraditorio_administrativo, historico_consumo_queda, valor_toi | cliente | TOI (T10) |
| suspensao_por_inadimplencia, aviso_previo_suspensao, religacao_prazo_horas, faturas_em_aberto_n | cliente | corte/religação (T10.1) |
| negativacao_realizada, negativacao_preexistente, debito_negativado_origem | cliente | negativação (T11.1) |
| litispendencia_cnj, coisa_julgada_cnj, acoes_mesma_uc_n, acoes_mesmo_autor_mesmo_reu_n, acoes_mesmo_advogado_mes_n, acoes_mesmo_evento_mesma_comarca_n, nota_fiscal_repetida_n, autor_falecido | antifraude | cruzamentos |
| indicio_falha_real_distribuidora | calculado | sinais de que a falha foi real e imputável |

## 4. Árvore de teses

Cada tese só entra na peça se **todas** as condições forem verdadeiras e as provas obrigatórias estiverem anexas; se uma "prova que afasta" aparecer, a tese é desativada e o revisor é avisado.

### Preliminares

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T01** | Impugnação à gratuidade | pede gratuidade **e** renda > ~3 SM [A CONFERIR] | comprovante de renda; faturas com classe/consumo | UC baixa renda / tarifa social | CPC 98–100, 99 §2º; critério do TJPA | revogar/indeferir ou intimar; subsidiário: parcelar custas |
| **T02** | Ilegitimidade ativa — autor não é titular da UC | uc_titular_e_autor = false | cadastro da UC | prova de residência e pagamento das faturas | CPC 17/18/485 VI; CDC 2º e 17 (enfrentar bystander); precedentes STJ/TJPA | extinção; subsidiário: limitar ao que o autor suportou |
| **T03** | Litispendência | processo em curso com tríplice identidade | cópia da inicial/andamento | eventos/faturas distintos | CPC 337 VI/VII, 485 V | extinção; subsidiário: conexão |
| **T03.1** | Coisa julgada (subtese) | processo transitado | certidão de trânsito | — | CPC 337 VII §4º, 502, 508 | extinção |
| **T04** | Fracionamento de demandas (mesma UC/evento) | acoes_mesma_uc_n ≥ 2 | relatório antifraude | eventos realmente distintos | CPC 55/58/59, 5º/6º/77/80; precedentes; Recomendação CNJ; CIJPA | reunião no prevento; dano moral único |

### Prejudicial

| Id | Tese | Quando aplicar | Provas | Afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T05** | Prescrição | há data do evento e do ajuizamento | fatura/OS que fixa a data | reclamação/PID interruptivos | CDC 27 (5 anos); CC 206 §3º × 205 para repetição de tarifa [A CONFERIR tema STJ] | extinção; subsidiário: parcial |

**Risco:** em interrupções recorrentes o juízo pode considerar a pretensão renovada; usar só com data certa.

### Mérito — interrupção / oscilação

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T06** | Caso fortuito / força maior — evento climático amazônico ou perturbação na Rede Básica | interrupção registrada **e** causa ∈ {climática, terceiro, rede básica/ONS} | **registro do sistema** (alimentador, início/fim, causa); **boletim INMET/METAR**; relatório ONS/ANEEL; Defesa Civil; OS de campo | interrupções recorrentes no alimentador (fortuito interno); sem evento climático na data; demora injustificada no restabelecimento | CDC 14 §3º II; CC 393; Lei 8.987 art. 6º §3º; Res. 1.000/PRODIST 8 (expurgo de eventos) [A CONFERIR]; STJ fortuito externo × interno; TJPA | improcedência; subsidiário: compensação DIC/FIC esgota a reparação |
| **T07** | Ausência de nexo com o dano ao equipamento (laudo de vistoria / prazo do PID) | autor alega dano a equipamento | histórico do alimentador na data; laudo de vistoria; **registro do PID ou sua ausência (prazo de 90 dias [A CONFERIR])**; fotos | sobretensão registrada / várias queimas no alimentador; vistoria confirmou nexo ou não foi feita no prazo; laudo de assistência técnica idôneo | CDC 14 §3º I; CPC 373 I e §1º; **Res. 1.000 arts. 203 e ss. [A CONFERIR numeração e prazos]**; TJPA sobre exigência de PID; Súmula 297/inversão (enfrentar) | improcedência do dano material; subsidiário: menor valor de reparo, nota idônea, depreciação |
| **T08** | Compensações DIC/FIC/DMIC já creditadas | compensacoes_dic_fic_pagas = true | **fatura com o lançamento**; relatório de indicadores da UC | limites violados sem compensação, ou creditada só após a ação | Res. 1.000/PRODIST 8 [A CONFERIR]; CC 944; TJPA sobre efeito da compensação | improcedência do material; consideração no moral; abatimento |
| **T09** | Interrupção programada/emergencial no prazo regulatório | causa ∈ {programada, falha de rede, vegetação} **e** registrada | aviso prévio; registro; OS | duração acima do limite / recorrência; sem aviso | Lei 8.987 art. 6º §3º I; Res. 1.000 [A CONFERIR]; TJPA | improcedência |

**Erro mais rejeitado desta tipologia:** alegar "chuva forte" sem boletim INMET/METAR anexo. T06 só entra com o dado externo.

### Mérito — TOI / recuperação de consumo / corte

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T10** | Regularidade do TOI e da recuperação de consumo | subtipo TOI/misto **e** TOI lavrado **e** perícia do medidor realizada | **TOI** (fotos, assinatura/recusa); **laudo do medidor com notificação do consumidor**; **memória de cálculo**; **histórico de consumo com degrau**; notificação com prazo de recurso | perícia unilateral sem notificar / sem perícia; TOI sem assinatura/fotos/testemunhas; consumo estável antes e depois; critério ou período fora da regulação | Res. 1.000 (antiga 414 arts. 129–133) [A CONFERIR]; CDC 42 § único; CC 884; **STJ Tema 699 (corte por TOI) [A CONFERIR]**; STJ sobre TOI unilateral; TJPA | improcedência; subsidiário: recálculo em vez de anulação; sem dobro |
| **T10.1** | Suspensão por inadimplência regular com aviso prévio (subtese) | corte por fatura regular **e** aviso prévio | faturas vencidas; notificação; OS de corte/religação | pagamento anterior ao corte; corte por fatura de TOI; aviso só na fatura quando a regulação exige mais | Lei 8.987 art. 6º §3º II; Res. 1.000 [A CONFERIR]; Tema 699 | improcedência |

### Mérito — dano moral / negativação

| Id | Tese | Quando aplicar | Provas | Afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T11** | Inexistência de dano moral — mera interrupção / mero inadimplemento | há pedido de dano moral | duração e restabelecimento; ausência de corte/negativação | interrupção > 24h ou recorrente sem causa externa [A CONFERIR]; paciente dependente de equipamento; reclamações ignoradas; negativação/corte indevidos | CC 186/927/944; STJ interrupção curta sem dano presumido (e exceção para prolongada); faixa do TJPA; Súmula 385 | improcedência; subsidiário: quantum moderado, Súmula 362 |
| **T11.1** | Negativação legítima / Súmula 385 (subtese) | negativacao_realizada = true | fatura em aberto; registro da inscrição e notificação do órgão; extrato com anotações anteriores | pagamento anterior; débito de TOI em discussão | CDC 43 §2º; CC 188 I; Súmulas 385 e 359 STJ | improcedência; subsidiário: quantum reduzido |

### Subsidiária

| Id | Tese | Quando aplicar | Provas | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|
| **T12** | Limites do ressarcimento, repetição simples, compensação | sempre que há valor da causa | débitos em aberto e compensações pagas; orçamentos | CC 368–380, 884, 944; CDC 42 § único; Res. 1.000 (opções de ressarcimento); EAREsp 676.608 (modulação do dobro) | menor valor de reparo; repetição simples; compensação; dobro só pós-modulação |

### Sinal (não é argumento autônomo)

| Id | Tese | Quando aplicar | Provas | Fundamentação (a conferir) | Providências |
|---|---|---|---|---|---|
| **T13** | Sinais de litigância predatória regional (Santarém/Marabá/Castanhal) | advogado com ≥ N ações no mês (N = 30, a calibrar por comarca) **e** flags confirmados por advogado com OAB | relatório antifraude com decisão humana | CPC 77, 80, 139 III, 385, 481; Recomendação CNJ; CIJPA/NUMOPEDE | depoimento pessoal; exibição do equipamento/NF original; inspeção judicial da UC; comunicação institucional **sem imputar conduta a pessoa** |

## 5. Exceções — quando a esteira para

| Id | Situação | Ação |
|---|---|---|
| X01 | Histórico de interrupções/OS da UC não entregue | pedir subsídio (M3) |
| X02 | Indício de falha real imputável (interrupção longa sem causa externa, OS fora do prazo, negativação de débito pago) | sinalizar acordo |
| X03 | Interrupção > 24h [A CONFERIR] com causa falha de rede/desconhecida | escalar ao sócio |
| X04 | TOI sem perícia do medidor / sem notificação do consumidor | sinalizar acordo — T10 desativada |
| X05 | Corte por débito de TOI (Tema 699) | alertar revisor |
| X06 | Autor possivelmente falecido antes da procuração/ajuizamento | escalar ao sócio; sem minuta padrão |
| X07 | Valor da causa > R$ 50 mil [A CONFERIR — alçada do cliente] | alertar revisor; segunda revisão |
| X08 | Fora da tipologia (acidente, choque, morte, servidão) | não gerar minuta; reclassificar |
| X09 | Liminar deferida e religação > 24h [A CONFERIR] | alertar revisor — comprovar cumprimento antes da contestação |

## 6. Sinais de acordo

**Política:** defender quando há **causa externa comprovada (INMET/METAR/ONS) ou ausência de perturbação na data + compensação DIC/FIC paga + (no TOI) laudo com contraditório**. Acordar cedo quando a falha é real e imputável, quando o TOI não tem perícia válida, ou quando há negativação de débito pago. A plataforma sinaliza; **a decisão é do advogado/cliente**.

**Acordar quando:** indício de falha real · TOI sem perícia · negativação por TOI em discussão · vistoria própria confirmou o nexo · equipamento < R$ 1,5 mil com PID tempestivo [valores A CONFERIR].

**Não acordar quando:** causa climática/Rede Básica com registro externo · ≥ 3 ações pela mesma UC · autor não titular sem comprovante próprio · mesma nota fiscal em outra ação (antes de decisão humana).

**Faixas ilustrativas — substituir pela média de condenação da carteira (12 meses) por subtipo e comarca:**

| Grupo de comarcas | Faixa (R$) |
|---|---|
| Região Metropolitana de Belém | 800 – 3.000 |
| Oeste e sudeste — polos de litigância (Santarém, Marabá, Castanhal, Parauapebas, Altamira, Itaituba) | 1.000 – 4.000 |
| Interior — demais comarcas | 1.000 – 5.000 |

**Alçadas [A CONFERIR]:** até R$ 3 mil, advogado da carteira · até R$ 10 mil, sócio FBS + jurídico do cliente · acima, comitê do cliente.

## 7. Antifraude específico da tipologia

> Nenhuma checagem produz rótulo de "fraudador"; só **flags com evidência**. Apenas decisão humana registrada com OAB confirma um flag.

| Código | O que verifica | Severidade | Já existe no M4? |
|---|---|---|---|
| procuracao_presente | procuração juntada | alta | sim |
| procuracao_antiga | procuração com > 180 dias do ajuizamento [a conferir] | média | não |
| comprovante_endereco_terceiro | comprovante em nome de terceiro ou de UC diversa | média | não |
| autor_nao_titular_uc | autor não é titular da UC e não prova residência | média | não |
| multiplas_acoes_mesma_uc | ≥ 2 ações sobre a mesma UC em 12 meses | alta | não |
| acoes_em_serie_mesmo_evento | ≥ 10 ações pelo mesmo evento (data/alimentador) na comarca com o mesmo advogado | média | não |
| nota_fiscal_repetida | mesma NF de equipamento em mais de uma ação | alta | não |
| laudo_generico_repetido | laudo/orçamento ≥ 95 % similar a outros, sem série/modelo | média | não |
| equipamento_incompativel_uc | equipamentos incompatíveis com classe/consumo da UC | baixa | não |
| concentracao_advogado_mes | mesmo advogado > 30 ações/mês por comarca [calibrar] | baixa | não |
| concentracao_autor | mesmo autor com 3+ ações | média | sim |
| autor_falecido | óbito anterior à procuração | alta | não |
| litispendencia | processo duplicado | alta | sim |
| gratuidade_x_renda | gratuidade × renda/classe da UC | média | sim |
| peticao_padronizada | inicial ≥ 95 % similar sem individualizar data/UC/equipamento | baixa | não |
| evento_sem_registro_externo | data do evento sem interrupção registrada nem evento INMET/METAR — pode ser evento inexistente **ou** falha de registro do cliente | média | não |
| indicio_falha_real_distribuidora | **a favor do autor**: falha real nos próprios registros do cliente | alta | não |

## 8. Modelo da contestação (seções, na ordem)

1. Endereçamento, qualificação e tempestividade
2. Síntese da demanda (identificar subtipo) — *com página*
3. Preliminares — T01, T02, T03, T03.1, T04 — *com página*
4. Prejudicial — prescrição — T05 — *com página*
5. Dos fatos — a UC e o evento (linha do tempo: UC/titular → histórico → evento → OS → compensações → reclamação/PID → vistoria → TOI → faturas → corte/negativação → ajuizamento) — *cada evento com página*
6. Do mérito — regularidade do serviço e causa da interrupção — T06, T09, T08 (só subtipos de interrupção) — *com página*
7. Do mérito — inexistência de nexo com o dano ao equipamento — T07 — *com página*
8. Do mérito — regularidade do TOI e da recuperação de consumo — T10, T10.1 (enfrentar Tema 699 se houve corte) — *com página*
9. Da inexistência de dano moral — T11, T11.1 — *com página*
10. Pedidos subsidiários — T12 — *com página*
11. Providências processuais — T13 (só com flags confirmados) — *com página*
12. Das provas (depoimento pessoal, perícia no medidor/instalação, inspeção judicial, ofícios INMET/ONS/ANEEL)
13. Dos pedidos
14. Rol de documentos

**Regra de citação:** toda afirmação de fato cita a página dos autos ou o documento anexo identificado; dado meteorológico/ONS só com o documento-fonte anexo.

**Estilo:** português formal; frases curtas; sem adjetivar; artigos da Res. 1.000 só os conferidos; tom respeitoso com consumidor de tarifa social, comunidades ribeirinhas e pessoas com dependência de equipamento elétrico.

## 9. Revisão (M7)

- **Tempo mínimo:** 15 minutos.
- **Revisor mínimo:** advogado com OAB; **segunda revisão por sócio** se valor da causa > R$ 50 mil [A CONFERIR], autor possivelmente falecido, indício de falha real, ou interrupção > 24h.

**Checklist do revisor** (B = bloqueia):

| Id | Item | |
|---|---|---|
| R01 | Cada fato tem citação de página ou documento anexo | B |
| R02 | Referências legais e artigos da Res. 1.000 conferidos; nenhum placeholder | B |
| R03 | T06 só com registro do sistema + dado externo (INMET/METAR/ONS/Defesa Civil) | B |
| R04 | T10 só com TOI + laudo do medidor com notificação + memória de cálculo + histórico de consumo | B |
| R05 | T08 só com fatura que mostra a compensação | B |
| R06 | Nenhuma imputação de fraude sem flag confirmado | B |
| R07 | Subtipo, UC, datas e valores batem; seções não aplicáveis omitidas | B |
| R08 | Pedidos subsidiários presentes | B |
| R09 | Liminar deferida: cumprimento comprovado | B |
| R10 | Tom respeitoso; sem "mero aborrecimento" em interrupção prolongada/paciente dependente | |
| R11 | Sinal de acordo avaliado e registrado | |

**Motivos de recusa padrão:** fato sem prova citável · tese sem prova (fortuito sem dado externo; TOI sem laudo) · referência não conferida · subtipo/UC/valores divergentes · linguagem imputa fraude · caso deveria ir para acordo/escalada · liminar descumprida sem comprovação.

## 10. Métricas

| Id | Métrica | Meta (a conferir) |
|---|---|---|
| M01 | Tempo médio de revisão | < 30 min |
| M02 | Aprovação sem alteração substancial | > 60 % após 200 casos |
| M03 | Subsídios faltantes detectados antes da defesa | > 90 % |
| M04 | Êxito por tese × subtipo × comarca | ≥ baseline + 10 p.p. |
| M05 | Condenação média por subtipo e comarca | −20 % vs. baseline |
| M06 | Custo de tokens por processo | < US$ 2 |
| M07 | Concordância modelo × revisor sênior | > 0,85 |
| M08 | Flags confirmados por humano | recalibrar se < 50 % |
| M09 | Acordos sinalizados × realizados | calibrar trimestralmente |
| M10 | Cobertura de dado externo em T06 | 100 % |
| M11 | Clusters de ações em série por evento detectados antes da 1ª contestação | monitorar |

---

*Rascunho gerado em 19/10/2026 para validação pelo advogado-dono. Fonte da verdade: `playbooks/energia-falha-fornecimento-tjpa.playbook.yaml`.*
