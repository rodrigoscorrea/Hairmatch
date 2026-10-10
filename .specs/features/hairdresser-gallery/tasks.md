# Galeria de fotos do cabeleireiro Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/hairdresser-gallery/spec.md`
**Context**: `.specs/features/hairdresser-gallery/context.md`
**Design**: `.specs/features/hairdresser-gallery/design.md`
**Status**: Draft (aguardando aprovação para Execute)
**Branch**: a criar a partir de `develop` no início do Execute, com o nome `118-galeria-de-fotos-do-cabeleireiro`.

**Pré-requisitos do Execute:**
- Os testes do backend rodam dentro do container `hairmatch_backend` (memória `backend-tests-run-in-docker`). Se o `hairmatch_db` estiver parado, rodar `docker start hairmatch_db`.
- Os testes usam o `InMemoryStorage` e o fake de Cognito. Não precisam do LocalStack nem do MiniStack.
- O UAT (T18) precisa do `docker compose up` completo e do app no web, com a aba visível (memória `expo-web-smoke-needs-visible-tab`), e no Android.
- Há uma migração nova (`users/0014`). Não há env var nova.
- As mudanças de spec desta feature já estão no working tree e entram no primeiro commit:
  - as linhas RT-94 a RT-96 no `api-restful-routes/spec.md`;
  - o `gallery-full` no `api-problem-details/spec.md`;
  - o AD-013 no `STATE.md`.

  O AD-007 exige a tabela antes do código.

**Ordem que mantém a suíte verde a cada commit:**
1. A Phase 1 (backend) vem antes do app, que depende das rotas.
2. A Phase 2 (seed) depende do modelo.
3. A Phase 3 cria a base do app sem mudar nenhuma tela.
4. A Phase 4 liga as telas.
5. A Phase 5 é o UAT.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas:
> - `.github/workflows/hairmatch-backend-test.yml`: `coverage run manage.py test`, sem limite mínimo.
> - `backend/users/tests.py`: os testes da `ProfilePictureView`, da exclusão de conta (`_delete_account`) e do seed (`test_restores_missing_seeded_pictures_on_the_same_key`, `:3136`).
> - `backend/review/tests.py:978` (`CustomerRatingRaceTest`, corrida com `TransactionTestCase` e `threading.Barrier`).
> - `backend/hairmatch/test_routes.py` e `backend/hairmatch/test_problems.py`.
> - `frontend-mobile`: sem testes, por decisão herdada do #106, do #139, do #141 e do #120. O gate é `npx tsc --noEmit` mais o UAT.
>
> Strong defaults aplicados nas camadas de backend.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: modelo `GalleryPhoto` e views da galeria | integration | Cada critério de backend do spec (GAL-01 a GAL-05, GAL-09 a GAL-19, GAL-31 a GAL-34, GAL-39, GAL-40, GAL-43, GAL-47 e GAL-48): o happy path, cada status de erro e "nenhuma linha e nenhum arquivo" onde o spec exige. Para o storage: o arquivo presente depois do `POST` e ausente depois do commit do `DELETE` (`captureOnCommitCallbacks(execute=True)`). | `backend/users/tests.py` (`APIClient`) | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput users'` |
| Backend: seed (`populate_hairdressers`) | integration | GAL-44 e GAL-45: as fotos criadas pelo modelo e a chave restaurada com WebP. | `backend/users/tests.py` | idem |
| Backend: contratos (`test_routes.py` e `test_problems.py`) | unit | RT-94 a RT-96 em `ROUTE_TABLE`, e `gallery-full` no `CATALOG` com 409. | `backend/hairmatch/test_*.py` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput hairmatch'` |
| App (`frontend-mobile`): tipos, serviço, hooks, componentes e telas | none | `npx tsc --noEmit` sem erro novo, mais o roteiro de UAT do T18. | - | App |
| Specs (`.specs/`) | none | `validate_spec.py` com exit 0. | - | - |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas com testes só de `users` ou só de `hairmatch` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput users'` (ou `hairmatch`) |
| Full | Tarefas que tocam o modelo, o URLconf ou o fim da Phase 1 | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput && coverage report -m'` |
| App | Tarefas do `frontend-mobile` | `cd frontend-mobile && npx tsc --noEmit` |
| Build | T18 (fim da feature) | Full + App + o roteiro de UAT do T18 |

