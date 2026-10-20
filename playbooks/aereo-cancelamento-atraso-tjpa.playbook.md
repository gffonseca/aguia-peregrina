# Playbook — Transporte aéreo: cancelamento, atraso, preterição e bagagem (defesa de companhia aérea) — TJPA

> **Versão para leitura.** Este documento reproduz em prosa e tabelas o arquivo `aereo-cancelamento-atraso-tjpa.playbook.yaml`, que é a **fonte da verdade** ingerida pela plataforma. Comentários e correções podem ser feitos aqui (ou no Word exportado deste Markdown); quem mantém o playbook transporta para o YAML e roda a validação. Se os dois divergirem, vale o YAML.
>
> **Estado: RASCUNHO (versão 1).** Nenhuma citação legal, número, prazo ou valor foi conferido. Tudo que está entre colchetes como **[A CONFERIR pelo advogado-dono]** precisa ser validado antes da aprovação — em especial os artigos da Res. ANAC 400/2016 (versão consolidada), o alcance do Tema 210 do STF (RE 636.331) e a jurisprudência do STJ sobre dano moral em atraso. Este é um ponto de partida, não conteúdo jurídico final.
>
> **Escopo: SOMENTE DEFESA.** O spinoff de compra de créditos judiciais opera esta mesma tipologia pelo lado do autor; este playbook não cobre esse lado e não deve ser reaproveitado para ele.

## 1. Identificação

| Campo | Valor |
|---|---|
| Tipologia | `aereo_cancelamento_atraso` |
| Tribunal | TJPA |
| Lado / réu-tipo | Defesa / companhia aérea (foco: Azul, LATAM, Gol operando no PA — BEL, STM, MAB, ATM, CKS) |
| Peça padrão | Contestação |
| Versão | 1 (rascunho) |
| Autor (OAB) | Gustavo Fonseca — OAB/PA 12.724 — revisão própria até nomear advogado-dono da tipologia |
| Aprovação | pendente |

**Escopo.** Cancelamento ou atraso de voo, perda de conexão, preterição de embarque (overbooking), extravio/avaria/violação de bagagem e falhas de assistência material. Pedidos típicos: dano moral, dano material (despesas, diárias, bens), reembolso.

**Fora do escopo:** acidente aéreo, milhas/fidelidade, cobrança indevida no cartão, pacote de agência (X08).

**Antes de aprovar:** (1) conferir artigos da Res. 400 (assistência por faixa de atraso, reacomodação, reembolso, aviso de 72h, bagagem); (2) conferir Tema 210 STF e seu alcance (bagagem × dano moral); STJ sobre dano moral por atraso (prova × in re ipsa) e limite de bagagem; (3) calibrar faixas por comarca e subtipo; (4) confirmar com o cliente formato e prazo de entrega de PNR, status do voo, código de motivo, METAR/TAF, vouchers, PIR.

## 2. Como a plataforma reconhece a tipologia

- **Assuntos CNJ (códigos a conferir):** transporte aéreo; dano moral/material — consumidor; atraso de voo; cancelamento de voo; extravio de bagagem; overbooking.
- **Palavras-chave:** cancelamento/atraso de voo; voo cancelado/atrasado; perda de conexão; overbooking; preterição; extravio/bagagem danificada/violada; reacomodação; assistência material; Resolução 400; ANAC; companhia aérea; Azul; LATAM; Gol; localizador; no-show.
- **Excluem:** acidente aéreo; queda de aeronave; cobrança no cartão; milhas; fidelidade; pacote de agência; aeronauta.
- **Confiança mínima:** 0,85.

## 3. O que o dossiê precisa ter

