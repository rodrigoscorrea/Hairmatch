# Cabeleireiros favoritos Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/favorite-hairdressers/spec.md`
**Context**: `.specs/features/favorite-hairdressers/context.md`
**Design**: `.specs/features/favorite-hairdressers/design.md`
**Status**: Execute: T1 a T10 concluídas. T11: a parte automatizada (E2E de API e bundle do Metro, no lugar do UAT em navegador) foi feita; o UAT manual no web e no Android está PENDENTE com o usuário.
**Branch**: `115-marcar-cabeleireiro-como-favorito`, criada a partir de `develop` em `c5d5242`.

**Pré-requisitos do Execute:**
- Os testes do backend rodam dentro do container `hairmatch_backend` (memória `backend-tests-run-in-docker`). Se o `hairmatch_db` estiver parado, rodar `docker start hairmatch_db`.
- Os testes usam o fake de Cognito do `HairmatchTestRunner`. Não precisam do LocalStack nem do MiniStack.
- O UAT (T11) precisa do `docker compose up` completo e do app no web, com a aba visível (memória `expo-web-smoke-needs-visible-tab`), e no Android.
- Há um app Django novo (`favorite`) com a migração `0001_initial`. Não há env var nova nem dependência nova.
- As linhas RT-97 a RT-99 já estão na Route Table do `api-restful-routes/spec.md`, no commit de planejamento, porque o AD-007 exige a tabela antes do código. O T2 e o T3 só as levam ao `ROUTE_TABLE` do `test_routes.py`.

**Ordem que mantém a suíte verde a cada commit:**
1. A Phase 1 (backend) vem antes do app, que depende das rotas.
2. A Phase 2 cria a base do app e o coração do perfil.
3. A Phase 3 cria a tela de favoritos e liga o menu.
4. A Phase 4 é o UAT.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas:
> - `.github/workflows/hairmatch-backend-test.yml`: `coverage run manage.py test`, sem limite mínimo.
> - `backend/preferences/tests.py` (rotas `PUT` e `DELETE` idempotentes, setup por `POST /api/users` e `activate_account`).
> - `backend/review/tests.py:1120` (`CustomerRatingRaceTest`, corrida com `TransactionTestCase` e `threading.Barrier`).
> - `backend/hairmatch/test_routes.py` (`ROUTE_TABLE`).
> - `frontend-mobile`: sem testes, por decisão herdada do #106, do #120 e do #118. O gate é `npx tsc --noEmit` mais o UAT.
>
> Strong defaults aplicados nas camadas de backend.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: modelo `FavoriteHairdresser` | integration | Unicidade do par (FAV-03), ordem padrão provada com `created_at` fora da ordem de inserção (FAV-19) e `CASCADE` a partir do cliente e do cabeleireiro. | `backend/favorite/tests.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput favorite'` |
| Backend: views do `favorite` | integration | Cada critério de backend do spec (FAV-01 a FAV-11, FAV-18 a FAV-24, FAV-39, FAV-40 e FAV-42): happy path, cada status de erro e "nenhuma linha mudou" onde o spec exige. A corrida do FAV-03 roda com `TransactionTestCase`. | `backend/favorite/tests.py` (`APIClient`) | idem |
| Backend: exclusão de conta e expurgo | integration | FAV-36 a FAV-38 e FAV-43 pelos caminhos reais: `DELETE /api/users/me`, `purge_unconfirmed_users` e a substituição no `POST /api/users`. | `backend/favorite/tests.py` | idem |
| Backend: contratos (`test_routes.py`) | unit | RT-97 a RT-99 em `ROUTE_TABLE`. | `backend/hairmatch/test_routes.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput hairmatch'` |
| App (`frontend-mobile`): tipos, serviço, hooks e telas | none | `npx tsc --noEmit` sem erro novo e o roteiro de UAT do T11. | - | App |
| Specs (`.specs/`) | none | `validate_spec.py` com exit 0. | - | - |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas com testes só de `favorite` ou só de `hairmatch` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput favorite hairmatch'` |
| Full | Tarefas que tocam o modelo, o URLconf ou o fim da Phase 1 | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput && coverage report -m'` |
| App | Tarefas do `frontend-mobile` | `cd frontend-mobile && npx tsc --noEmit`. O `eslint` só roda se o `eslint.config.js` estiver na branch, e hoje ele não está na `develop`. |
| Build | T11 (fim da feature) | Full + App + o roteiro de UAT do T11 |

