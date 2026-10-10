# Nota do cliente Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/customer-rating/spec.md`
**Context**: `.specs/features/customer-rating/context.md`
**Design**: `.specs/features/customer-rating/design.md`
**Status**: Draft (aguardando aprovação para Execute)
**Branch**: criar a partir de `develop` no início do Execute (por exemplo, `104-dar-nota-para-o-cliente`).

**Pré-requisitos do Execute:**
- Os testes do backend rodam dentro do container `hairmatch_backend` (memória `backend-tests-run-in-docker`). Se der `could not translate host name "db"`, rodar `docker start hairmatch_db`.
- Nenhuma env var nova e nenhuma dependência nova.
- **Feature `external-appointment` (#113)**: está planejada em paralelo e mexe nos mesmos arquivos da agenda (ver Risks no design). No início do Execute, conferir em `git log develop` se ela já entrou. Se entrou, T7, T11 e T12 partem do código dela: o modal fica em `app/(app)/hairdresser/agenda/index.tsx`, o `useFocusEffect` já existe, e o serializer já tem `title` e o item externo.
- Os arquivos não commitados de antes (`frontend-mobile/.env.example`, `frontend-mobile/services/axios-instance.ts`, `.specs/LESSONS.md`, `.specs/lessons.json`, `docs/`) ficam fora dos commits desta feature.

**Ordem que mantém a suíte verde a cada commit:**
1. As Phases 1 e 2 são do backend, e cada task traz os próprios testes.
2. As Phases 3 e 4 são do app, que só depende de rotas que já existem a partir da Phase 2.
3. A Phase 5 fecha com a documentação e o UAT.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas:
> - `.github/workflows/hairmatch-backend-test.yml`: `coverage run manage.py test`, sem limite mínimo.
> - `backend/review/tests.py:23-168` (`ReviewsTestCase`: cadastro pela API + `activate_account` + login com `APIClient`) e `backend/review/tests.py:709-` (`ReviewSessionTest`).
> - `backend/hairmatch/problem_testing.py:10` (`assert_problem`), `backend/hairmatch/test_problems.py:37` (contagem do catálogo) e `backend/hairmatch/test_routes.py` (Route Table).
> - `backend/agenda/tests.py` e `backend/users/tests.py` (exclusão de conta).
> - `frontend-mobile`: sem testes, por decisão herdada do #106, do #139 e do #141.
>
> Strong defaults aplicados nas camadas de backend.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: modelo e migrações de `users` (`User.rating`, cadastro) | integration | CRT-21 a CRT-23 e CRT-27: tipo float, migração de dados por relação, cadastro de cliente (e-mail e Google) com `null`, cabeleireiro com 5, JSON numérico | `backend/users/tests.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput users'` |
| Backend: modelo `CustomerRating` | integration | Constraint de 1 a 5, unicidade da reserva e os três `on_delete` (CRT-24 a CRT-26) pelos caminhos reais (`RemoveReserve`, `DELETE /api/users/me`) | `backend/review/tests.py` (`CustomerRatingModelTest`) | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput review'` |
| Backend: domínio (`review/customer_ratings.py`) | integration | Todos os ramos: média com 2 casas, `IntegrityError` → `review-exists`, lock (`FOR UPDATE` antes do `INSERT`), corrida real em `TransactionTestCase`, `service_end` com `start_time` nulo e no limite exato | `backend/review/tests.py` (`RecordCustomerRatingTest`, `CustomerRatingRaceTest`) | idem (review) |
| Backend: views de `review` (rotas novas) | integration | Cada rota: happy path + cada status de erro do spec (400/401/403/404/405/409) + "nenhuma linha alterada" onde o spec exige + a ordem de validação (CRT-17) | `backend/review/tests.py` (`CreateCustomerRatingTest`, `ListCustomerRatingsTest`) | idem (review) |
| Backend: agenda | integration | CRT-36 a CRT-38: campos novos com e sem reserva, avaliação presente e ausente, número constante de queries | `backend/agenda/tests.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput agenda'` |
| Backend: catálogo e rotas (`hairmatch/`) | unit | Contagem de slugs (40), título e status do slug novo, Route Table igual ao URLconf | `backend/hairmatch/test_problems.py`, `backend/hairmatch/test_routes.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput hairmatch'` |
| App (`frontend-mobile`) | none | `npx tsc --noEmit` sem erro novo + roteiro de UAT do T18 | - | App |
| Documentação | none | Revisão | - | - |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas com testes de um app só | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput <app>'` |
| Full | Tarefas com migração ou URLconf, e o fim de cada fase de backend | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput && coverage report -m'` |
| App | Tarefas do `frontend-mobile` | `cd frontend-mobile && npx tsc --noEmit` |
| Build | T18 (fim da feature) | Full + App + o roteiro de UAT |

> **Baseline de testes do backend:** `git grep -c "def test_"` em `fbf1d08` conta **724**:
> - `users` 384, `hairmatch` 100 (`tests.py` 44 + `test_problems.py` 47 + `test_routes.py` 9);
> - `availability` 55, `reserve` 45, `service` 40, `review` 35, `agenda` 23, `chatbot` 23, `preferences` 19.
>
> Nenhuma tarefa reduz esses números. O T1 confirma a baseline rodando a suíte antes de qualquer mudança.

> **Gate do app:** antes do T8, gravar a saída atual de `npx tsc --noEmit` como baseline. O gate passa quando nenhuma tarefa acrescenta erro novo.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend, dados

```
T1 → T3
T2 → T3
```

### Phase 2: Backend, API e agenda

```
T4 → T5 → T6
T7
```

### Phase 3: App, base

```
T8 → T11 → T12
T9
T10
```

### Phase 4: App, telas

```
T13 → T14
T15 → T16
```

### Phase 5: Documentação e verificação ponta a ponta

```
T17 → T18
```

---

## Task Breakdown

### Phase 1: Backend, dados (tarefas)

#### T1: `User.rating` vira float, e o cliente nasce sem nota

**What**:
- Trocar `User.rating` por `FloatField(blank=True, null=True, default=5)`.
- Criar a migração de schema `0012_alter_user_rating` e a de dados `0013_null_customer_ratings`. A de dados faz `RunPython` com `User.objects.filter(customer__isnull=False).update(rating=None)`, e o reverse grava 5.
- Em `_create_role_profile` (`users/views.py:394`), gravar `rating=None` quando cria um `Customer`.
**Where**: `backend/users/models.py`
**Depends on**: None
**Reuses**: o padrão de migração de dados de `backend/users/migrations/0009_dedupe_user_phone.py`
**Requirement**: CRT-20, CRT-21, CRT-22, CRT-23, CRT-27

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Antes de mudar qualquer coisa, a suíte inteira passa com 724 testes (baseline). Executados: 722 OK (o `git grep -c "def test_"` conta 724; os dois números são acompanhados).
- [x] Teste: um cliente cadastrado por e-mail/senha e outro pelo Google têm `rating is None`, e um cabeleireiro tem `rating == 5` (CRT-21).
- [x] Teste: a função da migração de dados, rodada sobre um cliente com 5 e um cabeleireiro com 4.5, deixa `None` e 4.5 (CRT-22). Um cliente com `role` em maiúsculas também vira `None`.
- [x] Teste: `GET /api/users/me` do cliente devolve `"rating": null`. Com `rating=4.33` gravado, devolve o número `4.33`, nunca a string (CRT-23).
- [x] Teste: `PATCH /api/users/me` com `rating: 1` não altera o valor (CRT-27). Se já existir teste equivalente, acrescentar a asserção para o cliente com `null`.
- [x] Os testes de `RatingIsNotUserSettableTest` que esperavam 5 para o cliente passam a esperar `None` (CRT-21). O payload com `rating` continua, então eles ainda provam que o corpo é ignorado.
- [x] O gate Full passa, com `makemigrations --check` limpo.
- [x] Contagem: `users` ≥ 384 + 5. Suíte: 727 OK.

**Tests**: integration
**Gate**: full

**Commit**: `feat(users): store the rating as a float and start customers unrated`

---

#### T2: Modelo `CustomerRating`

**What**: Criar o modelo `CustomerRating` do design, com a migração `review/0004_customerrating`:
- FK `'reserve.Reserve'` por string, `OneToOne`, `SET_NULL`, `related_name='customer_rating'`;
- `customer` com `CASCADE` e `hairdresser` com `SET_NULL`;
- `rating` com `CheckConstraint` de 1 a 5;
- `comment` e `created_at`.
**Where**: `backend/review/models.py`
**Depends on**: None
**Reuses**: o estilo de `Review` em `backend/review/models.py`
**Requirement**: CRT-06, CRT-24, CRT-25, CRT-26

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: gravar `rating=0` ou `rating=6` direto no ORM levanta `IntegrityError`.
- [x] Teste: uma segunda linha com a mesma reserva levanta `IntegrityError`, e duas linhas com `reservation=None` convivem (CRT-06).
- [x] Teste: `DELETE /api/reservations/{id}` de uma reserva avaliada mantém a avaliação com `reservation=None`, sem mudar `User.rating` (CRT-24).
- [x] Teste: `DELETE /api/users/me` do cabeleireiro autor mantém a avaliação com `hairdresser=None` e `User.rating` do cliente igual (CRT-25).
- [x] Teste: `DELETE /api/users/me` do cliente apaga as avaliações dele (CRT-26).
- [x] Nenhum import circular: `python manage.py check` passa.
- [x] O gate Full passa, com `makemigrations --check` limpo.
- [x] Contagem: `review` ≥ 35 + 5 (41). Suíte: 733 OK.

**Tests**: integration
**Gate**: full

**Commit**: `feat(review): add the customer rating model`

---

#### T3: Serviço de domínio `record_customer_rating`

**What**: Criar `review/customer_ratings.py` com `service_end(reservation)` e `record_customer_rating(hairdresser, reservation, rating, comment)`:
- uma transação;
- `select_for_update` no `User` do cliente;
- `create` dentro de um savepoint, em que o `IntegrityError` vira `Problem('review-exists')`;
- `Avg` arredondado para 2 casas e gravado em `User.rating`.
**Where**: `backend/review/customer_ratings.py`
**Depends on**: T1, T2
**Reuses**: `calculate_end_time` (`backend/reserve/views.py:244`), `Problem` (`backend/hairmatch/problems.py:67`)
**Requirement**: CRT-02, CRT-06, CRT-18, CRT-19, CRT-20

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: notas 5, 4 e 4 deixam `User.rating == 4.33`, e uma nota só (3) deixa `3.0` (CRT-18).
- [x] Teste: um cliente sem avaliação continua com `None` depois que outro cliente é avaliado (CRT-20).
- [x] Teste: chamar a função de novo para uma reserva já avaliada levanta `Problem` com o slug `review-exists`. O total de linhas e `User.rating` não mudam, e a transação de fora continua usável (CRT-06).
- [x] Teste: com `CaptureQueriesContext`, um `SELECT … FOR UPDATE` em `users_user` vem antes do `INSERT` em `review_customerrating` (CRT-19).
- [x] Teste (`TransactionTestCase`): duas threads com `threading.Barrier` avaliam reservas diferentes do mesmo cliente (5 e 1), e no fim `User.rating == 3.0` (CRT-19).
- [x] Teste: `service_end` devolve `start_time + duration` e devolve `None` com `start_time` nulo (CRT-02).
- [x] O gate Quick (review) passa.
- [x] Contagem: `review` ≥ 40 + 6 (49). Suíte: 741 OK. Sem o `select_for_update`, o teste de corrida falha (5.0 ou 1.0 em vez de 3.0).

**Tests**: integration
**Gate**: quick

**Commit**: `feat(review): record a customer rating and refresh the average`

---

### Phase 2: Backend, API e agenda (tarefas)

#### T4: Slug `service-not-finished`

**What**:
- Acrescentar `'service-not-finished': (409, 'Service not finished')` ao `CATALOG`.
- Atualizar o teste de contagem para 40.
- Acrescentar a linha do slug ao catálogo do spec `.specs/features/api-problem-details/spec.md`, com o texto pt-BR "O atendimento ainda não terminou.".
**Where**: `backend/hairmatch/problems.py`
**Depends on**: None
**Reuses**: as linhas vizinhas `review-exists` e `slot-unavailable`
**Requirement**: CRT-53

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: `test_catalog_has_the_40_slugs_of_the_spec` passa, e `problem_response(request, 'service-not-finished', …)` devolve status 409 e o título "Service not finished".
- [x] A linha está no catálogo do spec `api-problem-details`, na mesma ordem do `CATALOG`.
- [x] O gate Quick (hairmatch) passa.
- [x] Contagem: `hairmatch` ≥ 100 + 1 (101 executados no gate Quick).

**Tests**: unit
**Gate**: quick

**Commit**: `feat(api): add the service-not-finished problem type`

---

#### T5: `POST /api/customer-ratings` (RT-86)

**What**:
- Criar a view `CustomerRatingCollection.post` com a ordem do design: autenticação, JSON, validação de todos os campos, 404, 403, 409 duplicado, 409 não terminado e `record_customer_rating`, que responde 201 `{data}`.
- Registrar `path('customer-ratings', …)` em `review/urls.py`.
- Acrescentar `('POST', 'customer-ratings')  # RT-86` ao `ROUTE_TABLE` e a linha RT-86 à Route Table do spec `api-restful-routes`.
**Where**: `backend/review/views.py`
**Depends on**: T4, T3
**Reuses**: `authenticated_hairdresser`, `json_object`, `missing_field_errors`, `body_error`, `validation_problem`, `problem_response`, `_is_id`, `MIN_RATING`/`MAX_RATING`; T3 (`record_customer_rating`, `service_end`)
**Requirement**: CRT-01, CRT-02, CRT-03, CRT-04, CRT-05, CRT-06, CRT-07, CRT-08, CRT-09, CRT-10, CRT-11, CRT-12, CRT-13, CRT-14, CRT-15, CRT-16, CRT-17, CRT-54, CRT-55

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: o happy path devolve 201 com `{data: {id, reservation, rating, comment, created_at}}`, e a linha tem o cliente e o cabeleireiro da reserva (CRT-01).
- [x] Teste: uma reserva que termina exatamente agora é aceita; o `timezone.now` é fixado com `mock.patch` (CRT-02).
- [x] Teste: uma reserva que termina 1 minuto no futuro, ou que começou mas não terminou, devolve 409 `service-not-finished` sem linha nova (CRT-03).
- [x] Teste: `start_time=None` devolve 409 `service-not-finished` (CRT-04).
- [x] Teste: uma segunda avaliação devolve 409 `review-exists`, com a avaliação e `User.rating` iguais (CRT-05).
- [x] Teste: com a pré-checagem contornada por `mock.patch` (o `exists` devolve `False`), o `IntegrityError` vira 409 `review-exists` e nunca 500 (CRT-06).
- [x] Testes de autorização:
  - a reserva de outro cabeleireiro devolve 403 `forbidden` (CRT-07);
  - um id inexistente devolve 404 `not-found` (CRT-08);
  - sem cookie, 401 `invalid-session` (CRT-09);
  - uma sessão de cliente devolve 403 `hairdresser-required` (CRT-10).
- [x] Testes de validação:
  - `rating` com valor 4.5, `"5"`, `true`, 0, 6 ou ausente devolve 400 com `#/rating` (CRT-11);
  - `reservation` ausente ou `"abc"` devolve 400 com `#/reservation` (CRT-12);
  - `comment` com 501 caracteres ou o número 7 devolve 400 com `#/comment`, e 500 caracteres são aceitos (CRT-13);
  - `comment` ausente, `null` ou `"   "` vira `null`, e `"  ok  "` vira `"ok"` (CRT-14);
  - `rating` e `reservation` inválidos juntos devolvem 2 itens (CRT-15);
  - o corpo `[]` devolve 400 `malformed-request` (CRT-16);
  - uma entrada inválida para uma reserva inexistente devolve 400, e não 404 (CRT-17).
- [x] Teste: `GET`, `PUT` e `DELETE` em `/api/customer-ratings` devolvem 405 `method-not-allowed` com `Allow: POST, OPTIONS` (CRT-55).
- [x] `test_routes.py` passa com a RT-86, e a linha está no spec `api-restful-routes` (CRT-54).
- [x] O gate Full passa.
- [x] Contagem: `review` ≥ 46 + 20 (69). Suíte: 762 OK.
- [x] Edge case: avaliar, cancelar a reserva e reservar de novo o mesmo horário deixa avaliar a reserva nova (201), e a média conta as duas (CRT-24). Commit de teste à parte, depois do T7.

**Tests**: integration
**Gate**: full

**Commit**: `feat(review): let hairdressers rate the customer of a finished reservation`

---

#### T6: `GET /api/customers/{id}/ratings` (RT-87)

**What**:
- Criar a view `CustomerRatingsByCustomer.get` e o `CustomerRatingSerializer`, que monta `{id, rating, comment, created_at, service_name, hairdresser_name}`.
- Registrar `path('customers/<int:customer_id>/ratings', …)`.
- Acrescentar `('GET', 'customers/{id}/ratings')  # RT-87` ao `ROUTE_TABLE` e a linha RT-87 ao spec `api-restful-routes`.
**Where**: `backend/review/views.py`
**Depends on**: T5
**Reuses**: `authenticated_user`, `forbidden`, `problem_response`; o padrão de `ListReserve` (`backend/reserve/views.py:148-159`)
**Requirement**: CRT-28, CRT-29, CRT-30, CRT-31, CRT-32, CRT-33, CRT-34, CRT-35, CRT-54, CRT-55

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: com 2 avaliações de cabeleireiros diferentes, o cliente recebe `count: 2` e 2 itens, os mais recentes primeiro (CRT-28).
- [x] Teste: cada cabeleireiro recebe `count: 2`, `average` igual ao da média geral e só o item que escreveu (CRT-29).
- [x] Teste: outro cliente recebe 403 `forbidden` (CRT-30), um id inexistente recebe 404 `not-found` (CRT-31), e sem sessão a resposta é 401 `invalid-session` (CRT-32).
- [x] Teste: os campos de cada item. Depois de apagar a reserva, `service_name` é `null`. Depois de apagar a conta do autor, `hairdresser_name` é `null` (CRT-33).
- [x] Teste: um cliente sem avaliações recebe `{average: null, count: 0, ratings: []}` (CRT-34).
- [x] Teste: `average` é igual a `User.rating` gravado (CRT-35).
- [x] Teste: `POST /api/customers/{id}/ratings` devolve 405 com `Allow: GET, HEAD, OPTIONS` (CRT-55).
- [x] `test_routes.py` passa com a RT-87 (CRT-54).
- [x] O gate Full passa.
- [x] Contagem: `review` ≥ 66 + 9 (79). Suíte: 772 OK.
- [x] Edge case: um cliente pendente (`is_active=False`) recebe 200 `{average: null, count: 0, ratings: []}` para cabeleireiro e 403 para outro cliente. Commit de teste à parte, depois do T7.

**Tests**: integration
**Gate**: full

**Commit**: `feat(review): list the ratings a customer received`

---

#### T7: Agenda expõe a reserva, a nota e a avaliação

**What**:
- No `ListAgenda`, buscar as reservas com `select_related('customer__user', 'customer_rating')` e pôr no contexto `ratings_count_by_customer`, que vem de uma query agrupada.
- No `AgendaSerializer`, acrescentar `reservation_id` e `customer_rating`.
- Em `SimpleUserSerializer`, acrescentar `rating`; em `SimpleCustomerSerializer`, acrescentar `ratings_count`.
**Where**: `backend/agenda/serializers.py`
**Depends on**: T2
**Reuses**: o `reserve_map` existente em `backend/agenda/views.py:96-123`
**Requirement**: CRT-36, CRT-37, CRT-38

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: um item com reserva avaliada traz `reservation_id`, `customer.user.rating`, `customer.ratings_count` e `customer_rating: {rating, comment}`. Um item com reserva não avaliada traz `customer_rating: null` (CRT-36).
- [x] Teste: um item sem reserva traz `reservation_id: null`, `customer: null` e `customer_rating: null` (CRT-37).
- [x] Teste: `assertNumQueries` mede o mesmo número com 1 e com 5 reservas avaliadas (CRT-38).
- [x] Os testes atuais de `agenda` continuam passando sem alteração de asserção, porque os campos antigos não mudam.
- [x] O gate Full passa (fim da fase de backend).
- [x] Contagem: `agenda` ≥ 23 + 3 (26). Suíte: 775 OK. Sem o `select_related('customer_rating')`, o teste de queries falha (11 != 7).

**Tests**: integration
**Gate**: full

**Commit**: `feat(agenda): expose the reservation and the customer rating in the agenda`

---

### Phase 3: App, base (tarefas)

#### T8: Types, service e formatação da nota

**What**:
- Criar `models/CustomerRating.types.ts` (`CustomerRatingRequest`, `CustomerRating`, `CustomerRatingsSummary`).
- Estender `models/Agenda.types.ts` com os campos do backend e os do `AgendaEvent`.
- Criar `services/customer-rating.service.ts` com `createCustomerRating` e `getCustomerRatings`.
- Criar `utils/rating.ts` com `formatCustomerRating(average, count)`, que devolve "Sem avaliações" ou `"4.3 (3)"`.
**Where**: `frontend-mobile/services/customer-rating.service.ts`
**Depends on**: None
**Reuses**: `frontend-mobile/services/service.service.ts:5-18`, `frontend-mobile/services/axios-instance.ts`
**Requirement**: CRT-50, CRT-51, CRT-56, CRT-57

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] A baseline de `npx tsc --noEmit` está gravada antes da mudança: exit 0, sem nenhuma linha de saída.
- [x] As funções seguem o padrão `try/await axiosInstance…/return response.data/catch → console.error + throw`.
- [x] `formatCustomerRating(null, 0)` devolve "Sem avaliações", e `formatCustomerRating(4.33, 3)` devolve "4.3 (3)". Conferido no Node com o arquivo transpilado (`4.0 (1)`, `4.5 (2)` e `13/3` → `4.3 (3)` também). A tela fica para o UAT do T18.
- [x] O gate App passa sem erro novo (`tsc` exit 0, `eslint` sem erro nos arquivos tocados).

