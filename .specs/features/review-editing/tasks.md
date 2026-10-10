# Editar e excluir avaliações, com várias fotos Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/review-editing/spec.md`
**Design**: `.specs/features/review-editing/design.md`
**Status**: Draft (aguardando aprovação para Execute)
**Branch**: `105-editar-e-excluir-avaliacao`, criada a partir de `develop` em `2948100`.

**Pré-requisitos do Execute:**
- Os testes do backend rodam dentro do container `hairmatch_backend` (memória `backend-tests-run-in-docker`). Se der `could not translate host name "db"`, rodar `docker start hairmatch_db`.
- Nenhuma env var nova e nenhuma dependência nova.
- Os arquivos não commitados de antes ficam fora dos commits desta feature:
  - `frontend-mobile/.env.example`, `frontend-mobile/package.json`, `frontend-mobile/package-lock.json`;
  - `frontend-mobile/services/axios-instance.ts`, `frontend-mobile/eslint.config.js`;
  - `.specs/LESSONS.md`, `.specs/lessons.json` e `docs/`.
- A feature `hairdresser-gallery` (#118) foi planejada em paralelo. Ela usa o AD-013 e as rotas RT-94 a RT-96, e deixou reservados para esta feature o AD-011, o AD-012 e as rotas RT-90 a RT-93. Se ela entrar antes, a T1 parte do código dela, e a `GalleryPhoto` também passa a usar `delete_stored_files`. Se entrar depois, é ela que troca a referência.
- O stash `stale specs before pulling #104/#113/#120` guarda as cópias antigas de `.specs/` que estavam no checkout. Elas já estavam na `develop` em versão mais nova e não entram nesta feature.

**Ordem que mantém a suíte verde a cada commit:**
1. Phase 1 (expand): `ReviewPicture` entra ao lado de `Review.picture`, e as leituras ganham `pictures`.
2. Phase 2 (contract): as escritas migram, e a T8 remove a coluna `picture` junto com o último uso dela.
3. Phase 3: edição e exclusão da nota do cabeleireiro, mais os ADs.
4. Phases 4 e 5: o app. Entre a T6 e a T16, o app antigo manda `picture` e perde a foto. É o corte único do AD-007: backend e app saem no mesmo PR.

**Testes existentes que mudam de contrato** (reescritos, nunca apagados):

| Teste | Onde | AC que o substitui | Task |
| ----- | ---- | ------------------ | ---- |
| `test_create_review_with_picture_stores_a_webp` (WEBP-03) | `backend/review/tests.py:204` | REV-01 e REV-02: campo `pictures`, chave `reviews/<id>/<hex>.webp`, conteúdo WebP | T6 |
| `test_create_review_with_a_file_that_is_not_an_image_returns_400` (WEBP-12) | `backend/review/tests.py:236` | REV-06: mesmo 400, agora com `pictures` e com o storage vazio | T6 |
| `test_create_review_with_an_image_over_the_pixel_limit_returns_400` (WEBP-13) | `backend/review/tests.py:247` | REV-06: idem | T6 |
| `test_a_picture_in_the_body_is_ignored` | `backend/review/tests.py:452` | REV-20: o PUT não cria nem remove fotos (`review.pictures.count() == 0`) | T8 |
| `_hairdresser_with_bookings` e os dois testes de exclusão de conta que leem `Review.picture` | `backend/users/tests.py:5639`, `:5646`, `:5669` | REV-26: a review do fixture ganha 2 `ReviewPicture`, e as duas chaves somem depois do commit | T8 |

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas:
> - `.github/workflows/hairmatch-backend-test.yml`: `coverage run manage.py test`, sem limite mínimo.
> - `backend/review/tests.py` (`ReviewsTestCase`, `CreateReviewTest`, `CustomerRatingRaceTest` em `TransactionTestCase`), `backend/users/tests.py` (exclusão de conta com `captureOnCommitCallbacks`), `backend/agenda/tests.py` (`assertNumQueries`), `backend/hairmatch/test_routes.py`.
> - `frontend-mobile`: sem testes, por decisão herdada do #104 e do #120.
>
> Strong defaults aplicados nas camadas de backend.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: storage (`hairmatch/storage.py`) | integration | `delete_stored_files`: apaga cada nome, pula vazio, loga e segue quando um falha (REV-27) | `backend/hairmatch/tests.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput hairmatch'` |
| Backend: modelo `ReviewPicture` e migrações | integration | Chave `reviews/<review_id>/<32 hex>.webp`, conteúdo WebP, `CASCADE` e ordem por id (REV-02, REV-33) | `backend/review/tests.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput review'` |
| Backend: domínio (`review/pictures.py`, `review/customer_ratings.py`) | integration | Todos os ramos: cada erro de `picture_errors` e a ordem deles; `saved_names` parcial; média com 2 casas e `null`; o lock (`FOR UPDATE` antes da escrita); outras notas intactas | `backend/review/tests.py` | idem (review) |
| Backend: views de `review` (rotas novas e alteradas) | integration | Cada rota: happy path, cada status de erro do spec (400/401/403/404/405), "nada criado ou removido" e "storage vazio" onde o spec exige, e a ordem de validação (REV-45). Corrida do limite em `TransactionTestCase` (REV-15) | `backend/review/tests.py` | idem (review) |
| Backend: `reserve` (leitura) | integration | `pictures` em RT-43, RT-45 e RT-46. Queries constantes em RT-46 com 1 e 3 avaliações (REV-30, REV-32) | `backend/reserve/tests.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput reserve'` |
| Backend: `users` (exclusão de conta) | integration | As chaves das fotos de avaliações escritas e recebidas somem depois do commit. Rollback não apaga nada (REV-26, REV-28) | `backend/users/tests.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput users'` |
| Backend: agenda | integration | `customer_rating.id` presente, e `null` sem nota (REV-55) | `backend/agenda/tests.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput agenda'` |
| Backend: rotas (`hairmatch/test_routes.py`) | unit | Route Table igual ao URLconf com RT-90 a RT-93 (REV-56) | `backend/hairmatch/test_routes.py` | idem (hairmatch) |
| App (`frontend-mobile`) | none | Nenhum erro novo de `npx tsc --noEmit` e de `npx eslint` nos arquivos tocados, mais o roteiro de UAT da T25 | - | App |
| Documentação (`.specs/`) | none | Revisão | - | - |

## Gate Check Commands

> **Baseline de testes do backend** em `2948100`: a suíte roda **835** testes OK. `git grep -c "def test_"` conta 837:
> - `users` 423, `review` 81, `hairmatch` 101, `reserve` 49, `agenda` 46;
> - `availability` 55, `service` 40, `chatbot` 23, `preferences` 19.
>
> Nenhuma tarefa reduz esses números.

> **Baseline do app:** `npx tsc --noEmit` dá 7 erros em `2948100`. Todos vêm de `.expo/types/router.d.ts`, que está desatualizado e é ignorado pelo git (rotas `agenda/create` e `customer/ratings`). Antes da T16, regenerar os typed routes com o gerador do Expo, como fez a #113. Se ainda sobrar erro, a saída vira a baseline, e o gate passa quando nenhuma tarefa acrescenta erro novo.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas com testes de um app só | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput <app>'` |
| Full | Tarefas com migração ou URLconf, e o fim de cada fase de backend | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput && coverage report -m'` |
| App | Tarefas do `frontend-mobile` | `cd frontend-mobile && npx tsc --noEmit && npx eslint <arquivos tocados>` |
| Build | Fim da feature | Full + App |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend, base das fotos (expand)

```
T1 → T3
T2 → T3
T2 → T4 → T5
```

### Phase 2: Backend, escrita das fotos (contract)

```
T6 → T8
T7 → T8
T9 → T10
```

### Phase 3: Backend, nota do cabeleireiro e decisões

```
T11 → T12 → T13 → T15
T11 → T13
T14
```

### Phase 4: App, cliente

```
T16 → T17 → T18
T16 → T19
```

### Phase 5: App, cabeleireiro e verificação ponta a ponta

```
T20 → T21 → T22 → T25
T20 → T23 → T24 → T25
```

---

## Task Breakdown

### Phase 1: Backend, base das fotos (tarefas)

#### T1: `delete_stored_files` vai para `hairmatch/storage.py`

**What**:
- Mover `_delete_stored_files` de `backend/users/views.py:255` para `backend/hairmatch/storage.py` como `delete_stored_files(names)`, com o mesmo log (`logger.exception('Could not delete %s from the media storage', name)`), e pular nomes vazios.
- `users/views.py` passa a importar a função nova, e o nome antigo deixa de existir.
**Where**: `backend/hairmatch/storage.py`
**Depends on**: None
**Reuses**: o corpo de `_delete_stored_files`
**Requirement**: REV-27

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Antes de mudar qualquer coisa, a suíte passa com 835 testes (baseline).
- [x] Teste: com dois nomes gravados no `InMemoryStorage`, os dois somem. Um nome vazio é ignorado sem erro.
- [x] Teste: com `default_storage.delete` levantando no primeiro nome, o segundo ainda é apagado, e `assertLogs` captura o `ERROR` com traceback (REV-27).
- [x] Os testes de exclusão de conta e de foto de perfil de `users` passam sem mudança.
- [x] Gate Quick (`hairmatch` e `users`) passa. Contagem: `hairmatch` ≥ 101 + 2.

**Tests**: integration
**Gate**: quick

**Commit**: `refactor(storage): share the stored file deletion`

---

#### T2: Modelo `ReviewPicture`

**What**: Criar `review_picture_path` e `ReviewPicture` do design (FK `CASCADE` com `related_name='pictures'`, `WebPImageField`, `created_at`, `ordering = ['id']`) e a migração `review/0005_reviewpicture`. `Review.picture` continua existindo nesta task.
**Where**: `backend/review/models.py`
**Depends on**: None
**Reuses**: `user_profile_picture_path` (`backend/users/models.py:10`), `WebPImageField`
**Requirement**: REV-02, REV-33

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: `ReviewPicture.objects.create(review=r, picture=make_upload('Foto.PNG', fmt='PNG'))` grava a chave que casa com `^reviews/<r.id>/[0-9a-f]{32}\.webp$`, e o conteúdo abre como `WEBP` (REV-02).
- [x] Teste: duas fotos com o mesmo nome de arquivo na mesma review têm chaves diferentes.
- [x] Teste: `review.pictures.all()` vem por id crescente. Apagar a review apaga as linhas (REV-33).
- [x] Gate Full passa, com `makemigrations --check` limpo. Contagem: `review` ≥ 81 + 3.

**Tests**: integration
**Gate**: full

**Commit**: `feat(review): add the review pictures table`

---

#### T3: Domínio das fotos (`review/pictures.py`)

**What**: Criar `MAX_REVIEW_PICTURES`, `REVIEW_PICTURE_MAX_SIZE`, `INVALID_REVIEW_PICTURE_DETAIL`, `picture_errors(files, existing=0, required=False)`, `add_review_pictures(review, files, saved_names)` e `picture_names(queryset)`, como no design.
**Where**: `backend/review/pictures.py`
**Depends on**: T1, T2
**Reuses**: `body_error`, `ReviewPicture`
**Requirement**: REV-04, REV-05, REV-11, REV-12, REV-13

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: `picture_errors([], required=True)` dá um item `#/pictures` "This field is required.". `picture_errors([])` dá `[]`.
- [x] Teste: 6 arquivos, e também 2 arquivos com `existing=4`, dão um item `#/pictures` "A review can have at most 5 pictures.". 5 arquivos com `existing=0` dão `[]`.
- [x] Teste: um arquivo com `size = 5 * 1024 * 1024 + 1` dá "Each picture must have at most 5 MB.", e um com exatamente 5 MB passa. Um mock prova que nenhum arquivo é aberto.
- [x] Teste: quando cabem dois erros, sai um item só, na ordem obrigatório → limite → tamanho.
- [x] Teste: `add_review_pictures` com [válida, válida, inválida] levanta `InvalidImage`, e `saved_names` tem as 2 chaves já gravadas.
- [x] Teste: `picture_names` devolve os nomes das fotos do queryset.
- [x] Gate Quick (`review`) passa. Contagem: `review` ≥ 84 + 6.

**Tests**: integration
**Gate**: quick

**Commit**: `feat(review): validate and store review pictures`

---

#### T4: Serializers com `pictures` e prefetch na lista do cabeleireiro

**What**:
- Criar `ReviewPictureSerializer` (`id`, `url`).
- Acrescentar `pictures` (many, read_only) a `ReviewSerializer` e `ReviewLiteSerializer`.
- Em `ListReview` (`backend/review/views.py:120`), usar `.select_related('customer__user').prefetch_related('pictures')`.
**Where**: `backend/review/serializers.py`
**Depends on**: T2
**Reuses**: `CustomerNameSerializer`
**Requirement**: REV-30, REV-31, REV-32

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: `GET /api/hairdressers/{id}/reviews` com uma review de 2 fotos traz `pictures` com 2 itens `{id, url}` por id crescente, e `url == default_storage.url(nome)` (REV-30, REV-31).
- [x] Teste: uma review sem fotos traz `pictures: []`.
- [x] Teste: `assertNumQueries` mede o mesmo número com 1 e com 3 reviews com fotos (REV-32).
- [x] Gate Quick (`review`) passa. Contagem: `review` ≥ 90 + 3.

**Tests**: integration
**Gate**: quick

**Commit**: `feat(review): list the pictures of each review`

---

#### T5: Reservas devolvem as fotos da avaliação sem N+1

**What**: Em `ReserveById` (RT-43) e `ListReserve` (RT-45 e RT-46), usar `.select_related('service__hairdresser__user', 'review').prefetch_related('review__pictures')`.
**Where**: `backend/reserve/views.py`
**Depends on**: T4
**Reuses**: `ReviewLiteSerializer` com `pictures` (T4)
**Requirement**: REV-30, REV-32

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: `GET /api/reservations/{id}` de uma reserva avaliada com 2 fotos traz `review.pictures` com 2 itens (REV-30). O mesmo vale para `GET /api/reservations` e para `GET /api/customers/{id}/reservations`.
- [x] Teste: `GET /api/customers/{id}/reservations` mede o mesmo número de queries com 1 e com 3 reservas avaliadas com fotos (REV-32).
- [x] Gate Full passa. Contagem: `reserve` ≥ 49 + 3.

**Tests**: integration
**Gate**: full

**Commit**: `perf(reserve): prefetch the review pictures of the reservations`

---

### Phase 2: Backend, escrita das fotos (tarefas)

#### T6: `POST /api/reviews` aceita até 5 fotos em `pictures`

**What**:
- `CreateReview` (`backend/review/views.py:57`) lê `request.FILES.getlist('pictures')` e ignora `picture`.
- Junta `picture_errors(files)` aos erros de campo e cria a review e as fotos com o padrão de limpeza do design (`saved_names` e `delete_stored_files` na hora).
- `Review.objects.create` não recebe mais `picture`.
- Reescreve WEBP-03, WEBP-12 e WEBP-13 (ver a tabela do topo).
**Where**: `backend/review/views.py`
**Depends on**: T3, T4
**Reuses**: `pictures.py` (T3), `delete_stored_files` (T1)
**Requirement**: REV-01, REV-02, REV-03, REV-04, REV-05, REV-06, REV-07, REV-08

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: 3 PNGs em `pictures` dão 201 e 3 `ReviewPicture` na ordem de envio, com chaves em `reviews/<id>/` e conteúdo WebP (REV-01, REV-02). É a reescrita do WEBP-03.
- [x] Teste: sem `pictures`, dá 201 e a review sem fotos (REV-03).
- [x] Teste: 6 arquivos dão 400 `#/pictures`, sem review e com o storage sem chave nova (REV-04).
- [x] Teste: um arquivo acima de 5 MB dá 400 `#/pictures`, sem review, e um mock de `to_webp` prova que nada foi convertido (REV-05).
- [x] Teste: [PNG válido, PNG válido, arquivo que não é imagem] dá 400 `invalid-image` "The review picture is not a valid image.", sem review, com a reserva sem avaliação e sem nenhuma chave em `reviews/` (REV-06). É a reescrita do WEBP-12, e a do WEBP-13 (bomba de pixels) vem com `pictures`.
- [x] Teste: uma falha inesperada depois do upload (por exemplo `reserve.save` levantando) deixa o storage sem chave e propaga a exceção (REV-06, REV-28).
- [x] Teste: `rating` inválido mais 6 fotos dá um 400 com os dois ponteiros (REV-07).
- [x] Teste: um arquivo em `picture` dá 201 sem foto (REV-08).
- [x] Gate Quick (`review`) passa. Contagem: `review` ≥ 93 + 5 (os 3 reescritos continuam contando).

**Tests**: integration
**Gate**: quick

**Commit**: `feat(review): accept up to five pictures when reviewing`

---

#### T7: Apagar a avaliação apaga as fotos do storage

**What**: Em `RemoveReview` (`backend/review/views.py:150`), coletar `picture_names(review.pictures.all())` dentro do `atomic`, antes do `delete`, e registrar `on_commit(lambda: delete_stored_files(names))`.
**Where**: `backend/review/views.py`
**Depends on**: T3
**Reuses**: `picture_names` (T3), `delete_stored_files` (T1)
**Requirement**: REV-25, REV-28

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: uma review com 2 fotos, apagada dentro de `captureOnCommitCallbacks(execute=True)`, dá 204, remove as linhas e apaga as 2 chaves (REV-25).
- [x] Teste: sem executar os callbacks (rollback simulado), as chaves continuam no storage (REV-28).
- [x] Gate Quick (`review`) passa. Contagem: `review` ≥ 98 + 2.

**Tests**: integration
**Gate**: quick

**Commit**: `fix(review): delete the stored pictures with the review`

---

#### T8: A exclusão de conta lê `ReviewPicture`, e `Review.picture` sai

**What**:
- Em `_delete_account_rows` (`backend/users/views.py:229`), trocar o `values_list('picture')` de `Review` por `picture_names(ReviewPicture.objects.filter(Q(review__customer__user=user) | Q(review__hairdresser__user=user)))`.
- Remover `Review.picture`, com a migração `review/0006_remove_review_picture`.
- Reescrever os testes que ainda leem a coluna (ver a tabela do topo).
**Where**: `backend/users/views.py`
**Depends on**: T6, T7
**Reuses**: `picture_names` (T3)
**Requirement**: REV-20, REV-26, REV-28, REV-30

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: as exclusões de conta do cabeleireiro e do cliente apagam, depois do commit, as 2 chaves das fotos da review do fixture (REV-26). É a reescrita de `users/tests.py:5646` e `:5669`.
- [x] O teste da queda do Cognito que mantém as linhas e as fotos continua passando, agora também com as chaves de `ReviewPicture` (REV-28).
- [x] Teste: `PUT /api/reviews/{id}` com `picture` no corpo não cria nem remove fotos (REV-20). É a reescrita de `review/tests.py:452`.
- [x] Teste: o detalhe da reserva e a lista do cabeleireiro não trazem a chave `picture` na review (REV-30).
- [x] `git grep -nE "review\.picture\b|Review\.objects\.create\([^)]*picture=|\.get\(\)\.picture" -- backend` não acha nenhum leitor antigo. A prova principal é o gate Full: um leitor que sobrar levanta `FieldError` depois da remoção da coluna.
- [x] Gate Full passa, com `makemigrations --check` limpo. Contagem: `users` ≥ 423, `review` ≥ 100 + 1.

**Tests**: integration
**Gate**: full

**Commit**: `refactor(review): drop the single review picture column`

---

#### T9: `POST /api/reviews/{id}/pictures` (RT-90)

**What**:
- Criar `ReviewPictureCollection` e a rota `reviews/<int:id>/pictures` (`name='review_pictures'`), como no design: tamanho e obrigatório antes do lookup; review travada; contagem dentro do lock; padrão de limpeza; 201 com a lista completa.
- Acrescentar RT-90 à Route Table do `api-restful-routes/spec.md` e a `ROUTE_TABLE`.
**Where**: `backend/review/views.py`
**Depends on**: T3, T4
**Reuses**: `pictures.py` (T3), `ReviewPictureSerializer` (T4), `authenticated_customer`
**Requirement**: REV-10, REV-11, REV-12, REV-13, REV-14, REV-15, REV-17, REV-19, REV-56

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: numa review com 1 foto, enviar 2 dá 201 com `data` de 3 itens por id crescente (REV-10).
- [x] Teste: `pictures` ausente dá 400 `#/pictures` (REV-11). Com 4 fotos, enviar 2 dá 400 e mantém 4 (REV-12). Um arquivo acima de 5 MB dá 400 sem conversão (REV-13).
- [x] Teste: [válida, inválida] dá 400 `invalid-image`, sem linha nova e sem chave nova no storage (REV-14).
- [x] Teste (`TransactionTestCase`): duas threads com 3 fotos cada numa review sem fotos terminam com uma 201 e uma 400, e a review fica com 3 fotos (REV-15). Um teste com `CaptureQueriesContext` prova `FOR UPDATE` antes do `COUNT`.
- [x] Teste: uma review de outro cliente ou inexistente dá 404 `not-found`, sem alteração (REV-17).
- [x] Teste: sem sessão dá 401 `invalid-session`, e um cabeleireiro recebe 403 `customer-required` (REV-19).
- [x] `hairmatch.test_routes` passa com RT-90 (REV-56).
- [x] Gate Full passa. Contagem: `review` ≥ 101 + 7.

**Tests**: integration
**Gate**: full

**Commit**: `feat(review): add pictures to an existing review`

---

#### T10: `DELETE /api/reviews/{id}/pictures/{picture_id}` (RT-91)

**What**:
- Criar `ReviewPictureDetail` e a rota `reviews/<int:id>/pictures/<int:picture_id>` (`name='review_picture_detail'`), como no design: review do cliente ou 404; foto da review ou 404; `atomic` com `on_commit(delete_stored_files)`; 204.
- Acrescentar RT-91 à Route Table e a `ROUTE_TABLE`.
**Where**: `backend/review/views.py`
**Depends on**: T9
**Reuses**: `delete_stored_files` (T1), `authenticated_customer`
**Requirement**: REV-16, REV-17, REV-18, REV-19, REV-28, REV-56

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: remover uma de 2 fotos dá 204, deixa 1 linha e, depois do commit, apaga só a chave dela (REV-16).
- [x] Teste: sem executar os callbacks, a chave continua no storage (REV-28).
- [x] Teste: uma review de outro cliente dá 404 e não remove nada (REV-17).
- [x] Teste: uma foto de outra review do mesmo cliente, ou um id inexistente, dá 404 e não remove nada (REV-18).
- [x] Teste: sem sessão dá 401, e um cabeleireiro recebe 403 `customer-required` (REV-19).
- [x] Teste: `GET` na rota dá 405, com `Allow` contendo `DELETE`.
- [x] `hairmatch.test_routes` passa com RT-91 (REV-56).
- [x] Gate Full passa. Contagem: `review` ≥ 108 + 6.

**Tests**: integration
**Gate**: full

**Commit**: `feat(review): remove a picture from a review`

---

### Phase 3: Backend, nota do cabeleireiro e decisões (tarefas)

#### T11: Editar e excluir a nota com a média recalculada

**What**:
- Extrair `_store_average(user, customer)` de `record_customer_rating`.
- Criar `update_customer_rating(customer_rating, rating, comment)` e `delete_customer_rating(customer_rating)`, cada uma em `atomic` com o `User` do cliente travado (`select_for_update`).
- Tirar "It is immutable once created" do docstring de `CustomerRating`.
**Where**: `backend/review/customer_ratings.py`
**Depends on**: None
**Reuses**: `record_customer_rating` (`backend/review/customer_ratings.py:27`)
**Requirement**: REV-50, REV-51, REV-53

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste: com notas 5 e 3 (média 4.0), `update_customer_rating(3 → 4)` grava 4.5 em `User.rating`, e a nota 5 fica igual (REV-50, REV-53).
- [x] Teste: com 5, 4 e 4, apagar a 5 grava 4.0. Com 5 e 4 e 4, editar a 5 para 3 grava 3.67 (2 casas).
- [x] Teste: apagar a única nota grava `User.rating = None` (REV-51).
- [x] Teste: `CaptureQueriesContext` mostra o `SELECT ... FOR UPDATE` do `User` antes do `UPDATE` e antes do `DELETE` da nota (REV-50).
- [x] Os testes de `RecordCustomerRatingTest` e `CustomerRatingRaceTest` continuam passando.
- [x] Gate Quick (`review`) passa. Contagem: `review` ≥ 114 + 4.

**Tests**: integration
**Gate**: quick

**Commit**: `feat(review): update and delete customer ratings with the average`

---

#### T12: `PUT /api/customer-ratings/{id}` (RT-92)

**What**:
- `_customer_rating_errors` ganha `require_reservation=True`.
- Criar `CustomerRatingDetail.put` e a rota `customer-ratings/<int:id>` (`name='customer_rating_detail'`), como no design: sessão de cabeleireiro; corpo validado antes do lookup; 404; autor ou 403; `comment` normalizado; 200 com `CustomerRatingCreatedSerializer`.
- Acrescentar RT-92 à Route Table e a `ROUTE_TABLE`.
**Where**: `backend/review/views.py`
**Depends on**: T11
**Reuses**: `_customer_rating_errors`, `json_object`, `authenticated_hairdresser`, `forbidden`, `update_customer_rating` (T11)
**Requirement**: REV-40, REV-41, REV-42, REV-43, REV-44, REV-45, REV-46, REV-47, REV-48, REV-50, REV-56

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Teste: o autor envia `{rating: 4, comment: "  Pontual  "}`, recebe 200 com `{data: {id, reservation, rating: 4, comment: "Pontual", created_at}}`, e `User.rating` é recalculado (REV-40, REV-41, REV-50).
- [ ] Teste: `comment` ausente, `null` e `"   "` gravam `null` (REV-41).
- [ ] Teste: `rating` ausente, 4.5, `"5"`, `true`, 0 e 6 dão 400 `#/rating` (REV-42). Um comentário com 501 caracteres depois do trim, ou numérico, dá 400 `#/comment` (REV-43). Os dois juntos dão dois itens.
- [ ] Teste: um corpo que é lista JSON dá 400 `malformed-request` (REV-44).
- [ ] Teste: corpo inválido com id inexistente dá 400, não 404. Corpo inválido em nota de outro autor dá 400, não 403 (REV-45).
- [ ] Teste: id inexistente dá 404 `not-found` (REV-46).
- [ ] Teste: outro cabeleireiro, e uma nota com `hairdresser = None`, dão 403 `forbidden`, sem mudar a nota nem `User.rating` (REV-47).
- [ ] Teste: sem sessão dá 401, e um cliente recebe 403 `hairdresser-required` (REV-48).
- [ ] `hairmatch.test_routes` passa com RT-92 (REV-56).
- [ ] Gate Full passa. Contagem: `review` ≥ 118 + 9.

**Tests**: integration
**Gate**: full

**Commit**: `feat(review): let the hairdresser edit a customer rating`

---

#### T13: `DELETE /api/customer-ratings/{id}` (RT-93)

**What**:
- Acrescentar `delete` a `CustomerRatingDetail`: sessão de cabeleireiro, 404, autor ou 403, `delete_customer_rating` e 204.
- Acrescentar RT-93 à Route Table e a `ROUTE_TABLE`.
**Where**: `backend/review/views.py`
**Depends on**: T11, T12
**Reuses**: `delete_customer_rating` (T11)
**Requirement**: REV-46, REV-47, REV-48, REV-49, REV-51, REV-52, REV-56

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Teste: o autor apaga e recebe 204. A nota some, e `User.rating` vira a média das restantes, ou `null` se era a única (REV-49, REV-51).
- [ ] Teste: depois do DELETE, `POST /api/customer-ratings` para a mesma reserva dá 201 (REV-52).
- [ ] Teste: id inexistente dá 404 (REV-46). Outro cabeleireiro, e uma nota sem autor, dão 403 e não apagam (REV-47).
- [ ] Teste: sem sessão dá 401, e um cliente recebe 403 `hairdresser-required` (REV-48).
- [ ] Teste: `GET /api/customer-ratings/{id}` dá 405, com `Allow` contendo `PUT` e `DELETE`.
- [ ] `hairmatch.test_routes` passa com RT-93 (REV-56).
- [ ] Gate Full passa. Contagem: `review` ≥ 127 + 6.

**Tests**: integration
**Gate**: full

**Commit**: `feat(review): let the hairdresser delete a customer rating`

---

#### T14: A agenda expõe o id da nota

**What**: Em `get_customer_rating` (`backend/agenda/serializers.py:47`), devolver `{'id', 'rating', 'comment'}`.
**Where**: `backend/agenda/serializers.py`
**Depends on**: None
**Reuses**: o `reserve_map` com `customer_rating` já prefetchado
**Requirement**: REV-55

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Teste: um item com nota traz `customer_rating == {id, rating, comment}` com o id da nota, e um item sem nota traz `null` (REV-55).
- [ ] O teste de queries constantes da agenda (CRT-38) continua passando.
- [ ] Gate Quick (`agenda`) passa. Contagem: `agenda` ≥ 46 + 1.

**Tests**: integration
**Gate**: quick

**Commit**: `feat(agenda): expose the customer rating id`

---

#### T15: AD-011 e AD-012 no `STATE.md`

**What**:
- Acrescentar o AD-011 como aplicação do AD-013 (fotos de avaliação em `ReviewPicture`, chave `reviews/<review_id>/<uuid>.webp`, até 5 por avaliação e 5 MB por arquivo, limpeza por `delete_stored_files`).
- Acrescentar o AD-012 (a média do AD-010 também é recalculada na edição e na exclusão de `CustomerRating`, com o mesmo lock).
- Atualizar o escopo do AD-003 (`ReviewPicture.picture` no lugar de `Review.picture`) e o status do AD-010 ("active, estendido pelo AD-012").
**Where**: `.specs/STATE.md`
**Depends on**: T8, T13
**Reuses**: o formato dos ADs existentes
**Requirement**: REV-02, REV-50

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] AD-011 e AD-012 com Decision, Reason, Trade-off, Scope, Date e Status.
- [ ] O AD-003 e o AD-010 apontam para os ADs novos.
- [ ] Gate Full passa (nenhum código muda).

