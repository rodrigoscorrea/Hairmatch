# Notificações push Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/push-notifications/spec.md`
**Context**: `.specs/features/push-notifications/context.md`
**Design**: `.specs/features/push-notifications/design.md`
**Status**: Approved. Execute em andamento (T1 a T19 no código; T20 a T23 são manuais e dependem do usuário).
**Branch**: a criar a partir de `develop`, com o nome `182-notificacoes-push`.

### Pré-requisitos do Execute

- **Testes do backend.** Rodam dentro do container `hairmatch_backend` (memória `backend-tests-run-in-docker`). Usam os fakes do Cognito e do SNS do `HairmatchTestRunner`, então não precisam do LocalStack.
- **Imagem do backend.** Nenhuma dependência Python nova: o `boto3` já está no `requirements.txt`. A imagem não precisa ser refeita.
- **Contratos já no planejamento** (AD-006 e AD-007):
  - As rotas RT-100 a RT-104 já estão na Route Table do `api-restful-routes/spec.md`. As tasks só as levam ao `ROUTE_TABLE`.
  - O slug `push-unavailable` já está na tabela do `api-problem-details/spec.md`.
- **Firebase.** O projeto Firebase (T20) é tarefa manual do usuário e só bloqueia o dev build (T21) e o UAT (T23). Ele pode ser feito a qualquer momento, em paralelo às outras fases.
- **UAT.** A T23 roda contra o ambiente de preview (Render), com a AWS real da T22. Ela precisa de um aparelho Android físico com Play Services e do dev build da T21. O E2E local (T19) usa o `docker compose up` completo, e o LocalStack só guarda as mensagens, sem entregar.

### Ordem que mantém a suíte verde a cada commit

1. A Phase 1 cria a base do backend (slug, modelos, SNS, LocalStack, mensagens e `notify`) sem nenhuma rota.
2. A Phase 2 liga as rotas e os eventos.
3. A Phase 3 é o app.
4. A Phase 4 é a verificação ponta a ponta, as tarefas manuais e o UAT.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas:
> - `.github/workflows/hairmatch-backend-test.yml`: `coverage run manage.py test`, sem mínimo.
> - `backend/review/tests.py:800`: `captureOnCommitCallbacks(execute=True)` para efeitos depois do commit.
> - `backend/review/tests.py` (`CustomerRatingRaceTest`): corrida com `TransactionTestCase`.
> - `backend/users/cognito_fake.py`: fake de serviço AWS com `fail_next`.
> - `backend/hairmatch/test_routes.py` e `backend/hairmatch/test_problems.py`: contratos.
> - `frontend-mobile`: sem testes, por decisão herdada da #106, da #118 e da #115. O gate é `npx tsc --noEmit` mais o UAT.
>
> Strong defaults aplicados nas camadas de backend.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: modelos `PushDevice` e `Alert` | integration | Token único (NOTIF-04), ordem padrão provada com `created_at` fora da ordem de inserção (NOTIF-39) e `CASCADE` a partir do `User`. | `backend/notifications/tests/test_models.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput notifications'` |
| Backend: `SnsService` | unit | Cada método com `botocore.stub.Stubber` no client real: parâmetros enviados (payload FCM v1, `data` só com strings, `channel_id`), mapeamento de erros (`EndpointDisabled`, `NotFound`, `PushUnavailable`), busca do ARN por nome com paginação e o log sem token nem ARN (NOTIF-77). | `backend/notifications/tests/test_sns.py` | idem |
| Backend: `messages` | unit | 1:1 com cada linha do catálogo do spec: título, corpo, destinatário, dados, `America/Manaus`, formato da nota e "estrela"/"estrelas". | `backend/notifications/tests/test_messages.py` | idem |
| Backend: `dispatch` | integration | NOTIF-19 a NOTIF-26 e NOTIF-72/73 com o `FakeSns` e `captureOnCommitCallbacks(execute=True)`: grava, publica, não publica sem commit, falha isolada, endpoint apagado e autor = destinatário. | `backend/notifications/tests/test_dispatch.py` | idem |
| Backend: views de aparelho e de alerta | integration | Cada critério de backend do spec: happy path, cada status de erro e "nenhuma linha mudou". A corrida do NOTIF-04 roda com `TransactionTestCase`. | `backend/notifications/tests/test_views.py` | idem |
| Backend: eventos nas views existentes | integration | NOTIF-28 a NOTIF-30, NOTIF-32/33, NOTIF-35/36, NOTIF-59 a NOTIF-62 e NOTIF-64 a NOTIF-66, pelas rotas reais e pelo `create_new_reserve`. Inclui o caso de falha (nenhum alerta) e o SNS falhando sem mudar o status da ação. | `backend/reserve/tests.py`, `backend/review/tests.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput reserve review notifications'` |
| Backend: exclusão de conta | integration | NOTIF-11 e NOTIF-46 pelo `DELETE /api/users/me`, com o `delete_endpoint` executado no commit. | `backend/notifications/tests/test_views.py` | `... test --noinput notifications users` |
| Backend: contratos (`test_routes.py`, `test_problems.py`) | unit | RT-100 a RT-104 em `ROUTE_TABLE`; 42 slugs em `CATALOG`. | `backend/hairmatch/` | `... test --noinput hairmatch` |
| Infra local (`docker/`) | none | Go/no-go manual da T4 com `curl` no LocalStack. | - | Ver T4 |
| App (`frontend-mobile`) | none | `npx tsc --noEmit` sem erro novo e o roteiro de UAT da T23. | - | App |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas com testes só de `notifications` ou só de `hairmatch` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput notifications hairmatch'` |
| Full | Tarefas que tocam modelo, URLconf, `users`, `reserve` ou `review`, e o fim das Phases 1 e 2 | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput && coverage report -m'` |
| App | Tarefas do `frontend-mobile` | `cd frontend-mobile && npx tsc --noEmit`, mais `npx eslint .` se o `eslint.config.js` estiver na branch |
| Infra | T4 | `docker compose -f docker/docker-compose.yml up -d localstack`, seguido do roteiro de `curl` da T4 |
| Build | T19 e T23 | Full + App + o roteiro da tarefa |