**Tests**: none
**Gate**: app

**Commit**: `feat(app): add the customer rating types and service`

---

#### T9: Slug `service-not-finished` no app

**What**: Acrescentar `service-not-finished` à união `ProblemSlug` e a `PROBLEM_MESSAGES`, com o texto "O atendimento ainda não terminou.".
**Where**: `frontend-mobile/utils/api-problem.ts`
**Depends on**: None
**Reuses**: as entradas `review-exists` e `slot-unavailable`
**Requirement**: CRT-48, CRT-53

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] O slug está na união e no `Record`, e o `tsc` acusaria se faltasse um dos dois (`Record<ProblemSlug, string>` exige a chave e recusa chave fora da união).
- [x] O gate App passa sem erro novo (`tsc` exit 0; `eslint` com os mesmos 3 warnings de antes e 0 erro).

**Tests**: none
**Gate**: app

**Commit**: `feat(app): translate the service-not-finished problem`

---

#### T10: Componente `StarRating` compartilhado

**What**:
- Extrair o `StarRating` inline de `app/(app)/customer/review/[id].tsx:36-53` para `components/StarRating/StarRating.tsx`, com as props `{rating, onChange?, size?}`. Sem `onChange`, ele é só leitura.
- A tela do cliente passa a importá-lo, sem mudança visual.
**Where**: `frontend-mobile/components/StarRating/StarRating.tsx`
**Depends on**: None
**Reuses**: o `StarRating` inline (FontAwesome `star`/`star-o`, `#FFC107`/`#CCCCCC`)
**Requirement**: CRT-43, CRT-58

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] A tela de review do cliente usa o componente, com os mesmos rótulos, tamanho 32, cores e margens. A conferência visual fica para o UAT do T18.
- [x] O modo só leitura não reage ao toque: sem `onChange`, cada estrela é um `View`, sem `TouchableOpacity`.
- [x] O gate App passa sem erro novo (`tsc` exit 0). O `eslint` da tela caiu de 1 erro (`react-hooks/static-components`, o `StarRating` criado no render) para 0, com os mesmos 9 warnings.

