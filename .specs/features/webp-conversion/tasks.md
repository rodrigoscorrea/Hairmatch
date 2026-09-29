# Conversão de Fotos para WebP Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/webp-conversion/spec.md`
**Design**: `.specs/features/webp-conversion/design.md`
**Status**: Draft (aguardando aprovação para Execute)
**Branch sugerida**: `138-conversao-de-foto-para-webp`, criada a partir de `develop`, seguindo o padrão `<issue>-...` do repositório

**Pré-requisitos do Execute:**
- Postgres acessível para os testes do backend (`docker compose up db`, com as `DB_*` exportadas), ou os testes rodando dentro do container.
- O UAT (T9) precisa do `docker compose up` completo, com o LocalStack.
- Nenhuma credencial nova e nenhuma env var nova (preferência do projeto: só boto3).

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas:
> - `.github/workflows/hairmatch-backend-test.yml`: roda `coverage run manage.py test`, sem limite mínimo
> - `backend/hairmatch/tests.py`: `SimpleTestCase` com `patch('hairmatch.storage.boto3.client')` para o storage
> - `backend/users/tests.py`: `TestCase` + `APIClient` + `SimpleUploadedFile`; `PopulateHairdressersCommandTest` com `call_command` e `patch.object(PLACEHOLDERS_DIR)`
> - `backend/review/tests.py`: `ReviewsTestCase` + `APIClient`
> - `backend/hairmatch/settings.py:150`: `InMemoryStorage` durante os testes
>
> Strong defaults aplicados. As imagens de teste são geradas em memória com Pillow (`hairmatch/image_fixtures.py`), e nenhum binário novo entra no repositório.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: conversor e campo (`hairmatch/images.py`) | unit | Todos os ramos; 1:1 com WEBP-01 e WEBP-04 a WEBP-09 e WEBP-13; todos os edge cases de nome, modo, rotação + redução, WebP de entrada e JPEG truncado | `backend/hairmatch/tests.py` (classes novas `ToWebpTest`, `WebpNameTest`, `WebPImageFieldFileTest`) | `cd backend && python manage.py test hairmatch` |
| Backend: storage (`hairmatch/storage.py`) | unit | `ContentType` de `.webp` com `boto3` mockado (WEBP-04) | `backend/hairmatch/tests.py` (`S3MediaStorageTest`) | `cd backend && python manage.py test hairmatch` |
| Backend: views de cadastro e review | integration | Cada rota no escopo: foto válida vira `.webp`; foto inválida dá 400 com a mensagem exata e sem linhas no banco (WEBP-02, WEBP-03, WEBP-10 a WEBP-13) | `backend/users/tests.py`, `backend/review/tests.py` (`APIClient`) | `cd backend && python manage.py test users review` |
| Backend: management command do seed | integration | WEBP-14 a WEBP-17 via `call_command` | `backend/users/tests.py` (`PopulateHairdressersCommandTest`) | `cd backend && python manage.py test users` |
| Backend: models + migrations | none | Build gate: `makemigrations --check` sem mudanças pendentes | - | Build |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Os testes do backend precisam de Postgres: exporte `DB_HOST/DB_NAME/DB_USER/DB_PASSWORD`, ou rode dentro do container com `docker compose exec django python3 backend/manage.py test`.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas só com testes unit em `hairmatch` | `cd backend && python manage.py test hairmatch` |
| Full | Tarefas com testes de integração (views, seed) | `cd backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test && coverage report -m` |
| Build | Fim da feature (T9) | Full + verificações no container e no LocalStack descritas em T9 |

**Baseline de testes do backend**, contado com `git grep "def test_" -- 'backend/*tests.py'` em `develop` (`c445197`):
- **292** métodos `test_` em todo o projeto
- **16** em `backend/hairmatch/tests.py`
- **138** em `backend/users/tests.py`
- **14** em `backend/review/tests.py`

Nenhuma tarefa pode reduzir esses números. T1 confirma o baseline rodando a suíte antes de mudar qualquer coisa.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Conversor, storage e campo

