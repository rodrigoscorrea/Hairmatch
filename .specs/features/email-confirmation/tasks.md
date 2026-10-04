# Confirmação de e-mail no cadastro Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/email-confirmation/spec.md`
**Context**: `.specs/features/email-confirmation/context.md`
**Design**: `.specs/features/email-confirmation/design.md`
**Status**: Draft (aguardando aprovação para Execute)
**Branch**: a criar a partir de `develop` no início do Execute (por exemplo, `141-confirmacao-de-email-no-cadastro`). Hoje o checkout está em `170-fix-security-correcoes-auditoria-outubro`, e esta feature não entra nesse PR.

**Pré-requisitos do Execute:**
- Testes do backend dentro do container `hairmatch_backend` (memória `backend-tests-run-in-docker`). Se o `hairmatch_db` estiver parado, rodar `docker start hairmatch_db`.
- Os testes **não** usam o MiniStack: o fake de Cognito liga sozinho no modo teste (`COGNITO_USE_FAKE`).
- O UAT (T23) precisa do `docker compose up` completo, com o MiniStack reconciliado pelo T16.
- Nenhuma env var nova.

**Ordem que mantém a suíte verde a cada commit:**
1. A Phase 1 é aditiva. O T5 troca os helpers de teste que fazem cadastro → login por um helper que ativa a conta. Hoje esse helper não muda nada, porque a conta já nasce ativa, e é ele que protege a suíte quando o T6 passa a criar contas pendentes.
2. A Phase 2 muda o cadastro e o login juntos.
3. A Phase 3 adiciona as rotas novas, e as Phases 4 a 7 cuidam de limpeza, ambiente, app e documentação.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas:
> - `.github/workflows/hairmatch-backend-test.yml`: `coverage run manage.py test`, sem limite mínimo.
> - `backend/users/tests.py`: `FakeCognitoIdpTest` `:3121`, `CognitoServiceTest` `:3223`, `CognitoRegisterTest` `:3720`, `CognitoLoginTest` `:3923`, helpers `assert_throttled`/`assert_auth_unavailable` `:1957-2000` e throttle por IP `:3738`/`:3943`/`:4660-4684`.
> - `backend/hairmatch/test_problems.py:37` (contagem do catálogo) e `backend/hairmatch/test_routes.py` (Route Table).
> - Helpers de login que passam pelo cadastro em `backend/preferences/tests.py:58`, `backend/review/tests.py:138,152` e `backend/availability/tests.py`.
> - `frontend-mobile`: sem testes, por decisão herdada do #106 e do #139 (gate `npx tsc --noEmit` + UAT).
>
> Strong defaults aplicados nas camadas de backend.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: fake de Cognito (`users/cognito_fake.py`) | unit | Cada ramo de `confirm_sign_up`/`resend_confirmation_code`: código certo, errado e vencido, já confirmado, usuário inexistente, reenvio que invalida o código anterior | `backend/users/tests.py` (`FakeCognitoIdpTest`) | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput users'` |
| Backend: wrapper (`users/cognito.py`) | unit | Cada código boto3 novo → exceção de domínio, `AlreadyConfirmed`, `admin_get_status`, log sem código nem senha | `backend/users/tests.py` (`CognitoServiceTest`) | idem |
| Backend: throttles (`users/throttles.py`) | unit | Chave por e-mail normalizado (maiúsculas e espaços), `None` sem e-mail e no caminho Google, hash sem o e-mail em claro | `backend/users/tests.py` (`EmailThrottleTest`) | idem |
| Backend: views de `users` (cadastro, login, confirmar, reenviar, listagens) | integration | Cada rota: happy path + cada status de erro do spec (400/403/409/429/503) + "nenhuma linha alterada" onde o spec exige + corpo idêntico onde o spec proíbe enumeração | `backend/users/tests.py` (`APIClient`) | idem |
| Backend: management command `purge_unconfirmed_users` | integration | EMC-34 a EMC-37 via `call_command` + estado do fake e do Postgres + `assertLogs` | `backend/users/tests.py` (`PurgeUnconfirmedUsersCommandTest`) | idem |
| Backend: catálogo e rotas (`hairmatch/`) | unit | Contagem de slugs, títulos e status; Route Table igual ao URLconf | `backend/hairmatch/test_problems.py`, `backend/hairmatch/test_routes.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput hairmatch'` |
| Backend: settings (`CACHES`) | unit | Backend do cache é `DatabaseCache` e um valor gravado é lido de volta | `backend/hairmatch/tests.py` | idem (hairmatch) |
| Helpers de teste dos outros apps | integration | A suíte do app continua passando com o mesmo número de testes | `backend/<app>/tests.py` | Full |
| Infra (init do MiniStack, `entrypoint.sh`, README) | none | Verificação manual (T16, T23) | - | Build |
| App (`frontend-mobile`) | none | `npx tsc --noEmit` sem erro novo + roteiro de UAT do T23 | - | App |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas com testes de um app | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput <app>'` |
| Full | Tarefas que tocam settings, helpers de vários apps, URLconf ou o fim de uma fase de backend | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput && coverage report -m'` |
| App | Tarefas do `frontend-mobile` | `cd frontend-mobile && npx tsc --noEmit` |
| Build | Fim de feature e T23 | Full + App + as verificações manuais do T16 e do T23 |

> **Baseline de testes do backend:** `git grep -c "def test_"` em `5ae43b0` conta **619**:
> - `users` 288, `hairmatch` 95 (`tests.py` 40 + `test_problems.py` 46 + `test_routes.py` 9);
> - `availability` 55, `reserve` 45, `service` 40, `review` 35, `agenda` 23, `chatbot` 20, `preferences` 18.
>
> Nenhuma tarefa reduz esses números. O T1 confirma a baseline rodando a suíte antes de qualquer mudança.

