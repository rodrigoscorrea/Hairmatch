# Cabeleireiros favoritos Specification

**Issue:** [#115](https://github.com/rodrigoscorrea/Hairmatch/issues/115) · [Feature][Front/Back][Customer] Marcar cabeleireiro como favorito (RF25)
**Escopo:** Large (persistência, auth, idempotência, ciclo de vida dos dados, backend e app)
**Plataformas:** backend Django e app (web e Android)

## Problem Statement

O cliente não tem como guardar os cabeleireiros de que gostou. Para voltar a um profissional, ele precisa buscá-lo de novo pelo nome. O perfil do cliente já mostra o item "Favoritos" (`frontend-mobile/app/(app)/customer/profile.tsx:95-100`), mas o toque cai em `handleMenuPress`, que não faz nada (linhas 27-28). Não existe modelo, rota nem tela.

## Goals

- [ ] O cliente favorita e desfavorita um cabeleireiro pelo perfil público, e a mudança aparece no `GET /api/customers/me/favorite-hairdressers` seguinte.
- [ ] O cliente vê os favoritos na tela "Favoritos", do mais recente para o mais antigo, e desfavorita por ali sem abrir o perfil.
- [ ] Nenhum favorito sobrevive à exclusão da conta do cliente nem à do cabeleireiro.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Coração nos cards da busca e da home | Decisão do usuário: só o perfil público favorita. Esses cards usam o `PublicHairdresserSerializer`, que a busca e a home compartilham. |
| O item "Favoritos" das configurações do cabeleireiro (`hairdresser/profile/settings.tsx:80`) | Decisão do usuário: o item fica como está. Esta feature é só do cliente. |
| O cabeleireiro ver quem o favoritou, ou contagem de favoritos | A issue não pede. |
| Notificação ou recomendação a partir dos favoritos | A issue não pede. |
| Paginação do `GET` | Nenhuma lista do projeto pagina, e o total de favoritos é limitado pelo número de cabeleireiros. |
| Favoritos no seed | A issue não pede, e o seed não cria interações de cliente. |
| Testes automatizados no app | O app não tem suíte. O gate do app é `npx tsc --noEmit` mais o UAT, como na #118 e na #120. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Onde favoritar | Um coração no header do perfil público (`customer/hairdresser-reservation/[id].tsx`), à direita do voltar. | Escolha do usuário. | y |
| Tela "Favoritos" | Lista de cards como os da busca (foto, nome, nota, bairro e cidade). O toque abre o perfil, e o coração de cada card desfavorita direto, sem modal. | Escolha do usuário. Favoritar de novo desfaz a remoção, então o modal não protege nada. | y |
| Item "Favoritos" do cabeleireiro | Fica como está. | Escolha do usuário. | y |
| Ordem da lista | Do favoritado mais recente para o mais antigo (`created_at` desc, `id` desc no empate). | Escolha do usuário. | y |
| Estado inicial do coração no perfil | O app lê a lista do `GET` e confere se o `{id}` do perfil está nela. Não há rota de consulta por item. | A lista não pagina e é pequena. Uma rota a menos, e nenhum campo novo nos serializers compartilhados. | n |
| `PUT` repetido | Responde 204 e mantém uma linha só. Não muda o `created_at` do favorito existente. | Idempotência do `PUT` (RFC 9110), como o RT-21. A posição na lista não pula com um toque duplo. | n |
| `DELETE` de um cabeleireiro que existe e não é favorito | Responde 204. | Idempotência do `DELETE`, como o RT-22 e o RT-89. | n |
| Cabeleireiro que não existe | `PUT` e `DELETE` respondem 404 `not-found`. | Como o RT-21 e o RT-22, que respondem 404 para a preferência que não existe. | n |
| Cabeleireiro pendente (`is_active=False`, AD-008) | O `PUT` responde 404 `not-found`, e o `GET` não lista um favorito cujo cabeleireiro esteja inativo. O `DELETE` responde 204, como para qualquer cabeleireiro que existe. | O AD-008 tira a conta pendente de toda listagem, como a busca faz (`backend/users/views.py:897`). Uma conta pendente nunca foi favoritada, porque não aparece em listagem nem tem perfil a partir da busca. | n |
| Ordem das checagens | Primeiro a sessão (401 ou 403), depois o `{id}` (404). | Segue o `_authenticated_profile` e o `UserPreferenceView`. O `PUT` e o `DELETE` não têm corpo, então não há validação de corpo para ordenar (lição L-019). | n |
| Limite de favoritos por cliente | Nenhum. | N/A: o número de cabeleireiros já limita a lista. | n |
| Throttle | Nenhum. | N/A: as três rotas exigem sessão de cliente, e nenhuma dispara e-mail nem valida segredo (AD-008). | n |
| Coração durante a requisição | Fica desabilitado até a resposta, no perfil e em cada card. | Evita duas chamadas cruzadas de um toque duplo. | n |
| Falha ao favoritar ou desfavoritar | O coração volta ao estado anterior (no card, o card volta à lista) e o app mostra a mensagem do slug em `ErrorModal`. | O app troca o estado antes da resposta e desfaz a troca na falha. A tela usa `problemMessage` (AD-006). | n |
| Falha ao carregar a lista no perfil | O coração fica vazio e desabilitado, e o resto do perfil abre normalmente. | O estado do coração é desconhecido. Habilitar o toque poderia mandar um `PUT` para quem já é favorito, o que seria inofensivo, mas mostraria o estado errado. | n |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## User Stories

### P1: Favoritar e desfavoritar pelo perfil público ⭐ MVP

**User Story**: Como cliente, quero marcar um cabeleireiro como favorito no perfil dele, para encontrá-lo depois sem buscar de novo.

**Why P1**: É a metade "favorita/desfavorita" do critério de aceite da issue.

**Acceptance Criteria**:

1. **FAV-01** WHEN o cliente da sessão chama `PUT /api/customers/me/favorite-hairdressers/{id}` com o `{id}` de um cabeleireiro ativo que não é favorito THEN o backend SHALL gravar o favorito e responder 204 sem corpo.
2. **FAV-02** WHEN o cliente chama o `PUT` para um cabeleireiro que já é favorito dele THEN o backend SHALL responder 204, SHALL manter uma única linha para o par cliente e cabeleireiro e SHALL manter o `created_at` original.
3. The backend SHALL nunca gravar duas linhas para o mesmo par cliente e cabeleireiro, nem com dois `PUT` simultâneos. **(FAV-03)**
4. **FAV-04** IF o `{id}` do `PUT` não é de um cabeleireiro THEN o backend SHALL responder 404 `not-found` e SHALL não gravar nenhuma linha.
5. **FAV-05** IF o `{id}` do `PUT` é de um cabeleireiro com `user.is_active=False` THEN o backend SHALL responder 404 `not-found` e SHALL não gravar nenhuma linha.
6. **FAV-06** WHEN o cliente da sessão chama `DELETE /api/customers/me/favorite-hairdressers/{id}` com um cabeleireiro favorito dele THEN o backend SHALL apagar só a linha desse par e responder 204 sem corpo.
7. **FAV-07** WHEN o cliente chama o `DELETE` para um cabeleireiro que existe e não é favorito dele THEN o backend SHALL responder 204 e SHALL não apagar nenhuma linha.
8. **FAV-08** IF o `{id}` do `DELETE` não é de um cabeleireiro THEN o backend SHALL responder 404 `not-found`.
9. **FAV-09** IF o `PUT` ou o `DELETE` chega sem sessão válida THEN o backend SHALL responder 401 `invalid-session` e SHALL não mudar nenhuma linha.
10. **FAV-10** IF a sessão do `PUT` ou do `DELETE` é de um cabeleireiro THEN o backend SHALL responder 403 `customer-required` e SHALL não mudar nenhuma linha.
11. **FAV-11** WHEN o cliente desfavorita um cabeleireiro THEN o backend SHALL manter os favoritos de outros clientes para o mesmo cabeleireiro.
12. **FAV-12** WHEN o perfil público de um cabeleireiro abre THEN o app SHALL mostrar no header, à direita do voltar, o ícone `heart` preenchido se o cabeleireiro está na lista do `GET`, ou `heart-outline` se não está.
13. **FAV-13** WHEN o cliente toca no coração vazio THEN o app SHALL mostrar o coração preenchido e chamar o `PUT`.
14. **FAV-14** WHEN o cliente toca no coração preenchido THEN o app SHALL mostrar o coração vazio e chamar o `DELETE`.
15. **FAV-15** IF o `PUT` ou o `DELETE` do perfil falha THEN o app SHALL voltar o coração ao estado anterior e SHALL mostrar o texto do slug (`problemMessage`, fallback "Não foi possível atualizar seus favoritos.") num `ErrorModal`.
16. **FAV-16** WHILE o `PUT` ou o `DELETE` do perfil está em andamento o app SHALL desabilitar o coração.
17. **FAV-17** IF o `GET` da lista falha ao abrir o perfil THEN o app SHALL mostrar o coração vazio e desabilitado e SHALL mostrar o resto do perfil normalmente.

**Independent Test**: no web, como cliente, abrir o perfil de um cabeleireiro do seed e tocar no coração. Ele fica preenchido, e `GET /api/customers/me/favorite-hairdressers` passa a trazer o cabeleireiro. Sair e voltar ao perfil mantém o coração preenchido. Um novo toque o esvazia, e o `GET` deixa de trazê-lo.

---

### P1: Lista de favoritos ⭐ MVP

**User Story**: Como cliente, quero ver meus cabeleireiros favoritos numa tela só, para chegar ao perfil deles com um toque.

**Why P1**: É a metade "vê listados em Favoritos" do critério de aceite da issue.

**Acceptance Criteria**:

1. **FAV-18** WHEN o cliente da sessão chama `GET /api/customers/me/favorite-hairdressers` THEN o backend SHALL responder 200 `{"data": [...]}` com um item por favorito dele, cada um no formato do `PublicHairdresserSerializer` (`{"id", "user", "resume"}`, sem CNPJ nem dados de contato).
2. **FAV-19** The `GET` SHALL ordenar os itens pelo momento em que foram favoritados, do mais recente para o mais antigo, e pelo `id` do favorito decrescente no empate.
3. **FAV-20** WHEN o cliente não tem favoritos THEN o `GET` SHALL responder 200 `{"data": []}`.
4. The `GET` SHALL trazer só os favoritos do cliente da sessão, e nunca os de outro cliente. **(FAV-21)**
5. **FAV-22** WHILE o cabeleireiro favorito tem `user.is_active=False` o `GET` SHALL deixar esse cabeleireiro fora da lista.
6. **FAV-23** IF o `GET` chega sem sessão válida THEN o backend SHALL responder 401 `invalid-session`.
7. **FAV-24** IF a sessão do `GET` é de um cabeleireiro THEN o backend SHALL responder 403 `customer-required`.
8. **FAV-25** WHEN o cliente toca em "Favoritos" no perfil THEN o app SHALL abrir a tela `customer/favorites`, com o título "Favoritos" e o botão "‹ Voltar", que volta ao perfil do cliente.
9. **FAV-26** WHEN a tela de favoritos ganha o foco THEN o app SHALL chamar o `GET` e mostrar um card por item, na ordem da API.
10. The card de favorito SHALL mostrar a foto do cabeleireiro (ou o placeholder de perfil, se não há foto), o nome e sobrenome, a nota com uma casa decimal e "bairro, cidade". **(FAV-27)**
11. **FAV-28** WHEN o cliente toca num card fora do coração THEN o app SHALL abrir o perfil público do cabeleireiro (`/(app)/customer/hairdresser-reservation/{id}`).
12. **FAV-29** WHEN o `GET` responde `{"data": []}` THEN a tela SHALL mostrar "Você ainda não tem cabeleireiros favoritos.".
13. **FAV-30** IF o `GET` da tela falha THEN o app SHALL mostrar o texto do slug (`problemMessage`, fallback "Não foi possível carregar seus favoritos.") num `ErrorModal` e SHALL não mostrar a mensagem de lista vazia.

**Independent Test**: no web, como cliente, favoritar dois cabeleireiros pelo perfil e abrir "Favoritos". Os dois aparecem, o último favoritado primeiro, e o toque num card abre o perfil dele. Um cliente novo vê a mensagem de lista vazia.

---

### P1: Desfavoritar pela lista ⭐ MVP

**User Story**: Como cliente, quero tirar um cabeleireiro dos favoritos direto na lista, sem abrir o perfil dele.

**Why P1**: Escolha do usuário. Completa o critério "favorita/desfavorita" a partir da tela "Favoritos".

**Acceptance Criteria**:

1. The card de favorito SHALL mostrar um botão com o ícone `heart` preenchido, separado da área que abre o perfil. **(FAV-31)**
2. **FAV-32** WHEN o cliente toca no coração de um card THEN o app SHALL tirar o card da lista na hora, sem modal de confirmação, e chamar o `DELETE` desse cabeleireiro.
3. **FAV-33** IF o `DELETE` da lista falha THEN o app SHALL devolver o card à posição que ele tinha e SHALL mostrar o texto do slug (`problemMessage`, fallback "Não foi possível atualizar seus favoritos.") num `ErrorModal`.
4. **FAV-34** WHEN o último card sai da lista THEN a tela SHALL mostrar "Você ainda não tem cabeleireiros favoritos.".
5. **FAV-35** WHILE o `DELETE` de um card está em andamento o app SHALL desabilitar os corações da lista.

**Independent Test**: no web, com dois favoritos, tocar no coração do primeiro card. Ele some na hora, e o `GET` seguinte traz só o outro. Com o backend parado, o toque faz o card voltar e o modal aparecer.

---

### P1: Ciclo de vida dos favoritos ⭐ MVP

**User Story**: Como operador do Hairmatch, quero que os favoritos saiam junto com a conta de qualquer das duas partes, para não guardar relação de quem saiu.

**Why P1**: Sem isso, a exclusão de conta (#120) falharia por chave estrangeira ou deixaria linhas soltas.

**Acceptance Criteria**:

1. **FAV-36** WHEN um cliente exclui a conta (`DELETE /api/users/me`) THEN o backend SHALL apagar todos os favoritos dele.
2. **FAV-37** WHEN um cabeleireiro exclui a conta THEN o backend SHALL apagar todos os favoritos que apontam para ele, de todos os clientes.
3. **FAV-38** WHEN o `purge_unconfirmed_users` expurga uma conta pendente (AD-008) THEN o backend SHALL apagar os favoritos ligados a ela, sem erro de chave estrangeira.
4. **FAV-43** WHEN um novo cadastro com o mesmo e-mail substitui uma conta pendente (AD-008) THEN o backend SHALL apagar os favoritos ligados à conta substituída, sem erro de chave estrangeira.

**Independent Test**: com dois clientes que favoritam o mesmo cabeleireiro, excluir a conta do cabeleireiro. As duas listas ficam vazias. Excluir a conta de um cliente com favoritos não muda a lista do outro.

---

## Edge Cases

- **FAV-39** IF o `{id}` do path não é um inteiro (por exemplo `/favorite-hairdressers/abc`) THEN o backend SHALL responder 404 `not-found` pela rota catch-all do AD-006.
- **FAV-40** WHEN o cliente favorita, desfavorita e favorita de novo o mesmo cabeleireiro THEN o `GET` SHALL listá-lo uma vez, na posição do último favorito.
- **FAV-41** WHEN o cliente volta da tela de perfil, onde desfavoritou um cabeleireiro, para a tela de favoritos THEN a lista SHALL refletir a mudança sem recarregar o app.
- IF o `PUT` usa o método errado no path da lista (por exemplo `PUT /api/customers/me/favorite-hairdressers`) THEN o backend SHALL responder 405 `method-not-allowed`, como toda rota do AD-007. **(FAV-42)**

---

## Implicit-Requirement Dimensions

| Dimension | Coverage |
| --------- | -------- |
| Input validation & bounds | O único dado de entrada é o `{id}` inteiro do path: FAV-04, FAV-05, FAV-08 e FAV-39. Não há corpo. |
| Failure / partial-failure states | No backend, uma escrita de uma linha, sem estado parcial. No app: FAV-15, FAV-17, FAV-30 e FAV-33. |
| Idempotency / retry / duplicate handling | FAV-02, FAV-03, FAV-07 e FAV-40. |
| Auth boundaries & rate limits | FAV-09, FAV-10, FAV-21, FAV-23 e FAV-24. Throttle: N/A because as rotas exigem sessão de cliente e não enviam e-mail nem validam segredo. |
| Concurrency / ordering | FAV-03 (dois `PUT` simultâneos), FAV-16 e FAV-35 (toque duplo no app). A ordem da lista é a do FAV-19. |
| Data lifecycle / expiry | FAV-36 a FAV-38 e FAV-43. Não há expiração de favorito. |
| Observability | N/A because uma escrita de uma linha sem efeito externo não precisa de log. Erros inesperados já caem no 500 `internal-error` logado do AD-006. |
| External-dependency failure | N/A because as rotas não chamam serviço externo, além da verificação de sessão, que já responde 503 `auth-unavailable` (AD-004). |
| State-transition integrity | Um favorito só existe ou não existe: FAV-01, FAV-02, FAV-06 e FAV-07. |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| FAV-01 | P1: Favoritar pelo perfil | Tasks | Implemented |
| FAV-02 | P1: Favoritar pelo perfil | Tasks | Implemented |
| FAV-03 | P1: Favoritar pelo perfil | Tasks | Implemented |
| FAV-04 | P1: Favoritar pelo perfil | Tasks | Implemented |
| FAV-05 | P1: Favoritar pelo perfil | Tasks | Implemented |
| FAV-06 | P1: Favoritar pelo perfil | Tasks | Implemented |
| FAV-07 | P1: Favoritar pelo perfil | Tasks | Implemented |
| FAV-08 | P1: Favoritar pelo perfil | Tasks | Implemented |
| FAV-09 | P1: Favoritar pelo perfil | Tasks | Implemented |
| FAV-10 | P1: Favoritar pelo perfil | Tasks | Implemented |
| FAV-11 | P1: Favoritar pelo perfil | Tasks | Implemented |
| FAV-12 | P1: Favoritar pelo perfil | Tasks | Pending |
| FAV-13 | P1: Favoritar pelo perfil | Tasks | Pending |
| FAV-14 | P1: Favoritar pelo perfil | Tasks | Pending |
| FAV-15 | P1: Favoritar pelo perfil | Tasks | Pending |
| FAV-16 | P1: Favoritar pelo perfil | Tasks | Pending |
| FAV-17 | P1: Favoritar pelo perfil | Tasks | Pending |
| FAV-18 | P1: Lista de favoritos | Tasks | Implemented |
| FAV-19 | P1: Lista de favoritos | Tasks | Implemented |
| FAV-20 | P1: Lista de favoritos | Tasks | Implemented |
| FAV-21 | P1: Lista de favoritos | Tasks | Implemented |
| FAV-22 | P1: Lista de favoritos | Tasks | Implemented |
| FAV-23 | P1: Lista de favoritos | Tasks | Implemented |
| FAV-24 | P1: Lista de favoritos | Tasks | Implemented |
| FAV-25 | P1: Lista de favoritos | Tasks | Pending |
| FAV-26 | P1: Lista de favoritos | Tasks | Pending |
| FAV-27 | P1: Lista de favoritos | Tasks | Pending |
| FAV-28 | P1: Lista de favoritos | Tasks | Pending |
| FAV-29 | P1: Lista de favoritos | Tasks | Pending |
| FAV-30 | P1: Lista de favoritos | Tasks | Pending |
| FAV-31 | P1: Desfavoritar pela lista | Tasks | Pending |
| FAV-32 | P1: Desfavoritar pela lista | Tasks | Pending |
| FAV-33 | P1: Desfavoritar pela lista | Tasks | Pending |
| FAV-34 | P1: Desfavoritar pela lista | Tasks | Pending |
| FAV-35 | P1: Desfavoritar pela lista | Tasks | Pending |
| FAV-36 | P1: Ciclo de vida | Tasks | Implemented |
| FAV-37 | P1: Ciclo de vida | Tasks | Implemented |
| FAV-38 | P1: Ciclo de vida | Tasks | Implemented |
| FAV-39 | Edge Cases | Tasks | Implemented |
| FAV-40 | Edge Cases | Tasks | Implemented |
| FAV-41 | Edge Cases | Tasks | Pending |
| FAV-42 | Edge Cases | Tasks | Implemented |
| FAV-43 | P1: Ciclo de vida | Tasks | Implemented |

**ID format:** `FAV-NN`.

**Coverage:** 43 total, 43 mapped to tasks, 0 unmapped.

---

## Success Criteria

- [ ] O critério de aceite da issue passa no web e no Android: o cliente favorita e desfavorita e vê os favoritos listados em "Favoritos".
- [ ] Todos os critérios de backend (FAV-01 a FAV-11, FAV-18 a FAV-24, FAV-36 a FAV-40, FAV-42 e FAV-43) têm teste automatizado, e a suíte do backend passa sem perder nenhum teste da baseline.
- [ ] O `test_routes.py` aceita RT-97 a RT-99, e nenhuma rota entra sem estar na Route Table.