**Tests**: none
**Gate**: app

**Commit**: `refactor(app): share the star rating component`

---

#### T11: `useAgenda` guarda o cliente e a reserva, e recarrega no foco

**What**:
- Mapear `reservation_id`, `customer` (nome, `rating` e `ratings_count`) e `customer_rating` para o `AgendaEvent`.
- Trocar o `useEffect([userInfo])` por `useFocusEffect(useCallback(...))`.
- Expor `canRate(event)`, que vale `!!reservationId && !customerRating && now >= end`.
**Where**: `frontend-mobile/hooks/hairdresserHooks/useAgenda.ts`
**Depends on**: T8
**Reuses**: o padrão `useFocusEffect` de `frontend-mobile/hooks/customerHooks/useReserveDetails.ts:34-38`
**Requirement**: CRT-40, CRT-41, CRT-49

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Os campos novos chegam ao `AgendaEvent`, sem `any` novo: o `ev: any` do mapeamento virou `ev: AgendaItemResponse`.
- [x] A agenda busca de novo em todo foco (`useFocusEffect(useCallback(..., [hairdresserId]))`). A conferência ao voltar para a aba fica para o UAT do T18.
- [x] O gate App passa sem erro novo (`tsc` exit 0, `eslint` sem problema no hook).

**Tests**: none
**Gate**: app

