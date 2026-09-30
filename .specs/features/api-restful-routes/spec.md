# Rotas da API em RFC 3986 e convenção REST Specification

**Issue:** [#163](https://github.com/rodrigoscorrea/Hairmatch/issues/163) · [Task][Refactor] Padronização das URLs de APIs para RFCs adequadas
**Escopo:** Large. São 49 rotas, os `urls.py` de 8 apps, 11 serviços do app e o webhook externo do chatbot.
**Plataformas:** backend Django e app (`frontend-mobile`, web e Android).
**Depende de:** `api-problem-details`, que precisa estar em `develop` antes. Rota antiga e método errado respondem em problem+json (PD-60, PD-66).

## Problem Statement

A issue #161 pede para avaliar as rotas da API contra a RFC 3986 e redesenhá-las quando for possível sem mudar as regras de negócio. Hoje as rotas misturam três problemas.

**Verbos no path:** `create`, `list`, `update`, `remove`, `register`, `assign/cookie` e `unassign`.

**Hierarquia invertida ou quebrada:**
- `service/hairdresser/<id>` (os serviços de um profissional).
- `preferences/list/users/<id>`.
- `user/<email>` e `customer/home/<email>`, com e-mail no path e sem percent-encoding no app.

**Método HTTP errado:**
- POST para remover preferência.
- POST com corpo para uma consulta de horários.
- PUT fazendo update parcial.

Há também duplicatas: a exclusão de conta existe em `DELETE user/authenticated` e em `DELETE user/<email>`. E o singular e o plural variam entre apps (`reserve`, `service`, `hairdresser`).

## Goals

- [ ] Toda rota sob `/api/` segue a Route Table deste spec: substantivo no plural, sem verbo no path, hierarquia pai/filho no path e filtro na query.
- [ ] Toda rota nova tem a mesma regra de negócio, autenticação, validação e corpo de sucesso da rota antiga, exceto as mudanças listadas na Route Table.
- [ ] O app usa só as rotas novas, e a troca é um corte único no mesmo release.
- [ ] A avaliação contra a RFC 3986 fica registrada, separando o que a RFC exige do que é convenção REST.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Prefixo de versão (`/api/v1/`) | Decisão do usuário: corte único sem versionamento. O app é o único cliente da API REST. |
| Aliases das rotas antigas | Decisão do usuário: corte único. As rotas antigas passam a responder 404. |
| `/admin/` do Django | Não faz parte da API. |
| Formato de erro e status | Coberto pela `api-problem-details`. |
| Troca de envelopes de sucesso (`data`, `available_slots` etc.) | Mudaria todos os hooks. A única exceção é a busca (RT-55), porque hoje ela quebra o app. |
| Renomear os apps Django (`reserve`, `service`) e os modelos | O nome do recurso na URL não precisa ser o do código. Renomear app mexe em migrations. |
| Paginação, filtros novos e HATEOAS | Não pedidos. Nenhuma rota ganha comportamento novo. |
| Validar a assinatura do webhook do chatbot | Achado de segurança separado (F9 da auditoria). |

---

## Avaliação RFC 3986

A RFC 3986 define a **sintaxe** de URI. Ela não define nomes de recurso, plural nem métodos HTTP. Métodos e status vêm da RFC 9110. Plural, kebab-case e ausência de verbo são convenção REST.

| Regra | Fonte | Situação hoje | Ação |
| ----- | ----- | ------------- | ---- |
| Caracteres válidos em segmento (`pchar`: unreserved, pct-encoded, sub-delims, `:` e `@`) | RFC 3986 §3.3 | Todas as rotas são sintaticamente válidas. `@` e `+` do e-mail são permitidos em segmento. | Nenhuma correção de sintaxe é obrigatória. |
| Percent-encoding de dado variável no path | RFC 3986 §2.1 e §2.4 | O app monta `customer/home/${email}` sem `encodeURIComponent`. Um e-mail com `/`, `?`, `#` ou `%` (válidos pela RFC 5322) quebra o path. | Tirar o e-mail do path. A identidade vem da sessão (`/me`). |
| Path hierárquico, do geral para o específico | RFC 3986 §3.3 | `service/hairdresser/<id>` e `preferences/list/users/<id>` invertem a hierarquia. | Filhos sob o pai: `/hairdressers/{id}/services`, `/preferences/{id}/users`. |
| Dado não hierárquico na query | RFC 3986 §3.4 | A busca já usa `?search=`. A consulta de horários manda `service` e `date` no corpo de um POST. | Filtros na query: `?q=`, `?service=&date=`. |
| Path diferencia maiúsculas | RFC 3986 §6.2.2.1 | Todas as rotas são minúsculas. | Manter minúsculas. |
| Métodos seguros e idempotentes | RFC 9110 §9.2 | POST para ler horários e para remover preferência. PUT fazendo update parcial. | GET para leitura, DELETE para remoção, PATCH para update parcial. |
| Substantivo no plural, sem verbo, kebab-case, sem barra final | Convenção REST | Há verbos e singular, e `gemini_completion` usa underscore. | Aplicar a convenção em toda a tabela. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Estratégia de migração | Corte único: backend e app no mesmo release. As rotas antigas somem. | Escolha do usuário. | y |
| Versionamento | Nenhum prefixo `/v1`. | Consequência do corte único. O app é o único cliente. | y |
| Rotas de sessão | `login`, `logout`, `refresh` e `google` ficam em `/api/auth/*`. São "controllers" de sessão, aceitos pela convenção REST, e não recursos. | Mantém o `AUTH_EXCLUDED` estável e não força um recurso `sessions` artificial. | n |
| Cadastro | `POST /api/users` substitui `POST /api/auth/register`. Os dois modos (e-mail e `google_signup_token`) continuam no mesmo endpoint. | Cadastro é a criação do recurso usuário. O AD-001/AD-004 manda o cadastro Google terminar nesse endpoint, e ele continua sendo um só. | n |
| `GET /api/auth/user` | Vira `GET /api/auth/session` e continua 200 `{"authenticated": bool}`. | O recurso é o estado da sessão, não o usuário. O bootstrap do app depende do 200. | n |
| Rotas `user/<email>` | `GET` e `DELETE /api/user/<email>` são removidas sem substituta própria. `/api/users/me` cobre os dois usos. | Só o dono do e-mail pode usá-las, o que é exatamente `/me`. O app não as chama. Mantê-las exigiria percent-encoding no path. | n (confirmar a remoção) |
| Home do cliente | `GET /api/customers/me/home` substitui `customer/home/<email>`. `GET /api/home` substitui a variante pública `customer/home`. | Tira o e-mail do path e separa a home personalizada da pública, como hoje. | n |
| Sugestão de descrição por IA | `POST /api/hairdressers/description-drafts`. Continua anônima e com throttle de 10/h. | É chamada no cadastro, antes de o profissional existir, então não pode ficar sob `/hairdressers/{id}`. `description-drafts` é o substantivo do que o endpoint gera. | n |
| CEP | `GET /api/postal-codes/{cep}`. O `{cep}` continua aceitando o que aceita hoje: qualquer texto, normalizado para 8 dígitos em `cep_lookup.py`. `69000-000` e `69000000` funcionam. | O hífen é `unreserved` na RFC 3986. Mudar a validação alteraria a regra de negócio. | n |
| Parâmetro da busca | `GET /api/search?q=`. `search` deixa de ser aceito. | `q` é a convenção para busca livre. Sem aliases (corte único). | n |
| Atribuir e remover preferência | `PUT` e `DELETE /api/users/me/preferences/{id}`, os dois com 204. Repetir o PUT ou o DELETE dá o mesmo resultado. | A relação usuário-preferência é um recurso. PUT e DELETE são idempotentes pela RFC 9110, e o `add`/`remove` do M2M do Django já é. | n |
| Update da conta | `PATCH /api/users/me`, com o mesmo corpo parcial do PUT de hoje. | O PUT atual já faz update parcial. | n |
| Update unitário de disponibilidade | `PATCH /api/availabilities/{id}`, com o mesmo corpo parcial de hoje. | Mesmo motivo. | n |
| Update em lote de disponibilidade | `PUT /api/hairdressers/{id}/availabilities` substitui a coleção inteira, como hoje (apaga e recria). | É a semântica de PUT sobre a coleção. | n |
| Serviço e avaliação | Continuam PUT, sem PATCH. | As views exigem o corpo completo (`name`, `price`, `duration`; `rating`). | n |
| Erro de query string | Um item de `errors` que se refere a query string usa `{"parameter": "<nome>", "detail": "..."}` em vez de `pointer`, conforme o PD-07 da `api-problem-details`. | A RFC 9457 usa `pointer` para o corpo. O mesmo JSON Pointer não vale para a query. | n |
| Troca do webhook em produção | Não é requisito de código. Reconfigurar a URL na instância da Evolution API é passo operacional e exige autorização explícita antes do deploy em produção. | Nenhum código consegue provar que um deploy esperou uma aprovação. A regra de blast radius da skill já cobre esse passo. | n |
| Webhook do chatbot | `POST /api/chatbot/webhook` substitui `/api/chatbot/test`. Reconfigurar a URL do webhook na instância da Evolution API é passo operacional e exige autorização explícita. | `test` não descreve o recurso. A URL do webhook fica fora do repositório, na configuração da Evolution API. | n |
| Nome do recurso de reserva | `reservations`. O app Django continua `reserve`. | "reserves" não é o substantivo usual em inglês. | n |
| Nome do recurso de agenda | `agenda` (substantivo coletivo), com itens em `/api/agenda/{id}`. | É o nome do domínio no app e no backend. `agenda-entries` não acrescenta clareza. | n |
| Testes do app | Só teste manual. O gate do app é `npx tsc --noEmit` mais o roteiro de UAT. | O app não tem testes. Decisão herdada. | y (herdado) |

**Open questions:** none. Todas foram resolvidas ou registradas acima. A remoção de `user/<email>` é uma assunção que o usuário pode reverter na confirmação.

---

## Route Table

`{id}` é inteiro. Todas as rotas ficam sob `/api/`, em minúsculas e sem barra final.

**Nota de ordenação:** `me` é literal. Rotas `/users/me/...` precedem ou não colidem com `/users/{id}/...`, porque o conversor `int` não casa com `me`.

| ID | Método e rota nova | Rota antiga | Auth | Mudança além do path |
| -- | ------------------ | ----------- | ---- | -------------------- |
| RT-01 | `POST /api/users` | `POST /api/auth/register` | nenhuma ou `google_signup_token` | - |
| RT-02 | `GET /api/auth/session` | `GET /api/auth/user` | opcional | - |
| RT-03 | `POST /api/auth/login` | igual | nenhuma | nenhuma |
| RT-04 | `POST /api/auth/logout` | igual | nenhuma | nenhuma |
| RT-05 | `POST /api/auth/refresh` | igual | cookie de refresh | nenhuma |
| RT-06 | `POST /api/auth/google` | igual | nenhuma | nenhuma |
| RT-07 | `PUT /api/users/me/password` | `PUT /api/auth/change-password` | sessão | - |
| RT-08 | `GET /api/users/me` | `GET /api/user/authenticated` | sessão | - |
| RT-09 | `PATCH /api/users/me` | `PUT /api/user/authenticated` | sessão | PUT → PATCH |
| RT-10 | `DELETE /api/users/me` | `DELETE /api/user/authenticated` | sessão | - |
| RT-11 | (removida) | `GET` e `DELETE /api/user/<email>` | - | coberta por RT-08 e RT-10 |
| RT-12 | `GET /api/search?q=` | `GET /api/user/search?search=` | nenhuma | `search` → `q`; envelope sempre `{"data": [...]}` (RT-55) |
| RT-13 | `GET /api/customers/me/home` | `GET /api/customer/home/<email>` | cliente | e-mail sai do path |
| RT-14 | `GET /api/home` | `GET /api/customer/home` | nenhuma | - |
| RT-15 | `GET /api/hairdressers/{id}` | `GET /api/hairdresser/<id>` | nenhuma | - |
| RT-16 | `POST /api/hairdressers/description-drafts` | `POST /api/hairdresser/gemini_completion` | nenhuma, throttle 10/h | - |
| RT-17 | `GET /api/postal-codes/{cep}` | `GET /api/address/cep/<cep>` | nenhuma, throttle 30/min | - |
| RT-18 | `GET /api/preferences` | `GET /api/preferences/list` | nenhuma | - |
| RT-19 | `GET /api/users/{id}/preferences` | `GET /api/preferences/list/<users>` | nenhuma | - |
| RT-20 | `GET /api/preferences/{id}/users` | `GET /api/preferences/list/users/<id>` | sessão | - |
| RT-21 | `PUT /api/users/me/preferences/{id}` | `POST /api/preferences/assign/cookie/<id>` | sessão | POST → PUT; sucesso 204 |
| RT-22 | `DELETE /api/users/me/preferences/{id}` | `POST /api/preferences/unassign/<id>` | sessão | POST → DELETE; sucesso 204 |
| RT-23 | `POST /api/reviews` | `POST /api/review/register` | cliente | - |
| RT-24 | `GET /api/hairdressers/{id}/reviews` | `GET /api/review/list/<id>` | nenhuma | - |
| RT-25 | `PUT /api/reviews/{id}` | `PUT /api/review/update/<id>` | cliente | - |
| RT-26 | `DELETE /api/reviews/{id}` | `DELETE /api/review/remove/<id>` | cliente | - |
| RT-27 | `POST /api/availabilities` | `POST /api/availability/create` | profissional | - |
| RT-28 | `POST /api/hairdressers/{id}/availabilities` | `POST /api/availability/create/multiple/<id>` | profissional dono | - |
| RT-29 | `PUT /api/hairdressers/{id}/availabilities` | `PUT /api/availability/update/multiple/<id>` | profissional dono | - |
| RT-30 | `GET /api/hairdressers/{id}/availabilities` | `GET /api/availability/list/<id>` | nenhuma | - |
| RT-31 | `PATCH /api/availabilities/{id}` | `PUT /api/availability/update/<id>` | profissional dono | PUT → PATCH |
| RT-32 | `DELETE /api/availabilities/{id}` | `DELETE /api/availability/remove/<id>` | profissional dono | - |
| RT-33 | `POST /api/agenda` | `POST /api/agenda/create` | profissional | - |
| RT-34 | `GET /api/agenda` | `GET /api/agenda/list` | profissional | - |
| RT-35 | `GET /api/hairdressers/{id}/agenda` | `GET /api/agenda/list/<id>` | profissional dono | - |
| RT-36 | `DELETE /api/agenda/{id}` | `DELETE /api/agenda/remove/<id>` | profissional dono | - |
| RT-37 | `POST /api/services` | `POST /api/service/create` | profissional | - |
| RT-38 | `GET /api/services` | `GET /api/service/list` | nenhuma | - |
| RT-39 | `GET /api/services/{id}` | `GET /api/service/list/<id>` | nenhuma | - |
| RT-40 | `GET /api/hairdressers/{id}/services` | `GET /api/service/hairdresser/<id>` | nenhuma | - |
| RT-41 | `PUT /api/services/{id}` | `PUT /api/service/update/<id>` | profissional dono | - |
| RT-42 | `DELETE /api/services/{id}` | `DELETE /api/service/remove/<id>` | profissional dono | - |
| RT-43 | `GET /api/reservations/{id}` | `GET /api/reserve/<id>` | parte da reserva | - |
| RT-44 | `POST /api/reservations` | `POST /api/reserve/create` | cliente | - |
| RT-45 | `GET /api/reservations` | `GET /api/reserve/list` | cliente | - |
| RT-46 | `GET /api/customers/{id}/reservations` | `GET /api/reserve/list/<id>` | cliente dono | - |
| RT-47 | `DELETE /api/reservations/{id}` | `DELETE /api/reserve/remove/<id>` | parte da reserva | - |
| RT-48 | `GET /api/hairdressers/{id}/available-slots?service=&date=` | `POST /api/reserve/slots/<id>` com corpo `{service, date}` | nenhuma | POST → GET; corpo → query |
| RT-49 | `POST /api/chatbot/webhook` | `POST /api/chatbot/test` | nenhuma (como hoje) | - |

---

## User Stories

### P1: Rotas da API no padrão da tabela ⭐ MVP

**User Story**: Como dev que consome a API, quero rotas previsíveis, com recursos no plural, hierarquia no path e métodos HTTP corretos, para descobrir e usar os endpoints sem ler o código.

**Why P1**: É o pedido de rotas da issue.

**Acceptance Criteria**:

1. The backend SHALL expor sob `/api/` exatamente as rotas e os métodos da Route Table (RT-01 a RT-49), sem nenhuma outra rota de API. **(RT-50)**
2. WHEN um cliente chama uma rota da Route Table THEN o backend SHALL aplicar a mesma autenticação, validação, status e corpo de sucesso da rota antiga correspondente, exceto as mudanças da coluna "Mudança além do path". **(RT-51)**
3. WHEN um cliente chama um path antigo que não está na Route Table como "igual" THEN o backend SHALL responder 404 `not-found` em problem+json. **(RT-52)**
4. WHEN um cliente chama uma rota da Route Table com um método que ela não lista THEN o backend SHALL responder 405 `method-not-allowed`, com o header `Allow` listando os métodos daquele path. **(RT-53)**
5. The backend SHALL usar em todo path novo só letras minúsculas, dígitos, `-` e `/`, sem barra final, com coleções no plural e sem verbo. As exceções são os singulares da Route Table (`agenda`, `home`, `search`, `me`, `password`, `session`, `chatbot`, `webhook`) e os controllers de sessão em `/api/auth/` (`login`, `logout`, `refresh`, `google`). **(RT-54)**

**Independent Test**: a suíte do backend chama cada rota da tabela e confere status e corpo. `GET /api/service/list` responde 404 `not-found`, e `POST /api/services/1` responde 405.

---

### P1: Conta e sessão ⭐ MVP

**User Story**: Como usuário logado, quero gerenciar minha conta por `/api/users/me` para que minha identidade venha da sessão, não de um e-mail na URL.

**Why P1**: Tira o e-mail do path (RFC 3986 §2.1) e elimina a exclusão de conta duplicada.

**Acceptance Criteria**:

1. WHEN `POST /api/users` recebe um cadastro por e-mail ou por `google_signup_token` THEN o backend SHALL criar a conta como o `POST /api/auth/register` faz hoje, com os mesmos status (201, 400, 401, 409, 429, 500 e 503) e cookies. **(RT-56)**
2. WHEN `GET /api/auth/session` é chamado com ou sem sessão THEN o backend SHALL responder 200 `{"authenticated": true|false}` e SHALL nunca responder 401. **(RT-57)**
3. WHEN `PATCH /api/users/me` recebe um subconjunto dos campos da conta THEN o backend SHALL atualizar só esses campos, como o `PUT /api/user/authenticated` faz hoje. **(RT-58)**
4. WHEN `GET /api/customers/me/home` é chamado por um cliente THEN o backend SHALL responder o mesmo corpo de `GET /api/customer/home/<email-do-cliente>` de hoje. **(RT-59)**
5. WHEN `PUT /api/users/me/preferences/{id}` é chamado uma ou mais vezes para a mesma preferência THEN o backend SHALL deixar a preferência atribuída uma única vez e responder 204. **(RT-60)**
6. WHEN `DELETE /api/users/me/preferences/{id}` é chamado, com a preferência atribuída ou não THEN o backend SHALL deixá-la não atribuída e responder 204. **(RT-61)**
7. IF a preferência de RT-60 ou RT-61 não existe THEN o backend SHALL responder 404 `not-found`. **(RT-62)**

**Independent Test**: logar, chamar `PATCH /api/users/me` com `{"first_name": "Ana"}` e ver só o nome alterado. Chamar `GET /api/auth/session` sem cookie e ver 200 `{"authenticated": false}`.

---

### P1: Consultas por query string ⭐ MVP

**User Story**: Como cliente do app, quero buscar e consultar horários por GET com query string para que as leituras sejam seguras, cacheáveis e reenviáveis.

**Why P1**: A consulta de horários hoje é um POST, e a busca tem um envelope inconsistente que quebra o app quando vem vazia.

**Acceptance Criteria**:

1. WHEN `GET /api/hairdressers/{id}/available-slots?service=<id>&date=YYYY-MM-DD` é chamado THEN o backend SHALL responder 200 `{"available_slots": [...]}` com os mesmos horários que o `POST /api/reserve/slots/<id>` devolve hoje para o mesmo serviço e data. **(RT-63)**
2. IF `service` ou `date` falta na query, ou `date` não está em `YYYY-MM-DD` THEN o backend SHALL responder 400 `validation-error`, com um item em `errors` no formato `{"parameter": "<nome>", "detail": "..."}` para cada parâmetro com problema. **(RT-64)**
3. WHEN `GET /api/search` é chamado sem `q` ou com `q` vazio THEN o backend SHALL responder 200 `{"data": []}`. **(RT-65)**
4. WHEN `GET /api/search?q=<termo>` é chamado THEN o backend SHALL responder 200 `{"data": [...]}` com os mesmos resultados que `?search=<termo>` devolve hoje. **(RT-55)**

**Independent Test**: `GET /api/search` responde `{"data": []}`. `GET /api/hairdressers/1/available-slots?service=1` responde 400 com `errors[0].parameter == "date"`.

---

### P1: App usa as rotas novas ⭐ MVP

**User Story**: Como usuário do app, quero que todas as telas continuem funcionando depois da troca de rotas.

**Why P1**: Com o corte único, qualquer URL antiga no app quebra uma tela.

**Acceptance Criteria**:

1. The app SHALL chamar só rotas da Route Table. Uma busca pelos paths antigos em `frontend-mobile/services`, `frontend-mobile/hooks` e `frontend-mobile/app` SHALL não encontrar nenhuma ocorrência. **(RT-70)**
2. The app SHALL decidir a exclusão do refresh de sessão por comparação exata de path, sem `includes`, com a lista `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`, `/api/auth/google` e `POST /api/users`. **(RT-71)**
3. WHEN uma chamada a `/api/users/me` ou a qualquer rota `/api/users/...` responde 401 THEN o app SHALL disparar o refresh de sessão, apesar de `POST /api/users` estar excluído. **(RT-72)**
4. The app SHALL usar `POST /api/auth/refresh` nos dois pontos que hoje fazem o refresh (`services/axios-instance.ts` e `app/_layout.tsx`) a partir de uma única constante. **(RT-73)**
5. WHEN a tela de agendamento consulta horários THEN o app SHALL chamar `GET /api/hairdressers/{id}/available-slots` com `service` e `date` na query. **(RT-74)**
6. The app SHALL compilar sem erros em `npx tsc --noEmit`. **(RT-75)**

**Independent Test**: roteiro de UAT no web e no Android: login, cadastro (e-mail e Google), home, busca, perfil do profissional, agendamento, reservas, avaliação, serviços, disponibilidade, agenda e logout, todos funcionando.

---

### P2: Webhook do chatbot

**User Story**: Como operador do chatbot, quero que o webhook tenha um nome que descreva o recurso, sem perder mensagens na troca.

**Why P2**: Muda uma configuração externa, fora do repositório, com risco de perder mensagens do WhatsApp durante a troca.

**Acceptance Criteria**:

1. WHEN a Evolution API chama `POST /api/chatbot/webhook` THEN o backend SHALL processar a mensagem como o `POST /api/chatbot/test` faz hoje. **(RT-76)**
2. The README SHALL documentar a URL nova do webhook e o passo de reconfiguração da instância da Evolution API. **(RT-77)**

**Independent Test**: os testes do chatbot (`chatbot/tests.py`) passam chamando o path novo.

---

## Edge Cases

- WHEN um cliente chama uma rota nova com barra final (`/api/services/`) THEN o backend SHALL responder 404 `not-found`, sem redirecionar. **(RT-80)**
- WHEN `{id}` não é inteiro (`/api/services/abc`) THEN o backend SHALL responder 404 `not-found`. **(RT-81)**
- WHEN `GET /api/postal-codes/69000-000` é chamado THEN o backend SHALL responder como `GET /api/postal-codes/69000000`. **(RT-82)**
- IF um parâmetro de query aparece repetido (`?date=a&date=b`) THEN o backend SHALL usar o último valor, como o `QueryDict.get` do Django faz. **(RT-83)**

---

## Implicit-Requirement Dimensions

| Dimension | Resolução |
| --------- | --------- |
| Input validation & bounds | RT-64 e RT-81 a RT-83. As regras de validação das views não mudam (RT-51). |
| Failure / partial-failure states | N/A because a feature só muda path e método. As falhas continuam as da `api-problem-details`. |
| Idempotency / retry / duplicate handling | RT-60 e RT-61: PUT e DELETE da preferência são idempotentes. RT-63 e RT-65: leituras passam a GET, que é seguro para reenviar. |
| Auth boundaries & rate limits | RT-51 mantém a autenticação de cada rota. A coluna Auth da Route Table fixa a regra. Os throttles de RT-16 e RT-17 continuam os mesmos. RT-71 e RT-72 cuidam do refresh no app. |
| Concurrency / ordering | N/A because nenhuma lógica de concorrência muda. A ordem dos `urlpatterns` só importa para `me` e `{id}`, e o conversor `int` separa os dois. |
| Data lifecycle / expiry | N/A because nenhum dado é criado, migrado ou apagado pela troca de rotas. |
| Observability | N/A because os logs de erro vêm da `api-problem-details` (PD-65). Rota antiga responde 404 como qualquer rota inexistente. |
| External-dependency failure | RT-76 e RT-77: o webhook da Evolution API é a única dependência externa afetada. A troca exige autorização antes do deploy. |
| State-transition integrity | N/A because nenhuma transição de estado muda. |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| RT-01 | Route Table: conta e sessão | Execute | Done |
| RT-02 | Route Table: conta e sessão | Execute | Done |
| RT-03 | Route Table: conta e sessão | Execute | Done |
| RT-04 | Route Table: conta e sessão | Execute | Done |
| RT-05 | Route Table: conta e sessão | Execute | Done |
| RT-06 | Route Table: conta e sessão | Execute | Done |
| RT-07 | Route Table: conta e sessão | Execute | Done |
| RT-08 | Route Table: conta e sessão | Execute | Done |
| RT-09 | Route Table: conta e sessão | Execute | Done |
| RT-10 | Route Table: conta e sessão | Execute | Done |
| RT-11 | Route Table: conta e sessão | Execute | Done |
| RT-12 | Route Table: usuários | Execute | Done |
| RT-13 | Route Table: usuários | Execute | Done |
| RT-14 | Route Table: usuários | Execute | Done |
| RT-15 | Route Table: usuários | Execute | Done |
| RT-16 | Route Table: usuários | Execute | Done |
| RT-17 | Route Table: usuários | Execute | Done |
| RT-18 | Route Table: preferências | Execute | Done |
| RT-19 | Route Table: preferências | Execute | Done |
| RT-20 | Route Table: preferências | Execute | Done |
| RT-21 | Route Table: preferências | Execute | Done |
| RT-22 | Route Table: preferências | Execute | Done |
| RT-23 | Route Table: avaliações | Execute | Done |
| RT-24 | Route Table: avaliações | Execute | Done |
| RT-25 | Route Table: avaliações | Execute | Done |
| RT-26 | Route Table: avaliações | Execute | Done |
| RT-27 | Route Table: disponibilidade | Execute | Done |
| RT-28 | Route Table: disponibilidade | Execute | Done |
| RT-29 | Route Table: disponibilidade | Execute | Done |
| RT-30 | Route Table: disponibilidade | Execute | Done |
| RT-31 | Route Table: disponibilidade | Execute | Done |
| RT-32 | Route Table: disponibilidade | Execute | Done |
| RT-33 | Route Table: agenda | Execute | Done |
| RT-34 | Route Table: agenda | Execute | Done |
| RT-35 | Route Table: agenda | Execute | Done |
| RT-36 | Route Table: agenda | Execute | Done |
| RT-37 | Route Table: serviços | Execute | Done |
| RT-38 | Route Table: serviços | Execute | Done |
| RT-39 | Route Table: serviços | Execute | Done |
| RT-40 | Route Table: serviços | Execute | Done |
| RT-41 | Route Table: serviços | Execute | Done |
| RT-42 | Route Table: serviços | Execute | Done |
| RT-43 | Route Table: reservas | Execute | Done |
| RT-44 | Route Table: reservas | Execute | Done |
| RT-45 | Route Table: reservas | Execute | Done |
| RT-46 | Route Table: reservas | Execute | Done |
| RT-47 | Route Table: reservas | Execute | Done |
| RT-48 | Route Table: reservas | Execute | Done |
| RT-49 | Route Table: chatbot | Execute | Done |
| RT-50 | P1: Rotas no padrão da tabela | Execute | Done |
| RT-51 | P1: Rotas no padrão da tabela | Execute | Done |
| RT-52 | P1: Rotas no padrão da tabela | Execute | Done |
| RT-53 | P1: Rotas no padrão da tabela | Execute | Done |
| RT-54 | P1: Rotas no padrão da tabela | Execute | Done |
| RT-55 | P1: Consultas por query string | Execute | Done |
| RT-56 | P1: Conta e sessão | Execute | Done |
| RT-57 | P1: Conta e sessão | Execute | Done |
| RT-58 | P1: Conta e sessão | Execute | Done |
| RT-59 | P1: Conta e sessão | Execute | Done |
| RT-60 | P1: Conta e sessão | Execute | Done |
| RT-61 | P1: Conta e sessão | Execute | Done |
| RT-62 | P1: Conta e sessão | Execute | Done |
| RT-63 | P1: Consultas por query string | Execute | Done |
| RT-64 | P1: Consultas por query string | Execute | Done |
| RT-65 | P1: Consultas por query string | Execute | Done |
| RT-70 | P1: App usa as rotas novas | Execute | Done |
| RT-71 | P1: App usa as rotas novas | Execute | Done |
| RT-72 | P1: App usa as rotas novas | Execute | Done |
| RT-73 | P1: App usa as rotas novas | Execute | Done |
| RT-74 | P1: App usa as rotas novas | Execute | Done |
| RT-75 | P1: App usa as rotas novas | Execute | Done |
| RT-76 | P2: Webhook do chatbot | Execute | Done |
| RT-77 | P2: Webhook do chatbot | - | Pending |
| RT-80 | Edge Cases | Execute | Done |
| RT-81 | Edge Cases | Execute | Done |
| RT-82 | Edge Cases | Execute | Done |
| RT-83 | Edge Cases | Execute | Done |

**ID format:** `RT-NN`. As rotas são RT-01 a RT-49, e os comportamentos começam em RT-50. As lacunas (66-69, 78-79) separam as histórias e são intencionais.

**Coverage:** 77 total, 0 mapped to tasks, 77 unmapped ⚠️ (Tasks ainda não criado).

---

## Success Criteria

- [ ] Um teste que percorre os `urlpatterns` resolvidos sob `/api/` encontra exatamente as rotas da Route Table.
- [ ] A suíte do backend passa com todas as chamadas nos paths novos, sem nenhum teste removido nem pulado.
- [ ] `grep -rnE "/api/(user/|customer/|hairdresser/|address/|service/|reserve/|review/|availability/|agenda/(create|list|remove)|preferences/(list|assign|unassign)|auth/(register|user|change-password))" frontend-mobile/services frontend-mobile/hooks frontend-mobile/app` não encontra nada.
- [ ] O roteiro de UAT passa no web e no Android.
