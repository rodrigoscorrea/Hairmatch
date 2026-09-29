# Autenticação via AWS Cognito Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/cognito-auth/spec.md`
**Context**: `.specs/features/cognito-auth/context.md`
**Design**: `.specs/features/cognito-auth/design.md`
**Status**: Draft (aguardando aprovação para Execute)
**Branch**: `139-troca-autenticacao-para-aws-cognito`, criada a partir de `develop` (`b93baa5`)

**Pré-requisitos do Execute:**
- Postgres acessível para os testes do backend (`docker compose up db`, com as `DB_*` exportadas), ou os testes rodando dentro do container.
- Os testes do backend **não** precisam do MiniStack: o fake de Cognito liga sozinho no modo teste (`COGNITO_USE_FAKE`).
- O UAT (T24) precisa do `docker compose up` completo, com o LocalStack (token atual) e o MiniStack (sem token).
- Env vars novas: só `COGNITO_USER_POOL_ID` e `COGNITO_APP_CLIENT_ID`, vazias em dev. O endpoint do MiniStack é definido no compose.

**Ordem que mantém a suíte verde a cada commit:**
1. A fundação é só aditiva (Phase 1).
2. Os leitores de sessão migram para o autenticador central. Ele aceita **temporariamente** o formato antigo (`'secret'`) para que o login bcrypt continue funcionando (Phase 2).
3. Cadastro e login trocam para o Cognito juntos, porque os testes de todos os apps se autenticam por register → login (Phase 3).
4. Por último sai o formato antigo e o `bcrypt` (T16).

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas:
> - `.github/workflows/hairmatch-backend-test.yml`: roda `coverage run manage.py test` com Postgres 13, sem LocalStack e sem limite mínimo.
> - `backend/hairmatch/tests.py`: `SimpleTestCase` com `patch('hairmatch.storage.boto3.client')`.
> - `backend/users/tests.py`: `TestCase` + `APIClient`. Autenticação por register → login → `response.data['jwt']` (`:399`, `:483`, `:626`). O Google é mockado com `patch('users.views.verify_google_id_token')`.
> - `backend/preferences/tests.py:54`, `backend/review/tests.py:134` e `backend/availability/tests.py:50`: helpers de login próprios.
> - `backend/hairmatch/settings.py:150`: `InMemoryStorage` quando `'test' in sys.argv`. O fake de Cognito segue o mesmo padrão.
> - `frontend-mobile`: sem testes. Decisão herdada do #106 (gate `npx tsc --noEmit` + UAT).
>
> Strong defaults aplicados nas camadas de backend.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: fake de Cognito (`users/cognito_fake.py`) | unit | Política de senha, e-mail sem diferenciar maiúsculas, tokens verificáveis pelo próprio JWKS, revogação do refresh e `fail_next` | `backend/users/tests.py` (`FakeCognitoIdpTest`) | `cd backend && python manage.py test users` |
| Backend: wrapper (`users/cognito.py`) | unit | Todos os ramos. Cada código boto3 → exceção de domínio. Log sem segredo. Resolução de IDs (env × busca por nome). Compensação no confirm. JWKS com erro. COG-03, COG-04, COG-47 a COG-49. | `backend/users/tests.py` (`CognitoServiceTest`) | `cd backend && python manage.py test users` |
| Backend: autenticador (`users/authentication.py`) e `auth_tokens` | unit | 1:1 com COG-17 a COG-20, COG-23 e COG-24. Cada forma de token inválido listada em COG-19 tem um teste. | `backend/users/tests.py` (`AuthenticationTest`, `AuthTokensTest`) | `cd backend && python manage.py test users` |
| Backend: views de `users` | integration | Cada rota no escopo: happy path + cada status de erro do spec (400/401/403/409/429/503) + "nenhuma linha criada/alterada" onde o spec exige | `backend/users/tests.py` (`APIClient`) | `cd backend && python manage.py test users` |
| Backend: views de `availability`, `review` e `preferences` | integration | Cada rota de COG-22: aceita access token do Cognito e sessão Google; recusa com 401 token ausente, inválido e antigo; mantém os testes de regra de negócio | `backend/<app>/tests.py` | `cd backend && python manage.py test <app>` |
| Backend: management command do seed | integration | COG-38 a COG-40 via `call_command` + login pela API | `backend/users/tests.py` (`PopulateHairdressersCommandTest`) | `cd backend && python manage.py test users` |
| Backend: model + migration | none | Build gate: `makemigrations --check` sem mudanças pendentes | - | Full |
| Infra (compose, init script, `.env.example`, README) | none | Verificação manual no T24 (`docker compose up`, `aws cognito-idp`, login real) | - | Build |
| App (`frontend-mobile`) | none | `npx tsc --noEmit` sem erros + roteiro de UAT do T24 | - | App |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Os testes do backend precisam de Postgres: exporte `DB_HOST/DB_NAME/DB_USER/DB_PASSWORD`, ou rode dentro do container com `docker compose exec django python3 backend/manage.py test`.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas com testes unit ou integration de um app | `cd backend && python manage.py test <app>` (o app da tarefa) |
| Full | Tarefas que tocam model, mais de um app ou o contrato de sessão | `cd backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test && coverage report -m` |
| App | Tarefas do `frontend-mobile` | `cd frontend-mobile && npx tsc --noEmit` |
| Build | Fim de fase e T24 | Full + App + as verificações de container do T24 |

**Baseline de testes do backend**, contado com `git grep -c "def test_" -- '*tests.py'` em `develop` (`b93baa5`):
- **330** métodos `test_` no projeto.
- Por app: `users` 150, `hairmatch` 39, `availability` 32, `service` 28, `preferences` 25, `review` 17, `chatbot` 16, `reserve` 14, `agenda` 9.

Nenhuma tarefa pode reduzir esses números. Asserts que mudam de 403/500/200 para 401 por causa do novo contrato (Assumptions do spec) são **ajustados**, não removidos. T1 confirma o baseline rodando a suíte antes de mudar qualquer coisa.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação do backend (aditiva)

```
T1 → T2 → T5
T3 → T5
T4
```

### Phase 2: Leitores de sessão no autenticador central

```
T6
T7
T8
T9
```