> **Baseline de testes do backend:** `git grep -c "def test_"` em `2948100` conta **837**:
> - `users` 423 e `hairmatch` 101 (`tests.py` 44, `test_problems.py` 48 e `test_routes.py` 9);
> - `review` 81, `availability` 55, `reserve` 49, `agenda` 46, `service` 40, `chatbot` 23 e `preferences` 19.
>
> Nenhuma tarefa reduz esses números. Antes do T1, rodar o gate Full para confirmar a baseline.

> **Gate do app:** antes do T10, registrar a saída atual de `npx tsc --noEmit` como baseline. O gate passa quando nenhuma tarefa acrescenta um erro novo.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend: modelo, rotas e ciclo de vida

```
T1 → T4
T2 → T3 → T4 → T5
T2 → T6
T2 → T7
```

### Phase 2: Backend: seed

```
T8 → T9
```

### Phase 3: App: base

```
T10
T11 → T12 → T13
```

### Phase 4: App: telas

```
T14
T15 → T16 → T17
```

### Phase 5: UAT

```
T18
```

---

## Task Breakdown

### Phase 1: Backend: modelo, rotas e ciclo de vida

#### T1: Slug `gallery-full`

**What**: Acrescentar `'gallery-full': (409, 'Gallery is full')` ao `CATALOG`, depois de `service-not-finished`, e um teste em `test_problems.py` que monta a resposta com o slug e confere o status 409, o `type` e o `title`. A linha do catálogo no spec `api-problem-details` já está no working tree e entra neste commit.
**Where**: `backend/hairmatch/problems.py`
**Depends on**: None
**Reuses**: o teste de `service-not-finished` (`backend/hairmatch/test_problems.py:42`)
**Requirement**: GAL-42

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste novo em `test_problems.py`: `problem_response(..., 'gallery-full', ...)` responde 409 com `type` terminado em `/gallery-full` e `title` "Gallery is full".
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput hairmatch'`
- [x] Test count: `hairmatch` 101 → 102, sem remoção.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(api): add the gallery-full problem type`

---

#### T2: Modelo `GalleryPhoto`

**What**: Criar o modelo do design (FK com `CASCADE`, `WebPImageField(upload_to=gallery_photo_path)`, `created_at`, `ordering` e índice), `gallery_photo_path`, `GALLERY_MAX_PHOTOS = 30`, a migração `0014_galleryphoto` e o `GalleryPhotoSerializer`.
**Where**: `backend/users/models.py` (mais a migração gerada e `backend/users/serializers.py`)
**Depends on**: None
**Reuses**: `user_profile_picture_path` e `WebPImageField`
**Requirement**: GAL-05, GAL-10

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Classe nova `GalleryPhotoModelTest` com:
  - `image.save('foto da praia.png', <PNG 2000×1500>)` grava a chave que casa com `^hairdresser/gallery/<hairdresser_id>/[0-9a-f]{32}\.webp$`, sem `praia`;
  - o objeto no storage abre como WebP com o maior lado 1080;
  - a ordem padrão é `created_at` desc e `id` desc no empate (duas fotos com o mesmo `created_at` congelado);
  - apagar o `Hairdresser` apaga as linhas.
- [x] `makemigrations --check` limpo.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput'`
- [x] Test count: total sem remoção.

**Tests**: integration
**Gate**: full
**Commit**: `feat(users): add the hairdresser gallery photo model`

---

#### T3: `GET /api/hairdressers/{id}/gallery-photos`

