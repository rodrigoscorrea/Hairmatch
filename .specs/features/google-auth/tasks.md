# Login e Cadastro via Google Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/google-auth/spec.md`
**Context**: `.specs/features/google-auth/context.md`
**Design**: `.specs/features/google-auth/design.md`
**Status**: Draft (aguardando aprovação para Execute)
**Branch sugerida**: `106-login-e-cadastro-via-google`, criada a partir de `develop`, seguindo o padrão `98-...` do repositório

**Pré-requisitos do Execute:**
- Client IDs do Google Cloud: Web (com JavaScript origins e redirect URIs de cada origem web) e Android (pacote `com.rodrigosc615.frontendmobile` + SHA-1 do keystore EAS). Só são necessários para o UAT (T23). Os testes do backend usam mock.
- Postgres acessível para os testes do backend (`docker compose up db`, com `DB_*` exportadas).
- `npm install` em `frontend-mobile/`: `node_modules` não está instalado no checkout.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas: `.github/workflows/hairmatch-backend-test.yml` (roda `coverage run manage.py test`, sem limite mínimo), `backend/users/tests.py` (padrão Django `TestCase` + `APIClient`), `frontend-mobile/package.json` (preset `jest-expo` sem nenhum teste). Frontend: decisão do usuário registrada em `context.md` (só teste manual). Backend: strong defaults.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: helpers de domínio (`auth_tokens`, `google_auth`) | unit | Todos os ramos; 1:1 com os ACs que implementam (GAUTH-01, 04, 05, 13, 14); todos os edge cases listados | `backend/users/tests.py` (novas classes `*Test`) | `cd backend && python manage.py test users` |
| Backend: views e rotas (`LoginView`, `GoogleAuthView`, `RegisterView`) | integration | Todas as rotas no escopo: happy path, cada edge case e cada erro do spec (400/401/403/409), incluindo "nenhuma linha criada" e "sem Set-Cookie" | `backend/users/tests.py` (`APIClient` + `reverse`, mock de `users.views.verify_google_id_token`) | `cd backend && python manage.py test users` |
| Backend: modelo, migration, settings, dependências | none | Só o gate de build (as migrations aplicam e a suíte inteira passa) | - | Full gate |
| Frontend: services, hooks, contexto, componentes, telas | none | Decisão do usuário. O gate é o `tsc` sem novos erros, mais o roteiro de UAT manual (T23). | - | App gate |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Os testes do backend precisam de Postgres: exporte `DB_HOST/DB_NAME/DB_USER/DB_PASSWORD`, ou rode dentro do container com `docker compose exec django python3 backend/manage.py test users`.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas de backend com testes unit/integration no app `users` | `cd backend && python manage.py test users` |
| Full | Tarefas que mexem em modelo, migration, settings ou dependências do backend, e no fim de cada fase de backend | `cd backend && coverage run manage.py test && coverage report -m` |
| App | Tarefas de frontend (`Tests: none`) | `cd frontend-mobile && npx tsc --noEmit 2>&1 \| grep -c "error TS"`. O resultado precisa ser **≤ baseline** registrado em T9. |
| Build | Fim da feature (T23) | Full + App |

Baseline de testes do backend: **219** métodos `test_` em todo o projeto, **72** em `backend/users/tests.py`, contados em `f835c88`. Nenhuma tarefa pode reduzir esses números.

Baseline App gate: 4 erros (medido em T9 depois do `npm install` e antes das dependências novas; erros pré-existentes em `app/(app)/(customer)/_layout.tsx`, `app/(app)/(customer)/hairdresser-reservation/[id].tsx`, `app/(app)/(hairdresser)/_layout.tsx` e `components/BottomBar.tsx`).

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação do backend

```
T1 → T5
T2 → T5
T3
T4
```

### Phase 2: Endpoints do backend

```
T6
T7 → T8
```

### Phase 3: Fundação do app

```
T9 → T13 → T14
T9 → T14
T10
T11
T12
```

### Phase 4: UI do app

```
T15 → T17
T16 → T17
T15 → T20
T16 → T20
T19 → T20
T18
T21
T22
```

### Phase 5: Fechamento

```
T23
```

---

## Task Breakdown

### Phase 1: Fundação do backend (tarefas)

#### T1: Adicionar `google-auth` e `requests` às dependências do backend

**What**: Fixar `google-auth` e `requests` em `backend/requirements.txt`. Hoje eles só chegam como dependência transitiva de `google.generativeai`.
**Where**: `backend/requirements.txt`
**Depends on**: None
**Reuses**: formato atual do arquivo (um pacote por linha)
**Requirement**: GAUTH-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `pip install -r requirements.txt` instala os dois pacotes em Python 3.9
- [x] `python -c "from google.oauth2 import id_token; from google.auth.transport import requests"` roda sem erro
- [x] Gate check passes: Full gate (219 testes passam)

**Tests**: none
**Gate**: full

**Commit**: `build(backend): add google-auth and requests dependencies`

---

#### T2: Configurar `GOOGLE_OAUTH_CLIENT_IDS` no backend

**What**: Ler `GOOGLE_OAUTH_CLIENT_IDS` (lista separada por vírgula, com espaços removidos e itens vazios descartados) em `settings.py`, e documentar a variável em `.env.example` e no bloco `environment` do serviço `django` em `docker-compose.yml`.
**Where**: `backend/hairmatch/settings.py`, `.env.example`, `docker-compose.yml`
**Depends on**: None
**Reuses**: padrão `os.getenv` de `backend/hairmatch/settings.py:31-36`
**Requirement**: GAUTH-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `settings.GOOGLE_OAUTH_CLIENT_IDS` vale `[]` sem a variável, e `['a', 'b']` com `" a, b ,"`
- [x] `.env.example` e `docker-compose.yml` listam a variável
- [x] Gate check passes: Full gate (219 testes passam)

