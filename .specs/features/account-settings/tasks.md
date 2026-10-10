# Configurações da conta Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/account-settings/spec.md`
**Context**: `.specs/features/account-settings/context.md`
**Design**: `.specs/features/account-settings/design.md`
**Status**: Draft (aguardando aprovação para Execute)
**Branch**: a criar a partir de `develop` no início do Execute, com o nome `120-editar-dados-da-conta-e-excluir-conta`.

**Pré-requisitos do Execute:**
- Os testes do backend rodam dentro do container `hairmatch_backend` (memória `backend-tests-run-in-docker`). Se o `hairmatch_db` estiver parado, rodar `docker start hairmatch_db`.
- Os testes usam o fake de Cognito (`COGNITO_USE_FAKE`) e o `InMemoryStorage`. Não precisam do MiniStack nem do LocalStack.
- O UAT (T21) precisa do `docker compose up` completo e do app no web (memória `expo-web-smoke-needs-visible-tab`) e no Android.
- Nenhuma env var nova e nenhuma migração.
- Os arquivos não commitados que já existiam (`frontend-mobile/.env.example`, `frontend-mobile/services/axios-instance.ts`, `.specs/LESSONS.md`, `.specs/lessons.json` e `docs/`) ficam fora dos commits desta feature.

**Ordem que mantém a suíte verde a cada commit:**
1. As Phases 1 e 2 são de backend e vêm antes do app, que depende das rotas e da validação.
2. A Phase 3 cria a base do app (serviço, validação, `clearSession` e guardas de nulo) sem mudar nenhuma tela.
3. As Phases 4 e 5 ligam as telas, uma de cada vez.
4. A Phase 6 é o UAT.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas:
> - `.github/workflows/hairmatch-backend-test.yml`: `coverage run manage.py test`, sem limite mínimo.
> - `backend/users/tests.py`: `UserInfoCookieViewTest` `:644`, `CognitoDeleteAccountTest` `:5568`, `UpdateProfileEmailTest` `:5715`, `UpdateProfilePhoneTest` `:5794`, `UserProfilePicturePathTest` `:3376` e `FakeCognitoIdpTest` `:3384` (`fail_next`).
> - `backend/hairmatch/test_routes.py` (`ROUTE_TABLE` e `SINGULAR_SEGMENTS`).
> - `frontend-mobile`: sem testes, por decisão herdada do #106, do #139 e do #141. O gate é `npx tsc --noEmit` mais o UAT.
>
> Strong defaults aplicados nas camadas de backend.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: views de `users` (`PATCH /api/users/me`, `DELETE /api/users/me`, `ProfilePictureView`) | integration | Cada critério de ACC-01 a ACC-15, ACC-34 a ACC-41 e ACC-56 a ACC-58: happy path, cada status de erro do spec (400, 401, 409, 429 e 503) e "nenhuma linha alterada" onde o spec exige. Para o storage: arquivo novo presente, antigo ausente depois do commit (`captureOnCommitCallbacks(execute=True)`). | `backend/users/tests.py` (`APIClient`) | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput users'` |
| Backend: Route Table (`hairmatch/test_routes.py`) | unit | RT-88 e RT-89 em `ROUTE_TABLE`, `profile-picture` em `SINGULAR_SEGMENTS`, e a tabela igual ao URLconf. | `backend/hairmatch/test_routes.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput hairmatch'` |
| App (`frontend-mobile`): serviço, hooks, componentes e telas | none | `npx tsc --noEmit` sem erro novo, mais o roteiro de UAT do T21. | - | App |
| Specs (`.specs/`) | none | `validate_spec.py` com exit 0. | - | - |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas com testes só de `users` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput users'` |
| Full | Tarefas que tocam o URLconf ou o fim de uma fase de backend | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput && coverage report -m'` |
| App | Tarefas do `frontend-mobile` | `cd frontend-mobile && npx tsc --noEmit` |
| Build | T21 (fim da feature) | Full + App + o roteiro de UAT do T21 |

> **Baseline de testes do backend:** `git grep -c "def test_"` em `fbf1d08` conta **724**:
> - `users` 384 e `hairmatch` 100 (`tests.py` 44, `test_problems.py` 47 e `test_routes.py` 9);
> - `availability` 55, `reserve` 45, `service` 40, `review` 35, `agenda` 23, `chatbot` 23 e `preferences` 19.
>
> Nenhuma tarefa reduz esses números. Antes do T1, rodar o gate Full para confirmar a baseline.