### Phase 3: Cognito como provedor de e-mail/senha

```
T10 → T11
T10 → T12
T10 → T13 → T16
T10 → T14
T15
```

### Phase 4: Seed e ambiente local

```
T17
T18 → T19 → T20
```

### Phase 5: App e verificação ponta a ponta

```
T21 → T22 → T24
T21 → T23 → T24
```

---

## Task Breakdown

### Phase 1: Fundação do backend (aditiva) (tarefas)

#### T1: Criar o fake de Cognito para os testes

**What**: Criar `FakeCognitoIdp` conforme o `design.md` (métodos boto3, `jwks()`, `make_access_token`, `make_refresh_token`, `fail_next`, `calls`). Na mesma tarefa:
- trocar `PyJWT` por `PyJWT[crypto]` em `backend/requirements.txt`;
- adicionar `COGNITO_USER_POOL_ID`, `COGNITO_APP_CLIENT_ID` e `COGNITO_USE_FAKE = 'test' in sys.argv` em `backend/hairmatch/settings.py`;
- escrever os testes unitários do fake.

**Where**: `backend/users/cognito_fake.py` (novo)
**Depends on**: None
**Reuses**: estilo de `SimpleTestCase` de `backend/hairmatch/tests.py`
**Requirement**: COG-08 (política no fake), base para COG-17 a COG-49

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Baseline confirmado: `python manage.py test` passa com 330 testes antes da mudança
- [x] `FakeCognitoIdpTest` cobre:
  - [x] `sign_up` com `Senha123` → `UserSub`
  - [x] `sign_up` com `senha123`, `SENHA123`, `Senhaabc` e `Se1` → `ClientError` `InvalidPasswordException`
  - [x] `sign_up` repetido com `A@x.com` e `a@x.com` → `UsernameExistsException`
  - [x] `initiate_auth` `USER_PASSWORD_AUTH` com senha certa → tokens. O access token decodifica com a chave do `jwks()`, com `token_use="access"`, `client_id` e `iss` corretos.
  - [x] Senha errada → `NotAuthorizedException`
  - [x] `REFRESH_TOKEN_AUTH` depois de `revoke_token` → `NotAuthorizedException`
  - [x] `fail_next('initiate_auth', EndpointConnectionError(...))` levanta exatamente uma vez
- [x] Gate check passes: `cd backend && python manage.py test users`
- [x] Test count: ≥ 150 + novos em `users`, sem remoções

**Tests**: unit
**Gate**: quick

**Commit**: `test(users): add in-memory Cognito fake for the test suite`

---

#### T2: Criar o `CognitoService` (wrapper boto3)

**What**: Criar `get_cognito()`, `reset_cognito()`, `CognitoService` e as exceções de domínio conforme o `design.md`: mapeamento de erros, log WARNING sem segredo, IDs por env ou por busca de nome, `issuer`, `fetch_jwks()` e compensação quando o `AdminConfirmSignUp` falha. Os testes unitários vão na mesma tarefa.
**Where**: `backend/users/cognito.py` (novo). Também `backend/hairmatch/test_runner.py` (novo) e `TEST_RUNNER` em `settings.py`: o runner chama `reset_cognito()` a cada teste, porque o banco faz rollback entre testes e o fake em memória não faria. Sem isso, os testes de register do T10 receberiam 409 pelos e-mails repetidos.
**Depends on**: T1
**Reuses**: padrão lazy de `backend/hairmatch/storage.py:26-32`; `requests` (`backend/requirements.txt`)
**Requirement**: COG-03, COG-04, COG-47, COG-48, COG-49

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `CognitoServiceTest` cobre:
  - [x] Cada código de `ClientError` (`InvalidPasswordException`, `UsernameExistsException`, `NotAuthorizedException`, `UserNotFoundException`, `TooManyRequestsException`, `LimitExceededException`, `InternalErrorException`, código desconhecido) e `EndpointConnectionError` → a exceção de domínio da tabela do design
  - [x] `assertLogs('users.cognito', 'WARNING')` registra operação + código, e a senha usada não aparece em nenhuma linha (COG-49)
  - [x] Com `COGNITO_USER_POOL_ID`/`COGNITO_APP_CLIENT_ID` definidos (`override_settings`), nenhuma chamada `list_user_pools` em `fake.calls` (COG-03)
  - [x] Vazios → resolve `hairmatch-dev`/`hairmatch-backend` pela busca
  - [x] Pool inexistente → `CognitoUnavailable`
  - [x] `issuer == "https://cognito-idp.us-east-2.amazonaws.com/<pool>"`
  - [x] Com `AWS_ENDPOINT_URL_COGNITO_IDENTITY_PROVIDER` e `AWS_ENDPOINT_URL` diferentes no env (`patch.dict(os.environ)`), um `boto3.client('cognito-idp')` real (sem rede) tem `meta.endpoint_url` igual ao primeiro, e `boto3.client('s3')` igual ao segundo (COG-04)
  - [x] `sign_up_confirmed` com `fail_next('admin_confirm_sign_up', ...)` → `admin_delete_user` chamado e exceção propagada
  - [x] `admin_delete_user` com usuário inexistente → sem exceção
  - [x] `fetch_jwks` com `requests.get` patchado para `ConnectionError` e para status 500 → `CognitoUnavailable`
- [x] Gate check passes: `cd backend && python manage.py test users`
- [x] Test count: T1 + novos, sem remoções

**Tests**: unit
**Gate**: quick

**Commit**: `feat(users): add boto3 Cognito service with domain errors`

---

#### T3: Adicionar `User.cognito_sub`

**What**: Adicionar `cognito_sub = CharField(max_length=255, unique=True, null=True, blank=True)` e gerar a migration `0008_user_cognito_sub`.
**Where**: `backend/users/models.py` (modificar). A migration é gerada pelo `makemigrations`.
**Depends on**: None
**Reuses**: formato de `google_id` (`backend/users/models.py:43`, migration `0005_user_google_id.py`)
**Requirement**: COG-05, COG-17

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `python manage.py makemigrations --check --dry-run` sem pendências depois da migration gerada
- [x] Gate check passes (Full): a suíte inteira passa com 330 testes ou mais

**Tests**: none
**Gate**: full

