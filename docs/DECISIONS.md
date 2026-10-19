# Registro de decisões de arquitetura (ADR)

Formato: contexto → decisão → consequências. Uma entrada por decisão; nunca apagar, só superar.

---

## ADR-001 — Python 3.12 + FastAPI (não Laravel)

**Data:** 2026-10-19 · **Status:** aceita

**Contexto.** O relatório "Engenharia reversa da Enter" (§8) sugeria Laravel/PHP pela familiaridade do time. O relatório de compra de créditos (§7) já fixa Python/FastAPI, porque o pricing engine, a jurimetria (Kaplan–Meier/Cox, Monte Carlo) e os evals vivem no ecossistema Python.

**Decisão.** Backend único em Python 3.12 com FastAPI; pydantic v2 para schemas e saída estruturada dos LLMs; pydantic-settings para configuração.

**Consequências.** Um só runtime para API, workers, pricing e evals. O painel pode ser qualquer front (Next.js, Metabase) sobre a API.

## ADR-002 — SQLAlchemy 2 + Alembic sobre Postgres com pgvector

**Status:** aceita

**Decisão.** Modelos declarativos SQLAlchemy 2 (`Mapped[]`), migrações Alembic. Postgres 16 com `pgvector` para similaridade entre peças próprias (`document_pages.embedding vector(1536)`). SQLite só em testes.

**Consequências.** `Base.metadata` é a fonte única do schema; a migração inicial cria as tabelas a partir dele e acrescenta o que é específico de Postgres (vector, RLS, triggers).

## ADR-003 — Multi-tenant com `tenant_id` em toda tabela e RLS no Postgres

**Status:** aceita

**Contexto.** A "muralha de dados" entre o tenant de defesa (`law_firm`, FBS) e o tenant de compra (`credit_buyer`, Compradora) é pré-requisito jurídico (ACP OAB-SP; Res. CMN 5.343) e comercial. Um vazamento entre os dois lados contaminaria ambos.

**Decisão.**
- Dois tipos de tenant: `law_firm` e `credit_buyer`. Nenhuma tabela compartilhada além de `tenants`.
- `tenant_id` obrigatório e indexado em toda tabela de negócio (mixin `TenantMixin`).
- Postgres RLS: `ENABLE` + `FORCE ROW LEVEL SECURITY` e policy `tenant_isolation` (`USING`/`WITH CHECK tenant_id = app_current_tenant()`) em toda tabela com `tenant_id`; a role da aplicação `aguia_app` não tem `BYPASSRLS`. O tenant corrente vai por `set_config('app.tenant_id', …, true)` a cada transação.
- Defesa em profundidade na aplicação: `with_loader_criteria` filtra todo SELECT pelo tenant do contexto e `before_flush` bloqueia escrita cruzada (`TenantIsolationError`).
- Lista de exclusão (hash de CPF/CNPJ) impede que cliente da FBS vire cedente da Compradora.

**Consequências.** Nenhuma consulta sem tenant resolvido devolve linhas em produção. Jobs de workflow recebem `tenant_id` no payload e o setam no contexto antes de abrir sessão.

## ADR-004 — Hatchet para workflows, com adaptador e fallback in-process

**Status:** aceita

**Contexto.** O relatório recomenda não começar por Temporal/Kubernetes. Hatchet dá workflows duráveis, retries e filas com um SDK simples e tem versão self-hosted.

**Decisão.** Interface `WorkflowEngine` (`register`, `dispatch`) em `app/workflows/engine.py`, com `HatchetEngine` (hatchet-sdk, extra `workflows`) e `InProcessEngine` (síncrono, dev/testes). Escolha por `WORKFLOW_ENGINE`. Jobs: `intake_publication`, `process_document`, `build_dossier`, `generate_draft`, `monitor_publication`, `pricing_run`.

**Consequências.** O código de negócio não conhece o Hatchet. Trocar de engine (Celery, Temporal) é implementar a interface.

## ADR-005 — LiteLLM como gateway único de LLM; log obrigatório em `llm_calls`

**Status:** aceita

