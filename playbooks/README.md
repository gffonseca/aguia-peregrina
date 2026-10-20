# Playbooks de teses (M0)

> **Tese antes da máquina.** A plataforma não gera uma linha de minuta para uma tipologia que não tenha um playbook **aprovado por advogado-dono** (nome + OAB + timestamp). O playbook é a estratégia; a IA só executa dentro dele. Isso é o que separa a Águia Peregrina do que a OAB-SP ataca na ACP contra a Enter: a estratégia e a peça pertencem a um advogado inscrito, identificável, com trilha.

## O que há nesta pasta

| Arquivo | Para quê |
|---|---|
| `TEMPLATE.playbook.yaml` | Modelo comentado. Copie e preencha. Passa na validação como está. |
| `playbook.schema.json` | JSON Schema (draft 2020-12) gerado do pydantic. Use no editor (VS Code: `yaml.schemas`) para autocompletar e apontar erro ao digitar. |
| `consignado-rmc-tjpa.playbook.yaml` | Primeiro playbook: consignado/RMC não reconhecido, defesa de instituição financeira regional, TJPA. **Em revisão, pronto para aprovação** — sessão 1 (19/10/2026) e sessão 2 (20/10/2026) aplicadas; todas as referências legais e assuntos CNJ `conferido: true` com fonte na `nota` (levantamento de 19/10/2026: STJ, Planalto, CNJ, portal do TJPA). Pendência monitorada: Tema 929/STJ (T09). Sem cliente-piloto: piloto interno com casos encerrados da FBS primeiro; prospecção de Banpará/Basa/financeira regional em paralelo. |
| `consignado-rmc-tjpa.playbook.md` | O mesmo conteúdo em prosa e tabelas para quem não edita YAML. **Derivado**: o YAML é a fonte da verdade. |
| `energia-falha-fornecimento-tjpa.playbook.yaml` / `.md` | Energia elétrica: interrupção/oscilação, danos em equipamentos, TOI, religação e negativação — defesa de distribuidora (Equatorial Pará / Norte Energia), TJPA. **Rascunho** — tudo `[A CONFERIR pelo advogado-dono]`. |
| `aereo-cancelamento-atraso-tjpa.playbook.yaml` / `.md` | Transporte aéreo: cancelamento, atraso, overbooking e bagagem — defesa de companhia aérea (Azul/LATAM/Gol no PA), TJPA. **Rascunho**; só defesa (o lado do autor é do spinoff de créditos). |
| `trabalhista-reclamatoria-trt8.playbook.yaml` / `.md` | Reclamatória trabalhista típica — defesa do empregador (terceirizadas, mineração/serviços, call center, varejo), TRT-8. **Rascunho**; teses por pedido, briefing de audiência e modelagem de acordo por pedido. |
| `execucao-credito-basa-tjpa-tjam.playbook.yaml` / `.md` | Execução / recuperação de crédito bancário em massa — **polo ativo** (credor = Banco da Amazônia), TJPA + TJAM. Primeiro playbook com `metadata.polo: ativo`: as "teses" são módulos de decisão (triagem de recuperabilidade, impulso por fase, garantia rural, IDPJ/sucessão, cumprimento, impugnação a embargos, exceção de pré-executividade, art. 921/intercorrente, acordo, precatórias, monitória). **Em revisão** — sessão 1 (20/10/2026) aplicada: carteira morta por três critérios objetivos com decisão de sócio caso a caso, pedido cumulado Sisbajud+Renajud+Infojud com fallback por juízo, planilha sempre exigida em excesso de execução, acordo proativo em score médio, gatilho de 90 dias, intercorrente < 12 meses com diligência útil obrigatória, amostra top-200 por valor com bens. Referências legais ainda todas `conferido: false`. Baseado na radiografia da carteira BASA (16.656 processos). |

Código: `app/modules/m00_playbook/schema.py` (modelo pydantic, `validate_playbook(path)`, `to_thesis_payloads()`), testes em `tests/test_playbook_schema.py`.

## Fluxo para o advogado-dono

### 1. Criar