> **Baseline de testes do backend:** `git grep -c "def test_"` em `c5d5242` conta **967**:
> - `users` 469;
> - `review` 159;
> - `hairmatch` 104 (`test_problems.py` 49, `tests.py` 46 e `test_routes.py` 9);
> - `availability` 55, `reserve` 52, `agenda` 46, `service` 40, `chatbot` 23 e `preferences` 19.
>
> Nenhuma tarefa reduz esses números. Antes do T1, rodar o gate Full para confirmar a baseline.

> **Gate do app:** antes do T5, registrar a saída atual de `npx tsc --noEmit` como baseline. O gate passa quando nenhuma tarefa acrescenta um erro novo.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend: modelo, rotas e ciclo de vida

```
T1 → T2 → T3
T1 → T4
```

### Phase 2: App: base e coração do perfil

```
T5 → T6 → T7
```

### Phase 3: App: tela de favoritos

```
T8 → T9 → T10
```

### Phase 4: UAT

```
T11
```

---

## Task Breakdown

### Phase 1: Backend: modelo, rotas e ciclo de vida

#### T1: App `favorite` e modelo `FavoriteHairdresser`

**What**: Criar o app `favorite` (`__init__.py`, `apps.py` com `FavoriteConfig`, `models.py` e `tests.py`) com o modelo do design (as duas FKs com `CASCADE`, `created_at`, `Meta.ordering = ['-created_at', '-id']` e a `UniqueConstraint` `unique_favorite_hairdresser`). O app entra em `INSTALLED_APPS`, e a migração `0001_initial` é gerada.
**Where**: `backend/favorite/models.py` (mais o app, a migração gerada e uma linha em `backend/hairmatch/settings.py`)
**Depends on**: None
**Reuses**: a estrutura do app `preferences`
**Requirement**: FAV-03, FAV-19

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Classe `FavoriteHairdresserModelTest` em `backend/favorite/tests.py` com:
  - criar o mesmo par duas vezes pelo ORM levanta `IntegrityError` (FAV-03);
  - três favoritos do mesmo cliente, com o `created_at` reescrito por `update()` fora da ordem de inserção, saem de `FavoriteHairdresser.objects.filter(customer=...)` do mais recente para o mais antigo. Dois com o mesmo `created_at` saem por `id` decrescente (FAV-19, lição L-018);
  - apagar o `Customer` apaga só os favoritos dele, e apagar o `Hairdresser` apaga os favoritos de todos os clientes para ele.
- [x] `makemigrations --check` limpo.
- [x] Gate check passes: Full.
- [x] Test count: 965 → 971 (6 testes novos), sem remoção.

**Tests**: integration
**Gate**: full
**Commit**: `feat(favorite): add the favorite hairdresser model`

---

#### T2: `PUT` e `DELETE /api/customers/me/favorite-hairdressers/{id}` (RT-98 e RT-99)

**What**: Criar a `FavoriteHairdresserDetail` com `put` e `delete`, como no design. Também entram:
- `backend/favorite/urls.py`, com a rota `favorite_hairdresser`;
- o `include('favorite.urls')` em `backend/hairmatch/urls.py`, antes do catch-all;
- RT-98 e RT-99 em `ROUTE_TABLE`, com o comentário do topo citando `favorite-hairdressers`.
**Where**: `backend/favorite/views.py` (mais `favorite/urls.py`, `hairmatch/urls.py` e `hairmatch/test_routes.py`)
**Depends on**: T1
**Reuses**: `UserPreferenceView` (`backend/preferences/views.py:15-42`), `authenticated_customer`, `problem_response`
**Requirement**: FAV-01, FAV-02, FAV-03, FAV-04, FAV-05, FAV-06, FAV-07, FAV-08, FAV-09, FAV-10, FAV-11, FAV-39

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Classe `FavoriteHairdresserDetailTest` (`TestCase`, com setup de dois clientes e dois cabeleireiros por `POST /api/users` e `activate_account`). Cada teste leva o requisito na docstring:
  - FAV-01: o `PUT` responde 204 com corpo vazio, e existe uma linha `(cliente, cabeleireiro)`;
  - FAV-02: o segundo `PUT` responde 204, a contagem continua 1, e o `created_at` é igual ao da primeira linha;
  - FAV-04: o `PUT` com um `id` que não existe responde 404 `not-found`, e a contagem é 0;
  - FAV-05: o `PUT` para um cabeleireiro com `user.is_active=False` responde 404 `not-found`, e a contagem é 0;
  - FAV-06: o `DELETE` responde 204 e apaga só o par. Outro favorito do mesmo cliente continua;
  - FAV-07: o `DELETE` de um cabeleireiro que não é favorito responde 204, e a contagem não muda;
  - FAV-08: o `DELETE` com um `id` que não existe responde 404 `not-found`;
  - FAV-09: o `PUT` e o `DELETE` sem cookie respondem 401 `invalid-session`, e nenhuma linha muda;
  - FAV-10: o `PUT` e o `DELETE` com sessão de cabeleireiro respondem 403 `customer-required`, e nenhuma linha muda;
  - FAV-11: o `DELETE` do cliente A mantém o favorito do cliente B para o mesmo cabeleireiro;
  - FAV-39: `PUT .../favorite-hairdressers/abc` responde 404 `not-found`.
