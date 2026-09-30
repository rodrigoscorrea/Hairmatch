# Erros da API em RFC 9457 Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/api-problem-details/design.md`
**Status**: In Progress

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec. Guidelines found: none (sem `AGENTS.md`, `CONTRIBUTING.md` ou config de cobertura) - strong defaults applied. Os testes existentes (`*/tests.py`, Django `TestCase`) fixam o estilo e o piso. A decisão "o app não tem testes, o gate é `tsc` mais UAT" vem do spec (herdada do #106 e do #139).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Módulo de problems (`hairmatch/problems.py`) | unit + integration | Todo slug do catálogo, cada exceção do mapa, `Allow`, `Retry-After`, `DEBUG=True` e `False` | `backend/hairmatch/test_problems.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test hairmatch --noinput'` |
| Views e helpers de autenticação | integration | Todo erro da view com `Content-Type`, slug, status e `detail` em inglês, mais o caso feliz | `backend/<app>/tests.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test <app> --noinput'` |
| Cliente Gemini | unit | Sem configuração e com falha viram `Problem`, sem texto da exceção | `backend/hairmatch/tests.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test hairmatch --noinput'` |
| App: normalizador e catálogo | none | Sem teste automatizado (decisão do spec). Gate de tipos e UAT | `frontend-mobile/**` | `cd frontend-mobile && npx tsc --noEmit` |
| Docs e specs | none | - | `.specs/**` | - |

## Gate Check Commands

> Generated from codebase (`docker/docker-compose.yml`, `backend/hairmatch/test_runner.py`) - Python 3.9 no container.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefa que só mexe em um app | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test <app> --noinput'` |
| Full | Tarefa que muda o contrato compartilhado (T1, T2) ou fecha uma fase | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput'` |
| Build | Tarefas do app | `cd frontend-mobile && npx tsc --noEmit` |

---

## Execution Plan

### Phase 1: Núcleo

```
T1 → T2
```

### Phase 2: Usuários e contas

```
T2 → T3 → T4 → T5 → T6
```

### Phase 3: Agendamento

```
T6 → T7 → T8 → T9 → T10
```

### Phase 4: Endpoints auxiliares

```
T10 → T11 → T12 → T13
```

### Phase 5: App

```
T13 → T14 → T15 → T16 → T17
```

### Phase 6: Fechamento

```
T17 → T18
```

---

## Task Breakdown

### T1: Módulo central de problems

**What**: Criar catálogo, `Problem`, `problem_response`, `json_object`, `exception_handler` e a view catch-all, e ligá-los em `settings.py` e `urls.py`.
**Where**: `backend/hairmatch/problems.py`
**Depends on**: None
**Reuses**: `PROBLEM_TYPE_BASE_URI` em settings
**Requirement**: PD-01, PD-02, PD-03, PD-04, PD-05, PD-06, PD-07, PD-60, PD-61, PD-62, PD-63, PD-64, PD-65, PD-66, PD-67, PD-110, PD-111, PD-112, PD-113

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os 36 slugs do catálogo estão em `CATALOG` com status e title do spec
- [x] `test_problems.py` cobre 405 com `Allow`, 415, 429 com e sem `Retry-After`, 500 logado, 404 de rota, `DEBUG=True` e `False`, `/admin/` intocado
- [x] Gate check passes: full
- [x] Nenhum teste removido (463 antes)

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add RFC 9457 problem details core`

---

### T2: Helpers de autenticação em problem+json

**What**: Trocar o corpo das respostas 401, 403 e 503 de `authenticated_user`, `authenticated_hairdresser`, `authenticated_customer` e `forbidden`, e reescrever os asserts dessas respostas em todos os apps.
**Where**: `backend/users/authentication.py`
**Depends on**: T1
**Reuses**: `problem_response`
**Requirement**: PD-10, PD-11, PD-12, PD-13, PD-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] 401 `invalid-session`, 503 `auth-unavailable`, 403 `forbidden`, 403 `hairdresser-required`, 403 `customer-required`
- [x] Asserts de 401/403 reescritos em `users`, `service`, `agenda`, `availability`, `reserve`, `review`, `preferences`
- [x] Gate check passes: full

**Tests**: integration
**Gate**: full

**Commit**: `feat(auth): return problem details for session and permission errors`

---

### T3: Login, refresh, logout e Google

**What**: Converter os erros de `LoginView`, `RefreshView`, `GoogleAuthView`, `_cognito_error_response` e do login em conta Google.
**Where**: `backend/users/views.py`
**Depends on**: T2
**Reuses**: `problem_response`, `body_error`
**Requirement**: PD-15, PD-16, PD-17, PD-18, PD-19, PD-20, PD-21, PD-22, PD-23

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Cada critério com o slug do spec e `detail` em inglês
- [x] Login sem e-mail e sem senha devolve dois itens em `errors`
- [x] Refresh recusado continua apagando os cookies `jwt` e `refresh_token`
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test users --noinput'`

**Tests**: integration
**Gate**: quick

**Commit**: `feat(auth): problem details for login, refresh and Google auth`

---

### T4: Conta autenticada (GET, PUT, DELETE) e troca de senha

**What**: Converter os erros de `ChangePasswordView`, `UserInfoCookieView`, `UserInfoView` e `CustomerHomeView`, e fazer os DELETE de conta responderem 204.
**Where**: `backend/users/views.py`
**Depends on**: T3
**Reuses**: `problem_response`, `json_object`, `clear_auth_cookies`
**Requirement**: PD-14, PD-17, PD-28, PD-30, PD-35, PD-36, PD-37, PD-62, PD-72, PD-73, PD-114

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Troca de senha: campos ausentes em `errors`, senha atual errada `incorrect-current-password`, política `password-policy`, conta Google `google-account-login`
- [x] `PUT user/authenticated` com JSON inválido responde 400 `malformed-request` (era 500)
- [x] `GET customer/home/<email>` por não cliente responde 403 `customer-required` (era 404)
- [x] DELETE de conta responde 204 sem corpo e apaga os cookies
- [x] Gate check passes: quick (`users`)

**Tests**: integration
**Gate**: quick

**Commit**: `feat(users): problem details for account endpoints and 204 on delete`

---

### T5: Cadastro por e-mail e por Google

**What**: Converter os erros de `RegisterView` e `_register_with_google`, coletando todos os campos ausentes em `errors`.
**Where**: `backend/users/views.py`
**Depends on**: T4
**Reuses**: `validation_problem`, `body_error`
**Requirement**: PD-24, PD-25, PD-26, PD-27, PD-28, PD-29, PD-30, PD-31, PD-32, PD-33, PD-34

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Um item de `errors` por campo ausente, `#/role`, `#/phone` e `#/preferences` apontados
- [x] 409 `email-taken`, `phone-taken`, `google-account-taken`
- [x] 400 `password-policy` e `invalid-image`, 401 `signup-session-expired`, 500 `internal-error` sem deixar usuário criado
- [x] Gate check passes: quick (`users`)

**Tests**: integration
**Gate**: quick

**Commit**: `feat(users): problem details for sign-up`

---

### T6: CEP, Gemini, profissional e busca

**What**: Converter `CepLookupView`, `GeminiChatView`, `HairdresserInfoView` e o cliente Gemini, que passa a levantar `Problem`.
**Where**: `backend/hairmatch/ai_clients/gemini_client.py`
**Depends on**: T5
**Reuses**: `Problem`, `json_object`
**Requirement**: PD-63, PD-90, PD-91, PD-92, PD-93, PD-94, PD-57

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] 400 `invalid-postal-code`, 404 `postal-code-not-found`, 503 `postal-code-service-unavailable`
- [ ] Gemini sem configuração ou com falha: 503 `ai-service-unavailable`, sem `Config error` nem texto da exceção
- [ ] Throttle do CEP e do Gemini: 429 com `Retry-After`
- [ ] Testes de `hairmatch/tests.py` reescritos para `Problem`
- [ ] Gate check passes: full

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): problem details for CEP, Gemini and hairdresser lookup`

---

### T7: Reserva

**What**: Converter os erros de `ReserveById`, `CreateReserve`, `ListReserve`, `RemoveReserve` e `ReserveSlot`, e separar a constante de conflito do cliente em inglês (API) e português (chatbot).
**Where**: `backend/reserve/views.py`
**Depends on**: T6
**Reuses**: `problem_response`, `validation_problem`, `json_object`
**Requirement**: PD-40, PD-41, PD-42, PD-43, PD-44, PD-45, PD-46, PD-47, PD-48, PD-71, PD-72

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cada critério com o slug do spec, sem `f'...{e}'` em corpo de resposta
- [ ] `DELETE reserve/remove/<id>` responde 204, e reserva ausente `Reservation not found.`
- [ ] `get_available_slots` responde 404 para serviço ausente (era 500 no dict interno), e a mensagem em português do WhatsApp não muda
- [ ] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test reserve chatbot --noinput'`