**Tests**: none
**Gate**: full

**Commit**: `docs(specs): record the review pictures and rating edit decisions`

---

### Phase 4: App, cliente (tarefas)

#### T16: Tipos e serviço das avaliações

**What**:
- Criar `models/Review.types.ts` (`ReviewPicture`, `Review`) e trocar `review: any` por `Review | null` em `models/Reserve.types.ts`.
- Em `services/review.service.ts`: `createReview` passa a receber `{rating, comment, hairdresser, reserve, pictures: PickedImage[]}` e monta o `FormData` com `pictures` repetido; criar `updateReview`, `addReviewPictures` e `deleteReviewPicture`. Um `appendPicture` interno cuida do blob no web, como `account.service.ts`.
- Antes de mudar, regenerar os typed routes e registrar a baseline do `tsc`.
**Where**: `frontend-mobile/services/review.service.ts`
**Depends on**: T6, T9, T10
**Reuses**: `PickedImage` e o upload de `account.service.ts:21-46`
**Requirement**: REV-66, REV-67

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] As quatro funções têm a assinatura do design, e as de multipart mandam `Content-Type: multipart/form-data`.
- [ ] As chamadas existentes a `createReview` são ajustadas, ou ficam com o erro de tipo que a T17 resolve. A baseline do `tsc` registra qual.
- [ ] Gate App passa, sem erro novo além dos que a T17 remove.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): type the review pictures and their requests`

---

#### T17: `useReviewForm` com várias fotos e modo edição

**What**: Reescrever `hooks/customerHooks/useReviewForm.ts` com o estado e as funções do design:
- `existing`, `removedIds`, `queued` e `isEditing`;
- `pickPictures` (seleção múltipla, `selectionLimit` restante, `quality: 0.5`, sem `allowsEditing`, corte no web);
- `removeExisting` e `removeQueued`;
- `submit` com a guarda de duplo toque, a sequência PUT → DELETE → POST e a recuperação em erro.
**Where**: `frontend-mobile/hooks/customerHooks/useReviewForm.ts`
**Depends on**: T16
**Reuses**: `problemMessage`, `ErrorModal`, `getReserveById`
**Requirement**: REV-61, REV-62, REV-63, REV-65, REV-66, REV-67, REV-68, REV-69

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Numa reserva com review, o hook preenche `rating`, `comment` e `existing` (REV-61).
- [ ] `selectionLimit` é `5 − existing.length − queued.length`. A seleção que passa do limite é cortada, e o aviso "Você pode enviar até 5 fotos." aparece (REV-62, REV-63).
- [ ] A remoção só mexe no estado local (REV-65).
- [ ] Criar chama `createReview` uma vez (REV-66). Editar chama PUT, depois um DELETE por foto removida, depois um POST com as novas, pulando o que está vazio (REV-67).
- [ ] Em erro, o hook mostra o `problemMessage`, recarrega a reserva, refaz `existing` e mantém `queued`, `rating` e `comment`. As fotos marcadas para remoção que ainda existem no servidor continuam escondidas e na lista de remoção, para o próximo salvar (REV-68).
- [ ] O formulário só é limpo depois do sucesso, e um `useRef` barra o segundo toque (REV-69).
- [ ] Gate App passa.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): edit a review and its pictures`