**Tests**: none
**Gate**: full

**Commit**: `chore(backend): add GOOGLE_OAUTH_CLIENT_IDS setting`

---

#### T3: Adicionar `User.google_id` e a migration

**What**: Adicionar `google_id = CharField(max_length=255, unique=True, null=True, blank=True)` ao `User` e gerar a migration `0005_user_google_id` com `makemigrations`.
**Where**: `backend/users/models.py` (a migration é gerada)
**Depends on**: None
**Reuses**: estilo dos campos existentes em `backend/users/models.py:7-37`
**Requirement**: GAUTH-01, GAUTH-02, GAUTH-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `python manage.py makemigrations --check` não detecta mudanças pendentes depois da migration
- [x] `python manage.py migrate` aplica a `0005` em um banco limpo
- [x] Gate check passes: Full gate (219 testes passam)

**Tests**: none
**Gate**: full

**Commit**: `feat(users): add google_id field to User`

---

#### T4: Criar o helper `auth_tokens` (sessão e token de cadastro)

**What**: Criar `issue_session_token`, `set_session_cookie`, `create_signup_token`, `decode_signup_token`, `InvalidSignupToken` e `SIGNUP_TOKEN_TTL`, conforme o design.
**Where**: `backend/users/auth_tokens.py`
**Depends on**: None
**Reuses**: payload e atributos de cookie de `backend/users/views.py:120-135`
**Requirement**: GAUTH-01, GAUTH-13, GAUTH-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Nova classe `AuthTokensTest` em `backend/users/tests.py`. Ela testa que:
  - o token de sessão decodifica com `'secret'`/HS256 e tem `id` e `exp - iat == 3600 s`
  - o cookie `jwt` tem `httponly`, `samesite=None` e `secure`
  - o `signup_token` traz `email`, `sub` e `purpose` e expira em 30 min (usar tempo congelado com `unittest.mock.patch` no `datetime` do módulo)
  - um token expirado, adulterado, assinado com `'secret'` ou com outro `purpose` lança `InvalidSignupToken`
- [x] Gate check passes: Quick gate
- [x] Test count: 72 + ≥ 6 testes em `users` passam (nenhum removido) — 80 (72 + 8)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(users): add session and google signup token helpers`

---

#### T5: Criar o verificador `google_auth`

**What**: Criar `verify_google_id_token(token)` e `GoogleTokenError`, conforme o design: verificação com `audience=None`, checagem manual do `aud` contra `settings.GOOGLE_OAUTH_CLIENT_IDS`, normalização de `email_verified` e defaults `''` para os nomes.
**Where**: `backend/users/google_auth.py`
**Depends on**: T1, T2
**Reuses**: nada. Integração nova, documentada em `design.md`.
**Requirement**: GAUTH-04, GAUTH-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Nova classe `GoogleAuthVerifierTest`, com mock de `users.google_auth.id_token.verify_oauth2_token`. Ela testa que:
  - claims válidos com `aud` na lista retornam a identidade normalizada
  - `ValueError` vira `GoogleTokenError`
  - `GoogleAuthError` vira `GoogleTokenError`
  - um `aud` fora da lista é rejeitado
  - com a lista vazia, tudo é rejeitado
  - `email_verified` `'true'`/`True` vira `True`, e `'false'` ou ausente vira `False`
  - sem `given_name`/`family_name`, o resultado traz `''`
- [x] Gate check passes: Quick gate
- [x] Test count: contagem de T4 + ≥ 7 testes em `users` passam — 87 (80 + 7)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(users): add google id token verifier`

---

### Phase 2: Endpoints do backend (tarefas)

#### T6: Ajustar `LoginView` para contas Google e tokens inválidos

**What**:
- `post` passa a emitir a sessão via `set_session_cookie`, mantendo `response.data`.
- `post` responde 403 com a mensagem do GAUTH-11 quando `user.password` é nulo.
- `get` captura `jwt.InvalidTokenError` e responde `{'authenticated': False}`.

**Where**: `backend/users/views.py` (`LoginView`, linhas 108-157)
**Depends on**: T4
**Reuses**: `users/auth_tokens.py`
**Requirement**: GAUTH-11, GAUTH-14, GAUTH-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Todos os testes de `LoginViewTest` continuam passando sem alteração
- [x] Novos testes cobrem:
  - usuário com `password=None` recebe 403 com a mensagem exata do GAUTH-11
  - `GET /api/auth/user` com um `signup_token` no cookie responde 200 `{"authenticated": false}`
  - `GET /api/auth/user` com um token de assinatura inválida responde o mesmo
- [x] Gate check passes: Quick gate
- [x] Test count: contagem de T5 + ≥ 3 testes em `users` passam — 90 (87 + 3)

**Tests**: integration
**Gate**: quick

**Commit**: `fix(users): handle passwordless and invalid tokens in LoginView`

---

#### T7: Criar `GoogleAuthView` e a rota `auth/google`