> **Gate do app:** antes do T7, registrar a saída atual de `npx tsc --noEmit` como baseline. O gate passa quando nenhuma tarefa acrescenta um erro novo.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend: validar o `PATCH /api/users/me`

```
T1 → T2 → T3
T4
```

### Phase 2: Backend: foto de perfil

```
T5 → T6
```

### Phase 3: App: base

```
T7
T8
T9
T10
```

### Phase 4: App: dados da conta e endereço

```
T11 → T12
T13 → T14
```

### Phase 5: App: foto, exclusão, preferências e resumo

```
T15
T16
T17 → T18
T19 → T20
```

### Phase 6: UAT

```
T21
```

---

## Task Breakdown

### Phase 1: Backend: validar o `PATCH /api/users/me`

#### T1: Validar e normalizar o corpo do `PATCH`

**What**: Criar `_profile_update(user, data)` e usá-la no `CurrentUserView.patch`. A função:
- valida os campos obrigatórios, o `max_length`, o telefone, o CEP, a UF, o CPF, o CNPJ e o resumo;
- devolve todos os erros num único `validation-error`;
- normaliza dígitos e UF;
- compara o e-mail sem diferenciar maiúsculas;
- ignora campos fora da lista.

**Where**: `backend/users/views.py`
**Depends on**: None
**Reuses**: `_string_field_errors`, `body_error`, `validation_problem` e `json_object` (`backend/hairmatch/problems.py`)
**Requirement**: ACC-01, ACC-02, ACC-03, ACC-04, ACC-05, ACC-06, ACC-07, ACC-08, ACC-09, ACC-10, ACC-56, ACC-57

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Classe nova `ProfileUpdateValidationTest` em `backend/users/tests.py`, com um teste por critério:
  - vazio, só espaços e não string, para cada campo obrigatório, com o pointer e nenhuma linha alterada;
  - `max_length` de cada campo de texto;
  - telefone com 9, 14 e sem `55`;
  - CEP com 7 e 9 dígitos;
  - UF `Amazonas` e `A1`;
  - CPF com 10, CNPJ com 13 e o resumo com 1001 caracteres;
  - vários erros de uma vez (dois pointers no mesmo 400);
  - gravação normalizada (`55 (92) 99999-0000` → `5592999990000`, `69057-000` → `69057000`, `am` → `AM`);
  - e-mail em outra caixa ignorado e e-mail diferente com 400 sem gravar nada;
  - `rating`, `role`, `cognito_sub`, `google_id` e `is_active` ignorados.
- [x] Os testes atuais do `PATCH` continuam passando sem mudar o que afirmam.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput users'`
- [x] Test count: `users` ≥ 384 + os novos, sem remoção: 398 executados. A baseline executada é 382 (o `git grep -c "def test_"` conta 384).

**Tests**: integration
**Gate**: quick
**Commit**: `feat(users): validate and normalize the account update`

---

#### T2: Conflito de telefone no `PATCH`

**What**: No `PATCH`:
- o telefone de outra conta ativa dá 409 `phone-taken`;
- a conta pendente que tem o telefone é substituída por `_replace_pending_account`, e um `CognitoError` dá 503 ou 429 sem gravar;
- um `IntegrityError` dá 409 `phone-taken`;
- o próprio telefone (mesmos dígitos) é aceito sem validar o formato, mesmo fora do padrão `55` + dígitos.

**Where**: `backend/users/views.py`
**Depends on**: T1
**Reuses**: `_PENDING_ACCOUNT`, `_pending_accounts`, `_replace_pending_account` e `_cognito_error_response`
**Requirement**: ACC-11, ACC-12, ACC-13, ACC-14, ACC-58, ACC-60

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Testes novos em `UpdateProfilePhoneTest`:
  - conta pendente com o telefone: o `admin_delete_user` aparece nas chamadas do fake, a conta some e o telefone é gravado;
  - `fail_next('admin_delete_user', ...)` com indisponibilidade: 503 `auth-unavailable` e as duas contas intactas;
  - com throttling: 429 `too-many-requests`;
  - `IntegrityError` simulado no `save` (`patch.object`): 409 `phone-taken`, e não 500;
  - o próprio telefone num formato cru do seed (`74 8985-0719`) junto com `first_name`: 200, o nome muda e o telefone gravado não muda;
  - falha na gravação depois da substituição: a conta pendente continua apagada.