**What**: Criar a `GalleryPhotoCollection` com o `get`, registrar a rota `hairdressers/<int:hairdresser_id>/gallery-photos` (`name='gallery_photos'`) e incluir RT-94 em `ROUTE_TABLE`, com o comentário de cabeçalho atualizado. A view e a rota entram juntas porque o RT-50 (`test_routes.py`) falha se a rota existir sem estar na tabela.
**Where**: `backend/users/views.py` (mais `backend/users/urls.py` e `backend/hairmatch/test_routes.py`)
**Depends on**: T2
**Reuses**: `ListAvailability.get` (`backend/availability/views.py:124`) e `problem_response`
**Requirement**: GAL-01, GAL-02, GAL-03, GAL-04, GAL-05, GAL-41

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Classe nova `GalleryPhotoListTest` com:
  - 3 fotos criadas em instantes diferentes: 200 com os 3 `id` em ordem decrescente de `created_at`, cada item só com `id`, `image` e `created_at`;
  - as fotos de outro cabeleireiro não aparecem;
  - sem fotos: `{"data": []}`;
  - o pk de um `Hairdresser` que não existe: 404 `not-found`;
  - sem cookie: 200;
  - `image` termina em `.webp` e não contém o nome original enviado.
- [x] `RouteTableTests` passa com RT-94.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput'`
- [x] Test count: total sem remoção.

**Tests**: integration
**Gate**: full
**Commit**: `feat(users): list a hairdresser's gallery photos`

---

#### T4: `POST /api/hairdressers/{id}/gallery-photos`

**What**: Acrescentar o `post` à `GalleryPhotoCollection` na ordem do design (sessão, posse, campo, tamanho, contagem e gravação pelo `WebPImageField`) e incluir RT-95 em `ROUTE_TABLE`.
- Renomear `PROFILE_PICTURE_MAX_SIZE` para `IMAGE_UPLOAD_MAX_SIZE` e usar a constante nas duas views.
- A contagem já recusa a 31ª foto com `gallery-full`. O lock entra no T5.
- Se o `INSERT` falhar depois do upload, a chave subida é apagada.

**Where**: `backend/users/views.py` (mais `backend/hairmatch/test_routes.py`)
**Depends on**: T1, T3
**Reuses**: `ProfilePictureView.put`, `authenticated_hairdresser`, `forbidden`, `validation_problem` e `body_error`
**Requirement**: GAL-09, GAL-10, GAL-11, GAL-12, GAL-13, GAL-14, GAL-16, GAL-17, GAL-18, GAL-19, GAL-41, GAL-43, GAL-48

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Classe nova `GalleryPhotoCreateTest` com:
  - PNG válido: 201 `{"data": {id, image, created_at}}`, uma linha e o objeto `.webp` no storage;
  - sem o campo `image` e com corpo JSON: 400 `validation-error` com `errors[0].pointer == "#/image"`, sem linha e sem arquivo;
  - arquivo de 5 MB + 1 byte: 400 `#/image`, sem linha e sem arquivo;
  - texto como imagem: 400 `invalid-image`, sem linha e sem arquivo;
  - com 30 fotos: 409 `gallery-full`, ainda 30 linhas e nenhum arquivo novo;
  - com 29 fotos: 201, e a seguinte dá 409;
  - sem cookie: 401 `invalid-session`; cliente: 403 `hairdresser-required`; `{id}` de outro cabeleireiro: 403 `forbidden`, sem linha;
  - o `save` do storage levantando exceção (`mock.patch`): 500 `internal-error`, sem linha;
  - o `INSERT` falhando depois do upload: o arquivo subido é apagado;
  - `PUT` na coleção: 405 com `Allow: GET, OPTIONS, POST`.
- [x] Os testes da `ProfilePictureView` continuam passando com `IMAGE_UPLOAD_MAX_SIZE`.
- [x] `RouteTableTests` passa com RT-95.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput'`
- [x] Test count: total sem remoção.

**Tests**: integration
**Gate**: full
**Commit**: `feat(users): add photos to the hairdresser gallery`

---

#### T5: Limite de 30 sob concorrência

