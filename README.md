# Águia Peregrina

Esteira de IA para **contencioso de massa (defesa)** e **compra de créditos judiciais** — plataforma unificada multi-tenant.

Dois lados, um motor:

| Tenant `law_firm` (FBS) | Tenant `credit_buyer` (Compradora) |
|---|---|
| Recebe publicações, lê autos, consolida dossiê, gera minuta como sugestão, revisão por advogado com OAB, protocolo humano, write-back no ERP do cliente | Descobre créditos candidatos, faz due diligence, **precifica** (P_max/oferta), contrata, cobra, calibra probabilidades, reporta carteira |
| Decide **acordar × defender** | Decide **comprar × passar** e a que preço |

A separação entre os dois tenants é uma **muralha de dados** (RLS no Postgres + filtro na aplicação + lista de exclusão), não uma convenção.

Os relatórios que originaram a especificação estão em [`docs/`](docs/): *Engenharia reversa da Enter* (§8, módulos M0–M11), *Compra de créditos judiciais no Brasil* (§5 e §7) e a nota técnica *modelo_de_preco.md*. As decisões de arquitetura estão em [`docs/DECISIONS.md`](docs/DECISIONS.md).

---

## Arquitetura

```
FastAPI (web)  ──►  Postgres 16 + pgvector (RLS por tenant)
   │                Redis
   │                Hatchet (workflows duráveis) ── fallback in-process
   │
   ├── app/core/        config, sessão, tenancy, segurança (MFA), auditoria
   ├── app/models/      33 tabelas (defesa, crédito, jurimetria), todas com tenant_id
   ├── app/api/         routers por módulo
   ├── app/modules/     regras de negócio: m00…m11 (defesa) + credit/ (compra)
   ├── app/llm/         gateway LiteLLM; log de toda chamada em llm_calls
   ├── app/workflows/   engine adapter + jobs
   ├── app/integrations publications (Comunica PJe, Solucionare), ERP, DataJud, Legal One
   ├── app/evals/       harness de ground truth
   └── alembic/         migração inicial: schema + RLS + audit_log append-only
```

Stack fixada: Python 3.12 · FastAPI · SQLAlchemy 2 + Alembic · Postgres (pgvector) · Redis · Hatchet · LiteLLM · pydantic-settings · Railway.

## Módulos

### Defesa (M0–M11)

| Módulo | Pacote | Tabelas | Função |
|---|---|---|---|
| M0 Playbook | `modules/m00_playbook` | `theses`, `thesis_versions` | Árvore de teses por tipologia, versionada e **aprovada por sócio (OAB)**; arquivos `playbooks/*.playbook.yaml` validados por `schema.py` (ver [`playbooks/README.md`](playbooks/README.md)) |
| M1 Intake | `modules/m01_intake` | `publications` | Captura de distribuições/publicações via provedor, CSV do ERP ou sync do Legal One |
| M2 Autos | `modules/m02_autos` | `documents`, `document_pages` | Upload, OCR por visão LLM, split e classificação por página |
| M3 Subsídios | `modules/m03_subsidios` | — | Vínculo processo ↔ registro interno; checklist determinístico de faltantes |
| M4 Antifraude | `modules/m04_antifraude` | `fraud_checks` | Checagens determinísticas → flags com evidência; **nunca rótulo sem humano** |
| M5 Dossiê | `modules/m05_dossie` | `dossiers`, `extractions` | Documento consolidado (fatos, timeline, provas com score, exposição) |
| M6 Minuta | `modules/m06_minuta` | `drafts`, `draft_citations` | Peça como **sugestão**, cada citação aponta para `document_page_id` |
| M7 Revisão | `modules/m07_revisao` | `reviews` | Fila por advogado, tempo mínimo, aprovação com OAB, recusa com motivo, **export bloqueado** |
| M8 Protocolo | `modules/m08_protocolo` | `filings` | Humano protocola; recibo; sem MNI |
| M9 Monitoramento | `modules/m09_monitoramento` | `publications` | Classifica/resume publicação; alerta de liminar e prazo |
| M10 Write-back | `modules/m10_writeback` | `outcomes`, `erp_writebacks` | Resultado/motivo/fase para o ERP do cliente |
| M11 Qualidade | `modules/m11_qualidade` + `evals/` | `gt_tasks` | Ground truth: modelo × revisor × sênior |
| Transversal | `core/` | `tenants`, `users`, `audit_log`, `llm_calls` | MFA, tenant_id em tudo, logs de LLM |