```
T1 → T3
T2
```

### Phase 2: Usuários e seed

```
T4 → T5 → T6
```

### Phase 3: Reviews

```
T7 → T8
```

### Phase 4: Fechamento

```
T9
```

---

## Task Breakdown

### Phase 1: Conversor, storage e campo (tarefas)

#### T1: Criar o conversor `to_webp` em `hairmatch/images.py`

**What**: Criar `MAX_SIDE`, `WEBP_QUALITY`, `InvalidImage(ValueError)`, `webp_name(name)` e `to_webp(content)` conforme `design.md`, com o helper de teste `hairmatch/image_fixtures.py` e os testes unitários na mesma tarefa.
**Where**: `backend/hairmatch/images.py` (novo). Os testes co-localizados seguem o Location Pattern da matriz.
**Depends on**: None
**Reuses**: Pillow (`backend/requirements.txt:7`); o estilo de `SimpleTestCase` de `backend/hairmatch/tests.py`
**Requirement**: WEBP-05, WEBP-06, WEBP-07, WEBP-08, WEBP-09, WEBP-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Baseline confirmado: `python manage.py test` passa com 292 testes antes da mudança
- [x] No container: `python -c "from PIL import features; print(features.check('webp'))"` imprime `True`
- [x] `WebpNameTest`: `'dir/FOTO.JPG'` → `'dir/FOTO.webp'`, `'foto'` → `'foto.webp'`, `'a.b.png'` → `'a.b.webp'`
- [x] `ToWebpTest` cobre:
  - [x] JPEG RGB → saída com `format == 'WEBP'` (WEBP-01 no nível do conversor)
  - [x] JPEG 20×10 com `Orientation=6` → 10×20 (WEBP-05)
  - [x] JPEG 6000×4000 com `Orientation=6` → 720×1080 (WEBP-05 + WEBP-09)
  - [x] 4000×6000 → 720×1080; 6000×4000 → 1080×720; 1080×500 → 1080×500; 800×600 → 800×600 (WEBP-09)
  - [x] PNG `RGBA`, PNG `LA` e PNG `P` com transparência → `RGBA`; JPEG `CMYK`, PNG `L` e JPEG `RGB` → `RGB` (WEBP-06)
  - [x] JPEG com EXIF (inclusive GPS) → `getexif()` do WebP vazio; WebP de entrada com EXIF → saída sem EXIF (WEBP-07)
  - [x] JPEG com perfil ICC → o WebP mantém `info['icc_profile']` idêntico (decisão de Assumptions)
  - [x] `quality=80` passado ao encoder, verificado com `patch.object(Image.Image, 'save', wraps=...)` ou comparando o tamanho com uma codificação de referência q80 (WEBP-07)
  - [x] GIF com 3 quadros → `n_frames == 1` (WEBP-08)
  - [x] `b"file_content"`, texto com nome `.jpg` e JPEG truncado → `InvalidImage` (WEBP-10 a WEBP-12 no nível do conversor)
  - [x] Com `patch.object(Image, 'MAX_IMAGE_PIXELS', 10)`, uma imagem 20×10 → `InvalidImage` (WEBP-13)
- [x] Gate check passes: `cd backend && python manage.py test hairmatch`
- [x] Test count: ≥ 16 + novos testes em `hairmatch`, sem remoções

**Tests**: unit
**Gate**: quick

**Commit**: `feat(backend): add WebP image converter`
**Status**: ✅ Complete

---

#### T2: Registrar o MIME type `.webp` no storage