- [x] Classe `FavoriteHairdresserRaceTest(TransactionTestCase)`: dois `PUT` do mesmo par atrás de um `threading.Barrier` respondem 204, e fica uma linha (FAV-03, lição L-016).
- [x] O `RouteTableTests` passa com RT-98 e RT-99.
- [x] Gate check passes: Full.
- [x] Test count: 971 → 984 (13 testes novos), sem remoção.

**Tests**: integration
**Gate**: full
**Commit**: `feat(favorite): favorite and unfavorite a hairdresser`

---

#### T3: `GET /api/customers/me/favorite-hairdressers` (RT-97)

**What**: Criar a `FavoriteHairdresserList`, como no design (filtro `hairdresser__user__is_active=True`, `select_related('hairdresser__user')` e `PublicHairdresserSerializer`). Também entram a rota `favorite_hairdressers` e o RT-97 em `ROUTE_TABLE`.
**Where**: `backend/favorite/views.py` (mais `favorite/urls.py` e `hairmatch/test_routes.py`)
**Depends on**: T2
**Reuses**: `PublicHairdresserSerializer` (`backend/users/serializers.py:37-42`) e o filtro da busca (`backend/users/views.py:897`)
**Requirement**: FAV-18, FAV-19, FAV-20, FAV-21, FAV-22, FAV-23, FAV-24, FAV-40, FAV-42

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Classe `FavoriteHairdresserListTest`:
  - FAV-18: cada item tem exatamente as chaves `id`, `user` e `resume`. O `user` não tem `email`, `phone` nem `postal_code`, e o item não tem `cnpj`;
  - FAV-19: três favoritos com o `created_at` reescrito fora da ordem de inserção saem do mais recente para o mais antigo;
  - FAV-20: um cliente sem favoritos recebe 200 `{"data": []}`;
  - FAV-21: o cliente A não vê os favoritos do cliente B;
  - FAV-22: um favorito cujo cabeleireiro passou a `is_active=False` some da lista e volta quando ele é reativado;
  - FAV-23: sem cookie, 401 `invalid-session`;
  - FAV-24: com sessão de cabeleireiro, 403 `customer-required`;
  - FAV-40: favoritar A, favoritar B, desfavoritar A e favoritar A de novo deixa a lista `[A, B]`, sem A repetido;
  - FAV-42: `PUT /api/customers/me/favorite-hairdressers` responde 405 `method-not-allowed`. O teste não fixa o conteúdo do `Allow`, porque o DRF acrescenta `HEAD` a todo `GET` (desvio do GAL-43).
- [x] O `RouteTableTests` passa com RT-97.
- [x] Gate check passes: Full.
- [x] Test count: 984 → 993 (9 testes novos), sem remoção.

**Tests**: integration
**Gate**: full
**Commit**: `feat(favorite): list the customer's favorite hairdressers`

---

#### T4: Favoritos na exclusão de conta e no expurgo

**What**: Testes de aceite do ciclo de vida pelos caminhos reais. Nenhuma mudança de código é esperada, porque o `CASCADE` do T1 cobre os caminhos. Se um teste falhar, a correção entra nesta tarefa.
**Where**: `backend/favorite/tests.py`
**Depends on**: T1
**Reuses**: `DELETE /api/users/me` (`backend/users/views.py:225-256`), o comando `purge_unconfirmed_users` e a substituição de conta pendente do `POST /api/users`
**Requirement**: FAV-36, FAV-37, FAV-38, FAV-43

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Classe `FavoriteLifecycleTest`:
  - FAV-36: o cliente A, com dois favoritos, exclui a conta por `DELETE /api/users/me` (resposta 204). As linhas dele somem, e o favorito do cliente B continua;
  - FAV-37: um cabeleireiro favoritado por A e por B exclui a conta. As duas linhas somem, e o favorito de A para outro cabeleireiro continua;
  - FAV-38: um favorito gravado pelo ORM para um cliente pendente com mais de 7 dias some quando `call_command('purge_unconfirmed_users')` roda, sem erro;
  - FAV-43: um favorito gravado pelo ORM para um cliente pendente (cadastrado por `POST /api/users`, sem `activate_account`) some quando um novo `POST /api/users` com o mesmo e-mail substitui a conta, e o novo cadastro responde 201.