```bash
cp playbooks/TEMPLATE.playbook.yaml playbooks/<tipologia>-<tribunal>.playbook.yaml
```

Preencha `metadata` (você é o `autor_oab`), depois os blocos na ordem em que a esteira os consome.

**Polo.** `metadata.polo` diz de que lado o cliente está: `passivo` (réu/executado — padrão, todos os playbooks de defesa) ou `ativo` (autor/exequente — ex.: execução de crédito bancário, credor = banco). `lado` continua existindo (`defesa` | `autor`) e descreve a peça; `polo` descreve a posição processual e é o que M1/M5/M6 usam para saber se o "autor" dos autos é o cliente ou o adversário. Em polo ativo a árvore de `teses` é lida como **módulos de decisão** (o que fazer com o processo nesta fase), `sinais_acordo.faixas_valor` passa a significar faixa de dívida e o `tipo_peca_padrao` costuma ser uma peça curta de impulso — ver `execucao-credito-basa-tjpa-tjam.playbook.md`, seção 0.

1. **Gatilhos de classificação** — como M1/M9 reconhecem a tipologia (assuntos CNJ, palavras-chave, exclusões).
2. **Campos obrigatórios do dossiê** — o vocabulário que M3/M5 precisam extrair ou receber do cliente. Toda condição do playbook só pode citar campos daqui; o validador recusa campo desconhecido.
3. **Árvore de teses** — `T01`, `T02`, subteses `T06.1`. Cada tese tem: condições de aplicação (AND sobre campos do dossiê), provas necessárias, provas que afastam, fundamentação (dispositivos e precedentes), pedidos e subsidiários, risco se mal aplicada.
4. **Exceções** — quando a esteira deve parar (`nao_gerar_minuta`, `escalar_socio`, `sinalizar_acordo`, `pedir_subsidio`, `alertar_revisor`).
5. **Sinais de acordo** — quando acordar, quando não, faixas por grupo de comarcas, alçadas. A plataforma sinaliza; quem decide é o advogado/cliente.
6. **Antifraude** — checagens específicas da tipologia (códigos = `fraud_checks.check_code`). Flags com evidência; nunca rótulo.
7. **Modelo de peça** — seções, ordem, quais teses entram em cada seção, onde a citação de página é obrigatória.
8. **Critérios de revisão** — tempo mínimo, papel mínimo, quando exigir segunda revisão, checklist do revisor, motivos de recusa.
9. **Métricas** — o que M10/M11 medem para esta tipologia.

### 2. Marcar o que falta conferir

Toda citação legal nasce com `conferido: false` e `nota: "[A CONFERIR pelo advogado-dono]"`. Números (prazos, faixas de valor, N de ações) nascem com a nota no campo ao lado. Só troque para `conferido: true` depois de abrir a fonte (texto vigente, número do tema, ementa, modulação, jurisprudência atual do tribunal). O M6 não cita referência não conferida; o M7 recusa peça com placeholder.

### 3. Validar

```bash
python -m app.modules.m00_playbook.schema playbooks/<arquivo>.playbook.yaml
pytest tests/test_playbook_schema.py
```

O validador checa estrutura (JSON Schema), ids únicos, referências cruzadas (tese-mãe existe, seções apontam teses existentes, condições só usam campos declarados) e a regra de aprovação abaixo.

### 4. Versionar

- `metadata.versao` é um inteiro; cada mudança de conteúdo após aprovação é uma **nova versão** (`versao: 2`, `supera_versao: 1`), nunca edição em cima da aprovada.
- A versão anterior recebe `status: superado`.
- O arquivo é versionado em git; o histórico de quem mudou o quê fica no commit **e** no banco (`thesis_versions.author_oab`).

### 5. Aprovar

Mude `status` para `em_revisao` e peça a um sócio (pode ser você, se for o sócio responsável) que:

1. confira cada `conferido: false` e troque para `true` ou remova a referência;
2. calibre faixas de acordo e parâmetros antifraude com dados da carteira;
3. preencha `aprovado_por_nome`, `aprovado_por_oab`, `aprovado_em` (ISO 8601 com fuso) e `status: aprovado`.