**What**: Envolver a contagem e a gravação do `post` em `transaction.atomic()` com `Hairdresser.objects.select_for_update().get(pk=...)` antes da contagem, como o AD-010 faz.
**Where**: `backend/users/views.py`
**Depends on**: T4
**Reuses**: `record_customer_rating` (`backend/review/customer_ratings.py:33`) e `CustomerRatingRaceTest` (`backend/review/tests.py:978`)
**Requirement**: GAL-15

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Classe nova `GalleryPhotoRaceTest(TransactionTestCase)`: com 28 fotos, 4 threads fazem `POST` ao mesmo tempo (`threading.Barrier`). Exatamente 2 respondem 201 e 2 respondem 409 `gallery-full`, e a galeria termina com 30 linhas.
- [x] O teste falha com o `select_for_update` removido (conferido uma vez à mão e registrado no commit).
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput users'`
- [x] Test count: total sem remoção.

**Tests**: integration
**Gate**: quick
**Commit**: `fix(users): hold the gallery limit under concurrent uploads`

---

#### T6: `DELETE /api/hairdressers/{id}/gallery-photos/{photo_id}`

**What**: Criar a `GalleryPhotoDetail` com o `delete` (autenticação e posse, 404 para foto alheia ou inexistente, `delete` na transação, `_delete_stored_files` no `on_commit` e 204), registrar a rota `hairdressers/<int:hairdresser_id>/gallery-photos/<int:photo_id>` (`name='gallery_photo'`) e incluir RT-96 em `ROUTE_TABLE`.
**Where**: `backend/users/views.py` (mais `backend/users/urls.py` e `backend/hairmatch/test_routes.py`)
**Depends on**: T2
**Reuses**: `ProfilePictureView.delete` e `_delete_stored_files`
**Requirement**: GAL-31, GAL-32, GAL-33, GAL-34, GAL-41, GAL-43, GAL-47

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Classe nova `GalleryPhotoDeleteTest` com:
  - a foto própria: 204, a linha some, e o arquivo some só depois do commit;
  - uma foto de outro cabeleireiro sob o próprio `{id}`: 404, com a linha e o arquivo intactos;
  - um `photo_id` inexistente: 404; `photo_id` `abc`: 404;
  - sem cookie: 401; cliente: 403 `hairdresser-required`; `{id}` de outro: 403 `forbidden`, sem apagar;
  - o `delete` do storage levantando exceção: ainda 204, e o log (`assertLogs`) cita a chave;
  - `GET` no item: 405 com `Allow: DELETE, OPTIONS`.
- [x] `RouteTableTests` passa com RT-96.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput'`
- [x] Test count: total sem remoção.

**Tests**: integration
**Gate**: full
**Commit**: `feat(users): remove a photo from the hairdresser gallery`

---

#### T7: Galeria na exclusão da conta

**What**: Acrescentar as chaves de `GalleryPhoto` do usuário à lista `pictures` de `_delete_account_rows`, antes do `user.delete()`.
**Where**: `backend/users/views.py`
**Depends on**: T2
**Reuses**: o teste da exclusão de conta com foto de perfil e de avaliação
**Requirement**: GAL-39, GAL-40

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Testes novos na classe de exclusão de conta:
  - um cabeleireiro com 2 fotos exclui a conta: as linhas somem, e os 2 arquivos somem depois do commit;
  - com o fake de Cognito falhando (`fail_next`): as linhas e os arquivos ficam.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput'`
- [x] Test count: total sem remoção.

**Tests**: integration
**Gate**: full
**Commit**: `fix(users): delete the gallery files with the account`

---

### Phase 2: Backend: seed

#### T8: Fotos da galeria no seed

**What**: Mover os 5 `galery*.jpg` de `frontend-mobile/assets/hairdressers/gallery/` para `backend/users/management/commands/seed_assets/gallery/` (`git mv`, e a pasta do app some). Na criação de cada cabeleireiro, subir `random.randint(0, 6)` fotos por `GalleryPhoto.image.save`.
**Where**: `backend/users/management/commands/populate_hairdressers.py`
**Depends on**: None
**Reuses**: o upload de `profile_pic_name` do mesmo comando (`populate_hairdressers.py:256`)
**Requirement**: GAL-44, GAL-46

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Teste novo na classe do seed: com `random` fixado, o comando cria fotos em `hairdresser/gallery/<id>/*.webp`, entre 0 e 6 por cabeleireiro, e todos os objetos existem no storage.
- [x] `frontend-mobile/assets/hairdressers/gallery/` não existe mais, e `grep -rn "hairdressers/gallery" frontend-mobile --include=*.ts*` (fora do `node_modules`) não acha nada.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput users'`
- [x] Test count: total sem remoção.

