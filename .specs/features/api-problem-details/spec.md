# Erros da API em RFC 9457 e mensagens em inglês Specification

**Issue:** [#161](https://github.com/rodrigoscorrea/Hairmatch/issues/161) · [Task][Refactor] Padronização das respostas de APIs para RFCs adequadas
**Escopo:** Complex. Muda o contrato de erro de toda a API, o app e cerca de 80 asserts de teste.
**Plataformas:** backend Django (todos os apps sob `/api/`) e app (`frontend-mobile`, web e Android).
**Feature seguinte:** `api-restful-routes`, que trata a parte de rotas da issue (RFC 3986) e depende desta.

## Problem Statement

A API do Hairmatch não segue um formato de erro. Hoje convivem cinco formatos:
- `{"error": "..."}`, montado à mão em cada view.
- `{"detail": "..."}`, que o DRF gera nos 405, 415, 429 e erros de parse.
- `{"status": "error", "message": "..."}`, só no webhook do chatbot.
- `str(e)` vazado ao cliente, em `preferences`, `review`, `availability`, `reserve` e no cliente Gemini.
- Página HTML de 500 quando uma exceção escapa, porque `DEBUG=True` e o handler do DRF só trata `APIException`.

As mensagens também estão misturadas. Auth, usuários, CEP e imagem respondem em português, e o resto em inglês. Vários status não batem com a semântica HTTP: conflito com 400, "não encontrado" com 500, falta de permissão com 404, PUT com 201. O app pt-BR mostra `response.data.error` cru em cinco telas, então hoje o usuário vê inglês ou português conforme a rota.

A issue #161 pede o formato da RFC 9457 (Problem Details for HTTP APIs) e mensagens da API em inglês. O app passa a traduzir os erros por um catálogo próprio.

## Goals

- [ ] Todo erro sob `/api/` sai em `application/problem+json` com `type`, `title`, `status`, `detail` e `instance`, inclusive os gerados pelo DRF, por exceção não tratada e por rota inexistente.
- [ ] Todo texto que a API devolve (`title`, `detail`, mensagens de sucesso) está em inglês e nenhum `detail` carrega texto de exceção.
- [ ] O status de cada erro segue a semântica da RFC 9110 (tabela "Status corrigidos").
- [ ] O app mostra todo erro de backend em pt-BR, a partir do `type`, sem nunca exibir o `detail` em inglês.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Redesenho das rotas (RFC 3986, verbos, plural) | Fica na feature `api-restful-routes`, que depende desta. Aqui nenhum path muda. |
| Mensagens do chatbot de WhatsApp (`chatbot/views.py`, `chatbot/response_messages.py`, `chatbot/templates.py`, `chatbot/ai_utils.py`) e os textos que `reserve/views.py:create_new_reserve` devolve ao chatbot | São conversa com o usuário final no WhatsApp, em pt-BR. Não são mensagens da API. |
| Prompts do Gemini (`chatbot/prompts.py`, `hairmatch/ai_clients/gemini_client.py:59-71`) | São entrada do modelo. A saída é conteúdo do usuário, em pt-BR. |
| Dados de seed e catálogo de preferências (`populate_preferences`, `populate_hairdressers`) | São dados, não mensagens. |
| Chaves `coloracao`, `cachos`, `barbearia` e `trancas` do `customer/home` | Vêm de lookup pelo nome em português da preferência (`users/views.py:566`). Trocá-las quebra a home do app sem ganho para a issue. |
| Envelopes de sucesso (`data`, `available_slots`, `non_working_days`, `result`, `authenticated`, `status`) | A RFC 9457 trata só de erros. Trocar os envelopes muda todos os hooks do app. A inconsistência da busca fica na feature de rotas. |
| Página HTML de cada `type` (URI dereferenciável) | A RFC 9457 não exige. O catálogo deste spec é a documentação. |
| Tornar atômico o cadastro em lote de disponibilidade | Bug separado (criação parcial), não é formato de resposta. Registrado em Deferred Ideas. |
| Assinatura do webhook do chatbot e `DEBUG=True` fixo em `settings.py` | Achados de segurança fora da issue. Registrados em Deferred Ideas. |
| i18n no backend (`gettext`, `Accept-Language`) | Decisão do usuário: o backend fala só inglês e o app traduz. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Divisão da issue | Duas features. Esta cobre RFC 9457, inglês e status. `api-restful-routes` cobre rotas. | Formato de erro e tradução mexem nas mesmas linhas e nos mesmos asserts. Rotas têm outro blast radius (URLs do app, `AUTH_EXCLUDED`, webhook externo). | y |
| Como o app mostra erros | O app normaliza o problem+json em um ponto só e traduz pelo slug do `type` em um catálogo pt-BR. O `detail` nunca vai para a UI. | Escolha do usuário. O app é pt-BR, e o backend passa a falar inglês. | y |
| Status HTTP | Corrigidos nesta feature (tabela "Status corrigidos"). | Escolha do usuário. O `status` do problem precisa refletir a semântica real. | y |
| Forma do `type` | URI absoluta `https://hairmatch.app/problems/<slug>`. A base vem de uma constante em `settings.py` (`PROBLEM_TYPE_BASE_URI`), não de env var. | A RFC 9457 recomenda URI absoluta e não exige que ela seja dereferenciável. Constante fixa respeita a regra de não criar env var. | n (discrição do agente) |
| `about:blank` | Nunca é usado. Todo erro tem um slug do catálogo. | O app traduz pelo slug. `about:blank` obrigaria o app a traduzir pelo status. | n |
| `title` | Fixo por `type`, em inglês, igual ao catálogo. | A RFC 9457 diz que o `title` não deve mudar entre ocorrências do mesmo tipo. | n |
| `detail` | Frase em inglês, terminada em ponto, específica da ocorrência. Recurso ausente segue o padrão `"<Resource> not found."`. | Tira as variações de hoje (`Service not found` e `Service not found.`, `Result not found` para reserva). | n |
| `instance` | `request.path` da requisição, sem query string. | Não há ID de ocorrência persistido. O path identifica a chamada sem expor dados da query. | n |
| Extensões | Só `errors`, e só em `validation-error`. Cada item é `{"pointer": "#/<campo>", "detail": "..."}` para campo do corpo, ou `{"parameter": "<nome>", "detail": "..."}` para query string. | `pointer` é o formato do exemplo da RFC 9457 §3. Um JSON Pointer não endereça a query, então ela usa `parameter`. Hoje só as consultas de horários (`api-restful-routes`, RT-64) usam `parameter`. Nenhum outro erro precisa de dado estruturado. | n |
| Validação com vários campos ausentes | `errors` traz um item por campo ausente, não só o primeiro. | Custo baixo e é o uso que a RFC 9457 mostra. O app mostra uma mensagem só. | n |
| Troca de e-mail no `PUT /api/user/authenticated` | Continua 400, com o slug `email-change-unsupported`. | Não é conflito nem falta de permissão. Mantém o status atual. | n |
| Senha atual incorreta na troca de senha | Continua 400 (`incorrect-current-password`), não 401. | Um 401 dispara o refresh do `axiosInstance` e pode derrubar a sessão por um erro de digitação. | n |
| `GET /api/auth/user` | Continua 200 `{"authenticated": bool}`, sem problem. | O bootstrap do app depende do 200. Um 401 ali dispara o interceptor de refresh. | n |
| Mensagens de sucesso | Mantêm a chave `message`, em inglês. Os textos que já estão em inglês não mudam, exceto os DELETE, que passam a 204 sem corpo. | O app não lê `message` de sucesso (mapa do app, §4). | n |
| 204 em DELETE | Todo DELETE bem-sucedido responde 204 sem corpo. | O comentário em `review/tests.py:526` culpa o axios, mas o axios 1.9 trata 204 (`data` vazio), e nenhum hook lê o corpo do DELETE (`deleteReview` e `deleteService` ignoram). | n |
| Parse do problem+json no app | Nenhuma configuração extra. O axios 1.9 faz `JSON.parse` de qualquer corpo string (`transitional.forcedJSONParsing`, `node_modules/axios/lib/defaults/index.js:109`), e `fetch().json()` ignora o content-type. | Verificado no código instalado. | y (verificado) |
| Supersessão do AD-004 | O Design registra um AD-006 que supera o trecho do AD-004 sobre o 401 `{"error"}`. O restante do AD-004 continua valendo. | O AD-004 fixa o corpo do 401 como `{"error"}`, e este spec troca o corpo. | n |
| `DEBUG` nos testes de PD-64 e PD-66 | Esses testes rodam também com `override_settings(DEBUG=True)`. | O `DiscoverRunner` força `DEBUG=False`, mas `settings.py:28` fixa `DEBUG=True` em produção. Com `DEBUG=True`, o Django serve a própria página técnica de 404 e 500 e ignora `handler404`/`handler500`, então só um teste com `DEBUG=True` prova o comportamento de produção. |
| Testes do app | Só teste manual. O gate do app é `npx tsc --noEmit` mais o roteiro de UAT. | O app não tem testes. Decisão herdada do #106 e do #139. | y (herdado) |
| Asserts existentes | Todo assert de texto PT, de `{"error"}` ou de `Content-Type == application/json` em resposta de erro é reescrito para o outcome deste spec, na mesma tarefa da view. Os asserts citados: `users/tests.py:1613`, `users/tests.py:1804`, `service/tests.py:664`. | O outcome mudou por exigência do spec. Isso não enfraquece o teste. Nenhum assert de status ou de efeito colateral é removido. | n |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## Problem Type Catalog

Este é o contrato entre backend e app. Cada `type` é `https://hairmatch.app/problems/<slug>`. A coluna "App (pt-BR)" é o texto que o catálogo do app mostra. Ela reaproveita as mensagens em português que o backend devolve hoje.

| Slug | Status | Title (EN) | Gatilho | App (pt-BR) |
| ---- | ------ | ---------- | ------- | ----------- |
| `validation-error` | 400 | Invalid request data | Campo obrigatório ausente, formato inválido, valor fora do domínio. Leva `errors`. | Alguns dados estão inválidos. Revise e tente novamente. |
| `malformed-request` | 400 | Malformed request | Corpo que não é JSON válido ou não pode ser lido | Não foi possível processar a solicitação. Tente novamente. |
| `invalid-image` | 400 | Invalid image | `InvalidImage` na foto de perfil ou da avaliação | A imagem enviada é inválida. Escolha outra foto. |
| `invalid-postal-code` | 400 | Invalid postal code | CEP sem 8 dígitos | CEP inválido. Informe 8 dígitos. |
| `password-policy` | 400 | Password does not meet the policy | Senha recusada pela política do Cognito | A senha deve ter ao menos 8 caracteres, com letra maiúscula, letra minúscula e número. |
| `incorrect-current-password` | 400 | Incorrect current password | Senha atual errada na troca de senha | Senha atual incorreta. |
| `email-change-unsupported` | 400 | Email change not supported | `email` diferente no update da conta | A troca de e-mail não é suportada. |
| `invalid-session` | 401 | Invalid or expired session | Sessão ausente, inválida ou expirada em endpoint protegido | Sua sessão expirou. Entre novamente. |
| `invalid-credentials` | 401 | Invalid credentials | E-mail ou senha errados no login | E-mail ou senha inválidos. |
| `session-expired` | 401 | Session expired | Refresh recusado | Sessão expirada. Entre novamente. |
| `invalid-google-token` | 401 | Invalid Google token | `id_token` do Google não validado | Não foi possível validar sua conta Google. Tente novamente. |
| `signup-session-expired` | 401 | Signup session expired | `google_signup_token` inválido ou expirado | Sua sessão de cadastro com o Google expirou. Entre com o Google novamente. |
| `forbidden` | 403 | Forbidden | Sessão válida sem posse do recurso | Você não tem permissão para acessar este recurso. |
| `hairdresser-required` | 403 | Hairdresser account required | Ação de profissional chamada por quem não é profissional | Apenas profissionais podem realizar esta ação. |
| `customer-required` | 403 | Customer account required | Ação de cliente chamada por quem não é cliente | Apenas clientes podem realizar esta ação. |
| `google-account-login` | 403 | Account uses Google sign-in | Login ou troca de senha por e-mail em conta Google | Esta conta usa login com Google. Use o botão Entrar com Google. |
| `google-email-unverified` | 403 | Google email not verified | E-mail do Google não verificado | Seu e-mail do Google não está verificado. |
| `not-found` | 404 | Resource not found | Recurso inexistente ou rota inexistente sob `/api/` | Não encontramos o que você procurou. |
| `postal-code-not-found` | 404 | Postal code not found | CEP válido sem endereço nos provedores | CEP não encontrado. Confira o número ou preencha o endereço manualmente. |
| `method-not-allowed` | 405 | Method not allowed | Método HTTP não suportado pela rota | Não foi possível processar a solicitação. Tente novamente. |
| `email-taken` | 409 | Email already registered | E-mail já cadastrado | Usuário já está cadastrado na nossa base de dados. |
| `phone-taken` | 409 | Phone already registered | Telefone já cadastrado | O número de telefone inserido já está cadastrado na nossa base de dados. |
| `google-account-taken` | 409 | Google account already registered | Conta Google já cadastrada | Esta conta Google já está cadastrada na nossa base de dados. |
| `google-email-linked` | 409 | Email linked to another Google account | E-mail vinculado a outra conta Google | Este e-mail já está vinculado a outra conta Google. |
| `availability-exists` | 409 | Availability already exists | Disponibilidade repetida para o mesmo dia | Já existe uma disponibilidade para este dia. |
| `agenda-overlap` | 409 | Agenda slot overlaps | Bloqueio de agenda sobreposto | Este horário se sobrepõe a outro compromisso. |
| `service-has-reservations` | 409 | Service has reservations | Exclusão de serviço com reservas | Não é possível excluir esse serviço pois há um agendamento atrelado a ele. |
| `review-exists` | 409 | Reservation already reviewed | Segunda avaliação da mesma reserva | Esta reserva já foi avaliada. |
| `slot-unavailable` | 409 | Time slot unavailable | Profissional indisponível no horário pedido | O profissional não está disponível neste horário. |
| `customer-schedule-conflict` | 409 | Customer schedule conflict | Cliente já tem reserva no mesmo horário | Você já tem outra reserva agendada para o mesmo horário. |
| `unsupported-media-type` | 415 | Unsupported media type | Content-Type não aceito pela rota | Não foi possível processar a solicitação. Tente novamente. |
| `too-many-requests` | 429 | Too many requests | Throttle do DRF ou limite do Cognito | Muitas tentativas. Aguarde e tente novamente. |
| `internal-error` | 500 | Internal server error | Exceção não tratada ou falha inesperada | Ocorreu um erro no servidor. Tente novamente mais tarde. |
| `auth-unavailable` | 503 | Authentication service unavailable | Cognito ou JWKS indisponível | Serviço de autenticação indisponível. Tente novamente em instantes. |
| `postal-code-service-unavailable` | 503 | Postal code service unavailable | ViaCEP e BrasilAPI indisponíveis | Não foi possível buscar o CEP. Preencha o endereço manualmente. |
| `ai-service-unavailable` | 503 | AI service unavailable | Gemini sem configuração ou com falha | Não foi possível gerar a descrição agora. Tente novamente. |

---

## User Stories

### P1: Formato único de erro ⭐ MVP

**User Story**: Como dev do app (ou de qualquer cliente), quero que todo erro da API tenha o mesmo formato padrão para tratar erros em um único lugar.

**Why P1**: É o núcleo da issue. Todas as outras histórias dependem dele.

**Acceptance Criteria**:

1. The backend SHALL responder todo erro (status ≥ 400) de rota sob `/api/` com o header `Content-Type: application/problem+json` e um objeto JSON com os membros `type`, `title`, `status`, `detail` e `instance`, sem nenhum outro membro além da extensão `errors` de PD-07. **(PD-01)**
2. The backend SHALL preencher `type` com `https://hairmatch.app/problems/<slug>`, em que `<slug>` é uma linha do Problem Type Catalog, e SHALL nunca usar `about:blank`. **(PD-02)**
3. The backend SHALL preencher `title` com o título em inglês do catálogo para aquele slug, igual em toda ocorrência. **(PD-03)**
4. The backend SHALL preencher `status` com o mesmo inteiro do status HTTP da resposta. **(PD-04)**
5. The backend SHALL preencher `instance` com o path da requisição (`request.path`), sem query string. **(PD-05)**
6. The backend SHALL escrever `detail` em inglês, como frase terminada em ponto, sem texto de exceção, traceback, SQL, nome de classe Python ou dado de outro usuário. **(PD-06)**
7. WHEN o erro é `validation-error` THEN o backend SHALL incluir a extensão `errors`, uma lista com um item por campo inválido ou ausente: `{"pointer": "#/<campo>", "detail": "<frase em inglês>"}` para campo do corpo, e `{"parameter": "<nome>", "detail": "<frase em inglês>"}` para parâmetro de query string. **(PD-07)**

**Independent Test**: chamar `GET /api/service/list/999999` e ver 404 com `Content-Type: application/problem+json`, `type` terminando em `/not-found`, `title` `Resource not found`, `status` 404 e `instance` `/api/service/list/999999`.

---

### P1: Erros de autenticação e autorização ⭐ MVP

**User Story**: Como usuário do app, quero que sessão expirada ou falta de permissão tenham sempre o mesmo sinal para o app reagir certo (refresh, login ou aviso).

**Why P1**: Toda rota protegida passa por aqui, e o refresh do app depende do 401.

**Acceptance Criteria**:

1. WHEN um endpoint protegido recebe sessão ausente, inválida ou expirada THEN o backend SHALL responder 401 `invalid-session`. **(PD-10)**
2. IF as chaves de assinatura do Cognito não podem ser obtidas THEN o backend SHALL responder 503 `auth-unavailable`. **(PD-11)**
3. WHEN uma sessão válida acessa um recurso de outro usuário THEN o backend SHALL responder 403 `forbidden`. **(PD-12)**
4. WHEN uma ação de profissional é chamada por quem não é profissional (inclui `POST /api/availability/create`, hoje 404) THEN o backend SHALL responder 403 `hairdresser-required`. **(PD-13)**
5. WHEN uma ação de cliente é chamada por quem não é cliente (inclui criação, edição e exclusão de avaliação e `GET /api/customer/home/<email>`, hoje 404) THEN o backend SHALL responder 403 `customer-required`. **(PD-14)**
6. WHEN o login recebe e-mail ou senha errados THEN o backend SHALL responder 401 `invalid-credentials`. **(PD-15)**
7. WHEN o login chega sem e-mail ou sem senha THEN o backend SHALL responder 400 `validation-error`, com um item em `errors` para cada um dos dois campos que faltar (`#/email`, `#/password`). **(PD-16)**
8. WHEN o login por e-mail ou a troca de senha é feito em conta Google THEN o backend SHALL responder 403 `google-account-login`. **(PD-17)**
9. WHEN o refresh é recusado THEN o backend SHALL responder 401 `session-expired` e SHALL continuar apagando os cookies `jwt` e `refresh_token`. **(PD-18)**
10. IF o Cognito responde com limite de requisições THEN o backend SHALL responder 429 `too-many-requests`. Qualquer outra falha do Cognito SHALL responder 503 `auth-unavailable`. **(PD-19)**
11. WHEN `POST /api/auth/google` chega sem `id_token` THEN o backend SHALL responder 400 `validation-error` com `errors` apontando `#/id_token`. **(PD-20)**
12. IF o `id_token` do Google não é validado THEN o backend SHALL responder 401 `invalid-google-token`. **(PD-21)**
13. IF o e-mail do Google não está verificado THEN o backend SHALL responder 403 `google-email-unverified`. **(PD-22)**
14. IF o e-mail do Google já está vinculado a outra conta Google THEN o backend SHALL responder 409 `google-email-linked`. **(PD-23)**

**Independent Test**: chamar `GET /api/user/authenticated` sem cookie e ver 401 `invalid-session`. Chamar `DELETE /api/service/remove/<id>` com a sessão de outro cabeleireiro e ver 403 `forbidden`.

---

### P1: Cadastro e conta ⭐ MVP

**User Story**: Como pessoa se cadastrando ou editando a conta, quero erros específicos (e-mail já usado, senha fraca, foto inválida) para saber o que corrigir.

**Why P1**: O cadastro é uma das cinco telas que mostram o erro do backend.

**Acceptance Criteria**:

1. WHEN o cadastro por e-mail ou por Google chega sem campos obrigatórios THEN o backend SHALL responder 400 `validation-error` com um item em `errors` por campo ausente. **(PD-24)**
2. WHEN o cadastro recebe `role` fora de `customer`/`hairdresser` THEN o backend SHALL responder 400 `validation-error` com `errors` apontando `#/role`. **(PD-25)**
3. WHEN o cadastro recebe telefone curto demais THEN o backend SHALL responder 400 `validation-error` com `errors` apontando `#/phone`. **(PD-26)**
4. WHEN o cadastro, por e-mail ou por Google, usa um e-mail já cadastrado THEN o backend SHALL responder 409 `email-taken`. **(PD-27)**
5. WHEN o cadastro ou o update da conta usa um telefone já cadastrado THEN o backend SHALL responder 409 `phone-taken`. **(PD-28)**
6. WHEN o cadastro por Google usa uma conta Google já cadastrada THEN o backend SHALL responder 409 `google-account-taken`. **(PD-29)**
7. WHEN o Cognito recusa a senha no cadastro ou na troca de senha THEN o backend SHALL responder 400 `password-policy`. **(PD-30)**
8. WHEN a foto de perfil do cadastro não é uma imagem válida THEN o backend SHALL responder 400 `invalid-image`. **(PD-31)**
9. WHEN o campo `preferences` do cadastro não é um JSON de lista válido THEN o backend SHALL responder 400 `validation-error` com `errors` apontando `#/preferences`. **(PD-32)**
10. IF o `google_signup_token` é inválido ou expirou THEN o backend SHALL responder 401 `signup-session-expired`. **(PD-33)**
11. IF a criação da conta falha por erro inesperado THEN o backend SHALL responder 500 `internal-error` e SHALL não deixar usuário criado, como hoje. **(PD-34)**
12. WHEN a troca de senha chega sem a senha atual ou sem a nova THEN o backend SHALL responder 400 `validation-error` com `errors` para cada campo ausente. **(PD-35)**
13. WHEN a troca de senha recebe a senha atual errada THEN o backend SHALL responder 400 `incorrect-current-password`. **(PD-36)**
14. WHEN `PUT /api/user/authenticated` tenta trocar o e-mail THEN o backend SHALL responder 400 `email-change-unsupported`. **(PD-37)**

**Independent Test**: cadastrar duas vezes o mesmo e-mail e ver 409 `email-taken`. Cadastrar sem `phone` e ver 400 `validation-error` com `errors[0].pointer == "#/phone"`.

---

### P1: Agendamento (reserva, agenda, disponibilidade, serviço) ⭐ MVP

**User Story**: Como cliente ou profissional, quero que conflitos de horário e recursos ausentes tenham status e tipo corretos para o app explicar o que houve.

**Why P1**: A tela de reserva mostra o erro do backend. A exclusão de serviço depende do status.

**Acceptance Criteria**:

1. WHEN `POST /api/reserve/create` recebe um corpo que não é JSON THEN o backend SHALL responder 400 `malformed-request`, sem o texto da exceção. **(PD-40)**
2. WHEN a reserva referencia um serviço ou profissional inexistente THEN o backend SHALL responder 404 `not-found` com `detail` `Service not found.` ou `Hairdresser not found.`. **(PD-41)**
3. WHEN o serviço da reserva não pertence ao profissional THEN o backend SHALL responder 400 `validation-error` com `errors` apontando `#/service`. **(PD-42)**
4. WHEN `start_time` da reserva não está em ISO 8601 THEN o backend SHALL responder 400 `validation-error` com `errors` apontando `#/start_time`. **(PD-43)**
5. WHEN o profissional não está disponível no horário pedido THEN o backend SHALL responder 409 `slot-unavailable`. **(PD-44)**
6. WHEN o cliente já tem outra reserva no mesmo horário THEN o backend SHALL responder 409 `customer-schedule-conflict` com `detail` em inglês. **(PD-45)**
7. IF salvar a reserva falha por erro inesperado THEN o backend SHALL responder 500 `internal-error`. **(PD-46)**
8. WHEN uma reserva buscada ou removida não existe THEN o backend SHALL responder 404 `not-found` com `detail` `Reservation not found.`. **(PD-47)**
9. WHEN a consulta de horários (`POST /api/reserve/slots/<id>`) chega sem `service` ou `date`, ou com `date` fora de `YYYY-MM-DD` THEN o backend SHALL responder 400 `validation-error` com `errors` apontando cada campo com problema. **(PD-48)**
10. WHEN `POST /api/agenda/create` recebe `start_time` ou `end_time` em formato inválido THEN o backend SHALL responder 400 `validation-error` com `errors` apontando o campo. **(PD-49)**
11. WHEN `POST /api/agenda/create` referencia um serviço inexistente THEN o backend SHALL responder 404 `not-found`, e não 500. **(PD-50)**
12. WHEN o bloqueio de agenda se sobrepõe a outro compromisso THEN o backend SHALL responder 409 `agenda-overlap`, e não 400. **(PD-51)**
13. WHEN a criação de disponibilidade, unitária ou em lote, chega sem `weekday`, `start_time` ou `end_time`, ou com `weekday` inválido THEN o backend SHALL responder 400 `validation-error` com `errors` apontando cada campo. **(PD-52)**
14. WHEN a disponibilidade já existe para aquele dia THEN o backend SHALL responder 409 `availability-exists`, e não 400. **(PD-53)**
15. WHEN `PUT /api/availability/update/multiple/<id>` tem sucesso THEN o backend SHALL responder 200, e não 201. **(PD-54)**
16. WHEN a criação ou edição de serviço chega com corpo inválido THEN o backend SHALL responder 400 `malformed-request`. WHEN chega sem `name`, `price` ou `duration`, SHALL responder 400 `validation-error` com `errors` para cada campo ausente. **(PD-55)**
17. WHEN a exclusão de serviço encontra reservas vinculadas THEN o backend SHALL responder 409 `service-has-reservations`, e não 400. **(PD-56)**
18. WHEN um serviço, disponibilidade, bloqueio de agenda ou profissional não existe THEN o backend SHALL responder 404 `not-found` com `detail` no padrão `<Resource> not found.`. **(PD-57)**

**Independent Test**: excluir um serviço com reserva e ver 409 `service-has-reservations`. Criar duas reservas do mesmo cliente no mesmo horário e ver 409 `customer-schedule-conflict`.

---

### P1: Erros gerados fora das views ⭐ MVP

**User Story**: Como dev do app, quero que erros do framework e exceções inesperadas também saiam em problem+json para nunca receber HTML nem `{"detail"}`.

**Why P1**: Sem isso, o contrato do PD-01 falha justo nos casos imprevistos.

**Acceptance Criteria**:

1. WHEN uma rota sob `/api/` recebe um método que não suporta THEN o backend SHALL responder 405 `method-not-allowed` e SHALL manter o header `Allow`. **(PD-60)**
2. WHEN uma rota recebe um Content-Type que não aceita THEN o backend SHALL responder 415 `unsupported-media-type`. **(PD-61)**
3. WHEN o corpo da requisição não pode ser lido (JSON inválido, inclusive nas views que fazem `json.loads` à mão) THEN o backend SHALL responder 400 `malformed-request`, e não 500 nem HTML. **(PD-62)**
4. WHEN um throttle do DRF recusa a requisição (`CepLookupThrottle`, `GeminiCompletionThrottle`) THEN o backend SHALL responder 429 `too-many-requests` com o header `Retry-After` em segundos. **(PD-63)**
5. IF uma exceção não tratada escapa de uma view sob `/api/` THEN o backend SHALL responder 500 `internal-error` com `detail` `An unexpected error occurred.`, em JSON e não em HTML, com qualquer valor de `DEBUG`. **(PD-64)**
6. IF uma exceção não tratada escapa de uma view sob `/api/` THEN o backend SHALL registrar no log do servidor, em nível ERROR, o path, o método e o traceback. **(PD-65)**
7. WHEN uma URL sob `/api/` não corresponde a nenhuma rota THEN o backend SHALL responder 404 `not-found`, e não a página HTML do Django, com qualquer valor de `DEBUG`. **(PD-66)**
8. The backend SHALL manter sem mudança as respostas fora de `/api/` (`/admin/`). **(PD-67)**

**Independent Test**: `PATCH /api/auth/login` responde 405 `method-not-allowed`, com o header `Allow` listando os métodos da view. `GET /api/nao-existe` responde 404 problem+json.

---

### P1: Mensagens em inglês ⭐ MVP

**User Story**: Como dev que consome a API, quero todas as mensagens em inglês para a API seguir a convenção geral.

**Why P1**: É um dos três pedidos explícitos da issue.

**Acceptance Criteria**:

1. The backend SHALL devolver em inglês todo `title`, todo `detail` e todo `message` de sucesso sob `/api/`. As exceções são conteúdo de usuário, dados de seed e as chaves do `customer/home` (Out of Scope). **(PD-70)**
2. The backend SHALL usar para o conflito de agenda do cliente uma constante em inglês na API e outra em português no fluxo do chatbot. A mensagem que o WhatsApp mostra SHALL continuar igual à de hoje. **(PD-71)**
3. WHEN um DELETE sob `/api/` tem sucesso THEN o backend SHALL responder 204 sem corpo. Isso cobre `user/authenticated`, `user/<email>`, `review/remove`, `availability/remove`, `agenda/remove`, `service/remove` e `reserve/remove`. **(PD-72)**
4. WHEN a exclusão de conta responde 204 THEN o backend SHALL continuar apagando os cookies de sessão. **(PD-73)**

**Independent Test**: rodar a suíte do backend e ver os asserts de texto só em inglês. Pedir uma reserva em conflito pelo chatbot e ver a mensagem em português no WhatsApp (mock de `send_whatsapp_message`).

---

### P1: App mostra erros em pt-BR ⭐ MVP

**User Story**: Como usuário do app, quero ver os erros em português e com texto claro, mesmo que a API responda em inglês.

**Why P1**: Sem isso, a troca para inglês vaza para a UI nas cinco telas que exibem o erro do backend.

**Acceptance Criteria**:

1. WHEN uma chamada à API falha com corpo problem+json THEN o app SHALL convertê-la, em um único módulo, para `ApiProblem { slug, status, detail, errors }`, seja a chamada feita pelo `axiosInstance`, pelo axios cru ou pelo `fetch` do `signUp`. **(PD-80)**
2. WHEN o app exibe um erro vindo do backend THEN o app SHALL mostrar o texto pt-BR do catálogo para o slug e SHALL nunca mostrar o `detail`. **(PD-81)**
3. IF o slug não está no catálogo, a resposta não é problem+json, ou não houve resposta THEN o app SHALL mostrar a mensagem genérica em português que a tela já usa hoje. Sem resposta de rede, SHALL mostrar `Não foi possível conectar ao servidor.`. **(PD-82)**
4. The app SHALL usar o catálogo nas cinco telas que hoje mostram `response.data.error`: login por e-mail, login e cadastro por Google, cadastro (descrição e preferências) e confirmação de reserva. **(PD-83)**
5. WHEN a exclusão de serviço falha com `service-has-reservations` THEN o app SHALL mostrar `Não é possível excluir esse serviço pois há um agendamento atrelado a ele`. A decisão SHALL ser pelo slug, não pelo status 400. **(PD-84)**
6. WHEN a busca de CEP falha com `postal-code-not-found` THEN o app SHALL mostrar `ERROR_MESSAGES.cep_not_found`. Qualquer outra falha SHALL mostrar `ERROR_MESSAGES.cep_lookup_failed`, como hoje. **(PD-85)**
7. WHILE o refresh de sessão existir the app SHALL disparar o refresh só por status 401 fora de `AUTH_EXCLUDED`, como hoje, e SHALL voltar ao login quando o refresh falhar. **(PD-86)**
8. The app SHALL compilar sem erros em `npx tsc --noEmit`, com os tipos `ApiProblem` e `ProblemSlug` exportados. **(PD-87)**

**Independent Test**: no app, logar com senha errada e ver `E-mail ou senha inválidos.`. Reservar um horário em conflito e ver `Você já tem outra reserva agendada para o mesmo horário.`.

---

### P2: Endpoints auxiliares (IA, CEP, preferências, avaliações, webhook)

**User Story**: Como dev, quero que os endpoints secundários também sigam o contrato para não sobrar exceção ao formato.

**Why P2**: Nenhum deles mostra erro ao usuário hoje, exceto o CEP, que só olha o status. O contrato do PD-01 já cobre a forma. Aqui ficam os slugs e status específicos.

**Acceptance Criteria**:

1. WHEN `GET /api/address/cep/<cep>` recebe CEP sem 8 dígitos THEN o backend SHALL responder 400 `invalid-postal-code`. **(PD-90)**
2. WHEN o CEP é válido mas nenhum provedor encontra endereço THEN o backend SHALL responder 404 `postal-code-not-found`. **(PD-91)**
3. IF ViaCEP e BrasilAPI falham THEN o backend SHALL responder 503 `postal-code-service-unavailable`. **(PD-92)**
4. WHEN `POST /api/hairdresser/gemini_completion` recebe corpo inválido THEN o backend SHALL responder 400 `malformed-request`. **(PD-93)**
5. IF o Gemini está sem configuração ou falha THEN o backend SHALL responder 503 `ai-service-unavailable`, sem texto da exceção. Hoje responde 500 com `Config error: ...`. **(PD-94)**
6. WHEN a criação de avaliação chega sem `reserve`, `rating` ou `hairdresser`, com `rating` inválido, ou com profissional diferente do da reserva THEN o backend SHALL responder 400 `validation-error` com `errors` apontando o campo. **(PD-95)**
7. WHEN a reserva já foi avaliada THEN o backend SHALL responder 409 `review-exists`. **(PD-96)**
8. WHEN o cliente tenta avaliar uma reserva que não é dele THEN o backend SHALL responder 403 `forbidden`. **(PD-97)**
9. WHEN a foto da avaliação não é uma imagem válida THEN o backend SHALL responder 400 `invalid-image`. **(PD-98)**
10. WHEN a lista de preferências de um usuário está vazia ou a preferência não existe THEN o backend SHALL responder 404 `not-found`, mantendo o 404 de que o app depende. **(PD-99)**
11. WHEN o webhook `POST /api/chatbot/test` recebe JSON inválido THEN o backend SHALL responder 400 `malformed-request`. IF falha internamente THEN SHALL responder 500 `internal-error`. **(PD-100)**

**Independent Test**: `GET /api/address/cep/123` responde 400 `invalid-postal-code`. Com o Gemini sem `GEMINI_API_KEY`, `POST /api/hairdresser/gemini_completion` responde 503 `ai-service-unavailable`.

---

### P2: Fallbacks do próprio app em português

**User Story**: Como usuário do app, quero que as mensagens genéricas do app também estejam em português.

**Why P2**: Hoje três fallbacks do app estão em inglês (`_layout.tsx:63`, `useLogin`, `useReviewForm.ts:131`). É barato alinhar junto com o catálogo, mas não bloqueia a issue.

**Acceptance Criteria**:

1. WHEN o app cai em um fallback genérico de erro THEN o app SHALL mostrar texto em português, substituindo `Authentication failed. Please check your credentials.`, `An unknown error occurred.`, `An unknown error occurred during registration.` e `Something went wrong...`. **(PD-101)**

**Independent Test**: forçar um erro sem resposta no login e ver a mensagem em português.

---

## Edge Cases

- IF uma exceção do DRF (`APIException` e subclasses) ou um `Http404` sem slug próprio chega ao tratamento central THEN o backend SHALL manter o status da exceção e SHALL usar o slug genérico daquele status. 400 vira `validation-error` para `ValidationError` e `malformed-request` para o resto. 401 vira `invalid-session`, 403 vira `forbidden` (inclusive a falha de CSRF da `SessionAuthentication`) e 404 vira `not-found`. Só uma exceção não tratada que não seja HTTP vira `internal-error` (500). Adicionar um slug novo exige atualizar o catálogo deste spec e o do app. **(PD-110)**
- WHEN o mesmo campo falha por dois motivos THEN o backend SHALL devolver um item em `errors` por motivo, com o mesmo `pointer`. **(PD-111)**
- IF uma resposta de erro sob `/api/` for gerada antes de chegar a uma view (URL inexistente, método inválido) THEN o `instance` SHALL continuar sendo o path pedido. **(PD-112)**
- WHEN o throttle recusa e o DRF não informa o tempo de espera THEN o backend SHALL omitir o header `Retry-After`, sem inventar um valor. **(PD-113)**
- IF o corpo do 204 de exclusão de conta for inspecionado THEN ele SHALL estar vazio (`Content-Length: 0` ou sem corpo). **(PD-114)**

---

## Implicit-Requirement Dimensions

| Dimension | Resolução |
| --------- | --------- |
| Input validation & bounds | PD-07, PD-16, PD-24 a PD-26, PD-32, PD-35, PD-42, PD-43, PD-48, PD-49, PD-52, PD-55, PD-95. As regras de validação não mudam; muda só o formato. |
| Failure / partial-failure states | PD-34, PD-46, PD-64. A não-atomicidade do bulk de disponibilidade fica fora (Deferred Ideas). |
| Idempotency / retry / duplicate handling | Duplicidades viram 409 com slug próprio (PD-27 a PD-29, PD-53, PD-96). Não há retry novo. |
| Auth boundaries & rate limits | PD-10 a PD-23 e PD-63. As regras de acesso não mudam; muda o formato e, em dois casos, o status (PD-13, PD-14). |
| Concurrency / ordering | N/A because a feature muda o formato das respostas, não a lógica de concorrência. Os conflitos de horário já existentes só trocam de formato (PD-44, PD-45, PD-51). |
| Data lifecycle / expiry | N/A because nenhum dado é criado, migrado ou expirado. O `signup_token` mantém a expiração de 30 min (PD-33). |
| Observability | PD-65: o 500 é logado com traceback no servidor e nunca vai ao cliente (PD-06). |
| External-dependency failure | PD-11, PD-19, PD-92, PD-94: Cognito, provedores de CEP e Gemini têm slug 503 próprio. |
| State-transition integrity | N/A because nenhuma transição de estado é criada ou alterada. |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| PD-01 | P1: Formato único de erro | T1 | Implemented |
| PD-02 | P1: Formato único de erro | T1 | Implemented |
| PD-03 | P1: Formato único de erro | T1 | Implemented |
| PD-04 | P1: Formato único de erro | T1 | Implemented |
| PD-05 | P1: Formato único de erro | T1 | Implemented |
| PD-06 | P1: Formato único de erro | T1 | Implemented |
| PD-07 | P1: Formato único de erro | T1 | Implemented |
| PD-10 | P1: Autenticação e autorização | T2 | Implemented |
| PD-11 | P1: Autenticação e autorização | T2 | Implemented |
| PD-12 | P1: Autenticação e autorização | T2 | Implemented |
| PD-13 | P1: Autenticação e autorização | T2, T9 | Implemented |
| PD-14 | P1: Autenticação e autorização | T2, T4 | Implemented |
| PD-15 | P1: Autenticação e autorização | T3 | Implemented |
| PD-16 | P1: Autenticação e autorização | T3 | Implemented |
| PD-17 | P1: Autenticação e autorização | T3, T4 | Implemented |
| PD-18 | P1: Autenticação e autorização | T3 | Implemented |
| PD-19 | P1: Autenticação e autorização | T3 | Implemented |
| PD-20 | P1: Autenticação e autorização | T3 | Implemented |
| PD-21 | P1: Autenticação e autorização | T3 | Implemented |
| PD-22 | P1: Autenticação e autorização | T3 | Implemented |
| PD-23 | P1: Autenticação e autorização | T3 | Implemented |
| PD-24 | P1: Cadastro e conta | T5 | Implemented |
| PD-25 | P1: Cadastro e conta | T5 | Implemented |
| PD-26 | P1: Cadastro e conta | T5 | Implemented |
| PD-27 | P1: Cadastro e conta | T5 | Implemented |
| PD-28 | P1: Cadastro e conta | T4, T5 | Implemented |
| PD-29 | P1: Cadastro e conta | T5 | Implemented |
| PD-30 | P1: Cadastro e conta | T4, T5 | Implemented |
| PD-31 | P1: Cadastro e conta | T5 | Implemented |
| PD-32 | P1: Cadastro e conta | T5 | Implemented |
| PD-33 | P1: Cadastro e conta | T5 | Implemented |
| PD-34 | P1: Cadastro e conta | T5 | Implemented |
| PD-35 | P1: Cadastro e conta | T4 | Implemented |
| PD-36 | P1: Cadastro e conta | T4 | Implemented |
| PD-37 | P1: Cadastro e conta | T4 | Implemented |
| PD-40 | P1: Agendamento | T7 | Implemented |
| PD-41 | P1: Agendamento | T7 | Implemented |
| PD-42 | P1: Agendamento | T7 | Implemented |
| PD-43 | P1: Agendamento | T7 | Implemented |
| PD-44 | P1: Agendamento | T7 | Implemented |
| PD-45 | P1: Agendamento | T7 | Implemented |
| PD-46 | P1: Agendamento | T7 | Implemented |
| PD-47 | P1: Agendamento | T7 | Implemented |
| PD-48 | P1: Agendamento | T7 | Implemented |
| PD-49 | P1: Agendamento | T8 | Implemented |
| PD-50 | P1: Agendamento | T8 | Implemented |
| PD-51 | P1: Agendamento | T8 | Implemented |
| PD-52 | P1: Agendamento | T9 | Implemented |
| PD-53 | P1: Agendamento | T9 | Implemented |
| PD-54 | P1: Agendamento | T9 | Implemented |
| PD-55 | P1: Agendamento | - | Pending |
| PD-56 | P1: Agendamento | - | Pending |
| PD-57 | P1: Agendamento | T6, T8, T9 | Implemented |
| PD-60 | P1: Erros fora das views | T1 | Implemented |
| PD-61 | P1: Erros fora das views | T1 | Implemented |
| PD-62 | P1: Erros fora das views | T1, T4, T9 | Implemented |
| PD-63 | P1: Erros fora das views | T1, T6 | Implemented |
| PD-64 | P1: Erros fora das views | T1 | Implemented |
| PD-65 | P1: Erros fora das views | T1 | Implemented |
| PD-66 | P1: Erros fora das views | T1 | Implemented |
| PD-67 | P1: Erros fora das views | T1 | Implemented |
| PD-70 | P1: Mensagens em inglês | - | Pending |
| PD-71 | P1: Mensagens em inglês | T7 | Implemented |
| PD-72 | P1: Mensagens em inglês | T4, T7, T8, T9 | Implemented |
| PD-73 | P1: Mensagens em inglês | T4 | Implemented |
| PD-80 | P1: App mostra erros em pt-BR | - | Pending |
| PD-81 | P1: App mostra erros em pt-BR | - | Pending |
| PD-82 | P1: App mostra erros em pt-BR | - | Pending |
| PD-83 | P1: App mostra erros em pt-BR | - | Pending |
| PD-84 | P1: App mostra erros em pt-BR | - | Pending |
| PD-85 | P1: App mostra erros em pt-BR | - | Pending |
| PD-86 | P1: App mostra erros em pt-BR | - | Pending |
| PD-87 | P1: App mostra erros em pt-BR | - | Pending |
| PD-90 | P2: Endpoints auxiliares | T6 | Implemented |
| PD-91 | P2: Endpoints auxiliares | T6 | Implemented |
| PD-92 | P2: Endpoints auxiliares | T6 | Implemented |
| PD-93 | P2: Endpoints auxiliares | T6 | Implemented |
| PD-94 | P2: Endpoints auxiliares | T6 | Implemented |
| PD-95 | P2: Endpoints auxiliares | - | Pending |
| PD-96 | P2: Endpoints auxiliares | - | Pending |
| PD-97 | P2: Endpoints auxiliares | - | Pending |
| PD-98 | P2: Endpoints auxiliares | - | Pending |
| PD-99 | P2: Endpoints auxiliares | - | Pending |
| PD-100 | P2: Endpoints auxiliares | - | Pending |
| PD-101 | P2: Fallbacks do app em português | - | Pending |
| PD-110 | Edge Cases | T1 | Implemented |
| PD-111 | Edge Cases | T1 | Implemented |
| PD-112 | Edge Cases | T1 | Implemented |
| PD-113 | Edge Cases | T1 | Implemented |
| PD-114 | Edge Cases | T4 | Implemented |

**ID format:** `PD-NN`. As lacunas na numeração (08-09, 38-39, 58-59 etc.) separam as histórias e são intencionais.

**Coverage:** 90 total, 0 mapped to tasks, 90 unmapped ⚠️ (Tasks ainda não criado).

---

## Success Criteria

- [ ] Uma busca em `backend/**/views.py`, `users/authentication.py` e `hairmatch/ai_clients/gemini_client.py` não encontra nenhum `JsonResponse({'error'` nem `str(e)` em corpo de resposta.
- [ ] Toda resposta de erro exercitada pela suíte do backend tem `Content-Type: application/problem+json` e um slug do catálogo.
- [ ] A suíte do backend (`cd backend && python manage.py test`) passa, sem nenhum teste removido nem pulado.
- [ ] No UAT, cada uma das cinco telas que exibem erro mostra o texto pt-BR do catálogo em pelo menos um caso de erro real.
- [ ] `npx tsc --noEmit` passa no `frontend-mobile`.