**Commit**: `feat(users): add cognito_sub to User`

---

#### T4: Adicionar os helpers de cookie do Cognito em `auth_tokens`

**What**: Adicionar `set_cognito_cookies(response, tokens)`, `set_access_cookie(response, access_token)` e `clear_auth_cookies(response)` com os atributos do spec (`jwt` com `max_age=3600`; `refresh_token` com `path="/api/auth/"` e `max_age=2592000`; `httponly`, `samesite="None"`, `secure`). O `issue_session_token` **não muda** nesta tarefa (a troca é no T16).
**Where**: `backend/users/auth_tokens.py` (modificar)
**Depends on**: None
**Reuses**: `set_session_cookie` (`backend/users/auth_tokens.py:24-32`)
**Requirement**: COG-12, COG-25, COG-27, COG-28

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `AuthTokensTest` ganha testes com os atributos exatos de cada cookie (`max-age`, `path`, `httponly`, `samesite`, `secure`) e confirma que `clear_auth_cookies` expira os dois com o mesmo `path`
- [x] Gate check passes: `cd backend && python manage.py test users`
- [x] Test count: T2 + novos, sem remoções

**Tests**: unit
**Gate**: quick

**Commit**: `feat(users): add Cognito cookie helpers`

---

#### T5: Criar o autenticador central

**What**: Criar `authenticate_request`, `authenticated_user` e `SessionUser` conforme o `design.md`: caminho Cognito (RS256 + JWKS com cache e nova busca por `kid` desconhecido) e caminho Google no formato novo (HS256 + `SECRET_KEY` + `iss="hairmatch"` + `token_use="session"`). Inclui um caminho **legado temporário**: HS256 com `'secret'`, sem `iss`, payload `{id}`. Ele é marcado com `# TEMPORARY: removed in T16` e mantém o login bcrypt funcionando até a Phase 3.
**Where**: `backend/users/authentication.py` (novo)
**Depends on**: T2, T3
**Reuses**: `get_cognito()` (T2); `jwt` (PyJWT)
**Requirement**: COG-17, COG-18, COG-19, COG-23, COG-24

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `AuthenticationTest` cobre:
  - [x] Access token do fake → `SessionUser(provider="cognito")` do `User` com aquele `cognito_sub` (COG-17)
  - [x] Sessão Google no formato novo → `provider="google"` (COG-18)
  - [x] Cada caso de COG-19 → `None`, com um teste por caso: sem cookie, assinatura de outra chave RSA, expirado, `iss` de outro pool, `client_id` errado, `token_use="id"`, refresh token do fake, HS256 com `iss` do Cognito, RS256 com `iss="hairmatch"`, `alg=none`, `sub` sem `User`
  - [x] `authenticated_user` devolve 401 com `{"error": "Sessão inválida ou expirada."}` para os casos acima
  - [x] `kid` desconhecido → uma nova busca do JWKS. Continua desconhecido → 401, e `fetch_jwks` é chamado no máximo 2 vezes na requisição (COG-23)
  - [x] `fetch_jwks` levanta `CognitoUnavailable` → `authenticated_user` devolve 503 com a mensagem do spec (COG-24)
  - [x] Caminho legado aceita `jwt.encode({'id', 'exp', 'iat'}, 'secret')`. Esse teste é marcado para inversão no T16.
- [x] Gate check passes: `cd backend && python manage.py test users`
- [x] Test count: T4 + novos, sem remoções

**Tests**: unit
**Gate**: quick

**Commit**: `feat(users): add central cookie authenticator for Cognito and Google sessions`

---

### Phase 2: Leitores de sessão no autenticador central (tarefas)

#### T6: Migrar os leitores de sessão de `users` para o autenticador

**What**:
- `LoginView.get` passa a usar `authenticate_request`: `True`/`False` sempre com 200, e `CognitoUnavailable` vira `False`.
- `ChangePasswordView.put` e `UserInfoCookieView.get/put/delete` passam a usar `authenticated_user` (401 no lugar de 403, 500 ou 200 `{'authenticated': False}`).
- Os `jwt.decode` dessas views saem, e a regra de negócio não muda.
- Os asserts dos testes afetados são ajustados para 401.