- [x] Os três testes atuais de `UpdateProfilePhoneTest` continuam passando.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput users'`
- [x] Test count: `users` sem remoção: 403 executados (398 + 5).

**Tests**: integration
**Gate**: quick
**Commit**: `fix(users): free the phone of a pending account and answer 409 on a phone race`

---

#### T3: Gravar o `User` e o perfil numa transação

**What**: Envolver a gravação do `User` e do `Customer` ou `Hairdresser` em `transaction.atomic()`, de modo que uma falha no perfil desfaça o `User`.

**Where**: `backend/users/views.py`
**Depends on**: T2
**Reuses**: o padrão de `transaction.atomic` do cadastro (`views.py:251`)
**Requirement**: ACC-15

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] O teste novo força uma exceção no `save` do `Customer` (`patch.object(Customer, 'save', side_effect=...)`) com um corpo que muda `first_name` e `cpf`. A resposta é 500 `internal-error`, e o `GET /api/users/me` seguinte devolve o `first_name` antigo.
- [x] O mesmo teste para o `Hairdresser`, com `resume`.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput users'`
- [x] Test count: `users` sem remoção: 405 executados (403 + 2).

**Tests**: integration
**Gate**: quick
**Commit**: `fix(users): save the account and its profile atomically`

---

#### T4: Cobrir a exclusão de conta Google

**What**: Teste que exclui uma conta Google (sessão `hairmatch` e `cognito_sub` nulo) por `DELETE /api/users/me` e confere que a conta some, a resposta é 204 com os cookies limpos e o fake de Cognito não recebe nenhuma chamada.

**Where**: `backend/users/tests.py`
**Depends on**: None
**Reuses**: `CognitoDeleteAccountTest` (`:5568`) e o helper de sessão Google dos testes de `SessionFormatTest`
**Requirement**: ACC-34

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] O teste passa contra o código atual e falha se o `if cognito_sub:` de `_delete_account` for removido. A falha é conferida uma vez, à mão, e depois revertida.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput'`. É o gate Full, no fim da fase.
- [x] Test count: total ≥ 724 + os novos das T1 a T4: 746 executados (a baseline executada era 722; o `git grep` contava 724). O teste `test_google_accounts_are_deleted_without_calling_cognito` já cobria a linha e o Cognito; o novo acrescenta os cookies limpos.

**Tests**: integration
**Gate**: full
**Commit**: `test(users): cover deleting a Google account`

---

### Phase 2: Backend: foto de perfil

#### T5: `PUT /api/users/me/profile-picture`

**What**: Criar a `ProfilePictureView` com o `put`, registrar a rota `users/me/profile-picture` e incluir RT-88 em `ROUTE_TABLE` e `profile-picture` em `SINGULAR_SEGMENTS`. As linhas RT-88 e RT-89 e a lista do RT-54 já estão na Route Table do `api-restful-routes/spec.md` (o AD-007 exige a tabela antes do código).
- Grava pelo `WebPImageField`.
- Responde 200 `{"profile_picture": url}`.
- Apaga a foto antiga no `on_commit`.
- `invalid-image` deixa tudo intacto.
- Campo ausente ou arquivo acima de 5 MB dá `validation-error` `/profile_picture`.
- Sem sessão, dá 401.

As peças da rota entram juntas porque o RT-50 (`test_routes.py`) falha se a rota existir sem estar na tabela.