| Campo | Origem | O que é |
|---|---|---|
| comarca, juizado_especial, valor_causa, valores pedidos, dano_material_comprovado, data_ajuizamento | autos | identificação básica |
| **subtipo** (bloqueia) | autos | cancelamento / atraso / perda de conexão / overbooking / bagagem (extravio, avaria, violação) / assistência / misto |
| **voo_internacional** (bloqueia) | autos | regime da Convenção de Montreal |
| **data_voo** (bloqueia) | autos | data do voo original |
| autor_pede_gratuidade, renda_declarada_autor | autos | T01 |
| autor_alega_compromisso_perdido, compromisso_comprovado, autor_menor_idoso_pcd | autos | agravantes do dano moral (T12, X04) |
| comprovante_endereco_titular, comprovante_endereco_uf, data_procuracao | autos | foro e antifraude |
| **pnr** (bloqueia), pnr_autor_e_passageiro, passageiro_fez_checkin, passageiro_embarcou_reacomodacao, passageiro_no_show | cliente | reserva e embarque |
| **status_voo** (bloqueia), atraso_total_horas, motivo_codigo, **motivo_categoria** (bloqueia) | cliente | o que aconteceu e por quê |
| metar_taf_disponivel, metar_condicao_abaixo_minimos, outras_cias_afetadas_mesmo_dia, manutencao_registro_disponivel | cliente | prova da causa (T06, T07) |
| comunicacao_previa_horas, comunicacao_meio, assistencia_prestada, assistencia_comprovantes_disponiveis, opcao_oferecida, opcao_escolhida_passageiro, reembolso_realizado | cliente | Res. 400 (T08, T08.1) |
| overbooking_voluntarios_chamados, overbooking_compensacao_paga | cliente | T09 |
| pir_registrado, bagagem_entregue_dias, bagagem_conteudo_declarado, bagagem_indenizacao_paga | cliente | T11 |
| reclamacao_administrativa_previa | cliente | contexto |
| litispendencia_cnj, coisa_julgada_cnj, acoes_mesmo_pnr_n, acoes_mesmo_autor_mesmo_reu_n, acoes_mesmo_advogado_mes_n, acoes_mesmo_voo_n, autor_domicilio_outra_uf, autor_falecido | antifraude | cruzamentos |
| indicio_falha_real_cia | calculado | falha imputável sem assistência |

## 4. Árvore de teses

### Preliminares

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T01** | Impugnação à gratuidade | pede gratuidade **e** renda > ~3 SM [A CONFERIR] | comprovante de renda; histórico de viagens/classe | renda ≤ limite | CPC 98–100, 99 §2º; TJPA | revogar/indeferir ou intimar |
| **T02** | Incompetência territorial — foro artificial | autor_domicilio_outra_uf = true | cadastro do PNR (endereço, DDD); relatório antifraude (outras ações, comprovante de terceiro) | comprovante idôneo na comarca ou voo com origem/destino na comarca | CDC 101 I (domicílio **real**); CPC 64/65/337 II; CC 70–72; Lei 9.099 art. 4º; TJPA sobre foro de conveniência | declínio ao domicílio real; subsidiário: intimar a comprovar residência |
| **T03** | Litispendência | processo em curso | cópia da inicial/andamento | voos distintos | CPC 337 VI/VII, 485 V | extinção; conexão |
| **T03.1** | Coisa julgada | processo transitado | certidão de trânsito | — | CPC 337 VII §4º, 502, 508 | extinção |
| **T04** | Fracionamento (um PNR, várias ações; ida/volta; bagagem separada) | acoes_mesmo_pnr_n ≥ 2 | relatório antifraude; PNR completo | passageiros com danos próprios (criança, PcD) | CPC 55/58/59, 5º/6º/77/80; precedentes; Recomendação CNJ | reunião; dano moral em conjunto |

**Atenção:** incompetência relativa (T02) só nas preliminares da contestação — omissão prorroga a competência.

### Prejudicial

| Id | Tese | Quando aplicar | Provas | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|
| **T05** | Prescrição — CDC 27 (5 anos, doméstico) / Montreal art. 35 (2 anos, internacional) | há data do voo e do ajuizamento | PNR com data e natureza do voo | CDC 27; Montreal art. 35; CBA 317; **STF Tema 210 (RE 636.331)** | extinção |

**Risco:** prazo bienal só no internacional; verificar se o tribunal o estende ao dano moral.

### Mérito — causa do atraso/cancelamento

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T06** | Força maior — meteorologia (METAR/TAF) ou ATC/infraestrutura | motivo ∈ {meteorologia, ATC/infra} **e** voo atrasado/cancelado/desviado | **registro do voo** (horários, código); **METAR/TAF** da janela (REDEMET/ICEA) com leitura dos mínimos; NOTAM; painel de voos de outras cias | METAR dentro dos mínimos ou adverso só horas depois; outras cias operaram; código de motivo comercial divergente | CDC 14 §3º II; CC 393/734; CBA 256 §1º b, 230; Res. 400 arts. 20–27 (assistência subsiste); Montreal 19; STJ fortuito externo × previsibilidade; TJPA com METAR | improcedência; subsidiário: assistência mitigou (T08) |
| **T07** | Manutenção não programada / segurança de voo | motivo ∈ {manutenção, segurança} **e** há registro técnico | registro do voo; **log de manutenção / MEL / relatório de pane** e liberação; providências de reacomodação | falha recorrente ou manutenção vencida; sem registro correspondente | CBA/RBAC 121/135 (aeronavegabilidade); CDC 14 §3º I; **STJ: fortuito interno [A CONFERIR] — usar como mitigação**; TJPA | improcedência; subsidiário: quantum reduzido pela diligência |