> **Gate do app:** antes do T17, registrar a saída atual de `npx tsc --noEmit` como baseline. O gate passa quando nenhuma tarefa acrescenta erro novo.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação do backend (aditiva)

```
T1 → T2
T3
T4
T5
```

### Phase 2: Cadastro pendente e login

```
T6 → T7 → T9
T6 → T8
```

### Phase 3: Confirmar, reenviar e throttle por e-mail

```
T10 → T11
T10 → T12
T10 → T13
```

### Phase 4: Listagens e expurgo

```
T14
T15
```

### Phase 5: Ambiente local

```
T16
```

### Phase 6: App

```
T17 → T18 → T19 → T20
T19 → T21
```

### Phase 7: Documentação e verificação ponta a ponta

```
T22 → T23
```

---

## Task Breakdown

### Phase 1: Fundação do backend (aditiva) (tarefas)

#### T1: Estender o fake de Cognito com o ciclo de confirmação

**What**: Acrescentar ao `FakeCognitoIdp`:
- `confirm_sign_up` e `resend_confirmation_code`;
- código de 6 dígitos com validade de 24 h guardado no `sign_up`;
- os helpers de teste `confirmation_code(email)` e `expire_code(email)`;
- a resposta de `PreventUserExistenceErrors` (usuário inexistente: `CodeMismatchException` no confirm e entrega simulada no resend);
- `InvalidParameterException` no resend para usuário já `CONFIRMED`.
**Where**: `backend/users/cognito_fake.py`
**Depends on**: None
**Reuses**: `fail_next`, `calls`, `_get_user` e `_begin` do próprio fake
**Requirement**: base para EMC-13 a EMC-24

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Baseline confirmada: `python manage.py test --noinput` passa com 617 testes executados antes da mudança (o `git grep -c "def test_"` conta 619; a diferença de 2 não foi investigada, e os dois números são acompanhados)
- [x] `FakeCognitoIdpTest` cobre:
  - [x] `sign_up` → `confirmation_code(email)` tem 6 dígitos; `confirm_sign_up` com ele → `admin_get_user` mostra `CONFIRMED`
  - [x] Código diferente → `ClientError` `CodeMismatchException`, e o usuário segue `UNCONFIRMED`
  - [x] `expire_code(email)` + código certo → `ExpiredCodeException`
  - [x] Usuário já `CONFIRMED` → `NotAuthorizedException`
  - [x] Usuário inexistente → `CodeMismatchException` no confirm; `resend_confirmation_code` devolve `CodeDeliveryDetails` sem levantar
  - [x] `resend_confirmation_code` gera código novo, e o anterior passa a dar `CodeMismatchException`
  - [x] `resend_confirmation_code` para usuário `CONFIRMED` → `InvalidParameterException`
  - [x] `fail_next('confirm_sign_up', 'TooManyFailedAttemptsException')` levanta exatamente uma vez
- [x] Gate check passes: Quick (`users`)
- [x] Test count: 288 + novos em `users`, sem remoções

**Tests**: unit
**Gate**: quick

**Commit**: `test(users): emulate Cognito sign-up confirmation in the fake`

---

#### T2: Acrescentar o ciclo de confirmação ao `CognitoService`

**What**: Criar:
- `sign_up`, `confirm_sign_up`, `resend_confirmation_code` e `admin_get_status`;
- as exceções `InvalidConfirmationCode`, `ExpiredConfirmationCode`, `UserNotConfirmed`, `AlreadyConfirmed` e `ResendRejected`;
- os códigos novos em `_ERRORS_BY_CODE`.

`sign_up_confirmed` passa a ser `sign_up` + `admin_confirm_sign_up`, com a compensação atual.
**Where**: `backend/users/cognito.py`
**Depends on**: T1
**Reuses**: `_call`, `_username`, `_log`
**Requirement**: EMC-14, EMC-15, EMC-19, EMC-20, EMC-25, EMC-49, EMC-54 (camada de serviço)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `CognitoServiceTest` cobre:
  - [x] `CodeMismatchException` → `InvalidConfirmationCode`
  - [x] `ExpiredCodeException` → `ExpiredConfirmationCode`
  - [x] `UserNotConfirmedException` (no `authenticate`) → `UserNotConfirmed`
  - [x] `TooManyFailedAttemptsException` → `TooManyRequests`
  - [x] `NotAuthorizedException` no `confirm_sign_up` → `AlreadyConfirmed`, e no `authenticate` continua `InvalidCredentials`
  - [x] `sign_up` não chama `admin_confirm_sign_up` (`fake.calls`), e `sign_up_confirmed` chama
  - [x] `admin_get_status` → `UNCONFIRMED`, `CONFIRMED` e `None` (inexistente)
  - [x] `InvalidParameterException` no `resend_confirmation_code` → `ResendRejected`
  - [x] O teste de compensação de `sign_up_confirmed` (`fail_next('admin_confirm_sign_up', ...)`, `users/tests.py:3309`) continua passando
  - [x] `confirm_sign_up` e `resend_confirmation_code` mandam o e-mail em minúsculas
  - [x] `assertLogs('users.cognito', 'WARNING')` numa falha de `confirm_sign_up` não contém o código enviado (EMC-49)
- [x] Gate check passes: Quick (`users`)
- [x] Test count: T1 + novos, sem remoções

**Tests**: unit
**Gate**: quick

**Commit**: `feat(users): add Cognito sign-up confirmation to the service`

---

#### T3: Registrar os slugs de confirmação no catálogo de problemas

**What**: Acrescentar ao `CATALOG`:
- `email-not-confirmed` (403, "Email not confirmed");
- `invalid-confirmation-code` (400, "Invalid confirmation code");
- `confirmation-code-expired` (400, "Confirmation code expired").

