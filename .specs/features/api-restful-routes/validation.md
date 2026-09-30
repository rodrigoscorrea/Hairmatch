# Rotas da API em RFC 3986 Validation

**Spec**: `.specs/features/api-restful-routes/spec.md`
**Diff range**: `48eeb00..HEAD` (branch `163-padronizacao-das-urls-de-apis-para-rfcs-adequadas`)
**Verifier**: o mesmo agente que implementou. O harness não permite disparar um sub-agente sem pedido do usuário, então valeu o fallback standalone da skill (releitura do spec e do diff, sensor de mutação). Autor e verificador não são independentes.

## Validation

**Result**: PASS nos gates automatizados. O UAT manual no web e no Android continua pendente (critério de sucesso 4 do spec).

| Gate | Resultado |
| ---- | --------- |
| Suíte do backend (`manage.py test --noinput`) | 598 testes, OK (eram 590). Nenhum pulado. O critério "nenhum teste removido" não se sustenta em 8 testes que exercitavam comportamento de rota que o spec removeu (RT-11, RT-13, RT-64). Quatro foram apagados: exclusão por e-mail no Cognito (2) e comparação do e-mail do path sem caixa (home e exclusão). Quatro foram trocados: o POST de corpo não JSON nos slots virou o teste do parâmetro repetido, e os três 403 de "outro e-mail" viraram os testes do 404 da rota removida. A mensagem do commit de cada tarefa explica o caso. |
| `npx tsc --noEmit` (`frontend-mobile`) | exit 0 |
| Grep do spec por rotas antigas em `services`, `hooks` e `app` | 0 ocorrências |
| Grep amplo por `api/` fora dos serviços | só um comentário (`contexts/RegistrationContext.tsx:33`, `/api/auth/google`, rota que não mudou) |
| Jest descartável de `services/auth-routes.ts` | 17 casos OK, arquivo apagado (o app não tem testes por decisão) |

## Cobertura dos critérios (evidência ou zero)

| Requisito | Evidência (`file:line`) | Resultado do spec |
| --------- | ----------------------- | ----------------- |
| RT-50 e RT-01 a RT-49 | `backend/hairmatch/test_routes.py:94` `assertEqual(sorted(ROUTE_TABLE - found), [])` e `assertEqual(sorted(found - ROUTE_TABLE), [])` | Exatamente as rotas da tabela |
| RT-52 | `backend/hairmatch/test_routes.py:121` 12 paths antigos, `assert_problem(..., 404, 'not-found')` | 404 `not-found` |
| RT-53 | `backend/hairmatch/test_routes.py:134` e `:141`, `Allow` do path | 405 com `Allow` do path |
| RT-54 | `backend/hairmatch/test_routes.py:100` regex `^[a-z0-9/-]+$`, sem barra final, plural ou exceção listada | Formato do path |
| RT-80, RT-81 | `backend/hairmatch/test_routes.py:147` e `:151` | 404 |
| RT-57 | `backend/users/tests.py:463` `assertFalse(response.json()['authenticated'])` com status 200 | 200, nunca 401 |
| RT-58 | `backend/users/tests.py:774` só `first_name` muda | PATCH parcial |
| RT-09 | `backend/users/tests.py:791` PUT em `/users/me` dá 405 | PUT → PATCH |
| RT-11 | `backend/users/tests.py:955` `GET` e `DELETE /api/user/<email>` dão 404 e as contas ficam | Rota removida |
| RT-59, RT-13 | `backend/users/tests.py:1108` corpo `for_you` e `hairdressers_by_preferences`; `:1164` path com e-mail dá 404; `:1180` sem sessão 401 | Home pela sessão |
| RT-65, RT-55, RT-12 | `backend/users/tests.py:1458` `{'data': []}`; `:1474` `search` não é lido | Envelope e `q` |
| RT-82 | `backend/users/tests.py:2934` os dois formatos chegam à busca com o texto bruto e dão o mesmo corpo | CEP com hífen |
| RT-60, RT-61 | `backend/preferences/tests.py:251` duas vezes PUT, uma atribuição, 204; `:315` DELETE sem atribuição, 204 | Idempotência |
| RT-62 | `backend/preferences/tests.py:236` e `:300` 404 `not-found` | Preferência inexistente |
| RT-63 | `backend/reserve/tests.py:494` GET com `date` e `service` na query, corpo `available_slots` com `09:00` | Mesmos horários |
| RT-64 | `backend/reserve/tests.py:508` `errors` = `[{'parameter': 'service', ...}, {'parameter': 'date', ...}]`; `:561` data inválida | `parameter`, não `pointer` |
| RT-83 | `backend/reserve/tests.py:534` `?date=not-a-date&date=<segunda>` dá 200 | Último valor |
| RT-39, RT-41 | `backend/service/tests.py:665` GET lê o serviço; `:680` PUT valida o corpo | Path com três métodos |
| RT-31 | `backend/availability/tests.py:655` PATCH parcial mantém `start_time` e `end_time` | PUT → PATCH |
| RT-49, RT-76 | `backend/chatbot/tests.py:337` `/api/chatbot/webhook` dá 200 e `/api/chatbot/test` dá 404 | Webhook |
| RT-71 a RT-73 | Jest descartável (17 casos): `POST /api/users` excluído, `/api/users/me` e `/api/users/1/preferences` não; URL absoluta e com query normalizadas. `frontend-mobile/services/auth-routes.ts:25` `excluded.method === verb && excluded.path === path` | Comparação exata |
| RT-73 | `frontend-mobile/services/axios-instance.ts:31` `.post(REFRESH_PATH)` e `frontend-mobile/app/_layout.tsx:157` `${API_BACKEND_URL}${REFRESH_PATH}` | Uma constante |
| RT-74 | `frontend-mobile/services/reserve.service.ts:16` GET `available-slots` com `params: {service, date}` | Query |
| RT-77 | `README.md` seções "API routes" e "Chatbot webhook" | URL nova e passo manual |

Sem lacuna de precisão do spec.

## Sensor de discriminação

25 mutantes de comportamento injetados em cópia dos arquivos (o original restaurado depois de cada um) e a suíte inteira rodada: **25 mortos, 0 sobreviventes**. Cobrem: valor de parâmetro repetido, 200 no lugar de 204, DELETE sem efeito, `search` no lugar de `q`, lista crua na busca vazia, PUT no lugar de PATCH, 401 na sessão, rota extra e rota antiga de volta, GET no login, `pointer` no lugar de `parameter`, `--5` aceito, home sem checar o papel, métodos removidos de quatro paths, quatro paths renomeados, 404 perdido da preferência, serviço ignorado nos slots, barra final e webhook com o nome antigo. `git status` igual ao de antes do sensor.

Limite honesto: o sensor roda a suíte do backend. O app não tem suíte, e a lógica de exclusão do refresh foi conferida pelo jest descartável, sem mutantes.

## Pendências

- UAT manual no web e no Android (login, cadastro por e-mail e Google, home, busca, perfil, agendamento, reservas, avaliação, serviços, disponibilidade, agenda, logout).
- Reconfigurar a URL do webhook na Evolution API antes do deploy de produção, com autorização explícita.