> **Baseline de testes do backend.** `git grep -c "def test_" -- backend` em `fb3d11a` conta **999**: `users` 469, `review` 159, `hairmatch` 104, `availability` 55, `reserve` 52, `agenda` 46, `service` 40, `favorite` 32, `chatbot` 23 e `preferences` 19. Nenhuma tarefa reduz esses números. Antes da T1, rodar o gate Full para confirmar a baseline.

> **Gate do app.** Antes da T13, registrar a saída atual de `npx tsc --noEmit` como baseline. O gate passa quando nenhuma tarefa acrescenta erro novo.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend: base

```
T1
T2 → T3 → T6
T3 → T4
T2 → T5 → T6
```

### Phase 2: Backend: rotas e eventos

```
T7 → T8
T7 → T9
T10
T11
T12
```

### Phase 3: App

```
T13 → T15 → T16
T14 → T15
T14 → T17 → T18
T16 → T17
```

### Phase 4: Verificação, tarefas manuais e UAT

```
T19
T20 → T21 → T23
T20 → T22 → T23
T19 → T23
```

---

## Task Breakdown

### Phase 1: Backend: base

### T1: Slug `push-unavailable` no catálogo

**What**: Acrescentar `'push-unavailable': (503, 'Push service unavailable')` ao `CATALOG` e atualizar o teste de tamanho do catálogo (41 → 42), mais um teste que gera o problem+json do slug.
**Where**: `backend/hairmatch/problems.py` (modify)
**Depends on**: None
**Reuses**: As linhas de `ai-service-unavailable` em `problems.py` e `test_problems.py`
**Requirement**: NOTIF-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `CATALOG` tem 42 slugs, e `test_catalog_has_the_42_slugs_of_the_spec` passa.
- [x] Um teste chama `problem_response(..., 'push-unavailable', ...)` e confere status 503, `title` e o `type` terminando em `/push-unavailable`.
- [x] Gate check passes: Quick.
- [x] Test count: baseline + 1 em `hairmatch`.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(api): add the push-unavailable problem`

---

### T2: App `notifications` com `PushDevice` e `Alert`

**What**: Criar o app Django `notifications`, registrá-lo em `INSTALLED_APPS` e criar os dois modelos do design, com a migração `0001_initial`.
**Where**: `backend/notifications/models.py` (new)
**Depends on**: None
**Reuses**: O formato do app `favorite`
**Requirement**: NOTIF-04, NOTIF-11, NOTIF-39, NOTIF-46

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `apps.py`, `models.py`, `migrations/0001_initial.py` (gerada) e o pacote `tests/` existem, e `notifications` está em `INSTALLED_APPS`.
- [x] Teste: um segundo `PushDevice` com o mesmo token levanta `IntegrityError`.
- [x] Teste: a ordem padrão de `Alert` é `-created_at, -id`, provada com um alerta antigo inserido depois de um novo.
- [x] Teste: apagar o `User` apaga os aparelhos e os alertas dele, e só os dele.
- [x] `makemigrations --check` limpo, e o gate Full passa.
- [x] Test count: baseline + os testes novos de `notifications`.

**Tests**: integration
**Gate**: full
**Commit**: `feat(notifications): add the push device and alert models`

---

### T3: `SnsService` e `FakeSns`

**What**: Criar o wrapper do SNS (`create_endpoint`, `delete_endpoint`, `publish`, `platform_application_arn`, `get_sns`/`reset_sns`), o `FakeSns` em memória e as settings `SNS_PLATFORM_APPLICATION_ARN` e `SNS_USE_FAKE`. O `CognitoResetMixin` passa a chamar `reset_sns()`.
**Where**: `backend/notifications/sns.py` (new)
**Depends on**: T2
**Reuses**: `backend/users/cognito.py`, `backend/users/cognito_fake.py`, `backend/hairmatch/test_runner.py`
**Requirement**: NOTIF-06, NOTIF-21, NOTIF-24, NOTIF-69, NOTIF-70, NOTIF-77

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Testes com `Stubber`:
  - `create_endpoint` chama `CreatePlatformEndpoint` sem `CustomUserData` e depois `SetEndpointAttributes` com `Enabled='true'` e o token;
  - `publish` envia `MessageStructure='json'` e um `GCM` com `fcmV1Message`, `notification` (título e corpo), `data` só com strings e `android.notification.channel_id == 'default'`.
- [ ] Testes de erro:
  - `EndpointDisabled` e `NotFound` viram `EndpointGone`;
  - outro `ClientError`, `EndpointConnectionError` e `ReadTimeoutError` viram `PushUnavailable`;
  - `delete_endpoint` de um ARN inexistente não levanta.
- [ ] Teste: com a setting vazia, o ARN vem da platform application `hairmatch-dev-fcm`, mesmo na segunda página de `ListPlatformApplications`, e com a setting preenchida o valor dela é usado.
- [ ] Teste com `assertLogs`: o log de falha tem a operação e o código, e não tem o token nem o ARN.
- [ ] O `FakeSns` registra criações, publicações e remoções. Ele tem `fail_next(operation, error)` e `disable(arn)`.
- [ ] Gate check passes: Quick.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(notifications): add the SNS service`

