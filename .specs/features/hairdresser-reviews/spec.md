# Minhas avaliações (cabeleireiro) Specification

**Issue:** [#189](https://github.com/rodrigoscorrea/Hairmatch/issues/189) · [Feature][Front][Hairdresser] Tela de avaliações recebidas pelo cabeleireiro
**Épico:** #188 · **Depende de:** #182 (feature `push-notifications`), só para a história P2
**Escopo:** Medium. São uma tela nova, uma mudança de ordem numa rota que já existe e a troca de destino do toque em dois `kind` de alerta. Não há modelo, rota nem slug novo.
**Plataformas:** backend Django e app (web e Android)

## Problem Statement

Nenhuma tela do app mostra ao cabeleireiro as reviews que ele recebeu. O backend já as lista em `GET /api/hairdressers/{id}/reviews` (RT-24, `ListReview`, `backend/review/views.py:140`), com cliente, nota, comentário e fotos, mas o app não chama essa rota. A agenda mostra só a nota que o cabeleireiro deu ao cliente. Por isso, o alerta e o push de review criada ou editada (N11 e N12 da #182) não têm para onde levar, e a spec da #182 deixou o toque "sem navegar (#189)" (NOTIF-34 e NOTIF-63).

## Goals

- [ ] O cabeleireiro abre "Minhas avaliações" pelo perfil e vê cada review recebida com cliente, nota, data, comentário e fotos, da mais recente para a mais antiga.
- [ ] Tocar no alerta ou no push de `review-created` ou `review-updated` abre "Minhas avaliações".
- [ ] A ordem decrescente vem da própria API, e nenhuma rota nova é criada.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Nome do serviço no card | A issue não pede. A `Review` não tem FK para o serviço; ele só se acha pelo `Reserve.review`, o que mudaria o `ReviewSerializer` que outras telas usam. |
| Foto do cliente no card | A issue não pede. O `CustomerNameSerializer` só manda `id`, `first_name` e `last_name`. |
| Marca "editada" ou data da última edição | A `Review` não tem `updated_at` (`backend/review/models.py:15-20`). A marca exigiria campo novo e migração. |
| Rolar até a review do alerta ou destacá-la | Decisão do usuário: o toque abre a tela no topo. O push da #182 só leva `{alert_id, kind}`. |
| Média, total ou distribuição das notas no cabeçalho | A issue não pede. O AD-010 deixa a nota derivada do cabeleireiro para uma feature própria. |
| Responder, denunciar ou ocultar uma review | A issue não pede. |
| Toque em `review-deleted` | A issue fala em review "recebida ou editada". O alerta de exclusão segue o NOTIF-63: marca como lido e fica na caixa. |
| Paginação do `GET` | Nenhuma lista do projeto pagina. Um cabeleireiro recebe no máximo uma review por reserva. |
| Mudar a auth do RT-24 | A rota é pública (perfil público, Route Table) e continua assim. |
| Testes automatizados no app | O app não tem suíte. O gate do app é `npx tsc --noEmit` mais o UAT, como na #115, na #118 e na #120. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| O que o toque no alerta ou no push abre | A tela "Minhas avaliações" no topo, recarregada. Ela não rola até a review do alerta nem a destaca. | Escolha do usuário. A review nova já fica no topo, e o payload do push da #182 não muda. | y |
| `kind` que navegam | Só `review-created` e `review-updated`. O `review-deleted` continua só marcando como lido. | Texto da issue ("recebida ou editada"). A review excluída não está mais na lista. | n |
| Conteúdo do card | Nome e sobrenome do cliente, nota, data, comentário e fotos. Nada além disso. | É a lista da issue. Ver Out of Scope. | n |
| Formato da nota | As estrelas do `StarRating` (só leitura, cheias até a parte inteira) e, ao lado, o valor sem casa decimal quando é inteiro e com uma casa e vírgula quando não é ("4", "4,5"). | `Review.rating` é `FloatField` e aceita 4,5 pela API (`_parse_rating`). O `StarRating` não tem meia estrela, então o número evita esconder a fração. O formato é o mesmo do texto do push da #182. | n |
| Data mostrada | `created_at` em `DD/MM/YYYY`, no fuso do aparelho, como "Avaliações recebidas" (`customer/ratings.tsx`). Uma review editada mostra a data de criação. | A `Review` não tem `updated_at`. | n |
| Onde a ordem é decidida | No backend: o `ListReview` passa de `order_by('id')` para `order_by('-created_at', '-id')`. As fotos de cada review continuam por `id` crescente (`ReviewPicture.Meta.ordering`). | Uma só ordem para todo consumidor da RT-24, como o `CustomerRatingsByCustomer` (`backend/review/views.py:396`). Hoje nenhuma tela chama a rota, então ninguém depende da ordem antiga. O `test_list_reviews` (`backend/review/tests.py:602`), que afirma a ordem crescente, muda junto com a spec. | n |
| Rota usada pelo app | A RT-24 que já existe, com o `userInfo.hairdresser.id` da sessão. Não há `GET /api/hairdressers/me/reviews`. | Os dados já são públicos. Uma rota nova obrigaria a mexer na Route Table e no `test_routes.py` sem ganho. | n |
| Comentário vazio | Um comentário `null`, `""` ou só com espaços não ocupa espaço no card. | O `CreateReview` grava `''` quando o campo não vem (`backend/review/views.py:82`). | n |
| Fotos | Miniaturas na ordem da API (0 a 5 por review, AD-011). Um toque abre a foto em tela cheia, com o botão "Fechar foto". O visualizador é o mesmo da galeria (#118). | É o padrão de foto já usado no app (`components/gallery/GalleryStrip.tsx`). | n |
| Botão "‹ Voltar" | Volta à tela anterior da pilha do perfil (o perfil ou a caixa de alertas da #182, que fica em `hairdresser/profile/notifications`). A pilha do perfil declara `index` como rota inicial, então uma entrada direta pelo push sempre tem o perfil por baixo. | Num toque com o app fechado, a tela entra sem histórico na pilha do perfil. Com a rota inicial declarada, `router.back()` cai no perfil, sem ramo especial no código. O comportamento do expo-router 57 com `initialRouteName` numa pilha dentro de abas não foi conferido na documentação, e o UAT (T8, passo 6) o prova. | n |
| Falha ao carregar | `ErrorModal` com o texto do slug (`problemMessage`) e o fallback "Não foi possível carregar suas avaliações.". A mensagem de lista vazia não aparece. | O mesmo padrão de "Avaliações recebidas" e "Favoritos". | n |
| Texto de lista vazia | "Você ainda não recebeu avaliações." | É o texto de "Avaliações recebidas" do cliente. | n |
| Sequência com a #182 | As histórias P1 não dependem da #182 e podem ser entregues antes. A P2 só começa com a #182 mesclada na `develop`, e uma task da P2 emenda a spec e as tasks da #182 (o catálogo, o NOTIF-34, o NOTIF-63 e o T16). | O `alertRoute` e o tratamento do toque só existem depois da #182. | n |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## User Stories

### P1: Lista de avaliações recebidas ⭐ MVP

**User Story**: Como cabeleireiro, quero ver as avaliações que os clientes me deram, da mais recente para a mais antiga, para saber o que acharam do meu trabalho.

**Why P1**: É o primeiro critério de aceite da issue.

**Acceptance Criteria**:

1. **HRV-01** WHEN alguém chama `GET /api/hairdressers/{id}/reviews` THEN o backend SHALL responder 200 `{"data": [...]}` com as reviews do cabeleireiro `{id}` ordenadas por `created_at` decrescente.
2. **HRV-02** WHEN duas reviews do mesmo cabeleireiro têm o mesmo `created_at` THEN o `GET` SHALL listar primeiro a de maior `id`.
3. The backend SHALL manter cada item no formato atual: `{"id", "rating", "comment", "created_at", "customer": {"id", "user": {"id", "first_name", "last_name"}}, "hairdresser", "pictures": [{"id", "url"}]}`, com as fotos por `id` crescente. **(HRV-03)**
4. The `GET` SHALL trazer só as reviews do cabeleireiro `{id}`, e nunca as de outro cabeleireiro. **(HRV-04)**
5. **HRV-05** WHEN o cliente edita uma review (`PUT /api/reviews/{id}`) THEN o `GET` SHALL manter essa review na posição dada pelo `created_at` original.
6. **HRV-06** WHEN a tela "Minhas avaliações" ganha o foco THEN o app SHALL chamar o `GET` com o `id` do `Hairdresser` da sessão e mostrar um card por review, na ordem da API.
7. The tela SHALL mostrar o título "Minhas avaliações" e o botão "‹ Voltar". **(HRV-07)**
8. The card SHALL mostrar o nome e o sobrenome do cliente (`customer.user.first_name` e `last_name`). **(HRV-08)**
9. The card SHALL mostrar a nota com o `StarRating` só de leitura e, ao lado, o valor sem casa decimal quando é inteiro e com uma casa e vírgula quando não é ("4", "4,5"). **(HRV-09)**
10. The card SHALL mostrar o `created_at` no formato `DD/MM/YYYY`. **(HRV-10)**
11. **HRV-11** WHERE a review tem um comentário com algum caractere além de espaço o card SHALL mostrar o comentário.
12. **HRV-12** IF o comentário é `null`, `""` ou só espaços THEN o card SHALL não mostrar área de comentário.
13. **HRV-13** WHERE a review tem fotos o card SHALL mostrar uma miniatura por foto, na ordem da API.
14. **HRV-14** WHEN o cabeleireiro toca numa miniatura THEN o app SHALL abrir a foto em tela cheia, com um botão de fechar cujo `accessibilityLabel` é "Fechar foto".
15. **HRV-15** WHEN o `GET` responde `{"data": []}` THEN a tela SHALL mostrar "Você ainda não recebeu avaliações.".
16. **HRV-16** IF o `GET` da tela falha THEN o app SHALL mostrar o texto do slug (`problemMessage`, fallback "Não foi possível carregar suas avaliações.") num `ErrorModal` e SHALL não mostrar a mensagem de lista vazia.
17. **HRV-17** WHEN o cabeleireiro toca em "‹ Voltar" THEN o app SHALL voltar à tela anterior da pilha do perfil.
18. **HRV-18** IF a tela abriu sem uma tela anterior na pilha do perfil (por exemplo, pelo toque num push com o app fechado) THEN "‹ Voltar" SHALL abrir o perfil do cabeleireiro (`/(app)/hairdresser/profile`).

**Independent Test**: no web, como cabeleireiro do seed com duas reviews, uma delas com comentário e duas fotos, abrir `/(app)/hairdresser/profile/reviews`. A review mais recente aparece primeiro, com o nome do cliente, as estrelas, o valor da nota e a data. Só a review com comentário mostra o texto. O toque numa miniatura abre a foto em tela cheia. Um cabeleireiro sem reviews vê "Você ainda não recebeu avaliações.".

---

### P1: Acesso pelo perfil ⭐ MVP

**User Story**: Como cabeleireiro, quero chegar às minhas avaliações a partir do meu perfil.

**Why P1**: A issue pede o acesso pelo perfil. Sem ele, a tela só abriria por URL.

**Acceptance Criteria**:

1. The perfil do cabeleireiro (`hairdresser/profile/index.tsx`) SHALL mostrar o card "Minhas avaliações" logo abaixo do card "Minha galeria", com o mesmo estilo e a mesma seta. **(HRV-19)**
2. **HRV-20** WHEN o cabeleireiro toca no card "Minhas avaliações" THEN o app SHALL abrir `/(app)/hairdresser/profile/reviews`.
3. **HRV-21** WHEN o cabeleireiro abre "Minhas avaliações" pelo perfil e toca em "‹ Voltar" THEN o app SHALL voltar ao perfil.

**Independent Test**: no web, como cabeleireiro, abrir o perfil, tocar em "Minhas avaliações" e depois em "‹ Voltar". A tela abre e o perfil volta.

---

### P2: Toque no alerta ou no push de review

**User Story**: Como cabeleireiro, quero que o aviso de uma review nova ou editada me leve às minhas avaliações, para ler a review sem procurar.

**Why P2**: Depende da #182, que ainda não está na `develop`. A tela vale sozinha sem ele.

**Acceptance Criteria**:

1. **HRV-22** WHEN o cabeleireiro toca num alerta `review-created` na caixa de alertas THEN o app SHALL marcar o alerta como lido (NOTIF-34) e SHALL abrir "Minhas avaliações".
2. **HRV-23** WHEN o cabeleireiro toca num alerta `review-updated` na caixa de alertas THEN o app SHALL marcar o alerta como lido (NOTIF-63) e SHALL abrir "Minhas avaliações".
3. **HRV-24** WHEN o cabeleireiro toca num push `review-created` ou `review-updated`, com o app aberto, em segundo plano ou fechado, e o `PATCH` do alerta responde 200 THEN o app SHALL abrir "Minhas avaliações".
4. **HRV-25** WHEN "Minhas avaliações" abre por um toque em alerta ou push THEN o app SHALL mostrar a lista desde o topo e SHALL trazer a review do alerta, se ela ainda existir, numa chamada nova ao `GET`.
5. **HRV-26** WHEN o cabeleireiro toca num alerta ou push `review-deleted` THEN o app SHALL marcar o alerta como lido e SHALL manter a caixa de alertas aberta, sem abrir "Minhas avaliações".
6. The app SHALL manter os destinos do toque dos outros `kind` do catálogo da #182 (`reservation-created` e `customer-rating-*`). **(HRV-27)**

**Independent Test**: num dev build Android com a #182 ativa, como cliente, avaliar um atendimento. O cabeleireiro recebe "Nova avaliação". Com o app fechado, o toque no push abre "Minhas avaliações" com a review nova no topo, e "‹ Voltar" leva ao perfil. Na caixa de alertas, o toque em "Avaliação atualizada" abre a mesma tela, e o toque em "Avaliação removida" fica na caixa.

---

## Edge Cases

- **HRV-28** WHEN a review é excluída enquanto a tela está aberta THEN o próximo foco da tela SHALL deixar de mostrar essa review.
- **HRV-29** WHEN uma review tem 5 fotos THEN o card SHALL mostrar as 5 miniaturas numa faixa com rolagem horizontal, sem cortar o card.
- **HRV-30** WHILE o `userInfo.hairdresser` ainda não está carregado o app SHALL não chamar o `GET`.

---

## Implicit-Requirement Dimensions

| Dimension | Coverage |
| --------- | -------- |
| Input validation & bounds | O único dado de entrada é o `{id}` inteiro do path, que a rota já trata (`<int:hairdresser_id>`). As fotos vão de 0 a 5 por review (HRV-29). |
| Failure / partial-failure states | HRV-16. A rota é só de leitura, sem estado parcial. |
| Idempotency / retry / duplicate handling | N/A because a rota é um `GET` sem efeito, e o recarregamento no foco (HRV-06) é seguro. |
| Auth boundaries & rate limits | A RT-24 continua pública, como hoje. A tela fica no grupo `hairdresser`, cujo layout redireciona o cliente. Throttle: N/A because a rota não envia e-mail nem valida segredo (AD-008). |
| Concurrency / ordering | A ordem da lista é a do HRV-01 e do HRV-02, e uma edição não a muda (HRV-05). Uma review criada ou apagada durante a leitura aparece no próximo foco (HRV-06, HRV-28). |
| Data lifecycle / expiry | N/A because a feature não grava nada. Apagar a conta do cliente apaga as reviews dele (`CASCADE`), e elas somem da lista. |
| Observability | N/A because a feature não muda o tratamento de erro. Um erro inesperado já cai no 500 `internal-error` logado do AD-006. |
| External-dependency failure | As fotos vêm do S3 por URL. Uma foto que não carrega fica com a miniatura vazia e não quebra o card. O `GET` não chama serviço externo. |
| State-transition integrity | N/A because a feature não muda estado. O alerta é marcado como lido pelas regras da #182 (HRV-22, HRV-23 e HRV-26). |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| HRV-01 | P1: Lista de avaliações | Tasks | Pending |
| HRV-02 | P1: Lista de avaliações | Tasks | Pending |
| HRV-03 | P1: Lista de avaliações | Tasks | Pending |
| HRV-04 | P1: Lista de avaliações | Tasks | Pending |
| HRV-05 | P1: Lista de avaliações | Tasks | Pending |
| HRV-06 | P1: Lista de avaliações | Tasks | Pending |
| HRV-07 | P1: Lista de avaliações | Tasks | Pending |
| HRV-08 | P1: Lista de avaliações | Tasks | Pending |
| HRV-09 | P1: Lista de avaliações | Tasks | Pending |
| HRV-10 | P1: Lista de avaliações | Tasks | Pending |
| HRV-11 | P1: Lista de avaliações | Tasks | Pending |
| HRV-12 | P1: Lista de avaliações | Tasks | Pending |
| HRV-13 | P1: Lista de avaliações | Tasks | Pending |
| HRV-14 | P1: Lista de avaliações | Tasks | Pending |
| HRV-15 | P1: Lista de avaliações | Tasks | Pending |
| HRV-16 | P1: Lista de avaliações | Tasks | Pending |
| HRV-17 | P1: Lista de avaliações | Tasks | Pending |
| HRV-18 | P1: Lista de avaliações | Tasks | Pending |
| HRV-19 | P1: Acesso pelo perfil | Tasks | Pending |
| HRV-20 | P1: Acesso pelo perfil | Tasks | Pending |
| HRV-21 | P1: Acesso pelo perfil | Tasks | Pending |
| HRV-22 | P2: Toque no alerta ou no push | Tasks | Pending |
| HRV-23 | P2: Toque no alerta ou no push | Tasks | Pending |
| HRV-24 | P2: Toque no alerta ou no push | Tasks | Pending |
| HRV-25 | P2: Toque no alerta ou no push | Tasks | Pending |
| HRV-26 | P2: Toque no alerta ou no push | Tasks | Pending |
| HRV-27 | P2: Toque no alerta ou no push | Tasks | Pending |
| HRV-28 | Edge Cases | Tasks | Pending |
| HRV-29 | Edge Cases | Tasks | Pending |
| HRV-30 | Edge Cases | Tasks | Pending |

**ID format:** `HRV-NN`. O prefixo `REV-` é da feature `review-editing`.

**Coverage:** 30 total, 30 mapped to tasks, 0 unmapped.

---

## Success Criteria

- [ ] Os dois critérios de aceite da issue passam no web e no Android. O cabeleireiro vê as reviews com cliente, nota, data, comentário e fotos, e o toque no alerta ou no push de review recebida ou editada abre a tela.
- [ ] Os critérios de backend (HRV-01 a HRV-05) têm teste automatizado, e a suíte do backend passa sem perder nenhum teste da baseline.
- [ ] O `test_routes.py` não muda, porque nenhuma rota entra nem sai.
- [ ] `npx tsc --noEmit` não ganha erro novo.