**Where**: `backend/users/views.py` (mais `backend/users/urls.py` e `backend/hairmatch/test_routes.py`)
**Depends on**: None
**Reuses**: `authenticated_user`, `WebPImageField`, `INVALID_PROFILE_PICTURE_DETAIL`, o tratamento de `InvalidImage` do cadastro (`views.py:276-278`) e `_delete_stored_files`
**Requirement**: ACC-35, ACC-36, ACC-37, ACC-38, ACC-39, ACC-41, ACC-42

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Classe nova `ProfilePictureViewTest` com:
  - PNG válido: 200, a URL termina em `.webp` e o arquivo existe no storage;
  - troca: o arquivo antigo some depois do commit (`captureOnCommitCallbacks(execute=True)`) e o novo fica;
  - texto como imagem: 400 `invalid-image`, com a foto e o arquivo antigos intactos;
  - sem o campo: 400 `validation-error` `/profile_picture`;
  - arquivo de 5 MB + 1 byte: 400, sem gravar;
  - sem cookie: 401 `invalid-session`.
- [x] `RouteTableTests` passa com RT-88.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput'`
- [x] Test count: total sem remoção: 752 executados (746 + 6).

**Tests**: integration
**Gate**: full
**Commit**: `feat(users): replace the profile picture after sign-up`

---

#### T6: `DELETE /api/users/me/profile-picture`

**What**: Acrescentar o `delete` à `ProfilePictureView`: zera o campo, apaga o arquivo no `on_commit`, responde 204 e é idempotente sem foto. Incluir RT-89 em `ROUTE_TABLE`.

**Where**: `backend/users/views.py` (mais `backend/hairmatch/test_routes.py`)
**Depends on**: T5
**Reuses**: `_delete_stored_files`
**Requirement**: ACC-40, ACC-41, ACC-42

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Testes novos em `ProfilePictureViewTest`:
  - com foto: 204, o campo fica nulo e o arquivo some depois do commit;
  - sem foto: 204 e o storage não é chamado;
  - sem cookie: 401 `invalid-session`;
  - 405 com `Allow: DELETE, OPTIONS, PUT` para `GET`.
- [x] `RouteTableTests` passa com RT-89.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput'`
- [x] Test count: total sem remoção: 756 executados (752 + 4).

**Tests**: integration
**Gate**: full
**Commit**: `feat(users): remove the profile picture`

---

### Phase 3: App: base

#### T7: Serviço da conta

**What**: Criar `services/account.service.ts` com `updateMe`, `deleteMe`, `uploadProfilePicture` (multipart, com blob no web e `{uri,name,type}` no nativo), `removeProfilePicture`, `assignPreference` e `unassignPreference`, e os tipos `AccountUpdate` e `PickedImage`.

**Where**: `frontend-mobile/services/account.service.ts`
**Depends on**: None
**Reuses**: `axiosInstance`, `API_BACKEND_URL` e o multipart de `services/review.service.ts:6-11` e `hooks/customerHooks/useReviewForm.ts:100-114`
**Requirement**: ACC-17, ACC-26, ACC-30, ACC-44, ACC-46, ACC-49

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Cada função chama exatamente o método e o path do design e não engole o erro.
- [x] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`, sem erro novo em relação à baseline. Baseline antes do T7: exit 0, sem erro; depois: exit 0.

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): add the account service`

---

#### T8: `clearSession` no `AuthContext`

**What**: Expor `clearSession()` no `authContext` de `app/_layout.tsx`. A função zera `userToken` e `userInfo` sem chamar a API.

