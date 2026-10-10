# Galeria de fotos do cabeleireiro Specification

**Issue:** [#118](https://github.com/rodrigoscorrea/Hairmatch/issues/118) · [Feature][Front/Back][Hairdresser] Galeria de fotos: adicionar e excluir (RF31 e RF32)
**Escopo:** Complex (persistência, upload ao S3, posse do recurso, concorrência no limite, backend e app)
**Plataformas:** backend Django e app (web e Android)

## Problem Statement

O cabeleireiro não tem onde mostrar o próprio trabalho. O perfil público tinha uma seção "Galeria", mas ela lia imagens estáticas do app (`frontend-mobile/assets/hairdressers/gallery/`), iguais para todo profissional, e por isso foi comentada (`frontend-mobile/app/(app)/customer/hairdresser-reservation/[id].tsx:78-86`). Não existe modelo, rota nem tela de gestão.

A foto de perfil (#120) já resolve upload, conversão para WebP (AD-003) e limpeza no bucket para uma foto só. A galeria leva o mesmo fluxo para até 30 fotos por cabeleireiro.

## Goals

- [ ] O cabeleireiro adiciona várias fotos de uma vez e remove fotos pelo app. Cada mudança aparece no `GET /api/hairdressers/{id}/gallery-photos` seguinte.
- [ ] O cliente vê a galeria real no perfil público do cabeleireiro, sem login.
- [ ] Nenhuma galeria passa de 30 fotos, nem com uploads em paralelo, e nenhum arquivo fica órfão no bucket depois de remover uma foto ou excluir a conta.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Editar ou recortar uma foto | A edição é remover e adicionar, por decisão do usuário. O seletor com várias fotos não permite recorte (expo-image-picker 57). |
| Legenda, capa, curtidas e comentários | A issue não pede. |
| Reordenar as fotos | A ordem é a de envio, da mais nova para a mais antiga. |
| Vídeo | A issue pede fotos. O `WebPImageField` só trata imagem. |
| Paginação do `GET` | São no máximo 30 fotos de até 1080 px, e a resposta cabe numa página. |
| Moderação de conteúdo | Não há moderação em nenhuma mídia do projeto. Fica para uma feature própria. |
| Throttle do upload | A rota exige sessão de cabeleireiro, e o limite de 30 fotos já limita o armazenamento. |
| Testes automatizados no app | O app não tem suíte. O gate do app é `npx tsc --noEmit` mais o UAT, como na #120. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Chave no bucket | `hairdresser/gallery/<hairdresser_id>/<uuid4 hex>.webp`, sem barra inicial. | Escolha do usuário. Segue `profile_pics/<id>/`, e o uuid evita colisão e não expõe o nome original do arquivo. | y |
| Limite de fotos | 30 por cabeleireiro. | Escolha do usuário. | y |
| Limite por foto | 5 MB (5 × 1024 × 1024 bytes) antes da conversão, como a foto de perfil (ACC-39, `PROFILE_PICTURE_MAX_SIZE`). | A conversão roda na requisição (AD-003). Um limite só para as duas rotas de imagem. | y |
| Onde se gerencia | Tela própria, `hairdresser/profile/gallery`, aberta pelo card "Minha galeria" do perfil. | Escolha do usuário. Segue os cards "Meus serviços" e "Meus horários". | y |
| Upload de várias fotos | Seleção múltipla no seletor. O app manda uma requisição por foto, em sequência, e informa quantas falharam. | Escolha do usuário. Mandar em sequência evita disputar o lock do limite e deixa a falha parcial clara. | y |
| Persistência | Tabela própria (`GalleryPhoto`), e não um campo JSONB em `Hairdresser`. Ver `design.md` e AD-013. | O `WebPImageField` é campo de modelo (AD-003). O insert por foto não perde escrita concorrente, e a remoção é por PK. | y |
| Ordem | Da mais nova para a mais antiga (`created_at` desc, `id` desc no empate). | A foto recém-enviada aparece primeiro, sem um campo de ordem. | n |
| Galeria vazia no perfil | O perfil público e o perfil do cabeleireiro escondem a seção "Galeria". A tela de gestão mostra o estado vazio. | Uma seção vazia no perfil público não informa nada ao cliente. | n |
| Cabeleireiro pendente (`is_active=False`, AD-008) | O `GET` responde como para qualquer cabeleireiro. A galeria dele é sempre vazia, porque o `POST` exige sessão, e uma conta pendente não tem sessão. | Segue o `GET /api/hairdressers/{id}` (RT-15) e o `GET /api/hairdressers/{id}/availabilities` (RT-30), que não filtram `is_active`. | n |
| Confirmação da remoção | Modal "Remover esta foto da galeria?" com "Cancelar" e "Remover". | A remoção não tem desfazer. | n |
| Qualidade no seletor | `quality: 0.5`, como o cadastro e a foto de perfil. | Menos bytes no upload. O backend reduz para 1080 px de qualquer jeito. | n |
| Resposta do `POST` | 201 `{"data": {id, image, created_at}}`, o mesmo formato de um item do `GET`. | O app pode inserir a foto sem recarregar, embora recarregue no fim do lote. | n |
| Fotos do seed | De 0 a 6 fotos por cabeleireiro, sobretudo das imagens que hoje ficam em `frontend-mobile/assets/hairdressers/gallery/`, enviadas pelo modelo (memória `seed-mirrors-prod`). | O seed segue o fluxo real de upload. | n |
| Seed num banco já populado | O `populate_hairdressers` só cria cabeleireiros num banco sem nenhum (`handle`, `populate_hairdressers.py:87`), então GAL-44 não roda no banco de dev atual, e as galerias dele começam vazias. Não há backfill. Para ver as fotos do seed, é preciso recriar o banco, o que só acontece com a autorização do usuário. | Zero fotos é um resultado válido do sorteio, então um backfill não teria como distinguir quem já passou pelo seed. GAL-44 é provado pelo teste automatizado. | n |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## User Stories

### P1: Ver a galeria no perfil público ⭐ MVP

**User Story**: Como cliente, quero ver as fotos de trabalhos do cabeleireiro no perfil dele, para decidir se agendo.

**Why P1**: É o critério de aceite da issue do lado do cliente, e a seção existe hoje só comentada.

**Acceptance Criteria**:

1. **GAL-01** WHEN `GET /api/hairdressers/{id}/gallery-photos` é chamado para um cabeleireiro que existe THEN o backend SHALL responder 200 `{"data": [...]}` com todas as fotos dele, cada uma `{"id", "image", "created_at"}`, ordenadas por `created_at` decrescente e `id` decrescente no empate.
2. **GAL-02** WHEN o cabeleireiro não tem fotos THEN o `GET` SHALL responder 200 `{"data": []}`.
3. **GAL-03** IF o `{id}` não é de um cabeleireiro THEN o `GET` SHALL responder 404 `not-found`.
4. **GAL-04** WHEN o `GET` é chamado sem cookie de sessão THEN o backend SHALL responder como com sessão (200 com as fotos).
5. The campo `image` de cada foto SHALL ser a URL pública do storage (`default_storage.url`) de uma chave `hairdresser/gallery/<hairdresser_id>/<32 hex>.webp`, e a resposta SHALL não conter o nome original do arquivo enviado. **(GAL-05)**
6. **GAL-06** WHEN o perfil público do cabeleireiro abre THEN o app SHALL chamar o `GET` e mostrar a seção "Galeria", entre o resumo e "Técnicas", com as fotos numa faixa horizontal na ordem da API.
7. **GAL-07** IF o `GET` responde `{"data": []}` ou falha THEN o app SHALL esconder a seção "Galeria" e SHALL mostrar o resto do perfil normalmente.
8. **GAL-08** WHEN o usuário toca numa foto da faixa THEN o app SHALL abrir a foto em tela cheia, com um botão de fechar que volta ao perfil.

**Independent Test**: com um cabeleireiro do seed que tenha fotos, abrir o perfil público como cliente. A faixa mostra as fotos do bucket, e o toque abre a tela cheia. Com um cabeleireiro sem fotos, a seção não aparece.

---

### P1: Adicionar fotos ⭐ MVP

**User Story**: Como cabeleireiro, quero adicionar fotos dos meus trabalhos, várias de uma vez, para montar meu portfólio no perfil.

**Why P1**: É o RF31 e metade do critério de aceite da issue.

**Acceptance Criteria**:

1. **GAL-09** WHEN o cabeleireiro da sessão envia `POST /api/hairdressers/{id}/gallery-photos` com o próprio `{id}` e uma imagem válida no campo multipart `image` THEN o backend SHALL criar a foto e responder 201 `{"data": {"id", "image", "created_at"}}`.
2. The backend SHALL gravar cada foto da galeria pelo `WebPImageField` (AD-003): o objeto no storage é WebP, tem o maior lado com no máximo 1080 px e fica na chave `hairdresser/gallery/<hairdresser_id>/<32 hex>.webp`. **(GAL-10)**
3. **GAL-11** IF o `POST` não traz o campo `image` THEN o backend SHALL responder 400 `validation-error` com um item `{"pointer": "#/image"}` e SHALL não gravar nenhuma linha nem nenhum arquivo.
4. **GAL-12** IF o arquivo do `POST` tem mais de 5 MB (5 × 1024 × 1024 bytes) THEN o backend SHALL responder 400 `validation-error` com o pointer `#/image` e SHALL não gravar nenhuma linha nem nenhum arquivo.
5. **GAL-13** IF o arquivo do `POST` não é uma imagem que o `WebPImageField` converte THEN o backend SHALL responder 400 `invalid-image` e SHALL não gravar nenhuma linha nem nenhum arquivo.
6. **GAL-14** IF o cabeleireiro já tem 30 fotos THEN o `POST` SHALL responder 409 `gallery-full` e SHALL não gravar nenhuma linha nem nenhum arquivo.
7. **GAL-15** WHEN vários `POST` do mesmo cabeleireiro chegam ao mesmo tempo THEN o backend SHALL gravar no máximo `30 − N` deles, onde N é o total de fotos antes, e SHALL responder 409 `gallery-full` aos demais.
8. **GAL-16** IF o `POST` chega sem sessão válida THEN o backend SHALL responder 401 `invalid-session`.
9. **GAL-17** IF a sessão do `POST` é de um cliente THEN o backend SHALL responder 403 `hairdresser-required`.
10. **GAL-18** IF o `{id}` do `POST` não é o do cabeleireiro da sessão THEN o backend SHALL responder 403 `forbidden` e SHALL não gravar nenhuma linha nem nenhum arquivo.
11. **GAL-19** IF o upload ao storage falha THEN o backend SHALL responder 500 `internal-error` e SHALL não deixar nenhuma linha de `GalleryPhoto` gravada.
12. The perfil do cabeleireiro SHALL ter o card "Minha galeria", que abre a tela `hairdresser/profile/gallery`. **(GAL-20)**
13. **GAL-21** WHEN a tela da galeria abre THEN o app SHALL mostrar as fotos do `GET` numa grade de 3 colunas, na ordem da API, e o contador "N/30".
14. **GAL-22** WHILE a galeria está vazia a tela SHALL mostrar "Você ainda não adicionou fotos." e o botão "Adicionar fotos".
15. **GAL-23** WHEN o cabeleireiro toca em "Adicionar fotos" THEN o app SHALL pedir a permissão da galeria do aparelho e abrir o seletor só de imagens, com seleção múltipla, `selectionLimit` igual a `30 − N` (o Android e o iOS respeitam, o web não), sem recorte e com qualidade 0.5.
16. **GAL-24** IF a permissão da galeria é negada THEN o app SHALL mostrar "Permita o acesso às fotos para adicionar fotos à galeria." e SHALL não chamar a API.
17. **GAL-25** WHEN o cabeleireiro escolhe K fotos (K já limitado por GAL-49) THEN o app SHALL enviar K `POST`, uma foto por requisição e uma requisição por vez, e SHALL mostrar "Enviando i de K" durante o envio.
18. **GAL-26** WHEN todos os K envios terminam THEN o app SHALL recarregar a grade pelo `GET`.
19. **GAL-27** IF F dos K envios falham (F ≥ 1) THEN o app SHALL mostrar "F de K fotos não foram enviadas." seguido da mensagem do slug da primeira falha.
20. **GAL-28** WHILE a galeria tem 30 fotos o botão "Adicionar fotos" SHALL ficar desabilitado e a tela SHALL mostrar "Limite de 30 fotos atingido.".
21. **GAL-29** WHILE um envio ou uma remoção está em andamento o app SHALL desabilitar "Adicionar fotos" e os botões de remover, para não repetir a chamada.
22. **GAL-30** WHEN o perfil do cabeleireiro abre THEN o app SHALL mostrar a mesma faixa "Galeria" do perfil público (GAL-06 a GAL-08) com as fotos dele.

**Independent Test**: no web, como cabeleireiro, abrir "Minha galeria", escolher 3 imagens e um arquivo `.txt` renomeado para `.jpg`. Três fotos aparecem na grade, o contador vai a "3/30", aparece "1 de 4 fotos não foram enviadas." e o bucket do LocalStack tem 3 objetos `.webp` em `hairdresser/gallery/<id>/`.

---

### P1: Remover fotos ⭐ MVP

**User Story**: Como cabeleireiro, quero remover uma foto da galeria, para manter só os trabalhos que me representam.

**Why P1**: É o RF32 e a outra metade do critério de aceite da issue.

**Acceptance Criteria**:

1. **GAL-31** WHEN o cabeleireiro da sessão chama `DELETE /api/hairdressers/{id}/gallery-photos/{photo_id}` com o próprio `{id}` e uma foto dele THEN o backend SHALL apagar a linha, responder 204 e apagar o arquivo do storage depois do commit.
2. **GAL-32** IF `{photo_id}` não existe ou é de outro cabeleireiro THEN o `DELETE` SHALL responder 404 `not-found` e SHALL não apagar nenhuma linha nem nenhum arquivo.
3. **GAL-33** IF o `DELETE` chega sem sessão, com sessão de cliente ou com um `{id}` que não é o da sessão THEN o backend SHALL responder como no `POST` (401 `invalid-session`, 403 `hairdresser-required` e 403 `forbidden`, nessa ordem de checagem) e SHALL não apagar nada.
4. **GAL-34** IF apagar o arquivo do storage falha depois do commit THEN o backend SHALL manter a resposta 204 e SHALL registrar a falha no log com a chave do arquivo.
5. **GAL-35** WHEN o cabeleireiro toca no botão de remover de uma foto da grade THEN o app SHALL abrir o modal "Remover esta foto da galeria?" com "Cancelar" e "Remover".
6. **GAL-36** WHEN o cabeleireiro confirma "Remover" THEN o app SHALL chamar o `DELETE` e, no 204, SHALL tirar a foto da grade e atualizar o contador.
7. **GAL-37** IF o `DELETE` responde 404 THEN o app SHALL recarregar a grade pelo `GET` sem mostrar erro.
8. **GAL-38** IF o `DELETE` falha com outro erro THEN o app SHALL mostrar a mensagem do slug e manter a foto na grade.

**Independent Test**: no web, remover uma foto e confirmar. Ela some da grade e do perfil público, e o objeto some de `hairdresser/gallery/<id>/` no bucket. Cancelar o modal não muda nada.

---

### P1: Ciclo de vida dos arquivos ⭐ MVP

**User Story**: Como operador do Hairmatch, quero que as fotos da galeria saiam do bucket junto com a conta, para não guardar mídia de quem saiu.

**Why P1**: Sem isso, cada exclusão de conta de cabeleireiro deixa até 30 objetos órfãos no bucket. O `_delete_account_rows` já faz isso para as fotos de perfil e de avaliação (`backend/users/views.py:229`).

**Acceptance Criteria**:

1. **GAL-39** WHEN um cabeleireiro com fotos na galeria exclui a conta (`DELETE /api/users/me`) THEN o backend SHALL apagar as linhas de `GalleryPhoto` dele e, depois do commit, todos os arquivos da galeria dele no storage.
2. **GAL-40** IF a exclusão da conta falha e é desfeita (por exemplo, erro do Cognito) THEN o backend SHALL manter as linhas e os arquivos da galeria.

**Independent Test**: excluir pelo app a conta de um cabeleireiro com 2 fotos. Os 2 objetos somem de `hairdresser/gallery/<id>/`.

---

### P2: Contrato da API

**User Story**: Como desenvolvedor do app, quero as rotas e o erro novo nos contratos do projeto, para tratar a galeria como qualquer outro recurso.

**Why P2**: O AD-006 e o AD-007 exigem a Route Table e o catálogo antes do código. Os testes desses contratos falham sem isso.

**Acceptance Criteria**:

1. The Route Table do spec `api-restful-routes` e o `ROUTE_TABLE` de `backend/hairmatch/test_routes.py` SHALL conter RT-94 `GET /api/hairdressers/{id}/gallery-photos`, RT-95 `POST /api/hairdressers/{id}/gallery-photos` e RT-96 `DELETE /api/hairdressers/{id}/gallery-photos/{id}`. **(GAL-41)**
2. The slug `gallery-full` (409, "Gallery is full") SHALL constar do catálogo do spec `api-problem-details`, do `CATALOG` de `backend/hairmatch/problems.py` e do catálogo de `frontend-mobile/utils/api-problem.ts`, com o texto "Sua galeria já tem 30 fotos. Remova uma para adicionar outra.". **(GAL-42)**
3. **GAL-43** WHEN um método fora da Route Table é usado na coleção ou no item (por exemplo, `PUT /api/hairdressers/{id}/gallery-photos`) THEN o backend SHALL responder 405 `method-not-allowed` com `Allow` listando só os métodos da tabela (`GET, OPTIONS, POST` na coleção e `DELETE, OPTIONS` no item).

**Independent Test**: `RouteTableTests` e `test_problems` passam. `PUT /api/hairdressers/1/gallery-photos` responde 405 com o `Allow` do spec.

---

### P2: Seed com galeria

**User Story**: Como desenvolvedor, quero cabeleireiros do seed com fotos na galeria, para testar as telas sem subir fotos à mão.

**Why P2**: A feature funciona sem o seed, mas o UAT e as demonstrações dependem dele.

**Acceptance Criteria**:

1. **GAL-44** WHEN `populate_hairdressers` cria os cabeleireiros THEN cada um SHALL receber de 0 a 6 fotos na galeria, enviadas por `GalleryPhoto.image.save` a partir de `backend/users/management/commands/seed_assets/gallery/`.
2. **GAL-45** WHEN `populate_hairdressers` roda com cabeleireiros já criados e a chave de uma foto da galeria falta no bucket THEN o comando SHALL subir de novo, na mesma chave, um placeholder da galeria convertido para WebP.
3. The app SHALL deixar de conter `frontend-mobile/assets/hairdressers/gallery/` e o bloco comentado `galleryImages` de `customer/hairdresser-reservation/[id].tsx`. **(GAL-46)**

**Independent Test**: os testes automatizados de GAL-44 e GAL-45. Num banco recriado, com autorização, o perfil público dos cabeleireiros do seed mostra as fotos. Esvaziar o bucket e reiniciar o backend faz as fotos voltarem.

---

## Edge Cases

- IF `{photo_id}` não é inteiro (`/gallery-photos/abc`) THEN o backend SHALL responder 404 `not-found`, como manda o RT-81. **(GAL-47)**
- IF o `POST` chega com corpo JSON em vez de multipart THEN o backend SHALL responder 400 `validation-error` com o pointer `#/image`, como em GAL-11. **(GAL-48)**
- IF o seletor devolve mais fotos que as `30 − N` vagas (o web ignora o `selectionLimit`) THEN o app SHALL enviar só as `30 − N` primeiras e SHALL mostrar "Só cabem mais V fotos. As outras não foram enviadas.", onde V = `30 − N`. **(GAL-49)**
- IF outra sessão enche a galeria durante o envio de um lote THEN o `POST` SHALL responder 409 `gallery-full`, e o app SHALL contar esse envio como falha em GAL-27. **(GAL-51)**
- IF a sessão expira durante o envio do lote THEN o app SHALL seguir o fluxo atual do `axiosInstance` (refresh e, se ele falhar, login), e os envios que já terminaram SHALL continuar gravados. **(GAL-50)**

---

## Implicit-Requirement Dimensions

| Dimension | Coverage |
| --------- | -------- |
| Input validation & bounds | GAL-11 a GAL-14 (campo, 5 MB, imagem válida, 30 fotos), GAL-47 e GAL-48. |
| Failure / partial-failure states | GAL-19 (upload falha sem deixar linha), GAL-27 (lote com falha parcial), GAL-34 (falha ao apagar o arquivo) e GAL-40 (exclusão de conta desfeita). |
| Idempotency / retry / duplicate handling | GAL-29 (sem chamada repetida no app) e GAL-37 (404 no `DELETE` repetido recarrega sem erro). Um `POST` repetido grava outra foto, e isso é aceito: duas fotos iguais não violam nenhuma regra, e o limite de 30 vale do mesmo jeito. |
| Auth boundaries & rate limits | GAL-04 (leitura anônima), GAL-16 a GAL-18 e GAL-33 (dono). Throttle fora do escopo (Out of Scope). |
| Concurrency / ordering | GAL-15 (limite sob `POST` concorrente), GAL-51 (lote que perde a corrida) e GAL-01 (ordem determinística). |
| Data lifecycle / expiry | GAL-31 (arquivo apagado com a foto) e GAL-39 (arquivos apagados com a conta). |
| Observability | GAL-34 (log da falha ao apagar). Os erros inesperados já são logados pelo `exception_handler` (AD-006). |
| External-dependency failure | GAL-19 (S3 indisponível no upload), GAL-34 (S3 indisponível na remoção) e GAL-07 (app sem a galeria quando o `GET` falha). |
| State-transition integrity | N/A, porque a foto não tem estados: ela existe ou não existe. A transição da conta é coberta por GAL-39 e GAL-40. |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| GAL-01 | P1: Ver a galeria, AC1 | Tasks | Implementing |
| GAL-02 | P1: Ver a galeria, AC2 | Tasks | Implementing |
| GAL-03 | P1: Ver a galeria, AC3 | Tasks | Implementing |
| GAL-04 | P1: Ver a galeria, AC4 | Tasks | Implementing |
| GAL-05 | P1: Ver a galeria, AC5 | Tasks | Implementing |
| GAL-06 | P1: Ver a galeria, AC6 | Tasks | Implementing |
| GAL-07 | P1: Ver a galeria, AC7 | Tasks | Implementing |
| GAL-08 | P1: Ver a galeria, AC8 | Tasks | Implementing |
| GAL-09 | P1: Adicionar fotos, AC1 | Tasks | Implementing |
| GAL-10 | P1: Adicionar fotos, AC2 | Tasks | Implementing |
| GAL-11 | P1: Adicionar fotos, AC3 | Tasks | Implementing |
| GAL-12 | P1: Adicionar fotos, AC4 | Tasks | Implementing |
| GAL-13 | P1: Adicionar fotos, AC5 | Tasks | Implementing |
| GAL-14 | P1: Adicionar fotos, AC6 | Tasks | Implementing |
| GAL-15 | P1: Adicionar fotos, AC7 | Tasks | Implementing |
| GAL-16 | P1: Adicionar fotos, AC8 | Tasks | Implementing |
| GAL-17 | P1: Adicionar fotos, AC9 | Tasks | Implementing |
| GAL-18 | P1: Adicionar fotos, AC10 | Tasks | Implementing |
| GAL-19 | P1: Adicionar fotos, AC11 | Tasks | Implementing |
| GAL-20 | P1: Adicionar fotos, AC12 | Tasks | Pending |
| GAL-21 | P1: Adicionar fotos, AC13 | Tasks | Pending |
| GAL-22 | P1: Adicionar fotos, AC14 | Tasks | Pending |
| GAL-23 | P1: Adicionar fotos, AC15 | Tasks | Pending |
| GAL-24 | P1: Adicionar fotos, AC16 | Tasks | Pending |
| GAL-25 | P1: Adicionar fotos, AC17 | Tasks | Implementing |
| GAL-26 | P1: Adicionar fotos, AC18 | Tasks | Pending |
| GAL-27 | P1: Adicionar fotos, AC19 | Tasks | Pending |
| GAL-28 | P1: Adicionar fotos, AC20 | Tasks | Pending |
| GAL-29 | P1: Adicionar fotos, AC21 | Tasks | Pending |
| GAL-30 | P1: Adicionar fotos, AC22 | Tasks | Pending |
| GAL-31 | P1: Remover fotos, AC1 | Tasks | Implementing |
| GAL-32 | P1: Remover fotos, AC2 | Tasks | Implementing |
| GAL-33 | P1: Remover fotos, AC3 | Tasks | Implementing |
| GAL-34 | P1: Remover fotos, AC4 | Tasks | Implementing |
| GAL-35 | P1: Remover fotos, AC5 | Tasks | Pending |
| GAL-36 | P1: Remover fotos, AC6 | Tasks | Implementing |
| GAL-37 | P1: Remover fotos, AC7 | Tasks | Pending |
| GAL-38 | P1: Remover fotos, AC8 | Tasks | Pending |
| GAL-39 | P1: Ciclo de vida, AC1 | Tasks | Implementing |
| GAL-40 | P1: Ciclo de vida, AC2 | Tasks | Implementing |
| GAL-41 | P2: Contrato, AC1 | Tasks | Implementing |
| GAL-42 | P2: Contrato, AC2 | Tasks | Implementing |
| GAL-43 | P2: Contrato, AC3 | Tasks | Implementing |
| GAL-44 | P2: Seed, AC1 | Tasks | Implementing |
| GAL-45 | P2: Seed, AC2 | Tasks | Implementing |
| GAL-46 | P2: Seed, AC3 | Tasks | Implementing |
| GAL-47 | Edge Cases | Tasks | Implementing |
| GAL-48 | Edge Cases | Tasks | Implementing |
| GAL-49 | Edge Cases | Tasks | Pending |
| GAL-50 | Edge Cases | Tasks | Pending |
| GAL-51 | Edge Cases | Tasks | Pending |

**ID format:** `GAL-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 51 total, 51 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] UAT manual no web e no Android, como cabeleireiro (com uma conta nova, já que o banco de dev não ganha fotos do seed): adicionar várias fotos de uma vez, ver o contador, chegar ao limite, remover uma foto e conferir o bucket. Como cliente: ver a faixa no perfil público e abrir uma foto em tela cheia.
- [ ] A suíte do backend passa com os 837 testes da baseline (`git grep -c "def test_"` em `2948100`) mais os novos, sem nenhum teste removido.
- [ ] Cada critério de backend (GAL-01 a GAL-05, GAL-09 a GAL-19, GAL-31 a GAL-34, GAL-39 a GAL-45, GAL-47 e GAL-48) tem pelo menos um teste automatizado que falha se o comportamento for removido.
- [ ] `cd frontend-mobile && npx tsc --noEmit` não ganha nenhum erro novo.
