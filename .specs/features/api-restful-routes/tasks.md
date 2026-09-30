# Rotas da API em RFC 3986 Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/api-restful-routes/design.md`
**Status**: In Progress

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec. Guidelines found: none in the repo besides the existing suites; strong defaults applied. Memory note `backend-tests-run-in-docker` gives the runner.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Django views and URLconf (route/controller) | integration (Django test client) | Every route the task moves: happy path + every listed edge case + error paths, on the new path and method | `backend/<app>/tests.py`, `backend/hairmatch/test_routes.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput <app>'` |
| App services and screens (frontend-mobile) | none | - (decision inherited: manual UAT; type gate only) | - | `cd frontend-mobile && npx tsc --noEmit` |
| README and specs | none | - | - | build gate only |

## Gate Check Commands

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks with tests for one app | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput <app>'` |
| Full | Tasks that touch the URLconf | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput'` |
| Build | App tasks and the last task of a phase | full backend suite + `cd frontend-mobile && npx tsc --noEmit` |

---

## Execution Plan

```
Phase 1:  T1 ------> T2 ------> T3 ------> T4 ------> T5 ------> T6 ------> T7 ------> T8 ------> T9
Phase 2:  T10
Phase 3:  T11 ------> T12
Phase 4:  T13
```

---

## Task Breakdown

## Phase 1: Backend por app

### T1: Preferências: PUT/DELETE `users/me/preferences/{id}` e listas

**What**: Preferências: PUT/DELETE `users/me/preferences/{id}` e listas. Requisitos: RT-18 a RT-22, RT-60 a RT-62.
**Where**: `preferences/` (modify)
**Depends on**: -
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [x] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [x] Gate check passes
- [x] Test count: >= baseline, none removed or skipped

**Tests**: integration
**Gate**: quick

**Commit**: `feat(api): move preference routes to REST paths`

---

### T2: Avaliações: `reviews` e `hairdressers/{id}/reviews`

**What**: Avaliações: `reviews` e `hairdressers/{id}/reviews`. Requisitos: RT-23 a RT-26.
**Where**: `review/` (modify)
**Depends on**: T1
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [x] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [x] Gate check passes
- [x] Test count: >= baseline, none removed or skipped

**Tests**: integration
**Gate**: quick

**Commit**: `feat(api): move review routes to REST paths`

---

### T3: Disponibilidade: `availabilities` e `hairdressers/{id}/availabilities`, PUT vira PATCH

**What**: Disponibilidade: `availabilities` e `hairdressers/{id}/availabilities`, PUT vira PATCH. Requisitos: RT-27 a RT-32.
**Where**: `availability/` (modify)
**Depends on**: T2
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [x] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [x] Gate check passes
- [x] Test count: >= baseline, none removed or skipped

**Tests**: integration
**Gate**: quick

**Commit**: `feat(api): move availability routes to REST paths`

---

### T4: Agenda: `agenda`, `agenda/{id}` e `hairdressers/{id}/agenda`

**What**: Agenda: `agenda`, `agenda/{id}` e `hairdressers/{id}/agenda`. Requisitos: RT-33 a RT-36.
**Where**: `agenda/` (modify)
**Depends on**: T3
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [x] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [x] Gate check passes
- [x] Test count: >= baseline, none removed or skipped

**Tests**: integration
**Gate**: quick

**Commit**: `feat(api): move agenda routes to REST paths`

---

### T5: Serviços: `services`, `services/{id}` e `hairdressers/{id}/services`

**What**: Serviços: `services`, `services/{id}` e `hairdressers/{id}/services`. Requisitos: RT-37 a RT-42.
**Where**: `service/` (modify)
**Depends on**: T4
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [x] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [x] Gate check passes
- [x] Test count: >= baseline, none removed or skipped

**Tests**: integration
**Gate**: quick

**Commit**: `feat(api): move service routes to REST paths`

---

### T6: Reservas: `reservations`, `customers/{id}/reservations` e `available-slots` por GET

