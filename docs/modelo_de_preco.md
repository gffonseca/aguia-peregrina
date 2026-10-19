# Modelo de precificação / valuation para compra de créditos judiciais individuais (cível-consumidor e trabalhista) no Brasil — nota técnica (estado em 19/10/2026)

Convenções: valores em R$; "face" = valor nominal do crédito/pedido; "líquido" = o que efetivamente chega ao credor após honorários contratuais e descontos legais; `r` = taxa-alvo (TIR) nominal ao ano; `DF(t) = (1+r)^(-t)`. Tudo que está marcado **[PREMISSA]** é hipótese de modelagem sem fonte pública verificada nesta pesquisa; o que está marcado **[LACUNA]** precisa de dado próprio (jurimetria interna) ou de fonte ainda não obtida.

---

## KQ1 — Métodos da literatura e dos praticantes para precificar litígios e sentenças

### Takeaway
A precificação de um crédito litigioso é universalmente tratada como **valor esperado de uma árvore de decisão** (probabilidades subjetivas × resultados por nó, com análise de sensibilidade), que os funders transformam em **TIR/MOIC sobre caixa efetivamente realizado**; os benchmarks públicos de litigation finance (Burford: ROIC 83%, TIR 26%, vida média 2,6 anos, taxa de perda 10,2%) são a melhor referência pública de custo de capital/retorno exigido nesse mercado.