**Tests**: integration
**Gate**: quick
**Commit**: `feat(seed): give seeded hairdressers gallery photos`

---

#### T9: Restaurar as fotos da galeria no boot

**What**: Criar `restore_missing_gallery_photos()`, que sobe de novo, na mesma chave, um placeholder convertido (`to_webp`) para cada foto de cabeleireiro do seed cuja chave falta no storage, com a escolha estável `sorted(files)[zlib.crc32(key.encode()) % n]`. Chamar a função onde `restore_missing_pictures` já é chamada.
**Where**: `backend/users/management/commands/populate_hairdressers.py`
**Depends on**: T8
**Reuses**: `restore_missing_pictures` (`populate_hairdressers.py:29`)
**Requirement**: GAL-45

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Testes novos:
  - apagar do storage a chave de uma foto do seed e rodar o comando: a chave volta, e o objeto é WebP;
  - uma foto que não é do seed e que falta no storage não é restaurada;
  - uma chave presente não é regravada.
- [x] Gate check passes: `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput'`
- [x] Test count: total sem remoção.

**Tests**: integration
**Gate**: full
**Commit**: `feat(seed): restore missing gallery photos on boot`

---

### Phase 3: App: base

#### T10: `gallery-full` no catálogo do app

**What**: Acrescentar `'gallery-full'` ao tipo `ProblemSlug` e o texto "Sua galeria já tem 30 fotos. Remova uma para adicionar outra." ao mapa de mensagens.
**Where**: `frontend-mobile/utils/api-problem.ts`
**Depends on**: None
**Reuses**: a entrada de `service-not-finished` (`api-problem.ts:41` e `:103`)
**Requirement**: GAL-42

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`, sem erro novo.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): translate the gallery-full problem`

---

#### T11: Tipos e serviço da galeria

**What**: Criar `models/Gallery.types.ts` (`GalleryPhoto`) e `services/gallery.service.ts` com `listGalleryPhotos`, `uploadGalleryPhoto` (o mesmo `FormData` de `uploadProfilePicture`, campo `image`) e `removeGalleryPhoto`.
**Where**: `frontend-mobile/services/gallery.service.ts` (mais `frontend-mobile/models/Gallery.types.ts`)
**Depends on**: None
**Reuses**: `uploadProfilePicture` e `PickedImage` (`services/account.service.ts:21-46`)
**Requirement**: GAL-09, GAL-25, GAL-36

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] As três funções usam `axiosInstance` e os paths de RT-94 a RT-96, e o `POST` manda `Content-Type: multipart/form-data`.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`, sem erro novo.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): add the gallery service`

---

#### T12: Hook `useGalleryPhotos`

**What**: Criar o hook de leitura da faixa: chama `listGalleryPhotos(id)` quando o id existe e devolve `[]` em erro, com `refresh()` para o `useFocusEffect` do perfil do cabeleireiro.
**Where**: `frontend-mobile/hooks/useGalleryPhotos.ts`
**Depends on**: T11
**Reuses**: o padrão de `useHairdresserProfile`
**Requirement**: GAL-06, GAL-07

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Um erro do `GET` dá `photos = []`, sem `throw`.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`, sem erro novo.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): add the gallery photos hook`

---

#### T13: Componente `GalleryStrip`

**What**: Criar a seção "Galeria": título, `FlatList` horizontal de miniaturas 100 × 100 (estilos `gallery` e `galleryImage`) e um `Modal` em tela cheia com a imagem em `contain` e o botão de fechar. Com a lista vazia, devolve `null`.
**Where**: `frontend-mobile/components/gallery/GalleryStrip.tsx`
**Depends on**: T12
**Reuses**: os estilos de `HairdresserProfileReservationStyle.ts:55-63`
**Requirement**: GAL-06, GAL-07, GAL-08

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O componente aceita `photos: GalleryPhoto[]`, devolve `null` com `[]` e abre e fecha a tela cheia pelo toque.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`, sem erro novo.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): add the gallery strip`