---

#### T18: Tela de avaliação com galeria de fotos

**What**: Em `app/(app)/customer/review/[id].tsx`:
- título "Avaliar Atendimento" ou "Editar Avaliação";
- grade de miniaturas das fotos mantidas e das novas, cada uma com "x";
- botão de adicionar escondido quando não cabe mais nenhuma;
- "Enviando..." no botão;
- `ErrorModal` ligado ao hook.

Os estilos novos vão em `styles/customer/styles/ReviewStyles.ts`.
**Where**: `frontend-mobile/app/(app)/customer/review/[id].tsx`
**Depends on**: T17
**Reuses**: `StarRating` (`components/StarRating/StarRating.tsx`), `ErrorModal`
**Requirement**: REV-60, REV-61, REV-64, REV-65, REV-69

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O título muda conforme o modo (REV-60, REV-61).
- [ ] Cada miniatura tem "x", e o botão de adicionar some com 5 fotos (REV-64, REV-65).
- [ ] O `StarRating` local da tela é trocado pelo componente compartilhado.
- [ ] Gate App passa.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): show the review pictures as a gallery`

---

#### T19: Detalhe da reserva mostra as fotos e abre a edição

**What**:
- Em `app/(app)/customer/reserves/[id].tsx`, o item "Editar avaliação" do menu ganha `onPress`: fecha o menu e chama `handleEditReview(reserve.id)`, que `useReserveDetails` expõe (`router.push('/customer/review/{id}')`).
- A imagem única vira um `ScrollView` horizontal com `review.pictures`, ou o placeholder atual.
**Where**: `frontend-mobile/app/(app)/customer/reserves/[id].tsx`
**Depends on**: T16
**Reuses**: `handleReviewScreen` de `useReserveDetails.ts:65`
**Requirement**: REV-61, REV-70

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] "Editar avaliação" abre a tela de avaliação da reserva (REV-61).
- [ ] Uma review com 3 fotos mostra 3 imagens roláveis. Sem fotos, mostra o placeholder (REV-70).
- [ ] Nenhuma referência a `review.picture` sobra no app (`git grep -n "review?*\.picture\b" -- frontend-mobile`).
- [ ] Gate App passa.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): show every review picture in the reservation`