**Decisão.** Toda chamada de modelo passa por `app/llm/client.py` (wrapper sobre `litellm`), que usa nomes lógicos do `litellm_config.yaml` (`claude-sonnet`, `claude-haiku`, `claude-opus`, `gpt-4o`, `gpt-4o-mini`, `text-embedding`). Cada chamada grava `LlmCall` com `model`, `provider_model`, `prompt_hash` (SHA-256 do array de mensagens; o prompt em claro não é persistido), `prompt_version`, tokens, latência, custo, status, `case_id`. `structured()` força JSON validado por schema pydantic.

**ZDR.** Só modelos com `model_info.zdr: true` podem receber dados de autos. Anthropic: contrato comercial com não-treinamento; ZDR formal via enterprise. OpenAI: ZDR só após aprovação na conta. Evidência contratual deve ser anexada a este ADR antes do primeiro processo real.

**Consequências.** `litellm` é dependência opcional; sem ela o cliente roda em modo `fake` (CI). Custos por processo saem direto de `llm_calls`.

## ADR-006 — Railway (web + worker + Postgres + Redis)

**Status:** aceita

**Decisão.** `railway.json` com Nixpacks e `Procfile` com dois processos: `web` (migra e sobe uvicorn) e `worker` (`python -m app.workflows.worker`). Postgres (plugin com pgvector) e Redis como serviços do projeto. Bucket S3-compatível do Railway para autos.

## ADR-007 — Trilha de auditoria e princípios OAB codificados

**Status:** aceita

**Contexto.** ACP OAB-SP × Enter e Res. CFOAB apontam para um regime em que estratégia e minuta pertencem a advogados inscritos, com trilha por peça.

**Decisão (invariantes do código, não só do processo).**
1. **Advogado identificado por peça:** `thesis_versions.author_oab/approved_by_oab`, `reviews.reviewer_oab`, `filings.filed_by_oab`; rotas de aprovação exigem `require_lawyer` (role lawyer/partner + OAB + MFA).
2. **Bloqueio de exportação sem aprovação:** `assert_exportable()` em toda rota de export/protocolo; sem `reviews.approved_at` → HTTP 423.
3. **Tempo mínimo de revisão:** `approve()` recusa se `now − opened_at < REVIEW_MIN_SECONDS_<tipo>`.
4. **Direito de recusa:** `reject()` exige motivo (≥ 10 caracteres) e registra `rejected_at`.
5. **Nenhum rótulo "fraudador" sem aprovação humana:** `fraud_checks` só gera `flag` com evidência; `has_confirmed_fraud()` só é verdadeiro com `human_decision = confirmed` por OAB; a decisão passa por `audit_log`.
6. `audit_log` é append-only (sem UPDATE/DELETE para a role da aplicação; trigger que levanta exceção).
7. Logs de LLM nunca guardam o prompt em claro, só o hash e a versão.

## ADR-008 — Pricing engine explícito e versionado

**Status:** aceita

**Decisão.** `app/modules/credit/pricing_engine.py` implementa literalmente a fórmula da nota técnica (P_max com τ e DF̄, oferta com margem 10–20 %), árvore de cenários achatada em terminais e `params_hash` + `METHODOLOGY_VERSION` gravados em `pricing_runs`. Os quatro exemplos da nota são fixtures (`examples.py`) e testes com tolerância. Monte Carlo (p10–p90) e lookups nas cinco tabelas `jm_*` com fallback hierárquico são a próxima iteração.

**Nota.** No exemplo (ii), o relatório grafa 43,75 % para "extinção/improcedência"; a árvore fecha em 1 com 33,75 % e o PV não muda (CF = 0). No exemplo (iv), a fórmula exata dá P_max ≈ 650–700 contra os ≈ 750 arredondados do relatório; o teste usa tolerância de 15 % e trava o intervalo "≤ 15–20 % do pedido".

## ADR-009 — O que não construir no MVP

**Status:** aceita

Sem OCR próprio (visão LLM por página); sem conectividade bruta com tribunais (provedor de publicações + DataJud público); sem protocolo automático (MNI); sem Kubernetes/ClickHouse; sem 400 modelos; sem cobrança por êxito em contrato de software; sem base cross-cliente.
