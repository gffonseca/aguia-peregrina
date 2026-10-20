# Playbook — Consignado / RMC não reconhecido (defesa) — TJPA

> **Versão para leitura.** Este documento reproduz em prosa e tabelas o arquivo `consignado-rmc-tjpa.playbook.yaml`, que é a **fonte da verdade** ingerida pela plataforma. Comentários e correções podem ser feitos aqui (ou no Word exportado deste Markdown); quem mantém o playbook transporta para o YAML e roda a validação. Se os dois divergirem, vale o YAML.
>
> **Estado: EM REVISÃO (versão 1).** Sessão 1 de revisão realizada em 19/10/2026 por Gustavo Fonseca (OAB/PA 12.724) — decisões 1–16 aplicadas (ver [seção 11](#11-decisões-da-revisão-19102026)). **Nada aprovado ainda:** nenhuma citação legal, número de tema ou súmula foi conferido; o levantamento com fonte será feito e validado na sessão de 20/10/2026. Tudo que está como **[A CONFERIR pelo advogado-dono]** segue pendente. Pendências que ainda dependem de levantamento de jurisprudência do TJPA estão marcadas **⏳ PENDENTE**.

## 1. Identificação

| Campo | Valor |
|---|---|
| Tipologia | `consignado_rmc_nao_reconhecido` |
| Tribunal | TJPA |
| Lado / réu-tipo | Defesa / instituição financeira regional |
| Peça padrão | Contestação |
| Versão | 1 (em revisão) |
| Autor (OAB) | [A PREENCHER — advogado-dono] |
| Revisões | 19/10/2026 — Gustavo Fonseca OAB/PA 12.724 — sessão 1: decisões 1–16 |
| Aprovação | pendente (nome, OAB e data/hora serão registrados no YAML) |
| Piloto | sem cliente-piloto; piloto interno com casos encerrados da FBS primeiro; prospecção em paralelo: Banpará, Basa, financeira regional |

**Escopo.** Ações de consumidor (em geral aposentado/pensionista do INSS ou servidor) que negam a contratação de empréstimo consignado, cartão consignado com reserva de margem (RMC) ou cartão benefício (RCC), pedindo declaração de inexistência do débito, devolução (em dobro) dos descontos e dano moral.

**Antes de aprovar:** (1) conferir cada referência (sessão de 20/10/2026); (2) levantamento de jurisprudência do TJPA (12 meses) para fechar o prazo prescricional (T05) e a postura em RMC (T06.1); (3) confirmar com o cliente quais subsídios (log de autenticação, biometria, TED/PIX) ele entrega em até 5 dias úteis; (4) recalibrar as faixas de acordo com dados da carteira (90 dias de piloto).

## 2. Como a plataforma reconhece a tipologia

- **Assuntos CNJ (códigos a conferir):** empréstimo consignado; dano moral em contratos bancários; cartão de crédito/RMC; inexistência de relação jurídica/débito.
- **Palavras-chave:** empréstimo consignado; consignado não contratado; não reconhece; desconto indevido; reserva de margem consignável; RMC; RCC; cartão consignado; cartão benefício; inexistência de débito; repetição do indébito; benefício previdenciário.
- **Excluem:** revisional de juros; superendividamento; portabilidade; busca e apreensão.
- **Confiança mínima:** 0,85 — abaixo disso a classificação vai para triagem humana.

## 3. O que o dossiê precisa ter

Campos que M3 (subsídios do cliente) e M5 (extração dos autos) precisam preencher. Os marcados com **bloqueia** impedem a geração de minuta se ausentes.

| Campo | Origem | O que é |
|---|---|---|
| comarca, valor_causa, valor_dano_moral_pedido, data_ajuizamento | autos | identificação básica |
| **tipo_produto** (bloqueia) | cliente | consignado / RMC / RCC / cartão benefício / refinanciamento |
| valor_contrato, data_contrato, data_primeiro_desconto, descontos_parcelas_n | cliente | dados do contrato e dos descontos |
| data_ciencia_inequivoca | calculado | = primeiro desconto, salvo prova diversa |
| autor_idade, autor_beneficiario_inss | autos | perfil do autor |
| **autor_nega_contratacao** (bloqueia), autor_alega_vicio_rmc | autos | nega tudo × "achei que era empréstimo" |
| autor_pede_gratuidade, renda_declarada_autor | autos | para T01 |
| inicial_atende_requisitos_tema_1198 | autos | para T02 |
| reclamacao_administrativa_previa | cliente | SAC/ouvidoria/consumidor.gov |
| **contrato_localizado** (bloqueia), contrato_assinatura_tipo, biometria_score, documento_selfie_coincide, geolocalizacao_compativel, ip_log_disponivel | cliente | trilha de autenticação — log de autenticação e biometria: **disponibilidade a confirmar com o cliente** |
| **valor_creditado_conta_autor** (bloqueia), conta_credito_titularidade, ted_comprovante_localizado, extratos_mostram_uso, rmc_houve_saque_ou_compra | cliente | prova do recebimento — TED/PIX: **disponibilidade a confirmar com o cliente** |
| audio_sac_disponivel, contratos_ativos_autor_n, contratos_anteriores_adimplidos | cliente | contexto |
| litispendencia_cnj, coisa_julgada_cnj, acoes_mesmo_autor_mesmo_reu_n, acoes_mesmo_advogado_mes_n, autor_falecido, data_procuracao, comprovante_endereco_titular | antifraude / autos | cruzamentos |
| indicio_fraude_contra_autor | calculado | sinais de que a fraude pode ter sido real |

## 4. Árvore de teses

Cada tese só entra na peça se **todas** as condições forem verdadeiras e as provas obrigatórias estiverem anexas; se uma "prova que afasta" aparecer, a tese é desativada e o revisor é avisado.

### Preliminares

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T01** | Impugnação à gratuidade | pede gratuidade **e** renda nos autos > ~3 SM [A CONFERIR] | extrato do benefício/holerite; extratos bancários | renda ≤ limite do TJPA | CPC 98–100, 99 §2º; critério do STJ; TJPA | revogar/indeferir ou intimar a comprovar; subsidiário: parcelar custas |
| **T02** | Emenda da inicial — Tema 1.198 STJ | inicial não traz os requisitos do precedente | inicial e anexos | juízo já declarou a inicial apta | CPC 319–321, 330; **STJ Tema 1.198 [número e tese A CONFERIR]**; Recomendação CNJ sobre litigância predatória | emenda sob pena de indeferimento |
| **T03** | Litispendência | há processo em curso com tríplice identidade | cópia da inicial/andamento do outro feito | contratos comprovadamente distintos | CPC 337 VI/VII, 485 V | extinção sem mérito; subsidiário: conexão (CPC 55) |
| **T03.1** | Coisa julgada (subtese de T03) | há processo transitado com tríplice identidade | certidão de trânsito e sentença | — | CPC 337 VII §4º, 502, 508 | extinção sem mérito |
| **T04** | Fracionamento de demandas | autor tem ≥ 2 ações contra o réu | relatório antifraude com as ações | causas de pedir realmente distintas | CPC 55/58/59, 5º/6º/77/80; precedentes STJ/TJPA; Recomendação CNJ; Centro de Inteligência TJPA | reunião no prevento; fracionamento abusivo para dano moral único e sucumbência. Providências seguem a escalada (a)/(b)/(c) de T10 |

### Prejudicial

| Id | Tese | Quando aplicar | Provas | Afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T05** | Prescrição (e decadência) | há data de ciência (1º desconto) e data de ajuizamento | HISCRE/extrato com 1º desconto | reclamação que interrompa ou mostre ciência posterior | **⏳ PENDENTE — prazo (CDC 27 × CC 206 §3º × CC 205) aguarda levantamento TJPA 12 meses**; CDC 26; STJ sobre trato sucessivo | extinção (CPC 487 II); subsidiário: prescrição das parcelas anteriores ao prazo |

**Termo inicial (decidido em 19/10/2026):** sustentar o **1º desconto** como termo inicial (tese principal — pretensão única) e, **subsidiariamente**, o trato sucessivo com prescrição das parcelas anteriores ao prazo. O prazo em si (5, 3 ou 10 anos) só será afirmado na peça depois do levantamento do TJPA.

**Risco:** em descontos sucessivos o juízo costuma renovar a pretensão a cada parcela; a tese total raramente prospera sozinha.

### Mérito

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T06** | Contratação válida (biometria / assinatura digital / geolocalização / logs) | contrato localizado **e** há tipo de assinatura (biometria facial, ICP, eletrônica simples, digital por telefone, física) | **contrato**; **log de autenticação** (IP, dispositivo, data/hora, hash); biometria/selfie com score; geolocalização; documento apresentado; áudio SAC; averbação INSS | IP/geo em outra UF; BO de roubo de documentos anterior; assinatura física impugnada sem perícia viável; contrato com dados divergentes | CC 104/107/421-422; MP 2.200-2 art. 10 §2º e Lei 14.063/2020; Lei 10.820/2003 e IN do INSS; CPC 373 II, 411, 429 II; Súmulas 297 e 479 STJ (enfrentar); **Tema 1.061 STJ (ônus do banco) [A CONFERIR]**; acórdãos TJPA sobre biometria | improcedência; subsidiário: perícia |
| **T06.1** | RMC/RCC — regularidade do cartão (subtese de T06; escopo confirmado em 19/10/2026) | produto é RMC/RCC/cartão benefício e contrato localizado | termo de adesão com destaque de RMC e CET; faturas e saque/compras; autorização de reserva de margem | nenhum uso além do saque inicial, descontos perpétuos; termo sem destaque informativo | Lei 10.820/2003 art. 6º §5º; CDC 6º III, 31, 46 (enfrentar); **⏳ PENDENTE — postura (conversão, taxa, dobro) aguarda levantamento TJPA 12 meses; estrutura mantida** | improcedência; subsidiário: conversão com taxa média e compensação, sem dobro |
| **T07** | Recebimento e uso dos valores | crédito em conta **do próprio autor** | **comprovante de TED/PIX** com agência/conta do autor; extrato com crédito e saques; descontos sem reclamação por N meses | crédito em conta de terceiro ou aberta na mesma data; saque integral imediato em praça distante | CC 884–886; CC 187 e 422 (venire); precedentes STJ/TJPA | improcedência; subsidiário: compensação integral |
| **T08** | Ausência de dano moral / mero aborrecimento (estratégia confirmada em 19/10/2026) | há pedido de dano moral | proporção do desconto frente ao benefício | reclamação prévia ignorada; desconto que comprometeu parte relevante de benefício mínimo | CC 186/927/944; **TJPA presume dano in re ipsa nesta tipologia? [A CONFERIR]**; faixa usual do TJPA por comarca | improcedência; subsidiário: quantum moderado, juros/correção do arbitramento (Súmula 362) |

**Erro mais grave desta tipologia:** afirmar crédito em conta do autor quando a conta é de terceiro. T07 e T09 só entram com comprovante em nome do próprio autor.

### Subsidiária

| Id | Tese | Quando aplicar | Provas | Afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T09** | Compensação dos valores creditados e repetição simples | valor creditado ao autor | comprovante do crédito; total descontado | crédito em conta de terceiro | CC 368–380, 884; CDC 42 § único; **EAREsp 676.608 STJ — modulação do dobro (30/03/2021) [A CONFERIR]** | compensação; repetição simples; subsidiário: dobro só no período pós-modulação |

### Sinal (não é argumento autônomo)

| Id | Tese | Quando aplicar | Provas | Fundamentação (a conferir) | Providências |
|---|---|---|---|---|---|
| **T10** | Sinais de litigância predatória | advogado com ≥ 10 ações/mês contra o réu (nível *atenção*; *forte* = ≥ 30) **e** flags do M4 **confirmados por advogado com OAB** | relatório antifraude com decisão humana | CPC 77, 80, 139 III, 385; Recomendação CNJ; Cijepa/NUMOPEDE TJPA | escalada em três níveis (abaixo) |

**Escalada de providências (T04/T10), decidida em 19/10/2026:**

| Nível | Providência | Autorização |
|---|---|---|
| (a) padrão | depoimento pessoal do autor + exibição de documentos (comprovante de residência atual, documento com foto, extratos), na própria peça | flags confirmados por `human_decide` |
| (b) | comunicação institucional do padrão ao **Cijepa/NUMOPEDE do TJPA**, fora da peça, linguagem neutra, **sem imputar conduta a pessoa**; pressupõe nível *forte* (≥ 30 ações/mês) ou padrão equivalente | **dupla autorização por escrito: sócio FBS + jurídico do cliente**, registrada na plataforma |
| (c) | representação à **OAB-PA**, só em casos extremos, com dossiê de evidências | **dupla autorização por escrito: sócio FBS + jurídico do cliente**, registrada na plataforma |

A plataforma deve armazenar o registro da autorização (documento/aceite, identidade e OAB/cargo de cada autorizador, data-hora, caso e nível) vinculado ao caso e à minuta, como trilha de auditoria; sem registro, a providência não sai da plataforma.

## 5. Exceções — quando a esteira para

| Id | Situação | Ação |
|---|---|---|
| X01 | Contrato não localizado | pedir subsídio ao cliente (M3). Se continuar não localizado após o subsídio, **ambas as ações em paralelo**: sinalizar acordo **e** gerar minuta só com preliminares + antifraude (sem mérito); escalar ao advogado da carteira |
| X02 | Crédito em conta de terceiro ou titularidade desconhecida | escalar ao sócio; T07/T09 desativadas; avaliar acordo |
| X03 | Indício de fraude real contra o autor (IP/geo incompatível, sem biometria, conta recém-aberta) | **sinalizar acordo imediato** (confirmado) — defender contratação é temerário (Súmula 479) |
| X04 | Autor possivelmente falecido antes da procuração/ajuizamento | escalar ao sócio; sem minuta padrão |
| X05 | Valor da causa > **R$ 30 mil** (fixado em 19/10/2026; antes 60 mil) | alertar revisor; segunda revisão por sócio |
| X06 | Autor não nega contratação, discute juros/cláusulas | não gerar minuta; reclassificar (revisional) |
| X07 | Sem log de autenticação e sem comprovante de crédito | sinalizar acordo — defesa só em preliminares |
| X08 | Contrato com assinatura física impugnada | alertar revisor: **avaliar custo de perícia grafotécnica × valor do contrato** — sem regra fixa de valor; não é exceção automática de acordo |

## 6. Sinais de acordo

**Política (regra dos três pilares, confirmada em 19/10/2026):** defender quando há **contrato + trilha de autenticação + crédito em conta do autor**. Acordar cedo quando falta qualquer um dos três pilares ou há indício de fraude real. Exceção: **autor serial (≥ 3 ações contra o réu)** — não acordar salvo decisão do cliente.

**Acordar quando:** contrato não localizado · crédito não é em conta do autor · indício de fraude contra o autor. *(A regra "assinatura física e contrato < R$ 3 mil" foi removida: virou alerta ao revisor — X08.)*

**Não acordar quando:** biometria facial ou ICP **e** crédito em conta do autor (caso forte; acordo alimenta a litigância predatória) · autor com ≥ 3 ações contra o réu (serial), salvo decisão do cliente.

**Faixas provisórias (`provisorio: true`, recalibrar em 90 dias)** — o painel M10 (métrica M05, condenação média por comarca) recalibra cada faixa com a média de condenação da carteira:

| Grupo de comarcas | Faixa (R$) |
|---|---|
| Região Metropolitana de Belém (Belém, Ananindeua, Marituba, Benevides, Santa Bárbara, Santa Izabel) | 1.000 – 4.000 |
| Interior — polos (Santarém, Marabá, Castanhal, Parauapebas, Altamira) | 1.500 – 5.000 |
| Interior — demais comarcas | 1.500 – 6.000 |

**Fluxo de aprovação (substitui as alçadas por valor, decisão de 19/10/2026):** toda proposta de acordo passa pelo **jurídico do cliente**; a **FBS recomenda** com valor sugerido e faixa (grupo de comarcas) e racional; o cliente aprova, ajusta ou recusa. A plataforma registra a recomendação (valor, faixa, racional, OAB) e a decisão do cliente (quem, quando, valor aprovado) no caso.

## 7. Antifraude específico da tipologia

> Nenhuma checagem produz rótulo de "fraudador"; só **flags com evidência**. Apenas decisão humana registrada com OAB confirma um flag.

| Código | O que verifica | Severidade | Já existe no M4? |
|---|---|---|---|
| procuracao_presente | procuração juntada | alta | sim |
| procuracao_antiga | procuração com > 180 dias do ajuizamento (outorga em massa) — 180 dias confirmado | média | não |
| comprovante_endereco | comprovante presente | baixa | sim |
| comprovante_endereco_terceiro | comprovante em nome de terceiro (forçar foro / autor fictício) | média | não |
| concentracao_advogado_mes | mesmo advogado contra o cliente no mês — **dois níveis: *atenção* ≥ 10 ações/mês; *forte* ≥ 30 ações/mês** (atenção habilita T10 nível a; forte é pré-requisito do nível b) | média | não |
| concentracao_autor | mesmo autor com 3+ ações na carteira | média | sim |
| autor_falecido | indício de óbito anterior à procuração/ajuizamento | alta | não |
| litispendencia | processo duplicado em curso | alta | sim |
| fracionamento_contratos | vários contratos do mesmo autor em ações separadas em 90 dias | média | não |
| gratuidade_x_renda | gratuidade com renda > 5 SM [parâmetro do TJPA a conferir] | média | sim |
| peticao_padronizada | inicial ≥ 95 % similar a outras do mesmo advogado, sem individualizar o contrato | baixa | não |
| assinatura_procuracao_divergente | assinatura da procuração visivelmente diversa do RG (sinal visual, sem laudo) | média | não |
| indicio_fraude_contra_autor | **a favor do autor**: IP/geo incompatível, conta de terceiro, sem biometria, conta aberta na data — avisa que defender é temerário | alta | não |

## 8. Modelo da contestação (seções, na ordem)

1. Endereçamento, qualificação e tempestividade
2. Síntese da demanda (até 8 linhas, sem adjetivos) — *com página*
3. Preliminares — T01, T02, T03, T03.1, T04 (omitir se nenhuma se aplicar) — *com página*
4. Prejudicial de mérito — prescrição — T05 — *com página*
5. Dos fatos — a contratação (linha do tempo: proposta → autenticação → formalização → averbação → crédito → descontos → reclamação → ajuizamento) — *cada evento com página*
6. Do mérito — validade da contratação — T06, T06.1; enfrentar Súmula 479 e Tema 1.061 expressamente — *com página*
7. Do recebimento e utilização dos valores — T07 (somente se a conta é do autor) — *com página*
8. Da inexistência de dano moral — T08 (tom respeitoso; quantum subsidiário)
9. Pedidos subsidiários — compensação, repetição simples, juros — T09 — *com página*
10. Providências processuais — T10 (só com flags confirmados; linguagem neutra) — *com página*
11. Das provas (depoimento pessoal, perícia grafotécnica/técnica em logs, juntada)
12. Dos pedidos (preliminares → prejudicial → improcedência → subsidiários → sucumbência → intimações)
13. Rol de documentos (cada anexo com o tipo do playbook)

**Regra de citação:** toda afirmação de fato cita a página dos autos ou o documento anexo identificado. Sem página, sem afirmação.

**Estilo:** português formal, frases curtas, sem adjetivar o autor ou o advogado adverso; referências legais só as conferidas; tom respeitoso obrigatório com autor idoso/beneficiário do INSS.

## 9. Revisão (M7)

- **Tempo mínimo:** 15 minutos com a peça aberta (confirmado; medir nas primeiras 50 peças e ajustar só para cima, com justificativa registrada).
- **Revisor final:** advogado com OAB responsável pela carteira.
- **Sócio obrigatório (segunda revisão):** valor da causa > **R$ 30 mil** (X05); indício de fraude (X02 — conta de terceiro/desconhecida; X03 — indício de fraude contra o autor); autor possivelmente falecido (X04); qualquer **comunicação externa de padrão** (T04/T10 níveis b e c).
- **Dupla autorização por escrito (sócio FBS + jurídico do cliente):** exigida para os níveis (b) comunicação ao Cijepa/NUMOPEDE e (c) representação à OAB-PA; a plataforma guarda o registro (autorizadores, OAB/cargo, data-hora, caso, nível) como trilha de auditoria.

**Checklist do revisor** (B = bloqueia a aprovação):

| Id | Item | |
|---|---|---|
| R01 | Cada fato tem citação de página ou documento anexo identificado | B |
| R02 | Nenhuma referência legal não conferida ou placeholder sobrou no texto | B |
| R03 | T06 só foi usada com contrato + log/biometria anexos | B |
| R04 | T07/T09 só com comprovante de crédito em conta do **próprio** autor | B |
| R05 | Nenhuma expressão imputa fraude/má-fé sem flag confirmado por advogado | B |
| R06 | Produto correto (consignado × RMC × RCC); valores e datas batem com o dossiê | B |
| R07 | Pedidos subsidiários presentes (compensação, repetição simples, quantum) | B |
| R08 | Tom respeitoso; sem "mero aborrecimento" quando o benefício mínimo foi comprometido | |
| R09 | Sinal de acordo avaliado e registrado antes de protocolar; se acordo, recomendação FBS (valor + faixa) enviada ao jurídico do cliente | |
| R10 | Providências de nível (b)/(c) só com dupla autorização por escrito registrada na plataforma | B |

**Motivos de recusa padrão:** fato sem prova citável · tese sem prova necessária · referência legal não conferida/inexistente · produto/valores/datas divergentes · linguagem imputa fraude sem decisão humana · caso deveria ir para acordo/escalada.

## 10. Métricas

| Id | Métrica | Meta (a conferir) |
|---|---|---|
| M01 | Tempo médio de revisão por contestação | < 30 min |
| M02 | Aprovação sem alteração substancial | > 60 % após 200 casos |
| M03 | Subsídios faltantes detectados antes da defesa | > 90 % |
| M04 | Taxa de êxito por tese × comarca vs. baseline FBS | ≥ baseline + 10 p.p. |
| M05 | Condenação média (dano moral + repetição) por comarca | −20 % vs. baseline; alimenta as faixas de acordo |
| M06 | Custo de tokens por processo | < US$ 2 por contestação |
| M07 | Concordância modelo × revisor sênior | > 0,85 |
| M08 | Flags antifraude confirmados por humano | recalibrar se precisão < 50 % |
| M09 | Acordos sinalizados × realizados | calibrar faixas trimestralmente |

## 11. Decisões da revisão (19/10/2026)

Sessão 1 de revisão — Gustavo Fonseca, OAB/PA 12.724. Status permanece **em revisão**; nada foi aprovado. Itens marcados **⏳ PENDENTE** dependem de levantamento ainda não feito.

| # | Tema | Decisão |
|---|---|---|
| 1 | Escopo | RMC/RCC permanece neste playbook, como subtese **T06.1** de T06. |
| 2 | T05 prescrição | **⏳ PENDENTE** — prazo (CDC 27 × CC 206 §3º × CC 205) aguarda levantamento de jurisprudência do TJPA (12 meses). Termo inicial: **1º desconto** como tese principal; **trato sucessivo** como subsidiária (prescrição das parcelas anteriores ao prazo). |
| 3 | T08 dano moral | Confirmado: negação do dano + subsidiário quantum moderado. |
| 4 | T06.1 RMC | **⏳ PENDENTE** — postura (conversão, taxa, dobro) aguarda levantamento TJPA; estrutura atual mantida. |
| 5 | Litigância predatória (T04/T10) | Escalada em três níveis: (a) padrão — depoimento pessoal + exibição de documentos; (b) comunicação institucional ao Cijepa/NUMOPEDE do TJPA; (c) representação à OAB-PA em casos extremos. **(b) e (c) exigem dupla autorização por escrito (sócio FBS + jurídico do cliente), registrada na plataforma** (trilha de auditoria). |
| 6 | Política de acordo | Confirmada a regra dos três pilares e a exceção do autor serial (≥ 3 ações). |
| 7 | X01 contrato não localizado após subsídio | **Ambas** as ações em paralelo: sinalizar acordo **e** gerar minuta só com preliminares + antifraude (sem mérito); escalar ao advogado da carteira. |
| 8 | X03 indício de fraude real contra o autor | Confirmado: sinalizar acordo imediato. |
| 9 | X05 | Valor da causa > **R$ 30 mil** exige segunda revisão por sócio (antes: 60 mil). |
| 10 | Alçadas de acordo | Removidos os três níveis por valor. Toda proposta passa pelo jurídico do cliente; a FBS recomenda com valor sugerido e faixa; a decisão é registrada. |
| 11 | Antifraude e revisão | Concentração de advogado em dois níveis: *atenção* ≥ 10 ações/mês, *forte* ≥ 30 ações/mês. Procuração antiga > 180 dias (confirmado). Revisor final: advogado com OAB da carteira; sócio obrigatório em X05 (> 30 mil), indício de fraude (X02/X03) e comunicação externa de padrão. Tempo mínimo 15 min (confirmado; medir nas primeiras 50 peças, ajustar só para cima com justificativa). |
| 12 | Faixas de acordo por comarca | Mantidas as ilustrativas, marcadas `provisorio: true` com `recalibrar_em_dias: 90`; o painel M10 recalibra com a média de condenação da carteira. |
| 13 | Perícia grafotécnica em contrato pequeno | Sem regra fixa de valor: vira alerta ao revisor (X08 — "avaliar custo de perícia × valor do contrato"); removida a regra "< R$ 3 mil" dos sinais de acordo. |
| 14 | Campos do dossiê | **⏳ A CONFIRMAR COM O CLIENTE** — disponibilidade de log de autenticação, biometria e TED/PIX (`disponibilidade: "a confirmar com cliente"`). |
| 15 | Cliente-piloto | Ainda não há. Piloto interno com casos encerrados da FBS primeiro; prospecção de Banpará / Basa / financeira regional em paralelo. |
| 16 | Referências legais | **⏳ PENDENTE** — seguem `conferido: false`; levantamento com fonte será feito e validado na sessão de 20/10/2026. |

---

*Rascunho gerado em 19/10/2026; sessão 1 de revisão aplicada no mesmo dia. Fonte da verdade: `playbooks/consignado-rmc-tjpa.playbook.yaml`.*