**Commit**: `feat(app): keep the customer and reservation in the agenda`

---

#### T12: Modal da agenda com o cliente, a nota e o botão

**What**: No modal "Detalhes do Agendamento":
- mostrar o nome do cliente e `formatCustomerRating(rating, ratingsCount)`;
- mostrar "Sua avaliação: N★" quando já avaliado;
- mostrar o botão "Avaliar cliente" quando `canRate(event)`. Ele navega para `/(app)/hairdresser/rate-customer/{reservationId}`, com `customerName` nos `params`.
**Where**: `frontend-mobile/app/(app)/hairdresser/agenda.tsx`
**Depends on**: T11
**Reuses**: os estilos atuais do modal (`agenda.tsx:130-149`)
**Requirement**: CRT-39, CRT-40, CRT-41, CRT-42, CRT-56, CRT-57

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Um item sem reserva não mostra o bloco do cliente nem o botão: o bloco depende de `customer` e o botão de `canRate`, que exige `reservationId`.
- [x] O modal fecha antes do `router.push`, para não ficar sobre a tela de avaliação nem voltar com um `selectedEvent` velho.
- [x] O gate App passa sem erro novo (`tsc` exit 0). O `eslint` da tela segue com o único erro de antes (`react-hooks/static-components` do `Header`), e os warnings caíram de 3 para 2.
- Nota: o CRT-56 dá o exemplo "4.3 (3 avaliações)", mas o design e o roteiro do T18 usam "4.0 (1)". O modal usa a função compartilhada `formatCustomerRating`, com o rótulo "Nota do cliente: 4.3 (3)".