**What**: Implementar `POST /api/auth/google` conforme o fluxo de 6 passos do design e registrar `path('auth/google', GoogleAuthView.as_view(), name='google_auth')` junto das outras rotas `auth/` em `backend/users/urls.py`. A rota fica na mesma tarefa, porque a view não é testável sem ela.
**Where**: `backend/users/views.py` (a rota vai em `backend/users/urls.py`)
**Depends on**: T3, T4, T5
**Reuses**: `auth_tokens`, `google_auth`, padrão `JsonResponse({'error': ...})`
**Requirement**: GAUTH-01, GAUTH-02, GAUTH-03, GAUTH-04, GAUTH-05, GAUTH-06, GAUTH-12, GAUTH-13, GAUTH-23

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Nova classe `GoogleAuthViewTest`, com mock de `users.views.verify_google_id_token`. Ela testa que:
  - `sub` já vinculado → 200 `authenticated` + cookie `jwt` que `GET /api/auth/user` aceita (GAUTH-01)
  - e-mail existente com maiúsculas diferentes e `google_id` nulo → vincula o `sub` e responde 200 (GAUTH-02)
  - sem `id_token` → 400, sem cookie (GAUTH-03)
  - `GoogleTokenError` → 401, sem cookie e sem mudança no banco (GAUTH-04)
  - `email_verified=False` → 403, sem mudança no banco (GAUTH-05)
  - e-mail vinculado a outro `sub` → 409 (GAUTH-06)
  - conta nova → 200 `signup_required` com `prefill` correto, sem cookie e com `User.objects.count()` inalterado (GAUTH-12)
  - o `signup_token` devolvido decodifica para o `email` e o `sub` (GAUTH-13)
  - uma segunda chamada da mesma conta nova volta a responder `signup_required` (GAUTH-23)
- [x] Gate check passes: Quick gate
- [x] Test count: contagem de T6 + ≥ 9 testes em `users` passam — 99 (90 + 9)

**Tests**: integration
**Gate**: quick

**Commit**: `feat(users): add google sign-in endpoint`

---

#### T8: Caminho Google no `RegisterView`

**What**:
- Extrair `_create_role_profile(user, data)` de `views.py:77-101`, sem mudar o caminho clássico.
- Adicionar `_register_with_google(request)`, com decode do token, validações, checagens de duplicidade (e-mail `iexact`, `sub`, `55`+telefone), `transaction.atomic`, 201 e `set_session_cookie`.
- Despachar para esse método quando o form traz `google_signup_token`.

**Where**: `backend/users/views.py` (`RegisterView`, linhas 28-105)
**Depends on**: T7
**Reuses**: bloco de preferências e perfil existente, `auth_tokens`
**Requirement**: GAUTH-15, GAUTH-16, GAUTH-17, GAUTH-18, GAUTH-19, GAUTH-20, GAUTH-21, GAUTH-22

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Todos os testes de `RegisterViewTest` continuam passando sem alteração
- [x] Nova classe `GoogleRegisterTest` (multipart, sem `password`). Ela testa que:
  - cliente → 201, com `User(password=None, google_id=sub, role='customer', phone='55…')` + `Customer.cpf` + cookie aceito por `/api/auth/user` (GAUTH-15)
  - cabeleireiro → 201, com `Hairdresser` com CNPJ e campos profissionais + cookie (GAUTH-16)
  - `email` e `password` enviados no form são ignorados e o e-mail do token vence (GAUTH-17)
  - token expirado ou adulterado → 401, com zero linhas novas (GAUTH-18). Um `google_signup_token` vazio segue o caminho clássico, que não muda, e não é caso deste teste.
  - telefone já existente como `55…` → 409, com zero linhas (GAUTH-19)
  - e-mail ou `sub` já existentes → 409 (GAUTH-20)
  - cada campo obrigatório ausente e um `role` inválido → 400, com zero linhas (GAUTH-21, usando `subTest`)
  - preferências com JSON inválido → 400 e zero `User`, `Customer` e `Hairdresser` (GAUTH-22)
  - fluxo ponta a ponta: `POST /auth/google` (conta nova) → `POST /auth/register` com o token devolvido → `GET /api/user/authenticated` devolve o perfil do papel
- [x] Gate check passes: Full gate (fim da fase de backend)
- [x] Test count: 219 + todos os novos testes das fases 1 e 2 passam (nenhum removido) — 256 no projeto (219 + 37), 109 em `users` (72 + 37)

**Tests**: integration
**Gate**: full

**Commit**: `feat(users): complete google sign-up through register endpoint`

---

### Phase 3: Fundação do app (tarefas)

#### T9: Instalar as dependências de Google Sign-In no app e registrar o baseline do `tsc`

**What**:
- Rodar `npm install`, registrar no `tasks.md` o número de erros de `npx tsc --noEmit` como **baseline do App gate**, e só então instalar as dependências novas.
- `npx expo install expo-auth-session expo-crypto @react-native-google-signin/google-signin`.
- Adicionar o config plugin `@react-native-google-signin/google-signin` ao `app.json`. Se o plugin exigir `iosUrlScheme`, registrar o valor usado.
- Adicionar `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` a `frontend-mobile/.env.example` e ao perfil `preview` de `eas.json`.

**Where**: `frontend-mobile/package.json`, `frontend-mobile/package-lock.json`, `frontend-mobile/app.json`, `frontend-mobile/eas.json`, `frontend-mobile/.env.example`
**Depends on**: None
**Reuses**: padrão `EXPO_PUBLIC_*` de `frontend-mobile/eas.json:15-17`
**Requirement**: GAUTH-07, GAUTH-24

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Baseline do `tsc` anotado neste arquivo (linha "Baseline App gate: N erros") — 4 erros
- [x] `npx expo config --type public` inclui o plugin sem erro
- [x] As versões instaladas satisfazem o peer `expo >=52.0.40` do google-signin — `@react-native-google-signin/google-signin@16.1.5`, `expo-auth-session@6.0.3`, `expo-crypto@14.0.2`, com `expo@52.0.46`
- [x] Gate check passes: App gate (≤ baseline) — 4