---

### T4: SNS no LocalStack

**What**: Ligar o SNS no LocalStack e criar a platform application de dev:
- `SERVICES: s3,ses,sns`;
- no init, `create-platform-application --name hairmatch-dev-fcm --platform GCM --region "${AWS_DEFAULT_REGION:-us-east-2}"` com `PlatformCredential` falsa, idempotente. A região é explícita para a platform application nascer na mesma região do backend;
- `SNS_PLATFORM_APPLICATION_ARN=${SNS_PLATFORM_APPLICATION_ARN:-}` no serviço do backend;
- a variável documentada no `.env.example`.

**Where**: `docker/localstack/init/01-resources.sh` (modify)
**Depends on**: T3
**Reuses**: O bloco do bucket S3 no mesmo script e o bloco do Cognito no compose
**Requirement**: NOTIF-68, NOTIF-69, NOTIF-71

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `docker compose up -d localstack` sobe saudável, e o log mostra a platform application criada.
- [ ] **Go/no-go:**
  1. `awslocal sns list-platform-applications --region us-east-2` lista `hairmatch-dev-fcm`;
  2. um `create-platform-endpoint` com um token falso devolve um ARN;
  3. um `publish --message-structure json` para ele é aceito;
  4. `curl "http://localhost:4566/_aws/sns/platform-endpoint-messages?region=us-east-2"` mostra a mensagem.

  Se algum passo falhar (licença sem SNS ou credencial recusada), PARAR e decidir com o usuário (design, Risks & Concerns).
- [ ] O backend no compose, com a variável vazia, resolve o ARN pelo nome. Conferir com `python manage.py shell -c "from notifications.sns import get_sns; print(get_sns().platform_application_arn)"`.

**Tests**: none
**Gate**: build
**Commit**: `feat(docker): run SNS on LocalStack with a dev FCM platform application`

---

### T5: Mensagens do catálogo

**What**: Criar `notifications/messages.py` com o `Message` e uma função por `kind` do catálogo, mais `format_rating`, `stars` e `local_date_time`.
**Where**: `backend/notifications/messages.py` (new)
**Depends on**: T2
**Reuses**: `backend/hairmatch/local_time.py` (`LOCAL_TIMEZONE`)
**Requirement**: NOTIF-25, NOTIF-27, NOTIF-28, NOTIF-32, NOTIF-35, NOTIF-59, NOTIF-60, NOTIF-64, NOTIF-65

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Um teste por `kind`: destinatário, `kind`, título e corpo **literais** do spec, e os `data`.
- [ ] Teste: uma reserva às 13:00 UTC sai como "09:00" (Manaus, UTC−4), e uma às 03:30 UTC do dia 2 sai como o dia 1 às "23:30".
- [ ] Teste: as notas 5.0, 4.5 e 1.0 saem como "5", "4,5" e "1", e 1 usa "estrela".
- [ ] Gate check passes: Quick.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(notifications): build the alert messages`

---

### T6: `notify`, `publish_alert` e `delete_endpoints`

**What**: Criar `notifications/dispatch.py` com:
- `notify(message, actor=None)`, que grava o alerta e agenda a publicação com `on_commit(robust=True)`;
- `publish_alert`, que publica em cada aparelho, trata o `EndpointGone` e engole qualquer outra falha;
- `delete_endpoints`.

**Where**: `backend/notifications/dispatch.py` (new)
**Depends on**: T3, T5
**Reuses**: `transaction.on_commit` como em `review/views.py:194`
**Requirement**: NOTIF-19, NOTIF-20, NOTIF-21, NOTIF-22, NOTIF-23, NOTIF-24, NOTIF-26, NOTIF-72, NOTIF-73, NOTIF-77

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Com `captureOnCommitCallbacks(execute=True)`:
  - `notify` grava 1 alerta não lido e publica 1 vez por aparelho do destinatário (2 aparelhos → 2 publicações), com `alert_id` e `kind` como strings;
  - sem aparelho, não publica.
- [ ] `notify` dentro de um `atomic()` que levanta não deixa alerta, e o fake não registra publicação.
- [ ] `notify(message, actor=message.recipient)` devolve `None` e não grava nada (NOTIF-26).
- [ ] Com `fail_next('publish', ...)` no primeiro aparelho:
  - o segundo recebe;
  - nenhuma exceção sai do bloco de commit;
  - o alerta continua gravado;
  - o log tem a falha.
- [ ] Com `disable(arn)`, a linha do aparelho é apagada, o fake registra o `delete_endpoint`, e o outro aparelho recebe.
- [ ] Teste: a publicação vai para o dono do aparelho no momento do commit, e não para o dono no momento do `notify` (NOTIF-73).
- [ ] Gate check passes: Full (fim da Phase 1).

**Tests**: integration
**Gate**: full
**Commit**: `feat(notifications): record alerts and publish them after the commit`

---

### Phase 2: Backend: rotas e eventos

### T7: `POST` e `DELETE /api/users/me/push-devices`

**What**: Criar `PushDeviceCollection.post` (RT-100) e `PushDeviceDetail.delete` (RT-101), com as rotas em `notifications/urls.py`, o `include` em `hairmatch/urls.py` (antes do catch-all) e as duas linhas no `ROUTE_TABLE`.
**Where**: `backend/notifications/views.py` (new)
**Depends on**: None (usa T2, T3 e T6 da Phase 1)
**Reuses**: `authenticated_user`, `json_object`, `validation_problem`, `body_error`, `problem_response`; o tratamento de `IntegrityError` de `record_customer_rating`
**Requirement**: NOTIF-01, NOTIF-02, NOTIF-03, NOTIF-04, NOTIF-05, NOTIF-06, NOTIF-07, NOTIF-08, NOTIF-09, NOTIF-10

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Testes de cada critério:
  - 201 com o `id` e 1 endpoint no fake;
  - 200 com o mesmo `id` e nenhum endpoint novo;
  - 201 ao trocar de conta, e a outra conta fica sem a linha;
  - 400 `#/token` para token ausente, não string, vazio depois de `strip()` e com 1025 caracteres (1024 passa);
  - 503 `push-unavailable` sem linha quando o fake falha;
  - 204 e o endpoint apagado no commit;
  - 404 para `id` de outra conta e inexistente;
  - 401 sem sessão, nos dois métodos;
  - 204 mesmo com `delete_endpoint` falhando.