**Defesa mais rejeitada da tipologia:** "mau tempo" sem METAR/TAF anexo. T06 bloqueada sem o dado (X05).

### Mérito — cumprimento da Res. ANAC 400/2016

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T08** | Cumprimento integral da Res. 400 — informação, assistência, reacomodação, reembolso | há comprovantes de assistência **e** alguma alternativa foi oferecida | **registro de aviso** (data/hora/meio); **vouchers** de alimentação/hotel/transporte em nome do passageiro; **registro da oferta e opção escolhida**; comprovante de reembolso | vouchers de outro passageiro/data ou ausentes para a faixa atingida; aviso < 72h em alteração programada; reacomodação só dias depois sem outra cia/reembolso | Res. 400 arts. 12, 20–22, 21, 26–27 (1h/2h/4h), 28–29 [A CONFERIR cada prazo]; CDC 6º III, 14, 20; CC 741; STJ assistência reduz/afasta dano moral; TJPA | improcedência; subsidiário: redução substancial |
| **T08.1** | Reembolso integral já efetuado (subtese) | reembolso_realizado = true | comprovante do estorno; registro da escolha | parcial, em crédito recusado, ou fora de 7 dias [A CONFERIR] | Res. 400 arts. 28–29; CC 884 | improcedência do material |
| **T09** | Overbooking — voluntários e compensação paga | subtipo overbooking/misto **e** voluntários chamados | registro operacional da chamada; **comprovante de compensação (DES)**; assistência | sem voluntários; compensação não paga/abaixo do mínimo | Res. 400 arts. 22–24 (250/500 DES) [A CONFERIR]; CC 944; STJ (in re ipsa × compensação) | improcedência; subsidiário: abatimento |
| **T10** | No-show / culpa exclusiva do passageiro | passageiro_no_show = true **e** voo operou no horário | voo no horário com horários de fechamento; PNR sem check-in; comunicação dos limites | voo antecipado sem aviso; fila da própria cia; conexão no mesmo bilhete | CDC 14 §3º II; Res. 400 (tempo de apresentação); STJ/TJPA | improcedência |

**Erro mais comum:** afirmar assistência prestada sem voucher em nome do passageiro anexo.

### Mérito — bagagem

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T11** | Bagagem — devolução rápida, sem declaração de valor, limite de Montreal (internacional), PIR | subtipo bagagem/misto **e** PIR registrado | **PIR**; **comprovante de entrega ou indenização**; etiqueta/ausência de declaração de valor; ressarcimento administrativo | não localizada após 7 dias doméstico / 21 internacional [A CONFERIR] ou violada com registro; PIR recusado no balcão | Res. 400 arts. 32–35 [A CONFERIR]; Montreal 17, 22 (1.288 DES [A CONFERIR]), 31; CDC 14 / CC 734 § único; **STF Tema 210** (só dano material); STJ extravio temporário; TJPA | improcedência do moral (temporário breve); material limitado ao comprovado/teto |

### Mérito — dano moral

| Id | Tese | Quando aplicar | Provas | Afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T12** | Inexistência de dano moral — atraso < 4h / sem circunstância concreta | há pedido de dano moral | horário real de chegada; assistência | atraso ≥ 4h [A CONFERIR] ou pernoite não assistido; compromisso comprovado; passageiro vulnerável | CC 186/927/944; Res. 400 art. 26 (4h); **STJ REsp 1.584.465 e precedentes — dano moral por atraso não presumido [A CONFERIR número/tema]**; TJPA/Turmas Recursais; faixa local; Súmula 362 | improcedência; subsidiário: quantum moderado |

### Subsidiária

| Id | Tese | Provas | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|
| **T13** | Limites do dano material, abatimentos, juros/correção | valores pagos; documentos de despesas do autor | CC 402/403/944; CPC 373 I; Montreal 19 e 22 (5.346 / 1.288 DES [A CONFERIR]); Súmulas 362 e 54; Lei 14.905/2024 | material só o comprovado; abater pagos; juros da citação (contratual) e correção do arbitramento; tetos no internacional |

### Sinal (não é argumento autônomo)