### Cited Findings
- Método de árvore de decisão (Marc Victor): a árvore mapeia "os vários pontos de virada do caso", cada incerteza recebe uma estimativa probabilística baseada em julgamento, combinadas por teoria da probabilidade em "valores médios ponderados por probabilidade" (valor esperado); a **análise de sensibilidade** mostra como o valor esperado muda conforme a probabilidade de sucesso em um ponto específico varia — [Mediate.com, entrevista com Marc Victor, 13/07/2009](https://mediate.com/advanced-decision-tree-analysis-in-litigation-an-interview-with-marc-victor-part-ii/)
- Burford Capital (Principal Finance, ativos concluídos desde a fundação até 31/12/2025): **ROIC acumulado 83%, TIR acumulada 26%**, realizações de US$ 3,767 bi, **vida média ponderada (WAL) 2,6 anos**, **taxa de perda vitalícia 10,2%** (perdas em 15% do custo investido, com recuperação de 30% do custo nos ativos perdedores) — [Burford Capital, 8-K ex. 99.2, 26/02/2026](https://www.sec.gov/Archives/edgar/data/1714174/000171417426000006/bur-20260226xex992.htm)
- Dispersão por safra na Burford (ROIC / TIR de ativos concluídos): 2009: 251%/32%; 2011: −2%/0%; 2014: 31%/10%; 2015: 242%/131%; 2019: 55%/15%; WAL entre 2,0 e 4,0 anos — [Burford, Portfolio as of 31 Dec 25](https://s206.q4cdn.com/737820215/files/doc_financials/2025/q4/2026-02-26-Burford-Capital-Principal-Finance-and-Asset-Management-Portfolio-as-of-31-Dec-25-FINAL.pdf)
- Omni Bridgeway: **MOIC de 2,6x** nas conclusões do 1S FY26 e 3,0x no 2T26 (posição em 31/12/2025); TIR, duração e taxa de perda não divulgadas no release — [Omni Bridgeway, 09/02/2026](https://omnibridgeway.com/insights/press-releases/all-press-releases/press-release/2026/02/12/omni-bridgeway-releases-2q26-portfolio-update-with-excellent-completion-metrics)
- No Brasil, não existem estatísticas oficiais ou consolidadas de litigation finance; há "mais de 40 gestoras focadas em special sits"; mercado global estimado em US$ 25,8 bi (2026) → US$ 41,37 bi (2030) — [Capital Aberto, 08/07/2026](https://capitalaberto.com.br/regulacao/2026/07/litigios-financiamento-interesse-investidores)
- Fundos que compram créditos trabalhistas cobram "no mínimo 25% do valor da causa, às vezes mais de 50%", e o trabalhador ainda paga o advogado — [NSC Total citando Valor, 20/08/2021](https://www.nsctotal.com.br/?p=2848769)

### Inferences
- Para créditos pulverizados (tickets de R$ 3k–50k), a árvore de decisão deve ser **parametrizada por tabela** (tese × tribunal × réu × fase), não construída caso a caso; o Monte Carlo só agrega valor para (a) duração (distribuição assimétrica) e (b) correlação entre casos do mesmo réu/tese (risco sistêmico de mudança jurisprudencial, p.ex. um tema repetitivo).
- O custo de capital-alvo de um comprador brasileiro deve ser lido como **CDI + spread de risco de litígio**: a Burford entrega TIR 26% em dólar com perda de 10%; com Selic a 13,75% (ver KQ3), um alvo nominal em reais de **30–40% a.a. para créditos sem trânsito em julgado e 20–25% a.a. para créditos transitados contra réu solvente** é coerente com esses benchmarks **[PREMISSA]**.
- Modelo de perda (LGD) deve separar três componentes: perda jurídica (improcedência/reforma), perda de quantum (redução do valor) e perda de cobrança (insolvência/impenhorabilidade) — a Burford reporta recuperação de 30% do custo mesmo nos casos perdidos, o que mostra que "perda" raramente é 100%.

### Gaps
- Não encontrei paper acadêmico brasileiro com metodologia pública de precificação de carteiras de créditos judiciais pulverizados (ABJ/Turivius/Data Lawyer não publicam notas metodológicas de pricing acessíveis por busca) **[LACUNA]**.
- Não obtive dados de TIR/duração de FIDCs de precatórios brasileiros (lâminas em Gorila/Mais Retorno existem — RWM Preca, Precpago FIDC-NP, Momento Precatórios I, Jugis I, Res Judicata, CJP — mas não foram lidas) **[LACUNA]**.

---

## KQ2 — Números públicos confiáveis de duração e resultado por tribunal (CNJ Justiça em Números 2026; TJPA, TRT-8, STJ, TST)

### Takeaway
O Justiça em Números 2026 (ano-base 2025) dá médias nacionais por segmento (Estadual: conhecimento 2a8m, execução 4a9m; Trabalho: conhecimento 8m, execução 3a9m; recursos: 2º grau estadual 8m, STJ 8m, TST 1a8m) e a taxa de congestionamento do TRT-8 (37,7%); **não há, em fonte pública acessível, tempo médio do TJPA nem taxa de reforma atualizada por tribunal** — essas células da tabela precisam vir do DataJud.

### Cited Findings
- Justiça em Números 2026 (ano-base 2025): 40,9 mi de casos novos; acervo 75,5 mi (59 mi em tramitação efetiva); taxa de congestionamento geral 62,6% (líquida 56,6%); **execução 71%, conhecimento 59%; trabalho-conhecimento 39,3%, trabalho-execução 64%; TRT da 8ª Região 37,7%**; TJGO 47,6% (menor estadual) e TJES 71% (maior) — [Projuris, 29–30/09/2026](https://www.projuris.com.br/blog/justica-em-numeros-2026/)
- Tempo médio de tramitação (processos baixados em 2025): **Estadual — total 3a8m, conhecimento 2a8m, execução 4a9m; Federal — 3a5m / 2a / 5a3m; Trabalho — 2a7m / 8m / 3a9m**; primeiro grau até a sentença: conhecimento 1a3m, execução 4a11m (Estadual 5a4m; Trabalho 1a6m); **recursos até a baixa: 2º grau estadual 8 meses; TRFs 2 anos; STJ 8 meses; TST 1 ano e 8 meses** — [Projuris, 29–30/09/2026](https://www.projuris.com.br/blog/justica-em-numeros-2026/); confirmado parcialmente por [Judit, 2026](https://judit.io/blog/noticias/justica-numeros-2026-recorde-processos/) (conhecimento 2a5m, execução 4a9m, trabalhista 2a7m)
- Conciliação: 11,2% dos processos resolvidos por acordo em 2025; **conhecimento trabalhista 37,9%, execução trabalhista 7,9%**; acordos na execução geral 7,5% — [Projuris, 29–30/09/2026](https://www.projuris.com.br/blog/justica-em-numeros-2026/)
- Taxa de reforma de decisões — único dado público com granularidade por segmento é de 2009 (CNJ, publicado 2010): tribunais superiores 22,5%; Justiça do Trabalho 27%; Estadual só tem recorribilidade (33%) — [Machado Meyer citando Conjur, 14/04/2011](https://www.machadomeyer.com.br/pt/imprensa-ij/indice-de-reforma-de-decisoes-preocupa-advogados)
- TJPA: única notícia pública com ranking é de 2015 (ano-base 2014): 2ª menor taxa de congestionamento entre tribunais de médio porte; 4º lugar no IPC-Jus — [Brasil 61 / TJPA, 30/09/2015](https://brasil61.com/noticias/justica-em-numeros-judiciario-paraense-cresce-em-desempenho-segundo-cnj-tjpa150958)
- Pará saiu do regime especial de precatórios por decisão de 30/12/2022 (4º estado a entrar no regime geral, após AL, AM e ES): precatórios apresentados até 2 de abril entram na LDO para pagamento até o fim do exercício seguinte — [IBDP / Conjur, 09/01/2023](https://www.ibdp.org.br/?p=10393); em 2019 a PGE/PA afirmava RPVs pagas em 60 dias e precatórios no prazo constitucional, estoque R$ 190 mi — [O Liberal, 15/09/2019](https://www.oliberal.com/economia/precatorios-n-o-s-o-um-problema-grave-1.193060)
- Consumidor.gov.br 2025: índice de solução geral 81,43%, prazo médio de resposta 6 dias; aéreo 83,47%, bancos/financeiras/cartões 82,21%, energia elétrica 82,20%; 2,33 mi de reclamações finalizadas — [MJ, Boletim Consumidor.gov.br 2025](https://www.gov.br/mj/pt-br/assuntos/seus-direitos/consumidor/defesadoconsumidor/Biblioteca/boletins-1/boletim-consumidor-gov-br-2025-vfinal.pdf)

### Inferences
- **Tabela-base de duração (nacional, a ser substituída por DataJud TJPA/TRT-8 assim que calibrada):**

| Fase | Cível estadual | Trabalhista | Fonte |
|---|---|---|---|
| Ajuizamento → sentença 1º grau | ~15 meses (1a3m, nacional) | ~8 meses | JN 2026 |
| Recurso 2º grau (até baixa) | ~8 meses | TRT: **[PREMISSA]** 10–12 m (TRT-8 tem congestionamento baixo, 37,7%) | JN 2026 |
| STJ / TST | 8 meses / 1a8m | — / 1a8m | JN 2026 |
| Execução/cumprimento até sentença de extinção | 5a4m (estadual) — mas é média contaminada por devedores insolventes | 1a6m | JN 2026 |

- Para réu **banco/concessionária/companhia aérea solvente** o cumprimento de sentença não segue a média de 5 anos: o pagamento ocorre por depósito voluntário (prazo de 15 dias do art. 523 CPC) ou por SISBAJUD; **[PREMISSA]** 3–12 meses do trânsito em julgado ao alvará, a calibrar com eventos de cobrança próprios.
- Taxa de reforma: usar **[PREMISSA]** 20–30% de provimento (total ou parcial) de recurso do réu em 2º grau para teses de consumo de massa, e 10% no STJ/TST condicionado à admissibilidade (RR/REsp em causa de pequeno valor raramente sobe) — a calibrar via DataJud (movimentos de provimento/desprovimento).

### Gaps
- Painéis do CNJ (Justiça em Números interativo, "Estatísticas do Poder Judiciário") trazem tempo médio e recorribilidade por tribunal, mas não foram acessíveis via fetch nesta pesquisa; TJPA e TRT-8 não publicam série própria indexável **[LACUNA — extrair do painel CNJ ou do DataJud]**.
- Taxa de reforma por tribunal atualizada (TJPA, TRT-8, STJ, TST) não existe em fonte pública consolidada **[LACUNA]**.
- Tempo médio JEC/Turma Recursal TJPA e taxa de acordo em audiência JEC/CEJUSC por tese não encontrados **[LACUNA]**.

---

## KQ3 — Como modelar juros e correção depois da Lei 14.905/2024 e da ADC 58 (cível e trabalhista)

### Takeaway
Desde 30/08/2024 o crédito cível cresce por **IPCA (art. 389 CC) + taxa legal (art. 406 CC = Selic − IPCA, piso zero, juros simples somados mês a mês)**, o que na prática aproxima o acréscimo nominal da Selic (~13,75% a.a. hoje); na Justiça do Trabalho o TST (3ª Turma, 13/11/2025; SDI-1 em dez/2024, sem efeito vinculante) aplica: IPCA-E na fase pré-judicial, Selic do ajuizamento até 29/08/2024 e, a partir de 30/08/2024, IPCA + (Selic − IPCA).

### Cited Findings
- Lei 14.905/2024: publicada em 01/07/2024, vigência em 30/08/2024; art. 389: sem índice convencionado, correção pelo IPCA; art. 406: juros legais = Selic deduzido o IPCA, **resultado negativo = zero**; metodologia pelo CMN (Res. 5.171/2024, 29/08/2024) e divulgação pelo BCB; **taxas mensais somadas (juros simples)**; primeira taxa legal (ago/2024) 0,605306% — [CNB/SP, 09/01/2025](https://cnbsp.org.br/2025/01/09/artigo-lei-14-905-2024-uso-da-taxa-legal-como-indice-de-juros-moratorios-por-flavio-da-silva-andrade/)
- Fórmula operacional: Taxa Legal do mês = Selic mensal − IPCA-15 do mês anterior (piso zero), pro rata em períodos parciais — [SOS Cálculos](https://www.soscalculos.com.br/informacoes/taxa-legal/)
- Valor de referência: Comunicado BCB nº 44.301 (01/12/2025): **taxa legal de dezembro/2025 = 0,851001% a.m.** (fator Selic 1,01052703; fator IPCA 1,0020) — [Okai, Comunicado 44.301](https://okai.com.br/documento/2025-12-01/comunicado-n-44-301)
- Macro em 19/10/2026: Copom (281ª reunião, 16/09/2026) reduziu a **Selic para 13,75% a.a.**; Focus: IPCA 4,9% (2026) e 4,3% (2027) — [Atlas Público/BCB, 16/09/2026](https://atlaspublico.com.br/bcb/noticias/copom-reduz-selic-para-13-75pct-ao-ano-em-decisao-unanime-87748); IPCA 12 meses em set/2026 = 4,58%; Selic média set/2026 13,78% — [Valor Final, boletim set/2026](https://valorfinal.com.br/boletim-taxas)
- Trabalhista (TST, 3ª Turma, Rel. Balazeiro, j. 13/11/2025): **fase pré-judicial IPCA-E (ADC 58); do ajuizamento até 29/08/2024 Selic (que engloba juros e correção), inclusive para danos morais (Rcl 62.698 e E-RR 202-65.2011.5.04.0030, SDI-1); a partir de 30/08/2024 IPCA (art. 389) + juros = Selic − IPCA (art. 406, podendo ser zero)**; matéria de ordem pública, não sujeita a preclusão — [Legjur, ementa TST](https://www.legjur.com/jurisprudencia/eme/518.5173.8014.6544)
- SDI-1 do TST (dez/2024) uniformizou: até 29/08/2024 Selic (ADC 58); de 30/08/2024 IPCA + juros (Selic − IPCA); **sem efeito vinculante** — [Gilberto Melo citando Migalhas, 26/12/2024](https://gilbertomelo.com.br/?p=17528)
- TRT-9 (OJ EX SE 06, 2024/2025) sintetiza a tabela: até 29/08/2024 — pré-judicial IPCA-E + TR, judicial Selic; a partir de 30/08/2024 — pré-judicial IPCA + TR, judicial IPCA + (Selic − IPCA) — [TRT-9, 23/01/2025](https://www.trt9.jus.br/portal/noticias.xhtml?id=8885889)
- Precatórios (EC 136/2025, promulgada 09/09/2025): requisitórios de Estados/DF/Municípios expedidos a partir de 01/08/2025 — correção **IPCA + juros simples de 2% a.a.**; entes devem reservar 1% a 5% da RCL/ano conforme estoque em mora (+0,5 p.p. por década a partir de 2036); prazo federal de inscrição antecipado de 2 de abril para **1º de fevereiro**; acordos diretos com deságio permitidos — [IEPREV, 2025](https://www.ieprev.com.br/noticias/congresso-nacional-promulga-ec-1362025-e-redefine-o-regime-de-precatorios-no-pais); outra leitura diz "IPCA + 2% a.a. limitado à Selic" — [Monitor Mercantil, 22/07/2025](https://monitormercantil.com.br/impactos-da-pec-66-23-no-mercado-de-precatorios/) (divergência entre fontes sobre o teto; **conferir o texto da EC 136/2025**)

### Inferences
- **Modelo de crescimento nominal do crédito cível** (software): `V(t) = V0 × Π IPCA_m × (1 + Σ TL_m)` com `TL_m = max(0, Selic_m − IPCA15_{m−1})`; para projeção, usar `IPCA_esp` (Focus) e `Selic_esp` (curva), de modo que `g ≈ Selic`. Hoje: IPCA ~4,6% + TL ~9% ≈ **13,5% a.a. nominal** (juros simples na parcela TL).
- **Trabalhista**: três trechos no motor de cálculo (pré-judicial IPCA-E; judicial Selic até 29/08/2024; judicial IPCA + TL após). Como a maior parte das reclamações compradas em 2026 tem ajuizamento pós-2022, o trecho dominante é IPCA + TL ≈ Selic. Risco de modelo: a matéria não é vinculante e há divergência de Turmas; não precificar diferença maior que ±1 p.p. a.a. entre cenários.
- **Consequência de pricing**: como o crédito judicial rende ~Selic enquanto espera, o "custo da espera" do comprador é apenas o spread (TIR-alvo − Selic) mais o risco; isso explica por que créditos transitados contra réu solvente podem ser comprados a 70–85% da face mesmo com 12 meses de prazo (ver KQ5, exemplo i).
- **Precatórios pós-EC 136**: IPCA + 2% simples é bem abaixo da Selic → o crédito "perde" ~7 p.p. a.a. frente ao CDI enquanto espera, o que justifica deságios maiores (ver KQ6).

### Gaps
- Série completa da taxa legal (set/2024 → out/2026) não foi obtida (somente ago/2024 e dez/2025); o módulo deve consumir a série do BCB (SGS) diretamente **[LACUNA técnica, trivial]**.
- Texto literal da EC 136/2025 (teto Selic ou não) não lido **[LACUNA]**.

---

## KQ4 — Riscos jurídicos específicos: litigância predatória (Tema 1.198), impenhorabilidade/natureza alimentar, cessão de crédito trabalhista, tributação do deságio

### Takeaway
O Tema 1.198 do STJ (REsp 2.021.665-MS, j. 13/03/2025, publ. 11/06/2026) autoriza o juiz a exigir emenda da inicial diante de indícios de litigância abusiva — risco relevante justamente nas teses de massa (consignado, energia, aéreo), que deve entrar como probabilidade de extinção/atraso; a cessão de crédito trabalhista é admitida pelo TST (2021) mas o mercado só compra após 2ª instância; a tributação do deságio é controversa (STJ nega IR ao cedente; RFB exige ganho de capital desde SC 3.010/2025).

### Cited Findings
- Tese do Tema 1.198 (Corte Especial, REsp 2.021.665-MS): "Constatados indícios de litigância abusiva, o juiz pode exigir, de modo fundamentado e com observância à razoabilidade do caso concreto, a emenda da petição inicial a fim de demonstrar o interesse de agir e a autenticidade da postulação, respeitadas as regras de distribuição do ônus da prova"; julgado em **13/03/2025**, publicação **11/06/2026** — [Trilhante, Tema 1198](https://informativos.trilhante.com.br/temas-stj/tema-repetitivo-1198-stj); [Mattos Filho, 17/03/2025](https://www.mattosfilho.com.br/unico/tese-averiguacao-litigancia-abusiva/); exemplos de documentos exigíveis citados na questão submetida: procuração atualizada, declaração de pobreza e de residência, cópia do contrato e extratos bancários — [Teses e Súmulas](https://tesesesumulas.com.br/tese/stj/1198)
- CNJ Recomendação nº 159 (23/10/2024) sobre identificação, tratamento e prevenção da litigância abusiva — [Mattos Filho, 17/03/2025](https://www.mattosfilho.com.br/unico/tese-averiguacao-litigancia-abusiva/)
- STJ afetou repetitivo (Rel. Min. Isabel Gallotti) sobre se "o desconto indevido em benefício previdenciário, por si só, é suficiente para configurar dano moral presumido (in re ipsa)" — **pendente de julgamento em 25/05/2026** — [Cálculo Jurídico, 25/05/2026](https://calculojuridico.com.br/dano-moral-desconto-indevido-beneficio-previdenciario-stj/)
- Cessão de crédito trabalhista: ministro do TST (Douglas Alencar) considerou possível a venda de créditos trabalhistas (2021); antes a Justiça do Trabalho tratava o crédito como alimentar e indisponível; OAB/SC alerta para vedação ética de o próprio advogado comprar — [NSC Total, 20/08/2021](https://www.nsctotal.com.br/?p=2848769)
- Prática de mercado trabalhista: Anttecipe.com paga "até 80% do valor líquido" a que o reclamante tem direito, exige **sentença favorável em 2ª instância** e réu de médio/grande porte solvente; >1.000 clientes; R$ 30 mi captados em 2021 — [Gazeta SP, 16/01/2023](https://www.gazetasp.com.br/brasil/apos-anos-de-espera-na-justica-trabalhadores-da-baixada-santista/1119706/); pagamento em até 24h após assinatura; espera de até 3 anos após 2ª instância — [Contábeis, 11/04/2025](https://www.contabeis.com.br/artigos/70326/venda-de-processos-trabalhistas-entenda-como-funciona-e-os-riscos/)
- Tributação — cedente: STJ (AgInt no REsp 2.022.457/RJ, 1ª T., j. 14/11/2022) — cessão de precatório com deságio não gera ganho de capital; RFB (SC SRRF03 nº 3.010, 13/03/2025) — exige IR sobre ganho de capital, com custo de aquisição zero para o cedente original — [Tributário nos Bastidores, 03/2025](https://tributarionosbastidores.com.br/2025/03/receita-exige-ir-sobre-ganho-de-capital-na-cessao-de-precatorio-com-desagio/amp/)
- Dano moral aéreo — faixas compiladas 2025/2026: atraso 4–8h R$ 3–8k; >12h R$ 8–15k; cancelamento sem aviso R$ 5–20k; com perda de compromisso R$ 10–30k; STF Tema 1.240 (ARE 766.618, 30/11/2023): limites da Convenção de Montreal não se aplicam a danos morais — [Rosenbaum Advogados, atualizado 12/10/2026](https://www.rosenbaum.adv.br/direitos-do-passageiro-e-indenizacoes) (compilação de escritório, sem decisões citadas por faixa)
- Comissão AirHelp: 35% no Brasil; 35–50% quando há necessidade de ação judicial (UE) — [Euro Dicas, 05/04/2024, atualizado 09/05/2025](https://www.eurodicas.com.br/airhelp/)

### Inferences
- **Parâmetro `p_predatoria`** (probabilidade de exigência de emenda → atraso de 2–4 meses; e de extinção sem mérito): **[PREMISSA]** 5–15% para consignado/energia/aéreo em comarcas com Centro de Inteligência ativo; deve ser escorada em DataJud (movimento de "emenda à inicial" seguido de extinção). Mitigante no pré-ajuizamento: o pipeline próprio já monta o dossiê (procuração específica, comprovante de residência, contrato, extratos, protocolo no consumidor.gov) antes de distribuir.
- **Tributação do comprador PJ** **[PREMISSA — sem fonte específica obtida]**: o ganho (valor recebido − preço pago) é receita tributável no comprador (IRPJ/CSLL ~34% no lucro real + PIS/COFINS); estruturas via FIDC-NP deslocam a tributação para o cotista; o modelo deve carregar um parâmetro `τ` (alíquota efetiva sobre o ganho) com default 34% para PJ operacional e ~0–15% para veículo FIDC, e um parâmetro de IRRF/INSS sobre o crédito trabalhista (retido na fonte no alvará).
- **Impenhorabilidade/natureza alimentar**: não afeta a cessão em si (art. 286 CC; crédito trabalhista cedível segundo o TST), mas afeta a **cobrança contra réu pessoa física** (salário, bem de família) → só comprar créditos contra PJ solvente; `p_cobrança` para réu PF deve ser muito baixo.
- Honorários: a sucumbência pertence ao advogado (art. 85 §14 CPC — [Planalto, CPC](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm) — texto legal, não verificado via fetch) e **não compõe o crédito comprado**; os honorários contratuais (20–30% de praxe **[PREMISSA]**) são destacados do alvará, então o comprador adquire o **líquido**; multa de 10% do art. 523 §1º CPC reverte ao credor (compõe o crédito), os 10% de honorários do mesmo dispositivo vão ao advogado.

### Gaps
- Estatística de incidência de emenda/extinção por litigância abusiva por tribunal **[LACUNA — construir do DataJud]**.
- Tratamento tributário do cessionário PJ e de FIDC-NP de créditos judiciais não confirmado em fonte primária **[LACUNA]**.
- Limites atualizados do depósito recursal trabalhista 2026 (garantia parcial do crédito em fase recursal) não obtidos **[LACUNA]**.

---

## KQ5 — Fórmula concreta, tabela de parâmetros, sensibilidade e exemplos trabalhados

### Takeaway
Preço = valor presente esperado dos fluxos líquidos (árvore por fase) menos custos fixos e de servicing, ajustado pela tributação do ganho e por uma TIR-alvo de 25–40% a.a.; nos exemplos, isso dá ~60–72% da face para consignado R$ 10k em cumprimento no TJPA, **valor negativo (inviável) para falha de energia R$ 5k em 1ª instância com servicing manual** (≈10–15% do pedido com servicing automatizado), ~23–31% da face bruta (35–48% do líquido) para reclamação trabalhista R$ 40k em fase recursal no TRT-8, e ~15–20% do pedido para pré-ajuizamento aéreo R$ 5k (onde o modelo de comissão AirHelp de 35% é superior à compra).

### Cited Findings
- Inputs macro usados: Selic 13,75% a.a. (16/09/2026) — [Atlas Público/BCB](https://atlaspublico.com.br/bcb/noticias/copom-reduz-selic-para-13-75pct-ao-ano-em-decisao-unanime-87748); IPCA 12m 4,58% (set/2026) — [Valor Final](https://valorfinal.com.br/boletim-taxas); durações nacionais JN 2026 — [Projuris](https://www.projuris.com.br/blog/justica-em-numeros-2026/); conciliação trabalhista 37,9% (conhecimento) / 7,9% (execução) — [Projuris](https://www.projuris.com.br/blog/justica-em-numeros-2026/); benchmark de retorno Burford TIR 26% / perda 10,2% — [SEC 8-K](https://www.sec.gov/Archives/edgar/data/1714174/000171417426000006/bur-20260226xex992.htm); preço de mercado trabalhista "até 80% do líquido" após 2ª instância — [Gazeta SP](https://www.gazetasp.com.br/brasil/apos-anos-de-espera-na-justica-trabalhadores-da-baixada-santista/1119706/); comissão AirHelp 35% — [Euro Dicas](https://www.eurodicas.com.br/airhelp/); índice de solução consumidor.gov aéreo 83,47% — [MJ 2025](https://www.gov.br/mj/pt-br/assuntos/seus-direitos/consumidor/defesadoconsumidor/Biblioteca/boletins-1/boletim-consumidor-gov-br-2025-vfinal.pdf)

### Inferences

#### 5.1 Fórmula geral (módulo de pricing)

```
P_max = [ (1 − τ) · Σ_s π_s · Σ_t CF_{s,t} · DF(t_{s,t})  −  C_fix  −  PV(C_serv) ] / (1 − τ · DF̄)

onde:
  s        = cenário terminal da árvore (acordo, pagamento voluntário, penhora, redução, reforma, extinção, insolvência)
  π_s      = probabilidade do cenário = produto das probabilidades condicionais dos nós (p_proc, p_recurso, p_reforma, p_cobrança, p_predatória, p_acordo)
  CF_{s,t} = fluxo líquido ao cessionário na data t: V0 · G(t) · (1 − h_contr) · (1 − d_legais) · q_s  [+ multa 10% art. 523 quando aplicável]
  G(t)     = fator de atualização legal até t (cível: IPCA × (1+ΣTL); trabalhista: trechos ADC 58 / Lei 14.905)
  q_s      = fração do valor mantida no cenário (1,0 mantido; 0,6–0,8 redução; 0 reforma/extinção)
  h_contr  = honorários contratuais destacados do alvará (0 se o comprador já é o patrono/pipeline próprio)
  d_legais = descontos legais na fonte (IRRF/INSS no trabalhista; 0 no dano moral cível)
  DF(t)    = (1 + r)^(−t), r = TIR-alvo nominal
  τ        = alíquota efetiva sobre o ganho (CF − P); DF̄ = fator de desconto médio ponderado dos recebimentos
  C_fix    = diligência + instrumento de cessão + habilitação nos autos
  PV(C_serv) = valor presente do custo mensal de monitoramento/cobrança até o recebimento esperado
Oferta = P_max × (1 − margem de negociação)  [sugerido 10–20%]
```

Métricas de saída: preço/face, preço/líquido esperado, MOIC esperado (= E[CF]/P), TIR esperada, duração esperada, perda esperada (1 − Σπ_s·q_s), P(perda total).

#### 5.2 Tabela de parâmetros (defaults iniciais; todas as linhas sem fonte são **[PREMISSA]** a calibrar por jurimetria própria)

| Parâmetro | Consignado não reconhecido (banco) | Falha de energia (concessionária) | Voo cancelado (cia aérea) | Reclamação trabalhista (empresa média) | Fonte/observação |
|---|---|---|---|---|---|
| p_acordo extrajudicial / em audiência | 10% / 25% | 5% / 25% | 20% / 35% | — / 35% (conhecimento) | consumidor.gov índice de solução ≠ indenização em dinheiro; JT 37,9% (JN 2026) |
| p_procedência (total+parcial) em 1º grau | 60% | 55% | 70% | — (já sentenciado no ex. iii) | **[PREMISSA]** |
| Valor esperado condenado / pedido | 0,6–0,8 (dano moral reduzido) | 0,5–0,7 | 0,6–0,8 | — | faixas aéreo: Rosenbaum 2025/26 |
| p_recurso do réu | 60% | 60% | 50% | RO 90% / RR 35% | **[PREMISSA]** |
| p_reforma (total ou redução) | 25% | 25% | 20% | TRT 30% / TST 10% | âncora histórica CNJ 2009: JT 27%, superiores 22,5% |
| p_predatória (emenda/extinção) | 10% | 15% | 5% | 0 | Tema 1.198 **[PREMISSA]** |
| p_cobrança (réu solvente) | 98% | 97% | 90% (Azul/Gol: RJ/Ch.11 recentes) | 85% | **[PREMISSA]** |
| t sentença 1º grau | 12 m | 12 m | 10 m | 8 m | JN 2026 (1a3m 1º grau; JT 8m) |
| t recurso | 8 m (TR/2º grau) | 8 m | 8 m | TRT 10–12 m; TST 20 m | JN 2026 |
| t cobrança após TJ | 3–9 m | 3–9 m | 4–8 m | 12–18 m (JT execução até sentença 1a6m) | JN 2026 + **[PREMISSA]** |
| g (crescimento nominal) | IPCA + TL ≈ 13,5% a.a. | idem | idem | idem (trechos ADC 58) | KQ3 |
| h_contr | 30% | 30% | 30% (ou 0 se pipeline próprio) | 20–30% | **[PREMISSA]** |
| d_legais | 0 | 0 | 0 | 8–12% (INSS/IRRF) | **[PREMISSA]** |
| r (TIR-alvo) | 25% (transitado) / 35% (em curso) | 35% | 35% | 35% | Burford 26% USD + Selic 13,75% |
| τ | 34% PJ / ~0–15% FIDC | idem | idem | idem | **[PREMISSA]** |
| C_fix manual / automatizado | R$ 600 / R$ 80 | R$ 450 / R$ 50 | R$ 450 / R$ 50 | R$ 1.300 / R$ 300 | **[PREMISSA]** |
| C_serv mensal manual / automatizado | R$ 25 / R$ 3 | R$ 20 / R$ 3 | R$ 20 / R$ 3 | R$ 25 / R$ 5 | **[PREMISSA]** |

#### 5.3 Exemplos trabalhados (r = 35% salvo indicação; τ = 34%)

**(i) Consignado não reconhecido — condenação R$ 10.000 (líquido ao credor, já atualizado) no TJPA, em cumprimento de sentença, réu banco**
Cenários: A) depósito voluntário em 3 m (45%) → 10.330; B) SISBAJUD/alvará em 9 m com multa 10% (45%) → 12.115; C) impugnação parcialmente acolhida, −30%, 18 m (8%) → 8.491; D) perda (2%) → 0.
PV esperado = 0,45·10.330·0,928 + 0,45·12.115·0,798 + 0,08·8.491·0,638 = **R$ 9.098**. Custos: C_fix 600 + PV servicing 250 = 850.
Pré-imposto: P = 8.248 (82% da face). Com τ = 34% e DF̄ ≈ 0,85: **P_max ≈ R$ 7.250 (72,5% da face)**; MOIC esperado 1,49x em ~0,6 ano. Oferta sugerida com margem: **60–65% da face**.
Sensibilidade (PV esperado bruto): r = 25% → 9.494; r = 45% → 8.750; prazos dobrados → 7.753; p_perda 2%→10% → ~8.350.

**(ii) Falha de energia — pedido R$ 5.000, ação em 1ª instância (JEC), réu concessionária**
Cenários: acordo em audiência (25%) R$ 1.800 brutos → 1.260 líquidos (h=30%) em 4 m; extinção/improcedência (43,75%) → 0; procedência (41,25%) com condenação R$ 3.000: sem recurso (40%) → 2.240 líquidos em 1,5 a; recurso mantido (45%) → 2.450 em 2,3 a; recurso reformado (15%) → 0.
PV esperado = 285 + 236 + 228 = **R$ 749**.
Custos manuais: 150 + 300 + PV(24 × 20) ≈ 830 → **preço negativo: deal inviável com operação manual**. Custos automatizados (≈130): P pré-imposto 619 → **P_max ≈ R$ 480 (≈10% do pedido; ≈16% da condenação esperada)**. Conclusão: só faz sentido em carteira com servicing automatizado e aquisição a preço simbólico, ou como financiamento a êxito.

**(iii) Reclamação trabalhista — sentença líquida R$ 40.000 brutos, RO do réu pendente no TRT-8, réu empresa média solvente**
Líquido ao trabalhador ≈ 40k × (1 − 0,30 h_contr) × (1 − 0,08 d_legais) ≈ **R$ 26.000**.
Cenários: acordo no TRT (15%) 75% do líquido em 0,8 a → 19.500; TRT mantém (59,5%): sem RR/RR não admitido (65%) → 33.200 em 2,0 a; com RR mantido (31,5%) → 40.900 em 3,7 a; RR provido (3,5%) → 0; TRT reduz 20% (17%) → 27.600 em 2,3 a; reforma total (8,5%) → 0.
PV esperado = 2.301 + 7.046 + 2.526 + 2.353 = **R$ 14.226** (55% do líquido; 36% da face bruta). Custos: 500 + 800 + PV(30 × 25) ≈ 1.850.
Pré-imposto: P = 12.376 (48% do líquido / 31% da face). Com τ = 34%, DF̄ ≈ 0,5: **P_max ≈ R$ 9.100 (35% do líquido / 23% da face)**.
Coerência com o mercado: Anttecipe paga até 80% do líquido, mas **só após 2ª instância favorável**; em fase recursal, 35–48% do líquido é consistente com o risco adicional de reforma (30%) e de RR.

**(iv) Pré-ajuizamento — cancelamento de voo, pedido R$ 5.000, réu cia aérea**
Cenários: acordo extrajudicial (consumidor.gov) em dinheiro (20%) R$ 1.200 em 1 m; ajuizamento (80%): acordo em audiência (35%) R$ 2.000 em 5 m; procedência (70% de 65%) com condenação R$ 3.500: sem recurso (50%) → 3.700 em 1,2 a; recurso mantido (40%) → 4.000 em 1,9 a; reformado (10%) → 0; improcedência (30%) → 0.
PV esperado bruto (pipeline próprio, h_contr = 0) = 234 + 493 + 469 + 329 = **R$ 1.525**. Custos: patrocínio automatizado + audiência R$ 400 + preparo esperado 30 + servicing 90 = 520.
Pré-imposto: P = 1.005 (20% do pedido); **P_max ≈ R$ 750 (15% do pedido)** após τ.
Comparação: modelo AirHelp (comissão 35% sobre a indenização obtida, sem desembolso) gera receita esperada ≈ 0,35 × E[indenização] ≈ 0,35 × ~3.100 ≈ R$ 1.085 com risco de capital próximo de zero (apenas custo do patrocínio) → **no pré-ajuizamento, prefira contrato de êxito/cessão parcial a compra à vista**; a compra só se justifica quando o lead exige liquidez imediata e aceita ≤15–20% do pedido. Atenção ao risco de contraparte (recuperação judicial/Chapter 11 recentes no setor aéreo **[PREMISSA quanto ao status atual]**).

#### 5.4 Tabela de sensibilidade (direção e magnitude aproximada, derivadas dos exemplos)

| Choque | Efeito no P_max |
|---|---|
| TIR-alvo 35% → 25% | +4% a +15% (maior nos créditos longos; ex. iii +~20%) |
| TIR-alvo 35% → 45% | −4% a −12% |
| Duração ×2 | −15% (ex. i) a −35% (ex. iii) — o crescimento ≈ Selic amortece, mas o spread r − g pesa |
| p_reforma +10 p.p. | −8% a −14% |
| p_cobrança −10 p.p. | −10% linear |
| τ 34% → 0% (FIDC) | +10% a +20% |
| Servicing manual → automatizado | decisivo abaixo de R$ 8k de face (ex. ii passa de negativo a positivo) |

#### 5.5 Ticket mínimo (economia de servicing)
Regra prática: `C_fix + PV(C_serv) ≤ 10–15% do PV esperado`. Com custos manuais (R$ 1.000–1.500 ao longo de 2 anos) → PV esperado mínimo R$ 10–15k → **face mínima ≈ R$ 20–30k para créditos em 1ª instância** e ≈ R$ 12–15k para créditos transitados. Com pipeline automatizado (R$ 150–250 por caso) → PV esperado mínimo R$ 2–2,5k → **face mínima ≈ R$ 5–8k (1ª instância) e ≈ R$ 3k (transitado)**. Abaixo disso, operar apenas em modelo de êxito (comissão) ou em lotes do mesmo réu/tese com custo marginal próximo de zero.

### Gaps
- Todas as probabilidades condicionais e prazos por tese × comarca são premissas; a precisão do preço depende da tabela jurimétrica própria (KQ7).
- Honorários contratuais de praxe, descontos legais trabalhistas e custos operacionais são estimativas sem fonte pública.

---

## KQ6 — Benchmarks de deságio praticados (precatórios, RPV, trabalhista, aéreo)

### Takeaway
Fontes de 2025–2026 indicam deságios de **30–50% (federais), 40–70% (estaduais), até 70% (municipais)** no mercado secundário de precatórios, 50% citado por comprador no RS (mar/2026), acordos oficiais com o Estado de SP entre 20% e 40%; no trabalhista os compradores pagam até 80% do líquido após 2ª instância (deságio ≥ 20%) e fundos cobram 25% a >50%; no aéreo, a AirHelp cobra 35% (35–50% com judicialização).

### Cited Findings
- Deságio por esfera (levantamento do jornal Extra com empresas compradoras): **federal 30–50%; estadual 40–70%; municipal até 70%** — [Paraíba Business, 25/05/2025](https://paraibabusiness.com.br/precatorios-vale-ou-nao-a-pena-vende-los/)
- Banco Fiscal (Pedro Schuch): deságio "praticado a 50%" no RS; expectativa de aquecimento com o Acordo Gaúcho (precatórios abatem até 75% de multas e 60% de dívidas estaduais) — [Jornal do Comércio, 23/03/2026](https://www.jornaldocomercio.com/politica/2026/03/1241949-mercado-privado-de-precatorios-deve-ter-aquecimento.html)
- Expectativa pós-PEC 66/EC 136: precatórios antes negociados a 30% de desconto "possam vir a ser vendidos com até 70% de abatimento" conforme perfil do devedor — [Monitor Mercantil, 22/07/2025](https://monitormercantil.com.br/impactos-da-pec-66-23-no-mercado-de-precatorios/)
- Acordos diretos com o Estado de SP (Decreto 69.325, 22/01/2025): deságio escalonado por ano de vencimento — até 2015: 20%; 2016–17: 25%; 2018–19: 30%; 2020–21: 35%; 2022+: 40% (teto constitucional); idosos/doentes graves: 20% — [Monitor Mercantil, 24/02/2025](https://monitormercantil.com.br/menos-desagio-mais-justica-novo-capitulo-dos-precatorios-em-sp/)
- Exemplo didático de deságio 20–40% em acordos/cessões e alerta de que o líquido ainda sofre IR, contribuição previdenciária e honorários — [Jornal do Brás, 03/09/2026](https://jornaldobras.com.br/noticia/138105/receber-antes-compensa)
- Trabalhista: Anttecipe paga até 80% do líquido (2ª instância favorável) — [Gazeta SP, 16/01/2023](https://www.gazetasp.com.br/brasil/apos-anos-de-espera-na-justica-trabalhadores-da-baixada-santista/1119706/); fundos cobram ≥25%, às vezes >50% — [NSC Total/Valor, 20/08/2021](https://www.nsctotal.com.br/?p=2848769)
- Aéreo: AirHelp 35% (Brasil); 35–50% com assistência jurídica — [Euro Dicas](https://www.eurodicas.com.br/airhelp/)
- RPV: no Pará, PGE afirmava pagamento em 60 dias (2019) — [O Liberal, 15/09/2019](https://www.oliberal.com/economia/precatorios-n-o-s-o-um-problema-grave-1.193060)

### Inferences
- Tradução dos deságios em TIR implícita (sem risco de crédito, com crescimento IPCA + 2%): precatório estadual pago em 2 anos comprado a 50% da face → MOIC ≈ 2,0 × 1,13 → TIR ≈ 50% a.a.; a 70% da face (deságio 30%) → TIR ≈ 27% a.a. Isso sugere que o mercado precifica precatórios subnacionais a TIR-alvo de 25–50% a.a., consistente com o `r` proposto em KQ5.
- RPV (≤ 60 dias, ente adimplente) deve ser precificada quase como título: deságio de 5–10% cobre r de 25–35% a.a. para 2–3 meses + custo de habilitação **[PREMISSA]**.
- Para o crédito trabalhista, a referência "até 80% do líquido após 2ª instância" é o teto competitivo; o módulo deve exibir o preço do exemplo (iii) ao lado desse teto e do estágio processual para justificar a diferença.

### Gaps
- Não há série pública de preços de cessão por tribunal/ente; os números acima são declarações de compradores e levantamentos jornalísticos, não transações observadas **[LACUNA]**.
- Deságio praticado em créditos cíveis de consumo (bancos/concessionárias) transitados em julgado não encontrado em fonte pública **[LACUNA]** — o exemplo (i) (60–72% da face) é derivado do modelo, não de mercado.

---

## KQ7 — Pipeline de dados necessário (jurimetria, monitoramento, cobrança) e o que a esteira de defesa "tipo Enter" já produz

### Takeaway
O módulo precisa de quatro tabelas (resultado, valor, duração, reforma) por tese × comarca × réu, alimentadas pelo DataJud (movimentos/assuntos/classe/órgão, sem partes nem valores), pelo DJEN/Comunica PJe (publicações, com valores e nomes nos textos) e por eventos próprios de cobrança; a esteira própria planejada para as quatro tipologias (consignado/RMC, energia, voo, trabalhista) já produz a taxonomia de teses, a extração de pedidos/condenações das publicações e o monitoramento de prazos — faltam o log de eventos de cobrança e a calibração de probabilidades.

### Cited Findings
- DataJud API pública: autenticação por chave pública do CNJ no header `Authorization: APIKey <chave>`; rotas por alias de tribunal (índice por corte); campos: número CNJ, tribunal, grau, classe, assuntos (TPU), órgão julgador, data de ajuizamento, movimentos (código, nome, data, complementos tabelados), sigilo, sistema de origem, timestamps; **não há nomes de partes, CPF/CNPJ, textos de decisão, valores nem documentos**; sem webhooks; latência não especificada — [Judit, 04/04/2026 (atual. 15/09/2026)](https://judit.io/blog/legislacao-atualizacoes-regulatorias/datajud-cnj-api-publica-x-privada-comparacao/); cliente Python `pydatajud` resolve o endpoint pelos campos J/TR do número CNJ e agrega movimentos — [PyPI pydatajud](https://pypi.org/project/pydatajud/0.1.0/)
- Resultado por fase trabalhista observável no JN 2026 (conciliação 37,9% conhecimento / 7,9% execução; execução até sentença 1a6m) — [Projuris](https://www.projuris.com.br/blog/justica-em-numeros-2026/)
- Esteira própria (decisões de 19/10/2026): stack Python por fases com gatilhos, piloto com 4 tipologias — consignado/RMC, falha de energia, cancelamento/atraso de voo e reclamações trabalhistas — [memória do usuário: enter-ia-juridica-estudo]

### Inferences
- **Tabelas jurimétricas mínimas** (chave: tese × tribunal × comarca/vara × réu × ano de ajuizamento):
  1. `outcome`: P(acordo), P(procedência total/parcial/improcedência), P(extinção sem mérito — incl. emenda Tema 1.198), de movimentos TPU de sentença (códigos de procedência/improcedência/procedência em parte, extinção sem resolução, homologação de transação — **validar códigos na TPU/SGT do CNJ**).
  2. `award`: distribuição (mediana, p25, p75) do valor da condenação por tese; **não vem do DataJud** — extrair por NLP das publicações do DJEN (dispositivo da sentença) e dos próprios autos nos casos patrocinados.
  3. `duration`: tempos entre marcos (ajuizamento → citação → audiência → sentença → acórdão → trânsito → alvará), estimados por **Kaplan–Meier/Cox** (processos em curso são censurados à direita; usar a média de baixados do CNJ só como prior).
  4. `reversal`: P(provimento total/parcial) do recurso do réu e do autor, por órgão (Turmas Recursais TJPA, câmaras TJPA, Turmas TRT-8), a partir dos movimentos de julgamento de recurso.
  5. `collection`: eventos próprios — depósito voluntário (dias após intimação do art. 523), SISBAJUD positivo/negativo, impugnação, alvará, valor efetivamente levantado; permite calibrar `p_cobrança` e `t cobrança` por réu (banco X paga em 20 dias; concessionária Y só após penhora).
- **Monitoramento**: DJEN/Comunica PJe por OAB e por nome da parte para cada crédito comprado (dispara recálculo de preço/valor de carteira a cada marco); DataJud como fallback diário para movimentos; o Domicílio Judicial Eletrônico não se aplica ao cessionário (é do réu).
- **O que a esteira de defesa "tipo Enter" já entrega para o pricing**: (a) taxonomia de teses e classificação automática da inicial/sentença; (b) extração estruturada de pedidos, valores pedidos e condenados; (c) detecção de sinais de litigância predatória (mesmo advogado, petições padronizadas, ausência de documentos) — que vira `p_predatória`; (d) monitoramento de publicações e prazos. **O que falta**: log de cobrança (a defesa não cobra), estimação de duração por sobrevivência, e a visão do lado do autor (taxa de acordo por réu, comportamento de pagamento), além de uma base de réus (solvência: RJ, protestos, CNDs).
- Arquitetura sugerida do módulo: `pricing_engine(claim) → árvore parametrizada por lookup nas tabelas 1–5 (com fallback hierárquico comarca → tribunal → nacional e prior bayesiano quando n < 30) → Monte Carlo (10k simulações: duração lognormal por marco, resultado multinomial, correlação por réu/tese) → P_max, MOIC, TIR, duração, perda esperada, intervalo p10–p90`.

### Gaps
- Documentação oficial do DataJud (datajud-wiki.cnj.jus.br/api-publica) e da Comunica API do DJEN (comunicaapi.pje.jus.br) não foi acessível por fetch nesta pesquisa; endpoint exato, limites de paginação (search_after/10.000 hits) e filtros (OAB, nome, tribunal, datas) precisam ser confirmados na implementação **[LACUNA técnica]**.
- Códigos TPU exatos dos movimentos de resultado/recurso/trânsito devem ser extraídos do SGT do CNJ **[LACUNA técnica]**.
- Dados de solvência de réus (RJ, falência, protestos) exigem fonte paga (Serasa/Boa Vista) ou raspagem de editais — fora do escopo desta nota.
