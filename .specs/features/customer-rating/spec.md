# Nota do cliente dada pelo cabeleireiro Specification

**Issue:** [#104](https://github.com/rodrigoscorrea/Hairmatch/issues/104) · [Feature][Front/Back][Hairdresser] Dar nota para o cliente
**Requisito:** RF23 (`docs/requisitos-status.md`, MVP: Sim)
**Escopo:** Large (modelo novo, 2 rotas, contrato da agenda, migração de dados, 3 telas)
**Plataformas:** backend Django e app (web e Android)

## Problem Statement

O cabeleireiro não tem como registrar como foi o atendimento de um cliente:
- só existe `User.rating` (`backend/users/models.py:31`), um `PositiveSmallIntegerField` com default 5 que nenhum código recalcula;
- não há modelo, endpoint nem tela;
- o cabeleireiro nem vê o nome do cliente na agenda, porque `useAgenda` descarta o campo `customer` que o backend já manda (`frontend-mobile/hooks/hairdresserHooks/useAgenda.ts:30-35`).

A issue #104 pede quatro coisas:
- uma avaliação do cliente pelo cabeleireiro (nota e comentário opcional), vinculada à reserva;
- as rotas de criação e listagem;
- uma tela no fluxo da agenda;
- o recálculo de `User.rating` do cliente.

## Goals

- [ ] O cabeleireiro avalia o cliente pela agenda, uma única vez por reserva e só depois do fim do atendimento. O backend garante as duas regras, mesmo com duplo toque.
- [ ] A nota do cliente exibida no perfil é a média das avaliações recebidas, ou "Sem avaliações".
- [ ] Os comentários ficam visíveis só para o cliente avaliado e para o cabeleireiro que escreveu cada um. A média e o total são visíveis para qualquer cabeleireiro.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Editar ou apagar a avaliação (parte do cabeleireiro em RF29/RF30) | Decisão do usuário: a avaliação é imutável. Por isso o app pede confirmação antes de enviar, e a edição vira outra issue. |
| Recalcular a nota do **cabeleireiro** a partir das reviews dos clientes | É a lacuna de RF22, que é outra feature. O AD-010 deixa o padrão pronto para ela. |
| Validar no backend o horário da review do cliente (`CreateReview`) | Lacuna de RF22, registrada nos riscos do design. |
| Status de reserva e confirmação de serviço (RF20 e RN2) | A reserva não tem status. O fim do atendimento é derivado de `start_time + duration`. |
| Notificar o cliente de que foi avaliado | Não há canal de notificação no app. |
| Relatório de reviews (RF24) | Fora do MVP. |
| Prazo máximo para avaliar | Não foi pedido. Uma reserva antiga pode ser avaliada a qualquer momento. |
| Mostrar a nota do cliente fora da agenda (busca, reserva) | O cabeleireiro só vê clientes pela agenda. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Quando o cabeleireiro pode avaliar | Quando `now >= reserve.start_time + service.duration`, comparando instantes UTC no backend. | O usuário escolheu "fim do atendimento". A comparação de instantes não depende do fuso do salão, que é o problema do spike #160. | y |
| Fonte da verdade do fim do atendimento | O servidor usa a `duration` **atual** do serviço. O botão do app usa o `end_time` gravado no item da agenda. Se os dois divergirem porque a duração foi editada depois da reserva, vale o servidor, e o app mostra o 409. | `Reserve` não tem FK para `Agenda` nem `end_time` próprio, e o item da agenda pode ter sido apagado. A duração atual é o único dado que o servidor sempre tem. Editar a duração de um serviço com reservas é raro, e o pior caso é o botão aparecer alguns minutos antes. | n |
| Quem vê o quê | A média e o total de avaliações de um cliente são visíveis para qualquer cabeleireiro. A lista com comentários vai para o próprio cliente (inteira) e para o cabeleireiro autor (só as dele). | O usuário escolheu média pública e comentários restritos. | y |
| Cliente sem avaliação | `User.rating = null` e o app mostra "Sem avaliações". A migração põe `null` em todos os clientes atuais. | O usuário escolheu "Sem avaliações". O 5 atual é fictício, porque nenhuma avaliação existia. | y |
| Editar ou apagar | Fora do escopo. A avaliação é imutável. | Escolha do usuário. | y |
| Tipo do campo `User.rating` | `FloatField(null=True, blank=True, default=5)`. A média é gravada com 2 casas. | O inteiro trunca a média (4,33 vira 4). Um `Decimal` sai como string no `JsonResponse` e no DRF e quebra o `toFixed` do app. O default 5 continua valendo para cabeleireiro. | n |
| Nota inteira | `rating` é inteiro de 1 a 5. 4.5, `"5"`, `true` e 0 dão 400. | A UI usa estrelas inteiras. A review do cliente continua aceitando float, e isso não muda. | n |
| Tamanho do comentário | Até 500 caracteres depois de tirar os espaços das pontas. Vazio ou só espaços é gravado como `null`. | É o bastante para um relato curto e limita o abuso. A tela mostra o contador. | n |
| Duplicado | 409 `review-exists`, o slug que já existe ("Esta reserva já foi avaliada."). | O significado é o mesmo, e o app já tem o texto. | n |
| Atendimento não terminado | Slug novo `service-not-finished` (409, "Service not finished"), com o texto "O atendimento ainda não terminou." | Nenhum slug do catálogo cobre o caso. É 409 porque o pedido é válido, mas o estado da reserva ainda não permite. | n |
| Reserva cancelada ou apagada depois de avaliada | A FK `reservation` é `OneToOne`, `null=True` e `on_delete=SET_NULL`. A avaliação e a média ficam. | `RemoveReserve` não tem trava de horário, e qualquer parte pode apagar uma reserva passada. Com `CASCADE`, cancelar a reserva apagaria uma nota ruim. | n |
| Conta do cabeleireiro autor apagada | A FK `hairdresser` usa `SET_NULL`. A avaliação e a média ficam, e o app mostra "Cabeleireiro removido". | A nota é sobre o cliente. Ela não deixa de valer porque o autor saiu. | n |
| Conta do cliente apagada | A FK `customer` usa `CASCADE`. As avaliações vão junto. | Não sobra média para mostrar, e o dado é pessoal. | n |
| `{id}` de `GET /api/customers/{id}/ratings` | `Customer.id`, igual a `GET /api/customers/{id}/reservations` (`reserve/views.py:149-155`) e ao `customer.id` da agenda. | Mantém o contrato existente. | n |
| Ordem da lista | Mais recentes primeiro (`created_at` desc, `id` desc). | É o que interessa a quem lê. | n |
| Testes do app | Só manual. O gate é `npx tsc --noEmit` + UAT. O `expo lint` fica fora porque não há configuração de eslint versionada. Revisar o gate quando ela entrar. | O app não tem testes automatizados. A decisão é herdada do #106, do #139 e do #141. | y (herdado) |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## User Stories

### P1: Cabeleireiro avalia o cliente pela API ⭐ MVP

**User Story**: Como cabeleireiro, quero registrar uma nota de 1 a 5 e um comentário sobre o cliente de uma reserva atendida, para que outros cabeleireiros saibam como ele se comporta.

**Why P1**: É o núcleo de RF23.

**Acceptance Criteria**:
1. WHEN um cabeleireiro autenticado envia `POST /api/customer-ratings` com `{reservation, rating, comment}` válidos, para uma reserva de um serviço dele cujo atendimento já terminou, THEN o backend SHALL criar um `CustomerRating` com a reserva, o cliente e o cabeleireiro dela. Ele SHALL responder 201 com `{data: {id, reservation, rating, comment, created_at}}`. **(CRT-01)**
2. The backend SHALL considerar terminado o atendimento quando `now >= reserve.start_time + service.duration` minutos. A comparação é entre instantes. No instante exato do fim, a avaliação já é aceita. **(CRT-02)**
3. IF `now < start_time + duration` THEN o backend SHALL responder 409 `service-not-finished` e não SHALL criar nenhuma linha. **(CRT-03)**
4. IF `reserve.start_time` é nulo THEN o backend SHALL responder 409 `service-not-finished`. **(CRT-04)**
5. IF a reserva já tem um `CustomerRating` THEN o backend SHALL responder 409 `review-exists` e não SHALL alterar a avaliação existente nem `User.rating`. **(CRT-05)**
6. WHEN duas requisições avaliam a mesma reserva ao mesmo tempo, de modo que a checagem prévia passa nas duas, THEN a constraint única do banco SHALL deixar só uma avaliação. A outra requisição SHALL receber 409 `review-exists`, e nunca 500. **(CRT-06)**
7. IF a reserva é de um serviço de outro cabeleireiro THEN o backend SHALL responder 403 `forbidden`. **(CRT-07)**
8. IF a reserva não existe THEN o backend SHALL responder 404 `not-found`. **(CRT-08)**
9. IF não há sessão válida THEN o backend SHALL responder 401 `invalid-session`. **(CRT-09)**
10. IF a sessão é de um cliente THEN o backend SHALL responder 403 `hairdresser-required`. **(CRT-10)**

**Independent Test**: com o Django `APIClient`, logar como cabeleireiro e criar uma reserva com `start_time` no passado. O POST devolve 201, e um segundo POST devolve 409. Uma reserva futura devolve 409 `service-not-finished`.

---

### P1: Entrada da avaliação validada ⭐ MVP

**User Story**: Como dono do sistema, quero que só notas e comentários bem formados sejam gravados, para que a média não seja corrompida.

**Why P1**: A média é pública. Uma nota fora da faixa distorce a reputação do cliente.

**Acceptance Criteria**:
1. IF `rating` está ausente, não é um inteiro JSON (por exemplo 4.5, `"5"` ou `true`) ou está fora de 1 a 5 THEN o backend SHALL responder 400 `validation-error` com um item `{pointer: "#/rating"}`. **(CRT-11)**
2. IF `reservation` está ausente ou não é um id inteiro THEN o backend SHALL responder 400 `validation-error` com um item `{pointer: "#/reservation"}`. **(CRT-12)**
3. IF `comment` não é string nem `null`, ou tem mais de 500 caracteres depois do trim, THEN o backend SHALL responder 400 `validation-error` com um item `{pointer: "#/comment"}`. **(CRT-13)**
4. WHEN `comment` está ausente, é `null` ou só tem espaços THEN o backend SHALL gravar `comment = null`. Nos outros casos, SHALL gravar o texto sem os espaços das pontas. **(CRT-14)**
5. WHEN mais de um campo é inválido THEN o backend SHALL devolver um item de `errors` por campo na mesma resposta 400. **(CRT-15)**
6. IF o corpo não é um objeto JSON THEN o backend SHALL responder 400 `malformed-request`. **(CRT-16)**
7. The backend SHALL validar a entrada (CRT-11 a CRT-16) antes de buscar a reserva. Uma entrada inválida nunca responde 404, 403 nem 409. **(CRT-17)**

**Independent Test**: um POST para cada valor inválido devolve 400 com o `pointer` certo e nenhuma linha nova.

---

### P1: A nota do cliente é a média das avaliações ⭐ MVP

**User Story**: Como cliente, quero que a nota no meu perfil reflita as avaliações que recebi, e não um 5 fixo.

**Why P1**: É o segundo critério de aceite da issue.

**Acceptance Criteria**:
1. WHEN um `CustomerRating` é criado THEN o backend SHALL gravar em `User.rating` do cliente a média aritmética de todas as avaliações dele, arredondada para 2 casas. Por exemplo, notas 5, 4 e 4 dão 4.33. **(CRT-18)**
2. The backend SHALL criar a avaliação e recalcular a média numa transação só, com a linha `User` do cliente travada (`select_for_update`) antes do insert. Assim, duas avaliações simultâneas de cabeleireiros diferentes para o mesmo cliente entram as duas na média final. **(CRT-19)**
3. WHILE um cliente não tem nenhuma avaliação, the backend SHALL manter `User.rating = null`. **(CRT-20)**
4. WHEN uma conta de cliente é criada, por e-mail/senha ou pelo Google, THEN o backend SHALL gravar `User.rating = null`. Uma conta de cabeleireiro continua sendo criada com 5. **(CRT-21)**
5. WHEN a migração da feature roda THEN ela SHALL pôr `null` em `rating` de todo `User` que tem perfil `Customer`, selecionado pela relação e não pela string de `role`. Todo cabeleireiro SHALL manter o valor numérico que tinha. **(CRT-22)**
6. The backend SHALL serializar `User.rating` como número JSON ou `null`, nunca como string, em `GET /api/users/me` e nas outras respostas que o incluem. **(CRT-23)**
7. WHEN a reserva de uma avaliação é apagada, por cancelamento ou pela exclusão de conta, THEN a avaliação SHALL continuar existindo com `reservation = null`, e `User.rating` do cliente não SHALL mudar. **(CRT-24)**
8. WHEN o cabeleireiro autor de uma avaliação apaga a conta THEN a avaliação SHALL continuar existindo com `hairdresser = null`, e `User.rating` do cliente não SHALL mudar. **(CRT-25)**
9. WHEN o cliente apaga a conta THEN as avaliações recebidas por ele SHALL ser apagadas junto. **(CRT-26)**
10. IF um `PATCH /api/users/me` envia `rating` THEN o backend SHALL ignorar o campo, como já faz (`users/views.py:710`). **(CRT-27)**

**Independent Test**: criar três avaliações (5, 4, 4) para o mesmo cliente e conferir que `GET /api/users/me` do cliente devolve `rating: 4.33`. Um cliente recém-cadastrado tem `rating: null`.

---

### P1: Listar as avaliações de um cliente ⭐ MVP

**User Story**: Como cliente, quero ver as avaliações que recebi. Como cabeleireiro, quero ver a média do cliente e as avaliações que eu mesmo dei.

**Why P1**: A issue pede a rota de listagem, e o perfil do cliente depende dela.

**Acceptance Criteria**:
1. WHEN um cliente chama `GET /api/customers/{id}/ratings` com o próprio `Customer.id` THEN o backend SHALL responder 200 com `{data: {average, count, ratings}}`, em que `ratings` tem todas as avaliações dele, das mais recentes para as mais antigas. **(CRT-28)**
2. WHEN um cabeleireiro chama `GET /api/customers/{id}/ratings` THEN o backend SHALL responder 200 com `average` e `count` calculados sobre todas as avaliações do cliente. Em `ratings`, SHALL incluir só as que esse cabeleireiro escreveu. **(CRT-29)**
3. IF um cliente pede as avaliações de outro cliente THEN o backend SHALL responder 403 `forbidden`. **(CRT-30)**
4. IF o `Customer` não existe THEN o backend SHALL responder 404 `not-found`. **(CRT-31)**
5. IF não há sessão válida THEN o backend SHALL responder 401 `invalid-session`. **(CRT-32)**
6. The backend SHALL devolver cada item como `{id, rating, comment, created_at, service_name, hairdresser_name}`. `service_name` é `null` quando a reserva foi apagada, e `hairdresser_name` (nome e sobrenome) é `null` quando a conta do autor foi apagada. **(CRT-33)**
7. WHILE o cliente não tem avaliações, the backend SHALL responder `{average: null, count: 0, ratings: []}`. **(CRT-34)**
8. The backend SHALL devolver `average` igual ao `User.rating` gravado do cliente. **(CRT-35)**

**Independent Test**: com duas avaliações de cabeleireiros diferentes, o cliente vê 2 itens, cada cabeleireiro vê `count: 2` e 1 item, e outro cliente recebe 403.

---

### P1: Agenda expõe a reserva e a avaliação ⭐ MVP

**User Story**: Como cabeleireiro, quero que cada agendamento da agenda diga qual é a reserva, quem é o cliente e se já o avaliei, para avaliar a partir dali.

**Why P1**: Sem o id da reserva, o app não tem o que mandar no POST. Hoje a agenda só expõe o id da `Agenda`.

**Acceptance Criteria**:
1. WHEN um cabeleireiro lista a agenda (`GET /api/agenda` ou `GET /api/hairdressers/{id}/agenda`) THEN cada item com reserva SHALL trazer, além dos campos atuais: **(CRT-36)**
   - `reservation_id`;
   - `customer: {id, user: {first_name, last_name, rating}, ratings_count}`;
   - `customer_rating`, que é `{rating, comment}` da avaliação desta reserva, ou `null`.
2. WHEN um item da agenda não tem reserva THEN ele SHALL trazer `reservation_id: null`, `customer: null` e `customer_rating: null`. **(CRT-37)**
3. The backend SHALL montar a lista da agenda com um número de queries que não cresce com o número de itens. Um teste com 1 e com 5 reservas mede o mesmo número com `assertNumQueries`. **(CRT-38)**

**Independent Test**: a resposta da agenda de um cabeleireiro com uma reserva avaliada e outra não avaliada traz `customer_rating` preenchido só na primeira.

---

### P1: Cabeleireiro avalia pelo app ⭐ MVP

**User Story**: Como cabeleireiro, quero abrir um agendamento já atendido na agenda e avaliar o cliente em poucos toques.

**Why P1**: A issue pede a tela no fluxo da agenda.

**Acceptance Criteria**:
1. WHEN o cabeleireiro toca num agendamento com reserva THEN o modal "Detalhes do Agendamento" SHALL mostrar o nome e o sobrenome do cliente, além do serviço, da data e do horário. **(CRT-39)**
2. WHEN o agendamento tem reserva, `now >= end_time` (relógio do aparelho) e `customer_rating` é `null` THEN o modal SHALL mostrar o botão "Avaliar cliente". **(CRT-40)**
3. WHILE `now < end_time`, ou o agendamento não tem reserva, the app SHALL esconder o botão "Avaliar cliente". **(CRT-41)**
4. WHEN `customer_rating` não é `null` THEN o modal SHALL mostrar "Sua avaliação: N★", em que N é a nota, e não SHALL mostrar o botão. **(CRT-42)**
5. WHEN o cabeleireiro toca em "Avaliar cliente" THEN o app SHALL abrir a tela `hairdresser/rate-customer/{reservationId}`. A tela SHALL mostrar o nome do cliente, o serviço, a data, 5 estrelas e um campo de comentário com limite de 500 caracteres e contador `n/500`. **(CRT-43)**
6. WHILE nenhuma estrela está selecionada, the app SHALL manter desabilitado o botão "Enviar avaliação". **(CRT-44)**
7. WHEN o cabeleireiro toca em "Enviar avaliação" THEN o app SHALL abrir uma confirmação com o texto "A avaliação não pode ser alterada depois de enviada." e SHALL chamar o POST só depois que ele confirmar. **(CRT-45)**
8. WHILE o POST está em andamento, the app SHALL mostrar "Enviando..." no botão e SHALL mantê-lo desabilitado. **(CRT-46)**
9. WHEN o POST responde 201 THEN o app SHALL voltar para a agenda, e o agendamento SHALL mostrar "Sua avaliação: N★" sem precisar reiniciar o app. **(CRT-47)**
10. IF o POST falha THEN o app SHALL mostrar o `ErrorModal` com o texto de `problemMessage` (por exemplo, "O atendimento ainda não terminou." ou "Esta reserva já foi avaliada.") e SHALL manter a nota e o comentário preenchidos. **(CRT-48)**
11. WHEN a aba da agenda volta a ter foco THEN o app SHALL buscar a agenda de novo. **(CRT-49)**

**Independent Test**: UAT no web e no Android. Avaliar um agendamento passado, conferir "Sua avaliação" no modal e conferir que um agendamento futuro não tem o botão.

---

### P1: Perfil do cliente mostra a média ⭐ MVP

**User Story**: Como cliente, quero ver a minha nota atual no perfil.

**Why P1**: É o critério de aceite "a nota do cliente exibida no perfil reflete a média".

**Acceptance Criteria**:
1. WHEN o perfil do cliente ganha foco THEN o app SHALL chamar `GET /api/customers/{id}/ratings` e mostrar a média com 1 casa decimal e o total entre parênteses, por exemplo "4.3 (3)". **(CRT-50)**
2. WHILE `count` é 0, the app SHALL mostrar "Sem avaliações" no lugar da nota. **(CRT-51)**
3. IF a busca falha THEN o perfil SHALL mostrar "Nota indisponível", e o resto da tela SHALL continuar funcionando. **(CRT-52)**

**Independent Test**: com um cliente avaliado com 5 e 4, o perfil mostra "4.5 (2)". Um cliente novo vê "Sem avaliações".

---

### P1: Contrato de erro e rotas ⭐ MVP

**User Story**: Como dev, quero que as rotas e o erro novos sigam o AD-006 e o AD-007.

**Why P1**: `test_routes.py` e `test_problems.py` quebram sem isso.

**Acceptance Criteria**:
1. The backend SHALL ter o slug `service-not-finished` (409, título "Service not finished") no `CATALOG` de `hairmatch/problems.py` e no catálogo do spec `api-problem-details`. O app SHALL ter o slug em `utils/api-problem.ts`, com o texto "O atendimento ainda não terminou.". **(CRT-53)**
2. The Route Table do spec `api-restful-routes` e `ROUTE_TABLE` de `hairmatch/test_routes.py` SHALL conter `RT-86 POST /api/customer-ratings` (cabeleireiro) e `RT-87 GET /api/customers/{id}/ratings` (sessão). **(CRT-54)**
3. IF outro método chega nos paths novos THEN o backend SHALL responder 405 `method-not-allowed` com o header `Allow`. **(CRT-55)**

**Independent Test**: `python manage.py test hairmatch` passa, com a contagem do catálogo em 40.

---

### P2: Cabeleireiro vê a nota do cliente na agenda

**User Story**: Como cabeleireiro, quero ver a média e o total de avaliações de um cliente antes de atendê-lo.

**Why P2**: É útil, mas a issue não pede.

**Acceptance Criteria**:
1. WHEN o modal de um agendamento com reserva abre THEN o app SHALL mostrar a nota do cliente com 1 casa decimal e o total, por exemplo "4.3 (3 avaliações)". **(CRT-56)**
2. WHILE `ratings_count` é 0, the app SHALL mostrar "Sem avaliações". **(CRT-57)**

**Independent Test**: UAT. Um cliente avaliado mostra a média no modal, e um cliente novo mostra "Sem avaliações".

---

### P2: Cliente vê as avaliações recebidas

**User Story**: Como cliente, quero ler os comentários que os cabeleireiros escreveram sobre mim.

**Why P2**: A média já cobre o critério da issue. A lista dá transparência.

**Acceptance Criteria**:
1. WHEN o cliente toca em "Avaliações recebidas" no menu do perfil THEN o app SHALL abrir uma tela que lista, para cada avaliação, as estrelas, o comentário (se houver), o serviço, a data em `DD/MM/YYYY` e o nome do cabeleireiro, ou "Cabeleireiro removido". **(CRT-58)**
2. WHILE a lista está vazia, the app SHALL mostrar "Você ainda não recebeu avaliações.". **(CRT-59)**
3. IF a busca falha THEN o app SHALL mostrar o `ErrorModal` com o texto de `problemMessage`. **(CRT-60)**

**Independent Test**: UAT. Depois de duas avaliações, a tela lista as duas, a mais recente primeiro.

---

## Edge Cases

- WHEN o POST chega no instante exato `start_time + duration` THEN o backend SHALL aceitar (CRT-02).
- IF o relógio do aparelho está adiantado e mostra o botão antes do fim real THEN o backend SHALL responder 409 `service-not-finished`, e o app SHALL mostrar o texto do slug (CRT-03, CRT-48).
- WHEN `comment` tem exatamente 500 caracteres depois do trim THEN o backend SHALL aceitar. Com 501, SHALL responder 400 (CRT-13).
- IF o cabeleireiro avalia, cancela a reserva e cria outra no mesmo horário THEN a reserva nova SHALL poder ser avaliada, porque a antiga ficou com `reservation = null` (CRT-24).
- WHEN dois cabeleireiros avaliam o mesmo cliente ao mesmo tempo THEN `User.rating` SHALL refletir as duas notas (CRT-19).
- IF o `Customer.id` da URL é de um cliente pendente (`is_active=False`) THEN o backend SHALL responder como para qualquer cliente: 403 para outro cliente e 200 com `count: 0` para cabeleireiro. Um cliente pendente não tem reserva.
- IF a tela de avaliação é recarregada no web e perde os parâmetros da rota THEN o app SHALL mostrar "Cliente" no lugar do nome, e o serviço e a data continuam vindo de `GET /api/reservations/{id}` (CRT-43).
- WHEN a média dá uma dízima (por exemplo 13/3) THEN o backend SHALL gravar 4.33, e o app SHALL mostrar 4.3.

---

## Implicit-Requirement Dimensions Sweep

| Dimension | Coverage |
| --------- | -------- |
| Input validation & bounds | CRT-11 a CRT-17: nota inteira de 1 a 5, comentário até 500 caracteres, ids inteiros, `CheckConstraint` no banco. |
| Failure / partial-failure states | CRT-19: a avaliação e o recálculo ficam na mesma transação, então não sobra avaliação sem média. CRT-48 e CRT-52 tratam falha no app. |
| Idempotency / retry / duplicate handling | CRT-05, CRT-06 e CRT-46: constraint única, 409 no duplicado e botão desabilitado durante o envio. |
| Auth boundaries & rate limits | CRT-07, CRT-09, CRT-10 e CRT-28 a CRT-32. Rate limit: N/A, porque as rotas exigem sessão e não disparam e-mail (o AD-008 vale só para rota anônima). |
| Concurrency / ordering | CRT-06 (mesma reserva) e CRT-19 (mesmo cliente, lock na linha `User`). |
| Data lifecycle / expiry | CRT-24 a CRT-26: o que acontece com a reserva, o autor e o cliente apagados. Sem expiração. |
| Observability | N/A: os erros saem por `problem_response`, e o 500 já é logado pelo `exception_handler` (AD-006). Não há métrica nova. |
| External-dependency failure | N/A: nenhuma chamada externa. |
| State-transition integrity | CRT-02 a CRT-04: só uma reserva terminada pode ser avaliada. A avaliação não tem transição depois de criada, porque é imutável. |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| CRT-01 | P1: Avaliar pela API, AC1 | Tasks | Pending |
| CRT-02 | P1: Avaliar pela API, AC2 | Tasks | Pending |
| CRT-03 | P1: Avaliar pela API, AC3 | Tasks | Pending |
| CRT-04 | P1: Avaliar pela API, AC4 | Tasks | Pending |
| CRT-05 | P1: Avaliar pela API, AC5 | Tasks | Pending |
| CRT-06 | P1: Avaliar pela API, AC6 | Tasks | Pending |
| CRT-07 | P1: Avaliar pela API, AC7 | Tasks | Pending |
| CRT-08 | P1: Avaliar pela API, AC8 | Tasks | Pending |
| CRT-09 | P1: Avaliar pela API, AC9 | Tasks | Pending |
| CRT-10 | P1: Avaliar pela API, AC10 | Tasks | Pending |
| CRT-11 | P1: Entrada validada, AC1 | Tasks | Pending |
| CRT-12 | P1: Entrada validada, AC2 | Tasks | Pending |
| CRT-13 | P1: Entrada validada, AC3 | Tasks | Pending |
| CRT-14 | P1: Entrada validada, AC4 | Tasks | Pending |
| CRT-15 | P1: Entrada validada, AC5 | Tasks | Pending |
| CRT-16 | P1: Entrada validada, AC6 | Tasks | Pending |
| CRT-17 | P1: Entrada validada, AC7 | Tasks | Pending |
| CRT-18 | P1: Média, AC1 | Tasks | Pending |
| CRT-19 | P1: Média, AC2 | Tasks | Pending |
| CRT-20 | P1: Média, AC3 | Tasks | Implementing |
| CRT-21 | P1: Média, AC4 | Tasks | Implementing |
| CRT-22 | P1: Média, AC5 | Tasks | Implementing |
| CRT-23 | P1: Média, AC6 | Tasks | Implementing |
| CRT-24 | P1: Média, AC7 | Tasks | Pending |
| CRT-25 | P1: Média, AC8 | Tasks | Pending |
| CRT-26 | P1: Média, AC9 | Tasks | Pending |
| CRT-27 | P1: Média, AC10 | Tasks | Implementing |
| CRT-28 | P1: Listar, AC1 | Tasks | Pending |
| CRT-29 | P1: Listar, AC2 | Tasks | Pending |
| CRT-30 | P1: Listar, AC3 | Tasks | Pending |
| CRT-31 | P1: Listar, AC4 | Tasks | Pending |
| CRT-32 | P1: Listar, AC5 | Tasks | Pending |
| CRT-33 | P1: Listar, AC6 | Tasks | Pending |
| CRT-34 | P1: Listar, AC7 | Tasks | Pending |
| CRT-35 | P1: Listar, AC8 | Tasks | Pending |
| CRT-36 | P1: Agenda, AC1 | Tasks | Pending |
| CRT-37 | P1: Agenda, AC2 | Tasks | Pending |
| CRT-38 | P1: Agenda, AC3 | Tasks | Pending |
| CRT-39 | P1: Avaliar pelo app, AC1 | Tasks | Pending |
| CRT-40 | P1: Avaliar pelo app, AC2 | Tasks | Pending |
| CRT-41 | P1: Avaliar pelo app, AC3 | Tasks | Pending |
| CRT-42 | P1: Avaliar pelo app, AC4 | Tasks | Pending |
| CRT-43 | P1: Avaliar pelo app, AC5 | Tasks | Pending |
| CRT-44 | P1: Avaliar pelo app, AC6 | Tasks | Pending |
| CRT-45 | P1: Avaliar pelo app, AC7 | Tasks | Pending |
| CRT-46 | P1: Avaliar pelo app, AC8 | Tasks | Pending |
| CRT-47 | P1: Avaliar pelo app, AC9 | Tasks | Pending |
| CRT-48 | P1: Avaliar pelo app, AC10 | Tasks | Pending |
| CRT-49 | P1: Avaliar pelo app, AC11 | Tasks | Pending |
| CRT-50 | P1: Perfil, AC1 | Tasks | Pending |
| CRT-51 | P1: Perfil, AC2 | Tasks | Pending |
| CRT-52 | P1: Perfil, AC3 | Tasks | Pending |
| CRT-53 | P1: Contrato, AC1 | Tasks | Pending |
| CRT-54 | P1: Contrato, AC2 | Tasks | Pending |
| CRT-55 | P1: Contrato, AC3 | Tasks | Pending |
| CRT-56 | P2: Nota na agenda, AC1 | Tasks | Pending |
| CRT-57 | P2: Nota na agenda, AC2 | Tasks | Pending |
| CRT-58 | P2: Avaliações recebidas, AC1 | Tasks | Pending |
| CRT-59 | P2: Avaliações recebidas, AC2 | Tasks | Pending |
| CRT-60 | P2: Avaliações recebidas, AC3 | Tasks | Pending |

**Coverage:** 60 total, 60 mapped to tasks, 0 unmapped.

---

## Success Criteria

- [ ] Os dois critérios de aceite da issue #104 passam no UAT do T18, no web e no Android.
- [ ] A suíte do backend passa sem perder nenhum dos 724 testes atuais, e cada CRT de backend tem pelo menos um teste.
- [ ] `docs/requisitos-status.md` marca RF23 como ✅.
