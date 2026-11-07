# Telemetria da aplicação Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/app-telemetry/design.md`
**Status**: In Progress

---

## Test Coverage Matrix

> Generated from the codebase, the project guidelines and the spec. Guidelines found: none (`AGENTS.md`/`CONTRIBUTING.md` absent) - strong defaults applied. Existing samples: `backend/hairmatch/test_problems.py`, `test_routes.py`, `users/tests.py` (Django `TestCase`), no app tests.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Pure helpers (redaction, log filters, telemetry helpers, sanitizer, resource) | unit | All branches; 1:1 to spec ACs; every listed edge case | `backend/hairmatch/test_*.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test hairmatch --noinput'` |
| Views, middleware, instrumentation of a flow | integration | Happy path + each listed edge case + error paths, asserting exported spans, metrics and logs | `backend/<app>/tests.py`, `backend/hairmatch/test_telemetry_*.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput'` |
| Process behavior (init, resilience, shutdown) | integration | One subprocess per mode; real timing | `backend/hairmatch/test_telemetry_resilience.py` | same as above |
| Compose, `.env.example`, docs | none | - (build gate only) | - | build gate only |
| App utils and axios interceptor | unit | All ACs: format, uniqueness, flag off, broken generator, refresh | `frontend-mobile/utils/__tests__/*.test.ts`, `frontend-mobile/services/__tests__/*.test.ts` | `cd frontend-mobile && npx jest --watchAll=false <paths>` |

## Gate Check Commands

> Generated from the codebase - the backend runs in the `hairmatch_backend` container (`hairmatch_db` must be up).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | After tasks with unit tests only | Backend: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test hairmatch --noinput'`; app: `cd frontend-mobile && npx jest --watchAll=false utils services` |
| Full | After tasks with integration tests | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput'` (whole suite, baseline 1123 tests) |
| Build | After a phase or for config/docs tasks | Full backend suite + `cd frontend-mobile && npx tsc --noEmit` + `docker compose -f docker/docker-compose.yml config -q` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order. Execution is inline (no sub-agents): the system policy of this session forbids spawning agents unless the user asks.

### Phase 1: Redação, logs e dependências

```
T1 → T2 → T3 → T4
```

### Phase 2: Núcleo de telemetria

```
T5 → T6 → T7 → T8
```

### Phase 3: Fluxos instrumentados

```
T9 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T17 → T18 → T19 → T20 → T21
```

### Phase 4: Rota de saúde

```
T22 → T23 → T24
```

### Phase 5: Verificação transversal

```
T25 → T26 → T27
```

### Phase 6: App

```
T28 → T29
```

### Phase 7: Configuração, docs e E2E

```
T30 → T31 → T32
```

---

## Task Breakdown

### Phase 1 tasks: Redação, logs e dependências

### T1: Fixar as versões do OpenTelemetry e do formatador JSON

**What**: Fixar as versões do OpenTelemetry e do formatador JSON.
**Where**: `backend/requirements.txt`
**Depends on**: None
**Reuses**: `backend/requirements.txt`
**Requirement**: TEL-80

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Todo pacote `opentelemetry-*` e `python-json-logger` com `==`
- [x] Imagem reconstruída e container recriado; `pip check` sem conflito
- [x] Suíte inteira igual ao baseline (1123 testes)
- [x] Gate passes; no test deleted, skipped or weakened

**Tests**: none
**Gate**: build

---

### T2: Módulo de redação com as regex do Collector

**What**: Módulo de redação com as regex do Collector.
**Where**: `backend/hairmatch/redaction.py`
**Depends on**: T1
**Reuses**: `docker/observability/otel/config.yaml`
**Requirement**: TEL-44, TEL-45

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `redact()` troca JWT, e-mail, CNPJ, CPF e telefone, nessa ordem, e o JID do WhatsApp
- [x] Tabela de entradas com e sem máscara, falsos positivos documentados
- [x] Um teste lê o `config.yaml` e prova que as cinco expressões são as mesmas
- [x] `scrub_urls()` mantém esquema e host e troca o path
- [x] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### T3: Filtros e formatador JSON de log