**What**: Adicionar `mimetypes.add_type('image/webp', '.webp')` no nível do módulo de `hairmatch/storage.py` e um teste de `ContentType` para `.webp`.
**Where**: `backend/hairmatch/storage.py`
**Depends on**: None
**Reuses**: `S3MediaStorageTest.test_save_uploads_with_content_type` (`backend/hairmatch/tests.py:195`)
**Requirement**: WEBP-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `S3MediaStorage.save('profile_pics/1/a.webp', ...)` → `upload_fileobj` chamado uma vez com `ExtraArgs={'ContentType': 'image/webp'}` (WEBP-04)
- [x] O teste passa mesmo com `mimetypes.types_map` sem `.webp` (simular com `patch.dict(mimetypes.types_map)` removendo a chave e recarregando o registro, ou verificando que `add_type` roda no import)
- [x] Gate check passes: `cd backend && python manage.py test hairmatch`
- [x] Test count: ≥ contagem de T1 + 1 em `hairmatch`, sem remoções

**Tests**: unit
**Gate**: quick

**Commit**: `fix(backend): serve .webp media with image/webp content type`
**Status**: ✅ Complete

---

#### T3: Criar `WebPImageField` e `WebPImageFieldFile`

**What**: Adicionar a `hairmatch/images.py` o `WebPImageFieldFile(ImageFieldFile)`, cujo `save` converte com `to_webp` e troca o nome com `webp_name`, e o `WebPImageField(models.ImageField)` com `attr_class`. Os testes unitários ficam na mesma tarefa.
**Where**: `backend/hairmatch/images.py`
**Depends on**: T1
**Reuses**: `ImageField` e `ImageFieldFile` do Django; `InMemoryStorage` dos testes (`backend/hairmatch/settings.py:150`)
**Requirement**: WEBP-01, WEBP-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `WebPImageFieldFileTest` usa uma instância de `User` não salva (ou um model de teste) e cobre:
  - [x] `field_file.save('foto.png', File(png))` → nome termina em `foto.webp` e o conteúdo gravado no storage tem `format == 'WEBP'` (WEBP-01)
  - [x] Com o storage do campo trocado por um mock: `save` é chamado **uma** vez, com nome `.webp` e bytes WebP, e `_open`/`open` nunca é chamado (WEBP-04: o original nunca vai ao storage e não há leitura para converter)
  - [x] Um arquivo inválido levanta `InvalidImage`, e nada é gravado no storage
  - [x] Dois saves de `foto.jpg` no mesmo diretório → o segundo nome é diferente e ainda termina em `.webp` (edge case de colisão)
- [x] `WebPImageField().deconstruct()` devolve o path `hairmatch.images.WebPImageField`
- [x] Gate check passes: `cd backend && python manage.py test hairmatch`
- [x] Test count: ≥ contagem de T2 + novos testes em `hairmatch`, sem remoções

**Tests**: unit
**Gate**: quick

**Commit**: `feat(backend): add WebPImageField that stores uploads as WebP`
**Status**: ✅ Complete

---

### Phase 2: Usuários e seed (tarefas)

#### T4: Casar as fotos do seed por stem no restore

**What**: Mudar `restore_missing_pictures` para localizar o placeholder pelo stem da chave. Chaves `.webp` recebem `to_webp` do placeholder, e chaves `.jpg` recebem os bytes originais. Trocar os `b'fake image'` do `setUp` de `PopulateHairdressersCommandTest` por JPEGs reais de `image_fixtures`.
**Where**: `backend/users/management/commands/populate_hairdressers.py`
**Depends on**: T1
**Reuses**: `to_webp` (T1); `make_image_bytes` (`hairmatch/image_fixtures.py`); setup atual de `PopulateHairdressersCommandTest` (`backend/users/tests.py:2560`)
**Requirement**: WEBP-15, WEBP-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os três testes atuais de `PopulateHairdressersCommandTest` continuam passando, agora com JPEGs reais (o campo ainda é `ImageField` nesta tarefa)
- [x] Novo teste: usuário cabeleireiro com `profile_picture.name = 'profile_pics/<id>/1_hairdresser_placeholder_male.webp'` e sem objeto no storage → depois do comando, a chave existe e o conteúdo tem `format == 'WEBP'` (WEBP-15)
- [x] Novo teste: mesma situação com a chave `.jpg` → a chave existe e os bytes são idênticos ao placeholder (WEBP-16)
- [x] Novo teste: chave com stem que não existe nos placeholders → nada é gravado e o comando não falha
- [x] Gate check passes: `cd backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test && coverage report -m`
- [x] Test count: ≥ 138 + novos testes em `users`, sem remoções