**Where**: `backend/users/views.py` (modificar)
**Depends on**: T5
**Reuses**: `authenticated_user` (T5)
**Requirement**: COG-21, COG-22

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -n "jwt.decode" backend/users/views.py` não encontra nada
- [ ] `GET /api/auth/user`: token do fake → `true`; `signup_token` no cookie → `false` (GAUTH-14 continua passando); lixo → `false`, nunca 500
- [ ] `UserInfoCookieView` e `ChangePasswordView` sem cookie ou com token inválido → 401 com a mensagem do spec. Assinatura inválida, que antes dava 500, tem teste próprio.
- [ ] Gate check passes: `cd backend && python manage.py test users`
- [ ] Test count: ≥ contagem do T5 em `users`, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `refactor(users): read the session through the central authenticator`

---

#### T7: Migrar `availability` para o autenticador

**What**: `CreateAvailability.post` passa a usar `authenticated_user`, e o `jwt.decode` com `'secret'` sai. Os testes de token ausente ou expirado passam a afirmar 401, e entra um teste com access token do fake.
**Where**: `backend/availability/views.py` (modificar)
**Depends on**: T5
**Reuses**: `authenticated_user` (T5); helpers de `backend/availability/tests.py:50`
**Requirement**: COG-22

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Sem `jwt.decode` em `backend/availability/views.py`
- [ ] Access token do fake de um cabeleireiro → 201. Sem cookie → 401. Token assinado com outra chave → 401.
- [ ] Gate check passes: `cd backend && python manage.py test availability`
- [ ] Test count: ≥ 32 em `availability`, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `refactor(availability): authenticate through the central authenticator`

---

#### T8: Migrar `review` para o autenticador

**What**: `CreateReview.post`, `UpdateReview.put` e `RemoveReview.delete` passam a usar `authenticated_user`, e os três `jwt.decode` saem. Os asserts de token ausente, inválido ou expirado viram 401, e entram testes com access token do fake.
**Where**: `backend/review/views.py` (modificar)
**Depends on**: T5
**Reuses**: `authenticated_user` (T5); `login_as_customer` (`backend/review/tests.py:134`)
**Requirement**: COG-22

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Sem `jwt.decode` em `backend/review/views.py`
- [ ] As três rotas aceitam access token do fake e recusam com 401 um cookie ausente e um refresh token
- [ ] Gate check passes: `cd backend && python manage.py test review`
- [ ] Test count: ≥ 17 em `review`, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `refactor(review): authenticate through the central authenticator`

---

#### T9: Migrar `preferences` para o autenticador

**What**: `AssignPreferenceToUser.post` e `UnnassignPreferenceFromUser.post` passam a usar `authenticated_user`, e os dois `jwt.decode` saem. Os asserts viram 401 onde o contrato muda, e entram testes com access token do fake.
**Where**: `backend/preferences/views.py` (modificar)
**Depends on**: T5
**Reuses**: `authenticated_user` (T5); `login_user` (`backend/preferences/tests.py:54`)
**Requirement**: COG-22

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Sem `jwt.decode` em `backend/preferences/views.py`
- [ ] As duas rotas aceitam access token do fake e recusam com 401 um cookie ausente e um token assinado com outra chave
- [ ] Gate check passes: `cd backend && python manage.py test preferences`
- [ ] Test count: ≥ 25 em `preferences`, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `refactor(preferences): authenticate through the central authenticator`

---

### Phase 3: Cognito como provedor de e-mail/senha (tarefas)

#### T10: Cadastro e login por e-mail/senha no Cognito

**What**:
- `RegisterView.post` (caminho e-mail/senha):
  - roda as validações locais primeiro;
  - chama `sign_up_confirmed` e depois os inserts em `transaction.atomic`;
  - compensa com `admin_delete_user` em qualquer erro depois do sign-up;
  - tira `bcrypt` e `replace(' ', '')`.
- `LoginView.post`:
  - valida o corpo;
  - devolve 403 para conta Google;
  - chama `authenticate`, busca o `User` por `cognito_sub` e chama `set_cognito_cookies`;
  - mantém `response.data['jwt']`.
- Um `_cognito_error_response` compartilhado cobre 503 e 429.

As duas views mudam juntas porque todos os testes do projeto se autenticam por register → login (ver a nota de ordem no topo).
**Where**: `backend/users/views.py` (modificar)
**Depends on**: T2, T3, T4, T5, T6
**Reuses**: validações atuais (`backend/users/views.py:47-65`); `_create_role_profile` (`:166-189`); `get_cognito()` (T2); `set_cognito_cookies` (T4)
**Requirement**: COG-05, COG-06, COG-07, COG-08, COG-09, COG-10, COG-11, COG-12, COG-13, COG-14, COG-15, COG-16, COG-47, COG-48

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cadastro:
  - [ ] Cliente e cabeleireiro → 201, `User.cognito_sub == UserSub`, `password is None`, usuário presente no fake (COG-05, COG-06)
  - [ ] E-mail/telefone duplicado no Postgres, campo faltando e telefone curto → status e mensagem de hoje, com `fake.calls` sem `sign_up` (COG-07)
  - [ ] Senha `senha123` → 400 com a mensagem de COG-08 e zero linhas
  - [ ] `UsernameExistsException` (e-mail só no fake) → 409 e zero linhas (COG-09)
  - [ ] Foto inválida, preferências inválidas e falha no insert (patch em `_create_role_profile`) depois do sign-up → `admin_delete_user` em `fake.calls`, zero `User`/`Customer`/`Hairdresser`, e status 400/400/500 (COG-10)
  - [ ] Caminho Google: todos os testes `GoogleRegisterTest` passam sem nenhuma chamada no fake (COG-11)
- [ ] Login:
  - [ ] 200 com os dois cookies e os atributos do spec, e o `jwt` aceito por `GET /api/auth/user` (COG-12)
  - [ ] Senha errada e e-mail inexistente → 401 "E-mail ou senha inválidos." sem cookie (COG-13)
  - [ ] Conta Google → 403, sem chamada no fake (COG-14)
  - [ ] Usuário no fake sem `User` correspondente → 401 (COG-15)
  - [ ] Corpo sem `email`, sem `password` ou vazio → 400 "Informe e-mail e senha." (COG-16)
- [ ] Com `fail_next(..., EndpointConnectionError)`: cadastro e login → 503, zero linhas novas. `TooManyRequestsException` → 429. (COG-47, COG-48)
- [ ] `grep -n bcrypt backend/users/views.py` só encontra o uso restante em `ChangePasswordView` (sai no T13)
- [ ] Gate check passes (Full): `makemigrations --check` + suíte inteira. Os helpers register → login de todos os apps passam com o fake.
- [ ] Test count: ≥ 330 + novos, sem remoções

**Tests**: integration
**Gate**: full

**Commit**: `feat(users): register and log in e-mail accounts through Cognito`

---

#### T11: Criar o endpoint de refresh

**What**: Criar `RefreshView.post` e registrar a rota `auth/refresh` (name `refresh`) no `urls.py` de `users`. Lê o cookie `refresh_token`, chama `refresh` e `set_access_cookie`. Em `InvalidCredentials`, responde 401 e chama `clear_auth_cookies`. Os erros de serviço vão para `_cognito_error_response`.
**Where**: `backend/users/views.py` (modificar)
**Depends on**: T10
**Reuses**: `set_access_cookie` e `clear_auth_cookies` (T4); `_cognito_error_response` (T10)
**Requirement**: COG-25, COG-26, COG-27

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Depois do login, `POST /api/auth/refresh` → 200 `{"message": "Session refreshed"}`, com um `jwt` novo aceito por `GET /api/auth/user` (COG-25)
- [ ] Sem cookie → 401 "Sessão expirada. Entre novamente.", sem chamada no fake (COG-26)
- [ ] Refresh revogado no fake → 401 e os dois cookies expirados na resposta (COG-27)
- [ ] Gate check passes: `cd backend && python manage.py test users`
- [ ] Test count: T10 + novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `feat(users): add Cognito session refresh endpoint`

---

#### T12: Revogar a sessão no logout

**What**:
- `LogoutView.post` chama `revoke` quando há `refresh_token`.
- Qualquer `CognitoError` é engolido (com o log do T2).
- Chama `clear_auth_cookies` e devolve sempre 200 `{"message": "User logged out"}`.
- Remove a definição duplicada de `LogoutView` (`backend/users/views.py:477-483`).

**Where**: `backend/users/views.py` (modificar)
**Depends on**: T10
**Reuses**: `clear_auth_cookies` (T4); `get_cognito().revoke` (T2)
**Requirement**: COG-28, COG-29

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Logout depois do login → 200, dois cookies expirados e `revoke_token` em `fake.calls`. Depois disso, o refresh com o mesmo refresh token → 401 (COG-28).
- [ ] `fail_next('revoke_token', EndpointConnectionError(...))` → ainda 200 e cookies expirados. Sem cookie (sessão Google) → 200 (COG-29).
- [ ] `grep -c "class LogoutView" backend/users/views.py` → 1
- [ ] Gate check passes: `cd backend && python manage.py test users`
- [ ] Test count: T11 + novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `feat(users): revoke the Cognito session on logout`

---

#### T13: Trocar a senha pelo Cognito

**What**: `ChangePasswordView.put`:
- sessão Google → 403;
- valida `old_password` e `password` (400);
- chama `change_password(session.access_token, ...)`;
- `InvalidCredentials` → 400 "Senha atual incorreta.";
- `InvalidPassword` → 400 com a mensagem da política.

O último uso de `bcrypt` em `views.py` sai.
**Where**: `backend/users/views.py` (modificar)
**Depends on**: T10
**Reuses**: `authenticated_user` (T5); `get_cognito().change_password` (T2)
**Requirement**: COG-30, COG-31, COG-32, COG-33, COG-34

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Troca válida → 200, login com a senha nova → 200, login com a antiga → 401, `User.password` continua `None` (COG-30)
- [ ] Senha atual errada → 400 "Senha atual incorreta." (COG-31)
- [ ] Senha nova `abc` → 400 com a mensagem de COG-08 (COG-32)
- [ ] Sem `old_password` ou sem `password` → 400, sem chamada no fake (COG-33)
- [ ] Sessão Google → 403 com a mensagem do spec (COG-34)
- [ ] `grep -n bcrypt backend/users/views.py` não encontra nada
- [ ] Gate check passes: `cd backend && python manage.py test users`
- [ ] Test count: T12 + novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `feat(users): change passwords through Cognito`

---

#### T14: Sincronizar a exclusão de conta com o Cognito

**What**:
- `UserInfoCookieView.delete` e `UserInfoView.delete` chamam `admin_delete_user` antes de `user.delete()` quando há `cognito_sub`.
- `CognitoUnavailable` → 503 e a linha fica.
- `UserInfoCookieView.delete` passa a usar `clear_auth_cookies`.

**Where**: `backend/users/views.py` (modificar)
**Depends on**: T10
**Reuses**: `get_cognito().admin_delete_user` (T2); `clear_auth_cookies` (T4)
**Requirement**: COG-35, COG-36

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `DELETE /api/user/authenticated` → 200 `{"message": "user deleted"}`, usuário fora do fake e do Postgres, dois cookies expirados. Com o usuário já ausente no fake → 200 (COG-35).
- [ ] `DELETE /api/user/<email>` de conta Cognito → sai do fake e do Postgres. Com `fail_next(..., EndpointConnectionError)` → 503 e a linha continua (COG-36).
- [ ] Conta Google (sem `cognito_sub`) → apagada sem chamada no fake
- [ ] Gate check passes: `cd backend && python manage.py test users`
- [ ] Test count: T13 + novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `feat(users): delete the Cognito user with the account`

---

#### T15: Recusar a troca de e-mail no perfil

**What**: `UserInfoCookieView.put` responde 400 `{"error": "A troca de e-mail não é suportada."}` quando `email` difere do atual, antes de alterar qualquer campo. O mesmo e-mail segue o fluxo normal.
**Where**: `backend/users/views.py` (modificar)
**Depends on**: T6
**Reuses**: `allowed_fields` (`backend/users/views.py:390-398`)
**Requirement**: COG-37

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `PUT` com outro e-mail + `first_name` novo → 400, e nenhum campo muda no banco
- [ ] `PUT` com o mesmo e-mail + `first_name` novo → 200 e o nome muda
- [ ] Os testes existentes que trocavam e-mail são ajustados para o novo contrato, sem remoção
- [ ] Gate check passes: `cd backend && python manage.py test users`
- [ ] Test count: T14 + novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `fix(users): reject e-mail changes on profile update`

---

#### T16: Novo formato da sessão Google e fim do legado

**What**:
- `issue_session_token` passa a `{id, iss: "hairmatch", token_use: "session", iat, exp}` com `settings.SECRET_KEY` e `max_age=3600` no cookie.
- O caminho legado do T5 sai de `users/authentication.py`, e o teste do legado é invertido para esperar recusa.
- `bcrypt` sai de `backend/requirements.txt`.
- Os testes que montam tokens com `'secret'` (`backend/users/tests.py:538`, `:2028`) ou decodificam com `'secret'` (`:1832`, `:1843`, `:2075`, `:2243`) passam a usar `issue_session_token` ou `jwt.decode` com `SECRET_KEY`.

**Where**: `backend/users/auth_tokens.py` (modificar)
**Depends on**: T13, T7, T8, T9
**Reuses**: `create_signup_token` (mesma chave, sem `iss`)
**Requirement**: COG-06, COG-18, COG-20

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Token `{id, exp, iat}` assinado com `'secret'` → 401 em uma rota de COG-22 e `false` em `GET /api/auth/user` (COG-20)
- [ ] `signup_token` no cookie → 401 em rota protegida (COG-20)
- [ ] Login Google (`GoogleAuthViewTest`) emite o formato novo, aceito por todas as rotas de COG-22 (COG-18)
- [ ] `grep -rn "'secret'" backend --include=*.py` fora de `.venv` não encontra nada
- [ ] `grep -rn "jwt.decode" backend --include=*.py` fora de `.venv` e dos testes só encontra `users/authentication.py` e `users/auth_tokens.py`
- [ ] `grep -rn bcrypt backend --include=*.py backend/requirements.txt` fora de `.venv` não encontra nada
- [ ] Gate check passes (Full)
- [ ] Test count: ≥ 330 + novos, sem remoções

**Tests**: unit
**Gate**: full

**Commit**: `refactor(users): sign Google sessions with SECRET_KEY and drop legacy tokens`

---

### Phase 4: Seed e ambiente local (tarefas)

#### T17: Seed de cabeleireiros pelo Cognito

**What**:
- Cada cabeleireiro novo ganha `cognito_sub = get_cognito().sign_up_confirmed(email, SEED_PASSWORD)`, com `SEED_PASSWORD = "Senha123"`.
- Saem a chave `password` e o `set_password`.
- Entra `restore_missing_cognito_users()`, que roda em todo boot junto com `restore_missing_pictures`. Ele cobre os usuários `role="hairdresser"`, com `google_id` nulo e e-mail `^hairdresser\d+_`:
  - recria no Cognito os que estão com `cognito_sub` nulo ou ausentes no Cognito;
  - atualiza o `sub` divergente.

**Where**: `backend/users/management/commands/populate_hairdressers.py` (modificar)
**Depends on**: T10
**Reuses**: `restore_missing_pictures` (`:26`) como modelo; `sign_up_confirmed` e `admin_get_sub` (T2)
**Requirement**: COG-38, COG-39, COG-40

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `PopulateHairdressersCommandTest`:
  - [ ] Depois de `call_command`, todo cabeleireiro tem `cognito_sub`, `password is None`, e `POST /api/auth/login` com um e-mail do seed e `Senha123` → 200 (COG-38)
  - [ ] Zerar o `cognito_sub` de um usuário e apagar outro do fake → novo `call_command` recria os dois, sem novas linhas `User` (COG-39)
  - [ ] Um usuário fora do padrão `hairdresser<N>_` não é tocado (COG-39)
  - [ ] Segundo `call_command` sem mudanças → nenhum `sign_up` novo em `fake.calls` e `cognito_sub` inalterado (COG-40)
- [ ] Gate check passes: `cd backend && python manage.py test users`
- [ ] Test count: T16 + novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `feat(seed): create seeded hairdressers in Cognito`

---

#### T18: Script de init do Cognito no MiniStack

**What**: Criar o script idempotente, no estilo `set -e` + `echo` do `01-resources.sh`:
- sai se o pool `hairmatch-dev` já existe;
- senão cria o pool e o client com os parâmetros exatos do `design.md` (política sem símbolo, `CaseSensitive=false`, fluxos, validade 60 min / 30 dias);
- imprime os IDs.

**Where**: `docker/ministack/init/01-cognito.sh` (novo, executável)
**Depends on**: None
**Reuses**: `docker/localstack/init/01-resources.sh`
**Requirement**: COG-01, COG-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `bash -n docker/ministack/init/01-cognito.sh` sem erro
- [ ] Rodado duas vezes contra o MiniStack (`docker run --rm -p 4567:4566 ministackorg/ministack` + `AWS_ENDPOINT_URL=http://localhost:4567`), `list-user-pools` mostra um único `hairmatch-dev`, e `describe-user-pool` mostra `RequireSymbols=false`
- [ ] Gate: verificação manual acima (camada infra = none)