### Compra de créditos (N1–N6)

| Módulo | Arquivo | Tabelas |
|---|---|---|
| N1 Originação / CRM de cedentes | `credit/origination.py` | `cedentes` (LGPD, opt-out, exclusão) |
| N2 **Pricing engine** | `credit/pricing_engine.py`, `credit/examples.py` | `pricing_runs`, `credit_assets` |
| N3 Contrato e assinatura | `credit/contracts.py` | `contracts` |
| N4 Cobrança | `credit/collection.py` | `collection_events` |
| N5 Calibração | `credit/calibration.py` | (Brier; KM/Cox a seguir) |
| N6 Carteira | `credit/portfolio.py` | `portfolios` |
| Jurimetria | `models/jurimetria.py` | `jm_outcome`, `jm_award`, `jm_duration`, `jm_reversal`, `jm_collection` |

### Fórmula de precificação (N2)

```
P_max = [ (1 − τ) · Σ_s π_s · CF_s · DF(t_s) − C_fix − PV(C_serv) ] / (1 − τ · DF̄)
DF(t) = (1 + r)^(−t)      Oferta = P_max × (1 − margem), margem 10–20 %
```

`POST /pricing/run` recebe cenários terminais (`probability`, `cash_flow`, `t_years`), `r`, `τ`, custos e devolve `p_max`, oferta, MOIC, duração, P(perda total), `params_hash` e grava `pricing_runs`. `GET /pricing/examples/{nome}` roda os quatro exemplos da nota técnica (r = 35 % a.a., τ = 34 %):

| Exemplo | P_max | Referência |
|---|---|---|
| (i) consignado R$ 10 k em execução | ≈ R$ 7.250 | 72,5 % da face |
| (ii) energia R$ 5 k 1ª instância (servicing automatizado) | ≈ R$ 480 | 10 % do pedido; manual → inviável |
| (iii) trabalhista R$ 40 k, RO pendente | ≈ R$ 9.100 | 35 % do líquido |
| (iv) voo R$ 5 k pré-ajuizamento | ≈ R$ 650–750 | ≈ 15 % do pedido |

## Princípios de trilha de auditoria (OAB)

Estes princípios são **invariantes do código**, verificados em `tests/test_review_and_api.py`:

1. **Advogado identificado por peça.** Toda versão de tese, revisão e protocolo registra a OAB de quem autorou/aprovou. Rotas de aprovação exigem role `lawyer`/`partner`, OAB e MFA (`require_lawyer`).
2. **Bloqueio de exportação sem aprovação.** `assert_exportable()` guarda toda saída (Markdown/DOCX/protocolo). Sem `reviews.approved_at` a rota responde **423 Locked**.
3. **Tempo mínimo de revisão.** `approve()` recusa se o revisor ficou menos que `REVIEW_MIN_SECONDS_<tipo>` com a peça aberta (default 10 min; contestação 15 min).
4. **Direito de recusa.** `reject()` exige motivo e registra `rejected_at`; a minuta volta para regeneração.
5. **Nenhum rótulo "fraudador" sem aprovação humana.** O antifraude produz apenas flags com evidência. Só `human_decide(..., oab=...)` por advogado transforma um flag em decisão, e isso passa pelo `audit_log`.
6. **`audit_log` é append-only** (grant sem UPDATE/DELETE + trigger). **`llm_calls` nunca guarda o prompt em claro**, só hash e versão.

## Rodando localmente

Pré-requisitos: Python 3.12+, Docker.

```bash
cp .env.example .env
docker compose up -d                 # postgres (pgvector) + redis
pip install -e ".[all]"              # ou: uv pip install -e ".[all]"
alembic upgrade head                 # cria schema + RLS
make run                             # http://localhost:8000/docs
```

Todas as rotas (exceto `/health`, `/auth/*` e `/ops/bootstrap`) exigem `X-Tenant-ID: <uuid>` e `Authorization: Bearer <token>`. No MVP o login é um stub (`POST /auth/login` → `POST /auth/mfa` com código `000000` em dev).