**Where**: `frontend-mobile/app/_layout.tsx`
**Depends on**: None
**Reuses**: o corpo do `setSessionExpiredHandler` (`_layout.tsx:146-153`)
**Requirement**: ACC-31

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `useAuth().clearSession` existe e não faz requisição.
- [x] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): clear the local session without calling the API`

---

#### T9: Guardas de nulo nas telas de perfil

**What**: Trocar o acesso a `x.user.profile_picture` e a `x.user.*` por acesso com guarda (ou por um retorno antecipado quando `userInfo` é nulo) nas telas de perfil, de configurações e de `configs`.

**Where**: `frontend-mobile/app/(app)/customer/profile.tsx` (mais `hairdresser/profile/settings.tsx`, `hairdresser/profile/index.tsx` e os hooks `useCustomerProfile.ts` e `useHairdresserProfile.ts`)
**Depends on**: None
**Reuses**: nada
**Requirement**: ACC-32

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Com `userInfo` nulo, nenhuma das telas lê uma propriedade de `undefined`. Conferido por leitura e no UAT (T21: logout e exclusão). Cada tela retorna `null` antes de ler `x.user` (as duas `configs/accountSetting.tsx` também). Os hooks `useCustomerProfile`, `useHairdresserProfile` e `useHairdresserSettings` já usavam `?.` e não mudaram; as `configs/addressSetting.tsx` já usavam `?.`.
- [x] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `fix(app): render the profile screens without a session`

---

#### T10: Validação local da conta

**What**: Criar `utils/account-validation.ts` com funções puras que devolvem `{ errors: Record<campo, boolean>, messages: string[] }` para os dados da conta, o endereço e o resumo, nas mesmas regras de ACC-01 a ACC-07. Acrescentar as mensagens que faltarem em `constants/errorMessages.ts`.

**Where**: `frontend-mobile/utils/account-validation.ts`
**Depends on**: None
**Reuses**: `stripNonDigits` (`utils/forms.ts:62`) e `ERROR_MESSAGES`
**Requirement**: ACC-20, ACC-27, ACC-54

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] As regras batem com as do backend (T1): mesmos limites e mesmos formatos. Uma função só, `validateAccountUpdate(fields)`, serve às três telas: como o backend, confere só os campos presentes no corpo que vai ser enviado. Obrigatórios: nome, sobrenome, telefone, endereço, bairro, cidade, UF e CEP; `number` e `complement` aceitam vazio; limites 100/150/6/1000; telefone `^55\d{10,11}$`, CEP 8 dígitos, UF 2 letras, CPF 11 e CNPJ 14 dígitos.
- [x] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): validate the account fields before saving`

---

### Phase 4: App: dados da conta e endereço

#### T11: Hook `useAccountForm`

**What**: Hook que:
- monta o estado a partir de `userInfo` (telefone sem o `55` e documentos com máscara);
- calcula o diff;
- valida com o T10;
- envia só o diff (telefone `55` + dígitos, documentos só com dígitos);
- chama `loadSession`;
- expõe `saving` e as mensagens de sucesso, de "nenhuma alteração" e de erro (`problemMessage`).

**Where**: `frontend-mobile/hooks/accountHooks/useAccountForm.ts`
**Depends on**: None
**Reuses**: `updateMe` (T7), `utils/account-validation.ts` (T10) e `formatPhone`, `formatCPF` e `formatCNPJ`
**Requirement**: ACC-17, ACC-18, ACC-19, ACC-20, ACC-21, ACC-22

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Um salvamento sem alteração não chama `updateMe`. O `handleSave` sai com "Nenhuma alteração para salvar." antes do `updateMe` quando o diff é vazio.
- [x] O corpo enviado só tem os campos alterados. O diff compara nome e sobrenome sem espaços nas pontas, e telefone e documento pelos dígitos; o telefone apagado vai como `''` e cai na validação.
- [x] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): add the account form hook`

---

#### T12: Tela de dados da conta

**What**: Criar `components/account/AccountSettingScreen.tsx` com o `useAccountForm` e fazer as duas rotas `configs/accountSetting.tsx` o renderizarem com o papel.
- Os campos ficam editáveis e com máscara.
- O e-mail fica somente leitura.
- Os campos de senha saem.
- "Salvar" ganha `disabled` e indicador.
- Os modais de sucesso e de erro usam o `ErrorModal` com `title`.

**Where**: `frontend-mobile/components/account/AccountSettingScreen.tsx` (mais as duas rotas `configs/accountSetting.tsx`)
**Depends on**: T11
**Reuses**: `styles/customer/styles/AccountConfigStyles` e `ErrorModal`
**Requirement**: ACC-16, ACC-22

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] As duas rotas mostram a mesma tela, com CPF para o cliente e CNPJ para o cabeleireiro.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): edit the account data`

---

#### T13: Hook `useAddressForm`

**What**: Hook do endereço que:
- monta o estado a partir de `userInfo`;
- faz o autofill pelo `useCepLookup` com a lógica de merge de `useAddress.ts:34-69` (sem apagar número nem complemento);
- trava e destrava os campos;
- valida com o T10;
- envia só o diff (CEP só com dígitos);
- chama `loadSession`;
- expõe as mensagens.

