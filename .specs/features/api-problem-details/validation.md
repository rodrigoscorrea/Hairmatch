# Erros da API em RFC 9457 Validation

**Feature**: `api-problem-details` (issue #161)
**Diff range**: `34e9afb..HEAD` na branch `161-padronizacao-das-respostas-de-apis-para-rfcs-adequadas` (42 arquivos: 24 no `backend`, 14 no `frontend-mobile`, o resto em `.specs`)
**Verifier**: passada independente feita inline pelo mesmo agente que implementou, porque a sessão não autorizou sub-agentes. O passo é o "standalone fallback" do skill. Author = verifier: a evidência é dada por `file:line` e por execução, não por memória.

## Validation

**Result**: PASS para tudo o que é automatizável (backend, contrato no servidor real e `tsc`). O UAT das cinco telas do app **não foi executado** e está listado em "Não verificado".

## Gates

| Gate | Comando | Resultado |
| ---- | ------- | --------- |
| Backend completo | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput'` | 590 testes, OK, 0 pulados. Linha de base antes da feature: 463. |
| Tipos do app | `cd frontend-mobile && npx tsc --noEmit` | exit 0. Antes: 4 erros que já existiam em `_layout.tsx` (customer e hairdresser), `BottomBar.tsx` e `availability-formater.ts`, corrigidos só nos tipos no commit `fix(app): clear the four type errors that kept tsc red`. |
| Normalizador do app | jest temporário (não commitado) sobre `frontend-mobile/utils/api-problem.ts` | 10 testes: `AxiosError`, problema cru, string JSON, sem resposta, slug desconhecido, `__proto__`, `toString`, os 36 slugs. |
| Servidor real (`DEBUG=True` fixo) | `curl` em `http://localhost:8000` | `/api/does-not-exist` 404, `PATCH /api/auth/login` 405 com `Allow`, `/api/address/cep/123` 400, `/api/service/list/999999` 404, `/api/user/authenticated` 401, login desconhecido 401, corpo vazio 400 com dois itens em `errors`, JSON inválido 400. Todos `application/problem+json`. `/admin/nope/` segue com o HTML do Django. |

## Test integrity

- Definições `def test_`: 465 antes, 592 depois. Nenhuma removida (`git diff 34e9afb HEAD -- 'backend/*/tests.py'` não tem linha `-  def test_`), nenhuma pulada.
- Os asserts de texto em português, de `{"error"}` e de `Content-Type: application/json` em resposta de erro foram reescritos para o outcome do spec (`assert_problem`, que confere status, `Content-Type`, o conjunto exato de membros, `type`, `title`, `status`, `detail` terminado em ponto e, quando dado, `errors`). Nenhum assert de status ou de efeito colateral foi removido.

## Spec-anchored outcome check

Cada requisito foi ligado a uma linha de implementação e a um teste cujo assert confere o valor que o spec define (slug, status, `detail` quando o spec o fixa, `errors` com `pointer`). Uma âncora que não existe faz o script de auditoria falhar, então as 90 linhas abaixo existem no código.

| Requisito | Implementação (`file:line`) | Evidência de teste (`file:line`) |
| --------- | --------------------------- | -------------------------------- |
| PD-01 | `backend/hairmatch/problems.py:74` | `backend/hairmatch/test_problems.py:36` |
| PD-02 | `backend/hairmatch/problems.py:82` | `backend/hairmatch/test_problems.py:43` |
| PD-03 | `backend/hairmatch/problems.py:83` | `backend/hairmatch/problem_testing.py:26` |
| PD-04 | `backend/hairmatch/problems.py:84` | `backend/hairmatch/problem_testing.py:27` |
| PD-05 | `backend/hairmatch/problems.py:86` | `backend/hairmatch/test_problems.py:178` |
| PD-06 | `backend/hairmatch/problems.py:139` | `backend/hairmatch/test_problems.py:154` |
| PD-07 | `backend/hairmatch/problems.py:96` | `backend/hairmatch/test_problems.py:51` |
| PD-10 | `backend/users/authentication.py:63` | `backend/users/tests.py:3452` |
| PD-11 | `backend/users/authentication.py:61` | `backend/users/tests.py:3552` |
| PD-12 | `backend/users/authentication.py:67` | `backend/reserve/tests.py:437` |
| PD-13 | `backend/users/authentication.py:74` | `backend/availability/tests.py:1277` |
| PD-14 | `backend/users/authentication.py:79` | `backend/users/tests.py:1165` |
| PD-15 | `backend/users/views.py:305` | `backend/users/tests.py:3923` |
| PD-16 | `backend/users/views.py:292` | `backend/users/tests.py:3978` |
| PD-17 | `backend/users/views.py:302` | `backend/users/tests.py:3956` |
| PD-18 | `backend/users/views.py:339` | `backend/users/tests.py:4051` |
| PD-19 | `backend/users/views.py:73` | `backend/users/tests.py:4062` |
| PD-20 | `backend/users/views.py:350` | `backend/users/tests.py:2341` |
| PD-21 | `backend/users/views.py:355` | `backend/users/tests.py:2353` |
| PD-22 | `backend/users/views.py:358` | `backend/users/tests.py:2366` |
| PD-23 | `backend/users/views.py:365` | `backend/users/tests.py:2377` |
| PD-24 | `backend/users/views.py:124` | `backend/users/tests.py:3756` |
| PD-25 | `backend/users/views.py:251` | `backend/users/tests.py:3762` |
| PD-26 | `backend/users/views.py:254` | `backend/users/tests.py:3732` |
| PD-27 | `backend/users/views.py:133` | `backend/users/tests.py:3804` |
| PD-28 | `backend/users/views.py:135` | `backend/users/tests.py:4353` |
| PD-29 | `backend/users/views.py:208` | `backend/users/tests.py:2630` |
| PD-30 | `backend/users/views.py:140` | `backend/users/tests.py:3794` |
| PD-31 | `backend/users/views.py:172` | `backend/users/tests.py:316` |
| PD-32 | `backend/users/views.py:265` | `backend/users/tests.py:3771` |
| PD-33 | `backend/users/views.py:189` | `backend/users/tests.py:2561` |
| PD-34 | `backend/users/views.py:176` | `backend/users/tests.py:3784` |
| PD-35 | `backend/users/views.py:424` | `backend/users/tests.py:4181` |
| PD-36 | `backend/users/views.py:431` | `backend/users/tests.py:4166` |
| PD-37 | `backend/users/views.py:478` | `backend/users/tests.py:4320` |
| PD-40 | `backend/reserve/views.py:75` | `backend/reserve/tests.py:227` |
| PD-41 | `backend/reserve/views.py:87` | `backend/reserve/tests.py:331` |
| PD-42 | `backend/reserve/views.py:90` | `backend/reserve/tests.py:315` |
| PD-43 | `backend/reserve/views.py:98` | `backend/reserve/tests.py:253` |
| PD-44 | `backend/reserve/views.py:113` | `backend/reserve/tests.py:170` |
| PD-45 | `backend/reserve/views.py:117` | `backend/reserve/tests.py:264` |
| PD-46 | `backend/reserve/views.py:119` | `backend/reserve/tests.py:278` |
| PD-47 | `backend/reserve/views.py:60` | `backend/reserve/tests.py:469` |
| PD-48 | `backend/reserve/views.py:172` | `backend/reserve/tests.py:526` |
| PD-49 | `backend/agenda/views.py:17` | `backend/agenda/tests.py:235` |
| PD-50 | `backend/agenda/views.py:56` | `backend/agenda/tests.py:175` |
| PD-51 | `backend/agenda/views.py:75` | `backend/agenda/tests.py:201` |
| PD-52 | `backend/availability/views.py:30` | `backend/availability/tests.py:1340` |
| PD-53 | `backend/availability/views.py:87` | `backend/availability/tests.py:1318` |
| PD-54 | `backend/availability/views.py:212` | `backend/availability/tests.py:1388` |
| PD-55 | `backend/service/views.py:16` | `backend/service/tests.py:221` |
| PD-56 | `backend/service/views.py:118` | `backend/service/tests.py:603` |
| PD-57 | `backend/service/views.py:59` | `backend/service/tests.py:595` |
| PD-60 | `backend/hairmatch/problems.py:171` | `backend/hairmatch/test_problems.py:203` |
| PD-61 | `backend/hairmatch/problems.py:173` | `backend/hairmatch/test_problems.py:116` |
| PD-62 | `backend/hairmatch/problems.py:115` | `backend/users/tests.py:3932` |
| PD-63 | `backend/hairmatch/problems.py:182` | `backend/hairmatch/test_problems.py:218` |
| PD-64 | `backend/hairmatch/problems.py:190`, `backend/hairmatch/problems.py:199` | `backend/hairmatch/test_problems.py:240`, `backend/hairmatch/test_problems.py:309` |
| PD-65 | `backend/hairmatch/problems.py:189` | `backend/hairmatch/test_problems.py:147` |
| PD-66 | `backend/hairmatch/urls.py:32` | `backend/hairmatch/test_problems.py:184` |
| PD-67 | `backend/hairmatch/urls.py:22` | `backend/hairmatch/test_problems.py:253` |
| PD-70 | `backend/hairmatch/problems.py:180` | `backend/hairmatch/test_problems.py:36` |
| PD-71 | `backend/reserve/views.py:23` | `backend/chatbot/tests.py:444` |
| PD-72 | `backend/reserve/views.py:167` | `backend/reserve/tests.py:452` |
| PD-73 | `backend/users/views.py:99` | `backend/users/tests.py:4236` |
| PD-80 | `frontend-mobile/utils/api-problem.ts:142` | `frontend-mobile/app/_layout.tsx:116` |
| PD-81 | `frontend-mobile/utils/api-problem.ts:170` | `frontend-mobile/hooks/customerHooks/useServiceBooking.ts:187` |
| PD-82 | `frontend-mobile/utils/api-problem.ts:60` | `frontend-mobile/utils/api-problem.ts:176` |
| PD-83 | `frontend-mobile/hooks/authHooks/useGoogleAuth.ts:17` | `frontend-mobile/hooks/authHooks/usePreferences.ts:134` |
| PD-84 | `frontend-mobile/hooks/hairdresserHooks/useServiceManager.ts:60` | `frontend-mobile/utils/api-problem.ts:92` |
| PD-85 | `frontend-mobile/hooks/authHooks/useCepLookup.ts:22` | `frontend-mobile/utils/api-problem.ts:83` |
| PD-86 | `frontend-mobile/services/axios-instance.ts:60` | `frontend-mobile/services/axios-instance.ts:63` |
| PD-87 | `frontend-mobile/utils/api-problem.ts:7` | `frontend-mobile/utils/api-problem.ts:51` |
| PD-90 | `backend/users/views.py:393` | `backend/users/tests.py:2909` |
| PD-91 | `backend/users/views.py:395` | `backend/users/tests.py:2914` |
| PD-92 | `backend/users/views.py:398` | `backend/users/tests.py:2919` |
| PD-93 | `backend/users/views.py:637` | `backend/users/tests.py:4446` |
| PD-94 | `backend/hairmatch/ai_clients/gemini_client.py:101` | `backend/hairmatch/tests.py:164` |
| PD-95 | `backend/review/views.py:57` | `backend/review/tests.py:324` |
| PD-96 | `backend/review/views.py:77` | `backend/review/tests.py:347` |
| PD-97 | `backend/review/views.py:73` | `backend/review/tests.py:274` |
| PD-98 | `backend/review/views.py:98` | `backend/review/tests.py:220` |
| PD-99 | `backend/preferences/views.py:48` | `backend/preferences/tests.py:85` |
| PD-100 | `backend/chatbot/views.py:368` | `backend/chatbot/tests.py:434` |
| PD-101 | `frontend-mobile/app/_layout.tsx:64` | `frontend-mobile/hooks/authHooks/useLogin.ts:62` |
| PD-110 | `backend/hairmatch/problems.py:184` | `backend/hairmatch/test_problems.py:143` |
| PD-111 | `backend/hairmatch/problems.py:111` | `backend/hairmatch/test_problems.py:55` |
| PD-112 | `backend/hairmatch/problems.py:86` | `backend/hairmatch/test_problems.py:180` |
| PD-113 | `backend/hairmatch/problems.py:182` | `backend/hairmatch/test_problems.py:137` |
| PD-114 | `backend/users/views.py:99` | `backend/users/tests.py:732` |

Nos requisitos do app (PD-80 a PD-87, PD-101) a evidência de teste é a implementação mais o jest temporário e o `tsc`. O app não tem testes automatizados por decisão do spec.

### Spec-precision gaps

O spec não define o texto exato nestes pontos, então os testes fixam o texto escolhido na implementação, e não um valor do spec:

- `detail` de PD-42, PD-43, PD-49, PD-52, PD-55, PD-95 (o spec fixa slug, status e o campo apontado, mas não a frase).
- `detail` de `Agenda slot not found.` (PD-57 diz só "`<Resource> not found.`").
- PD-84: o spec cita o texto sem ponto final e o catálogo cita com ponto. O app usa o texto sem ponto, o que a tela já mostrava.

## Discrimination sensor

30 falhas de comportamento injetadas em uma worktree descartável (`git worktree`, montada em um segundo container). O baseline sem mutação passou na suíte completa no mesmo harness. Cada mutante foi morto por falha de teste, nunca por erro de carga. Depois, a worktree foi removida e o `git status --porcelain` da árvore real ficou idêntico ao de antes.

| Mutante | Resultado |
| ------- | --------- |
| M01 `Retry-After` some | KILLED (`test_throttle_answers_429_with_retry_after`) |
| M02 `instance` com query string | KILLED (`test_unknown_route_debug_off`) |
| M03 rota catch-all removida | KILLED (`test_bare_api_path_is_not_found`) |
| M04 500 respondido com status 200 | KILLED (`test_unhandled_exception_debug_off`) |
| M05 exceção inesperada sem log | KILLED (`test_unhandled_exception_debug_off`) |
| M06 `forbidden()` responde 401 | KILLED (`test_forbidden_answers_403_forbidden`) |
| M07 slug `customer-required` trocado | KILLED (`test_authenticated_customer_refuses_a_hairdresser_with_403`) |
| M08 checagem de conta Google no login removida | KILLED (`test_google_account_answers_403_without_calling_cognito`) |
| M09 telefone duplicado não checado no cadastro | KILLED (`test_local_validation_failures_answer_as_before_without_calling_cognito`) |
| M10 `role` não validada | KILLED (`test_invalid_role_and_short_phone_are_reported_together`) |
| M11 exclusão de conta sem apagar cookies | KILLED (`test_deleting_the_own_account_removes_the_cognito_user_the_row_and_the_cookies`) |
| M12 senha atual errada vira `password-policy` | KILLED (`test_wrong_current_password_answers_400_and_keeps_the_password`) |
| M13 CEP 404 vira `not-found` | KILLED (`test_not_found_returns_404`) |
| M14 Gemini vaza o texto da exceção | KILLED (`test_hairdresser_profile_ai_completion_config_error`) |
| M15 conflito do cliente vira `slot-unavailable` | KILLED (`test_create_reserve_that_clashes_with_another_reserve_of_the_customer_answers_409`) |
| M16 remoção de reserva responde 200 | KILLED (`test_hairdresser_of_the_service_removes_the_reserve`) |
| M17 texto do chatbot em inglês | KILLED (`test_a_clash_with_another_reserve_of_the_customer_is_refused`) |
| M18 sobreposição de agenda vira 400 | KILLED (`test_create_agenda_that_overlaps_an_existing_block_answers_409`) |
| M19 serviço inexistente na agenda vira 500 | KILLED (`test_create_agenda_invalid_service`) |
| M20 PUT em lote responde 201 | KILLED (`test_owner_replaces_own_schedule`) |
| M21 disponibilidade duplicada vira 400 | KILLED (`test_creating_the_same_weekday_twice_answers_409`) |
| M22 serviço com reservas é excluído | KILLED (`test_business_logic_enforcement`) |
| M23 avaliação repetida aceita | KILLED (`test_a_reserve_that_was_already_reviewed_answers_409`) |
| M24 avaliar reserva alheia aceito | KILLED (`test_create_review_not_authorized_for_reserve`) |
| M25 lista vazia de preferências vira 200 | KILLED (`test_list_preferences_of_a_user_without_any_answers_404`) |
| M26 webhook engole o 400 | KILLED (`test_a_body_that_is_not_a_json_object_answers_400_malformed_request`) |
| M27 `json_object` aceita lista | KILLED (`test_json_that_is_not_an_object_is_malformed_request`) |
| M28 `errors` só com o primeiro item | KILLED (`test_missing_old_or_new_password_answers_400_without_calling_cognito`) |
| M29 middleware nunca trata a exceção | KILLED (`test_a_response_that_cannot_be_rendered_debug_off`) |
| M30 middleware também trata caminhos fora de `/api/` | KILLED (`test_a_path_outside_api_keeps_the_django_500`) |

Nenhum mutante sobreviveu, então não há lição a registrar (um PASS limpo não grava nada).

## Desvios e acréscimos em relação ao spec

- **PD-25 vale para os dois cadastros.** O cadastro por e-mail antes aceitava qualquer `role`. Agora recusa com `#/role`. A fixture de `preferences/tests.py` cadastrava `role: "professional"` e foi trocada por `customer`.
- **Validação antes do 409 no cadastro.** Campo ausente responde 400 antes de e-mail ou telefone repetido responderem 409.
- **Validações extras para não virar 500:** ids que não são inteiros (reserva, avaliação, serviço da agenda, `preferences`), horários fora de HH:MM, `price` e `duration` não numéricos, `rating` não finito. Todas viram `validation-error` com o campo apontado.
- **Lote de disponibilidade valida antes de escrever.** Um item inválido não cria nem apaga nada. A duplicidade no meio do lote continua parcial (Deferred Ideas do spec: tornar o lote atômico).
- **`get_available_slots`** devolve `status: 404` no dict interno para serviço ausente (era 500). Só o chatbot lê esse dict.
- **`hairdresser_profile_ai_completion`** valida `preferences` e devolve 400 quando não é uma lista de ids. Antes um corpo sem `preferences` dava 500.
- **`ProblemDetailsMiddleware`, fora do design original.** A revisão final apontou que o DRF só envolve a chamada da view: uma view que não devolve resposta, ou dados que o renderer JSON não codifica, escapam do `exception_handler` e o Django serve HTML de 500 com `DEBUG=True`. O caso foi reproduzido por teste antes da correção. As views com `pass` (`UpdateReserve`, `UpdateAgenda`) têm a rota comentada e respondem 404 problem+json, então não eram alcançáveis.
- **App:** a descrição por IA no cadastro mostra o texto do catálogo para `too-many-requests` e `ai-service-unavailable`.

## Não verificado

- **Leitores de status e corpo no app:** conferido por busca (`grep`), não por execução. Só `deleteService` e `deleteReview` chamam DELETE e nenhum lê o corpo, e nenhuma tela compara status das rotas que mudaram (201→200, 400→409).
- **UAT das cinco telas** (login por e-mail, login e cadastro por Google, cadastro com descrição e preferências, confirmação de reserva). Precisa do app rodando (web ou Android) contra o backend. O que está provado é o contrato do servidor real, o mapeamento slug → texto no jest e a compilação de tipos. Não está provado o texto na tela.
- **Tela de exclusão de serviço** com um serviço que tem agendamento (PD-84) e **busca de CEP** com CEP inexistente (PD-85), também só no UAT.
- **Fluxos com Cognito real na AWS.** Os testes usam o Cognito em memória, e o servidor real rodou contra o MiniStack.