- [x] Gate check passes: Full.
- [x] Test count: 993 → 997 (4 testes novos), sem remoção.

**Tests**: integration
**Gate**: full
**Commit**: `test(favorite): cover the favorites in account deletion and purge`

---

### Phase 2: App: base e coração do perfil

#### T5: Tipo e serviço dos favoritos

**What**: Criar o tipo `FavoriteHairdresser` (`Pick<HairdresserResponse, 'id' | 'user' | 'resume'>`) e o serviço com `listFavoriteHairdressers`, `addFavoriteHairdresser` e `removeFavoriteHairdresser`. As chamadas usam paths relativos ao `axiosInstance` e não usam `catch`.
**Where**: `frontend-mobile/services/favorite-hairdresser.service.ts` (mais `frontend-mobile/models/FavoriteHairdresser.types.ts`)
**Depends on**: None
**Reuses**: `frontend-mobile/services/gallery.service.ts`
**Requirement**: FAV-12, FAV-26

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] As três funções seguem os contratos do design: `GET` devolve `response.data.data`, `PUT` e `DELETE` devolvem `void`.
- [x] Gate check passes: App.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): add the favorite hairdresser requests`

---

#### T6: Hook `useFavoriteToggle`

**What**: Criar o hook do coração do perfil, como no design: carga no foco, `toggle` otimista com reversão, `disabled` durante a requisição e com a lista não carregada, e o `errorModal` com `problemMessage`.
**Where**: `frontend-mobile/hooks/customerHooks/useFavoriteToggle.ts`
**Depends on**: T5
**Reuses**: `frontend-mobile/hooks/customerHooks/useReceivedRatings.ts`
**Requirement**: FAV-12, FAV-13, FAV-14, FAV-15, FAV-16, FAV-17

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] O hook devolve `{ isFavorite, disabled, toggle, errorModal, closeError }`.
- [x] O fallback da mensagem é "Não foi possível atualizar seus favoritos.".
- [x] Gate check passes: App.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): add the favorite toggle hook`

---

#### T7: Coração no perfil público

**What**: Pôr o coração no header de `hairdresser-reservation/[id].tsx`, à direita do voltar, com `heart`/`heart-outline`, `disabled` e `accessibilityLabel`, e o `ErrorModal` do hook.
**Where**: `frontend-mobile/app/(app)/customer/hairdresser-reservation/[id].tsx`
**Depends on**: T6
**Reuses**: o header que já existe (`styles.header` com `space-between`)
**Requirement**: FAV-12, FAV-13, FAV-14, FAV-15, FAV-16, FAV-17

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] O coração aparece só depois que o perfil carregou, ao lado oposto do voltar.
- [x] Gate check passes: App.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): favorite a hairdresser from the profile`

---

### Phase 3: App: tela de favoritos

#### T8: Hook `useFavoriteHairdressers`

**What**: Criar o hook da tela, como no design:
- carga no foco, com `isLoaded`;
- `handleRemove` otimista, que devolve o item ao mesmo índice na falha, com `removing`;
- `handleOpen` e `handleGoBack`;
- o `errorModal`, com os fallbacks "Não foi possível carregar seus favoritos." e "Não foi possível atualizar seus favoritos.".
**Where**: `frontend-mobile/hooks/customerHooks/useFavoriteHairdressers.ts`
**Depends on**: None
**Reuses**: `useReceivedRatings`
**Requirement**: FAV-25, FAV-26, FAV-28, FAV-30, FAV-32, FAV-33, FAV-35, FAV-41

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] O hook devolve `{ favorites, isLoaded, removing, handleRemove, handleOpen, handleGoBack, errorModal, closeError }`.
- [x] Gate check passes: App.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): add the favorite hairdressers hook`

---

#### T9: Tela "Favoritos"