**Tests**: integration
**Gate**: quick

**Commit**: `feat(reserve): problem details and 409 for reservation conflicts`

---

### T8: Agenda

**What**: Converter os erros de `CreateAgenda`, `ListAgenda` e `RemoveAgenda`.
**Where**: `backend/agenda/views.py`
**Depends on**: T7
**Reuses**: `problem_response`, `validation_problem`, `json_object`
**Requirement**: PD-49, PD-50, PD-51, PD-57, PD-72

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Formato inválido de `start_time` ou `end_time` aponta o campo em `errors`
- [ ] Serviço inexistente responde 404 (era 500), sobreposição responde 409 `agenda-overlap` (era 400)
- [ ] DELETE responde 204
- [ ] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test agenda --noinput'`

**Tests**: integration
**Gate**: quick

**Commit**: `feat(agenda): problem details and 409 for agenda overlap`

---

### T9: Disponibilidade

**What**: Converter os erros de `CreateAvailability`, `CreateMultipleAvailability`, `UpdateMultipleAvailability`, `UpdateAvailability`, `RemoveAvailability` e `ListAvailability`, sem `str(e)`.
**Where**: `backend/availability/views.py`
**Depends on**: T8
**Reuses**: `problem_response`, `validation_problem`, `json_object`
**Requirement**: PD-13, PD-52, PD-53, PD-54, PD-57, PD-62, PD-72

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `POST /api/availability/create` por não profissional responde 403 `hairdresser-required` (era 404)
- [ ] Campos ausentes e `weekday` inválido apontados em `errors`, na criação unitária e em lote
- [ ] Duplicidade responde 409 `availability-exists` (era 400)
- [ ] `PUT update/multiple/<id>` responde 200 (era 201)
- [ ] DELETE responde 204, `<Resource> not found.` no 404
- [ ] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test availability --noinput'`