Para o gateway LiteLLM como proxy separado: `docker compose --profile gateway up -d` e defina `LITELLM_PROXY_URL=http://localhost:4000`.

Sem Hatchet (`WORKFLOW_ENGINE=in_process`) os jobs rodam síncronos no processo web — bom para desenvolvimento. Com `WORKFLOW_ENGINE=hatchet` e `HATCHET_CLIENT_TOKEN`, suba `make worker`.

### Testes e qualidade

```bash
make check      # ruff + mypy + pytest
pytest          # usa SQLite em memória; não precisa de Postgres
```

O RLS do Postgres só é exercitado em banco real; `tests/test_tenant_isolation.py` cobre a camada da aplicação e verifica que a migração aplica a policy em **toda** tabela com `tenant_id`.

## Integração Legal One

Conector **somente leitura** do Legal One (Thomson Reuters), ERP jurídico da FBS, em `app/integrations/legalone/`. Traz processos, partes, contatos, andamentos e tarefas para a plataforma; o M1 classifica a tipologia e a esteira segue a partir daí.

### Variáveis

| Variável | Uso |
|---|---|
| `LEGALONE_CLIENT_ID` / `LEGALONE_CLIENT_SECRET` | credenciais OAuth `client_credentials` (HTTP Basic no `GET {LEGALONE_OAUTH}?grant_type=client_credentials`). Defina nos serviços `web` **e** `worker`; nunca no repositório |
| `LEGALONE_BASE` | `https://api.thomsonreuters.com/legalone/v1/api/rest` (default) |
| `LEGALONE_OAUTH` | `https://api.thomsonreuters.com/legalone/oauth` (default) |
| `OPS_KEY` | protege `GET /integrations/legalone/probe` e `POST /integrations/legalone/sync` (header `X-Ops-Key`, mesma regra de `/health/llm/ping`: sem chave → 404) |

O token é cacheado por `expires_in − 120 s`; em `401` o cache é descartado e a chamada repetida uma vez; falhas nunca são cacheadas. `5xx`/`429`/rede → backoff exponencial e, esgotadas as tentativas, `LegalOneUnavailable`.

### Limites da API (verificados no tenant da FBS em 2026-10-19)

- OData **somente leitura**. `$top` máximo **30** (HTTP 400 acima); paginação por `$skip`; `$count` não suportado.
- `$filter`, `$orderby` e `$expand=participants` funcionam em `lawsuits`; `$expand=updates` **não**.
- Endpoints de lookup (`natures`, `actiontypes`, `courts`…) respondem **404**: guardamos os ids (`natureId`, `phaseId`, `courtId`…) em `cases.meta.legalone` e decodificamos tribunal/segmento/foro do **número CNJ** (`app/core/cnj.py`: `NNNNNNN-DD.AAAA.J.TR.OOOO`, J = 8 estadual / 5 trabalhista / 4 federal, TR = tribunal, OOOO = foro; valida o dígito verificador mod 97).
- A relação `updates`/`tasks` → `lawsuits` **não é documentada**. O sync tenta, nesta ordem, `lawsuitId`/`litigationId`, `relationships[].linkId` e, por fim, número CNJ no texto; o que não casa fica como `unlinked` nas estatísticas. `GET /integrations/legalone/probe` testa esses candidatos no tenant real (`update_relation`).
- Ainda **não verificado** (sem credenciais neste ambiente): formato aceito pelo `$filter` de data em `updates`/`tasks` (o sync refaz sem filtro em caso de 400, limitado a `max_pages`), filtro `id eq a or id eq b` em `contacts`, e o conteúdo de `appointments`.

### O que é sincronizado