**Nota de execução (T9):** o config plugin exige `iosUrlScheme` (sem opções, ele entra no modo Firebase e espera `google-services.json`). O valor precisa começar com `com.googleusercontent.apps.`. Valor usado: `com.googleusercontent.apps.ios-not-used-placeholder`. Ele só afeta o `Info.plist` do iOS, que está fora do escopo. Se o iOS entrar, trocar pelo Client ID iOS invertido. `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` ficou vazio em `.env.example` e com o placeholder `REPLACE_WITH_GOOGLE_WEB_CLIENT_ID` no perfil `preview` de `eas.json`. O valor real precisa ser preenchido antes do build do UAT (T23).

**Tests**: none
**Gate**: app

**Commit**: `build(mobile): add google sign-in dependencies and config`

---

#### T10: Extrair `loadSession()` e corrigir `signUp` no contexto de auth

**What**:
- Extrair a sequência `/api/auth/user` → `/api/user/authenticated` (`app/_layout.tsx:58-67`) para `loadSession()`, exposta no contexto e usada por `signIn`.
- Em `signUp`, o web usa `withCredentials: true`, e o nativo checa `response.ok` e lança o JSON de erro.

**Where**: `frontend-mobile/app/_layout.tsx`
**Depends on**: None
**Reuses**: lógica atual de `signIn`
**Requirement**: GAUTH-07, GAUTH-26, GAUTH-27

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O login por e-mail e senha continua levando cliente e cabeleireiro às suas homes (verificação manual rápida no web) — **pendente, vai para o UAT (T23)**: sem backend nem navegador no ambiente do lote 2. Por leitura de código, `signIn` faz as mesmas três chamadas, na mesma ordem e com as mesmas mensagens de erro.
- [x] `loadSession` retorna `{ success, error? }` e está no valor do contexto
- [x] Gate check passes: App gate (≤ baseline) — 4

**Tests**: none
**Gate**: app

**Commit**: `refactor(mobile): extract loadSession and surface signUp errors`

---

#### T11: Modo Google no `RegistrationContext` e provider elevado

**What**:
- Adicionar `google_signup_token` a `IRegistrationData`.
- Exportar `INITIAL_REGISTRATION_DATA` e expor `resetRegistration()`.
- Mover o `RegistrationProvider` de `app/(auth)/register/_layout.tsx` para `app/(auth)/_layout.tsx`.

**Where**: `frontend-mobile/contexts/RegistrationContext.tsx` (move o provider em `app/(auth)/_layout.tsx` e `app/(auth)/register/_layout.tsx`)
**Depends on**: None
**Reuses**: contexto existente
**Requirement**: GAUTH-24, GAUTH-30

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `useRegistration()` funciona na tela de login e em todas as etapas do cadastro — por estrutura: o `RegistrationProvider` envolve o `Stack` de `app/(auth)/_layout.tsx`, que contém `login` e `register/*`
- [ ] O cadastro clássico ainda percorre as cinco etapas (verificação manual rápida no web) — **pendente, vai para o UAT (T23)**: sem navegador no ambiente do lote 2
- [x] Gate check passes: App gate (≤ baseline) — 4

**Tests**: none
**Gate**: app

**Commit**: `refactor(mobile): lift registration provider and add google signup token`

---

#### T12: Criar `google-auth.service`

**What**: Criar o tipo `GoogleAuthResponse` e a função `loginWithGoogle(idToken)`, que faz `POST /api/auth/google` com `withCredentials: true`, conforme o contrato do design.
**Where**: `frontend-mobile/services/google-auth.service.ts`
**Depends on**: T7
**Reuses**: `API_BACKEND_URL` de `@/app/_layout`, padrão dos services existentes
**Requirement**: GAUTH-01, GAUTH-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os tipos refletem exatamente o contrato de `POST /api/auth/google` do design (conferido também contra `GoogleAuthView` em `backend/users/views.py`)
- [x] Gate check passes: App gate (≤ baseline) — 4

**Tests**: none
**Gate**: app

**Commit**: `feat(mobile): add google auth service`

---

#### T13: `useGoogleIdToken` para web

**What**: Implementar o hook web com `WebBrowser.maybeCompleteAuthSession()`, `useAutoDiscovery('https://accounts.google.com')` e `useAuthRequest` (`ResponseType.IdToken`, `nonce`, `usePKCE: false`). O hook retorna `{ ready, getIdToken }`, e `null` significa cancelamento. Também exporta o tipo `UseGoogleIdTokenResult`, compartilhado com a versão Android.
**Where**: `frontend-mobile/hooks/authHooks/useGoogleIdToken.web.ts`
**Depends on**: T9
**Reuses**: `expo-web-browser` (já instalado)
**Requirement**: GAUTH-07, GAUTH-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] No web, com o Client ID configurado, `getIdToken()` abre o popup do Google e devolve um `id_token`. Fechar o popup devolve `null`. — **pendente, vai para o UAT (T23)**: sem Client ID real nem navegador no lote 2. Por leitura de código: fechar o popup → `dismiss` → `null`.
- [x] Os pontos incertos do design (nonce e fechamento do popup) foram confirmados, ou o desvio foi registrado em `design.md` — ver "Resultado da execução" em `design.md`, incluindo o **risco aberto** do `maybeCompleteAuthSession` no build web de produção e a restrição de `await` para T15
- [x] Gate check passes: App gate (≤ baseline) — 4

**Tests**: none
**Gate**: app

**Commit**: `feat(mobile): add web google id token hook`

---

#### T14: `useGoogleIdToken` para Android