Atualizar `len(CATALOG)` de 36 para 39 em `hairmatch/test_problems.py` e as três linhas da tabela do spec `api-problem-details` (AD-006, PD-110).
**Where**: `backend/hairmatch/problems.py`
**Depends on**: None
**Reuses**: formato atual do `CATALOG`
**Requirement**: EMC-47

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `test_problems.py` afirma 39 slugs, e cada slug novo tem o status e o título do spec
- [x] A tabela de `.specs/features/api-problem-details/spec.md` tem as três linhas (slug, status, título, gatilho e texto em pt-BR do design)
- [x] Gate check passes: Quick (`hairmatch`)
- [x] Test count: 95 + novos em `hairmatch`, sem remoções

**Tests**: unit
**Gate**: quick

**Commit**: `feat(api): add the email confirmation problem types`

---

#### T4: Guardar o cache padrão no Postgres

**What**: Definir `CACHES['default']` como `DatabaseCache` (`LOCATION='hairmatch_cache'`) e criar uma migração de `users` com `RunPython` que chama `createcachetable`. Assim, qualquer ambiente que rode `migrate` (local, CI, Render) tem a tabela antes do primeiro request com throttle. O `entrypoint.sh` não muda nesta tarefa.
**Where**: `backend/hairmatch/settings.py` e `backend/users/migrations/0011_create_cache_table.py` (nova)
**Depends on**: None
**Reuses**: `HairmatchTestRunner` (o `cache.clear()` segue igual); o banco de teste roda as migrações e, portanto, cria a tabela
**Requirement**: EMC-33

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Um teste em `backend/hairmatch/tests.py` afirma que `caches['default']` é `DatabaseCache` e que `cache.set`/`cache.get` funcionam no banco de teste
- [x] Os testes de throttle por IP e de cache do CEP continuam passando
- [x] `migrate` num banco limpo cria `hairmatch_cache`, e rodá-lo de novo não falha (`createcachetable` é idempotente)
- [x] A migração tem `reverse_code` no-op, e `makemigrations --check` não acusa pendência
- [x] Gate check passes: Full
- [x] Test count: 619 + novos, sem remoções

**Tests**: unit
**Gate**: full

**Commit**: `feat(api): keep throttle counters in a database cache`

---

#### T5: Criar o helper de teste que ativa uma conta cadastrada

**What**: Criar `activate_account(email)`, que chama `admin_confirm_sign_up` no fake e marca `User.is_active=True`. Usá-lo logo depois de todo cadastro por e-mail/senha via API cuja conta o teste usa depois, seja para login, seja para aparecer em busca, home ou perfil. Vale para `users`, `preferences`, `review` e `availability`. Os testes que verificam o próprio cadastro (status, corpo, linhas criadas) não chamam o helper. Por enquanto ele não muda o comportamento, porque a conta ainda nasce ativa.
**Where**: `backend/users/testing.py` (novo), mais as chamadas nos `tests.py` dos apps
**Depends on**: None
**Reuses**: `get_cognito().client` (fake)
**Requirement**: base para EMC-03 (mantém a suíte verde quando o cadastro passar a criar conta pendente)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `grep -rn "activate_account" backend --include=*.py` encontra o helper e as chamadas em cada helper de login que passa pelo cadastro (`preferences/tests.py:58`, `review/tests.py:138,152`, `availability/tests.py` e as classes de `users/tests.py` que cadastram e logam)
- [x] Levantamento registrado no commit: `grep -n "reverse('register')" backend/*/tests.py` e, para cada ocorrência, se a conta é usada depois (login, listagem ou perfil) e se recebeu o helper
- [x] Verificação antecipada: com `is_active=False` forçado temporariamente no `RegisterView` (sem commit), a suíte só falha nos testes do próprio cadastro que o T6 vai ajustar
- [x] Gate check passes: Full
- [x] Test count: igual ao do T4, sem remoções

**Tests**: integration
**Gate**: full

**Commit**: `test(users): activate registered accounts before logging in`

---

### Phase 2: Cadastro pendente e login (tarefas)

#### T6: Criar a conta de e-mail/senha como pendente

**What**: Mudar o `RegisterView` para:
- chamar só o `sign_up`;
- criar o `User` com `is_active=False`;
- checar e-mail duplicado com `email__iexact`;
- responder 201 com `confirmation_required: true`.

O caminho Google e o seed continuam criando contas ativas.
**Where**: `backend/users/views.py` (`RegisterView`)
**Depends on**: T2, T5
**Reuses**: `_discard_cognito_user`, `_create_role_profile`, `_cognito_error_response`
**Requirement**: EMC-03, EMC-04, EMC-05, EMC-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes de integração:
  - [x] Cadastro de cliente e de cabeleireiro → 201 com o corpo exato de EMC-03, sem `Set-Cookie`, `is_active=False`, `cognito_sub` preenchido e o perfil criado
  - [x] `fake.calls` tem `sign_up` e não tem `admin_confirm_sign_up`
  - [x] Cadastro Google → `is_active=True`, sem chamadas ao fake (EMC-04)
  - [x] Conta ativa `a@x.com` + cadastro com `A@X.com` → 409 `email-taken`, sem chamadas ao fake (EMC-05)
  - [x] `populate_hairdressers` → cabeleireiros com `is_active=True`, e login com `Senha123` → 200 (EMC-06)
  - [x] `test_failed_confirmation_answers_503_and_leaves_no_cognito_user_or_rows` (`users/tests.py:3884`), que injeta falha em `admin_confirm_sign_up` pelo `RegisterView`, passa a injetar `fail_next('sign_up', 'InternalErrorException')` e afirma 503 sem linhas nem usuário no fake. Ganha nome novo e mantém a contagem. O caso do `admin_confirm_sign_up` fica coberto no serviço (`users/tests.py:3309`)
  - [x] Os demais testes de compensação de COG-10 (insert, foto e preferências) continuam passando
- [x] Gate check passes: Full
- [x] Test count: T5 + novos, sem remoções