- [ ] Corrida: dois `POST` simultâneos com o mesmo token deixam 1 linha (`TransactionTestCase` com `threading.Barrier`).
- [ ] `ROUTE_TABLE` tem RT-100 e RT-101, e o `test_routes` passa.
- [ ] Gate check passes: Full.

**Tests**: integration
**Gate**: full
**Commit**: `feat(notifications): register and remove a push device`

---

### T8: Endpoints apagados na exclusão da conta

**What**: Fazer `_delete_account_rows` coletar os `endpoint_arn` do usuário antes do `user.delete()`, e o `_delete_account` agendar `delete_endpoints(arns)` no `on_commit`.
**Where**: `backend/users/views.py` (modify)
**Depends on**: T7
**Reuses**: O padrão de `pictures` e `delete_stored_files` no mesmo trecho (`users/views.py:228`)
**Requirement**: NOTIF-11, NOTIF-46

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Teste: um usuário com 2 aparelhos e 3 alertas faz `DELETE /api/users/me`. As linhas somem, o fake registra 2 `delete_endpoint` depois do commit, e os aparelhos e alertas de outro usuário continuam.
- [ ] Teste: uma falha do Cognito que desfaz a exclusão não apaga nenhum endpoint.
- [ ] A docstring de `_delete_account_rows` cita os aparelhos.
- [ ] Gate check passes: Full.

**Tests**: integration
**Gate**: full
**Commit**: `feat(notifications): remove the push endpoints with the account`

---

### T9: `GET` e `PATCH` dos alertas

**What**: Criar `AlertCollection.get` (RT-102), `AlertCollection.patch` (RT-103) e `AlertDetail.patch` (RT-104), com as rotas e as linhas no `ROUTE_TABLE`.
**Where**: `backend/notifications/views.py` (modify)
**Depends on**: T7
**Reuses**: `authenticated_user`, `json_object`, `validation_problem`
**Requirement**: NOTIF-38, NOTIF-39, NOTIF-40, NOTIF-41, NOTIF-42, NOTIF-43, NOTIF-44, NOTIF-45

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Testes do `GET`:
  - 200 com o formato `{id, kind, title, body, data, read, created_at}`;
  - com 55 alertas, devolve os 50 mais novos na ordem do spec;
  - `unread_count` conta todos os não lidos, inclusive os fora dos 50;
  - nunca traz alertas de outra conta;
  - responde `{"alerts": [], "unread_count": 0}` sem alertas.
- [ ] Testes do `PATCH /{id}`:
  - `read: true` grava `read_at`, e `read: false` o limpa, com 200 e o alerta;
  - 404 para alerta de outra conta e inexistente;
  - 400 `#/read` para `read` ausente, `"true"` e `1`.
- [ ] Testes do `PATCH` da coleção:
  - `read: true` marca todos os do usuário e nenhum de outro, com 204;
  - `read: false` dá 400 `#/read` e não muda nada.
- [ ] 401 sem sessão nas três rotas.
- [ ] `ROUTE_TABLE` tem RT-102 a RT-104.
- [ ] Gate check passes: Full.

**Tests**: integration
**Gate**: full
**Commit**: `feat(notifications): list the alerts and mark them as read`

---

### T10: Notificar a nova reserva (N01)