**Tests**: none
**Gate**: build

**Commit**: `chore(docker): add idempotent Cognito init script for MiniStack`

---

#### T19: Serviço `ministack` no docker compose

**What**:
- Adicionar o serviço `ministack` conforme o `design.md`: imagem, porta `4567:4566`, `PERSIST_STATE=1` com o volume `ministack_state`, init em `/etc/localstack/init/ready.d` e healthcheck que só passa com o pool criado.
- No serviço `django`, adicionar `depends_on` (`service_healthy`), `AWS_ENDPOINT_URL_COGNITO_IDENTITY_PROVIDER=http://ministack:4566`, `COGNITO_USER_POOL_ID` e `COGNITO_APP_CLIENT_ID`.

**Where**: `docker/docker-compose.yml` (modificar)
**Depends on**: T18
**Reuses**: bloco do `localstack` (`docker/docker-compose.yml:95-119`)
**Requirement**: COG-01, COG-02, COG-03, COG-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `docker compose -f docker/docker-compose.yml --env-file docker/.env config` sem erro
- [ ] `docker compose up`: `hairmatch_ministack` fica `healthy`, e o `django` só sobe depois
- [ ] Gate: verificação manual acima. O fluxo completo é validado no T24.

**Tests**: none
**Gate**: build

**Commit**: `chore(docker): run Cognito locally on MiniStack`