**Tests**: integration
**Gate**: full

**Commit**: `feat(users): create e-mail accounts pending confirmation`

---

#### T7: Substituir a conta pendente que ocupa o e-mail ou o telefone

**What**: No `RegisterView`:
- uma conta inativa com `cognito_sub` que tem o mesmo e-mail (`iexact`) ou o mesmo telefone normalizado é apagada no Cognito (`admin_delete_user`) e no Postgres antes do `sign_up`;
- o órfão `UNCONFIRMED` do Cognito sem linha no Postgres é apagado e o `sign_up` é repetido uma única vez;
- conta ativa continua respondendo 409.
**Where**: `backend/users/views.py` (`RegisterView`, helper `_replace_pending_account`)
**Depends on**: T6
**Reuses**: `admin_delete_user`, `admin_get_status`, `normalize_phone`
**Requirement**: EMC-07, EMC-08, EMC-09, EMC-10, EMC-11, EMC-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes de integração:
  - [x] Pendente `a@x.com` + cadastro `A@x.com` → 201, um único `User` com esse e-mail, e `admin_delete_user` antes de `sign_up` em `fake.calls` (EMC-07)
  - [x] Pendente com telefone X + cadastro com outro e-mail e telefone X → 201, e a conta antiga sumiu (EMC-08)
  - [x] Ativo com telefone X → 409 `phone-taken`, sem chamadas ao fake (EMC-09)
  - [x] Órfão `UNCONFIRMED` só no fake → 201 depois de `admin_delete_user` + segundo `sign_up` (EMC-10)
  - [x] Órfão `CONFIRMED` só no fake → 409 `email-taken`, sem `admin_delete_user` (EMC-10)
  - [x] `fail_next('admin_delete_user', EndpointConnectionError)` → 503 `auth-unavailable`, e a conta antiga continua no fake e no Postgres (EMC-11)
  - [x] Falha no insert depois da substituição → a compensação apaga a conta nova, e a antiga continua apagada (EMC-12)
- [x] Gate check passes: Quick (`users`)
- [x] Test count: T6 + novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `feat(users): replace a pending account on a new sign-up`

---

#### T8: Recusar o login de conta pendente com 403

**What**: No `LoginView`, `UserNotConfirmed` responde 403 `email-not-confirmed`. Um `sub` autenticado cujo `User` está inativo também responde 403, sem cookie. É o caso do MiniStack. Também ganha teste o invariante do autenticador para usuário inativo.
**Where**: `backend/users/views.py` (`LoginView`)
**Depends on**: T6
**Reuses**: `authenticate`, `authenticate_token`, `problem_response`
**Requirement**: EMC-25, EMC-26, EMC-27

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes de integração:
  - [x] Cadastro + login sem confirmar → 403 `email-not-confirmed`, sem `Set-Cookie` (`UserNotConfirmedException` do fake)
  - [x] Conta confirmada no fake, mas `is_active=False` no Postgres → 403 `email-not-confirmed`, sem `Set-Cookie`
  - [x] Senha errada de conta pendente → 401 `invalid-credentials` (EMC-26)
  - [x] Access token válido de `User` inativo em `GET /api/users/me` → 401 `invalid-session` (EMC-27)
- [x] Gate check passes: Quick (`users`)
- [x] Test count: T7 + novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `feat(users): refuse login of accounts pending confirmation`

---

#### T9: Impedir que o Google herde uma conta pendente

**What**: No `GoogleAuthView`, uma conta achada por e-mail (`iexact`) que está inativa e tem `cognito_sub` não é vinculada. Ela é apagada pelo `_replace_pending_account` (Cognito antes do Postgres), e a resposta segue o caminho de conta nova (`signup_token`). No `_register_with_google`, o e-mail do token ou o telefone de uma conta pendente aciona a mesma substituição antes do insert.
**Where**: `backend/users/views.py` (`GoogleAuthView`, `_register_with_google`)
**Depends on**: T7
**Reuses**: `_replace_pending_account` (T7), mock `patch('users.views.verify_google_id_token')` dos testes GAUTH
**Requirement**: EMC-52, EMC-53, EMC-55

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes de integração:
  - [x] Conta pendente `Ana@gmail.com` + `POST /api/auth/google` com identidade `ana@gmail.com` → 200 com `signup_token`; a conta sumiu do fake e do Postgres; nenhum `User` tem o `google_id` (EMC-52)
  - [x] Conta **ativa** com o mesmo e-mail continua sendo vinculada como hoje (GAUTH, sem regressão)
  - [x] Conta pendente com o telefone X + cadastro Google com telefone X → 201, e a conta Google nasce ativa (EMC-53)
  - [x] `fail_next('admin_delete_user', EndpointConnectionError)` nos dois caminhos → 503 `auth-unavailable`, e a conta pendente fica intacta, sem `google_id` (EMC-55)
- [x] Gate check passes: Quick (`users`)
- [x] Test count: T8 + novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `fix(users): never link a Google sign-in to a pending account`

---

### Phase 3: Confirmar, reenviar e throttle por e-mail (tarefas)

#### T10: Criar os throttles por e-mail e por IP das rotas de confirmação

**What**: Criar `EmailRateThrottle` (chave pelo SHA-256 do e-mail normalizado; `None` sem e-mail ou com `google_signup_token`), mais:
- `ConfirmEmailThrottle` (10/hora), `ResendCodeEmailThrottle` (3/hora) e `RegisterEmailThrottle` (3/hora);
- `ConfirmIpThrottle` (10/min) e `ResendCodeIpThrottle` (10/hora).
**Where**: `backend/users/throttles.py` (novo)
**Depends on**: None
**Reuses**: `SimpleRateThrottle` e `AnonRateThrottle` do DRF; padrão de `RegisterThrottle`
**Requirement**: EMC-29, EMC-31, EMC-32 e EMC-33 (camada de throttle)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `EmailThrottleTest` (`APIRequestFactory`):
  - [x] `" A@X.com "` e `"a@x.com"` → a mesma chave
  - [x] A chave não contém o e-mail em claro
  - [x] Corpo sem e-mail → `None`
  - [x] Corpo com `google_signup_token` → `None`
  - [x] Os rates de cada classe são os do spec