**What**: Criar `customer/favorites.tsx` no esqueleto de `ratings.tsx`:
- o título "Favoritos";
- os cards do design, com a área do perfil e o coração separados;
- o `ListEmptyComponent` só com `isLoaded`;
- o `ErrorModal`.

A rota é registrada com `href: null` em `customer/_layout.tsx`.
**Where**: `frontend-mobile/app/(app)/customer/favorites.tsx` (mais uma linha em `customer/_layout.tsx`)
**Depends on**: T8
**Reuses**: `ratings.tsx`, o card de `search.tsx:59-79` e `SearchStyle.ts`
**Requirement**: FAV-25, FAV-26, FAV-27, FAV-28, FAV-29, FAV-30, FAV-31, FAV-32, FAV-33, FAV-34, FAV-35

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] A tela não aparece na barra de abas.
- [x] A mensagem de lista vazia é "Você ainda não tem cabeleireiros favoritos.".
- [x] Gate check passes: App.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): add the favorite hairdressers screen`

---

#### T10: Menu "Favoritos" do perfil do cliente

**What**: Acrescentar `handleFavorites` ao `useCustomerProfile`, com `router.push('/(app)/customer/favorites')`, e ligá-lo ao `MenuItem` "Favoritos" de `profile.tsx`, no lugar de `handleMenuPress('Favoritos')`.
**Where**: `frontend-mobile/app/(app)/customer/profile.tsx` (mais `hooks/customerHooks/useCustomerProfile.ts`)
**Depends on**: T9
**Reuses**: `handleReceivedRatings`
**Requirement**: FAV-25

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] O toque em "Favoritos" abre a tela do T9.
- [x] Os outros itens do menu não mudam.
- [x] Gate check passes: App.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): open the favorites from the customer profile`

---

### Phase 4: UAT

#### T11: UAT no web e no Android

**What**: Rodar o roteiro abaixo com um cliente novo e dois cabeleireiros do seed. Depois, atualizar a coluna Status da rastreabilidade do spec. O que falhar vira uma tarefa de correção.

Roteiro:
1. **Perfil público:** abrir o cabeleireiro A. O coração aparece vazio à direita do voltar. Tocar: ele fica preenchido. Sair e voltar ao perfil: continua preenchido. Tocar de novo: ele esvazia.
2. **Lista:** favoritar A e depois B. Abrir Perfil → "Favoritos": B aparece antes de A, com foto, nome, nota e "bairro, cidade". O toque no card de A abre o perfil dele.
3. **Desfavoritar pela lista:** tocar no coração do card de B. O card some na hora, sem modal. Voltar ao perfil de B: o coração está vazio.
4. **Lista vazia:** desfavoritar A pela lista. Aparece "Você ainda não tem cabeleireiros favoritos.".
5. **Volta do perfil para a lista (FAV-41):** com A favorito, abrir "Favoritos" → A → desfavoritar → voltar. A lista não mostra A.
6. **Falha:** com o backend parado (`docker stop hairmatch_backend`), tocar no coração no perfil e na lista. O estado volta, e o modal diz "Não foi possível conectar ao servidor.". Religar o backend.
7. **Exclusão da conta:** excluir a conta do cliente com favoritos. Com um segundo cliente, os favoritos dele para os mesmos cabeleireiros continuam.

**Where**: `.specs/features/favorite-hairdressers/spec.md`
**Depends on**: None
**Reuses**: o roteiro de UAT da `hairdresser-gallery` (T18)
**Requirement**: FAV-12, FAV-13, FAV-14, FAV-15, FAV-16, FAV-17, FAV-25, FAV-26, FAV-27, FAV-28, FAV-29, FAV-30, FAV-31, FAV-32, FAV-33, FAV-34, FAV-35, FAV-41