---

### Phase 5: App, cabeleireiro e verificação ponta a ponta (tarefas)

#### T20: Serviço e tipos para editar e excluir a nota

**What**:
- Criar `updateCustomerRating(id, {rating, comment})` e `deleteCustomerRating(id)` em `services/customer-rating.service.ts`.
- `models/Agenda.types.ts`: `customer_rating` e `customerRating` ganham `id`, e o mapeamento em `useAgenda` passa o `id` adiante.
**Where**: `frontend-mobile/services/customer-rating.service.ts`
**Depends on**: T12, T13, T14
**Reuses**: `createCustomerRating`
**Requirement**: REV-55, REV-78, REV-80

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] As duas funções chamam `PUT` e `DELETE /api/customer-ratings/{id}`.
- [ ] `AgendaEvent.customerRating` tem `id`.
- [ ] Gate App passa.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): add the customer rating edit requests`

---

#### T21: `useAgenda` edita e exclui a nota

**What**:
- `goToEditRating(event)` empurra `rate-customer/{reservationId}` com `{customerName, customerId, ratingId}`.
- `requestDeleteRating` e `confirmDeleteRating`: abrem a confirmação, chamam `deleteCustomerRating`, fecham o modal e buscam a agenda de novo.
- `errorModal` com `problemMessage` em falha.
**Where**: `frontend-mobile/hooks/hairdresserHooks/useAgenda.ts`
**Depends on**: T20
**Reuses**: `goToRateCustomer` e o fetch do `useFocusEffect`
**Requirement**: REV-76, REV-80, REV-81

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Os params da edição são `customerName`, `customerId` e `ratingId` (REV-76).
- [ ] Depois do DELETE, a agenda é buscada de novo, e o evento fica sem `customerRating` (REV-80).
- [ ] Um DELETE com falha mostra o `problemMessage` (REV-81).
- [ ] Gate App passa.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): edit and delete a customer rating from the agenda`