---

### Phase 4: App: telas

#### T14: Galeria no perfil público

**What**: Em `customer/hairdresser-reservation/[id].tsx`, trocar o bloco comentado `galleryImages` por `<GalleryStrip photos={...} />`, entre o resumo e "Técnicas", alimentado pelo `useGalleryPhotos(hairdresser.id)`.
**Where**: `frontend-mobile/app/(app)/customer/hairdresser-reservation/[id].tsx`
**Depends on**: None
**Reuses**: `GalleryStrip` e `useGalleryPhotos` (T12 e T13)
**Requirement**: GAL-06, GAL-07, GAL-08, GAL-46

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `grep -n "galleryImages" "frontend-mobile/app/(app)/customer/hairdresser-reservation/[id].tsx"` não acha nada.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`, sem erro novo.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): show the gallery on the public hairdresser profile`

---

#### T15: Hook `useGalleryManager`

**What**: Criar o hook da tela de gestão, como no design:
- a lista e o contador;
- `pickAndUpload`, com a permissão, `allowsMultipleSelection`, `selectionLimit = 30 − count`, sem `allowsEditing` e com `quality: 0.5`;
- o corte de `result.assets` às `30 − count` primeiras, com a mensagem de GAL-49, porque o web ignora o `selectionLimit`;
- o envio sequencial com `progress` e a contagem das falhas;
- o reload no fim e a mensagem "F de K fotos não foram enviadas." mais o slug da primeira falha;
- a remoção com confirmação (no 204, tira a foto do estado; no 404, recarrega; outro erro abre o modal);
- o `busyRef` contra a reentrada.

**Where**: `frontend-mobile/hooks/hairdresserHooks/useGalleryManager.ts`
**Depends on**: None
**Reuses**: `useProfilePicture` (`hooks/accountHooks/useProfilePicture.ts`) e `problemMessage`
**Requirement**: GAL-21, GAL-23, GAL-24, GAL-25, GAL-26, GAL-27, GAL-28, GAL-29, GAL-36, GAL-37, GAL-38, GAL-49, GAL-50, GAL-51

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O hook expõe a interface do design, e as mensagens pt-BR são as do spec, textualmente.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`, sem erro novo.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): add the gallery manager hook`

---

#### T16: Tela "Minha galeria"

**What**: Criar `hairdresser/profile/gallery.tsx`:
- cabeçalho com voltar, "Minha galeria" e "N/30";
- "Adicionar fotos", desabilitado com 30 fotos ou ocupado;
- a linha de progresso ou de limite;
- a grade de 3 colunas com o botão de remover;
- o estado vazio, o `ConfirmationModal` ("Remover esta foto da galeria?", "Remover") e o `ErrorModal`.

Registrar `<Stack.Screen name="gallery" />` na pilha do perfil.

**Where**: `frontend-mobile/app/(app)/hairdresser/profile/gallery.tsx` (mais `profile/_layout.tsx`)
**Depends on**: T15
**Reuses**: `ConfirmationModal`, `ErrorModal` e os estilos do perfil do cabeleireiro
**Requirement**: GAL-21, GAL-22, GAL-28, GAL-29, GAL-35

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Os textos da tela são os do spec, textualmente.
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`, sem erro novo.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): add the hairdresser gallery screen`

---

#### T17: Card e faixa no perfil do cabeleireiro

**What**: No `hairdresser/profile/index.tsx`:
- acrescentar o card "Minha galeria", que chama o `goToGallery` novo de `useHairdresserProfile` e abre `/(app)/hairdresser/profile/gallery`;
- acrescentar a `GalleryStrip` com o `useGalleryPhotos(hairdresser.id)`, recarregada no foco (`useFocusEffect`) para mostrar as mudanças feitas na tela de gestão.