**What**: Implementar o hook nativo com `GoogleSignin.configure({ webClientId })`, `hasPlayServices()` e `signIn()`, na mesma interface de T13. O cancelamento devolve `null`.
**Where**: `frontend-mobile/hooks/authHooks/useGoogleIdToken.ts`
**Depends on**: T9, T13
**Reuses**: tipo `UseGoogleIdTokenResult` de T13
**Requirement**: GAUTH-07, GAUTH-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] A forma de retorno de `signIn()` foi confirmada na versão instalada, e o hook trata `success` e `cancelled` — v16.1.5, confirmada no código-fonte do pacote
- [ ] O módulo nativo é carregado com `require` dentro de `getIdToken`, nunca no topo do arquivo. No Expo Go, o app abre normalmente, e tocar no botão mostra "Login com Google indisponível no Expo Go. Use o build do app." — o `require` tardio e a mensagem estão no código (o tipo vem só de `import type`). **O comportamento no Expo Go está pendente e vai para o UAT (T23)**: não havia dispositivo.
- [x] Gate check passes: App gate (≤ baseline) — 4

**Tests**: none
**Gate**: app

**Commit**: `feat(mobile): add android google id token hook`

---

### Phase 4: UI do app (tarefas)

#### T15: Criar o hook orquestrador `useGoogleAuth`

**What**: Implementar `handleGoogle`, `isGoogleLoading`, `ready`, `googleError` e `closeGoogleError`, conforme o design. `authenticated` chama `loadSession()`. `signup_required` semeia o contexto e navega para `/(auth)/register`. Cancelamento é silencioso, e erros mostram a mensagem do backend ou o texto padrão.
**Where**: `frontend-mobile/hooks/authHooks/useGoogleAuth.ts`
**Depends on**: T10, T11, T12, T13, T14
**Reuses**: `useAuth`, `useRegistration`, `loginWithGoogle`, `useGoogleIdToken`
**Requirement**: GAUTH-07, GAUTH-08, GAUTH-09, GAUTH-10, GAUTH-24, GAUTH-28, GAUTH-29

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Cada ramo (authenticated, signup_required, cancelamento, erro com `error`, erro sem `error`) tem o caminho de código descrito no design — conferido por leitura de código em `hooks/authHooks/useGoogleAuth.ts`
- [x] Gate check passes: App gate (≤ baseline) — 4

**Nota de execução (T15, lote 3):**
- `getIdToken()` é o primeiro `await` de `handleGoogle`. Antes dele só rodam um guarda `useRef` contra toque duplo e o `setIsGoogleLoading(true)`, que é síncrono. Isso preserva a restrição do popup blocker.
- **Desvio (`SPEC_DEVIATION` no código):** erros do axios mostram `response.data.error` ou o texto padrão do GAUTH-09. Isso inclui o backend fora do ar. Erros que não vêm do axios mostram `error.message`. É o caso da mensagem do Expo Go exigida em T14.
- Se `loadSession()` falhar depois de `authenticated`, o modal mostra o texto padrão do GAUTH-09.
- **Correção do risco `maybeCompleteAuthSession`, aplicada:** `WebBrowser.maybeCompleteAuthSession()` agora roda no topo de `app/_layout.tsx`, na inicialização do app. A chamada em `useGoogleIdToken.web.ts` ficou, e chamar duas vezes não causa problema. **O T23 precisa validar isso com a URL web publicada (`expo export`).** Passar no `expo start --web` não prova a correção.

**Tests**: none
**Gate**: app

**Commit**: `feat(mobile): add google auth flow hook`

---

#### T16: Criar o componente `GoogleSignInButton`

**What**: Criar o botão com o ícone `logo-google` (Ionicons), `label`, `onPress` e `disabled`/`loading`, que desabilitam o toque e reduzem a opacidade.
**Where**: `frontend-mobile/components/GoogleSignInButton.tsx`
**Depends on**: None
**Reuses**: `@expo/vector-icons` (já usado em `app/(auth)/login.tsx:12`), cores dos estilos de login
**Requirement**: GAUTH-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Com `disabled` ou `loading`, o botão não dispara `onPress` — por leitura de código: `TouchableOpacity disabled={disabled || loading}`, com opacidade 0.5
- [x] Gate check passes: App gate (≤ baseline) — 4

**Tests**: none
**Gate**: app

**Commit**: `feat(mobile): add google sign-in button component`

---

#### T17: Botão "Entrar com Google" na tela de login

**What**: Inserir o divisor "ou" e o `GoogleSignInButton label="Entrar com Google"` entre "Entrar" e "Cadastre-se" (`app/(auth)/login.tsx:69-78`), ligado ao `useGoogleAuth`, com o `googleError` exibido no `ErrorModal`.
**Where**: `frontend-mobile/app/(auth)/login.tsx`
**Depends on**: T15, T16
**Reuses**: `ErrorModal`, `LoginStyle`
**Requirement**: GAUTH-07, GAUTH-08, GAUTH-09, GAUTH-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O botão aparece no web e no Android, fica desabilitado enquanto `isGoogleLoading` ou `!ready`, e os erros aparecem no modal — **pendente, vai para o UAT (T23)**: sem dispositivo nem navegador com Client ID real no lote 3. Por leitura de código: `disabled={!ready}`, `loading={isGoogleLoading}`, e um único `ErrorModal` exibe `googleError` ou `errorModal`. Fechar o modal limpa os dois.
- [x] Gate check passes: App gate (≤ baseline) — 4

**Tests**: none
**Gate**: app

**Commit**: `feat(mobile): add google button to login screen`

---

#### T18: Limpar o cadastro ao abrir pelo link "Cadastre-se"