---

#### T20: Documentar o Cognito local e as env vars

**What**:
- `docker/.env.example` ganha `COGNITO_USER_POOL_ID=` e `COGNITO_APP_CLIENT_ID=` (vazios em dev, com comentário).
- O `README.md` ganha a seção "Cognito local (MiniStack)":
  - motivo (licença `freemium` do LocalStack sem `cognito-idp`) e porta 4567;
  - `aws --endpoint-url http://localhost:4567 cognito-idp list-users`;
  - código fixo `123456`;
  - reset (`docker compose down -v`) e senha do seed `Senha123`;
  - configuração exigida do pool real (política, client, env vars);
  - reset do banco ao trocar de sistema de auth (contas bcrypt antigas não logam).

**Where**: `README.md` (modificar)
**Depends on**: T19
**Reuses**: seção `## LocalStack (AWS emulation)` (`README.md:13-27`)
**Requirement**: COG-01, COG-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Seguindo só o README em um clone limpo, o dev sobe o ambiente e loga com um usuário do seed (verificado no T24)
- [ ] Gate: revisão manual (camada infra = none)

**Tests**: none
**Gate**: build

**Commit**: `docs: document local Cognito on MiniStack`

---

### Phase 5: App e verificação ponta a ponta (tarefas)

#### T21: Refresh automático no `axiosInstance`

**What**:
- Interceptor de resposta: em 401 fora de `AUTH_EXCLUDED`, marca `_retry`, aguarda uma única `refreshPromise` compartilhada (`POST /api/auth/refresh`) e repete a chamada uma vez.
- Se o refresh falha, chama o handler registrado por `setSessionExpiredHandler` e rejeita, sem repetir.