**Where**: `frontend-mobile/hooks/accountHooks/useAddressForm.ts`
**Depends on**: None
**Reuses**: `useCepLookup`, `formatCEP`, `updateMe` (T7) e `utils/account-validation.ts` (T10)
**Requirement**: ACC-24, ACC-25, ACC-26, ACC-27

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O hook não importa o `RegistrationContext`.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): add the address form hook`

---

#### T14: Tela de endereço

**What**: Criar `components/account/AddressSettingScreen.tsx` com o `useAddressForm`, com o CEP primeiro e o layout de `register/address.tsx:33-96`, e fazer as duas rotas `configs/addressSetting.tsx` o renderizarem.

**Where**: `frontend-mobile/components/account/AddressSettingScreen.tsx` (mais as duas rotas `configs/addressSetting.tsx`)
**Depends on**: T13
**Reuses**: `styles/register/styles/AdressStyle.ts` e `ErrorModal`
**Requirement**: ACC-23, ACC-27

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] As duas rotas mostram a tela, e os campos travam e destravam como no cadastro.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): edit the address`

---

### Phase 5: App: foto, exclusão, preferências e resumo

#### T15: Foto de perfil na tela de conta

**What**: Criar `hooks/accountHooks/useProfilePicture.ts` e usá-lo na `AccountSettingScreen`.
- Tocar na foto abre a escolha entre "Escolher nova foto" e "Remover foto" (esta só se houver foto).
- A escolha usa a permissão e o seletor do cadastro (recorte quadrado, qualidade 0.5).
- Depois vem o upload ou a remoção, e então `loadSession`.
- A permissão negada mostra a mensagem do spec sem chamar a API.

**Where**: `frontend-mobile/hooks/accountHooks/useProfilePicture.ts` (mais `components/account/AccountSettingScreen.tsx`)
**Depends on**: None
**Reuses**: `useRegisterForm.ts:22-54`, `uploadProfilePicture` e `removeProfilePicture` (T7)
**Requirement**: ACC-43, ACC-44, ACC-45, ACC-46

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] A foto nova aparece depois do upload, e a imagem padrão aparece depois da remoção. Conferido no T21.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): change and remove the profile picture`

---

#### T16: Excluir a conta

**What**: Criar `hooks/accountHooks/useDeleteAccount.ts` e acrescentar o item "Excluir conta" e o `ConfirmationModal` (textos do ACC-29) aos menus do cliente e do cabeleireiro.
- Uma chamada só por confirmação.
- No 204, `router.replace('/(auth)/login')` e depois `clearSession`.
- No erro, a mensagem do slug, e a sessão continua.

**Where**: `frontend-mobile/hooks/accountHooks/useDeleteAccount.ts` (mais `app/(app)/customer/profile.tsx` e `app/(app)/hairdresser/profile/settings.tsx`)
**Depends on**: None
**Reuses**: `deleteMe` (T7), `clearSession` (T8), `ConfirmationModal` e `MenuItem`
**Requirement**: ACC-28, ACC-29, ACC-30, ACC-31, ACC-33

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Os dois menus mostram o item, e o modal do cabeleireiro tem a frase das reservas dos clientes.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): delete the account`

---

#### T17: Hook `usePreferencesSetting`

**What**: Hook que:
- carrega o catálogo e as preferências do usuário (404 = `[]`);
- alterna a seleção;
- no "Salvar", chama `assignPreference` para cada adicionada e `unassignPreference` para cada removida, em sequência;
- em falha, mostra a mensagem e recarrega do servidor;
- se o catálogo falha, deixa o "Salvar" desabilitado.

**Where**: `frontend-mobile/hooks/accountHooks/usePreferencesSetting.ts`
**Depends on**: None
**Reuses**: `listPreferences`, `getPreferencesByUser`, `assignPreference` e `unassignPreference` (T7) e a lógica de seleção de `usePreferences.ts:50-63`
**Requirement**: ACC-48, ACC-49, ACC-50, ACC-51, ACC-52

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Sem mudança na seleção, o hook não faz chamada.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): add the preferences setting hook`

---

#### T18: Tela de preferências

**What**: Criar `components/account/PreferencesSettingScreen.tsx` com o seletor do cadastro e "Salvar", as rotas `customer/configs/preferencesSetting.tsx` e `hairdresser/configs/preferencesSetting.tsx`, e o item "Preferências" nos dois menus.

**Where**: `frontend-mobile/components/account/PreferencesSettingScreen.tsx` (mais as duas rotas e os dois menus)
**Depends on**: T17
**Reuses**: `app/(auth)/register/preferences.tsx:77-100` e `styles/register/styles/PreferencesStyle.ts`
**Requirement**: ACC-47

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Os dois menus abrem a tela, e ela mostra as preferências atuais marcadas.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): edit the preferences`

