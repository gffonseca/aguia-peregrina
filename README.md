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
   ├── app/integrations publications (Comunica PJe, Solucionare), ERP, DataJud
   ├── app/evals/       harness de ground truth
   └── alembic/         migração inicial: schema + RLS + audit_log append-only
```

Stack fixada: Python 3.12 · FastAPI · SQLAlchemy 2 + Alembic · Postgres (pgvector) · Redis · Hatchet · LiteLLM · pydantic-settings · Railway.

## Módulos

### Defesa (M0–M11)

| Módulo | Pacote | Tabelas | Função |
|---|---|---|---|
| M0 Playbook | `modules/m00_playbook` | `theses`, `thesis_versions` | Árvore de teses por tipologia, versionada e **aprovada por sócio (OAB)** |
| M1 Intake | `modules/m01_intake` | `publications` | Captura de distribuições/publicações via provedor ou CSV do ERP |
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

Todas as rotas (exceto `/health` e `/auth/*`) exigem `X-Tenant-ID: <uuid>` e `Authorization: Bearer <token>`. No MVP o login é um stub (`POST /auth/login` → `POST /auth/mfa` com código `000000` em dev).

Para o gateway LiteLLM como proxy separado: `docker compose --profile gateway up -d` e defina `LITELLM_PROXY_URL=http://localhost:4000`.

Sem Hatchet (`WORKFLOW_ENGINE=in_process`) os jobs rodam síncronos no processo web — bom para desenvolvimento. Com `WORKFLOW_ENGINE=hatchet` e `HATCHET_CLIENT_TOKEN`, suba `make worker`.

### Testes e qualidade

```bash
make check      # ruff + mypy + pytest
pytest          # usa SQLite em memória; não precisa de Postgres
```

O RLS do Postgres só é exercitado em banco real; `tests/test_tenant_isolation.py` cobre a camada da aplicação e verifica que a migração aplica a policy em **toda** tabela com `tenant_id`.

## Deploy no Railway

1. Crie um projeto com os serviços **Postgres** (template com pgvector) e **Redis**.
2. Crie dois serviços a partir deste repositório: `web` (start command do `railway.json`) e `worker` (`python -m app.workflows.worker`). O `Procfile` descreve os dois.
3. Variáveis: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `WORKFLOW_ENGINE`, `HATCHET_CLIENT_TOKEN`, `PUBLICATIONS_PROVIDER` e as do `.env.example`.
4. O `web` roda `alembic upgrade head` antes de subir. Healthcheck em `/health`.
5. Crie a role `aguia_app` (a migração cria se não existir) e aponte `DATABASE_URL` para um usuário **sem** `BYPASSRLS` em produção; o superusuário só para migrações.

## Estado

Esqueleto executável: modelos, migração inicial, API com os fluxos de aprovação/bloqueio, pricing engine com os quatro exemplos testados, adaptadores de workflow/LLM/integrações como stubs documentados. Próximos passos: OCR por visão real, prompts de dossiê/minuta com evals, conector do provedor de publicações, Monte Carlo e lookups nas tabelas `jm_*`.