---

#### T22: Modal da agenda com "Editar avaliação" e "Excluir avaliação"

**What**: Em `app/(app)/hairdresser/agenda/index.tsx`, com `customerRating`:
- mostrar "Sua avaliação: N★" e os botões "Editar avaliação" e "Excluir avaliação";
- usar o `ConfirmationModal` "Excluir avaliação?" e o `ErrorModal` do hook.
**Where**: `frontend-mobile/app/(app)/hairdresser/agenda/index.tsx`
**Depends on**: T21
**Reuses**: `ConfirmationModal`, `ErrorModal`
**Requirement**: REV-75, REV-80, REV-81

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Os dois botões aparecem só quando há nota. "Avaliar cliente" continua aparecendo só pelo `canRate` (REV-75).
- [ ] "Excluir avaliação" abre a confirmação antes do DELETE (REV-80).
- [ ] Gate App passa.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): add the rating actions to the agenda modal`

---

#### T23: `useRateCustomer` em modo edição

**What**:
- Com `ratingId`, o hook entra em modo edição: busca `getCustomerRatings(customerId)`, acha o item pelo `id` e preenche `rating` e `comment`. Se não achar, ou se a busca falhar, mostra "Não foi possível carregar a avaliação." e vai para a agenda ao fechar.
- `submit` chama `updateCustomerRating` (comentário vazio vira `null`) e volta para a agenda.
- Expõe `isEditing`.
**Where**: `frontend-mobile/hooks/hairdresserHooks/useRateCustomer.ts`
**Depends on**: T20
**Reuses**: `getCustomerRatings`, o reset por `formReservationId` já existente
**Requirement**: REV-76, REV-77, REV-78, REV-81

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Com `ratingId` válido, o formulário abre preenchido (REV-76).
- [ ] Com `ratingId` fora da lista, ou com a busca falhando, aparece o erro, e fechar leva para a agenda (REV-77).
- [ ] Salvar chama o PUT e volta para a agenda (REV-78). Uma falha mantém o formulário e mostra o `problemMessage` (REV-81).
- [ ] O reset ao trocar de reserva também zera o modo edição.
- [ ] Gate App passa.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): edit a customer rating`