---

#### T19: Hook `useResumeForm`

**What**: Hook do resumo do cabeleireiro: estado a partir de `userInfo.hairdresser.resume`, limite de 1000 caracteres com contagem, `PATCH {resume}` só se mudou, `loadSession` e as mensagens de ACC-18 a ACC-22.

**Where**: `frontend-mobile/hooks/accountHooks/useResumeForm.ts`
**Depends on**: None
**Reuses**: `updateMe` (T7) e `utils/account-validation.ts` (T10)
**Requirement**: ACC-54, ACC-55

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O hook não aceita texto acima de 1000 caracteres.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): add the resume form hook`

---

#### T20: Tela do resumo

**What**: Criar `app/(app)/hairdresser/configs/resumeSetting.tsx` com o textarea de `register/description.tsx:32-39`, a contagem "N/1000" e "Salvar", e o item "Resumo" no menu do cabeleireiro.

**Where**: `frontend-mobile/app/(app)/hairdresser/configs/resumeSetting.tsx` (mais `app/(app)/hairdresser/profile/settings.tsx`)
**Depends on**: T19
**Reuses**: o layout de `app/(auth)/register/description.tsx` e `ErrorModal`
**Requirement**: ACC-53

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O menu do cabeleireiro abre a tela com o resumo atual.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`

**Tests**: none (app sem suíte; gate App)
**Gate**: app
**Commit**: `feat(app): edit the hairdresser resume`

---

### Phase 6: UAT

#### T21: UAT no web e no Android

**What**: Rodar o roteiro abaixo com um cliente e um cabeleireiro (contas do seed e uma conta nova), atualizar a coluna Status da rastreabilidade do spec e corrigir o que falhar em tarefas de correção.

Roteiro:
1. **Dados da conta:**
   - trocar o nome e o telefone e salvar: a mensagem de sucesso aparece, e o perfil mostra os dados novos;
   - salvar sem mudar nada: aparece "Nenhuma alteração para salvar.";
   - apagar o sobrenome: aparece o erro, e nenhuma requisição sai (aba Network);
   - usar o telefone de outra conta: aparece a mensagem de `phone-taken`.
2. **Endereço:** digitar `69057-000`: o autofill preenche os campos e mantém o número. Salvar e reabrir a tela.
3. **Foto:**
   - trocar a foto: o perfil mostra a foto nova, e em `profile_pics/<id>/` do bucket do LocalStack só há o arquivo novo;
   - remover a foto: aparece a imagem padrão;
   - negar a permissão (Android): aparece a mensagem do spec.
4. **Preferências:** marcar uma, desmarcar outra, salvar e reabrir a tela. Com uma conta sem preferências, a tela abre vazia, sem erro.
5. **Resumo** (cabeleireiro): reescrever o resumo e salvar. O perfil público mostra o texto novo. A contagem trava em 1000.
6. **Exclusão:**
   - cancelar no modal: nada acontece;
   - confirmar: o app vai ao login sem crash, logar de novo falha e o usuário some do pool do MiniStack;
   - com o backend parado: aparece o erro de conexão, e a sessão continua.
7. **Sessão expirada** com uma tela de configuração aberta: o app segue o refresh e, se ele falhar, vai ao login (ACC-59).

**Where**: `.specs/features/account-settings/spec.md`
**Depends on**: None
**Reuses**: o roteiro de UAT do `email-confirmation` (T23)
**Requirement**: ACC-16 a ACC-33, ACC-43 a ACC-55, ACC-59

**Tools**:
- MCP: `claude-in-chrome` (UAT no web)
- Skill: `run`

**Done when**:
- [ ] Cada item do roteiro passa no web e no Android, ou vira uma tarefa de correção.
- [ ] Os critérios de app do spec ficam Verified.
- [ ] Gate check passes: Full + App.

**Tests**: none (UAT manual)
**Gate**: build
**Commit**: `docs(specs): record the account settings UAT`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6