**What**: Chamar `notify(reservation_created(reserve), actor=...)` dentro do `atomic()` de `CreateReserve` e de `create_new_reserve`.
**Where**: `backend/reserve/views.py` (modify)
**Depends on**: None (usa T6 da Phase 1)
**Reuses**: `notify` e `reservation_created`
**Requirement**: NOTIF-28, NOTIF-29, NOTIF-30

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Teste: `POST /api/reservations` com sucesso grava 1 alerta `reservation-created` para o usuário do cabeleireiro, com o texto do spec, e publica no aparelho dele.
- [ ] Teste: `create_new_reserve` faz o mesmo.
- [ ] Teste: 409 `slot-unavailable`, 409 `customer-schedule-conflict`, 400 e 404 não gravam alerta.
- [ ] Teste: com o fake do SNS falhando, o `POST` responde 201 e `create_new_reserve` devolve `success`.
- [ ] Gate check passes: Full.

**Tests**: integration
**Gate**: full
**Commit**: `feat(reserve): notify the hairdresser of a new reservation`

---

### T11: Notificar a review criada, editada e excluída (N11, N12)

**What**: Chamar `notify` em `CreateReview` (dentro do `atomic()`), em `UpdateReview` (`save` e `notify` num `atomic()` novo) e em `RemoveReview` (mensagem montada antes do `review.delete()`).
**Where**: `backend/review/views.py` (modify)
**Depends on**: None (usa T6 da Phase 1)
**Reuses**: `notify`, `review_created`, `review_updated`, `review_deleted`
**Requirement**: NOTIF-32, NOTIF-33, NOTIF-59, NOTIF-60, NOTIF-61, NOTIF-62

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Teste: criar, editar e excluir pela rota gravam, cada um, 1 alerta do `kind` certo para o cabeleireiro, com a nota no texto.
- [ ] Teste: 409 `review-exists`, 403, 404 e 400 não gravam alerta.
- [ ] Teste: `POST` e `DELETE` de foto (RT-90, RT-91) não gravam alerta.
- [ ] Teste: o `delete_stored_files` do `RemoveReview` continua rodando quando a publicação falha.
- [ ] Gate check passes: Full.

**Tests**: integration
**Gate**: full
**Commit**: `feat(review): notify the hairdresser of review changes`

---

### T12: Notificar a nota do cliente (N13, N14)

**What**: Chamar `notify` em `record_customer_rating`, `update_customer_rating` e `delete_customer_rating`, dentro do `atomic()` de cada uma. Na exclusão, a mensagem é montada antes do `delete()`.
**Where**: `backend/review/customer_ratings.py` (modify)
**Depends on**: None (usa T6 da Phase 1)
**Reuses**: `notify` e as mensagens `customer_rating_*`
**Requirement**: NOTIF-35, NOTIF-36, NOTIF-64, NOTIF-65, NOTIF-66

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Teste: `POST`, `PUT` e `DELETE /api/customer-ratings...` gravam, cada um, 1 alerta para o cliente, com o nome do cabeleireiro e a nota.
- [ ] Teste: 409 `review-exists`, 409 `service-not-finished`, 403, 404 e 400 não gravam alerta.
- [ ] Teste: a média do cliente (AD-010, AD-012) continua certa nos três casos.
- [ ] Gate check passes: Full (fim da Phase 2).

**Tests**: integration
**Gate**: full
**Commit**: `feat(review): notify the customer of rating changes`

---

### Phase 3: App

### T13: Dependência e configuração nativa

**What**: Fazer a configuração nativa do push:
- instalar `expo-notifications` com `npx expo install`;
- adicionar o plugin no `app.json`, com `defaultChannel: "default"`;
- criar o `app.config.js`, que aponta `android.googleServicesFile` para `process.env.GOOGLE_SERVICES_JSON ?? './google-services.json'`;
- listar `google-services.json` no `.gitignore` do app.

**Where**: `frontend-mobile/app.config.js` (new)
**Depends on**: None
**Reuses**: O `app.json` atual, que o `app.config.js` recebe como `config`
**Requirement**: NOTIF-13

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `npx expo config --type public` mostra o plugin e o `googleServicesFile`.
- [ ] A versão instalada é a do SDK 57, e as dependências nativas transitivas foram conferidas (memória `expo-web-smoke-needs-visible-tab`).
- [ ] O app web continua abrindo (`npx expo start --web`).
- [ ] Gate check passes: App.

**Tests**: none
**Gate**: build
**Commit**: `build(app): add expo-notifications and the FCM config`

---

### T14: Serviços, tipos e slug no app

**What**: Criar o seguinte:
- `services/push-device.service.ts`;
- `services/alert.service.ts`;
- `models/Alert.types.ts`;
- `'push-unavailable'` em `utils/api-problem.ts`, com o texto do catálogo.

**Where**: `frontend-mobile/services/alert.service.ts` (new)
**Depends on**: None
**Reuses**: `axiosInstance` e o formato de `favorite-hairdresser.service.ts`
**Requirement**: NOTIF-13, NOTIF-17, NOTIF-38, NOTIF-40, NOTIF-41

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] As funções do design existem com os paths do RT-100 a RT-104.
- [ ] O union `ApiProblemSlug` tem `push-unavailable`.
- [ ] Gate check passes: App.

**Tests**: none
**Gate**: build
**Commit**: `feat(app): add the push device and alert requests`

---

### T15: Registro do aparelho (nativo e web)