**Tests**: none
**Gate**: app

**Commit**: `feat(app): show the customer and the rate action in the agenda`

---

### Phase 4: App, telas (tarefas)

#### T13: Hook `useRateCustomer`

**What**: Criar o hook do design:
- lê `reservationId` e `customerName` de `useLocalSearchParams`, e usa "Cliente" quando o nome não vem;
- carrega o serviço e a data com `getReserveById`;
- guarda o estado de `rating`, `comment`, `confirmVisible` e `isSubmitting`;
- `submit` chama `createCustomerRating`, faz `router.back()` no sucesso e, no erro, abre o `errorModal` com `problemMessage(error, 'Não foi possível enviar a avaliação.')` sem limpar o formulário.
**Where**: `frontend-mobile/hooks/hairdresserHooks/useRateCustomer.ts`
**Depends on**: T8, T9
**Reuses**: `frontend-mobile/hooks/hairdresserHooks/useServiceManager.ts:57-61` (errorModal); T8 (service); T9 (slug)
**Requirement**: CRT-44, CRT-45, CRT-46, CRT-47, CRT-48

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `submit` não roda com `rating === 0` nem com `isSubmitting`.
- [ ] Sem `customerName` nos params, como num refresh do web, o hook devolve "Cliente" e não quebra.
- [ ] O erro não limpa a nota nem o comentário.
- [ ] O gate App passa sem erro novo.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): add the rate customer hook`

---

#### T14: Tela `rate-customer/[reservationId]`

**What**: Criar a tela com:
- o cabeçalho (cliente, serviço e data);
- o `StarRating` com "Ruim"/"Ótimo";
- o comentário multilinha com `maxLength={500}` e contador `n/500`;
- o botão "Enviar avaliação", desabilitado sem estrela e com "Enviando..." durante o envio;
- o `ConfirmationModal` com "A avaliação não pode ser alterada depois de enviada." e o `ErrorModal`.

Ocultar a rota nas tabs com `href: null` em `app/(app)/hairdresser/_layout.tsx` e criar `styles/hairdresser/RateCustomerStyles.ts`.
**Where**: `frontend-mobile/app/(app)/hairdresser/rate-customer/[reservationId].tsx`
**Depends on**: T13, T10
**Reuses**: `ConfirmationModal`, `ErrorModal`; T10 (`StarRating`); o layout de `frontend-mobile/app/(app)/customer/review/[id].tsx`
**Requirement**: CRT-43, CRT-44, CRT-45, CRT-46, CRT-47, CRT-48

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] A rota não aparece na barra de abas.
- [ ] O POST só sai depois de confirmar.
- [ ] O gate App passa sem erro novo.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): add the rate customer screen`

