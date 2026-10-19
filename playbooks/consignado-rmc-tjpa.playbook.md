# Playbook — Consignado / RMC não reconhecido (defesa) — TJPA

> **Versão para leitura.** Este documento reproduz em prosa e tabelas o arquivo `consignado-rmc-tjpa.playbook.yaml`, que é a **fonte da verdade** ingerida pela plataforma. Comentários e correções podem ser feitos aqui (ou no Word exportado deste Markdown); quem mantém o playbook transporta para o YAML e roda a validação. Se os dois divergirem, vale o YAML.
>
> **Estado: RASCUNHO (versão 1).** Nenhuma citação legal, número, prazo ou valor foi conferido. Tudo que está entre colchetes como **[A CONFERIR pelo advogado-dono]** precisa ser validado antes da aprovação. Este é um ponto de partida para o advogado-dono, não conteúdo jurídico final.

## 1. Identificação

| Campo | Valor |
|---|---|
| Tipologia | `consignado_rmc_nao_reconhecido` |
| Tribunal | TJPA |
| Lado / réu-tipo | Defesa / instituição financeira regional |
| Peça padrão | Contestação |
| Versão | 1 (rascunho) |
| Autor (OAB) | [A PREENCHER — advogado-dono] |
| Aprovação | pendente (nome, OAB e data/hora serão registrados no YAML) |

**Escopo.** Ações de consumidor (em geral aposentado/pensionista do INSS ou servidor) que negam a contratação de empréstimo consignado, cartão consignado com reserva de margem (RMC) ou cartão benefício (RCC), pedindo declaração de inexistência do débito, devolução (em dobro) dos descontos e dano moral.

**Antes de aprovar:** (1) conferir cada referência; (2) calibrar faixas de acordo com a carteira do cliente; (3) confirmar com o cliente quais subsídios (logs, biometria, TED, áudio) ele entrega em até 5 dias úteis.

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
| **contrato_localizado** (bloqueia), contrato_assinatura_tipo, biometria_score, documento_selfie_coincide, geolocalizacao_compativel, ip_log_disponivel | cliente | trilha de autenticação |
| **valor_creditado_conta_autor** (bloqueia), conta_credito_titularidade, ted_comprovante_localizado, extratos_mostram_uso, rmc_houve_saque_ou_compra | cliente | prova do recebimento |
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
| **T04** | Fracionamento de demandas | autor tem ≥ 2 ações contra o réu | relatório antifraude com as ações | causas de pedir realmente distintas | CPC 55/58/59, 5º/6º/77/80; precedentes STJ/TJPA; Recomendação CNJ; Centro de Inteligência TJPA | reunião no prevento; fracionamento abusivo para dano moral único e sucumbência |

### Prejudicial

| Id | Tese | Quando aplicar | Provas | Afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T05** | Prescrição (e decadência) | há data de ciência (1º desconto) e data de ajuizamento | HISCRE/extrato com 1º desconto | reclamação que interrompa ou mostre ciência posterior | **CDC 27 (5 anos) × CC 206 §3º (3 anos) × CC 205 (10 anos) — qual o TJPA aplica? [A CONFERIR]**; CDC 26; STJ sobre trato sucessivo | extinção (CPC 487 II); subsidiário: prescrição das parcelas anteriores ao prazo |

**Risco:** em descontos sucessivos o juízo costuma renovar a pretensão a cada parcela; a tese total raramente prospera sozinha.

### Mérito

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T06** | Contratação válida (biometria / assinatura digital / geolocalização / logs) | contrato localizado **e** há tipo de assinatura (biometria facial, ICP, eletrônica simples, digital por telefone, física) | **contrato**; **log de autenticação** (IP, dispositivo, data/hora, hash); biometria/selfie com score; geolocalização; documento apresentado; áudio SAC; averbação INSS | IP/geo em outra UF; BO de roubo de documentos anterior; assinatura física impugnada sem perícia viável; contrato com dados divergentes | CC 104/107/421-422; MP 2.200-2 art. 10 §2º e Lei 14.063/2020; Lei 10.820/2003 e IN do INSS; CPC 373 II, 411, 429 II; Súmulas 297 e 479 STJ (enfrentar); **Tema 1.061 STJ (ônus do banco) [A CONFERIR]**; acórdãos TJPA sobre biometria | improcedência; subsidiário: perícia |
| **T06.1** | RMC/RCC — regularidade do cartão (subtese de T06) | produto é RMC/RCC/cartão benefício e contrato localizado | termo de adesão com destaque de RMC e CET; faturas e saque/compras; autorização de reserva de margem | nenhum uso além do saque inicial, descontos perpétuos; termo sem destaque informativo | Lei 10.820/2003 art. 6º §5º; CDC 6º III, 31, 46 (enfrentar); **orientação do TJPA sobre conversão de RMC [A CONFERIR — risco alto]** | improcedência; subsidiário: conversão com taxa média e compensação, sem dobro |
| **T07** | Recebimento e uso dos valores | crédito em conta **do próprio autor** | **comprovante de TED/PIX** com agência/conta do autor; extrato com crédito e saques; descontos sem reclamação por N meses | crédito em conta de terceiro ou aberta na mesma data; saque integral imediato em praça distante | CC 884–886; CC 187 e 422 (venire); precedentes STJ/TJPA | improcedência; subsidiário: compensação integral |
| **T08** | Ausência de dano moral / mero aborrecimento | há pedido de dano moral | proporção do desconto frente ao benefício | reclamação prévia ignorada; desconto que comprometeu parte relevante de benefício mínimo | CC 186/927/944; **TJPA presume dano in re ipsa nesta tipologia? [A CONFERIR]**; faixa usual do TJPA por comarca | improcedência; subsidiário: quantum moderado, juros/correção do arbitramento (Súmula 362) |