---

#### T24: Textos da tela de nota do cliente

**What**: Em `app/(app)/hairdresser/rate-customer/[reservationId].tsx`:
- título "Editar Avaliação" quando `isEditing`;
- confirmação "Salvar as alterações da avaliação?" na edição e "Você poderá editar ou excluir a avaliação depois." na criação;
- botão "Salvar alterações" na edição.
**Where**: `frontend-mobile/app/(app)/hairdresser/rate-customer/[reservationId].tsx`
**Depends on**: T23
**Reuses**: `ConfirmationModal`
**Requirement**: REV-76, REV-78, REV-79

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Título, botão e confirmação mudam conforme o modo (REV-76, REV-78).
- [ ] O texto "não pode ser alterada" sumiu do app (REV-79).
- [ ] Gate App passa.

**Tests**: none
**Gate**: app

**Commit**: `feat(app): word the rating screen for editing`

---

#### T25: UAT no web e no Android

**What**: Roteiro manual com o compose de dev (LocalStack, MiniStack) e o Metro em 8081, com a aba visível (memória `expo-web-smoke-needs-visible-tab`):
1. O cliente cria uma avaliação com 3 fotos e confere as 3 chaves em `reviews/<id>/` no LocalStack.
2. O cliente edita: troca a nota, remove 1 foto e adiciona 2. Confere 4 fotos no detalhe e 4 chaves no bucket.
3. Com 5 fotos, o botão de adicionar some. No web, escolher 3 numa avaliação com 4 mostra o aviso e fica com 1.
4. O cliente exclui a avaliação, e as chaves somem do bucket.
5. O cabeleireiro edita uma nota de 5 para 3 pela agenda e confere "Sua avaliação: 3★" e a média nova no perfil do cliente.
6. O cabeleireiro exclui a nota. "Avaliar cliente" volta, e a média do cliente fica "Sem avaliações" quando era a única.
7. Android: os passos 1, 2 e 5.
**Where**: `.specs/features/review-editing/spec.md`
**Depends on**: T18, T19, T22, T24
**Reuses**: memória `expo-web-smoke-needs-visible-tab`
**Requirement**: REV-60, REV-61, REV-62, REV-63, REV-64, REV-65, REV-66, REV-67, REV-68, REV-69, REV-70, REV-75, REV-76, REV-77, REV-78, REV-79, REV-80, REV-81