**What**: Fazer `handleGoRegister` chamar `resetRegistration()` antes de `router.push('/(auth)/register')`.
**Where**: `frontend-mobile/hooks/authHooks/useLogin.ts`
**Depends on**: T11
**Reuses**: `resetRegistration` de T11
**Requirement**: GAUTH-30

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Depois de uma tentativa em modo Google, voltar ao login e tocar em "Cadastre-se" abre o formulário vazio e com os campos de senha — **pendente, vai para o UAT (T23)**: sem dispositivo nem navegador com Client ID real no lote 3. Por leitura de código: `handleGoRegister` chama `resetRegistration()` antes do `push`.
- [x] Gate check passes: App gate (≤ baseline) — 4

**Tests**: none
**Gate**: app

**Commit**: `fix(mobile): reset registration data when starting a new sign-up`

---

#### T19: Modo Google na validação da etapa 1

**What**: Calcular `isGoogleMode = !!registrationData.google_signup_token`, pular a validação de senha e confirmação em `validateFields` (`useRegisterForm.ts:66-132`) quando `isGoogleMode`, e retornar `isGoogleMode`.
**Where**: `frontend-mobile/hooks/authHooks/useRegisterForm.ts`
**Depends on**: T11
**Reuses**: `validateFields` existente
**Requirement**: GAUTH-25

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Em modo Google, `handleRegister` avança sem senha, e as demais validações (CPF/CNPJ, telefone, nomes) continuam valendo — **pendente, vai para o UAT (T23)**: sem dispositivo nem navegador com Client ID real no lote 3. Por leitura de código: as três checagens de senha (a primeira logo depois de `last_name`, a de `validatePassword` e a de confirmação) ficam atrás de `!isGoogleMode`.
- [x] Gate check passes: App gate (≤ baseline) — 4

**Tests**: none
**Gate**: app

**Commit**: `feat(mobile): skip password validation in google sign-up mode`

---

#### T20: Botão "Cadastrar com Google" e modo Google na tela da etapa 1

**What**:
- Adicionar `GoogleSignInButton label="Cadastrar com Google"` abaixo do subtítulo (`register/index.tsx:40`), escondido em modo Google.
- Em modo Google, o e-mail fica `editable={false}`, e os campos de senha e confirmação não são renderizados.
- O `googleError` é exibido no `ErrorModal`.

**Where**: `frontend-mobile/app/(auth)/register/index.tsx`
**Depends on**: T15, T16, T19
**Reuses**: estilos de `RegisterStyle`
**Requirement**: GAUTH-25, GAUTH-28, GAUTH-29

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Com conta nova: tocar no botão preenche nome e e-mail, trava o e-mail e esconde as senhas — **pendente, vai para o UAT (T23)**: sem dispositivo nem navegador com Client ID real no lote 3.
- [ ] Com conta existente: tocar no botão leva à home do papel — **pendente, vai para o UAT (T23)**: sem dispositivo nem navegador com Client ID real no lote 3.
- [x] Gate check passes: App gate (≤ baseline) — 4

**Observação para o T23:** semear o modo Google na própria etapa 1 usa `...INITIAL_REGISTRATION_DATA` (como o design pede), então `profile_picture` volta a `null`. Mas o estado local `profileImage` do `useRegisterForm` continua mostrando uma foto escolhida antes. Nesse caso, a foto aparece na tela e não é enviada. Não foi corrigido, porque está fora do escopo do design.

**Tests**: none
**Gate**: app

**Commit**: `feat(mobile): add google sign-up to registration first step`

---

#### T21: Envio final do cliente em modo Google

**What**: Em `finishRegistration` (`usePreferences.ts:63-119`), quando está em modo Google:
- não anexa `password`, `confirmPassword` nem `email`, e anexa `google_signup_token`;
- depois do sucesso, chama `loadSession()` em vez de `Alert` + `router.replace('/(auth)/login')`;
- em erro, mantém o `ErrorModal` na tela.

O caminho clássico não muda.
**Where**: `frontend-mobile/hooks/authHooks/usePreferences.ts`
**Depends on**: T10, T11
**Reuses**: montagem de `FormData` existente
**Requirement**: GAUTH-26, GAUTH-27

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Um cliente em modo Google termina logado na home, e um erro do backend aparece no modal sem sair do wizard — **pendente, vai para o UAT (T23)**: sem dispositivo nem navegador com Client ID real no lote 3. Por leitura de código:
  - Em modo Google, `password`, `confirmPassword` e `email` saem de `allData` antes do laço que monta o `FormData`, e o `google_signup_token` entra.
  - No caminho clássico, o `google_signup_token` vazio é removido, e o payload fica igual ao de antes da feature.
  - Depois do sucesso, `loadSession()` é chamado.
  - Em modo Google, fechar o modal não redireciona para o login. Isso foi necessário para o GAUTH-27, porque `closeErrorModal` sempre redirecionava.
- [x] Gate check passes: App gate (≤ baseline) — 4

**Tests**: none
**Gate**: app

**Commit**: `feat(mobile): finish customer google sign-up with session`

---

#### T22: Envio final do cabeleireiro em modo Google

**What**: Aplicar em `handleFinish` (`useDescription.ts:43-99`) a mesma regra de T21. Em modo Google, `handleCloseErrorModal` (`useDescription.ts:108-111`) só fecha o modal, sem redirecionar para o login.
**Where**: `frontend-mobile/hooks/authHooks/useDescription.ts`
**Depends on**: T10, T11
**Reuses**: montagem de `FormData` existente
**Requirement**: GAUTH-26, GAUTH-27

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Um cabeleireiro em modo Google termina logado na agenda, e um erro do backend aparece no modal sem sair do wizard — **pendente, vai para o UAT (T23)**: sem dispositivo nem navegador com Client ID real no lote 3. Por leitura de código: a mesma regra de T21 em `handleFinish`, e `handleCloseErrorModal` só redireciona fora do modo Google.
- [x] Gate check passes: App gate (≤ baseline) — 4