**Tests**: integration
**Gate**: full

**Commit**: `feat(seed): restore seeded pictures as WebP when the key is .webp`
**Status**: ✅ Complete

---

#### T5: Usar `WebPImageField` em `User.profile_picture`

**What**: Trocar `profile_picture` para `WebPImageField(upload_to=user_profile_picture_path, ...)` e gerar a migration AlterField `users/0007`. Atualizar os testes que dependem do nome ou do conteúdo da foto.
**Where**: `backend/users/models.py`
**Depends on**: T3, T4
**Reuses**: `user_profile_picture_path` (`backend/users/models.py:8`); `make_upload` (`hairmatch/image_fixtures.py`)
**Requirement**: WEBP-02, WEBP-14, WEBP-17

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Migration `backend/users/migrations/0007_*.py` gerada com `makemigrations users`, contendo só a AlterField de `profile_picture`
- [x] `test_register_with_profile_picture` usa um JPEG real e verifica `profile_pics/{user.id}/profile.webp` e `format == 'WEBP'` (WEBP-02)
- [x] Novo teste: cadastro Google com `profile_picture` válida → `profile_pics/{user.id}/<stem>.webp` (WEBP-02)
- [x] Novo teste: cadastro com `FOTO.JPG` 3000×2000 → nome `.../FOTO.webp` e dimensões 1080×720 (WEBP-02, WEBP-09 de ponta a ponta)
- [x] `test_uploads_each_hairdresser_picture_to_its_own_directory` verifica diretório `profile_pics/{user.id}`, stem entre os placeholders, extensão `.webp` e conteúdo WebP (WEBP-14)
- [x] `test_running_twice_does_not_duplicate_uploads_or_hairdressers` continua verificando um único arquivo por diretório (WEBP-17)
- [x] `test_restores_missing_seeded_pictures_on_the_same_key` recria a chave `.webp` com conteúdo WebP (WEBP-15)
- [x] Gate check passes: `cd backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test && coverage report -m`
- [x] Test count: ≥ contagem de T4 + novos testes em `users`, sem remoções

**Tests**: integration
**Gate**: full

**Commit**: `feat(users): store profile pictures as WebP`
**Status**: ✅ Complete

---

#### T6: Rejeitar foto de perfil inválida no cadastro

**What**: No `RegisterView`, colocar a criação do usuário por senha (create + foto + `_create_role_profile`) dentro de `transaction.atomic()` e tratar `InvalidImage` com 400 `"Imagem de perfil inválida."` nos dois caminhos. No caminho Google, o `except InvalidImage` vem antes do `except ValueError`.
**Where**: `backend/users/views.py`
**Depends on**: T5
**Reuses**: `transaction.atomic` já usado em `_register_with_google` (`backend/users/views.py:130`); `InvalidImage` (T1)
**Requirement**: WEBP-10, WEBP-11, WEBP-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Cadastro por senha com `profile_picture` = `SimpleUploadedFile('p.jpg', b'not an image')` → 400 `{"error": "Imagem de perfil inválida."}`, `User.objects.count() == 0`, `Customer.objects.count() == 0` (WEBP-10)
- [x] Mesmo teste com `role='hairdresser'` → `Hairdresser.objects.count() == 0` (WEBP-10)
- [x] Depois do 400, o mesmo payload com uma foto válida → 201 (o e-mail não ficou preso) (WEBP-10)
- [x] Cadastro Google com foto inválida → 400 com a mensagem exata (não a de preferências), `User.objects.count() == 0` e sem cookie `jwt` na resposta (WEBP-11)
- [x] Cadastro por senha com JPEG truncado → 400 com a mensagem exata (edge case)
- [x] Com `patch.object(Image, 'MAX_IMAGE_PIXELS', 10)` → 400 com a mesma mensagem (WEBP-13)
- [x] Cadastro sem `profile_picture` continua devolvendo 201 com `profile_picture` vazio (edge case)
- [x] Gate check passes: `cd backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test && coverage report -m`
- [x] Test count: ≥ contagem de T5 + novos testes em `users`, sem remoções