**What**: Filtros e formatador JSON de log.
**Where**: `backend/hairmatch/logs.py`
**Depends on**: T2
**Reuses**: `redaction.py`
**Requirement**: TEL-36, TEL-37, TEL-38, TEL-40, TEL-43, TEL-45, TEL-46, TEL-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Linha JSON com `ts`, `level`, `name`, `message`
- [x] `trace_id`/`span_id` só dentro de span válido; ausentes sem span
- [x] Traceback em `exc_info` na mesma linha, redigido; `stack_info` redigido
- [x] `RedactionFilter` devolve cópia (o outro handler vê o original)
- [x] Limite de 1 linha por 60 s por logger `opentelemetry.*`
- [x] Access log sem query string
- [x] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### T4: LOGGING no settings e `traceparent` no CORS

**What**: LOGGING no settings e `traceparent` no CORS.
**Where**: `backend/hairmatch/settings.py`
**Depends on**: T3
**Reuses**: `settings.py:205`
**Requirement**: TEL-14, TEL-36, TEL-43, TEL-46, TEL-75

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Handler de stdout JSON com redação e contexto de trace no root (INFO)
- [x] Logger `opentelemetry` só no stdout, sem propagar
- [x] `django.server` no mesmo formato
- [x] `traceparent` em `CORS_ALLOW_HEADERS` e preflight com o header devolve 200
- [x] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### Phase 2 tasks: Núcleo de telemetria

### T5: Helpers de métrica e de span que nunca lançam

**What**: Helpers de métrica e de span que nunca lançam.
**Where**: `backend/hairmatch/telemetry.py`
**Depends on**: T4
**Reuses**: API do OpenTelemetry
**Requirement**: TEL-12, TEL-13, TEL-60

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Sem SDK, todo helper roda sem exceção
- [x] Exceção do SDK dentro do helper não sobe
- [x] Rótulo fora do conjunto fechado não é registrado
- [x] Nove contadores com os nomes e rótulos do spec
- [x] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### T6: Processor de saneamento e resource

**What**: Processor de saneamento e resource.
**Where**: `backend/hairmatch/otel.py`
**Depends on**: T5
**Reuses**: `redaction.py`
**Requirement**: TEL-29, TEL-30, TEL-31, TEL-47, TEL-48, TEL-86

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Atributos proibidos removidos (lista de TEL-47, `messaging.*`)
- [x] Span `aws-api` vira `<Serviço>.<Operação>`, `CLIENT`, sem ARN
- [x] `exception.message`, `exception.stacktrace` e status redigidos
- [x] Resource com `service.name`, `service.version`, `deployment.environment.name` e `service.instance.id` único
- [x] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### T7: Inicialização idempotente e gancho no WSGI

**What**: Inicialização idempotente e gancho no WSGI.
**Where**: `backend/hairmatch/wsgi.py`
**Depends on**: T6
**Reuses**: `otel.py`
**Requirement**: TEL-01, TEL-02, TEL-03, TEL-04, TEL-05, TEL-06, TEL-07, TEL-08, TEL-35, TEL-82

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Endpoint vazio: providers continuam no-op, sem rede e sem log
- [x] Exceção na inicialização: um `WARNING` com o tipo e o app segue
- [x] Segunda chamada é no-op
- [x] Exportadores com timeout de 2 s, fila 2048, métricas a cada 15 s
- [x] Sampler parent-based, flag `00` não exporta
- [x] Comandos do `manage.py` e testes não iniciam o SDK
- [x] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### T8: Infra de teste com providers em memória e traços da requisição

**What**: Infra de teste com providers em memória e traços da requisição.
**Where**: `backend/hairmatch/test_runner.py`
**Depends on**: T7
**Reuses**: `CognitoResetMixin`
**Requirement**: TEL-16, TEL-17, TEL-20, TEL-21, TEL-32, TEL-33, TEL-37, TEL-83

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Runner instala providers em memória antes de `setup_databases`
- [x] Span SERVER com `http.route` em template; queries filhas sem valores
- [x] `traceparent` válido vira pai; inválido abre trace novo e responde igual
- [x] Histograma `http.server.request.duration` em `s` com `http.route` e exemplar
- [x] Rota fora de `/api/` segue as mesmas regras
- [x] Suíte inteira passa instrumentada
- [x] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### Phase 3 tasks: Fluxos instrumentados