- [x] Gate check passes: Quick (`users`)
- [x] Test count: T8 + novos, sem remoções

**Tests**: unit
**Gate**: quick

**Commit**: `feat(users): add per-email throttles for sign-up confirmation`

---

#### T11: Limitar o cadastro por e-mail alvo

**What**: Acrescentar `RegisterEmailThrottle` aos `throttle_classes` do `RegisterView`. O `RegisterThrottle` por IP é mantido.
**Where**: `backend/users/views.py` (`RegisterView`)
**Depends on**: T10
**Reuses**: helper `assert_throttled`
**Requirement**: EMC-32

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Teste de integração: quatro cadastros de `a@x.com` alternando `REMOTE_ADDR` entre dois IPs (o primeiro é substituído pelos seguintes) → o quarto responde 429 `too-many-requests` com `Retry-After`, e `fake.calls` tem só três `sign_up`
- [x] O teste de 10/hora por IP continua passando
- [x] Gate check passes: Quick (`users`)
- [x] Test count: T10 + novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `feat(users): throttle sign-up per target e-mail`

---

#### T12: Criar a rota de confirmação de e-mail

**What**: Criar `EmailConfirmationView` (`POST /api/auth/email-confirmations`) com o fluxo do design e os throttles `ConfirmIpThrottle` + `ConfirmEmailThrottle`. Registrar a rota em `users/urls.py`, no `ROUTE_TABLE` de `hairmatch/test_routes.py` e na Route Table do spec `api-restful-routes`, nesta ordem (AD-007).
**Where**: `backend/users/views.py` (`EmailConfirmationView`)
**Depends on**: T10
**Reuses**: `confirm_sign_up`, `validation_problem`, `missing_field_errors`, `_cognito_error_response`
**Requirement**: EMC-13 a EMC-20, EMC-28, EMC-29, EMC-48, EMC-49, EMC-50 (rota de confirmação)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes de integração:
  - [x] Código lido do fake → 200 `{"message": "Email confirmed"}`, sem `Set-Cookie`, `is_active=True`, e o login seguinte → 200 (EMC-13)
  - [x] Código errado → 400 `invalid-confirmation-code`, e a conta segue inativa (EMC-14)
  - [x] `expire_code` → 400 `confirmation-code-expired` (EMC-15)
  - [x] E-mail sem conta → 400 com o mesmo `type`, `title`, `status` e `detail` do código errado, sem chamadas ao fake (EMC-16)
  - [x] Sem `email`, sem `code`, `code="12345"` e `code="abcdef"` → 400 `validation-error` com os `pointer`s, sem chamadas ao fake (EMC-17)
  - [x] Conta já ativa → 200, sem chamadas ao fake (EMC-18)
  - [x] `fail_next('confirm_sign_up', 'TooManyFailedAttemptsException')` → 429, e a conta segue inativa (EMC-19)
  - [x] Confirmada no fake e inativa no Postgres → 200, e `is_active=True` (EMC-20)
  - [x] E-mail em outra caixa (`A@X.com`) → 200 (Edge Case)
  - [x] 11ª chamada do mesmo IP em 1 minuto → 429 + `Retry-After` (EMC-28)
  - [x] 11ª tentativa para o mesmo e-mail vinda de IPs alternados → 429 (EMC-29)
  - [x] `EndpointConnectionError` → 503, `is_active` não muda, e o `assertLogs` não contém o código (EMC-48, EMC-49)
- [x] `test_routes.py` passa com `('POST', 'auth/email-confirmations')`
- [x] Gate check passes: Full
- [x] Test count: T11 + novos, sem remoções

**Tests**: integration
**Gate**: full

**Commit**: `feat(users): confirm sign-up e-mail with the Cognito code`

---

#### T13: Criar a rota de reenvio do código

**What**: Criar `ConfirmationCodeView` (`POST /api/auth/confirmation-codes`) com os throttles `ResendCodeIpThrottle` + `ResendCodeEmailThrottle`. A rota responde sempre 202 e só chama o Cognito para conta pendente. Registrar a rota em `users/urls.py`, no `ROUTE_TABLE` e na Route Table do spec.
**Where**: `backend/users/views.py` (`ConfirmationCodeView`)
**Depends on**: T10
**Reuses**: `resend_confirmation_code`, `missing_field_errors`, `_cognito_error_response`
**Requirement**: EMC-21 a EMC-24, EMC-30, EMC-31, EMC-48, EMC-50 (rota de reenvio), EMC-54

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes de integração:
  - [x] Conta pendente → 202 com o corpo de EMC-21, `resend_confirmation_code` em `fake.calls`, e o código antigo passa a falhar na confirmação
  - [x] E-mail inexistente, conta ativa e conta Google → 202 com corpo idêntico (exceto `instance`, que nem existe no 202), sem chamadas ao fake (EMC-22)
  - [x] Sem `email` → 400 `validation-error` com `pointer` `/email` (EMC-23)
  - [x] `fail_next('resend_confirmation_code', 'LimitExceededException')` → 429 (EMC-24)
  - [x] 11ª chamada do mesmo IP em 1 hora → 429 + `Retry-After` (EMC-30)
  - [x] 4º pedido para o mesmo e-mail vindo de IPs alternados → 429, e só três `resend_confirmation_code` em `fake.calls` (EMC-31)
  - [x] `EndpointConnectionError` → 503 (EMC-48)
  - [x] Conta `CONFIRMED` no fake e inativa no Postgres → o fake levanta `InvalidParameterException`, o backend consulta o status, ativa o `User` e responde 202; com status `UNCONFIRMED` e o mesmo erro injetado por `fail_next` → 503 (EMC-54)