**Tools**:
- MCP: NONE (o usuário não autorizou o Claude in Chrome no UAT da #118). O UAT em tela é do usuário. Sem ele, entra o E2E de API contra o servidor da branch, como no T18 da galeria, e os itens de tela ficam pendentes.
- Skill: `run`

**Done when**:
- [ ] Cada item do roteiro passa no web e no Android, ou vira uma tarefa de correção.
- [ ] Os critérios de app do spec ficam Verified.
- [ ] Gate check passes: Build.

**Status (Execute)**: PARCIAL. O UAT manual no web e no Android está PENDENTE e não foi feito (o usuário proibiu o Claude in Chrome, e o Android depende dele). No lugar do roteiro em navegador:
- **E2E de API** contra um servidor Django real do worktree (porta 8001, banco descartável `hairmatch_e2e_fav`, MiniStack para o Cognito): 46 de 46 verificações passam. Cobrem as três rotas (RT-97 a RT-99) com cookies reais, 401 e 403, o formato público do item, a ordem do mais recente ao mais antigo, o `PUT` repetido que mantém linha e `created_at`, 6 `PUT` simultâneos que deixam uma linha, 404 para `{id}` desconhecido, pendente e `abc`, 405 no path da lista, o isolamento entre clientes, o cabeleireiro pendente que sai da lista e volta, o preflight de CORS de `PUT` e `DELETE` a partir do `:8081`, e a exclusão da conta do cabeleireiro e do cliente. O servidor, o banco e os usuários do Cognito foram removidos depois.
- **Bundle do Metro**: o app compila com as telas novas (`Web Bundled … 2400 modules`, sem erro), e `npx tsc --noEmit` fecha com 0 erros depois que o Metro regenerou o `.expo/types/router.d.ts`.

Os itens do roteiro que dependem da tela (1 a 6, e o 7 no app) seguem sem prova e continuam no UAT manual. Os critérios de app (FAV-12 a FAV-17, FAV-25 a FAV-35 e FAV-41) ficam como Implemented até esse UAT.

**Tests**: none
**Gate**: build
**Commit**: `docs(specs): record the favorite hairdressers UAT`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4

Phase 1:  T1 ------→ T2 ------→ T3
          T1 ------→ T4
Phase 2:  T5 ------→ T6 ------→ T7
Phase 3:  T8 ------→ T9 ------→ T10
Phase 4:  T11
```

A execução é sequencial: uma tarefa de cada vez, na ordem T1 a T11.

**Lotes para sub-agentes** (11 tarefas, cerca de 7 por lote, só fases inteiras):
- Lote 1: Phase 1 (T1 a T4), o backend.
- Lote 2: Phases 2, 3 e 4 (T5 a T11), o app e o UAT. O T11 depende do usuário para o Android.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Modelo | 1 modelo + app + migração gerada + 1 linha de settings | ⚠️ Coeso: o app só existe para o modelo, e a migração é gerada |
| T2: `PUT` e `DELETE` | 1 view (2 métodos de um mesmo path) + rota + `ROUTE_TABLE` | ⚠️ Vários arquivos de propósito: o RT-50 falha se a rota existir sem a tabela |
| T3: `GET` | 1 view + rota + `ROUTE_TABLE` | ⚠️ Mesmo motivo do T2 |
| T4: Ciclo de vida | 1 classe de testes | ✅ Granular |
| T5: Serviço | 1 serviço + 1 tipo | ⚠️ Coeso: o tipo só existe para o serviço |
| T6: `useFavoriteToggle` | 1 hook | ✅ Granular |
| T7: Coração no perfil | 1 tela | ✅ Granular |
| T8: `useFavoriteHairdressers` | 1 hook | ✅ Granular |
| T9: Tela "Favoritos" | 1 tela + 1 linha de rota | ⚠️ A linha só registra a tela |
| T10: Menu | 1 handler + 1 linha de tela | ⚠️ Coeso |
| T11: UAT | roteiro manual | ✅ |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | - | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T1 | T1 → T4 | ✅ Match |
| T5 | None (usa as rotas da Phase 1) | - | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | T6 | T6 → T7 | ✅ Match |
| T8 | None (usa T5, de uma fase anterior) | - | ✅ Match |
| T9 | T8 | T8 → T9 | ✅ Match |
| T10 | T9 | T9 → T10 | ✅ Match |
| T11 | None (depende de todas as fases anteriores) | - | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1: Modelo | Backend: modelo | integration | integration | ✅ OK |
| T2: `PUT` e `DELETE` | Backend: views + Route Table | integration + unit | integration (+ `RouteTableTests`) | ✅ OK |
| T3: `GET` | Backend: views + Route Table | integration + unit | integration (+ `RouteTableTests`) | ✅ OK |
| T4: Ciclo de vida | Backend: exclusão de conta e expurgo | integration | integration | ✅ OK |
| T5: Serviço | App | none | none | ✅ OK |
| T6: Hook do coração | App | none | none | ✅ OK |
| T7: Perfil público | App | none | none | ✅ OK |
| T8: Hook da lista | App | none | none | ✅ OK |
| T9: Tela | App | none | none | ✅ OK |
| T10: Menu | App | none | none | ✅ OK |
| T11: UAT | Specs | none | none | ✅ OK |