**Tests**: integration
**Gate**: quick

**Commit**: `feat(availability): problem details, 409 on duplicates and 200 on bulk update`

---

### T10: Serviço

**What**: Converter os erros de `CreateService`, `ListService`, `ListServiceHairdresser`, `UpdateService` e `RemoveService`.
**Where**: `backend/service/views.py`
**Depends on**: T9
**Reuses**: `problem_response`, `validation_problem`, `json_object`
**Requirement**: PD-55, PD-56, PD-57, PD-72

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Corpo inválido responde `malformed-request`, campos ausentes viram itens de `errors`
- [ ] Exclusão com reservas responde 409 `service-has-reservations` (era 400)
- [ ] DELETE responde 204
- [ ] Gate check passes: quick (`service`)

**Tests**: integration
**Gate**: quick

**Commit**: `feat(service): problem details and 409 when a service has reservations`

---

### T11: Avaliações

**What**: Converter os erros de `CreateReview`, `ListReview`, `UpdateReview` e `RemoveReview`, sem `str(e)`.
**Where**: `backend/review/views.py`
**Depends on**: T10
**Reuses**: `problem_response`, `validation_problem`
**Requirement**: PD-14, PD-95, PD-96, PD-97, PD-98, PD-72

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Campos ausentes, `rating` inválido e profissional divergente apontados em `errors`
- [ ] 409 `review-exists`, 403 `forbidden`, 400 `invalid-image`, 403 `customer-required`
- [ ] DELETE responde 204
- [ ] Gate check passes: quick (`review`)

**Tests**: integration
**Gate**: quick

**Commit**: `feat(review): problem details for reviews`

---

### T12: Preferências

**What**: Converter os erros das views de preferências, sem `str(e)` e mantendo o 404 de que o app depende.
**Where**: `backend/preferences/views.py`
**Depends on**: T11
**Reuses**: `problem_response`
**Requirement**: PD-99, PD-57

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Lista vazia e preferência inexistente respondem 404 `not-found` com `Preference not found.`
- [ ] Nenhum `except Exception` devolve `str(e)`
- [ ] Gate check passes: quick (`preferences`)

**Tests**: integration
**Gate**: quick

**Commit**: `feat(preferences): problem details for preferences`

---

### T13: Webhook do chatbot

**What**: Converter o 400 de JSON inválido e o 500 de falha interna de `EvolutionApi`.
**Where**: `backend/chatbot/views.py`
**Depends on**: T12
**Reuses**: `problem_response`
**Requirement**: PD-100, PD-71

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] JSON inválido: 400 `malformed-request`. Falha interna: 500 `internal-error`
- [ ] As mensagens em português enviadas ao WhatsApp não mudam
- [ ] Gate check passes: full (fecha o backend)

**Tests**: integration
**Gate**: full

**Commit**: `feat(chatbot): problem details for the webhook errors`

---

### T14: Normalizador e catálogo pt-BR do app