**Where**: `frontend-mobile/app/(app)/hairdresser/profile/index.tsx` (mais `hooks/hairdresserHooks/useHairdresserProfile.ts`)
**Depends on**: T16
**Reuses**: os cards "Meus serviços" e "Meus horários de atendimento", e o `useFocusEffect` do `useAgenda`
**Requirement**: GAL-20, GAL-30

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Gate check passes: `cd frontend-mobile && npx tsc --noEmit`, sem erro novo.

**Tests**: none
**Gate**: app
**Commit**: `feat(app): link the gallery from the hairdresser profile`

---

### Phase 5: UAT

#### T18: UAT no web e no Android

**What**: Rodar o roteiro abaixo com um cabeleireiro do seed, um cabeleireiro novo e um cliente, atualizar a coluna Status da rastreabilidade do spec e corrigir o que falhar em tarefas de correção.

Roteiro:
1. **Perfil público** (cliente), depois do passo 2: abrir o cabeleireiro novo. A faixa aparece entre o resumo e "Técnicas", e o toque abre a tela cheia e fecha. Um cabeleireiro do seed (sem fotos no banco de dev atual) não mostra a seção.
2. **Adicionar** (cabeleireiro novo):
   - abrir "Minha galeria": aparecem o estado vazio e "0/30";
   - escolher 3 imagens e 1 `.txt` renomeado para `.jpg`: aparece "Enviando i de 4", a grade mostra 3 fotos e "3/30", e o modal diz "1 de 4 fotos não foram enviadas." mais o texto de `invalid-image`;
   - o bucket do LocalStack tem 3 objetos `.webp` em `hairdresser/gallery/<id>/`.
3. **Limite**:
   - com 29 fotos, no Android o seletor só deixa escolher 1;
   - no web, escolher 3: só 1 é enviada, e aparece "Só cabem mais 1 fotos. As outras não foram enviadas.";
   - com 30, "Adicionar fotos" fica desabilitado, e aparece "Limite de 30 fotos atingido.".
4. **Remover**: cancelar o modal não muda nada. Confirmar tira a foto da grade, do perfil do cabeleireiro ao voltar e do bucket.
5. **Permissão negada** (Android): aparece a mensagem do GAL-24, e nenhuma requisição sai.
6. **Exclusão da conta**: excluir a conta de um cabeleireiro com fotos. As chaves somem de `hairdresser/gallery/<id>/`.
7. **Seed**: só com a autorização do usuário para recriar o banco de dev. Com o banco novo, o perfil público dos cabeleireiros do seed mostra as fotos. Recriar o bucket do LocalStack e reiniciar o backend faz as fotos voltarem. Sem autorização, GAL-44 e GAL-45 ficam provados só pelos testes do T8 e do T9.

**Where**: `.specs/features/hairdresser-gallery/spec.md`
**Depends on**: None
**Reuses**: o roteiro de UAT da `account-settings` (T21)
**Requirement**: GAL-06, GAL-07, GAL-08, GAL-20, GAL-21, GAL-22, GAL-23, GAL-24, GAL-25, GAL-26, GAL-27, GAL-28, GAL-29, GAL-30, GAL-35, GAL-36, GAL-37, GAL-38, GAL-49, GAL-50, GAL-51

**Tools**:
- MCP: `claude-in-chrome` (UAT no web)
- Skill: `run`

**Done when**:
- [ ] Cada item do roteiro passa no web e no Android, ou vira uma tarefa de correção.
- [ ] Os critérios de app do spec ficam Verified.
- [ ] Gate check passes: Full + App.

**Tests**: none (UAT manual)
**Gate**: build
**Commit**: `docs(specs): record the hairdresser gallery UAT`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

Phase 1:  T1 ------→ T4
          T2 ------→ T3 ------→ T4 ------→ T5
          T2 ------→ T6
          T2 ------→ T7
Phase 2:  T8 ------→ T9
Phase 3:  T10
          T11 ------→ T12 ------→ T13
Phase 4:  T14
          T15 ------→ T16 ------→ T17