**Tools**:
- MCP: `claude-in-chrome` (web)
- Skill: `run`

**Done when**:
- [ ] Os 7 passos passam, ou cada falha vira uma task de correção.
- [ ] Os critérios de app ficam como Verified no spec.

**Tests**: none
**Gate**: build

**Commit**: `docs(specs): record the review editing UAT`

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1 | 1 função movida | ✅ Granular |
| T2 | 1 modelo + migração | ✅ Granular |
| T3 | 1 módulo de domínio (3 funções coesas) | ⚠️ OK, coeso |
| T4 | 1 serializer + prefetch da view que o usa | ⚠️ OK, coeso |
| T5 | prefetch em 2 views do mesmo arquivo | ✅ Granular |
| T6 | 1 endpoint alterado | ✅ Granular |
| T7 | 1 endpoint alterado | ✅ Granular |
| T8 | 1 leitor migrado + remoção da coluna (o contract do expand) | ⚠️ OK, precisa ser atômico |
| T9 | 1 endpoint | ✅ Granular |
| T10 | 1 endpoint | ✅ Granular |
| T11 | 2 funções de domínio + 1 helper | ⚠️ OK, coeso |
| T12 | 1 endpoint | ✅ Granular |
| T13 | 1 endpoint | ✅ Granular |
| T14 | 1 método de serializer | ✅ Granular |
| T15 | 1 arquivo de doc | ✅ Granular |
| T16 | 1 serviço + tipos | ⚠️ OK, coeso |
| T17 | 1 hook | ✅ Granular |
| T18 | 1 tela | ✅ Granular |
| T19 | 1 tela | ✅ Granular |
| T20 | 1 serviço + tipo | ✅ Granular |
| T21 | 1 hook | ✅ Granular |
| T22 | 1 tela | ✅ Granular |
| T23 | 1 hook | ✅ Granular |
| T24 | 1 tela | ✅ Granular |
| T25 | UAT | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | - | ✅ Match |
| T2 | None | - | ✅ Match |
| T3 | T1, T2 | T1 → T3, T2 → T3 | ✅ Match |
| T4 | T2 | T2 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T3, T4 (Phase 1) | - (cross-phase) | ✅ Match |
| T7 | T3 (Phase 1) | - (cross-phase) | ✅ Match |
| T8 | T6, T7 | T6 → T8, T7 → T8 | ✅ Match |
| T9 | T3, T4 (Phase 1) | - (cross-phase) | ✅ Match |
| T10 | T9 | T9 → T10 | ✅ Match |
| T11 | None | - | ✅ Match |
| T12 | T11 | T11 → T12 | ✅ Match |
| T13 | T11, T12 | T11 → T13, T12 → T13 | ✅ Match |
| T14 | None | - | ✅ Match |
| T15 | T8 (Phase 2), T13 | T13 → T15 | ✅ Match |
| T16 | T6, T9, T10 (Phase 2) | - (cross-phase) | ✅ Match |
| T17 | T16 | T16 → T17 | ✅ Match |
| T18 | T17 | T17 → T18 | ✅ Match |
| T19 | T16 | T16 → T19 | ✅ Match |
| T20 | T12, T13, T14 (Phase 3) | - (cross-phase) | ✅ Match |
| T21 | T20 | T20 → T21 | ✅ Match |
| T22 | T21 | T21 → T22 | ✅ Match |
| T23 | T20 | T20 → T23 | ✅ Match |
| T24 | T23 | T23 → T24 | ✅ Match |
| T25 | T18, T19 (Phase 4), T22, T24 | T22 → T25, T24 → T25 | ✅ Match |

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Backend: storage | integration | integration | ✅ OK |
| T2 | Backend: modelo e migrações | integration | integration | ✅ OK |
| T3 | Backend: domínio | integration | integration | ✅ OK |
| T4 | Backend: views de review (serializer + lista) | integration | integration | ✅ OK |
| T5 | Backend: reserve | integration | integration | ✅ OK |
| T6 | Backend: views de review | integration | integration | ✅ OK |
| T7 | Backend: views de review | integration | integration | ✅ OK |
| T8 | Backend: users + migração | integration | integration | ✅ OK |
| T9 | Backend: views de review + rotas | integration | integration | ✅ OK |
| T10 | Backend: views de review + rotas | integration | integration | ✅ OK |
| T11 | Backend: domínio | integration | integration | ✅ OK |
| T12 | Backend: views de review + rotas | integration | integration | ✅ OK |
| T13 | Backend: views de review + rotas | integration | integration | ✅ OK |
| T14 | Backend: agenda | integration | integration | ✅ OK |
| T15 | Documentação | none | none | ✅ OK |
| T16 a T24 | App | none | none | ✅ OK |
| T25 | App (UAT) | none | none | ✅ OK |