**Tests**: none
**Gate**: app

**Commit**: `feat(mobile): finish hairdresser google sign-up with session`

---

### Phase 5: Fechamento (tarefas)

#### T23: UAT manual e atualização de RF2/RF5

**What**: Executar o roteiro de UAT abaixo no web e no Android e registrar o resultado neste arquivo. Depois, atualizar RF2 e RF5 em `docs/requisitos-status.md` para ✅, com as referências `file:line` da implementação.

Atenção: `docs/` hoje **não está versionado** (`git status` mostra `?? docs/`). Confirmar com o usuário antes de incluir o arquivo no commit.

**Where**: `docs/requisitos-status.md`
**Depends on**: T8, T17, T18, T20, T21, T22
**Reuses**: formato da tabela existente (`docs/requisitos-status.md:48`, `:51`)
**Requirement**: GAUTH-02, GAUTH-07, GAUTH-08, GAUTH-09, GAUTH-10, GAUTH-11, GAUTH-19, GAUTH-24, GAUTH-25, GAUTH-26, GAUTH-27, GAUTH-28, GAUTH-29, GAUTH-30

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Todos os passos do roteiro de UAT passam no web e no Android (APK `preview`), com o resultado anotado
- [ ] Gate check passes: Build gate (Full + App ≤ baseline)

**Tests**: none
**Gate**: build

**Commit**: `docs: mark RF2 and RF5 as implemented`

---

## Roteiro de UAT manual (T23)

Pré-requisitos: Client ID Web com **Authorized JavaScript origins** e **Authorized redirect URIs** cadastrados para cada origem web usada (`http://localhost:8081` e a URL web publicada); backend com `GOOGLE_OAUTH_CLIENT_IDS` = Client ID Web; app com `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID`; duas contas Google novas (A e B) e uma conta Google cujo e-mail já tem conta por senha (C). Rodar o roteiro inteiro no **web** e no **Android**.

| # | Passo | Resultado esperado | Req |
| - | ----- | ------------------ | --- |
| 1 | Login → "Entrar com Google" → fechar o seletor do Google | Continua no login, sem modal | GAUTH-08 |
| 2 | Login → "Entrar com Google" com a conta A | O wizard abre com nome e e-mail de A, o e-mail travado e sem campos de senha | GAUTH-24, 25 |
| 3 | Escolher Cliente, preencher CPF, telefone, endereço, preferências e concluir | Termina logado na home de cliente, sem passar pelo login | GAUTH-26 |
| 4 | Logout → "Entrar com Google" com a conta A | Vai direto para a home de cliente | GAUTH-07 |
| 5 | Cadastro (link) → "Cadastrar com Google" com a conta B → Profissional → CNPJ, endereço, preferências, história e descrição → concluir | Termina logado na agenda do cabeleireiro | GAUTH-28, 26 |
| 6 | Logout → login por senha com o e-mail de B e qualquer senha | Modal: "Esta conta usa login com Google. Use o botão Entrar com Google." | GAUTH-11 |
| 7 | "Entrar com Google" com a conta C (já cadastrada por senha) | Entra direto na home do papel de C, e o login por senha de C continua funcionando | GAUTH-02 |
| 8 | Wizard Google com a conta nova D, usando o telefone de A no envio final | Modal com erro de telefone já cadastrado. Continua no wizard | GAUTH-19, 27 |
| 9 | Com o wizard do passo 8 aberto, voltar ao login → "Cadastre-se" | Formulário vazio, com campos de senha | GAUTH-30 |
| 10 | Tocar duas vezes rápido em "Entrar com Google" | Só um fluxo é aberto; o botão fica desabilitado durante a requisição | GAUTH-10 |
| 11 | Backend fora do ar → "Entrar com Google" | Modal: "Não foi possível entrar com o Google. Tente novamente." | GAUTH-09 |

---

## Phase Execution Map

Phases run in sequence, and tasks within a phase run in order. The dependency arrows are the ones in the Execution Plan above.

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