- [x] `test_routes.py` passa com `('POST', 'auth/confirmation-codes')`
- [x] Gate check passes: Full
- [x] Test count: T12 + novos, sem remoções

**Tests**: integration
**Gate**: full

**Commit**: `feat(users): resend the sign-up confirmation code`

---

### Phase 4: Listagens e expurgo (tarefas)

#### T14: Tirar o cabeleireiro pendente das listagens

**What**: Filtrar `is_active=True` na busca global (`GlobalSearchView`), na home por preferência (`_home_response`, antes do `[:10]`) e no "para você" (`CustomerHomeView`).
**Where**: `backend/users/views.py` (listagens)
**Depends on**: T6
**Reuses**: querysets atuais
**Requirement**: EMC-39

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes de integração:
  - [x] Um cabeleireiro ativo e um pendente com o mesmo nome e a mesma preferência → a busca pelo nome, a lista da preferência em `GET /api/home` e o `for_you` de `GET /api/customers/me/home` trazem só o ativo
  - [x] Onze cabeleireiros ativos e um pendente na mesma preferência → a lista da home traz dez ativos
- [x] Gate check passes: Quick (`users`)
- [x] Test count: T13 + novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `fix(users): hide hairdressers pending confirmation from listings`

---

#### T15: Criar o command de expurgo de contas pendentes

**What**: Criar `purge_unconfirmed_users`, com o fluxo do design (Cognito antes do Postgres, WARNING por falha, INFO no fim). Chamá-lo no `entrypoint.sh` depois do `migrate`.
**Where**: `backend/users/management/commands/purge_unconfirmed_users.py` (novo)
**Depends on**: T6
**Reuses**: `get_cognito().admin_delete_user`, estrutura de `populate_hairdressers.py`
**Requirement**: EMC-34, EMC-35, EMC-36, EMC-37, EMC-38

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `PurgeUnconfirmedUsersCommandTest` (com `date_joined` ajustado via `update()`):
  - [x] Pendentes de 8 dias, de 7 dias exatos e de 1 hora, uma conta ativa de 30 dias e uma conta Google inativa de 30 dias → só a de 8 dias some do fake e do Postgres (EMC-34, EMC-35)
  - [x] `admin_delete_user` aparece em `fake.calls` antes da remoção da linha
  - [x] `fail_next('admin_delete_user', EndpointConnectionError)` com duas elegíveis → uma apagada e uma mantida, WARNING com o id, sem exceção (EMC-36)
  - [x] `assertLogs` INFO com `deleted=1 kept=1`; uma segunda execução → `deleted=0` (EMC-37)
- [x] `entrypoint.sh` chama `purge_unconfirmed_users` (EMC-38; conferido no T23)
- [x] Gate check passes: Quick (`users`)
- [x] Test count: T14 + novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `feat(users): purge accounts left pending for over seven days`

---

### Phase 5: Ambiente local (tarefas)

#### T16: Configurar a verificação por código no MiniStack

**What**: No script de init:
- `create-user-pool` ganha `--verification-message-template` (assunto e corpo do spec);
- `create-user-pool-client` ganha `--prevent-user-existence-errors ENABLED`;
- em vez do `exit 0` para pool existente, o script reconcilia com `update-user-pool` e `update-user-pool-client`, passando o conjunto completo de atributos.
**Where**: `docker/ministack/init/01-cognito.sh`
**Depends on**: None
**Reuses**: o próprio script (busca por nome, `awslocal`)
**Requirement**: EMC-01, EMC-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `docker restart hairmatch_ministack` com o volume atual. `describe-user-pool` mostra o template, a política de senha e `AutoVerifiedAttributes=["email"]`; `describe-user-pool-client` mostra `PreventUserExistenceErrors=ENABLED`, os auth flows e as validades; o `Id` do pool não mudou
- [ ] Segundo restart → mesmo estado, e um único `hairmatch-dev` em `list-user-pools`
- [ ] Login com um cabeleireiro do seed continua respondendo 200
- [ ] Gate check passes: Build (verificação manual acima registrada no commit)

**Tests**: none
**Gate**: build

**Commit**: `chore(docker): send Cognito verification codes in local dev`

---

### Phase 6: App (tarefas)

#### T17: Acrescentar os slugs, as rotas anônimas e o serviço de confirmação ao app

**What**: Acrescentar os três slugs ao `ProblemSlug` e ao `PROBLEM_MESSAGES` (textos do design) e as duas rotas ao `REFRESH_EXCLUDED`. Criar `services/email-confirmation.service.ts` com `confirmEmail(email, code)` e `resendConfirmationCode(email)` pelo `axiosInstance`.
**Where**: `frontend-mobile/services/email-confirmation.service.ts` (novo)
**Depends on**: None
**Reuses**: `axiosInstance`, `API_BACKEND_URL`, `utils/api-problem.ts`, `services/auth-routes.ts`
**Requirement**: EMC-45, EMC-46

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Baseline de `npx tsc --noEmit` registrada antes da mudança
- [ ] `utils/api-problem.ts` e `services/auth-routes.ts` têm os itens novos
- [ ] Gate check passes: App, sem erro novo

**Tests**: none
**Gate**: app

**Commit**: `feat(app): add the e-mail confirmation service and problem types`

---

#### T18: Guardar a confirmação pendente em memória e criar o hook da tela