### T9: Upload ao S3 no thread da requisição

**What**: Upload ao S3 no thread da requisição.
**Where**: `backend/hairmatch/storage.py`
**Depends on**: T8
**Reuses**: `S3MediaStorage._save`
**Requirement**: TEL-18, TEL-23

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `PutObject` é filho do span da requisição (mesmo `trace_id`, pai = requisição)
- [x] Comportamento do upload igual (content type, chave)
- [x] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### T10: Span da conversão para WebP

**What**: Span da conversão para WebP.
**Where**: `backend/hairmatch/images.py`
**Depends on**: T9
**Reuses**: `to_webp`
**Requirement**: TEL-23, TEL-24

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Span `image.to_webp` com `image.bytes_in` e `image.bytes_out` inteiros e nenhum outro dado
- [x] Upload de foto da galeria gera `image.to_webp` e `S3.PutObject` no mesmo trace
- [x] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### T11: Contador de push e SNS no mesmo trace

**What**: Contador de push e SNS no mesmo trace.
**Where**: `backend/notifications/dispatch.py`
**Depends on**: T10
**Reuses**: `publish_alert`
**Requirement**: TEL-18, TEL-22, TEL-48, TEL-52, TEL-53

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `push.results` com `published`, `endpoint_gone`, `unavailable` por aparelho e `error` fora do laço
- [x] Pedido ao SNS idêntico ao de antes (sem `MessageAttributes`) e span `SNS.Publish` sem ARN, token nem corpo
- [x] `POST /api/reservations` com aparelho gera requisição, queries e `SNS.Publish` no mesmo `trace_id`
- [x] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### T12: Reserva: atributos, contador por canal e logger

**What**: Reserva: atributos, contador por canal e logger.
**Where**: `backend/reserve/views.py`
**Depends on**: T11
**Reuses**: `CreateReserve`, `create_new_reserve`
**Requirement**: TEL-28, TEL-41, TEL-42, TEL-51

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `hairmatch.reserve_id` e `hairmatch.hairdresser_id` inteiros no span
- [ ] `reserves.created` com `app` e `whatsapp` só depois do commit
- [ ] `print()` trocado por log sem texto livre
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### T13: Contador de erros por slug

**What**: Contador de erros por slug.
**Where**: `backend/hairmatch/problems.py`
**Depends on**: T12
**Reuses**: `problem_response`
**Requirement**: TEL-50

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `problems` soma 1 com `slug` e `status` da resposta
- [ ] Slug fora do catálogo não gera rótulo novo
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### T14: Contador de sessões recusadas

**What**: Contador de sessões recusadas.
**Where**: `backend/users/authentication.py`
**Depends on**: T13
**Reuses**: `authenticated_user`
**Requirement**: TEL-54

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `auth.rejections` com `missing`, `expired`, `invalid` e `unavailable`
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### T15: Contador dos passos do cadastro

**What**: Contador dos passos do cadastro.
**Where**: `backend/users/views.py`
**Depends on**: T14
**Reuses**: `RegisterView`, `EmailConfirmationView`, `ConfirmationCodeView`
**Requirement**: TEL-55

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `signup.events` com `created`, `confirmed`, `resent` e `throttled`
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### T16: Contador de uploads de perfil e galeria

**What**: Contador de uploads de perfil e galeria.
**Where**: `backend/users/views.py`
**Depends on**: T15
**Reuses**: `ProfilePictureView`, `GalleryPhotoCollection`
**Requirement**: TEL-56

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `uploads` com `kind` `profile`/`gallery` e `outcome` `stored`/`invalid_image`/`failed`
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### T17: Contador de uploads de avaliação

**What**: Contador de uploads de avaliação.
**Where**: `backend/review/views.py`
**Depends on**: T16
**Reuses**: `CreateReview`, `ReviewPictureCollection`
**Requirement**: TEL-56

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `uploads` com `kind=review` e os três resultados
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### T18: Consulta de CEP: contador e log sem URL

