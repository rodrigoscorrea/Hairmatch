# Editar e excluir avaliações, com várias fotos Specification

**Issue:** [#105](https://github.com/rodrigoscorrea/Hairmatch/issues/105) · [Feature][Front/Back] Editar e excluir avaliação (tela de edição e suporte ao cabeleireiro)
**Requisito:** RF29 Editar Avaliação e RF30 Excluir Avaliação (`docs/requisitos-status.md`, MVP: Sim)
**Escopo:** Large (modelo novo, 4 rotas novas, 2 rotas alteradas, recálculo de média, 4 telas)
**Plataformas:** backend Django e app (web e Android)

## Problem Statement

Hoje o cliente não consegue editar a avaliação pelo app, e o cabeleireiro não consegue editar nem excluir a nota que deu a um cliente:
- `PUT /api/reviews/{id}` existe, mas só aceita JSON e não tem tela. O item "Editar avaliação" do menu do detalhe da reserva não faz nada (`frontend-mobile/app/(app)/customer/reserves/[id].tsx`).
- A avaliação aceita uma foto só (`Review.picture`, `backend/review/models.py:10`), gravada em `reviews/images/`. `RemoveReview` apaga a linha e deixa o arquivo no bucket.
- `CustomerRating` (#104) foi feita imutável, e o app avisa "A avaliação não pode ser alterada depois de enviada."

A #105 pede:
- a tela de edição da avaliação do cliente, com nota, comentário e foto;
- que o cabeleireiro edite e exclua as notas que deu.

O usuário também pediu que uma avaliação aceite uma ou mais fotos, gravadas no bucket de media em `reviews/<id_da_review>/`.

## Goals

- [ ] O cliente edita a nota, o comentário e as fotos da avaliação pela tela de detalhes da reserva.
- [ ] Uma avaliação tem de 0 a 5 fotos, todas em `reviews/<review_id>/` e em WebP. Nenhuma operação deixa arquivo órfão no bucket.
- [ ] O cabeleireiro edita e exclui as notas que deu, e a média do cliente (`User.rating`) acompanha cada mudança.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Recalcular `User.rating` do cabeleireiro a partir das `Review` | É a lacuna de RF22. O AD-010 deixa o cabeleireiro com o default até essa feature. |
| Prazo para editar ou excluir | Não foi pedido. A criação também não tem prazo. |
| Reordenar as fotos ou escolher uma capa | Não foi pedido. A ordem é a de envio. |
| Rota `GET /api/customer-ratings/{id}` | A tela de edição do cabeleireiro lê a nota de `GET /api/customers/{id}/ratings` (RT-87), que já devolve as notas dele. |
| Mover objetos antigos de `reviews/images/` | O usuário confirmou que não há objetos no S3 de QA e PRD e que o dev não persiste. |
| Câmera dentro do app | O fluxo atual só usa a galeria. |
| Notificar o avaliado da edição ou exclusão | Não há canal de notificação no app. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Onde guardar várias fotos | Tabela `ReviewPicture` (FK para `Review`, `WebPImageField`). Não JSONB. | A tabela cumpre o AD-003 (um `WebPImageField` por foto). Adicionar ou remover uma foto é uma linha, sem reescrever um array nem perder escrita concorrente. A FK com `CASCADE` dá integridade. A leitura custa uma query a mais por listagem com `prefetch_related`, sem N+1. | y |
| Caminho no bucket | `reviews/<review_id>/<uuid4 hex>.webp`. | O usuário pediu `reviews/<id_da_review>`. O uuid evita colisão entre fotos com o mesmo nome e o rename do storage. | y |
| Limites | No máximo 5 fotos por avaliação e 5 MB (5 × 1024 × 1024 bytes) por arquivo. O tamanho é checado antes de abrir a imagem. | Escolha do usuário. 5 MB é o limite da foto de perfil (`ProfilePictureView`). A conversão é síncrona (AD-003), então o número de fotos também limita a latência. | y |
| Dados existentes | Nenhuma migração de dados. `Review.picture` é removida. | O usuário confirmou que não há fotos de avaliação em nenhum ambiente. | y |
| Metade do cabeleireiro | Entra nesta feature e desfaz a imutabilidade decidida na #104. | O usuário confirmou que a #104 já foi entregue. | y |
| Forma das rotas de foto | Sub-recurso: `POST /api/reviews/{id}/pictures` (RT-90) e `DELETE /api/reviews/{id}/pictures/{picture_id}` (RT-91). `PUT /api/reviews/{id}` continua em JSON e não mexe em fotos. | Segue o AD-007 (filho sob o pai, método como verbo). Só `request.FILES` vira arquivo, como pediu o commit 527a69a, que tirou a foto do PUT. | n |
| Campo multipart | `pictures`, repetido uma vez por arquivo, na criação e no RT-90. O campo antigo `picture` é ignorado. | App e backend saem no mesmo release (AD-007), sem período com os dois campos. | n |
| PUT da review do cliente | Mantém o contrato atual: `rating` obrigatório, de 1 a 5, aceita float, e `comment` ausente preserva o anterior. | Já está em produção, e o app novo manda sempre os dois campos. Mudar o contrato não ajuda a #105. | n |
| PUT da nota do cabeleireiro | Substitui (AD-007): `comment` ausente, `null` ou só espaços grava `null`. Mesmas regras do POST da #104: `rating` inteiro JSON de 1 a 5, comentário até 500 caracteres. | O app manda sempre os dois campos. A semântica de PUT pede substituição. | n |
| Quem edita a nota do cabeleireiro | Só o autor. Outro cabeleireiro recebe 403 `forbidden`, como no POST da #104. Uma nota cujo autor apagou a conta (`hairdresser = null`) não é editável nem removível por ninguém. | Mantém a regra de ownership da #104. | n |
| Quem edita a review do cliente | Só o cliente dono. A review de outro cliente responde 404 `not-found`, como o PUT e o DELETE atuais. | Mantém o contrato das rotas RT-25 e RT-26. | n |
| Excluir a nota do cabeleireiro | Libera a reserva: a agenda volta a mostrar "Avaliar cliente", e um novo POST é aceito. | Excluir desfaz a avaliação. É o mesmo comportamento da `Review` do cliente hoje (`reserve.review = None`). | n |
| Falha parcial no upload | Se uma foto falha na conversão, nenhuma linha é criada, e os objetos que a mesma requisição já tinha enviado são apagados do storage antes da resposta. | Uma requisição não pode deixar órfãos no bucket. | n |
| Falha ao apagar do storage | O backend loga com traceback e responde como se tivesse apagado. O objeto fica órfão. | É o comportamento de `_delete_stored_files` desde a #120. A linha já foi removida, e falhar a requisição não traria a linha de volta. | n |
| Ordem das fotos | Por `id` crescente, que é a ordem de envio. | Não há reordenação. | n |
| Edição no app | Três passos, nesta ordem: `PUT`, os `DELETE` das fotos removidas e um `POST /pictures` com as novas. Um passo sem nada a fazer é pulado. Não é atômico. | A alternativa atômica seria um PUT multipart com lista de fotos mantidas, o que reabre o problema do commit 527a69a. A falha parcial é tratada pela tela (REV-67). | n |
| Seletor de fotos | `allowsMultipleSelection`, `selectionLimit` = 5 − (fotos mantidas + fotos novas na fila), `quality: 0.5` e sem `allowsEditing`. No web, onde `selectionLimit` não existe, o app fica com as primeiras que cabem. | No expo-image-picker 57, `allowsEditing` e `allowsMultipleSelection` são mutuamente exclusivos (`ImagePicker.types.d.ts:380`). `quality: 0.5` é o do `useProfilePicture` e deixa uma foto de celular abaixo de 5 MB. | n |
| Texto da confirmação do cabeleireiro | Criar: "Você poderá editar ou excluir a avaliação depois." Editar: "Salvar as alterações da avaliação?" | O texto da #104 ("não pode ser alterada") deixa de ser verdade. | n |
| Tela de edição do cabeleireiro | A agenda passa `customerId`, `ratingId` e `customerName` por params. A tela lê a nota em `GET /api/customers/{customerId}/ratings` e acha o item pelo `id`. | Funciona depois de um refresh no web, porque os params ficam na URL, e não põe o comentário na URL. Não exige rota nova. | n |
| Testes do app | Só manual. O gate é `npx tsc --noEmit` + `expo lint` nos arquivos tocados + UAT. | O app não tem testes automatizados. Decisão herdada do #104 e do #120. | y (herdado) |
| WEBP-03, WEBP-12 e WEBP-13 (`webp-conversion`) | REV-02 e REV-06 substituem esses ACs para as fotos de avaliação. Os testes deles são reescritos para o campo `pictures`, sem perder nenhuma asserção de WebP ou de imagem inválida. | O caminho `reviews/images/<stem>.webp` deixa de existir. | n |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## User Stories

### P1: Cliente envia várias fotos na avaliação ⭐ MVP

**User Story**: Como cliente, quero anexar até 5 fotos do resultado ao avaliar um atendimento, para mostrar o corte de mais de um ângulo.

**Why P1**: O usuário pediu, e o modelo de fotos é a base de todas as outras histórias.

**Acceptance Criteria**:
1. WHEN um cliente autenticado envia `POST /api/reviews` válido com 1 a 5 arquivos de imagem no campo multipart `pictures` THEN o backend SHALL criar a avaliação e uma `ReviewPicture` por arquivo, na ordem recebida, e SHALL responder 201. **(REV-01)**
2. The backend SHALL gravar cada foto de avaliação no storage de media com a chave `reviews/<review_id>/<32 dígitos hexadecimais>.webp` e conteúdo WebP. **(REV-02)**
3. WHEN `POST /api/reviews` chega sem nenhum arquivo em `pictures` THEN o backend SHALL criar a avaliação sem fotos. **(REV-03)**
4. IF `POST /api/reviews` traz mais de 5 arquivos em `pictures` THEN o backend SHALL responder 400 `validation-error` com um item `{pointer: "#/pictures"}`, e não SHALL criar nenhuma linha nem objeto no storage. **(REV-04)**
5. IF algum arquivo de `pictures` tem mais de 5 MB (5 × 1024 × 1024 bytes) THEN o backend SHALL responder 400 `validation-error` com um item `{pointer: "#/pictures"}`, sem abrir nenhuma imagem, e não SHALL criar nenhuma linha nem objeto no storage. **(REV-05)**
6. IF algum arquivo de `pictures` não é uma imagem decodificável THEN o backend SHALL responder 400 `invalid-image` com `detail` "The review picture is not a valid image.", não SHALL criar a avaliação, SHALL deixar a reserva sem avaliação e não SHALL deixar no storage nenhum objeto da requisição, inclusive os das fotos anteriores à inválida. **(REV-06)**
7. WHEN `POST /api/reviews` tem erros de campo e erros em `pictures` ao mesmo tempo THEN o backend SHALL devolver todos na mesma resposta 400, um item por campo. **(REV-07)**
8. WHEN `POST /api/reviews` traz um arquivo no campo antigo `picture` THEN o backend SHALL ignorá-lo e não SHALL criar foto. **(REV-08)**

**Independent Test**: com o `APIClient`, criar uma avaliação com 3 PNGs e conferir 3 linhas com chaves em `reviews/<id>/` e conteúdo WebP. Com 6 arquivos, conferir o 400 e o storage vazio.

---

### P1: Cliente adiciona e remove fotos de uma avaliação ⭐ MVP

**User Story**: Como cliente, quero trocar as fotos de uma avaliação que já enviei.

**Why P1**: A issue pede "permitir troca de foto".

**Acceptance Criteria**:
1. WHEN o cliente dono envia `POST /api/reviews/{id}/pictures` com 1 ou mais arquivos em `pictures`, e o total da avaliação fica em até 5, THEN o backend SHALL criar uma `ReviewPicture` por arquivo e SHALL responder 201 com `{data: [{id, url}]}`, que são todas as fotos da avaliação por `id` crescente. **(REV-10)**
2. IF `pictures` está ausente ou vazio THEN o backend SHALL responder 400 `validation-error` com um item `{pointer: "#/pictures"}`. **(REV-11)**
3. IF as fotos atuais mais as novas passam de 5 THEN o backend SHALL responder 400 `validation-error` com um item `{pointer: "#/pictures"}`, e não SHALL criar nenhuma foto. **(REV-12)**
4. IF algum arquivo tem mais de 5 MB THEN o backend SHALL responder 400 `validation-error` com um item `{pointer: "#/pictures"}`, sem abrir nenhuma imagem, e não SHALL criar nenhuma foto. **(REV-13)**
5. IF algum arquivo não é uma imagem decodificável THEN o backend SHALL responder 400 `invalid-image`, não SHALL criar nenhuma foto e não SHALL deixar no storage nenhum objeto da requisição. **(REV-14)**
6. WHEN duas requisições adicionam fotos à mesma avaliação ao mesmo tempo THEN o backend SHALL travar a linha da avaliação (`select_for_update`) antes de contar as fotos, e a avaliação nunca SHALL passar de 5 fotos. **(REV-15)**
7. WHEN o cliente dono envia `DELETE /api/reviews/{id}/pictures/{picture_id}` THEN o backend SHALL remover a linha, SHALL responder 204 e, depois do commit, SHALL apagar o objeto do storage. **(REV-16)**
8. IF a avaliação não existe ou é de outro cliente THEN `POST /api/reviews/{id}/pictures` e `DELETE /api/reviews/{id}/pictures/{picture_id}` SHALL responder 404 `not-found` e não SHALL alterar nada. **(REV-17)**
9. IF a foto não existe ou pertence a outra avaliação THEN `DELETE /api/reviews/{id}/pictures/{picture_id}` SHALL responder 404 `not-found` e não SHALL remover nada. **(REV-18)**
10. IF não há sessão válida THEN as duas rotas SHALL responder 401 `invalid-session`. IF a sessão é de um cabeleireiro THEN SHALL responder 403 `customer-required`. **(REV-19)**
11. WHEN o cliente dono envia `PUT /api/reviews/{id}` THEN o backend SHALL manter o contrato atual (JSON, `rating` obrigatório de 1 a 5, `comment` ausente preserva o anterior) e não SHALL alterar as fotos. **(REV-20)**

**Independent Test**: numa avaliação com 4 fotos, adicionar 1 dá 201 com 5 itens, e adicionar mais 1 dá 400. Remover uma dá 204 e apaga o objeto. Outro cliente recebe 404 nas duas rotas.

---

### P1: Nenhum arquivo de avaliação fica órfão ⭐ MVP

**User Story**: Como dono do sistema, quero que apagar uma avaliação ou uma conta apague as fotos do bucket.

**Why P1**: Hoje `RemoveReview` deixa o arquivo no bucket. Com até 5 fotos por avaliação, o vazamento cresce cinco vezes.

**Acceptance Criteria**:
1. WHEN o cliente dono apaga a avaliação (`DELETE /api/reviews/{id}`) THEN o backend SHALL remover as `ReviewPicture` dela e, depois do commit, SHALL apagar os objetos de todas as fotos no storage. **(REV-25)**
2. WHEN uma conta de cliente ou de cabeleireiro é excluída (`DELETE /api/users/me`) THEN o backend SHALL apagar, depois do commit, os objetos das fotos de todas as avaliações escritas e recebidas pela conta. **(REV-26)**
3. IF apagar um objeto do storage falha THEN o backend SHALL logar o erro com traceback e SHALL manter a resposta de sucesso. **(REV-27)**
4. IF a transação que remove uma foto, uma avaliação ou uma conta é desfeita THEN o backend não SHALL apagar nenhum objeto do storage. **(REV-28)**

**Independent Test**: com o `InMemoryStorage`, criar uma avaliação com 2 fotos, apagar a avaliação com `captureOnCommitCallbacks(execute=True)` e conferir que as 2 chaves sumiram.

---

### P1: As respostas trazem a lista de fotos ⭐ MVP

**User Story**: Como app, quero receber todas as fotos de cada avaliação para mostrá-las.

**Why P1**: Sem o contrato de leitura, as fotos novas não aparecem em lugar nenhum.

**Acceptance Criteria**:
1. The backend SHALL serializar cada avaliação com `pictures: [{id, url}]`, por `id` crescente, e sem o campo `picture`, em `GET /api/hairdressers/{id}/reviews` (RT-24), `GET /api/reservations/{id}` (RT-43), `GET /api/reservations` (RT-45) e `GET /api/customers/{id}/reservations` (RT-46). **(REV-30)**
2. The backend SHALL devolver em `url` a URL pública do objeto, a mesma que o storage gera para a foto de perfil. **(REV-31)**
3. The backend SHALL montar `GET /api/hairdressers/{id}/reviews` e `GET /api/customers/{id}/reservations` com um número de queries que não cresce com o número de avaliações nem de fotos. Um teste com 1 e com 3 avaliações (com fotos) mede o mesmo número com `assertNumQueries`. **(REV-32)**
4. WHEN uma avaliação é apagada THEN as `ReviewPicture` dela SHALL ser removidas junto (`on_delete=CASCADE`). **(REV-33)**

**Independent Test**: o detalhe de uma reserva avaliada com 2 fotos traz `review.pictures` com 2 itens `{id, url}` e não traz `review.picture`.

---

### P1: Cabeleireiro edita e exclui a nota que deu ⭐ MVP

**User Story**: Como cabeleireiro, quero corrigir ou retirar a nota que dei a um cliente.

**Why P1**: É o segundo critério de aceite da issue.

**Acceptance Criteria**:
1. WHEN o cabeleireiro autor envia `PUT /api/customer-ratings/{id}` com `{rating, comment}` válidos THEN o backend SHALL gravar a nota e o comentário e SHALL responder 200 com `{data: {id, reservation, rating, comment, created_at}}`. **(REV-40)**
2. WHEN o `comment` do PUT está ausente, é `null` ou só tem espaços THEN o backend SHALL gravar `comment = null`. Nos outros casos, SHALL gravar o texto sem os espaços das pontas. **(REV-41)**
3. IF `rating` está ausente, não é um inteiro JSON (por exemplo 4.5, `"5"` ou `true`) ou está fora de 1 a 5 THEN o PUT SHALL responder 400 `validation-error` com um item `{pointer: "#/rating"}`. **(REV-42)**
4. IF `comment` não é string nem `null`, ou tem mais de 500 caracteres depois do trim, THEN o PUT SHALL responder 400 `validation-error` com um item `{pointer: "#/comment"}`. **(REV-43)**
5. IF o corpo do PUT não é um objeto JSON THEN o backend SHALL responder 400 `malformed-request`. **(REV-44)**
6. The backend SHALL validar o corpo do PUT (REV-42 a REV-44) antes de buscar a nota. Um corpo inválido nunca responde 404 nem 403. **(REV-45)**
7. IF a nota não existe THEN `PUT` e `DELETE /api/customer-ratings/{id}` SHALL responder 404 `not-found`. **(REV-46)**
8. IF o cabeleireiro da sessão não é o autor da nota, inclusive quando o autor apagou a conta (`hairdresser = null`), THEN `PUT` e `DELETE` SHALL responder 403 `forbidden` e não SHALL alterar a nota nem `User.rating`. **(REV-47)**
9. IF não há sessão válida THEN `PUT` e `DELETE` SHALL responder 401 `invalid-session`. IF a sessão é de um cliente THEN SHALL responder 403 `hairdresser-required`. **(REV-48)**
10. WHEN o cabeleireiro autor envia `DELETE /api/customer-ratings/{id}` THEN o backend SHALL remover a nota e SHALL responder 204. **(REV-49)**
11. WHEN uma nota é editada ou removida THEN o backend SHALL gravar em `User.rating` do cliente a média aritmética das notas restantes, arredondada para 2 casas, na mesma transação e com a linha `User` do cliente travada (`select_for_update`) antes da escrita. **(REV-50)**
12. WHEN a nota removida era a única do cliente THEN o backend SHALL gravar `User.rating = null`. **(REV-51)**
13. WHEN uma nota é removida THEN a reserva dela SHALL voltar a aceitar `POST /api/customer-ratings`, que responde 201. **(REV-52)**
14. WHEN o PUT ou o DELETE muda uma nota THEN as outras notas do cliente SHALL ficar inalteradas. **(REV-53)**

**Independent Test**: com notas 5 e 3 para o mesmo cliente (média 4.0), editar a 3 para 4 dá média 4.5. Remover a 5 dá 4.0, e remover a última dá `null`. Outro cabeleireiro recebe 403.

---

### P1: Agenda e Route Table acompanham as rotas novas ⭐ MVP

**User Story**: Como app, quero saber o id da nota do cabeleireiro na agenda, para editá-la ou excluí-la.

**Why P1**: Sem o id, o app não tem o que chamar no PUT e no DELETE.

**Acceptance Criteria**:
1. WHEN o cabeleireiro lista a agenda e um item tem nota THEN `customer_rating` SHALL ser `{id, rating, comment}`. **(REV-55)**
2. The Route Table do spec `api-restful-routes` e `ROUTE_TABLE` de `backend/hairmatch/test_routes.py` SHALL conter: **(REV-56)**
   - `RT-90 POST /api/reviews/{id}/pictures` (cliente dono);
   - `RT-91 DELETE /api/reviews/{id}/pictures/{id}` (cliente dono);
   - `RT-92 PUT /api/customer-ratings/{id}` (profissional autor);
   - `RT-93 DELETE /api/customer-ratings/{id}` (profissional autor).

**Independent Test**: `hairmatch.test_routes` passa com as quatro rotas. A agenda de uma reserva avaliada traz `customer_rating.id`.

---

### P1: Cliente avalia e edita pelo app com várias fotos ⭐ MVP

**User Story**: Como cliente, quero editar pelo app a nota, o comentário e as fotos de uma avaliação.

**Why P1**: É o primeiro critério de aceite da issue.

**Acceptance Criteria**:
1. WHEN o cliente abre a tela de avaliação de uma reserva sem avaliação THEN o app SHALL mostrar o título "Avaliar Atendimento" e o formulário vazio. **(REV-60)**
2. WHEN o cliente toca em "Editar avaliação" no menu da avaliação, no detalhe da reserva, THEN o app SHALL abrir a tela de avaliação com o título "Editar Avaliação" e com as estrelas, o comentário e as fotos atuais preenchidos. **(REV-61)**
3. WHEN o cliente toca em adicionar foto THEN o app SHALL abrir a galeria com seleção múltipla, `selectionLimit` igual a 5 − (fotos mantidas + fotos novas na fila), `quality: 0.5` e sem recorte. **(REV-62)**
4. IF a galeria devolve mais fotos do que cabem (no web, onde não há `selectionLimit`) THEN o app SHALL ficar com as primeiras que cabem e SHALL mostrar "Você pode enviar até 5 fotos.". **(REV-63)**
5. WHILE fotos mantidas + fotos novas somam 5, the app SHALL esconder o botão de adicionar foto. **(REV-64)**
6. WHEN o cliente toca no "x" de uma miniatura THEN o app SHALL tirar a foto do formulário sem chamar o backend. Uma foto que já existia só é removida no envio. **(REV-65)**
7. WHEN o cliente envia uma avaliação nova THEN o app SHALL chamar `POST /api/reviews` uma vez, com todas as fotos da fila no campo `pictures`. **(REV-66)**
8. WHEN o cliente salva uma edição THEN o app SHALL chamar, nesta ordem: **(REV-67)**
   - o `PUT /api/reviews/{id}`;
   - um `DELETE /api/reviews/{id}/pictures/{picture_id}` por foto removida;
   - um `POST /api/reviews/{id}/pictures` com as fotos novas.

   O app SHALL pular o passo que não tem nada a fazer e, no fim, SHALL voltar para o detalhe da reserva.
9. IF algum passo do envio falha THEN o app SHALL: **(REV-68)**
   - mostrar o `ErrorModal` com o texto de `problemMessage`;
   - recarregar a reserva e refazer a lista de fotos existentes a partir dela;
   - manter escondidas, e na lista de remoção do próximo salvar, as fotos marcadas para remoção que ainda existem no servidor;
   - manter na fila as fotos novas que não foram enviadas;
   - manter a nota e o comentário digitados.
10. WHILE o envio está em andamento, the app SHALL mostrar "Enviando..." no botão e SHALL ignorar novos toques. **(REV-69)**
11. WHEN o detalhe da reserva mostra uma avaliação THEN o app SHALL mostrar todas as fotos dela numa linha rolável na horizontal. Sem fotos, SHALL mostrar o placeholder atual. **(REV-70)**

**Independent Test**: UAT no web e no Android. Criar uma avaliação com 3 fotos, editar removendo 1 e adicionando 2, conferir 4 fotos no detalhe e as chaves em `reviews/<id>/` no LocalStack.

---

### P1: Cabeleireiro edita e exclui pelo app ⭐ MVP

**User Story**: Como cabeleireiro, quero editar ou excluir pela agenda a nota que dei.

**Why P1**: É o segundo critério de aceite da issue, do lado do app.

**Acceptance Criteria**:
1. WHEN o modal de um agendamento com `customerRating` abre THEN o app SHALL mostrar "Sua avaliação: N★" e os botões "Editar avaliação" e "Excluir avaliação". **(REV-75)**
2. WHEN o cabeleireiro toca em "Editar avaliação" THEN o app SHALL abrir `hairdresser/rate-customer/{reservationId}` com os params `customerId`, `ratingId` e `customerName`. A tela SHALL mostrar o título "Editar Avaliação" e a nota e o comentário atuais, lidos de `GET /api/customers/{customerId}/ratings`. **(REV-76)**
3. IF a nota `ratingId` não está na resposta de `GET /api/customers/{customerId}/ratings`, ou a leitura falha, THEN a tela SHALL mostrar o `ErrorModal` com "Não foi possível carregar a avaliação." e SHALL voltar para a agenda ao fechar. **(REV-77)**
4. WHEN o cabeleireiro salva a edição e confirma "Salvar as alterações da avaliação?" THEN o app SHALL chamar `PUT /api/customer-ratings/{id}` com a nota e o comentário (vazio vira `null`) e, no 200, SHALL voltar para a agenda, que mostra a nota nova. **(REV-78)**
5. WHEN o cabeleireiro confirma o envio de uma avaliação nova THEN a confirmação SHALL dizer "Você poderá editar ou excluir a avaliação depois.". **(REV-79)**
6. WHEN o cabeleireiro toca em "Excluir avaliação" THEN o app SHALL abrir a confirmação "Excluir avaliação?". Depois de confirmar, SHALL chamar `DELETE /api/customer-ratings/{id}`, fechar o modal e buscar a agenda de novo. **(REV-80)**
7. IF o PUT ou o DELETE falha THEN o app SHALL mostrar o `ErrorModal` com o texto de `problemMessage`. A tela de edição SHALL manter a nota e o comentário digitados. **(REV-81)**

**Independent Test**: UAT no web e no Android. Editar uma nota de 5 para 3 e conferir "Sua avaliação: 3★" e a média nova do cliente. Excluir e conferir que "Avaliar cliente" volta.

---

## Edge Cases

- IF `POST /api/reviews` traz 6 arquivos THEN o backend SHALL responder 400 sem criar nada (REV-04).
- IF a 3ª de 3 fotos é inválida THEN as 2 primeiras não SHALL ficar no storage (REV-06 e REV-14).
- WHEN a avaliação já tem 5 fotos THEN o RT-90 SHALL responder 400 até que uma seja removida (REV-12).
- WHEN duas abas adicionam 3 fotos cada a uma avaliação com 0 THEN uma SHALL receber 201 e a outra 400 (REV-15).
- IF o `picture_id` é de outra avaliação do mesmo cliente THEN o RT-91 SHALL responder 404 (REV-18).
- WHEN a única nota do cliente é removida THEN `User.rating` SHALL voltar a `null`, e o app SHALL mostrar "Sem avaliações" (REV-51).
- IF a conta do autor foi apagada THEN ninguém SHALL editar nem remover a nota dele (REV-47).
- IF a edição falha no passo de `DELETE` THEN o app SHALL mostrar o estado real das fotos e manter as fotos novas na fila (REV-68).

## Implicit-Requirement Dimensions

| Dimension | Coverage |
| --------- | -------- |
| Input validation & bounds | REV-04 a REV-07, REV-11 a REV-14, REV-41 a REV-45. |
| Failure / partial-failure states | REV-06, REV-14, REV-27, REV-28, REV-68. |
| Idempotency / retry / duplicate handling | Repetir o RT-91 com a mesma foto responde 404 (REV-18). Repetir o RT-90 cria fotos de novo até o limite (REV-12): não há chave de deduplicação, porque fotos iguais são permitidas. O app evita duplo toque (REV-69). |
| Auth boundaries & rate limits | REV-17 a REV-19, REV-46 a REV-48. Rate limit: N/A, porque todas as rotas exigem sessão e nenhuma envia e-mail nem valida segredo (AD-008). |
| Concurrency / ordering | REV-15 (limite de fotos) e REV-50 (média com lock). |
| Data lifecycle / expiry | REV-25, REV-26, REV-33 e REV-52. |
| Observability | REV-27 (falha do storage logada com traceback). Nada além do log existente. |
| External-dependency failure | REV-27 e REV-28 (S3). Uma falha de upload no S3 durante a requisição vira 500 `internal-error` pelo handler do AD-006, e os objetos já enviados são apagados (REV-06). |
| State-transition integrity | REV-47 (só o autor), REV-51 (média volta a `null`) e REV-52 (a reserva volta a aceitar avaliação). |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| REV-01 | P1: Várias fotos na avaliação | Tasks | Implemented |
| REV-02 | P1: Várias fotos na avaliação | Tasks | Implemented |
| REV-03 | P1: Várias fotos na avaliação | Tasks | Implemented |
| REV-04 | P1: Várias fotos na avaliação | Tasks | Implemented |
| REV-05 | P1: Várias fotos na avaliação | Tasks | Implemented |
| REV-06 | P1: Várias fotos na avaliação | Tasks | Implemented |
| REV-07 | P1: Várias fotos na avaliação | Tasks | Implemented |
| REV-08 | P1: Várias fotos na avaliação | Tasks | Implemented |
| REV-10 | P1: Adicionar e remover fotos | Tasks | Implemented |
| REV-11 | P1: Adicionar e remover fotos | Tasks | Implemented |
| REV-12 | P1: Adicionar e remover fotos | Tasks | Implemented |
| REV-13 | P1: Adicionar e remover fotos | Tasks | Implemented |
| REV-14 | P1: Adicionar e remover fotos | Tasks | Implemented |
| REV-15 | P1: Adicionar e remover fotos | Tasks | Implemented |
| REV-16 | P1: Adicionar e remover fotos | Tasks | Implemented |
| REV-17 | P1: Adicionar e remover fotos | Tasks | Implemented |
| REV-18 | P1: Adicionar e remover fotos | Tasks | Implemented |
| REV-19 | P1: Adicionar e remover fotos | Tasks | Implemented |
| REV-20 | P1: Adicionar e remover fotos | Tasks | Implemented |
| REV-25 | P1: Nenhum arquivo órfão | Tasks | Implemented |
| REV-26 | P1: Nenhum arquivo órfão | Tasks | Implemented |
| REV-27 | P1: Nenhum arquivo órfão | Tasks | Implemented |
| REV-28 | P1: Nenhum arquivo órfão | Tasks | Implemented |
| REV-30 | P1: Lista de fotos nas respostas | Tasks | Implemented |
| REV-31 | P1: Lista de fotos nas respostas | Tasks | Implemented |
| REV-32 | P1: Lista de fotos nas respostas | Tasks | Implemented |
| REV-33 | P1: Lista de fotos nas respostas | Tasks | Implemented |
| REV-40 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-41 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-42 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-43 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-44 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-45 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-46 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-47 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-48 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-49 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-50 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-51 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-52 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-53 | P1: Cabeleireiro edita e exclui | Tasks | Implemented |
| REV-55 | P1: Agenda e Route Table | Tasks | Implemented |
| REV-56 | P1: Agenda e Route Table | Tasks | Implemented |
| REV-60 | P1: Cliente pelo app | Tasks | Implemented |
| REV-61 | P1: Cliente pelo app | Tasks | Implemented |
| REV-62 | P1: Cliente pelo app | Tasks | Implemented |
| REV-63 | P1: Cliente pelo app | Tasks | Implemented |
| REV-64 | P1: Cliente pelo app | Tasks | Implemented |
| REV-65 | P1: Cliente pelo app | Tasks | Implemented |
| REV-66 | P1: Cliente pelo app | Tasks | Implemented |
| REV-67 | P1: Cliente pelo app | Tasks | Implemented |
| REV-68 | P1: Cliente pelo app | Tasks | Implemented |
| REV-69 | P1: Cliente pelo app | Tasks | Implemented |
| REV-70 | P1: Cliente pelo app | Tasks | Implemented |
| REV-75 | P1: Cabeleireiro pelo app | Tasks | Implemented |
| REV-76 | P1: Cabeleireiro pelo app | Tasks | Implemented |
| REV-77 | P1: Cabeleireiro pelo app | Tasks | Pending |
| REV-78 | P1: Cabeleireiro pelo app | Tasks | Implemented |
| REV-79 | P1: Cabeleireiro pelo app | Tasks | Pending |
| REV-80 | P1: Cabeleireiro pelo app | Tasks | Implemented |
| REV-81 | P1: Cabeleireiro pelo app | Tasks | Implemented |

**ID format:** `REV-NN`. As lacunas na numeração separam as histórias.

**Coverage:** 61 total, 61 mapped to tasks, 0 unmapped.

---

## Success Criteria

- [ ] O cliente edita nota, comentário e fotos de uma avaliação no web e no Android, sem reiniciar o app.
- [ ] Depois de criar, editar e excluir avaliações no UAT, o bucket do LocalStack só tem objetos em `reviews/<id>/` de avaliações que existem.
- [ ] O cabeleireiro edita e exclui uma nota, e a média do cliente no perfil acompanha, chegando a "Sem avaliações" quando não sobra nenhuma.
- [ ] A suíte do backend passa com a baseline de 835 testes mais os novos, e `makemigrations --check` fica limpo.