**Tests**: integration
**Gate**: full

**Commit**: `fix(users): reject invalid profile pictures without creating the user`
**Status**: ✅ Complete

---

### Phase 3: Reviews (tarefas)

#### T7: Usar `WebPImageField` em `Review.picture`

**What**: Trocar `Review.picture` para `WebPImageField(upload_to='reviews/images/', ...)`, gerar a migration AlterField `review/0003` e testar a criação de review com foto.
**Where**: `backend/review/models.py`
**Depends on**: T3
**Reuses**: `ReviewsTestCase` e `CreateReviewTest` (`backend/review/tests.py:12`, `:156`); `make_upload`
**Requirement**: WEBP-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Migration `backend/review/migrations/0003_*.py` gerada, contendo só a AlterField de `picture`
- [ ] Novo teste: `POST` de review em multipart com `picture` PNG válido → 201, `picture.name` igual a `reviews/images/<stem>.webp` e conteúdo WebP (WEBP-03)
- [ ] Os testes existentes de `review` continuam passando
- [ ] Gate check passes: `cd backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test && coverage report -m`
- [ ] Test count: ≥ 14 + novos testes em `review`, sem remoções

**Tests**: integration
**Gate**: full

**Commit**: `feat(review): store review pictures as WebP`

---

#### T8: Rejeitar foto inválida na criação de review

**What**: Em `CreateReview.post`, tratar `InvalidImage` antes do `except Exception`, devolvendo 400 `"Imagem inválida."`. O `transaction.atomic` existente desfaz a review.
**Where**: `backend/review/views.py`
**Depends on**: T7
**Reuses**: `transaction.atomic` existente (`backend/review/views.py:69`); `InvalidImage` (T1)
**Requirement**: WEBP-12, WEBP-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Review com `picture` = texto → 400 `{"error": "Imagem inválida."}`, `Review.objects.count()` inalterado e `reserve.review` ainda nulo depois de `refresh_from_db()` (WEBP-12)
- [ ] Com `patch.object(Image, 'MAX_IMAGE_PIXELS', 10)` → 400 com a mesma mensagem (WEBP-13)
- [ ] Gate check passes: `cd backend && python manage.py makemigrations --check --dry-run && coverage run manage.py test && coverage report -m`
- [ ] Test count: ≥ contagem de T7 + novos testes em `review`, sem remoções

**Tests**: integration
**Gate**: full

**Commit**: `fix(review): reject invalid review pictures with 400`

---

### Phase 4: Fechamento (tarefas)

#### T9: Verificação ponta a ponta no LocalStack

**What**: Rodar o roteiro abaixo no ambiente Docker, registrar os resultados nesta tarefa e corrigir o que falhar em uma tarefa nova.
**Where**: `.specs/features/webp-conversion/tasks.md` (registro dos resultados; nenhum código)
**Depends on**: T2, T6, T8
**Reuses**: `docker/docker-compose.yml`; `awslocal`
**Requirement**: WEBP-01, WEBP-02, WEBP-04, WEBP-09, WEBP-10, WEBP-14

**Tools**:

- MCP: NONE
- Skill: `run` (para subir o app, se útil)

**Done when**:

- [ ] No container: `python -c "import hairmatch.storage, mimetypes; print(mimetypes.guess_type('a.webp'))"` → `('image/webp', None)`
- [ ] **Pré-condição:** banco sem cabeleireiros (volume novo do Postgres). Hoje o banco de dev persiste e tem o seed antigo com chaves `.jpg`, que o restore recria como JPEG (WEBP-16). Apagar o volume (`docker compose down -v`) **exige a autorização do usuário antes**. Sem essa autorização, pule este item e o próximo e registre o motivo.
- [ ] `docker compose up` com o banco e o bucket vazios → `awslocal s3 ls s3://<bucket>/profile_pics/ --recursive` lista 40 objetos, todos `.webp`, somando ≤ 5 MB (Success Criteria)
- [ ] `curl -I` na URL de um cabeleireiro devolvida pela API → 200 com `Content-Type: image/webp` (WEBP-04)
- [ ] Um objeto criado nesta verificação, baixado e aberto com Pillow, tem o maior lado ≤ 1080 px (WEBP-09)
- [ ] `curl -F profile_picture=@foto.jpg ...` em `/api/auth/register` → 201 e só a chave `profile_pics/<id>/foto.webp` no bucket, sem nenhum `foto.jpg` (WEBP-02, WEBP-04)
- [ ] `curl -F profile_picture=@notas.txt ...` → 400 `"Imagem de perfil inválida."` e o e-mail continua livre (WEBP-10)
- [ ] Gate check passes: Build (Full + os itens acima)

**Tests**: none
**Gate**: build

**Commit**: `docs(specs): record webp-conversion end-to-end verification`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4

Phase 1:  T1 ------→ T3
          T2
Phase 2:  T4 ------→ T5 ------→ T6
Phase 3:  T7 ------→ T8
Phase 4:  T9
```

São 9 tarefas, então no Execute o empacotamento dá dois lotes: Phases 1–2 (6 tarefas) e Phases 3–4 (3 tarefas). O Execute oferece sub-agentes antes de começar. Se o usuário recusar, tudo roda inline, em sequência.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Conversor `to_webp` | 1 módulo (funções coesas) + helper de fixtures de teste | ✅ Granular |
| T2: MIME `.webp` no storage | 1 linha em 1 arquivo | ✅ Granular |
| T3: `WebPImageField` | 2 classes coesas em 1 arquivo | ✅ Granular |
| T4: Restore do seed por stem | 1 função | ✅ Granular |
| T5: Campo em `User` | 1 campo + migration gerada | ✅ Granular |
| T6: Foto inválida no cadastro | 1 view (dois caminhos do mesmo endpoint) | ✅ Granular |
| T7: Campo em `Review` | 1 campo + migration gerada | ✅ Granular |
| T8: Foto inválida na review | 1 handler | ✅ Granular |
| T9: Verificação E2E | 1 roteiro manual | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | nenhuma aresta de entrada | ✅ Match |
| T2 | None | nenhuma aresta de entrada | ✅ Match |
| T3 | T1 | T1 → T3 | ✅ Match |
| T4 | T1 (Phase 1) | nenhuma aresta de entrada dentro da Phase 2 | ✅ Match |
| T5 | T3 (Phase 1), T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | T3 (Phase 1) | nenhuma aresta de entrada dentro da Phase 3 | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | T2 (Phase 1), T6 (Phase 2), T8 (Phase 3) | nenhuma aresta de entrada dentro da Phase 4 | ✅ Match |

Nenhuma dependência aponta para uma fase posterior.

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Conversor (`hairmatch/images.py`) | unit | unit | ✅ OK |
| T2 | Storage (`hairmatch/storage.py`) | unit | unit | ✅ OK |
| T3 | Campo (`hairmatch/images.py`) | unit | unit | ✅ OK |
| T4 | Management command do seed | integration | integration | ✅ OK |
| T5 | Model + migration, afetando a view de cadastro e o seed | integration (maior tipo entre model=none e views/seed=integration) | integration | ✅ OK |
| T6 | View de cadastro | integration | integration | ✅ OK |
| T7 | Model + migration, afetando a view de review | integration | integration | ✅ OK |
| T8 | View de review | integration | integration | ✅ OK |
| T9 | Nenhum código (roteiro de verificação) | none | none | ✅ OK |
