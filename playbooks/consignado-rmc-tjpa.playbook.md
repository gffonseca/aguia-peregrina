# Playbook — Consignado / RMC não reconhecido (defesa) — TJPA

> **Versão para leitura.** Este documento reproduz em prosa e tabelas o arquivo `consignado-rmc-tjpa.playbook.yaml`, que é a **fonte da verdade** ingerida pela plataforma. Comentários e correções podem ser feitos aqui (ou no Word exportado deste Markdown); quem mantém o playbook transporta para o YAML e roda a validação. Se os dois divergirem, vale o YAML.
>
> **Estado: EM REVISÃO (versão 1) — pronto para aprovação.** Sessão 1 em 19/10/2026 (decisões 1–16, [seção 11](#11-decisões-da-revisão-19102026)) e sessão 2 em 20/10/2026 ([seção 12](#12-decisões-da-revisão-20102026)), ambas por Gustavo Fonseca (OAB/PA 12.724). Na sessão 2 **todas as referências legais foram conferidas** contra o levantamento de 19/10/2026 (STJ, Planalto, CNJ e portal de jurisprudência do TJPA, out/2025–out/2026) e cada uma traz a fonte na `nota`. O validador já aceita `status: aprovado` (dry-run); a aprovação (nome, OAB, data/hora) é ato separado do advogado-dono. Pendência que fica sob monitoramento: **Tema 929/STJ** (ver T09).

## 1. Identificação

| Campo | Valor |
|---|---|
| Tipologia | `consignado_rmc_nao_reconhecido` |
| Tribunal | TJPA |
| Lado / réu-tipo | Defesa / instituição financeira regional |
| Peça padrão | Contestação |
| Versão | 1 (em revisão) |
| Autor (OAB) | Gustavo Fonseca — OAB/PA 12.724 |
| Revisões | 19/10/2026 — sessão 1: decisões 1–16 · 20/10/2026 — sessão 2: referências validadas, T01/T05/T06.1/T08/T09 ajustados |
| Aprovação | pendente (nome, OAB e data/hora serão registrados no YAML) |
| Piloto | sem cliente-piloto; piloto interno com casos encerrados da FBS primeiro; prospecção em paralelo: Banpará, Basa, financeira regional |

**Escopo.** Ações de consumidor (em geral aposentado/pensionista do INSS ou servidor) que negam a contratação de empréstimo consignado, cartão consignado com reserva de margem (RMC) ou cartão benefício (RCC), pedindo declaração de inexistência do débito, devolução (em dobro) dos descontos e dano moral.

**O que ainda não foi objeto do levantamento (não bloqueia a aprovação):** classes CNJ 7 e 436 (conferir no SGT/CNJ); metas numéricas das métricas (confirmar no piloto); texto oficial da IN PRES/INSS 213/2026; data de publicação do Tema 1.061; acórdão do Tema 929.

**Antes de aprovar:** (1) confirmar com o cliente quais subsídios (log de autenticação, biometria, TED/PIX, TCE no RMC) ele entrega em até 5 dias úteis; (2) recalibrar as faixas de acordo com dados da carteira (90 dias de piloto) — seguem `provisorio: true`, o que não impede a aprovação.

## 2. Como a plataforma reconhece a tipologia

- **Assuntos CNJ (TPU, conferidos em 20/10/2026 pelos metadados dos acórdãos do TJPA):** 11806 Empréstimo consignado; 9607 Contratos bancários; 9585 e 7772 Cartão de crédito (é assim que o TJPA autua RMC/RCC — **não existe código próprio "RMC"**); 10433 Indenização por dano moral; 11811 Práticas abusivas.
- **Classes CNJ:** 7 (Procedimento Comum Cível) e 436 (Juizado Especial Cível) — não cobertas pelo levantamento.
- **Palavras-chave:** empréstimo consignado; consignado não contratado; não reconhece; desconto indevido; reserva de margem consignável; RMC; RCC; cartão consignado; cartão benefício; inexistência de débito; repetição do indébito; benefício previdenciário.
- **Excluem:** revisional de juros; superendividamento; portabilidade; busca e apreensão.
- **Confiança mínima:** 0,85 — abaixo disso a classificação vai para triagem humana.

## 3. O que o dossiê precisa ter

Campos que M3 (subsídios do cliente) e M5 (extração dos autos) precisam preencher. Os marcados com **bloqueia** impedem a geração de minuta se ausentes. Novos na sessão 2: `data_ultimo_desconto`, `rmc_tce_localizado`, `hipotese_afastamento_dano_moral`.

| Campo | Origem | O que é |
|---|---|---|
| comarca, valor_causa, valor_dano_moral_pedido, data_ajuizamento | autos | identificação básica |
| **tipo_produto** (bloqueia) | cliente | consignado / RMC / RCC / cartão benefício / refinanciamento |
| valor_contrato, data_contrato, data_primeiro_desconto, **data_ultimo_desconto**, descontos_parcelas_n | cliente | dados do contrato e dos descontos — o último desconto é o termo inicial do CDC 27 (T05) |
| data_ciencia_inequivoca | calculado | = primeiro desconto; só argumento acessório em T05 |
| autor_idade, autor_beneficiario_inss | autos | perfil do autor |
| **autor_nega_contratacao** (bloqueia), autor_alega_vicio_rmc | autos | nega tudo × "achei que era empréstimo" |
| autor_pede_gratuidade, renda_declarada_autor | autos | para T01 (renda é só gatilho interno) |
| inicial_atende_requisitos_tema_1198 | autos | procuração atualizada, comprovante de residência atual, extratos, individualização do contrato (T02) |
| reclamacao_administrativa_previa | cliente | SAC/ouvidoria/consumidor.gov |
| **contrato_localizado** (bloqueia), contrato_assinatura_tipo, biometria_score, documento_selfie_coincide, geolocalizacao_compativel, ip_log_disponivel | cliente | trilha de autenticação — log e biometria: **disponibilidade a confirmar com o cliente** |
| **valor_creditado_conta_autor** (bloqueia), conta_credito_titularidade, ted_comprovante_localizado, extratos_mostram_uso, rmc_houve_saque_ou_compra, **rmc_tce_localizado** | cliente | prova do recebimento — TED/PIX: **disponibilidade a confirmar**; TCE é o pilar da validade do RMC (T06.1) |
| audio_sac_disponivel, contratos_ativos_autor_n, contratos_anteriores_adimplidos | cliente | contexto |
| litispendencia_cnj, coisa_julgada_cnj, acoes_mesmo_autor_mesmo_reu_n, acoes_mesmo_advogado_mes_n, autor_falecido, data_procuracao, comprovante_endereco_titular | antifraude / autos | cruzamentos |
| indicio_fraude_contra_autor | calculado | sinais de que a fraude pode ter sido real |
| **hipotese_afastamento_dano_moral** | calculado | contratacao_provada / inercia_prolongada / rmc_credito_recebido / nenhuma — decide se T08 entra |

## 4. Árvore de teses

Cada tese só entra na peça se **todas** as condições forem verdadeiras e as provas obrigatórias estiverem anexas; se uma "prova que afasta" aparecer, a tese é desativada e o revisor é avisado. Toda referência abaixo está `conferido: true` no YAML, com fonte na `nota`. Acórdãos do TJPA: conferir pelo nº CNJ em https://jurisprudencia.tjpa.jus.br/ (aba "Processo").

### Preliminares

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (conferida) | Pedido |
|---|---|---|---|---|---|---|
| **T01** | Impugnação à gratuidade — **só com elementos concretos** | pede gratuidade **e** (gatilho interno) renda nos autos > R$ 4.554 — o limiar **nunca** é citado na peça | extrato do benefício/holerite; extratos bancários; outros contratos; **Infojud/Renajud** (requerer) | só há a declaração e a renda do benefício | CPC 98–100, 99 §2º, 98 §6º; **TJPA AI 0820042-02.2025.8.14.0000** (2ª T. Dir. Público, Mairton Carneiro, j. 04/05/2026 — veda critério fixo, exige 99 §2º); AI 0802127-03.2026.8.14.0000 (risco); Rec. CNJ 159/2024, Anexo B-4 | intimação para comprovar (99 §2º) com Infojud/Renajud; revogação se não comprovada; subsidiário: parcelar custas |
| **T02** | Emenda da inicial — Tema 1.198 STJ (litigância abusiva) | inicial não traz os elementos mínimos **e** há indícios de abuso (flags) | inicial e anexos; relatório antifraude | juízo já declarou a inicial apta | CPC 319–321, 330; **Tema 1.198 — REsp 2.021.665/MS, Corte Especial, Moura Ribeiro, j. 13/03/2025, publ. DJEN 11/06/2026** (emenda por litigância abusiva; veda exigir cópia do contrato); Rec. CNJ 159/2024; TJPA 1ª T. Centeno (Ap. 0800038-32.2026.8.14.0121) a favor; 3ª T. Anete Penna e 2ª T. Gleide Moura (risco) | emenda **fundamentada e proporcional**: procuração atualizada, comprovante de residência, ratificação pessoal. **Nunca cópia do contrato; não pedir extinção direta** |
| **T03** | Litispendência | há processo em curso com tríplice identidade | cópia da inicial/andamento do outro feito | contratos comprovadamente distintos | CPC 337 VI/VII, 485 V, 55 | extinção sem mérito; subsidiário: conexão |
| **T03.1** | Coisa julgada (subtese de T03) | há processo transitado com tríplice identidade | certidão de trânsito e sentença | — | CPC 337 VII §4º, 502, 508 | extinção sem mérito |
| **T04** | Fracionamento de demandas | autor tem ≥ 2 ações contra o réu | relatório antifraude com as ações | causas de pedir realmente distintas | CPC 55/58/59, 5º/6º/77/80; Tema 1.198 (limite: não exigir juntada de outras iniciais); Rec. CNJ 159 Anexo A-6 / B-8; NT 06/2022 Cijepa + Painel de Monitoramento de Potenciais Anomalias Processuais do TJPA; 2ª TR RI 0800686-51.2025.8.14.0087 (multa por litigância fragmentada); 3ª T. Ap. 0802538-44.2025.8.14.0012 (risco: fracionar é faculdade) | reunião no prevento + emenda proporcional; dano moral único e sucumbência pelo conjunto. Escalada (a)/(b)/(c) de T10 |

### Prejudicial

| Id | Tese | Quando aplicar | Provas | Afastam | Fundamentação (conferida) | Pedido |
|---|---|---|---|---|---|---|
| **T05** | Prescrição — **CDC 27, 5 anos, trato sucessivo** | há 1º desconto e data de ajuizamento | HISCRE/extrato com 1º e último desconto | reclamação que interrompa; descontos iniciados há < 5 anos | **CDC 27** (prazo); CC 205 / 206 §3º V **só como afastados**; CPC 487 II; STJ AgInt AREsp 1.056.534/MS, 1.130.505/MS, 1.478.001/MS, 1.728.230/MS (linha dominante: último desconto); AgInt REsp 1.791.165/RJ e AgInt AREsp 2.439.042/MG (1º desconto — só argumento); **TJPA EDcl 0004156-73.2019.8.14.0107** (1ª T., 23/02/2026) e **EDcl 0805230-14.2024.8.14.0024** (3ª T., 18/11/2025) — parcelar; AgInt 0878013-80.2023.8.14.0301 e 0800235-73.2024.8.14.0018 (risco: sem prescrição enquanto houver desconto) | principal: prescrição quinquenal se o último desconto é anterior a 5 anos do ajuizamento (CPC 487 II); subsidiário: parcelas anteriores ao quinquênio |

**Decidido em 20/10/2026:** tese principal = CDC 27 (5 anos) em trato sucessivo, termo no **último desconto**, conforme STJ e TJPA; subsidiária = prescrição **parcelar**; o **1º desconto** fica só como argumento acessório (linha minoritária do STJ), não como tese. A peça **não** sustenta prazo trienal (CC 206 §3º) nem decadência (CC 178): nenhuma decisão do TJPA no período os aplicou a favor do banco.

### Mérito

| Id | Tese | Quando aplicar | Provas necessárias | Provas que afastam | Fundamentação (conferida) | Pedido |
|---|---|---|---|---|---|---|
| **T06** | Contratação válida (biometria / assinatura digital / geolocalização / logs) | contrato localizado **e** há tipo de assinatura | **contrato**; **log de autenticação**; biometria com liveness; geolocalização; documento; áudio SAC; averbação INSS | IP/geo em outra UF; BO anterior; assinatura física impugnada sem perícia viável; dados divergentes ou **só telas sistêmicas** | CC 104/107/421-422; MP 2.200-2 art. 10 §2º + Lei 14.063/2020 art. 4º (parâmetro analógico); **Lei 10.820/2003 art. 6º §5º (45% = 35+5+5, Lei 14.601/2023; MP 1.355/2026 caducou em 31/08/2026) + IN PRES/INSS 138/2022 até IN 213/2026** — exigências novas não retroagem; CPC 370, 373 II, 411, 429 II; Súmulas 297 e 479; **Tema 1.061 (REsp 1.846.649/MA, 2ª Seção, Bellizze, 24/11/2021)**; **REsp 2.197.156/SP** (3ª T., Nancy Andrighi, 03/03/2026 — sem ICP-Brasil é válido); TJPA 0802924-08.2024.8.14.0013, 0804017-84.2025.8.14.0008, 0803239-24.2024.8.14.0017, 0800212-94.2024.8.14.0029, 0800322-10.2025.8.14.0110 (dossiê completo dispensa perícia); **risco: 0800274-05.2023.8.14.0051** (Kátia Sena, 01/09/2026 — só telas = anulação para perícia) | improcedência; subsidiário: perícia |
| **T06.1** | RMC/RCC — **validade** com TCE + CCB + biometria + faturas + TED (subtese de T06; regra condicional) | produto RMC/RCC/cartão benefício **e** contrato **e** `rmc_tce_localizado` **e** crédito em conta do autor | TCE/termo com destaque de RMC e CET, CCB; faturas e saque; TED; biometria; autorização de margem | nenhum uso além do saque; termo sem destaque (biometria prova assinatura, não informação) | Lei 10.820 art. 6º §5º; CDC 6º III, 31, 46; **Ap. 0803213-13.2025.8.14.0107** (1ª T., Centeno, 28/09/2026); **Ap. 0813629-20.2024.8.14.0028** (3ª T., Norat, 01/09/2026 — conversão impossível); risco: Ap. 0902391-37.2022.8.14.0301 e 0800675-50.2025.8.14.0110 (3ª T.) | improcedência; manutenção do cartão |
| **T06.1.1** | RMC/RCC **sem TCE** — subsidiária (filha de T06.1) | produto RMC/RCC **e** `rmc_tce_localizado = false` → também dispara **X09 (sinalizar acordo)** | TED; faturas/histórico | crédito a terceiro/sem comprovante | CC 138/139/170/368; CDC 42 p.ú.; TJPA 1ª T. (AgInt 0812585-97.2023.8.14.0028, 0800567-41.2023.8.14.0029 — taxa média BACEN, dobro); 2ª T. AgInt 0814170-87.2023.8.14.0028 e 3ª T. AgInt 0800235-73.2024.8.14.0018 / Ap. 0902391-37.2022.8.14.0301 (restituição simples); **2ª TR RI 0800613-16.2024.8.14.0087 rejeita conversão** | subsidiário: conversão à taxa média BACEN, repetição simples, compensação; nos JEC: compensação + simples |
| **T07** | Recebimento e uso dos valores | crédito em conta **do próprio autor** | **comprovante de TED** vinculado ao contrato; extrato; descontos sem reclamação | conta de terceiro/aberta na data; mera alegação de depósito; saque em praça distante | CC 884–886; CC 174/187/422; TJPA 0802924-08.2024.8.14.0013, 0800322-10.2025.8.14.0110; TRs RI 0806610-27.2024.8.14.0039 e RI 0801592-89.2022.8.14.0008 (só crédito provado conta) | improcedência; subsidiário: compensação integral |
| **T08** | Ausência de dano moral — **só nas 3 hipóteses do TJPA** | pedido de dano moral **e** `hipotese_afastamento_dano_moral` ∈ {contratação provada, inércia prolongada, RMC com crédito recebido} | TED; tempo até a reclamação; dossiê de autenticação | reclamação prévia ignorada; benefício mínimo comprometido | CC 186/927/944; **Ap. 0800054-39.2024.8.14.0029** (3ª T., 14/04/2026 — RMC com crédito, sem DM); RI 0806610-27.2024.8.14.0039 (inércia); Ap. 0802924-08.2024.8.14.0013 (contratação provada); risco: Ap. 0803062-39.2025.8.14.0045 (R$ 79 → R$ 5.000 in re ipsa) | improcedência do dano moral; subsidiário: T08.1 |
| **T08.1** | Quantum — **parâmetro R$ 3.000, faixa TJPA R$ 3–5 mil** + Tema 1.435 (filha de T08) | sempre que há pedido de dano moral | proporção do desconto e duração | — | CC 944; TJPA R$ 3.000: AgInt 0878013-80.2023.8.14.0301 (1ª T.), AgInt 0800132-68.2025.8.14.0103 e Ap. 0801423-06.2022.8.14.0040 (3ª T.); teto R$ 5.000: Ap. 0000049-74.2014.8.14.0005 (2ª T., 15/09/2026), Ap. 0800987-68.2023.8.14.0054; piso R$ 1.000 (Gleide Moura); **Tema 1.435/STJ — REsp 2.219.864/MG, Rel. Gallotti, afetação 18/05/2026 (suspensão só de REsp/AREsp)**; Súmula 362 | quantum moderado (R$ 3.000; faixa 3–5 mil), correção do arbitramento; **não pedir sobrestamento no 1º grau** — Tema 1.435 só na fase recursal |

**Erro mais grave desta tipologia:** afirmar crédito em conta do autor quando a conta é de terceiro. T07 e T09 só entram com comprovante em nome do próprio autor.

### Subsidiária

| Id | Tese | Quando aplicar | Provas | Afastam | Fundamentação (conferida) | Pedido |
|---|---|---|---|---|---|---|
| **T09** | Compensação dos valores creditados e repetição simples | valor creditado ao autor | comprovante do crédito vinculado ao contrato; total descontado | crédito a terceiro/sem comprovante idôneo | CC 170, 368–380, 884; CDC 42 § único; **EAREsp 676.608/RS — Corte Especial, Og Fernandes, j. 21/10/2020, DJe 30/03/2021** (30/03 é a publicação); TJPA AgInt 0800672-18.2023.8.14.0029 (1ª T., 03/11/2025 — ainda aplica a modulação); compensação dominante: EDcl 0004156-73.2019, AgInt 0815385-04.2022, EDcl 0805230-14.2024, RI 0800328-57.2025; risco sem TED: RI 0806610-27.2024, RI 0801592-89.2022 | compensação; repetição simples; subsidiário: dobro só após 30/03/2021 |

**⏳ Pendência monitorada (T09):** Tema 929/STJ (REsp 1.963.770/CE) reafirmado pela Corte Especial em set/2026 **sem modulação** (fonte secundária; acórdão pendente). A modulação segue como argumento enquanto o TJPA a aplicar; o **M9 (monitoramento de publicações)** deve acompanhar a publicação e abrir revisão de T09.

### Sinal (não é argumento autônomo)

| Id | Tese | Quando aplicar | Provas | Fundamentação (conferida) | Providências |
|---|---|---|---|---|---|
| **T10** | Sinais de litigância predatória | advogado com ≥ 10 ações/mês contra o réu (nível *atenção*; *forte* = ≥ 30) **e** flags do M4 **confirmados por advogado com OAB** | relatório antifraude com decisão humana | CPC 77, 80, 139 III, 321, 385; Tema 1.198; Rec. CNJ 159/2024; NT 06/2022 Cijepa + Painel de Anomalias do TJPA; TJPA a favor: Kátia Sena (0808445-32.2024.8.14.0045, 0804916-89.2024.8.14.0017), Centeno (0800038-32.2026.8.14.0121); contra: Gleide Moura (0800798-60.2025.8.14.0009), Anete Penna (0800040-02.2026.8.14.0121), Filomena Buarque (0808446-17.2024.8.14.0045) | escalada em três níveis (abaixo) |

**Escalada de providências (T04/T10), decidida em 19/10/2026 e ajustada em 20/10/2026:**

| Nível | Providência | Autorização |
|---|---|---|
| (a) padrão | **emenda fundamentada e proporcional** (procuração atualizada, comprovante de residência atual, ratificação pessoal) citando Painel de Monitoramento de Potenciais Anomalias Processuais do TJPA + Tema 1.198 + Rec. CNJ 159; depoimento pessoal do autor + exibição de documentos. **Nunca cópia do contrato; não pedir extinção direta** (TJPA dividido: mantêm 1ª T. e 3ª T./Kátia Sena; anulam 2ª T./Gleide Moura e 3ª T./Filomena Buarque, Anete Penna) | flags confirmados por `human_decide` |
| (b) | comunicação institucional do padrão ao **Cijepa/NUMOPEDE do TJPA** (no TJPA, a ferramenta é o Painel de Anomalias), fora da peça, linguagem neutra, **sem imputar conduta a pessoa**; pressupõe nível *forte* (≥ 30 ações/mês) | **dupla autorização por escrito: sócio FBS + jurídico do cliente**, registrada na plataforma |
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
| **X09** (nova, 20/10/2026) | RMC/RCC **sem TCE** / sem prova da informação sobre o produto cartão | **sinalizar acordo**; T06.1 desativada; minuta segue com T06.1.1 (subsidiária). Sem TCE o TJPA converte (taxa média BACEN, dobro na 1ª/2ª T., DM R$ 3.000); a 2ª TR nem converte |

## 6. Sinais de acordo

**Política (regra dos três pilares, confirmada em 19/10/2026; quarto pilar em RMC acrescentado em 20/10/2026):** defender quando há **contrato + trilha de autenticação + crédito em conta do autor** (e, em RMC/RCC, **TCE**). Acordar cedo quando falta qualquer pilar ou há indício de fraude real. Exceção: **autor serial (≥ 3 ações contra o réu)** — não acordar salvo decisão do cliente.

**Acordar quando:** contrato não localizado · crédito não é em conta do autor · indício de fraude contra o autor · **RMC/RCC sem TCE (X09)**.

**Não acordar quando:** biometria facial ou ICP **e** crédito em conta do autor (caso forte; acordo alimenta a litigância predatória) · autor com ≥ 3 ações contra o réu (serial), salvo decisão do cliente.

**Faixas provisórias (`provisorio: true`, recalibrar em 90 dias)** — o painel M10 (métrica M05, condenação média por comarca) recalibra cada faixa com a média de condenação da carteira. O `provisorio` **não bloqueia** a aprovação (invariante do validador só olha OAB, timestamp e referências conferidas):

| Grupo de comarcas | Faixa (R$) | Faixa de condenação observada no TJPA — 12 meses (dano moral, levantamento B3) |
|---|---|---|
| Região Metropolitana de Belém (Belém, Ananindeua, Marituba, Benevides, Santa Bárbara, Santa Izabel) | 1.000 – 4.000 | 3.000 – 5.000 (moda 3.000) |
| Interior — polos (Santarém, Marabá, Castanhal, Parauapebas, Altamira) | 1.500 – 5.000 | 3.000 – 5.000 (moda 3.000) |
| Interior — demais comarcas | 1.500 – 6.000 | 3.000 – 5.000; sem diferença sistemática Belém × interior na amostra |

Mínimo observado R$ 1.000 (2ª T., Gleide Moura); Turmas Recursais até R$ 8.000. Ao estimar a exposição de cada caso, somar a repetição (simples ou em dobro, T09) e descontar a compensação dos valores creditados.

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
| gratuidade_x_renda | gratuidade com renda > 5 SM — **flag de triagem interna** (decide se T01 é avaliada); o TJPA veda critério fixo, a peça usa elementos concretos | média | sim |
| peticao_padronizada | inicial ≥ 95 % similar a outras do mesmo advogado, sem individualizar o contrato | baixa | não |
| assinatura_procuracao_divergente | assinatura da procuração visivelmente diversa do RG (sinal visual, sem laudo) | média | não |
| indicio_fraude_contra_autor | **a favor do autor**: IP/geo incompatível, conta de terceiro, sem biometria, conta aberta na data — avisa que defender é temerário | alta | não |

## 8. Modelo da contestação (seções, na ordem)

1. Endereçamento, qualificação e tempestividade
2. Síntese da demanda (até 8 linhas, sem adjetivos) — *com página*
3. Preliminares — T01, T02, T03, T03.1, T04 (omitir se nenhuma se aplicar; T01 só com elementos concretos; T02/T04 emenda proporcional, nunca cópia do contrato nem extinção direta) — *com página*
4. Prejudicial de mérito — prescrição — T05 (CDC 27, último desconto; parcelar como subsidiária; sem trienal/decadência) — *com página*
5. Dos fatos — a contratação (linha do tempo: proposta → autenticação → formalização → averbação → crédito → descontos → reclamação → ajuizamento) — *cada evento com página*
6. Do mérito — validade da contratação — T06, T06.1, T06.1.1; enfrentar Súmula 479 e Tema 1.061; citar REsp 2.197.156/SP — *com página*
7. Do recebimento e utilização dos valores — T07 (somente se a conta é do autor) — *com página*
8. Do dano moral — T08 (só nas três hipóteses) e T08.1 (quantum R$ 3.000; Tema 1.435 sem sobrestamento no 1º grau)
9. Pedidos subsidiários — compensação, repetição simples, juros — T09 — *com página*
10. Providências processuais — T10 (só com flags confirmados; linguagem neutra; emenda proporcional) — *com página*
11. Das provas (depoimento pessoal, perícia grafotécnica/técnica em logs, juntada; Infojud/Renajud em T01)
12. Dos pedidos (preliminares → prejudicial → improcedência → subsidiários → sucumbência → intimações)
13. Rol de documentos (cada anexo com o tipo do playbook)

**Regra de citação:** toda afirmação de fato cita a página dos autos ou o documento anexo identificado. Sem página, sem afirmação.

**Estilo:** português formal, frases curtas, sem adjetivar o autor ou o advogado adverso; referências legais só as conferidas; tom respeitoso obrigatório com autor idoso/beneficiário do INSS (Estatuto da Pessoa Idosa — Lei 10.741/2003).

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
| R03 | T06 só foi usada com contrato + log/biometria anexos; T06.1 só com TCE + CCB + faturas + TED | B |
| R04 | T07/T09 só com comprovante de crédito em conta do **próprio** autor | B |
| R05 | Nenhuma expressão imputa fraude/má-fé sem flag confirmado por advogado | B |
| R06 | Produto correto (consignado × RMC × RCC); valores e datas batem com o dossiê | B |
| R07 | Pedidos subsidiários presentes (compensação, repetição simples, quantum) | B |
| R08 | Tom respeitoso; sem "mero aborrecimento" quando o benefício mínimo foi comprometido; dano negado só nas três hipóteses de T08 | |
| R09 | Sinal de acordo avaliado e registrado antes de protocolar; se acordo, recomendação FBS (valor + faixa) enviada ao jurídico do cliente | |
| R10 | Providências de nível (b)/(c) só com dupla autorização por escrito registrada na plataforma | B |
| **R11** (nova) | T01 não cita limiar de renda; T02/T04/T10 não pedem cópia do contrato nem extinção direta; T08.1 não pede sobrestamento pelo Tema 1.435 no 1º grau | B |

**Motivos de recusa padrão:** fato sem prova citável · tese sem prova necessária · referência legal não conferida/inexistente · produto/valores/datas divergentes · linguagem imputa fraude sem decisão humana · caso deveria ir para acordo/escalada · pedido vedado pelo playbook (cópia do contrato, extinção direta, limiar de renda, sobrestamento em 1º grau).

## 10. Métricas

| Id | Métrica | Meta (a confirmar no piloto) |
|---|---|---|
| M01 | Tempo médio de revisão por contestação | < 30 min |
| M02 | Aprovação sem alteração substancial | > 60 % após 200 casos |
| M03 | Subsídios faltantes detectados antes da defesa (X01/X07/X09) | > 90 % |
| M04 | Taxa de êxito por tese × comarca vs. baseline FBS | ≥ baseline + 10 p.p. |
| M05 | Condenação média (dano moral + repetição) por comarca | −20 % vs. baseline; alimenta as faixas de acordo; referência externa TJPA 12 meses: DM R$ 3.000–5.000 |
| M06 | Custo de tokens por processo | < US$ 2 por contestação |
| M07 | Concordância modelo × revisor sênior | > 0,85 |
| M08 | Flags antifraude confirmados por humano | recalibrar se precisão < 50 % |
| M09 | Acordos sinalizados × realizados | calibrar faixas trimestralmente |

## 11. Decisões da revisão (19/10/2026)

Sessão 1 de revisão — Gustavo Fonseca, OAB/PA 12.724. Status permanece **em revisão**. Itens então marcados ⏳ foram fechados na sessão 2 (seção 12), salvo os indicados.

| # | Tema | Decisão |
|---|---|---|
| 1 | Escopo | RMC/RCC permanece neste playbook, como subtese **T06.1** de T06. |
| 2 | T05 prescrição | Prazo aguardava levantamento TJPA → **fechado na sessão 2** (CDC 27, trato sucessivo). |
| 3 | T08 dano moral | Confirmado: negação do dano + subsidiário quantum moderado → **refinado na sessão 2** (negação só nas 3 hipóteses). |
| 4 | T06.1 RMC | Postura aguardava levantamento → **fechado na sessão 2** (regra condicional pelo TCE). |
| 5 | Litigância predatória (T04/T10) | Escalada em três níveis: (a) padrão; (b) comunicação institucional ao Cijepa/NUMOPEDE do TJPA; (c) representação à OAB-PA. **(b) e (c) exigem dupla autorização por escrito (sócio FBS + jurídico do cliente), registrada na plataforma.** |
| 6 | Política de acordo | Confirmada a regra dos três pilares e a exceção do autor serial (≥ 3 ações). |
| 7 | X01 contrato não localizado após subsídio | **Ambas** as ações em paralelo: sinalizar acordo **e** gerar minuta só com preliminares + antifraude; escalar ao advogado da carteira. |
| 8 | X03 indício de fraude real contra o autor | Confirmado: sinalizar acordo imediato. |
| 9 | X05 | Valor da causa > **R$ 30 mil** exige segunda revisão por sócio (antes: 60 mil). |
| 10 | Alçadas de acordo | Removidos os três níveis por valor. Toda proposta passa pelo jurídico do cliente; a FBS recomenda com valor sugerido e faixa. |
| 11 | Antifraude e revisão | Concentração de advogado em dois níveis (≥ 10 / ≥ 30 ações/mês). Procuração antiga > 180 dias. Revisor final: advogado com OAB da carteira; sócio obrigatório em X05, X02/X03 e comunicação externa. Tempo mínimo 15 min. |
| 12 | Faixas de acordo por comarca | Mantidas as ilustrativas (`provisorio: true`, `recalibrar_em_dias: 90`). |
| 13 | Perícia grafotécnica em contrato pequeno | Sem regra fixa de valor: alerta ao revisor (X08). |
| 14 | Campos do dossiê | **⏳ A CONFIRMAR COM O CLIENTE** — disponibilidade de log de autenticação, biometria e TED/PIX. |
| 15 | Cliente-piloto | Ainda não há. Piloto interno com casos encerrados da FBS primeiro; prospecção de Banpará / Basa / financeira regional em paralelo. |
| 16 | Referências legais | Seguiam `conferido: false` → **fechado na sessão 2**. |

## 12. Decisões da revisão (20/10/2026)

Sessão 2 de revisão — Gustavo Fonseca, OAB/PA 12.724. Base: levantamento de 19/10/2026 (`research_notes/Consignado TJPA referencias e jurisprudencia/levantamento.md`) e checklist de validação. Status permanece **em revisão**; a aprovação é ato separado. O validador aceita `status: aprovado` com OAB + timestamp (dry-run feito).

| # | Tema | Decisão |
|---|---|---|
| 1 | **T05 prescrição** | Tese principal = **CDC 27, 5 anos, trato sucessivo, termo no último desconto** (STJ: AgInt AREsp 1.056.534/MS, 1.130.505/MS, 1.478.001/MS, 1.728.230/MS; TJPA: EDcl 0004156-73.2019.8.14.0107, 1ª T., 23/02/2026; EDcl 0805230-14.2024.8.14.0024, 3ª T., 18/11/2025). Subsidiária = prescrição das parcelas anteriores a 5 anos. "1º desconto" só como argumento. CC 205/206 §3º só como "afastados"; CDC 26 (decadência) removido. Pendência removida. Novo campo `data_ultimo_desconto`. |
| 2 | **T06.1 RMC** | Regra condicional: com **TCE + CCB + biometria/assinatura + faturas + TED ao autor** → defender validade (Ap. 0803213-13.2025.8.14.0107, 1ª T., 28/09/2026; Ap. 0813629-20.2024.8.14.0028, 3ª T., 01/09/2026). Sem TCE/informação → **T06.1.1** (subsidiária: conversão à taxa média BACEN, repetição simples, compensação) + **X09 sinaliza acordo**. 2ª Turma Recursal rejeita conversão (RI 0800613-16.2024.8.14.0087). Pendência removida. Novo campo `rmc_tce_localizado`. |
| 3 | **T08 dano moral** | Negação **só nas 3 hipóteses** em que o TJPA afasta o dano: contratação provada; inércia prolongada do consumidor; RMC com crédito recebido (Ap. 0800054-39.2024.8.14.0029, 3ª T.). Fora delas → direto ao quantum (**T08.1**: parâmetro R$ 3.000, faixa TJPA R$ 3–5 mil, TRs até 8 mil) e registrar **Tema 1.435/STJ** (REsp 2.219.864/MG, Rel. Gallotti, afetação 18/05/2026 — suspensão só de REsp/AREsp; **não pedir sobrestamento no 1º grau**). Novo campo `hipotese_afastamento_dano_moral`. |
| 4 | **T02 Tema 1.198** | REsp 2.021.665/MS, Corte Especial, Rel. Moura Ribeiro, j. 13/03/2025, publ. DJEN 11/06/2026 — descrição corrigida: **emenda da inicial por litigância abusiva** (não ônus da prova). Conferido. |
| 5 | **T09 repetição em dobro** | EAREsp 676.608/RS — j. 21/10/2020, **DJe 30/03/2021 (publicação)**, Rel. Og Fernandes. Modulação mantida como argumento enquanto o TJPA a aplica (AgInt 0800672-18.2023.8.14.0029). `pendencia`: Tema 929 (REsp 1.963.770) reafirmado em set/2026 sem modulação — acórdão pendente; **M9 acompanha a publicação**. |
| 6 | **T01 gratuidade** | Removido o critério objetivo (3 SM) da peça; impugnação só com elementos concretos (Infojud/Renajud, extratos, patrimônio) — TJPA 2ª T. Dir. Público, AI 0820042-02.2025.8.14.0000, j. 04/05/2026 (veda critério fixo; exige CPC 99 §2º) e Rec. CNJ 159 Anexo B-4. Gatilho por renda mantido só como `condicao` interna. Conferido. |
| 7 | **Lei 10.820/2003 art. 6º §5º** | Margem **45% (35 + 5 RMC + 5 RCC, Lei 14.601/2023)**; MP 1.355/2026 caducou em 31/08/2026; IN de regência = **IN PRES/INSS 138/2022 alterada até IN 213/2026** (biometria/prova de vida); exigências novas não retroagem. **Lei 14.509/2022 removida** (servidores federais). Conferido. |
| 8 | **Bloco conferido** | Tema 1.061 (REsp 1.846.649/MA, 2ª Seção, 24/11/2021); Súmulas STJ 297/479/362; MP 2.200-2 art. 10 §2º + Lei 14.063/2020 art. 4º (+ **REsp 2.197.156/SP**, 3ª T., Nancy Andrighi, 03/03/2026); Rec. CNJ 159/2024 (item 20 = Anexo A); códigos TPU 11806, 9607, 9585, 7772, 10433, 11811 — sem código "RMC". |
| 9 | **"Recomendação CFOAB 001/2024"** | Não localizada em nenhuma fonte — **removida** de todo o playbook; substituída pela Rec. CNJ 159/2024. |
| 10 | **T04/T10 litigância predatória** | Pedido padrão = **emenda fundamentada e proporcional** (procuração atualizada, comprovante de residência, ratificação) citando Painel de Monitoramento de Potenciais Anomalias Processuais do TJPA + Tema 1.198 + Rec. CNJ 159; **nunca cópia do contrato; não pedir extinção direta** (TJPA dividido: mantêm 1ª T. e 3ª T./Kátia Sena; anulam 2ª T./Gleide Moura e 3ª T./Filomena Buarque, Anete Penna). Níveis a/b/c e dupla autorização mantidos. Novo item R11 no checklist. |
| 11 | **Demais decisões da sessão 1** | Mantidas. Faixas de acordo seguem `provisorio: true` (não bloqueia a aprovação — validador inalterado); `nota_calibracao` recebe a faixa de condenação observada no TJPA em 12 meses (R$ 3–5 mil). |
| 12 | **Referências restantes** | Todas as referências legais das teses e os assuntos CNJ estão `conferido: true` (artigos básicos de CPC/CC/CDC: "texto legal vigente"). Fora do levantamento, sem bloquear: classes CNJ 7/436; metas das métricas. |
| 13 | **Metadados** | `autor_nome: Gustavo Fonseca`, `autor_oab: PA 12724`; registro da sessão 2 em `revisoes`; status `em_revisao`. |

---

*Rascunho gerado em 19/10/2026; sessão 1 aplicada no mesmo dia; sessão 2 aplicada em 20/10/2026. Fonte da verdade: `playbooks/consignado-rmc-tjpa.playbook.yaml`.*