**What**: Reservas: `reservations`, `customers/{id}/reservations` e `available-slots` por GET. Requisitos: RT-43 a RT-48, RT-63, RT-64, RT-83.
**Where**: `reserve/` (modify)
**Depends on**: T5
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [x] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [x] Gate check passes
- [x] Test count: >= baseline, none removed or skipped

**Tests**: integration
**Gate**: quick

**Commit**: `feat(api): move reservation routes to REST paths`

---

### T7: Chatbot: `chatbot/webhook`

**What**: Chatbot: `chatbot/webhook`. Requisitos: RT-49, RT-76.
**Where**: `chatbot/` (modify)
**Depends on**: T6
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [x] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [x] Gate check passes
- [x] Test count: >= baseline, none removed or skipped

**Tests**: integration
**Gate**: quick

**Commit**: `feat(api): rename the chatbot webhook route`

---

### T8: Conta e sessão: `users`, `auth/session`, `users/me`, `users/me/password`; remove `user/<email>`

**What**: Conta e sessão: `users`, `auth/session`, `users/me`, `users/me/password`; remove `user/<email>`. Requisitos: RT-01 a RT-11, RT-56 a RT-58.
**Where**: `users/` (modify)
**Depends on**: T7
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [x] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [x] Gate check passes
- [x] Test count: >= baseline, none removed or skipped

**Tests**: integration
**Gate**: quick

**Commit**: `feat(api): move account and session routes to REST paths`

---

### T9: Busca, home, profissional, CEP e sugestão de descrição

**What**: Busca, home, profissional, CEP e sugestão de descrição. Requisitos: RT-12 a RT-17, RT-55, RT-59, RT-65, RT-82.
**Where**: `users/` (modify)
**Depends on**: T8
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [x] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [x] Gate check passes
- [x] Test count: >= baseline, none removed or skipped

**Tests**: integration
**Gate**: quick

**Commit**: `feat(api): move search, home and lookup routes to REST paths`

---

## Phase 2: Tabela de rotas

### T10: Tabela de rotas: `urls.py` raiz e testes RT-50, 52 a 54, 80, 81

**What**: Tabela de rotas: `urls.py` raiz e testes RT-50, 52 a 54, 80, 81. Requisitos: RT-50 a RT-54, RT-80, RT-81.
**Where**: `hairmatch/` (modify)
**Depends on**: T9
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [x] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [x] Gate check passes
- [x] Test count: >= baseline, none removed or skipped

**Tests**: integration
**Gate**: full

**Commit**: `test(api): assert the resolved routes match the route table`

---

## Phase 3: App

### T11: App: refresh e exclusão por path exato

**What**: App: refresh e exclusão por path exato. Requisitos: RT-71 a RT-73, RT-75.
**Where**: `frontend-mobile/services/axios-instance.ts` (modify)
**Depends on**: T10
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [x] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [x] Gate check passes
- [x] Test count: >= baseline, none removed or skipped

**Tests**: none
**Gate**: build

**Commit**: `refactor(app): match session refresh exclusions by exact path`

---

### T12: App: serviços e telas nas rotas novas

**What**: App: serviços e telas nas rotas novas. Requisitos: RT-70, RT-74, RT-75.
**Where**: `frontend-mobile/services/` (modify)
**Depends on**: T11
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [x] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [x] Gate check passes
- [x] Test count: >= baseline, none removed or skipped

**Tests**: none
**Gate**: build

**Commit**: `feat(app): call the REST routes`

---

## Phase 4: Documentação

### T13: README (webhook) e AD-007

**What**: README (webhook) e AD-007. Requisitos: RT-77.
**Where**: `README.md` (modify)
**Depends on**: T12
**Reuses**: Views existentes; `problems.py`

**Done when**:

- [ ] Rotas e métodos da tabela respondem com a regra de negócio da rota antiga
- [ ] Gate check passes
- [ ] Test count: >= baseline, none removed or skipped

**Tests**: none
**Gate**: build

**Commit**: `docs(api): document the route table and the webhook change`

---