**What**: Criar `utils/push-registration.ts`, com canal, permissão, token, `POST`, `id` em memória, listener de troca de token, `unregisterForPush`, `onAlertTap` e `onAlertReceived`. Criar também `utils/push-registration.web.ts`, com as mesmas funções sem efeito.
**Where**: `frontend-mobile/utils/push-registration.ts` (new)
**Depends on**: T13, T14
**Reuses**: O split `useGoogleIdToken.ts` / `.web.ts`
**Requirement**: NOTIF-12, NOTIF-13, NOTIF-14, NOTIF-15, NOTIF-16, NOTIF-17, NOTIF-18, NOTIF-74

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] A permissão só é pedida quando o status é `undetermined`.
- [ ] O canal é criado antes de `getDevicePushTokenAsync`.
- [ ] Qualquer erro é engolido.
- [ ] `onAlertTap` lê `content.data`, com fallback para `trigger.remoteMessage.data`, e também consulta `getLastNotificationResponseAsync`.
- [ ] O build web não importa `expo-notifications`: o bundle web abre sem erro.
- [ ] Gate check passes: App.

**Tests**: none
**Gate**: build
**Commit**: `feat(app): register the device for push notifications`

---

### T16: Ciclo de sessão e toque no push

**What**: Ligar o push à sessão e ao toque:
- criar `utils/alert-routes.ts` (`alertRoute`) e `hooks/usePushNotifications.ts`;
- montar o hook em `app/(app)/_layout.tsx`;
- chamar `unregisterForPush()` no `signOut` antes do logout.

**Where**: `frontend-mobile/hooks/usePushNotifications.ts` (new)
**Depends on**: T15
**Reuses**: `useAuth`, `router`
**Requirement**: NOTIF-13, NOTIF-17, NOTIF-31, NOTIF-34, NOTIF-37, NOTIF-63, NOTIF-67, NOTIF-74, NOTIF-75, NOTIF-76

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `alertRoute` devolve a agenda para `reservation-created`, `/(app)/customer/ratings` para `customer-rating-*` e `null` para `review-*`.
- [ ] O toque chama `PATCH /api/users/me/alerts/{id}` com `read: true`. Com 200, navega por `alertRoute`; com 404 (alerta de outra conta), abre a caixa.
- [ ] O `signOut` conclui o logout mesmo com o `DELETE` falhando.
- [ ] Gate check passes: App.

**Tests**: none
**Gate**: build
**Commit**: `feat(app): handle push taps and unregister on logout`

---

### T17: Caixa de alertas

**What**: Criar a caixa de alertas:
- o hook `hooks/useAlerts.ts` e o componente `components/alerts/AlertList.tsx`;
- as telas `app/(app)/customer/notifications.tsx` e `app/(app)/hairdresser/profile/notifications.tsx`;
- o registro da tela do cliente no `customer/_layout.tsx`, com `href: null`.

**Where**: `frontend-mobile/components/alerts/AlertList.tsx` (new)
**Depends on**: T14, T16
**Reuses**: `useFavoriteHairdressers` e `favorites.tsx` (foco, lista, otimista, `ErrorModal`), `alertRoute`
**Requirement**: NOTIF-47, NOTIF-48, NOTIF-49, NOTIF-50, NOTIF-51, NOTIF-52, NOTIF-53, NOTIF-54, NOTIF-55

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] As telas mostram o título "Notificações" e o "‹ Voltar".
- [ ] A lista vem na ordem da API, com destaque nos não lidos e data relativa.
- [ ] Tocar num alerta marca como lido na hora e segue `alertRoute`.
- [ ] "Marcar todas como lidas" fica desabilitado sem não lidos.
- [ ] Sem alertas, a tela mostra "Você ainda não tem notificações.".
- [ ] Os `ErrorModal` usam os textos de fallback do spec.
- [ ] Gate check passes: App.

**Tests**: none
**Gate**: build
**Commit**: `feat(app): add the notifications inbox`

---

### T18: Menu "Notificações" com contador

**What**: Ligar o menu à caixa:
- criar `hooks/useUnreadAlertsCount.ts`;
- dar ao `MenuItem` uma prop `badge`;
- ligar o item "Notificações" do perfil do cliente e das configurações do cabeleireiro à caixa, com o contador.

**Where**: `frontend-mobile/hooks/useUnreadAlertsCount.ts` (new)
**Depends on**: T17
**Reuses**: `MenuItem`, `onAlertReceived`
**Requirement**: NOTIF-47, NOTIF-56, NOTIF-57, NOTIF-58

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O toque no item abre a caixa nos dois papéis.
- [ ] O número aparece só quando é maior que zero, e "99+" a partir de 100.
- [ ] O número atualiza no foco e quando um push chega.
- [ ] O número some sem erro quando o `GET` falha.
- [ ] Gate check passes: App (fim da Phase 3).

**Tests**: none
**Gate**: build
**Commit**: `feat(app): open the notifications from the menu with the unread count`

---

### Phase 4: Verificação, tarefas manuais e UAT

### T19: E2E de API contra o LocalStack