**Where**: `frontend-mobile/services/axios-instance.ts` (modificar)
**Depends on**: T11
**Reuses**: interceptor existente (`frontend-mobile/services/axios-instance.ts:26-39`)
**Requirement**: COG-41, COG-42

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `setSessionExpiredHandler` exportado
- [ ] 401 em rota de `AUTH_EXCLUDED` não dispara refresh
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`
- [ ] Comportamento verificado no roteiro do T24 (passos 6 e 7)

**Tests**: none
**Gate**: app

**Commit**: `feat(app): refresh the Cognito session on 401`

---

#### T22: Levar as chamadas cruas de review e Google para o `axiosInstance`

**What**:
- `createReview` e `deleteReview` usam `axiosInstance`. `createReview` passa `headers: {'Content-Type': 'multipart/form-data'}` nas duas plataformas, porque o axios 1.x converte `FormData` em JSON com o header padrão `application/json`.
- `loginWithGoogle` (no serviço de auth do Google) usa `axiosInstance`. Continua fora do refresh por estar em `AUTH_EXCLUDED`.

**Where**: `frontend-mobile/services/review.service.ts` (modificar)
**Depends on**: T21
**Reuses**: `axiosInstance` (T21)
**Requirement**: COG-44

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -n "from 'axios'" frontend-mobile/services/review.service.ts frontend-mobile/services/google-auth.service.ts` não encontra nada
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`
- [ ] Criar review com foto funciona no web e no Android (T24, passo 5)

**Tests**: none
**Gate**: app

**Commit**: `refactor(app): send review and Google calls through axiosInstance`

---

#### T23: Login, logout e restauração da sessão no contexto de auth

**What**: Em `app/_layout.tsx`:
- `signIn` e `signOut` passam a usar `axiosInstance`, com `withCredentials`. No `signOut`, a limpeza de estado vai para o `finally` (COG-43).
- O bootstrap passa a ser `loadSession()`. Se não autenticado: `POST /api/auth/refresh`, depois `loadSession()` de novo, com `isLoading` até terminar (COG-45, COG-46).
- Saem `AsyncStorage`, `fetchUserInfo` e o header `Bearer`.
- `setSessionExpiredHandler` registra a limpeza de estado + `router.replace('/(auth)/login')` (COG-42).

**Where**: `frontend-mobile/app/_layout.tsx` (modificar)
**Depends on**: T21
**Reuses**: `loadSession` (`frontend-mobile/app/_layout.tsx:57-73`)
**Requirement**: COG-42, COG-43, COG-45, COG-46

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -n "AsyncStorage\|Bearer" frontend-mobile/app/_layout.tsx` não encontra nada
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`
- [ ] Comportamento verificado no roteiro do T24 (passos 3, 8 e 9)

**Tests**: none
**Gate**: app

**Commit**: `feat(app): restore and end sessions through the backend cookies`

---

#### T24: Verificação ponta a ponta (UAT)

**What**: Rodar o roteiro abaixo com `docker compose up` (banco zerado com `down -v`), no web (`npx expo start --web`) e no Android (APK `preview`), com cliente e cabeleireiro. Registrar o resultado em `validation.md` pelo Verifier.
**Where**: `.specs/features/cognito-auth/validation.md` (gerado pelo Verifier)
**Depends on**: T22, T23, T16, T17, T20
**Reuses**: roteiro de UAT do `google-auth`
**Requirement**: COG-01 a COG-49 (verificação ponta a ponta)

**Tools**:

- MCP: `claude-in-chrome` (web)
- Skill: `run`

**Done when**:

- [ ] 1. `hairmatch_ministack` fica `healthy`. `aws --endpoint-url http://localhost:4567 cognito-idp list-user-pools --max-results 10` mostra um `hairmatch-dev`. `docker exec hairmatch_django python -c "import boto3;print(boto3.client('cognito-idp').meta.endpoint_url)"` imprime `http://ministack:4566`. (COG-01, COG-04)
- [ ] 2. Login com um cabeleireiro do seed e `Senha123` cai na agenda. (COG-38)
- [ ] 3. Cadastro de cliente pelo wizard. O usuário aparece em `list-users`, com `cognito_sub` no Postgres e `password` nulo. O login cai na home. (COG-05, COG-12)
- [ ] 4. Login Google sem regressão (cliente existente). (COG-11, COG-18)
- [ ] 5. Criar e apagar uma review com foto; atribuir uma preferência. (COG-22, COG-44)
- [ ] 6. No web, apagar só o cookie `jwt` e navegar: a tela carrega, e o Network mostra `refresh` e depois o retry. (COG-41)
- [ ] 7. Apagar também o `refresh_token` e navegar: o app vai para o login, sem `ErrorModal`. (COG-42)
- [ ] 8. "Sair": cookies apagados. Depois disso, `POST /api/auth/refresh` com o refresh antigo (curl) → 401. (COG-28, COG-43)
- [ ] 9. Fechar e reabrir o app logado: cai na home. No Android, matar o app e reabrir. (COG-45, COG-46)
- [ ] 10. `docker compose restart ministack`: o mesmo `Id` de pool, e login ainda funciona. (COG-02)
- [ ] 11. `docker compose stop ministack`: o login mostra "Serviço de autenticação indisponível...". (COG-47)
- [ ] Gate (Build): Full + App passam

**Tests**: none
**Gate**: build

**Commit**: `docs(specs): record cognito-auth end-to-end verification`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

Phase 1:  T1 ------→ T2 ------→ T5
          T3 ------→ T5
          T4
Phase 2:  T6
          T7
          T8
          T9
Phase 3:  T10 -----→ T11
          T10 -----→ T12
          T10 -----→ T13 -----→ T16
          T10 -----→ T14
          T15
Phase 4:  T17
          T18 -----→ T19 -----→ T20
Phase 5:  T21 -----→ T22 -----→ T24
          T21 -----→ T23 -----→ T24