**What**: Acrescentar `pendingConfirmation`, `setPendingConfirmation` e `clearPendingConfirmation` ao `RegistrationContext`, só em memória. Criar `useConfirmEmail`:
- estado do código e `canSubmit` (6 dígitos);
- `submit()`: confirma, faz `signIn` com a senha em memória e limpa a senha; sem senha, vai para o login com a mensagem do spec;
- `resend()` com cooldown de 60 s e limpeza do timer no unmount;
- `errorModal` pelo `problemMessage`.
**Where**: `frontend-mobile/hooks/authHooks/useConfirmEmail.ts` (novo)
**Depends on**: T17
**Reuses**: `useAuth().signIn`, `useRegistration`, `problemMessage`
**Requirement**: EMC-42, EMC-43, EMC-44, EMC-45

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -n "AsyncStorage\|console.log" hooks/authHooks/useConfirmEmail.ts contexts/RegistrationContext.tsx` não mostra a senha sendo gravada nem logada
- [ ] Gate check passes: App, sem erro novo

**Tests**: none
**Gate**: app

**Commit**: `feat(app): add the e-mail confirmation hook`

---

#### T19: Criar a tela de confirmação do e-mail

**What**: Criar `app/(auth)/confirm-email.tsx`:
- texto "Enviamos um código para <e-mail>";
- campo numérico de 6 dígitos (`number-pad`, `oneTimeCode`);
- botão "Confirmar", desabilitado até ter 6 dígitos;
- botão "Reenviar código" com contagem regressiva;
- `ErrorModal`.

Sem `pendingConfirmation`, a tela volta para o login.
**Where**: `frontend-mobile/app/(auth)/confirm-email.tsx` (novo)
**Depends on**: T18
**Reuses**: estilos e componentes de `app/(auth)/login.tsx`, `ErrorModal`
**Requirement**: EMC-42, EMC-43, EMC-44

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Gate check passes: App, sem erro novo
- [ ] A rota aparece no Stack de `app/(auth)/_layout.tsx` (se o layout lista as telas)

**Tests**: none
**Gate**: app

**Commit**: `feat(app): add the e-mail confirmation screen`

---

#### T20: Levar o fim do wizard à confirmação

**What**: No modo e-mail, o 201 chama `setPendingConfirmation({email, password})` e `router.replace('/(auth)/confirm-email')` no lugar do alert e do redirecionamento para o login. O modo Google não muda.
**Where**: `frontend-mobile/hooks/authHooks/usePreferences.ts` e `frontend-mobile/hooks/authHooks/useDescription.ts`
**Depends on**: T19
**Reuses**: `useRegistration`
**Requirement**: EMC-40

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os dois hooks não têm mais o alert "Cadastro concluído!" no modo e-mail
- [ ] Gate check passes: App, sem erro novo

**Tests**: none
**Gate**: app

**Commit**: `feat(app): open e-mail confirmation after sign-up`

---

#### T21: Levar o login de conta pendente à confirmação

**What**: `signIn` (`app/_layout.tsx`) devolve também o `slug` do problema. Em `useLogin`, `email-not-confirmed` chama `setPendingConfirmation({email, password})` e navega para `/(auth)/confirm-email`, sem `ErrorModal`.
**Where**: `frontend-mobile/hooks/authHooks/useLogin.ts`
**Depends on**: T19
**Reuses**: `toApiProblem`, `useRegistration`
**Requirement**: EMC-41

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O tipo de retorno de `signIn` inclui `slug?: ProblemSlug`, e os outros chamadores continuam compilando
- [ ] Gate check passes: App, sem erro novo

**Tests**: none
**Gate**: app

**Commit**: `feat(app): send pending accounts from login to confirmation`

---

### Phase 7: Documentação e verificação ponta a ponta (tarefas)

#### T22: Documentar a confirmação para dev e produção

**What**: No README:
- **dev:** onde ler o código (`http://localhost:4567/_ministack/ses/messages`), o código fixo `123456`, o fato de que o MiniStack aceita qualquer código, e como rodar `purge_unconfirmed_users`;
- **produção:** checklist do pool (`EmailConfiguration` `DEVELOPER` + `SourceArn` + `From`, `VerificationMessageTemplate`, `PreventUserExistenceErrors=ENABLED`), SES fora do sandbox, como agendar o expurgo e conferir na AWS real o código de erro do `ResendConfirmationCode` para conta já confirmada (EMC-54).
**Where**: `README.md`
**Depends on**: None
**Reuses**: seções de Cognito e MiniStack já existentes no README
**Requirement**: EMC-51

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O README tem os dois blocos, e os comandos citados existem
- [ ] Gate check passes: Build (suíte do backend inalterada)

**Tests**: none
**Gate**: build

**Commit**: `docs: explain sign-up e-mail confirmation in dev and production`

---

#### T23: Verificar o fluxo de ponta a ponta (UAT)

**What**: Subir o compose e percorrer o roteiro no web e no Android, com cliente e cabeleireiro:
1. Cadastro → e-mail em `/_ministack/ses/messages` (EMC-02) → código → home sem redigitar a senha.
2. Cadastro, fechar o app, login → tela de confirmação (403) → confirmar → home.
3. Reenviar: a contagem de 60 s aparece e um segundo e-mail chega.
4. Cabeleireiro pendente fora da busca.
5. Login Google e login do seed sem regressão.
6. Logs do boot mostram `purge_unconfirmed_users deleted=… kept=…` (EMC-38), e a tabela `hairmatch_cache` existe no Postgres.
7. Cadastro por e-mail/senha com um Gmail próprio sem confirmar, seguido de "Entrar com Google" com o mesmo e-mail → wizard Google, sem herdar a conta pendente (EMC-52).

Marcar as requisições verificadas como `Verified` na Traceability do spec.
**Where**: `.specs/features/email-confirmation/spec.md` (Traceability)
**Depends on**: T22
**Reuses**: memória `expo-web-smoke-needs-visible-tab` (aba visível, Metro na 8081)
**Requirement**: EMC-02, EMC-38, EMC-40 a EMC-46, EMC-52 (verificação manual)

**Tools**:

- MCP: `claude-in-chrome` (web)
- Skill: `run`