**What**: Rodar o roteiro ponta a ponta por `curl` contra o compose completo e registrar o resultado em `validation.md`. Isso substitui a parte do UAT que não depende de aparelho (memória `api-e2e-and-tsc-gotchas`).
**Where**: `.specs/features/push-notifications/validation.md` (new)
**Depends on**: None (depende das Phases 1 a 3)
**Reuses**: O E2E de API da #115 e da #118
**Requirement**: NOTIF-01, NOTIF-07, NOTIF-21, NOTIF-28, NOTIF-29, NOTIF-32, NOTIF-35, NOTIF-38, NOTIF-41, NOTIF-59, NOTIF-60, NOTIF-64, NOTIF-65, NOTIF-68, NOTIF-69

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Com um cliente e um cabeleireiro do seed, cada um com um token falso registrado:
  1. reservar;
  2. avaliar (depois do horário);
  3. editar a review e excluí-la;
  4. dar nota, editar a nota e removê-la.

  Cada passo grava o alerta certo, e `/_aws/sns/platform-endpoint-messages?region=us-east-2` mostra a mensagem no endpoint do destinatário.
- [ ] Com o LocalStack parado, a reserva responde 201, e o alerta é gravado.
- [ ] O logout com `DELETE` do aparelho remove o endpoint do LocalStack.
- [ ] Gate check passes: Build (Full + App).

**Tests**: none
**Gate**: build
**Commit**: `docs(specs): record the push notifications API E2E`

---

### T20: Projeto Firebase (manual, usuário)

**What**: Configurar o Firebase. São três passos manuais do usuário:
1. criar o projeto Firebase e adicionar o app Android `com.rodrigosc615.frontendmobile`;
2. baixar o `google-services.json` para `frontend-mobile/` (fora do git) e cadastrá-lo no EAS como variável de arquivo `GOOGLE_SERVICES_JSON`;
3. gerar a chave da service account (JSON) para o FCM HTTP v1.

**Where**: Console do Firebase e do EAS (fora do repositório)
**Depends on**: None. Pode ser feita a qualquer momento, em paralelo às Phases 1 a 3.
**Reuses**: O projeto EAS `4f8004a8-4568-4b40-a0f2-e2416946fbb3`
**Requirement**: NOTIF-13

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O arquivo existe localmente e no EAS.
- [ ] O JSON da service account está guardado fora do repositório.

**Tests**: none
**Gate**: build
**Commit**: nenhum (tarefa fora do repositório)

---

### T21: Dev build com o módulo de push

**What**: Gerar e instalar um dev build Android novo (`eas build --profile development --platform android` ou `npx expo run:android`), já com `expo-notifications` e o `google-services.json`.
**Where**: Build do EAS ou local (fora do repositório)
**Depends on**: T20
**Reuses**: O perfil `development` do `eas.json`
**Requirement**: NOTIF-12, NOTIF-13

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O app abre no aparelho físico.
- [ ] Depois do login, ele pede a permissão de notificação.

**Tests**: none
**Gate**: build
**Commit**: nenhum

---

### T22: AWS de produção (manual, usuário)

**What**: Configurar a AWS de produção. São três passos manuais do usuário, antes do deploy:
1. criar a platform application FCM (GCM) no SNS da conta real, com o JSON da service account no `PlatformCredential`;
2. dar às credenciais AWS do Render as permissões `sns:CreatePlatformEndpoint`, `sns:SetEndpointAttributes`, `sns:Publish` e `sns:DeleteEndpoint` na platform application;
3. definir `SNS_PLATFORM_APPLICATION_ARN` no Render.

**Where**: Console da AWS e do Render (fora do repositório)
**Depends on**: T20
**Reuses**: As credenciais AWS que o Render já usa para o S3
**Requirement**: NOTIF-69, NOTIF-71

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Um `POST /api/users/me/push-devices` no ambiente de preview responde 201.

**Tests**: none
**Gate**: build
**Commit**: nenhum

---

### T23: UAT no Android e no web

**What**: Rodar o roteiro manual com push real, contra o ambiente de **preview** (Render), que tem a AWS real configurada na T22. O compose local não serve para este roteiro: o backend local manda todo boto3 para o LocalStack (`AWS_ENDPOINT_URL`), que nunca entrega no aparelho. Fazer o deploy da branch no preview exige o aval do usuário.
**Where**: `.specs/features/push-notifications/validation.md` (modify)
**Depends on**: T19, T21, T22
**Reuses**: O roteiro de UAT da #118
**Requirement**: NOTIF-12 a NOTIF-18, NOTIF-31, NOTIF-34, NOTIF-37, NOTIF-47 a NOTIF-58, NOTIF-63, NOTIF-67, NOTIF-74 a NOTIF-76

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Os 7 `kind` chegam como push no aparelho do destinatário, com o app aberto, em segundo plano e fechado.
- [ ] O toque com o app fechado segue o destino do catálogo (risco R4).
- [ ] Com a permissão negada, não há erro, e a caixa funciona.
- [ ] O logout faz o aparelho parar de receber.
- [ ] A troca de conta no mesmo aparelho passa o push para a conta nova.
- [ ] No web, a caixa e o contador funcionam sem pedir permissão.
- [ ] Os requisitos verificados estão marcados como Verified no spec.