```

São 24 tarefas, então no Execute o empacotamento dá cerca de 4 lotes de fases inteiras (por exemplo {P1}, {P2}, {P3}, {P4 + P5}). O Execute oferece sub-agentes antes de começar. Se o usuário recusar, tudo roda inline, em sequência.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Fake de Cognito | 1 módulo novo + 1 linha em requirements + 3 settings | ✅ Granular (config coesa com o fake) |
| T2: `CognitoService` | 1 módulo | ✅ Granular |
| T3: `User.cognito_sub` | 1 campo + migration gerada | ✅ Granular |
| T4: Helpers de cookie | 3 funções coesas em 1 arquivo | ✅ Granular |
| T5: Autenticador | 1 módulo | ✅ Granular |
| T6: Leitores de `users` | 3 views no mesmo arquivo, mesma troca mecânica | ⚠️ OK (coeso) |
| T7: `availability` | 1 view | ✅ Granular |
| T8: `review` | 3 views no mesmo arquivo, mesma troca mecânica | ⚠️ OK (coeso) |
| T9: `preferences` | 2 views no mesmo arquivo, mesma troca mecânica | ⚠️ OK (coeso) |
| T10: Cadastro + login | 2 views no mesmo arquivo. Separar quebraria todos os testes register → login entre os commits. | ⚠️ OK (acoplamento de teste justificado) |
| T11: Refresh | 1 endpoint | ✅ Granular |
| T12: Logout | 1 endpoint | ✅ Granular |
| T13: Troca de senha | 1 endpoint | ✅ Granular |
| T14: Exclusão de conta | 2 handlers `delete` com a mesma regra | ⚠️ OK (coeso) |
| T15: Troca de e-mail | 1 guarda em 1 handler | ✅ Granular |
| T16: Sessão Google + fim do legado | 1 função + remoção do caminho temporário + 1 linha de requirements | ⚠️ OK (fecha a transição de formato em um commit) |
| T17: Seed | 1 command | ✅ Granular |
| T18: Init script | 1 script | ✅ Granular |
| T19: Compose | 1 arquivo | ✅ Granular |
| T20: Docs | README + `.env.example` | ✅ Granular |
| T21: Interceptor | 1 arquivo | ✅ Granular |
| T22: Serviços com axios cru | 2 serviços com a mesma troca | ⚠️ OK (coeso) |
| T23: Contexto de auth | 1 arquivo | ✅ Granular |
| T24: UAT | 1 roteiro | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | nenhuma aresta de entrada | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | None | nenhuma aresta de entrada | ✅ Match |
| T4 | None | nenhuma aresta de entrada | ✅ Match |
| T5 | T2, T3 | T2 → T5, T3 → T5 | ✅ Match |
| T6 | T5 (Phase 1) | nenhuma aresta de entrada dentro da Phase 2 | ✅ Match |
| T7 | T5 (Phase 1) | nenhuma aresta de entrada dentro da Phase 2 | ✅ Match |
| T8 | T5 (Phase 1) | nenhuma aresta de entrada dentro da Phase 2 | ✅ Match |
| T9 | T5 (Phase 1) | nenhuma aresta de entrada dentro da Phase 2 | ✅ Match |
| T10 | T2, T3, T4, T5 (Phase 1), T6 (Phase 2) | nenhuma aresta de entrada dentro da Phase 3 | ✅ Match |
| T11 | T10 | T10 → T11 | ✅ Match |
| T12 | T10 | T10 → T12 | ✅ Match |
| T13 | T10 | T10 → T13 | ✅ Match |
| T14 | T10 | T10 → T14 | ✅ Match |
| T15 | T6 (Phase 2) | nenhuma aresta de entrada dentro da Phase 3 | ✅ Match |
| T16 | T13, T7, T8, T9 (Phase 2) | T13 → T16 | ✅ Match |
| T17 | T10 (Phase 3) | nenhuma aresta de entrada dentro da Phase 4 | ✅ Match |
| T18 | None | nenhuma aresta de entrada | ✅ Match |
| T19 | T18 | T18 → T19 | ✅ Match |
| T20 | T19 | T19 → T20 | ✅ Match |
| T21 | T11 (Phase 3) | nenhuma aresta de entrada dentro da Phase 5 | ✅ Match |
| T22 | T21 | T21 → T22 | ✅ Match |
| T23 | T21 | T21 → T23 | ✅ Match |
| T24 | T22, T23, T16 (Phase 3), T17 e T20 (Phase 4) | T22 → T24, T23 → T24 | ✅ Match |

Nenhuma dependência aponta para uma fase posterior.

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Fake de Cognito (+ settings e requirements) | unit | unit | ✅ OK |
| T2 | Wrapper `users/cognito.py` | unit | unit | ✅ OK |
| T3 | Model + migration | none (build via `makemigrations --check`) | none, gate full | ✅ OK |
| T4 | `auth_tokens` | unit | unit | ✅ OK |
| T5 | Autenticador | unit | unit | ✅ OK |
| T6 | Views de `users` | integration | integration | ✅ OK |
| T7 | Views de `availability` | integration | integration | ✅ OK |
| T8 | Views de `review` | integration | integration | ✅ OK |
| T9 | Views de `preferences` | integration | integration | ✅ OK |
| T10 | Views de `users` | integration | integration | ✅ OK |
| T11 | Views de `users` | integration | integration | ✅ OK |
| T12 | Views de `users` | integration | integration | ✅ OK |
| T13 | Views de `users` | integration | integration | ✅ OK |
| T14 | Views de `users` | integration | integration | ✅ OK |
| T15 | Views de `users` | integration | integration | ✅ OK |
| T16 | `auth_tokens` + autenticador (+ requirements). Os asserts das rotas usam `APIClient`. | unit (maior tipo entre `auth_tokens`=unit e requirements=none) | unit, gate full | ✅ OK |
| T17 | Management command do seed | integration | integration | ✅ OK |
| T18 | Infra (init script) | none | none | ✅ OK |
| T19 | Infra (compose) | none | none | ✅ OK |
| T20 | Infra (docs e `.env.example`) | none | none | ✅ OK |
| T21 | App | none (tsc + UAT) | none | ✅ OK |
| T22 | App | none (tsc + UAT) | none | ✅ OK |
| T23 | App | none (tsc + UAT) | none | ✅ OK |
| T24 | Nenhum código (roteiro de verificação) | none | none | ✅ OK |