**Done when**:

- [ ] Os 7 passos passam no web, e os passos 1 a 3 passam no Android
- [ ] Gate check passes: Build

**Tests**: none
**Gate**: build

**Commit**: `docs(specs): record e-mail confirmation UAT`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7
```

São 23 tarefas, o que dá mais de um lote de cerca de 7. No início do Execute, oferecer sub-agentes por lote, com fases inteiras:
- **Lote A:** Phase 1 + Phase 2 (9 tarefas; as fases não são quebradas). Backend central, nível alto de raciocínio.
- **Lote B:** Phase 3 + Phase 4 + Phase 5 (7 tarefas). Rotas, limpeza e infra.
- **Lote C:** Phase 6 + Phase 7 (7 tarefas). App, documentação e UAT, com o UAT exigindo o usuário presente.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: fake de confirmação | 1 classe (fake) | ✅ Granular |
| T2: serviço de confirmação | 1 classe + exceções no mesmo arquivo | ✅ Granular |
| T3: slugs | 1 dicionário (+ contagem e linha do spec) | ⚠️ OK, coeso (AD-006 exige os 4 pontos juntos) |
| T4: `CACHES` | 1 setting + 1 migração que cria a tabela | ⚠️ OK, coeso |
| T5: helper de ativação | 1 função + chamadas em testes | ⚠️ OK, coeso (refactor só de teste) |
| T6: cadastro pendente | 1 view | ✅ Granular |
| T7: substituição | 1 helper na mesma view | ✅ Granular |
| T8: login 403 | 1 view | ✅ Granular |
| T9: Google sem herdar conta pendente | 2 funções da mesma view de auth | ⚠️ OK, coeso |
| T10: throttles | 1 módulo | ✅ Granular |
| T11: throttle do cadastro | 1 atributo de view | ✅ Granular |
| T12: rota de confirmação | 1 endpoint (+ registro de rota exigido pelo AD-007) | ✅ Granular |
| T13: rota de reenvio | 1 endpoint (+ registro de rota) | ✅ Granular |
| T14: listagens | 3 querysets no mesmo arquivo | ⚠️ OK, coeso |
| T15: expurgo | 1 command (+ 1 linha do entrypoint) | ✅ Granular |
| T16: init do MiniStack | 1 script | ✅ Granular |
| T17: slugs e serviço do app | 1 serviço + 2 listas | ⚠️ OK, coeso |
| T18: hook + estado no contexto | 1 hook + 1 campo de contexto | ⚠️ OK, coeso |
| T19: tela | 1 componente | ✅ Granular |
| T20: fim do wizard | o mesmo trecho em 2 hooks | ⚠️ OK, coeso |
| T21: login pendente | 1 hook (+ tipo de retorno de `signIn`) | ✅ Granular |
| T22: README | 1 arquivo | ✅ Granular |
| T23: UAT | verificação | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | início da Phase 1 | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | None | isolada | ✅ Match |
| T4 | None | isolada | ✅ Match |
| T5 | None | isolada | ✅ Match |
| T6 | T2, T5 (fases anteriores) | início da Phase 2 | ✅ Match |
| T7 | T6 | T6 → T7 | ✅ Match |
| T8 | T6 | T6 → T8 | ✅ Match |
| T9 | T7 | T7 → T9 | ✅ Match |
| T10 | None | início da Phase 3 | ✅ Match |
| T11 | T10 | T10 → T11 | ✅ Match |
| T12 | T10 | T10 → T12 | ✅ Match |
| T13 | T10 | T10 → T13 | ✅ Match |
| T14 | T6 (fase anterior) | isolada | ✅ Match |
| T15 | T6 (fase anterior) | isolada | ✅ Match |
| T16 | None | isolada | ✅ Match |
| T17 | None | início da Phase 6 | ✅ Match |
| T18 | T17 | T17 → T18 | ✅ Match |
| T19 | T18 | T18 → T19 | ✅ Match |
| T20 | T19 | T19 → T20 | ✅ Match |
| T21 | T19 | T19 → T21 | ✅ Match |
| T22 | None | início da Phase 7 | ✅ Match |
| T23 | T22 | T22 → T23 | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1: fake | Backend: fake de Cognito | unit | unit | ✅ OK |
| T2: serviço | Backend: wrapper | unit | unit | ✅ OK |
| T3: slugs | Backend: catálogo | unit | unit | ✅ OK |
| T4: `CACHES` | Backend: settings | unit | unit | ✅ OK |
| T5: helper | Helpers de teste dos outros apps | integration | integration | ✅ OK |
| T6: cadastro pendente | Backend: views de `users` | integration | integration | ✅ OK |
| T7: substituição | Backend: views de `users` | integration | integration | ✅ OK |
| T8: login 403 | Backend: views de `users` | integration | integration | ✅ OK |
| T9: Google | Backend: views de `users` | integration | integration | ✅ OK |
| T10: throttles | Backend: throttles | unit | unit | ✅ OK |
| T11: throttle do cadastro | Backend: views de `users` | integration | integration | ✅ OK |
| T12: confirmar | Backend: views de `users` + rotas | integration | integration | ✅ OK |
| T13: reenviar | Backend: views de `users` + rotas | integration | integration | ✅ OK |
| T14: listagens | Backend: views de `users` | integration | integration | ✅ OK |
| T15: expurgo | Backend: management command | integration | integration | ✅ OK |
| T16: init do MiniStack | Infra | none | none | ✅ OK |
| T17: slugs e serviço do app | App | none | none | ✅ OK |
| T18: hook | App | none | none | ✅ OK |
| T19: tela | App | none | none | ✅ OK |
| T20: wizard | App | none | none | ✅ OK |
| T21: login | App | none | none | ✅ OK |
| T22: README | Infra (README) | none | none | ✅ OK |
| T23: UAT | Verificação | none | none | ✅ OK |