**Tests**: none
**Gate**: build
**Commit**: `docs(specs): record the push notifications UAT`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4
```

Os arcos de cada fase são os mesmos do Execution Plan acima:
- **Phase 1:** T1 sozinha; T2 → T3 → T4; T2 → T5; T3 e T5 → T6.
- **Phase 2:** T7 → T8; T7 → T9; T10, T11 e T12 sozinhas.
- **Phase 3:** T13 e T14 → T15 → T16; T14 e T16 → T17 → T18.
- **Phase 4:** T19 sozinha; T20 → T21; T20 → T22; T19, T21 e T22 → T23.

Execution is strictly sequential. As tarefas manuais T20 e T22 são do usuário e podem ser antecipadas a qualquer momento: elas não bloqueiam nenhuma tarefa de código.

**Sub-agentes:** são 23 tarefas, 19 delas de código ou verificação, em 4 fases. A divisão em lotes fica: Phase 1 (6) · Phase 2 (6) · Phase 3 (6) · Phase 4 (T19 e T23, mais as manuais). O Execute oferece sub-agentes por lote.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Slug | 1 linha do catálogo + 2 testes | ✅ Granular |
| T2: Modelos | 1 app + 2 modelos + migração gerada + 1 linha de settings | ⚠️ Coeso: o app só existe para os modelos |
| T3: `SnsService` | 1 serviço + fake + 2 settings + 1 linha do runner | ⚠️ Coeso: o fake e o reset são a forma de testar o serviço |
| T4: LocalStack | init + compose + `.env.example` | ⚠️ Vários arquivos de config de um único recurso |
| T5: Mensagens | 1 módulo de funções puras | ✅ Granular |
| T6: `notify` | 1 módulo | ✅ Granular |
| T7: Aparelho | 1 view (2 rotas) + urls + `ROUTE_TABLE` | ⚠️ O RT falha se a rota existir sem a tabela |
| T8: Exclusão da conta | 1 função | ✅ Granular |
| T9: Alertas | 1 view (3 rotas) + urls + `ROUTE_TABLE` | ⚠️ Mesmo motivo da T7 |
| T10: N01 | 2 pontos de 1 arquivo | ✅ Granular |
| T11: N11/N12 | 3 views de 1 arquivo | ⚠️ Coeso: o mesmo recurso |
| T12: N13/N14 | 3 funções de 1 arquivo | ⚠️ Coeso: o mesmo recurso |
| T13: Config nativa | dependência + plugin + `app.config.js` + `.gitignore` | ⚠️ Uma única mudança de build |
| T14: Serviços | 2 serviços + 1 tipo + 1 slug | ⚠️ Coeso: só tipos e chamadas |
| T15: Registro | 1 módulo (nativo + web) | ✅ Granular |
| T16: Sessão e toque | 1 hook + 1 função pura + 2 pontos de ligação | ⚠️ O hook não serve sem a ligação |
| T17: Caixa | 1 hook + 1 componente + 2 telas finas + 1 linha de layout | ⚠️ As telas só envolvem o componente |
| T18: Menu | 1 hook + 1 prop + 2 itens de menu | ⚠️ Coeso |
| T19 a T22 | Verificação e tarefas manuais | ✅ |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | - | ✅ Match |
| T2 | None | - | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T2 | T2 → T5 | ✅ Match |
| T6 | T3, T5 | T3 → T6, T5 → T6 | ✅ Match |
| T7 | None (Phase 1) | - | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | T7 | T7 → T9 | ✅ Match |
| T10 | None (Phase 1) | - | ✅ Match |
| T11 | None (Phase 1) | - | ✅ Match |
| T12 | None (Phase 1) | - | ✅ Match |
| T13 | None | - | ✅ Match |
| T14 | None | - | ✅ Match |
| T15 | T13, T14 | T13 → T15, T14 → T15 | ✅ Match |
| T16 | T15 | T15 → T16 | ✅ Match |
| T17 | T14, T16 | T14 → T17, T16 → T17 | ✅ Match |
| T18 | T17 | T17 → T18 | ✅ Match |
| T19 | None (Phases 1 a 3) | - | ✅ Match |
| T20 | None | - | ✅ Match |
| T21 | T20 | T20 → T21 | ✅ Match |
| T22 | T20 | T20 → T22 | ✅ Match |
| T23 | T19, T21, T22 | T19 → T23, T21 → T23, T22 → T23 | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Backend: contratos | unit | unit | ✅ OK |
| T2 | Backend: modelos | integration | integration | ✅ OK |
| T3 | Backend: `SnsService` | unit | unit | ✅ OK |
| T4 | Infra local | none | none (go/no-go manual) | ✅ OK |
| T5 | Backend: `messages` | unit | unit | ✅ OK |
| T6 | Backend: `dispatch` | integration | integration | ✅ OK |
| T7 | Backend: views + contratos | integration + unit | integration (+ `test_routes`) | ✅ OK |
| T8 | Backend: exclusão de conta | integration | integration | ✅ OK |
| T9 | Backend: views + contratos | integration + unit | integration (+ `test_routes`) | ✅ OK |
| T10 | Backend: eventos | integration | integration | ✅ OK |
| T11 | Backend: eventos | integration | integration | ✅ OK |
| T12 | Backend: eventos | integration | integration | ✅ OK |
| T13 a T18 | App | none | none | ✅ OK |
| T19 | Specs (E2E registrado) | none | none | ✅ OK |
| T20, T21, T22 | Fora do repositório | none | none | ✅ OK |
| T23 | Specs (UAT registrado) | none | none | ✅ OK |