| Id | Tese | Quando aplicar | Fundamentação (a conferir) | Providências |
|---|---|---|---|---|
| **T14** | Sinais de litigância predatória | advogado ≥ N ações/mês (30, a calibrar) **e** flags confirmados por advogado | CPC 77, 80, 139 III, 385; Recomendação CNJ; CIJPA | depoimento pessoal (embarque, bagagem, domicílio); exibição de cartão de embarque, comprovante de residência atual, originais dos gastos; comunicação institucional **sem imputar conduta a pessoa** |

## 5. Exceções — quando a esteira para

| Id | Situação | Ação |
|---|---|---|
| X01 | Motivo do voo desconhecido / PNR não entregue | pedir subsídio |
| X02 | Indício de falha real imputável sem assistência | sinalizar acordo |
| X03 | Autor não consta como passageiro no PNR | escalar ao sócio |
| X04 | Passageiro vulnerável com atraso ≥ 12h [A CONFERIR] | escalar ao sócio |
| X05 | Motivo meteorológico sem METAR/TAF | pedir subsídio — T06 bloqueada |
| X06 | Autor possivelmente falecido | escalar ao sócio |
| X07 | Valor da causa > R$ 50 mil [A CONFERIR] | alertar revisor; segunda revisão |
| X08 | Fora da tipologia | não gerar minuta |
| X09 | Voo internacional (Convenção de Montreal) | alertar revisor — Tema 210: prazo e tetos só para dano material |

## 6. Sinais de acordo

**Política:** defender quando há **causa externa documentada (METAR/TAF/NOTAM) ou culpa do passageiro + assistência comprovada com vouchers**. Acordar cedo quando o motivo é comercial/malha, falta comprovante de assistência, atraso longo com vulnerável, ou bagagem não devolvida. **A decisão é do advogado/cliente.** Só defesa — o lado do autor é do spinoff.

**Acordar quando:** indício de falha real · motivo malha/tripulação/comercial com atraso ≥ 4h · sem voucher com atraso ≥ 4h · bagagem > 7 dias · overbooking sem voluntários [valores A CONFERIR].

**Não acordar quando:** meteorologia/ATC com METAR abaixo dos mínimos + assistência · no-show em voo no horário · atraso < 4h sem compromisso alegado · ≥ 3 ações pelo mesmo PNR · foro artificial (arguir incompetência antes).

**Faixas ilustrativas — substituir pela média de condenação da carteira por subtipo e faixa de atraso:**

| Grupo de comarcas | Faixa (R$) |
|---|---|
| Região Metropolitana de Belém | 1.000 – 4.000 |
| Interior — polos com aeroporto (Santarém, Marabá, Altamira, Parauapebas) | 1.500 – 5.000 |
| Interior — demais comarcas (atenção a foro de conveniência sem aeroporto) | 1.500 – 6.000 |

**Alçadas [A CONFERIR]:** até R$ 3 mil, advogado da carteira · até R$ 10 mil, sócio FBS + jurídico do cliente · acima, comitê do cliente.

## 7. Antifraude específico da tipologia

> Nenhuma checagem produz rótulo de "fraudador"; só **flags com evidência**. Apenas decisão humana registrada com OAB confirma um flag.

| Código | O que verifica | Severidade | Já existe no M4? |
|---|---|---|---|
| procuracao_presente | procuração juntada | alta | sim |
| procuracao_antiga | procuração > 180 dias [a conferir] | média | não |
| comprovante_endereco_terceiro | comprovante de terceiro | média | não |
| comprovante_endereco_outra_uf | comprovante na comarca, mas PNR/DDD/outras ações apontam outra UF (forçar foro) | alta | não |
| mesmo_pnr_varias_acoes | mesma reserva em ≥ 2 ações | alta | não |
| passageiro_nao_embarcou | pede por atraso/bagagem mas há no-show ou nenhuma bagagem despachada | alta | não |
| autor_nao_consta_pnr | autor não é passageiro da reserva | alta | não |
| acoes_em_serie_mesmo_voo | ≥ 10 ações pelo mesmo voo com o mesmo advogado [a conferir] | média | não |
| concentracao_advogado_mes | mesmo advogado > 30 ações/mês [calibrar] | baixa | não |
| concentracao_autor | mesmo autor com 3+ ações (viajante litigante) | média | sim |
| autor_falecido | óbito anterior à procuração | alta | não |
| litispendencia | processo duplicado | alta | sim |
| gratuidade_x_renda | gratuidade × renda/perfil de viagem | média | sim |
| peticao_padronizada | inicial ≥ 95 % similar sem individualizar voo/assistência | baixa | não |
| despesas_sem_nexo | notas com data/local incompatíveis ou repetidas em outras ações | média | não |
| indicio_falha_real_cia | **a favor do autor**: motivo comercial, sem voucher, atraso > 12h, bagagem não devolvida | alta | não |