Phase 1:  T1 ------→ T2 ------→ T3
          T4
Phase 2:  T5 ------→ T6
Phase 3:  T7    T8    T9    T10
Phase 4:  T11 ------→ T12
          T13 ------→ T14
Phase 5:  T15    T16
          T17 ------→ T18
          T19 ------→ T20
Phase 6:  T21
```

A execução é sequencial: uma tarefa de cada vez, na ordem.

**Lotes para sub-agentes** (21 tarefas, ~7 por lote, só fases inteiras):
- Lote 1: Phases 1 e 2 (T1 a T6), backend.
- Lote 2: Phases 3 e 4 (T7 a T14), base do app, conta e endereço.
- Lote 3: Phases 5 e 6 (T15 a T21), foto, exclusão, preferências, resumo e UAT. O T21 depende do usuário para o Android.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Validar o `PATCH` | 1 função + 1 view | ✅ Granular |
| T2: Conflito de telefone | 1 view | ✅ Granular |
| T3: Transação | 1 view | ✅ Granular |
| T4: Teste da exclusão Google | 1 teste | ✅ Granular |
| T5: `PUT` da foto | 1 endpoint (view + rota + Route Table) | ⚠️ Vários arquivos de propósito: o RT-50 falha se a rota existir sem a tabela |
| T6: `DELETE` da foto | 1 endpoint (view + Route Table) | ⚠️ Mesmo motivo do T5 |
| T7: Serviço | 1 arquivo | ✅ Granular |
| T8: `clearSession` | 1 função | ✅ Granular |
| T9: Guardas de nulo | 1 mudança repetida em 5 arquivos | ⚠️ Coeso: o mesmo padrão nos arquivos que quebram juntos |
| T10: Validação local | 1 módulo | ✅ Granular |
| T11, T13, T17, T19: Hooks | 1 hook cada | ✅ Granular |
| T12, T14, T18: Telas compartilhadas | 1 componente + rotas de uma linha | ⚠️ As rotas só renderizam o componente |
| T15: Foto | 1 hook + ligação na tela | ⚠️ Coeso |
| T16: Exclusão | 1 hook + item nos 2 menus | ⚠️ Coeso |
| T20: Tela do resumo | 1 tela + 1 item de menu | ⚠️ Coeso |
| T21: UAT | roteiro manual | ✅ |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | - | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | None | - | ✅ Match |
| T5 | None | - | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | None | - | ✅ Match |
| T8 | None | - | ✅ Match |
| T9 | None | - | ✅ Match |
| T10 | None | - | ✅ Match |
| T11 | None (usa T7 e T10, de uma fase anterior) | - | ✅ Match |
| T12 | T11 | T11 → T12 | ✅ Match |
| T13 | None (usa T7 e T10, de uma fase anterior) | - | ✅ Match |
| T14 | T13 | T13 → T14 | ✅ Match |
| T15 | None (usa T7 e T12, de fases anteriores) | - | ✅ Match |
| T16 | None (usa T7 e T8, de uma fase anterior) | - | ✅ Match |
| T17 | None (usa T7, de uma fase anterior) | - | ✅ Match |
| T18 | T17 | T17 → T18 | ✅ Match |
| T19 | None (usa T7 e T10, de uma fase anterior) | - | ✅ Match |
| T20 | T19 | T19 → T20 | ✅ Match |
| T21 | None (depende de todas as fases anteriores) | - | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1: Validar o `PATCH` | Backend: views de `users` | integration | integration | ✅ OK |
| T2: Conflito de telefone | Backend: views de `users` | integration | integration | ✅ OK |
| T3: Transação | Backend: views de `users` | integration | integration | ✅ OK |
| T4: Exclusão Google | Backend: views de `users` (só teste) | integration | integration | ✅ OK |
| T5: `PUT` da foto | Backend: views + Route Table | integration + unit | integration (+ `RouteTableTests`) | ✅ OK |
| T6: `DELETE` da foto | Backend: views + Route Table | integration + unit | integration (+ `RouteTableTests`) | ✅ OK |
| T7 a T20 | App (`frontend-mobile`) | none | none (gate App) | ✅ OK |
| T21: UAT | Specs | none | none | ✅ OK |