**What**: Consulta de CEP: contador e log sem URL.
**Where**: `backend/users/cep_lookup.py`
**Depends on**: T17
**Reuses**: `lookup_cep`
**Requirement**: TEL-19, TEL-57

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `cep.lookups` com `cache`, `viacep`, `brasilapi`, `not_found`, `unavailable`
- [ ] Span HTTP com método, host e status, sem o CEP
- [ ] Log de falha do provedor sem a URL
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### T19: Gemini do perfil: span, contadores e tokens

**What**: Gemini do perfil: span, contadores e tokens.
**Where**: `backend/hairmatch/ai_clients/gemini_client.py`
**Depends on**: T18
**Reuses**: `generate_ai_text`
**Requirement**: TEL-25, TEL-26, TEL-27, TEL-58, TEL-59

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Span `gemini generate_content` com modelo e `hairmatch.ai.feature`, sem prompt nem resposta
- [ ] Tokens no span e em `ai.tokens` quando a resposta os traz
- [ ] Exceção: span com erro e tipo; a exceção segue para o tratamento existente; `ai.requests` `error`
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### T20: Gemini do chatbot: utilitários

**What**: Gemini do chatbot: utilitários.
**Where**: `backend/chatbot/ai_utils.py`
**Depends on**: T19
**Reuses**: `gemini_client.py`
**Requirement**: TEL-25, TEL-41, TEL-42, TEL-58

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Chamadas do Gemini com `feature=chatbot`
- [ ] `print()` trocado por log com evento, IDs e tipo da exceção
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### T21: Gemini do chatbot: views

**What**: Gemini do chatbot: views.
**Where**: `backend/chatbot/views.py`
**Depends on**: T20
**Reuses**: `EvolutionApi`
**Requirement**: TEL-25, TEL-41, TEL-42, TEL-58

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Três chamadas do chatbot com span e contador
- [ ] Zero `print()` e nenhum número, texto ou resposta nos logs
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### Phase 4 tasks: Rota de saúde

### T22: Rota de saúde

**What**: Rota de saúde.
**Where**: `backend/hairmatch/health.py`
**Depends on**: T21
**Reuses**: `problem_response`
**Requirement**: TEL-34, TEL-61, TEL-62, TEL-63, TEL-64, TEL-65

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] 200 `{"status": "ok"}`; 503 problem+json `service-unavailable` com a conexão quebrada
- [ ] Sem sessão e sem throttle
- [ ] POST responde 405 com `Allow` contendo GET
- [ ] Sem span e sem ponto de métrica HTTP
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### T23: Slug `service-unavailable` no catálogo

**What**: Slug `service-unavailable` no catálogo.
**Where**: `backend/hairmatch/problems.py`
**Depends on**: T22
**Reuses**: `CATALOG`
**Requirement**: TEL-67

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Linha no `CATALOG`, no catálogo do spec `api-problem-details` e em `frontend-mobile/utils/api-problem.ts`
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### T24: Rota RT-100 na tabela de rotas

**What**: Rota RT-100 na tabela de rotas.
**Where**: `backend/hairmatch/test_routes.py`
**Depends on**: T23
**Reuses**: `ROUTE_TABLE`
**Requirement**: TEL-66

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `GET health` no `ROUTE_TABLE` e RT-100 no spec `api-restful-routes`
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### Phase 5 tasks: Verificação transversal

### T25: Testes de privacidade por fluxo

**What**: Testes de privacidade por fluxo.
**Where**: `backend/hairmatch/test_telemetry_privacy.py`
**Depends on**: T24
**Reuses**: `testing_telemetry.py`
**Requirement**: TEL-49

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cadastro, login, CEP, preflight do CEP, reserva com push, upload e Gemini: nenhum valor de teste em span, evento, resource nem log
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### T26: Testes de resiliência por subprocesso

**What**: Testes de resiliência por subprocesso.
**Where**: `backend/hairmatch/test_telemetry_resilience.py`
**Depends on**: T25
**Reuses**: `manage.py runserver --noreload`
**Requirement**: TEL-09, TEL-10, TEL-11, TEL-15, TEL-84

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Conexão recusada, nome que não resolve e IP sem resposta: mesmo status e corpo; p95 dentro de 50 ms
- [ ] Desligamento em até 5 s
- [ ] No máximo 1 linha de erro por sinal a cada 60 s
- [ ] Volta a exportar quando o Collector volta
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: integration
**Gate**: full