Phase 1:  T1, T2, T3, T4, T5        (T5 depende de T1 e T2)
Phase 2:  T6, T7, T8                (T8 depende de T7)
Phase 3:  T9, T10, T11, T12, T13, T14   (T13 depende de T9; T14 de T9 e T13)
Phase 4:  T15, T16, T17, T18, T19, T20, T21, T22   (T17 de T15 e T16; T20 de T15, T16 e T19)
Phase 5:  T23
```

**Batches para sub-agentes** (~7 tarefas, fases inteiras): 23 tarefas → 4 workers.
- Lote 1: Fases 1 e 2 (8 tarefas de backend)
- Lote 2: Fase 3 (6)
- Lote 3: Fase 4 (8)
- Lote 4: Fase 5 (1, com o UAT e a interação com o usuário, de preferência inline)

O Execute oferece os sub-agentes antes de começar. Tier sugerido: alto para o Lote 1 (segurança/auth) e para o Verifier; médio para os Lotes 2 e 3.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: dependências backend | 1 arquivo | ✅ Granular |
| T2: setting `GOOGLE_OAUTH_CLIENT_IDS` | 1 setting + 2 arquivos de documentação de env | ⚠️ OK (coeso: a variável e onde ela é declarada) |
| T3: `User.google_id` | 1 campo + migration gerada | ✅ Granular |
| T4: `auth_tokens` | 1 módulo | ✅ Granular |
| T5: `google_auth` | 1 função | ✅ Granular |
| T6: ajustes `LoginView` | 1 view | ✅ Granular |
| T7: `GoogleAuthView` + rota | 1 endpoint + 1 linha em `urls.py` | ⚠️ OK (merge backward: sem a rota, a view não é testável) |
| T8: caminho Google no `RegisterView` | 1 endpoint | ✅ Granular |
| T9: deps e config do app | config de dependências (4 manifestos) | ⚠️ OK (uma instalação; os manifestos mudam juntos) |
| T10: `loadSession` + `signUp` | 1 arquivo | ✅ Granular |
| T11: modo Google no contexto + provider elevado | 1 contexto + mover 1 provider | ⚠️ OK (coeso: o provider muda de lugar por causa do campo novo) |
| T12: service | 1 função | ✅ Granular |
| T13: hook web | 1 hook | ✅ Granular |
| T14: hook Android | 1 hook | ✅ Granular |
| T15: `useGoogleAuth` | 1 hook | ✅ Granular |
| T16: `GoogleSignInButton` | 1 componente | ✅ Granular |
| T17: tela de login | 1 tela | ✅ Granular |
| T18: reset no `useLogin` | 1 função | ✅ Granular |
| T19: validação modo Google | 1 função | ✅ Granular |
| T20: tela etapa 1 | 1 tela | ✅ Granular |
| T21: submit cliente | 1 função | ✅ Granular |
| T22: submit cabeleireiro | 1 função | ✅ Granular |
| T23: UAT + docs | 1 arquivo | ✅ Granular |

---

## Diagram-Definition Cross-Check

A paridade vale dentro de cada fase. Dependências entre fases apontam sempre para trás e são checadas pelo validador de fase.

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | nenhuma seta de entrada | ✅ Match |
| T2 | None | nenhuma seta de entrada | ✅ Match |
| T3 | None | nenhuma seta de entrada | ✅ Match |
| T4 | None | nenhuma seta de entrada | ✅ Match |
| T5 | T1, T2 | T1 → T5, T2 → T5 | ✅ Match |
| T6 | T4 (fase 1) | nenhuma seta intra-fase | ✅ Match |
| T7 | T3, T4, T5 (fase 1) | nenhuma seta intra-fase | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | None | nenhuma seta de entrada | ✅ Match |
| T10 | None | nenhuma seta de entrada | ✅ Match |
| T11 | None | nenhuma seta de entrada | ✅ Match |
| T12 | T7 (fase 2) | nenhuma seta intra-fase | ✅ Match |
| T13 | T9 | T9 → T13 | ✅ Match |
| T14 | T9, T13 | T9 → T14, T13 → T14 | ✅ Match |
| T15 | T10, T11, T12, T13, T14 (fase 3) | nenhuma seta intra-fase | ✅ Match |
| T16 | None | nenhuma seta de entrada | ✅ Match |
| T17 | T15, T16 | T15 → T17, T16 → T17 | ✅ Match |
| T18 | T11 (fase 3) | nenhuma seta intra-fase | ✅ Match |
| T19 | T11 (fase 3) | nenhuma seta intra-fase | ✅ Match |
| T20 | T15, T16, T19 | T15 → T20, T16 → T20, T19 → T20 | ✅ Match |
| T21 | T10, T11 (fase 3) | nenhuma seta intra-fase | ✅ Match |
| T22 | T10, T11 (fase 3) | nenhuma seta intra-fase | ✅ Match |
| T23 | T8, T17, T18, T20, T21, T22 (fases 2 e 4) | nenhuma seta intra-fase | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1: deps backend | dependências | none | none | ✅ OK |
| T2: setting | settings/config | none | none | ✅ OK |
| T3: `google_id` | modelo/migration | none | none | ✅ OK |
| T4: `auth_tokens` | helper de domínio | unit | unit | ✅ OK |
| T5: `google_auth` | helper de domínio | unit | unit | ✅ OK |
| T6: `LoginView` | view/rota | integration | integration | ✅ OK |
| T7: `GoogleAuthView` | view/rota | integration | integration | ✅ OK |
| T8: `RegisterView` | view/rota | integration | integration | ✅ OK |
| T9–T22 | frontend | none (decisão do usuário) | none | ✅ OK |
| T23: docs + UAT | documentação | none | none | ✅ OK |

---

## Requirement Coverage

| Requirement | Tasks |
| ----------- | ----- |
| GAUTH-01 | T3, T4, T6, T7, T12 |
| GAUTH-02 | T3, T7, T23 |
| GAUTH-03 | T7 |
| GAUTH-04 | T1, T2, T5, T7 |
| GAUTH-05 | T5, T7 |
| GAUTH-06 | T7 |
| GAUTH-07 | T9, T10, T13, T14, T15, T17, T23 |
| GAUTH-08 | T13, T14, T15, T17, T23 |
| GAUTH-09 | T15, T17, T23 |
| GAUTH-10 | T15, T16, T17, T23 |
| GAUTH-11 | T6, T23 |
| GAUTH-12 | T7, T12 |
| GAUTH-13 | T4, T7 |
| GAUTH-14 | T4, T6 |
| GAUTH-15 | T3, T8 |
| GAUTH-16 | T8 |
| GAUTH-17 | T8 |
| GAUTH-18 | T8 |
| GAUTH-19 | T8, T23 |
| GAUTH-20 | T8 |
| GAUTH-21 | T8 |
| GAUTH-22 | T8 |
| GAUTH-23 | T7 |
| GAUTH-24 | T9, T11, T15, T23 |
| GAUTH-25 | T19, T20, T23 |
| GAUTH-26 | T10, T21, T22, T23 |
| GAUTH-27 | T10, T21, T22, T23 |
| GAUTH-28 | T15, T20, T23 |
| GAUTH-29 | T15, T20, T23 |
| GAUTH-30 | T11, T18, T23 |

**Coverage:** 30 requisitos, 30 mapeados, 0 sem tarefa.
