# Minhas avaliações (cabeleireiro) Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/hairdresser-reviews/spec.md`
**Context**: `.specs/features/hairdresser-reviews/context.md`
**Design**: `.specs/features/hairdresser-reviews/design.md`
**Status**: Approved. Execute em andamento.
**Branch**: `189-avaliacoes-recebidas-cabeleireiro`, criada a partir da `develop` (`23d900a`, com a #182 mesclada).

**Pré-requisitos do Execute:**
- Os testes do backend rodam dentro do container `hairmatch_backend` (memória `backend-tests-run-in-docker`). Se o `hairmatch_db` estiver parado, rodar `docker start hairmatch_db`.
- Os testes usam o fake de Cognito do `HairmatchTestRunner`, e o storage dos testes é `InMemoryStorage`. Não precisam do LocalStack nem do MiniStack.
- Não há migração, env var nem dependência nova.
- Nenhuma rota entra nem sai, então o `test_routes.py` não muda. A nota de ordem do RT-24 já foi acrescentada à Route Table do `api-restful-routes/spec.md`, numa edição de planejamento ainda sem commit.
- **A Phase 3 (T7) só começa com a #182 (`push-notifications`) mesclada na `develop`**, porque o `utils/alert-routes.ts` e o tratamento do toque nascem no T16 da #182. As Phases 1 e 2 não dependem da #182. Se a #182 não estiver mesclada quando a Phase 2 terminar, o Execute para antes do T7 e registra o ponto no Handoff.
- O UAT (T8) precisa do `docker compose up` completo e do app no web, com a aba visível (memória `expo-web-smoke-needs-visible-tab`). A parte de push precisa de um dev build Android com o Firebase real (T20 da #182).

**Ordem que mantém a suíte verde a cada commit:**
1. A Phase 1 (backend) muda a ordem da RT-24 e o teste antigo no mesmo commit.
2. A Phase 2 cria a tela e o acesso pelo perfil.
3. A Phase 3 liga o toque do alerta e emenda a spec da #182.
4. A Phase 4 é o UAT.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas:
> - `.github/workflows/hairmatch-backend-test.yml`: `coverage run manage.py test`, sem limite mínimo.
> - `backend/review/tests.py`: `ListReviewTest` (`:570`, criação pelo `POST /api/reviews`) e `ListReviewPicturesTest` (`:1704`, formato das fotos).
> - `frontend-mobile`: sem testes, por decisão herdada do #106, do #115, do #118 e do #120. O gate é `npx tsc --noEmit` mais o UAT.
>
> Strong defaults aplicados na camada de backend.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: view `ListReview` (RT-24) | integration | Cada critério de backend do spec (HRV-01 a HRV-05). A ordem é provada com `created_at` reescrito fora da ordem de inserção, e o desempate com `created_at` igual. | `backend/review/tests.py` (`APIClient`) | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput review'` |
| App (`frontend-mobile`): tipo, serviço, hook, componente, telas e `alertRoute` | none | `npx tsc --noEmit` sem erro novo e o roteiro de UAT do T8. | - | App |
| Specs (`.specs/`) | none | `validate_spec.py` com exit 0 nas specs emendadas. | - | - |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | T1, durante o desenvolvimento | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput review'` |
| Full | Fim do T1 (fim da Phase 1) | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput && coverage report -m'` |
| App | Tarefas do `frontend-mobile` | `cd frontend-mobile && npx tsc --noEmit`. Rota nova só existe para o `tsc` depois que o Metro regenera os typed routes. O `eslint` só roda se o `eslint.config.js` estiver na branch, e hoje ele é WIP sem commit. |
| Build | T8 (fim da feature) | Full + App + o roteiro de UAT do T8 |

> **Baseline de testes do backend:** `git grep -c "def test_"` na `develop` (`fb3d11a`) contava **999**, sendo **159** em `review`. Com a #182 mesclada (`23d900a`), a baseline recontada no início do T1 é **1120** (171 em `review`), e a suíte roda 1118 testes. Nenhuma tarefa reduz esses números. Antes do T1, rodar o gate Full para confirmar a baseline.

> **Gate do app:** antes do T2, registrar a saída atual de `npx tsc --noEmit` como baseline. O gate passa quando nenhuma tarefa acrescenta um erro novo.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend: ordem da RT-24

```
T1
```

### Phase 2: App: tela e acesso pelo perfil

```
T2 → T3 → T5 → T6
T4 → T5
```

### Phase 3: App: toque no alerta e no push (exige a #182 na `develop`)

```
T7
```

### Phase 4: UAT

```
T8
```

---

## Task Breakdown

### Phase 1: Backend: ordem da RT-24

#### T1: `ListReview` do mais recente para o mais antigo

**What**: Trocar `.order_by('id')` por `.order_by('-created_at', '-id')` no `ListReview`. Atualizar o comentário da linha. Atualizar o `test_list_reviews` para a ordem do spec e escrever os testes novos de ordem, desempate, isolamento e edição.
**Where**: `backend/review/views.py` (`ListReview`, linha 146). Os testes ficam co-localizados no arquivo de testes do app `review`.
**Depends on**: None
**Reuses**: `ReviewsTestCase` e o setup do `ListReviewTest` (`backend/review/tests.py:570`); a ordem de `CustomerRatingsByCustomer` (`backend/review/views.py:396`)
**Requirement**: HRV-01, HRV-02, HRV-03, HRV-04, HRV-05

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] O `test_list_reviews` espera a review de nota 5 (a segunda criada) em `data[0]` e a de nota 4 em `data[1]` (HRV-01).
- [x] Os testes novos ficam numa classe `ListReviewOrderTest` em `backend/review/tests.py`:
  - três reviews do mesmo cabeleireiro com o `created_at` reescrito por `update()` fora da ordem de inserção saem do `created_at` mais recente para o mais antigo (HRV-01, lição L-018);
  - duas reviews com o mesmo `created_at` saem pela de maior `id` primeiro (HRV-02);
  - reviews de dois cabeleireiros: o `GET` de cada um traz só as dele (HRV-04);
  - depois de um `PUT /api/reviews/{id}` na review mais antiga, ela continua na última posição (HRV-05);
  - o item tem exatamente as chaves `id`, `rating`, `comment`, `created_at`, `customer`, `hairdresser` e `pictures`. O `customer` é `{id, user: {id, first_name, last_name}}`, com os valores do cliente (HRV-03).
- [x] O `ListReviewPicturesTest` continua provando as fotos por `id` crescente (HRV-03). O teste de contagem de queries lista 3 reviews com 2, 3 e 1 fotos, então a ordem nova muda o `[2, 3, 1]` esperado para `[1, 3, 2]`. É mudança de spec (HRV-01), não asserção enfraquecida.
- [x] `makemigrations --check` limpo.
- [x] Gate check passes: Full.
- [x] Test count: 1120 → 1125 `def test_` (5 testes novos, baseline recontada com a #182 na `develop`), sem remoção. A suíte roda 1118 → 1123.

**Tests**: integration
**Gate**: full
**Commit**: `feat(review): list a hairdresser's reviews newest first`

---

### Phase 2: App: tela e acesso pelo perfil

#### T2: Tipo `ReceivedReview` e `getHairdresserReviews`

**What**:
- Criar a função `getHairdresserReviews(hairdresserId)` em `services/review.service.ts`. Ela faz `GET /api/hairdressers/{id}/reviews` e devolve `response.data.data`, sem `catch`.
- Acrescentar a `models/Review.types.ts` a interface `ReceivedReview`, com o `customer` aninhado do design.

**Where**: `frontend-mobile/services/review.service.ts`
**Depends on**: None
**Reuses**: as outras funções de `review.service.ts` (`axiosInstance` e `withCredentials`)
**Requirement**: HRV-03, HRV-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `ReceivedReview` declara `customer: { id; user: { id; first_name; last_name } }`, e o tipo `Review` existente não muda.
- [ ] `getHairdresserReviews` devolve `Promise<ReceivedReview[]>` e deixa o erro subir.
- [ ] Gate check passes: App.

**Tests**: none
**Gate**: build
**Commit**: `feat(app): add the hairdresser reviews service`

---

#### T3: Hook `useHairdresserReviews`

**What**: Criar o hook do design. Ele carrega no foco com a flag `active` e marca `isLoaded` só no sucesso. Na falha, abre o `errorModal` com o fallback "Não foi possível carregar suas avaliações.". O `handleGoBack` chama `router.back()`.
**Where**: `frontend-mobile/hooks/hairdresserHooks/useHairdresserReviews.ts` (new)
**Depends on**: T2
**Reuses**: `useReceivedRatings` (`frontend-mobile/hooks/customerHooks/useReceivedRatings.ts`)
**Requirement**: HRV-06, HRV-16, HRV-17, HRV-21, HRV-28, HRV-30

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Sem `userInfo.hairdresser.id`, o hook não chama o serviço.
- [ ] Cada foco chama `getHairdresserReviews` de novo, e uma resposta que chega depois de perder o foco é descartada.
- [ ] Na falha, `isLoaded` continua `false`, e o `errorModal` usa `problemMessage`.
- [ ] Gate check passes: App.

**Tests**: none
**Gate**: build
**Commit**: `feat(app): add the hairdresser reviews hook`

---

#### T4: Componente `PhotoViewer`

**What**: Mover o `Modal` de foto em tela cheia do `GalleryStrip` para `components/PhotoViewer.tsx` (`{ uri: string | null, onClose }`), sem mudança visual. O `GalleryStrip` passa a usar o componente.
**Where**: `frontend-mobile/components/PhotoViewer.tsx` (new)
**Depends on**: None
**Reuses**: o modal e os estilos `viewer`, `fullImage` e `closeButton` de `frontend-mobile/components/gallery/GalleryStrip.tsx`
**Requirement**: HRV-14

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O `PhotoViewer` fica visível enquanto `uri !== null`, e o botão de fechar tem `accessibilityLabel="Fechar foto"`.
- [ ] O `GalleryStrip` não tem mais `Modal` próprio e continua abrindo e fechando a foto como antes. O T8 confere isso.
- [ ] Gate check passes: App.

**Tests**: none
**Gate**: build
**Commit**: `refactor(app): extract the full screen photo viewer`

---

#### T5: Tela "Minhas avaliações"

**What**: Criar a tela do design com:
- o título "Minhas avaliações" e o "‹ Voltar";
- a `FlatList` com `ListEmptyComponent` só depois do carregamento;
- o card com o nome do cliente, o `StarRating` só de leitura, o valor da nota por `formatRating`, a data `DD/MM/YYYY`, o comentário só quando `comment?.trim()`, e a faixa horizontal de miniaturas que abre o `PhotoViewer`;
- o `ErrorModal`.

Em `hairdresser/profile/_layout.tsx`, registrar `<Stack.Screen name="reviews" />` e exportar `unstable_settings = { initialRouteName: 'index' }`.
**Where**: `frontend-mobile/app/(app)/hairdresser/profile/reviews.tsx` (new)
**Depends on**: T3, T4
**Reuses**: `frontend-mobile/app/(app)/customer/ratings.tsx` (esqueleto e estilos), `StarRating`, `PhotoViewer`
**Requirement**: HRV-07, HRV-08, HRV-09, HRV-10, HRV-11, HRV-12, HRV-13, HRV-14, HRV-15, HRV-16, HRV-18, HRV-25, HRV-29

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `formatRating(4)` dá `"4"`, e `formatRating(4.5)` dá `"4,5"`.
- [ ] Uma review com `comment` `null`, `""` ou `"   "` não ganha área de comentário.
- [ ] As miniaturas seguem a ordem de `pictures`, cada uma com `accessibilityLabel="Abrir foto"`, e 5 delas rolam na horizontal sem alargar o card.
- [ ] A mensagem de lista vazia é "Você ainda não recebeu avaliações." e só aparece com `isLoaded`.
- [ ] A rota `/(app)/hairdresser/profile/reviews` abre no web. Aberta direto pela URL, "‹ Voltar" leva ao perfil (HRV-18).
- [ ] Gate check passes: App, com os typed routes regenerados.

**Tests**: none
**Gate**: build
**Commit**: `feat(app): add the hairdresser reviews screen`

---

#### T6: Card "Minhas avaliações" no perfil

**What**: Acrescentar `goToReviews` ao `useHairdresserProfile`, que faz `router.push('/(app)/hairdresser/profile/reviews')`. No perfil, acrescentar o card "Minhas avaliações" logo abaixo de "Minha galeria", com `styles.card`, `styles.cardText` e a seta.
**Where**: `frontend-mobile/app/(app)/hairdresser/profile/index.tsx`
**Depends on**: T5
**Reuses**: o card "Minha galeria" (`index.tsx:72-75`) e o `goToGallery` (`useHairdresserProfile.ts:36`)
**Requirement**: HRV-19, HRV-20, HRV-21

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O card aparece abaixo de "Minha galeria", com o mesmo estilo.
- [ ] O toque abre "Minhas avaliações", e "‹ Voltar" volta ao perfil.
- [ ] Gate check passes: App.

**Tests**: none
**Gate**: build
**Commit**: `feat(app): open the reviews from the hairdresser profile`

---

### Phase 3: App: toque no alerta e no push (exige a #182 na `develop`)

#### T7: `alertRoute` leva review criada ou editada a "Minhas avaliações"

**What**:
- Em `utils/alert-routes.ts`, `review-created` e `review-updated` passam a devolver `'/(app)/hairdresser/profile/reviews'`. `review-deleted` continua `null`, e os outros `kind` não mudam.
- No mesmo commit, emendar a spec da #182, como no design:
  - em `push-notifications/spec.md`: as células "Toque" do catálogo, o NOTIF-34, o NOTIF-63, a linha do Out of Scope e a assumption do toque;
  - em `push-notifications/tasks.md`: o item do T16 sobre `review-*`.

**Where**: `frontend-mobile/utils/alert-routes.ts`
**Depends on**: None (usa a tela do T5, de uma fase anterior, e o `alertRoute` da #182)
**Reuses**: `alertRoute`, `usePushNotifications` e `useAlerts` da #182, que já navegam pelo retorno
**Requirement**: HRV-22, HRV-23, HRV-24, HRV-25, HRV-26, HRV-27

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `alertRoute('review-created', ...)` e `alertRoute('review-updated', ...)` devolvem `'/(app)/hairdresser/profile/reviews'`.
- [ ] `alertRoute('review-deleted', ...)` devolve `null`.
- [ ] `alertRoute` de `reservation-created` e `customer-rating-*` devolve o mesmo destino de antes.
- [ ] O catálogo, o NOTIF-34, o NOTIF-63 e o T16 da `push-notifications` descrevem o destino novo, e `validate_spec.py .specs/features/push-notifications` sai com exit 0.
- [ ] Gate check passes: App.

**Tests**: none
**Gate**: build
**Commit**: `feat(app): open the reviews screen from review alerts`

---

### Phase 4: UAT

#### T8: UAT no web e no Android

**What**: Rodar o roteiro abaixo com um cabeleireiro do seed e um cliente com dois atendimentos terminados. Depois, atualizar a coluna Status da rastreabilidade do spec. O que falhar vira uma tarefa de correção.

Roteiro:
1. **Lista vazia:** como cabeleireiro sem reviews, abrir Perfil → "Minhas avaliações". Aparece "Você ainda não recebeu avaliações.". "‹ Voltar" leva ao perfil.
2. **Lista:** como cliente, avaliar o primeiro atendimento com nota 4, sem comentário e com 2 fotos. Depois, avaliar o segundo com nota 5, um comentário e nenhuma foto. Como cabeleireiro, abrir a tela:
   - a review de nota 5 aparece primeiro, com o nome do cliente, 5 estrelas, "5", a data de hoje e o comentário;
   - a de nota 4 não tem área de comentário e mostra 2 miniaturas.
3. **Foto:** tocar numa miniatura. A foto abre em tela cheia, e "Fechar foto" fecha. Na galeria do perfil, a foto também abre e fecha como antes (T4).
4. **Edição:** como cliente, editar a review de nota 4 para 3. Na tela do cabeleireiro, ela continua em segundo lugar e mostra "3".
5. **Falha:** com o backend parado (`docker stop hairmatch_backend`), abrir a tela. O modal diz "Não foi possível conectar ao servidor.", e a mensagem de lista vazia não aparece. Religar o backend.
6. **Toque (só com a Phase 3 feita):** num dev build Android com a #182, como cliente, criar uma review.
   - Com o app do cabeleireiro fechado, o toque no push abre "Minhas avaliações" no topo, com a review nova. "‹ Voltar" leva ao perfil. Este item prova a rota inicial da pilha do perfil, que não foi conferida na documentação (design, Risks).
   - Na caixa de alertas, o toque em "Avaliação atualizada" abre a tela, e o toque em "Avaliação removida" fica na caixa.

**Where**: `.specs/features/hairdresser-reviews/spec.md`
**Depends on**: None
**Reuses**: o roteiro de UAT da `favorite-hairdressers` (T11)
**Requirement**: HRV-06, HRV-07, HRV-08, HRV-09, HRV-10, HRV-11, HRV-12, HRV-13, HRV-14, HRV-15, HRV-16, HRV-17, HRV-18, HRV-19, HRV-20, HRV-21, HRV-22, HRV-23, HRV-24, HRV-25, HRV-26, HRV-27, HRV-28, HRV-29, HRV-30

**Tools**:
- MCP: NONE. O UAT em tela é do usuário. Sem ele, entra o E2E de API contra o servidor da branch, como no T11 da `favorite-hairdressers`, e os itens de tela ficam pendentes.
- Skill: `run`

**Done when**:
- [ ] Cada item do roteiro passa no web e no Android, ou vira uma tarefa de correção.
- [ ] Os critérios de app do spec ficam Verified.
- [ ] Gate check passes: Build.

**Tests**: none
**Gate**: build
**Commit**: `docs(specs): record the hairdresser reviews UAT`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4

Phase 1:  T1
Phase 2:  T2 ------→ T3 ------→ T5 ------→ T6
          T4 ------→ T5
Phase 3:  T7   (só com a #182 na develop)
Phase 4:  T8
```

A execução é sequencial: uma tarefa de cada vez, na ordem de T1 a T8. São 8 tarefas, que cabem num lote só, então o Execute roda inline, sem sub-agentes de lote. O Verificador independente roda no fim, como sempre.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Ordem da RT-24 | 1 linha de view + os testes dela | ✅ Granular |
| T2: Serviço | 1 função + 1 tipo | ⚠️ Coeso: o tipo só existe para o serviço |
| T3: Hook | 1 hook | ✅ Granular |
| T4: `PhotoViewer` | 1 componente + o uso no `GalleryStrip` | ⚠️ Coeso: a extração só fica completa com a origem usando o componente |
| T5: Tela | 1 tela + o registro na pilha do perfil | ⚠️ O registro só existe para a tela |
| T6: Card no perfil | 1 handler + 1 card | ⚠️ Coeso |
| T7: `alertRoute` | 1 função + a emenda na spec da #182 | ⚠️ Coeso: o código e o resultado esperado pela spec mudam juntos |
| T8: UAT | roteiro manual | ✅ |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | - | ✅ Match |
| T2 | None | - | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | None | - | ✅ Match |
| T5 | T3, T4 | T3 → T5, T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | None (usa T5, de uma fase anterior) | - | ✅ Match |
| T8 | None (depende de todas as fases anteriores) | - | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1: Ordem da RT-24 | Backend: view `ListReview` | integration | integration | ✅ OK |
| T2: Serviço | App | none | none | ✅ OK |
| T3: Hook | App | none | none | ✅ OK |
| T4: `PhotoViewer` | App | none | none | ✅ OK |
| T5: Tela | App | none | none | ✅ OK |
| T6: Card no perfil | App | none | none | ✅ OK |
| T7: `alertRoute` | App + Specs | none | none | ✅ OK |
| T8: UAT | Specs | none | none | ✅ OK |