---

### T27: Gate de ausência de `print()`

**What**: Gate de ausência de `print()`.
**Where**: `backend/hairmatch/test_no_print.py`
**Depends on**: T26
**Reuses**: `ast`
**Requirement**: TEL-41

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Teste varre o AST do backend sem testes e falha em qualquer `print(`
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### Phase 6 tasks: App

### T28: Gerador de `traceparent` do app

**What**: Gerador de `traceparent` do app.
**Where**: `frontend-mobile/utils/telemetry.ts`
**Depends on**: T27
**Reuses**: `push-registration.ts`
**Requirement**: TEL-69, TEL-70, TEL-72, TEL-73, TEL-74

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Formato `00-<32 hex>-<16 hex>-01` em minúsculas, nunca todo zero, único por chamada
- [ ] `telemetry.web.ts` com as mesmas exportações
- [ ] Gerador quebrado não lança
- [ ] Nenhuma dependência nativa nova
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### T29: Interceptor do axios com `traceparent`

**What**: Interceptor do axios com `traceparent`.
**Where**: `frontend-mobile/services/axios-instance.ts`
**Depends on**: T28
**Reuses**: `axiosInstance`
**Requirement**: TEL-68, TEL-71, TEL-72, TEL-76, TEL-79, TEL-85

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Variável `true`: toda requisição leva `traceparent`; ausente ou outro valor: nenhum
- [ ] Refresh (401, refresh, nova tentativa) leva três `traceparent` distintos
- [ ] `.env.example` lista `EXPO_PUBLIC_TRACE_PROPAGATION` vazia
- [ ] `npx tsc --noEmit` sem erro novo
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: unit
**Gate**: quick

---

### Phase 7 tasks: Configuração, docs e E2E

### T30: Variáveis `OTEL_*` no compose e no `.env.example`

**What**: Variáveis `OTEL_*` no compose e no `.env.example`.
**Where**: `docker/docker-compose.yml`
**Depends on**: T29
**Reuses**: `docker/docker-compose.yml`
**Requirement**: TEL-77, TEL-78

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Serviço `django` recebe as três, vazias por padrão
- [ ] `docker/.env.example` lista as três com o comentário do modo combinado
- [ ] Compose sobe sem `docker/.env` com a telemetria desligada
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: none
**Gate**: build

---

### T31: Seção do README de observabilidade

**What**: Seção do README de observabilidade.
**Where**: `docs/observability/README.md`
**Depends on**: T30
**Reuses**: `docs/observability/README.md`
**Requirement**: TEL-81

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Passo a passo para ligar backend e app e achar o trace e os logs de uma reserva
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: none
**Gate**: build

---

### T32: E2E contra a stack real, AD-016 e fechamento

**What**: E2E contra a stack real, AD-016 e fechamento.
**Where**: `.specs/STATE.md`
**Depends on**: T31
**Reuses**: stack da #193
**Requirement**: TEL-84

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Trace da reserva no Tempo com o `trace_id` do header, logs do span no Loki, contadores no Prometheus, dashboard `api-red.json` sem mudança
- [ ] AD-016 registrado e Handoff atualizado
- [ ] Gate passes; no test deleted, skipped or weakened

**Tests**: none
**Gate**: build

---

## Phase Execution Map

```
Phase 1:  T1 ------→ T2 ------→ T3 ------→ T4
Phase 2:  T5 ------→ T6 ------→ T7 ------→ T8
Phase 3:  T9 ------→ T10 ------→ T11 ------→ T12 ------→ T13 ------→ T14 ------→ T15 ------→ T16 ------→ T17 ------→ T18 ------→ T19 ------→ T20 ------→ T21
Phase 4:  T22 ------→ T23 ------→ T24
Phase 5:  T25 ------→ T26 ------→ T27
Phase 6:  T28 ------→ T29
Phase 7:  T30 ------→ T31 ------→ T32
```

Execution is strictly sequential, one task at a time.