**What**: Criar `ApiProblem`, `ProblemSlug`, `toApiProblem` e `problemMessage` com o catálogo pt-BR do spec.
**Where**: `frontend-mobile/utils/api-problem.ts`
**Depends on**: T13
**Reuses**: `constants/errorMessages.ts`
**Requirement**: PD-80, PD-81, PD-82, PD-87

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Aceita `AxiosError`, problem cru e JSON parseado
- [ ] Sem resposta de rede devolve `Não foi possível conectar ao servidor.`
- [ ] Slug fora do catálogo ou corpo não problem devolve o fallback da tela, e o `detail` nunca é devolvido
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none
**Gate**: build

**Commit**: `feat(app): add problem details normalizer and pt-BR catalog`

---

### T15: Login, sessão e cadastro (transporte)

**What**: Trocar `response.data.error` por `problemMessage` no `signIn` e no `loadSession`, normalizar o erro do `signUp` (web e native) e trocar os fallbacks em inglês.
**Where**: `frontend-mobile/app/_layout.tsx`
**Depends on**: T14
**Reuses**: `problemMessage`, `toApiProblem`
**Requirement**: PD-80, PD-82, PD-86, PD-101

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `signIn` e `loadSession` mostram o texto do catálogo
- [ ] `signUp` levanta o problem normalizado nas duas plataformas
- [ ] Fallbacks `Authentication failed...` e `An unknown error occurred...` em português
- [ ] O refresh continua disparando só por 401 fora de `AUTH_EXCLUDED`
- [ ] Gate check passes: build

**Tests**: none
**Gate**: build

**Commit**: `feat(app): show catalog messages for login and session errors`

---

### T16: Telas que mostram erro do backend

**What**: Usar o catálogo em `useGoogleAuth`, `useDescription`, `usePreferences`, `useServiceBooking` e `useLogin`, e trocar o fallback de `useReviewForm`.
**Where**: `frontend-mobile/hooks/customerHooks/useServiceBooking.ts`
**Depends on**: T15
**Reuses**: `problemMessage`
**Requirement**: PD-81, PD-82, PD-83, PD-101

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] As cinco telas (login, Google, cadastro descrição, cadastro preferências, confirmação de reserva) mostram o texto do catálogo
- [ ] Nenhum `response.data.error` nem `error.error` sobra em `hooks/` e `app/`
- [ ] Fallbacks em português (`useLogin`, `useReviewForm`)
- [ ] Gate check passes: build

**Tests**: none
**Gate**: build

**Commit**: `feat(app): show pt-BR catalog messages in the five error screens`

---

### T17: Exclusão de serviço e busca de CEP por slug

**What**: Decidir pelo slug, e não pelo status, em `useServiceManager` e `useCepLookup`.
**Where**: `frontend-mobile/hooks/hairdresserHooks/useServiceManager.ts`
**Depends on**: T16
**Reuses**: `toApiProblem`
**Requirement**: PD-84, PD-85, PD-87

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `service-has-reservations` mostra `Não é possível excluir esse serviço pois há um agendamento atrelado a ele`
- [ ] `postal-code-not-found` mostra `ERROR_MESSAGES.cep_not_found`, o resto `cep_lookup_failed`
- [ ] Gate check passes: build

**Tests**: none
**Gate**: build

**Commit**: `feat(app): decide service deletion and CEP messages by problem slug`

---

### T18: Fechamento (AD-006, rastreabilidade, validação)

**What**: Registrar o AD-006 e o handoff no `STATE.md`, fechar a rastreabilidade do spec e escrever o `validation.md` do Verifier.
**Where**: `.specs/STATE.md`
**Depends on**: T17
**Reuses**: `scripts/validate_state.py`, `scripts/validate_spec.py`
**Requirement**: PD-01, PD-87

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [ ] AD-006 registrado, AD-004 marcado como parcialmente superado
- [ ] Rastreabilidade do spec em `Verified` com evidência
- [ ] `validation.md` com PASS e `file:line`, e `validate_state.py` com exit 0
- [ ] Gate check passes: full e build

**Tests**: none
**Gate**: full

**Commit**: `docs(specs): record AD-006 and verification for api-problem-details`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6

Phase 1:  T1 ------→ T2
Phase 2:  T3 ------→ T4 ------→ T5 ------→ T6
Phase 3:  T7 ------→ T8 ------→ T9 ------→ T10
Phase 4:  T11 -----→ T12 -----→ T13
Phase 5:  T14 -----→ T15 -----→ T16 -----→ T17
Phase 6:  T18
```

Execução sequencial, em linha na janela principal (sem sub-agentes: o usuário não os pediu).