| Legal One | Plataforma | Chave de idempotência |
|---|---|---|
| `lawsuits` (+participantes) | `cases` — `external_ref = legalone:<id>`, `cnj_number` normalizado, `court` (do CNJ), `status` (`closed` → `closed`), `claim_value`, `filed_at`, `typology_hint`, `meta.legalone` (pasta, título, ids, probabilidade, valores) | `external_ref`; adota caso já criado à mão com o mesmo CNJ |
| participantes | `case_parties` — `Customer→cliente`, `OtherParty→parte_contraria`, `LawyerOfOtherParty→advogado_contrario`, `PersonInCharge→responsavel_interno`, `Party→parte`, `Other→terceiro` | `(case_id, tipo:contactId)` em `meta` |
| `contacts` dos `Customer` | `clients` (`erp_kind = legalone`, CNPJ/CPF em `document`) | `erp_config.legalone_contact_id` |
| `updates` | `publications` (`provider = legalone_update`, `category = andamento`), vinculadas ao caso quando a relação é descoberta | `(provider, provider_ref)` |
| `tasks` | `legalone_records` (`kind = task`, `source_date = deadLine`) — **lacuna:** não há tabela de prazos ainda; quando houver, migrar daqui | `(kind, external_id)` |
| tudo acima | `legalone_records` (JSON bruto) + `legalone_sync_runs` (cursor e estatísticas por execução) | |

`typology_hint` é um palpite determinístico (segmento CNJ 5 → trabalhista; palavras no título como *consignado, RMC, cartão, energia, voo, reclamatória*; nome do cliente). A tipologia final continua com a classificação do M1.

### Como rodar

```bash
# incremental desde uma data (creationDate dos processos, date dos andamentos, deadLine das tarefas)
python -m app.workflows.run sync_legalone --since 2026-10-01 --max-pages 50
# desde a última execução bem-sucedida; só alguns recursos
python -m app.workflows.run sync_legalone --since auto --resources lawsuits,updates
# tudo (sem --since) — respeite o limite de 30 por página: use --max-pages
python -m app.workflows.run sync_legalone --tenant-id <uuid> --max-pages 200

# ops (OPS_KEY definida)
curl -H "X-Ops-Key: $OPS_KEY" https://<web>/integrations/legalone/probe
curl -X POST -H "X-Ops-Key: $OPS_KEY" -H "X-Tenant-ID: <uuid>" -H "Content-Type: application/json" \
     -d '{"since":"auto","max_pages":50}' https://<web>/integrations/legalone/sync
```

Sem `--tenant-id` o CLI usa o único tenant `law_firm` ativo. Com `WORKFLOW_ENGINE=hatchet` o endpoint enfileira o job `sync_legalone` no worker; com `in_process` executa na hora e devolve as estatísticas.

### Decisão: protocolo continua manual no Legal One

Não há (ainda) endpoint de escrita validado. **Cadastro de andamentos, prazos e protocolo/peticionamento permanecem manuais no Legal One**; a plataforma só lê. O write-back (M10) para o Legal One fica bloqueado até validarmos endpoints de escrita no tenant — enquanto isso, o `CsvExportConnector` continua sendo o fallback.

## Operação: bootstrap, playbooks e teste de ponta a ponta

Endpoints `/ops/*` exigem `X-Ops-Key == OPS_KEY` (sem chave → 404) e nunca devolvem segredos:

| Rota | Tenant | Função |
|---|---|---|
| `GET /ops/tenants` | — | lista tenants (id, nome, tipo, `test_mode`) |
| `POST /ops/bootstrap` | — | cria/garante tenant, advogado (OAB + MFA placeholder `000000`) e cliente; idempotente por nome/e-mail |
| `POST /ops/playbooks/load?file=<slug>` | `X-Tenant-ID` | carrega `playbooks/<slug>.playbook.yaml` em `theses`/`thesis_versions`; se o YAML está `aprovado`, a versão é aprovada com a OAB e o timestamp do arquivo (idempotente por tipologia+código+versão do playbook) |
| `GET /ops/cases/{id}/trace` | `X-Tenant-ID` | `llm_calls` (modelo, tokens, custo), `audit_log`, checagens de fraude, minutas e revisões do processo |

**Jobs longos são assíncronos.** `POST /dossiers/cases/{id}/build` e `POST /drafts/cases/{id}/generate` devolvem `{"job": ref, "async": true}` e rodam em thread do processo web (engine `in_process`); consulte `GET /jobs/{ref}` (`running|done|failed`). Motivo: o proxy do Railway encerra requisições HTTP em ~5 min e a minuta leva 3–6 min no Sonnet. `?wait=true` mantém o modo síncrono (testes). Com Hatchet, o worker assume e o polling passa a ser pelo painel/SDK.