**Erro mais grave desta tipologia:** afirmar crédito em conta do autor quando a conta é de terceiro. T07 e T09 só entram com comprovante em nome do próprio autor.

### Subsidiária

| Id | Tese | Quando aplicar | Provas | Afastam | Fundamentação (a conferir) | Pedido |
|---|---|---|---|---|---|---|
| **T09** | Compensação dos valores creditados e repetição simples | valor creditado ao autor | comprovante do crédito; total descontado | crédito em conta de terceiro | CC 368–380, 884; CDC 42 § único; **EAREsp 676.608 STJ — modulação do dobro (30/03/2021) [A CONFERIR]** | compensação; repetição simples; subsidiário: dobro só no período pós-modulação |

### Sinal (não é argumento autônomo)

| Id | Tese | Quando aplicar | Provas | Fundamentação (a conferir) | Providências |
|---|---|---|---|---|---|
| **T10** | Sinais de litigância predatória | advogado com ≥ N ações no mês (N = 30, a calibrar) **e** flags do M4 **confirmados por advogado com OAB** | relatório antifraude com decisão humana | CPC 77, 80, 139 III, 385; Recomendação CNJ; Centro de Inteligência/NUMOPEDE TJPA | depoimento pessoal do autor; exibição de comprovante de residência, documento com foto e extratos; comunicação institucional do padrão **sem imputar conduta a pessoa** |

## 5. Exceções — quando a esteira para

| Id | Situação | Ação |
|---|---|---|
| X01 | Contrato não localizado | pedir subsídio ao cliente (M3); se persistir, sinalizar acordo |
| X02 | Crédito em conta de terceiro ou titularidade desconhecida | escalar ao sócio; T07/T09 desativadas; avaliar acordo |
| X03 | Indício de fraude real contra o autor (IP/geo incompatível, sem biometria, conta recém-aberta) | sinalizar acordo — defender contratação é temerário (Súmula 479) |
| X04 | Autor possivelmente falecido antes da procuração/ajuizamento | escalar ao sócio; sem minuta padrão |
| X05 | Valor da causa > R$ 60 mil [A CONFERIR — alçada do cliente] | alertar revisor; segunda revisão por sócio |
| X06 | Autor não nega contratação, discute juros/cláusulas | não gerar minuta; reclassificar (revisional) |
| X07 | Sem log de autenticação e sem comprovante de crédito | sinalizar acordo — defesa só em preliminares |

## 6. Sinais de acordo

**Política:** defender quando há **contrato + trilha de autenticação + crédito em conta do autor**. Acordar cedo quando falta qualquer um dos três pilares ou há indício de fraude real. A plataforma sinaliza e registra; **a decisão é do advogado/cliente**.

**Acordar quando:** contrato não localizado · crédito não é em conta do autor · indício de fraude contra o autor · assinatura física e contrato < R$ 3 mil (perícia custa mais que o contrato) [valores A CONFERIR].

**Não acordar quando:** biometria facial ou ICP **e** crédito em conta do autor (caso forte; acordo alimenta a litigância predatória) · autor com ≥ 3 ações contra o réu (serial), salvo decisão do cliente.

**Faixas ilustrativas — substituir pela média de condenação da carteira (12 meses) por comarca:**

| Grupo de comarcas | Faixa (R$) |
|---|---|
| Região Metropolitana de Belém (Belém, Ananindeua, Marituba, Benevides, Santa Bárbara, Santa Izabel) | 1.000 – 4.000 |
| Interior — polos (Santarém, Marabá, Castanhal, Parauapebas, Altamira) | 1.500 – 5.000 |
| Interior — demais comarcas | 1.500 – 6.000 |

**Alçadas [A CONFERIR]:** até R$ 3 mil, advogado responsável pela carteira · até R$ 10 mil, sócio FBS + jurídico do cliente · acima, comitê do cliente.

## 7. Antifraude específico da tipologia

> Nenhuma checagem produz rótulo de "fraudador"; só **flags com evidência**. Apenas decisão humana registrada com OAB confirma um flag.

| Código | O que verifica | Severidade | Já existe no M4? |
|---|---|---|---|
| procuracao_presente | procuração juntada | alta | sim |
| procuracao_antiga | procuração com > 180 dias do ajuizamento (outorga em massa) [N a conferir] | média | não |
| comprovante_endereco | comprovante presente | baixa | sim |
| comprovante_endereco_terceiro | comprovante em nome de terceiro (forçar foro / autor fictício) | média | não |
| concentracao_advogado_mes | mesmo advogado com > 30 ações contra o cliente no mês [N a calibrar] | baixa | não |
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

- **Tempo mínimo:** 15 minutos com a peça aberta.
- **Revisor mínimo:** advogado com OAB; **segunda revisão por sócio** se valor da causa > R$ 60 mil [A CONFERIR], autor possivelmente falecido ou indício de fraude contra o autor.

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
| R09 | Sinal de acordo avaliado e registrado antes de protocolar | |

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

---

*Rascunho gerado em 19/10/2026 para validação pelo advogado-dono. Fonte da verdade: `playbooks/consignado-rmc-tjpa.playbook.yaml`.*