---

#### T15: Perfil do cliente mostra a média

**What**:
- `useCustomerProfile` passa a chamar `getCustomerRatings(customer.id)` em `useFocusEffect` e expõe `ratingLabel`: o resultado de `formatCustomerRating`, ou "Nota indisponível" se der erro.
- `customer/profile.tsx:47-50` mostra o `ratingLabel` no lugar do `rating` cru.
- O menu ganha o item "Avaliações recebidas".
**Where**: `frontend-mobile/hooks/customerHooks/useCustomerProfile.ts`
**Depends on**: T8
**Reuses**: T8 (`getCustomerRatings`, `formatCustomerRating`); `MenuItem`
**Requirement**: CRT-50, CRT-51, CRT-52

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Um cliente novo vê "Sem avaliações", e a falha da rota mostra "Nota indisponível" sem quebrar a tela.
- [ ] O gate App passa sem erro novo.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): show the customer's average rating in the profile`

---

#### T16: Tela "Avaliações recebidas" (P2)

**What**:
- Criar o hook `hooks/customerHooks/useReceivedRatings.ts` e a tela `app/(app)/customer/ratings.tsx`.
- A tela lista o `StarRating` só leitura, o comentário, o serviço, a data `DD/MM/YYYY` (dayjs `pt-br`) e o nome do cabeleireiro, ou "Cabeleireiro removido".
- O estado vazio mostra "Você ainda não recebeu avaliações.". O erro abre o `ErrorModal` com `problemMessage`.
- Registrar a rota com `href: null` em `customer/_layout.tsx`.
- O item "Avaliações recebidas" do perfil navega para ela.
**Where**: `frontend-mobile/app/(app)/customer/ratings.tsx`
**Depends on**: T15, T8, T10
**Reuses**: T8 (`getCustomerRatings`), T10 (`StarRating`), `ErrorModal`
**Requirement**: CRT-58, CRT-59, CRT-60

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Os itens aparecem na ordem da API, os mais recentes primeiro.
- [ ] O gate App passa sem erro novo.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): list the ratings a customer received`

---

### Phase 5: Documentação e verificação ponta a ponta (tarefas)

#### T17: Documentação

**What**:
- Em `docs/requisitos-status.md`, marcar RF23 como ✅ com a evidência (rotas, modelo e telas) e atualizar as observações de RF29 e RF30, onde a parte do cabeleireiro continua faltando.
- Atualizar a Handoff do `.specs/STATE.md`.
**Where**: `docs/requisitos-status.md`
**Depends on**: None
**Reuses**: o formato das linhas vizinhas
**Requirement**: CRT-54

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] RF23 aparece como ✅ no resumo e na tabela de Avaliações.
- [ ] `docs/requisitos-status.md` só entra no commit se o usuário autorizar, porque hoje o arquivo não é versionado. Senão, a mudança fica local e o motivo é anotado na Handoff.

**Tests**: none
**Gate**: none (documentação)

**Commit**: `docs(specs): record the customer rating delivery`

---

#### T18: UAT manual no web e no Android

**What**: Rodar o roteiro abaixo com o `docker compose up` e o app (web em `:8081` e Android). Os resultados vão para `validation.md`.

**Roteiro:**
1. **Cabeleireiro: agendamento passado.** Na agenda, o modal mostra o nome, "Sem avaliações" e o botão "Avaliar cliente".
2. **Avaliar.** Enviar sem estrela não é possível. Com 4 estrelas e um comentário, a confirmação aparece. Ao confirmar, a tela volta para a agenda, e o modal mostra "Sua avaliação: 4★" e "4.0 (1)".
3. **Agendamento futuro.** O modal não mostra o botão.
4. **Cliente: perfil.** Mostra "4.0 (1)", e "Avaliações recebidas" lista a avaliação.
5. **Cliente novo.** O perfil mostra "Sem avaliações".
6. **Review do cliente sobre o salão.** A tela continua igual (refactor do T10).
7. **Duplicado.** Um POST repetido por curl devolve 409.
**Where**: `.specs/features/customer-rating/validation.md`
**Depends on**: T17
**Reuses**: o roteiro de UAT do `email-confirmation` (T23)
**Requirement**: CRT-39, CRT-40, CRT-41, CRT-42, CRT-43, CRT-44, CRT-45, CRT-46, CRT-47, CRT-48, CRT-49, CRT-50, CRT-51, CRT-52, CRT-56, CRT-57, CRT-58, CRT-59, CRT-60

**Tools**:
- MCP: NONE
- Skill: `run`

**Done when**:
- [ ] Todos os passos foram conferidos pelo usuário no web e no Android.
- [ ] O gate Build passa.

**Tests**: none
**Gate**: build

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

Phase 1:  T1 → T3
          T2 → T3
Phase 2:  T4 → T5 → T6
          T7
Phase 3:  T8 → T11 → T12
          T9
          T10
Phase 4:  T13 → T14
          T15 → T16
Phase 5:  T17 → T18
```