## 8. Modelo da contestação (seções, na ordem)

1. Endereçamento, qualificação e tempestividade
2. Síntese da demanda (subtipo, voo, data, trechos, internacional?) — *com página*
3. Preliminares — T01, **T02 (obrigatoriamente aqui)**, T03, T03.1, T04 — *com página*
4. Prejudicial — prescrição — T05 — *com página*
5. Dos fatos — a reserva, o voo e o atendimento (PNR → voo programado → comunicação → causa/código → METAR/NOTAM → alternativas → assistência → reacomodação/reembolso → chegada → PIR/entrega → reclamação → ajuizamento) — *cada evento com página*
6. Do mérito — causa do atraso/cancelamento — T06, T07, T10 — *com página*
7. Do cumprimento da Res. ANAC 400 — T08, T08.1, T09 — **tabela obrigação × prova anexa** — *com página*
8. Do mérito — bagagem — T11 — *com página*
9. Da inexistência de dano moral — T12 — *com página*
10. Pedidos subsidiários — T13 — *com página*
11. Providências processuais — T14 (só com flags confirmados) — *com página*
12. Das provas (depoimento pessoal, registros operacionais, ofícios ANAC/DECEA/REDEMET)
13. Dos pedidos (incompetência primeiro)
14. Rol de documentos

**Regra de citação:** toda afirmação de fato cita página ou documento anexo; METAR/TAF e vouchers só com o documento-fonte anexo.

**Estilo:** formal; frases curtas; sem adjetivar; Res. 400 e Convenção só nos termos conferidos; nunca estender a Convenção ao dano moral sem decisão do advogado-dono; tom respeitoso com passageiro vulnerável.

## 9. Revisão (M7)

- **Tempo mínimo:** 15 minutos.
- **Revisor mínimo:** advogado; **segunda revisão por sócio** se valor da causa > R$ 50 mil [A CONFERIR], autor falecido, indício de falha real, voo internacional ou passageiro vulnerável.

**Checklist do revisor** (B = bloqueia):

| Id | Item | |
|---|---|---|
| R01 | Cada fato tem citação de página ou documento anexo | B |
| R02 | Referências, Res. 400 e Convenção conferidas; nenhum placeholder | B |
| R03 | T06 só com registro do voo + METAR/TAF/NOTAM com horários compatíveis | B |
| R04 | T08 só com vouchers em nome do passageiro e na data; tabela obrigação × prova preenchida | B |
| R05 | Convenção de Montreal só em voo internacional e só para dano material/prazo | B |
| R06 | Incompetência relativa (T02), se cabível, está nas preliminares | B |
| R07 | Nenhuma imputação de fraude sem flag confirmado | B |
| R08 | Subtipo, PNR, voo, datas, atraso total e valores batem com o dossiê | B |
| R09 | Pedidos subsidiários presentes | B |
| R10 | Tom respeitoso; sem "mero dissabor" em pernoite não assistido/vulnerável | |
| R11 | Sinal de acordo avaliado e registrado | |

**Motivos de recusa padrão:** fato sem prova · tese sem prova (meteorologia sem METAR; assistência sem voucher) · referência não conferida · Convenção fora do escopo · dados divergentes · linguagem imputa fraude · caso deveria ir para acordo/escalada.

## 10. Métricas

| Id | Métrica | Meta (a conferir) |
|---|---|---|
| M01 | Tempo médio de revisão | < 25 min |
| M02 | Aprovação sem alteração substancial | > 60 % após 200 casos |
| M03 | Subsídios faltantes detectados antes da defesa | > 90 % |
| M04 | Êxito por tese × subtipo × comarca | ≥ baseline + 10 p.p. |
| M05 | Condenação média por subtipo e faixa de atraso (<4h, 4–12h, >12h) | −20 % vs. baseline |
| M06 | Custo de tokens por processo | < US$ 2 |
| M07 | Concordância modelo × revisor sênior | > 0,85 |
| M08 | Flags confirmados por humano | recalibrar se < 50 % |
| M09 | Acordos sinalizados × realizados | calibrar trimestralmente |
| M10 | Cobertura de METAR/TAF em T06 | 100 % |
| M11 | Declínios de competência obtidos (T02) | monitorar |

---

*Rascunho gerado em 19/10/2026 para validação pelo advogado-dono. Fonte da verdade: `playbooks/aereo-cancelamento-atraso-tjpa.playbook.yaml`.*