O validador **recusa** `status: aprovado` sem OAB + timestamp, ou com qualquer referência legal/assunto CNJ ainda não conferido. Essa é a invariante de M0; a mesma regra vive no banco em `approve_version()` (`approved_by_oab`, `approved_at`).

## Como o playbook vira dado no banco (M0)

`to_thesis_payloads(playbook)` gera um item por tese com `typology`, `code`, `title`, `parent_code`, `body_markdown`, `conditions` e `author_oab`. O serviço de M0 (`app/modules/m00_playbook/service.py`) grava:

| Playbook | Tabela / coluna |
|---|---|
| `metadata.tipologia` | `theses.typology`, `cases.typology` |
| `teses[].id` | `theses.code` |
| `teses[].nome` | `theses.title` |
| `teses[].pai` | `theses.parent_id` |
| resumo + argumentos + fundamentação + pedidos | `thesis_versions.body_markdown` |
| condições, provas, pedidos subsidiários, `playbook_id`/`versao` | `thesis_versions.conditions` (JSON) |
| `metadata.autor_oab` | `thesis_versions.author_oab` |
| `metadata.aprovado_por_oab`, `aprovado_em` | `thesis_versions.approved_by_oab`, `approved_at` (via `approve_version`) |

## Como cada módulo consome o playbook

| Módulo | Bloco do playbook | Uso |
|---|---|---|
| **M1/M9 Intake e monitoramento** | `gatilhos_classificacao` | Classificar a distribuição/publicação na tipologia; abaixo de `confianca_minima` vai para triagem humana. |
| **M3 Subsídios** | `campos_dossie_obrigatorios` com `origem: subsidio` e `teses[].provas_necessarias` | Checklist determinístico do que pedir ao cliente (contrato, TED, logs…) antes de qualquer redação; `bloqueia_minuta_se_ausente` trava a esteira. |
| **M4 Antifraude** | `antifraude.checagens` | Quais checagens rodar e com que parâmetros; `implementada_em_m4: false` é backlog de engenharia. Saída: flags com evidência. |
| **M5 Dossiê** | `campos_dossie_obrigatorios` | Schema de extração estruturada; o dossiê só está completo quando os campos `obrigatorio: true` existem. Avalia `excecoes` e `sinais_acordo` sobre o dossiê. |
| **M6 Minuta** | `teses` (condições → teses aplicáveis), `modelo_peca` (seções/ordem), `regra_citacao` | Seleciona as teses cujas `condicoes_aplicacao` são verdadeiras e cujas `provas_necessarias` obrigatórias estão anexas; desativa a tese se uma `prova_que_afasta` apareceu; monta a peça na ordem das seções; cada fato cita `document_page_id`. Grava `thesis_version_ids` no draft. |
| **M7 Revisão** | `criterios_revisao` | `tempo_minimo_segundos` → `REVIEW_MIN_SECONDS_<tipo>`; `checklist` aparece na tela do revisor (itens `bloqueante` impedem aprovar); `exige_segunda_revisao_se` roteia para sócio; `motivos_recusa_padrao` alimentam `reject()`. |
| **M10/M11 Write-back e qualidade** | `metricas` | Definem os painéis por tese × comarca × revisor e a amostra de ground truth; `outcomes.thesis_version_ids` liga resultado à versão da tese, fechando o loop que corrige o playbook. |

## Regras que não mudam

1. Sem playbook aprovado, sem minuta.
2. Uma referência legal só entra na peça se estiver `conferido: true` no playbook.
3. Nenhuma checagem antifraude rotula pessoa; só advogado com OAB confirma um flag (`human_decide`).
4. Sinal de acordo é sinal; a decisão é humana e registrada — a FBS recomenda (valor + faixa), o jurídico do cliente aprova (`sinais_acordo.fluxo_aprovacao`).
5. Versão aprovada não se edita; cria-se a próxima.
6. Comunicação externa de padrão (Cijepa/NUMOPEDE, OAB) só com dupla autorização por escrito (sócio FBS + jurídico do cliente), registrada pela plataforma (`criterios_revisao.autorizacao_dupla`, `teses[].providencias_escalonadas`).