Phase 5:  T18
```

A execução é sequencial: uma tarefa de cada vez, na ordem T1 a T18.

**Lotes para sub-agentes** (18 tarefas, ~7 por lote, só fases inteiras):
- Lote 1: Phase 1 (T1 a T7), backend.
- Lote 2: Phases 2 e 3 (T8 a T13), seed e base do app.
- Lote 3: Phases 4 e 5 (T14 a T18), telas e UAT. O T18 depende do usuário para o Android.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Slug `gallery-full` | 1 entrada no catálogo | ✅ Granular |
| T2: Modelo | 1 modelo + migração gerada + serializer | ⚠️ Coeso: a migração é gerada, e o serializer é a forma do modelo na API |
| T3: `GET` | 1 endpoint (view + rota + Route Table) | ⚠️ Vários arquivos de propósito: o RT-50 falha se a rota existir sem a tabela |
| T4: `POST` | 1 endpoint (view + Route Table) | ⚠️ Mesmo motivo do T3 |
| T5: Lock do limite | 1 trecho de view | ✅ Granular |
| T6: `DELETE` | 1 endpoint (view + rota + Route Table) | ⚠️ Mesmo motivo do T3 |
| T7: Exclusão da conta | 1 função | ✅ Granular |
| T8: Seed (criação) | 1 comando + mover assets | ⚠️ Coeso: os assets mudam de lugar para o comando usá-los |
| T9: Seed (restauração) | 1 função | ✅ Granular |
| T10: Catálogo do app | 1 arquivo | ✅ Granular |
| T11: Serviço | 1 serviço + 1 tipo | ⚠️ Coeso: o tipo só existe para o serviço |
| T12: `useGalleryPhotos` | 1 hook | ✅ Granular |
| T13: `GalleryStrip` | 1 componente | ✅ Granular |
| T14: Perfil público | 1 tela | ✅ Granular |
| T15: `useGalleryManager` | 1 hook | ✅ Granular |
| T16: Tela da galeria | 1 tela + 1 linha de rota | ⚠️ A rota só registra a tela |
| T17: Perfil do cabeleireiro | 1 tela + 1 handler no hook | ⚠️ Coeso |
| T18: UAT | roteiro manual | ✅ |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | - | ✅ Match |
| T2 | None | - | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T1, T3 | T1 → T4, T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T2 | T2 → T6 | ✅ Match |
| T7 | T2 | T2 → T7 | ✅ Match |
| T8 | None (usa T2, de uma fase anterior) | - | ✅ Match |
| T9 | T8 | T8 → T9 | ✅ Match |
| T10 | None | - | ✅ Match |
| T11 | None | - | ✅ Match |
| T12 | T11 | T11 → T12 | ✅ Match |
| T13 | T12 | T12 → T13 | ✅ Match |
| T14 | None (usa T12 e T13, de uma fase anterior) | - | ✅ Match |
| T15 | None (usa T10 e T11, de uma fase anterior) | - | ✅ Match |
| T16 | T15 | T15 → T16 | ✅ Match |
| T17 | T16 | T16 → T17 | ✅ Match |
| T18 | None (depende de todas as fases anteriores) | - | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1: Slug | Backend: contratos | unit | unit | ✅ OK |
| T2: Modelo | Backend: modelo | integration | integration | ✅ OK |
| T3: `GET` | Backend: views + Route Table | integration + unit | integration (+ `RouteTableTests`) | ✅ OK |
| T4: `POST` | Backend: views + Route Table | integration + unit | integration (+ `RouteTableTests`) | ✅ OK |
| T5: Lock | Backend: views | integration | integration | ✅ OK |
| T6: `DELETE` | Backend: views + Route Table | integration + unit | integration (+ `RouteTableTests`) | ✅ OK |
| T7: Exclusão | Backend: views | integration | integration | ✅ OK |
| T8: Seed | Backend: seed | integration | integration | ✅ OK |
| T9: Restauração | Backend: seed | integration | integration | ✅ OK |
| T10 a T17 | App (`frontend-mobile`) | none | none (gate App) | ✅ OK |
| T18: UAT | Specs | none | none | ✅ OK |