Dependências entre fases (sempre para trás):
- T5 depende de T3;
- T7 depende de T2;
- T13 depende de T8 e T9;
- T14 depende de T10;
- T15 e T16 dependem de T8.

São 18 tasks, que se agrupam em 3 lotes:
- lote 1: Phases 1 e 2, com 7 tasks;
- lote 2: Phase 3, com 5 tasks;
- lote 3: Phases 4 e 5, com 6 tasks.

Por isso o Execute **oferece** sub-agents antes de começar.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: `User.rating` float | 1 campo + 2 migrações + 1 linha no cadastro | ⚠️ Coeso: a migração não existe sem o campo |
| T2: modelo `CustomerRating` | 1 modelo + migração | ✅ Granular |
| T3: `record_customer_rating` | 1 módulo, 2 funções | ✅ Granular |
| T4: slug | 1 entrada de catálogo + espelho no spec | ✅ Granular |
| T5: POST | 1 endpoint (+ rota e Route Table) | ✅ Granular |
| T6: GET | 1 endpoint + serializer (+ rota e Route Table) | ✅ Granular |
| T7: agenda | 1 serializer + contexto da view | ⚠️ Coeso: o contexto só existe para o serializer |
| T8: types e service | 1 service + types + 1 função utilitária | ⚠️ Coeso: o contrato da API no app |
| T9: slug no app | 1 arquivo | ✅ Granular |
| T10: `StarRating` | 1 componente + troca de import | ✅ Granular |
| T11: `useAgenda` | 1 hook | ✅ Granular |
| T12: modal da agenda | 1 tela | ✅ Granular |
| T13: `useRateCustomer` | 1 hook | ✅ Granular |
| T14: tela de avaliação | 1 tela + estilo + registro da rota | ✅ Granular |
| T15: perfil | 1 hook + 1 tela | ⚠️ Coeso: hook e tela do mesmo perfil |
| T16: lista P2 | 1 hook + 1 tela | ⚠️ Coeso: a tela não existe sem o hook |
| T17: docs | 1 arquivo | ✅ Granular |
| T18: UAT | verificação | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | início da Phase 1 | ✅ Match |
| T2 | None | início da Phase 1 | ✅ Match |
| T3 | T1, T2 | T1 → T3, T2 → T3 | ✅ Match |
| T4 | None | início da Phase 2 | ✅ Match |
| T5 | T4, T3 (T3 na Phase 1) | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | T2 (Phase 1) | sozinho na Phase 2 | ✅ Match |
| T8 | None | início da Phase 3 | ✅ Match |
| T9 | None | sozinho na Phase 3 | ✅ Match |
| T10 | None | sozinho na Phase 3 | ✅ Match |
| T11 | T8 | T8 → T11 | ✅ Match |
| T12 | T11 | T11 → T12 | ✅ Match |
| T13 | T8, T9 (Phase 3) | início da Phase 4 | ✅ Match |
| T14 | T13, T10 (T10 na Phase 3) | T13 → T14 | ✅ Match |
| T15 | T8 (Phase 3) | início da Phase 4 | ✅ Match |
| T16 | T15, T8, T10 (T8 e T10 na Phase 3) | T15 → T16 | ✅ Match |
| T17 | None | início da Phase 5 | ✅ Match |
| T18 | T17 | T17 → T18 | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Backend: modelo e migrações de `users` | integration | integration | ✅ OK |
| T2 | Backend: modelo `CustomerRating` | integration | integration | ✅ OK |
| T3 | Backend: domínio | integration | integration | ✅ OK |
| T4 | Backend: catálogo | unit | unit | ✅ OK |
| T5 | Backend: views de `review` + rotas | integration | integration | ✅ OK |
| T6 | Backend: views de `review` + rotas | integration | integration | ✅ OK |
| T7 | Backend: agenda | integration | integration | ✅ OK |
| T8 | App | none | none | ✅ OK |
| T9 | App | none | none | ✅ OK |
| T10 | App | none | none | ✅ OK |
| T11 | App | none | none | ✅ OK |
| T12 | App | none | none | ✅ OK |
| T13 | App | none | none | ✅ OK |
| T14 | App | none | none | ✅ OK |
| T15 | App | none | none | ✅ OK |
| T16 | App | none | none | ✅ OK |
| T17 | Documentação | none | none | ✅ OK |
| T18 | Verificação | none | none | ✅ OK |