**Tempo mínimo de revisão em tenant de teste.** `REVIEW_MIN_SECONDS_*` é global. Só um tenant com `tenants.settings.test_mode = true` pode reduzi-lo via `settings.review_min_seconds` (`{"contestacao": 30, "default": 30}`), nunca abaixo de 5 s (`review_min_seconds_for()` em `m07_revisao/service.py`). O E2E cria o tenant **"FBS Piloto (E2E sintético)"** com essa configuração; o tenant real da FBS não tem `test_mode` e segue os 15 min da contestação. Com mais de um tenant `law_firm`, o CLI `python -m app.workflows.run` passa a exigir `--tenant-id`.

**Ponta a ponta (M0→M7) com caso sintético:**

```bash
OPS_KEY_FILE=/caminho/ops_key python scripts/e2e_consignado.py            # produção (default)
AP_BASE_URL=http://localhost:8000 OPS_KEY=... python scripts/e2e_consignado.py --regenerate
```

O script é idempotente (reaproveita tenant, playbook, processo por `external_ref`, documentos por sha256, dossiê e minuta já gerados; `--regenerate` refaz o LLM), imprime a linha do tempo com duração/tokens/custo por etapa e salva `minuta-*.docx`, `minuta.md`, `dossier.json` e `trace.json` em `out/e2e/`. Fixtures em `tests/fixtures/e2e/` (petição de 12 páginas, contrato com assinatura eletrônica, TED, log de autenticação — tudo fictício, CPF com dígito inválido de propósito). O mesmo fluxo roda sem rede em `tests/test_e2e_pipeline.py` com LLM enlatado.

**O que a esteira faz hoje (por módulo):** M2 extrai texto de PDF com camada de texto (`pypdf`) ou texto puro (páginas por `\f`/`--- página N ---`) e classifica tipos de página com `claude-haiku` (um chamado por documento); páginas digitalizadas ficam `outro`/`ocr_confidence=0` até o OCR por visão. M3 guarda os subsídios do cliente em `cases.meta.subsidios` e devolve o checklist de faltantes. M4 deriva o contexto dos autos (procuração, comprovante, OAB, concentração na carteira) e só produz flags. M5 extrai com `claude-sonnet` os campos `extracao` do playbook e fatos/timeline/provas ancorados em apelidos de página `P1…Pn` (resolvidos para `document_page_id`), mescla subsídio/antifraude/calculados e avalia as condições das teses e exceções (`m00_playbook/conditions.py`). M6 usa só teses com versão aprovada por OAB cujas condições foram satisfeitas, segue as seções do `modelo_peca` e grava `draft_citations`; exceção `nao_gerar_minuta` ou campo bloqueante ausente impede a geração. M7 exporta Markdown ou DOCX (`?format=docx`) com o bloco de capa "MINUTA — revisão obrigatória — gerada em … — playbook … aprovado por OAB/…".

## Deploy no Railway

1. Crie um projeto com os serviços **Postgres** (template com pgvector) e **Redis**.
2. Crie dois serviços a partir deste repositório (build pelo `Dockerfile`): `web` (pre-deploy `alembic upgrade head`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`) e `worker` (start `python -m app.workflows.worker`). O `Procfile` descreve os dois.
3. Variáveis: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `WORKFLOW_ENGINE`, `HATCHET_CLIENT_TOKEN`, `PUBLICATIONS_PROVIDER`, `OPS_KEY`, `LEGALONE_CLIENT_ID`/`LEGALONE_CLIENT_SECRET` (nos serviços `web` **e** `worker`) e as do `.env.example`.
4. O `web` roda `alembic upgrade head` antes de subir. Healthcheck em `/health`.
5. Crie a role `aguia_app` (a migração cria se não existir) e aponte `DATABASE_URL` para um usuário **sem** `BYPASSRLS` em produção; o superusuário só para migrações.

## Estado

Esqueleto executável: modelos, migração inicial, API com os fluxos de aprovação/bloqueio, pricing engine com os quatro exemplos testados, adaptadores de workflow/LLM/integrações como stubs documentados. Próximos passos: OCR por visão real, prompts de dossiê/minuta com evals, conector do provedor de publicações, Monte Carlo e lookups nas tabelas `jm_*`.
