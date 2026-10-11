# Notificações push Validation

**Date**: 2026-10-11
**Spec**: `.specs/features/push-notifications/spec.md`
**Diff range**: `fb3d11a..HEAD` (branch `182-notificacoes-push`, 20 commits de código e de status)
**Verifier**: passada independente do mesmo agente, sem sub-agente (fallback do skill: o usuário escolheu executar sem sub-agentes). Reli o `spec.md` e o diff do zero, derivei a cobertura com evidence-or-zero e rodei o sensor num `git worktree` descartável, em um segundo container.

**Overall**: ✅ PASS no backend (NOTIF-01 a NOTIF-11, 19 a 30, 32, 33, 35, 36, 38 a 46, 59 a 62, 64 a 66, 68 a 73, 77). ⚠️ O app (NOTIF-12 a 18, 31, 34, 37, 47 a 58, 63, 67, 74 a 76) está **Implemented, não Verified**: o gate é `tsc` e o bundle, e o UAT em aparelho (T20 a T23) está PENDENTE com o usuário.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 | ✅ Done | Slug `push-unavailable`, 42 slugs |
| T2 | ✅ Done | App `notifications`, `PushDevice`, `Alert`, migração `0001_initial` |
| T3 | ✅ Done | `SnsService`, `FakeSns`, settings, reset no runner |
| T4 | ✅ Done | Go/no-go do SNS no LocalStack passou; a platform application precisou de `PlatformPrincipal` e de JSON no `--attributes` |
| T5 | ✅ Done | Mensagens do catálogo |
| T6 | ✅ Done | `notify`, `publish_alert`, `delete_endpoints` |
| T7 | ✅ Done | RT-100, RT-101 |
| T8 | ✅ Done | Endpoints apagados na exclusão da conta |
| T9 | ✅ Done | RT-102 a RT-104 |
| T10 | ✅ Done | N01 pelo app e pelo chatbot |
| T11 | ✅ Done | N11, N12 (o REV-28 foi ajustado com o aval do usuário) |
| T12 | ✅ Done | N13, N14 |
| T13 | ✅ Done | `expo-notifications`, plugin, `app.config.js` |
| T14 | ✅ Done | Serviços, tipos e slug |
| T15 | ✅ Done | `push-registration` (nativo e web) |
| T16 | ✅ Done | `usePushNotifications`, `alertRoute`, logout |
| T17 | ✅ Done | Caixa de alertas e duas telas |
| T18 | ✅ Done | Menu com contador |
| T19 | ✅ Done | E2E de API (48 de 48), abaixo |
| T20 | ⏭️ Manual | Projeto Firebase: do usuário |
| T21 | ⏭️ Manual | Dev build: depende da T20 |
| T22 | ⏭️ Manual | AWS de produção: do usuário |
| T23 | ⏭️ Pendente | UAT no Android e no web: depende da T21 e da T22 |

---

## Spec-Anchored Acceptance Criteria (backend)

Arquivos de teste, sob `backend/`: `V` = `notifications/tests/test_views.py`, `D` = `notifications/tests/test_dispatch.py`, `S` = `notifications/tests/test_sns.py`, `M` = `notifications/tests/test_models.py`, `G` = `notifications/tests/test_messages.py`, `R` = `reserve/tests.py`, `W` = `review/tests.py`, `P` = `hairmatch/test_problems.py`.

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| NOTIF-01 `POST` de token novo | 201 `{"data": {"id"}}`, endpoint no SNS, uma linha | `V:45` `assertEqual(response.status_code, 201)`; `V:46` `assertEqual(response.json(), {'data': {'id': device.id}})`; `V:49` `assertEqual(self.fake.endpoints[device.endpoint_arn], {'Token': TOKEN, 'Enabled': 'true'})` | ✅ PASS |
| NOTIF-02 token que já é da conta | 200, mesmo `id`, uma linha | `V:58` status 200; `V:59` `{'data': {'id': first}}`; `V:60` `assertEqual(self.rows(), before)`; `V:61` `assertEqual(len(self.fake.created), 1)` | ✅ PASS |
| NOTIF-03 token de outra conta | passa para o usuário da sessão, 201, a outra conta perde o aparelho | `V:69` status 201; `V:70` mesmo `id`; `V:71` `assertEqual([...], [(self.user.id, TOKEN)])`; `V:72` `assertEqual(PushDevice.objects.filter(user=self.other).count(), 0)` | ✅ PASS |
| NOTIF-04 nunca duas linhas | `UNIQUE(token)` e `POST` simultâneo com uma linha | `M:27` `assertRaises(IntegrityError)`; `M:30` `assertEqual(PushDevice.objects.filter(token='token-1').count(), 1)`; `V:87` e `V:88` (perde a corrida e responde com a linha vencedora); `V:229` `assertEqual(PushDevice.objects.filter(token=TOKEN).count(), 1)`; `V:230` `assertEqual(sorted(statuses), [200, 201])` | ✅ PASS |
| NOTIF-05 token inválido | 400 `validation-error` em `#/token`, nenhuma linha | `V:115` `assertEqual([error['pointer'] ...], ['#/token'])` para ausente, não string, `null`, vazio, só espaços e 1025 caracteres; `V:116` e `V:117` nada gravado; `V:95` `strip()`; `V:101` e `V:102` 1024 passa | ✅ PASS |
| NOTIF-06 SNS falha no registro | 503 `push-unavailable`, nenhuma linha, log sem o token | `V:126` `assert_problem(response, 'push-unavailable')`; `V:127` `count() == 0`; `V:129` a `V:131` log com a operação e o código, `assertNotIn(TOKEN, text)`; `S:65` `assertEqual(raised.exception.code, 'InternalError')`; `P:45` `(503, 'Push service unavailable')` | ✅ PASS |
| NOTIF-07 `DELETE` do aparelho | 204 sem corpo, linha apagada, endpoint apagado depois do commit | `V:156` `assertEqual((response.status_code, response.content), (204, b''))`; `V:157` `count() == 0`; `V:158` `fake.deleted == []` antes do commit; `V:161` `assertEqual(self.fake.deleted, [self.arn])` depois | ✅ PASS |
| NOTIF-08 `{id}` inexistente ou de outra conta | 404 `not-found`, nada apagado | `V:170` a `V:172` (outra conta: `rows() == before`, `fake.deleted == []`); `V:178` e `V:179` (inexistente) | ✅ PASS |
| NOTIF-09 sem sessão | 401 `invalid-session`, nada muda | `V:137` a `V:139` (`POST`); `V:185` a `V:187` (`DELETE`) | ✅ PASS |
| NOTIF-10 falha ao apagar o endpoint | 204 mantido, falha no log | `V:197` `assertEqual(response.status_code, 204)`; `V:199` `assertIn('sns delete_endpoint failed: InternalError', ...)` | ✅ PASS |
| NOTIF-11 exclusão da conta | linhas de aparelho apagadas e, depois do commit, os endpoints | `V:258` `PushDevice ... count() == 0`; `V:263` `assertEqual(sorted(self.fake.deleted), sorted(self.arns))`; `V:271` e `V:273` os de outra conta ficam; `V:297` e `V:298` o desfazer do Cognito não apaga endpoint | ✅ PASS |
| NOTIF-19 grava o alerta | alerta não lido com `kind`, título, corpo e dados | `D:45` `assertEqual((saved.recipient, saved.kind, saved.title, saved.body, saved.data, saved.read_at), (...,  None))`; `R:888` a `R:891` e `W:2496` a `W:2499` (mesma tupla para reserva, review e nota) | ✅ PASS |
| NOTIF-20 ação desfeita | nenhum alerta e nenhum push | `D:98` `Alert.objects.count() == 0`; `D:99` `assertEqual(callbacks, [])`; `D:100` `fake.published == []`; `D:86` e `D:87` nada publicado antes do commit | ✅ PASS |
| NOTIF-21 push depois do commit | título, corpo e `alert_id`/`kind` (strings) em cada aparelho | `D:61` `assertEqual(sorted(self.fake.published ...), sorted([... 'data': {'alert_id': str(alert.pk), 'kind': ...}]))`; `S:100` e `S:101` payload FCM v1 com `data` em strings e `channel_id == 'default'`; E2E `N01` | ✅ PASS |
| NOTIF-22 sem aparelho | alerta gravado, SNS não chamado | `D:76` `Alert.objects.count() == 1`; `D:77` `assertEqual([name for name, _ in self.fake.calls if name == 'publish'], [])` | ✅ PASS |
| NOTIF-23 falha ao publicar | alerta e resposta mantidos, log sem token | `D:125` e `D:126` (o segundo aparelho recebe); `D:127` `logs.output == ['WARNING:notifications.sns:sns publish failed: InternalError']`; `D:138` e `D:139` (erro inesperado não sai do commit); `R:952` a `R:954` (`201`); `R:964` e `R:965` (chatbot); `W:2607` a `W:2611` (a exclusão da review segue) | ✅ PASS |
| NOTIF-24 endpoint desativado ou inexistente | linha apagada, envio segue nos outros | `D:175` a `D:177` (`[alive.pk]`, `fake.deleted == [dead.endpoint_arn]`, só o vivo recebe); `D:188` `PushDevice.objects.count() == 0`; `S:109` a `S:132` os três códigos viram `EndpointGone`; E2E `N-24` | ✅ PASS |
| NOTIF-25 texto montado antes de apagar | texto da review e da nota removidas | `W:2540` e `W:2680` `assert_alert_and_push('review-deleted', ... 'removeu a avaliação do seu atendimento.')`. Os testes provam o texto, não a ordem: o Django mantém os campos depois do `delete()`, então a inversão é um mutante equivalente | ✅ PASS (ver nota abaixo) |
| NOTIF-26 nunca notifica o autor | nenhum alerta, `None` | `D:109` `assertIsNone(result)`; `D:110` `Alert.objects.count() == 0`; `D:111` `(callbacks, self.fake.published) == ([], [])`; E2E `N-26` | ✅ PASS |
| NOTIF-27 relógio de Manaus | 13:00 UTC → 09:00; 03:30 UTC do dia 2 → 23:30 do dia 1 | `G:155` `assertIn('para 20/10 às 09:00.', ...)`; `G:161` `assertIn('para 01/11 às 23:30.', ...)`; `G:169` fuso de São Paulo → `09:00`; `R:888` `'... para 04/03 às 10:00.'` para 14:00 UTC | ✅ PASS |
| NOTIF-28 reserva pelo app | cabeleireiro do serviço recebe `reservation-created` | `R:902` status 201; `R:903` e `R:888` a `R:896` (tupla do alerta e o push); E2E `N01` | ✅ PASS |
| NOTIF-29 reserva pelo chatbot | o mesmo `reservation-created` | `R:910` `assertTrue(result.get('success'))`; `R:911` `assert_one_alert_and_push(result['reserve'].pk)` | ✅ PASS |
| NOTIF-30 reserva não criada | nenhum alerta (409 ×2, 400, 404) | `R:928` `assert_problem(attempt(), name)` para os quatro; `R:930` `Alert.objects.count() == 0`; `R:941` e `R:942` (chatbot) | ✅ PASS |
| NOTIF-32 review criada | `review-created` com a nota | `W:2510` status 201; `W:2511` `assert_alert_and_push('review-created', 'Nova avaliação', 'Test Customer avaliou seu atendimento com 5 estrelas.', ...)` | ✅ PASS |
| NOTIF-33 review não criada | nenhum alerta (409, 403, 404, 400) | `W:2557` `assert_problem(attempt(), name)`; `W:2559` e `W:2560` | ✅ PASS |
| NOTIF-35 nota criada | `customer-rating-created` com a nota | `W:2655` status 201; `W:2656` `assert_alert_and_push('customer-rating-created', 'Você foi avaliado', 'Test Hairdresser deu nota 4 para você.', ...)`; `W:2660` a média continua | ✅ PASS |
| NOTIF-36 nota não criada | nenhum alerta (409 ×2, 403, 404, 400) | `W:2703` e `W:2706`; `W:2708` e `W:2709` | ✅ PASS |
| NOTIF-38 `GET` dos alertas | 200 `{alerts, unread_count}`, 50 mais recentes, formato `{id, kind, title, body, data, read, created_at}` | `V:334` status 200; `V:338` `assertEqual(body['alerts'][0], {...})`; `V:343` `created_at` igual ao do banco; `V:363` `len(alerts) == 50`; `V:384` `unread_count == 50` (inclui os fora da página); `V:403` `{'data': {'alerts': [], 'unread_count': 0}}` | ✅ PASS |
| NOTIF-39 ordem e isolamento | `created_at` desc, `id` desc no empate, só os da conta | `V:362` ordem com inserção invertida; `V:373` empate; `V:395` e `V:396` outra conta fora; `M:61` e `M:70` na ordem do modelo | ✅ PASS |
| NOTIF-40 `PATCH` de um alerta | grava o estado, 200 com o alerta | `V:421` a `V:424` (`read: true`, `read_at >= before`); `V:433` a `V:435` (`read: false`, `read_at is None`) | ✅ PASS |
| NOTIF-41 `PATCH` da coleção | todos lidos, 204 sem corpo | `V:485` `(204, b'')`; `V:486` os 3 da conta; `V:488` o de outra conta intacto | ✅ PASS |
| NOTIF-42 `read` ausente ou não booleano | 400 em `#/read` | `V:458` e `V:521` `assertEqual([error['pointer'] ...], ['#/read'])` para ausente, `"true"`, `1`, `null` | ✅ PASS |
| NOTIF-43 `PATCH` da coleção com `false` | 400 em `#/read`, nada muda | `V:507` `assert_problem(response, 'validation-error')`; `V:508` `['#/read']`; `V:511` lido continua lido, não lido continua não lido | ✅ PASS |
| NOTIF-44 `{id}` inexistente ou de outra conta | 404 `not-found` | `V:441` e `V:443` (outra conta, continua não lido); `V:449` (inexistente) | ✅ PASS |
| NOTIF-45 sem sessão | 401 `invalid-session` nas três rotas | `V:472` e `V:474`; `V:536` `assert_problem(call(), 'invalid-session')` para `GET`, `PATCH` da coleção e `PATCH` do alerta | ✅ PASS |
| NOTIF-46 exclusão da conta | alertas da conta apagados | `V:259` `Alert.objects.filter(recipient_id=...).count() == 0`; `V:272` `assertEqual(list(Alert.objects.all()), [self.kept_alert])`; `M:80` | ✅ PASS |
| NOTIF-59 review editada | `review-updated` com a nota nova | `W:2525` status 200; `W:2526` `assert_alert_and_push('review-updated', ... 'atualizou a avaliação do seu atendimento: 4,5 estrelas.', ...)` | ✅ PASS |
| NOTIF-60 review excluída | `review-deleted` | `W:2538` 204; `W:2539` `Review.objects.count() == 0`; `W:2540` `assert_alert_and_push('review-deleted', ...)` | ✅ PASS |
| NOTIF-61 edição ou exclusão que falha | nenhum alerta (400, 404) | `W:2575` `assert_problem(attempt(), slug)`; `W:2577` e `W:2578` | ✅ PASS |
| NOTIF-62 foto não notifica | `POST` e `DELETE` de foto sem alerta | `W:2591` `(201, 204)`; `W:2592` e `W:2593` | ✅ PASS |
| NOTIF-64 nota editada | `customer-rating-updated` com a nota nova | `W:2667` status 200; `W:2668` `assert_alert_and_push('customer-rating-updated', ... 'mudou sua nota para 1.')`; `W:2672` média 3.0 | ✅ PASS |
| NOTIF-65 nota removida | `customer-rating-deleted` | `W:2679` 204; `W:2680` `assert_alert_and_push('customer-rating-deleted', ...)`; `W:2683` média 5.0 | ✅ PASS |
| NOTIF-66 edição ou remoção que falha | nenhum alerta (400, 403, 404) | `W:2715` a `W:2720`; `W:2722` e `W:2723` | ✅ PASS |
| NOTIF-68 init cria `hairmatch-dev-fcm` | platform application criada com credencial falsa | Sem teste automatizado (script de shell). Evidência: o log do LocalStack mostra `Creating SNS platform application: hairmatch-dev-fcm` nos três boots, o reboot é idempotente, e o E2E `LocalStack restarted ...` usa a aplicação recriada | ✅ PASS (manual) |
| NOTIF-69 ARN pelo nome | vazio → `hairmatch-dev-fcm`, mesmo na 2ª página; preenchido → o valor da setting | `S:234` `assertEqual(arn, 'arn:aws:sns:us-east-2:123456789012:app/GCM/hairmatch-dev-fcm')`; `S:250` `assertEqual(self.service.platform_application_arn, APP_ARN)`; E2E contra o LocalStack | ✅ PASS |
| NOTIF-70 fake nos testes | `get_sns()` devolve o `FakeSns` | `S:267` `assertIsInstance(get_sns().client, FakeSns)` | ✅ PASS |
| NOTIF-71 `.env.example` | documenta `SNS_PLATFORM_APPLICATION_ARN` | `docker/.env.example:73` `SNS_PLATFORM_APPLICATION_ARN=`, com o comentário de dev e de produção; `docker/docker-compose.yml:70` | ✅ PASS (leitura do arquivo) |
| NOTIF-72 vários aparelhos | publica em todos | `D:61` `sorted(published) == sorted([first, second])` com um terceiro aparelho de outro usuário fora | ✅ PASS |
| NOTIF-73 dono no momento do envio | o aparelho que mudou de dono não recebe | `D:200` `assertEqual(self.fake.published, [])`; `D:210` `assertEqual([push['arn'] ...], [device.endpoint_arn])` | ✅ PASS |
| NOTIF-77 sem token nem ARN no log | nenhum dos dois em nenhuma linha | `S:84` e `S:164` (`logs.output` exato); `D:160` `assertNotIn(TOKEN_1, text)`; `D:161` `assertNotIn(device.endpoint_arn, text)`; `V:131`; E2E: o log do servidor só tem a operação e o código | ✅ PASS |

**Spec-precision gaps** (o spec não define o resultado; escolha registrada, não falha):

1. **Ordem do corpo e do `{id}` no `PATCH /api/users/me/alerts/{id}`.** O spec diz "primeiro a sessão (401), depois o corpo (400) ou o `{id}` (404)". Implementei o corpo primeiro (L-019), com o teste `V:466` `assert_problem(response, 'validation-error')` para corpo inválido em alerta inexistente. O spec devia dizer a ordem.
2. **`read: true` num alerta já lido.** O spec diz "gravar o estado". O `PATCH` da coleção mantém o `read_at` original (`V:498` `assertEqual(already.read_at, before)`). O do alerta único também não o regrava. O spec não define.
3. **"Não existe" no NOTIF-24.** O LocalStack responde `InvalidParameter` com o texto "No endpoint found for the target arn specified" onde o SNS documenta `NotFound`. O código trata os dois (`S:125`) e mantém o aparelho para qualquer outro `InvalidParameter` (`S:135`). **Não verifiquei na AWS real** qual código ela devolve para um endpoint apagado. O `NotFound` é o que a documentação do SNS lista.

**Status**: ✅ All backend ACs covered, 3 spec-precision gaps flagged

---

## Discrimination Sensor

Sensor leve (18 mutações de comportamento, acima do mínimo, por causa de auth, dados e serviço externo). Rodei num `git worktree` descartável do `HEAD`, num segundo container (`hairmatch-django`, `--entrypoint python`, banco próprio por mutante) e testei `notifications reserve review hairmatch`. A base sem mutação passa (`Ran 436 tests ... OK`). Depois removi o worktree e os bancos, e `git status --porcelain` da árvore real ficou idêntico ao de antes.

| Mutation | File | Description | Killed? |
| -------- | ---- | ----------- | ------- |
| M1 | `notifications/dispatch.py` | Removi o `transaction.on_commit` da publicação | ✅ Killed (`D:179`) |
| M2 | `notifications/dispatch.py` | `EndpointGone` não apaga a linha do aparelho | ✅ Killed (`D:179`) |
| M3 | `notifications/dispatch.py` | Notifica o autor (`if False:`) | ✅ Killed (`D:102`) |
| M4 | `notifications/dispatch.py` | Publica só no primeiro aparelho (`[:1]`) | ✅ Killed (`D:165`) |
| M5 | `notifications/views.py` | O aparelho não troca de dono | ✅ Killed (`V:63`) |
| M6 | `notifications/views.py` | A corrida perdida vira erro (`raise`) | ✅ Killed (`V:74`) |
| M7 | `notifications/views.py` | O token mantém os espaços | ✅ Killed (`V:90`) |
| M8 | `notifications/views.py` | `DELETE` apaga o aparelho de qualquer conta | ✅ Killed (`V:163`) |
| M9 | `notifications/views.py` | `GET` devolve todos os alertas, sem o corte de 50 | ✅ Killed (`V:354`) |
| M10 | `notifications/views.py` | `read: false` marca tudo como lido | ✅ Killed (`V:500`, `V:513`) |
| M11 | `notifications/views.py` | `PATCH` alcança o alerta de qualquer conta | ✅ Killed (`V:437`) |
| M12 | `notifications/sns.py` | Não reativa o endpoint (`SetEndpointAttributes`) | ✅ Killed (`S:306`) |
| M13 | `reserve/views.py` | O chatbot não notifica | ✅ Killed (`R:905`) |
| M14 | `reserve/views.py` | A reserva pelo app não notifica | ✅ Killed (`R:897`) |
| M15 | `review/views.py` | A review nova não notifica | ✅ Killed (`W:2505`) |
| M16 | `review/customer_ratings.py` | A nota editada não notifica | ✅ Killed (`W:2662`) |
| M17 | `users/views.py` | A exclusão da conta não apaga os endpoints | ✅ Killed (`V:275`) |
| M18 | `notifications/messages.py` | 1,5 estrela no singular (`>= 1`) | ✅ Killed (`W:2505`) |

**Nota sobre o M12**: o teste do `Stubber` (`S:43`) também cobre a segunda chamada com `assert_no_pending_responses`. O mutante morreu primeiro no `FakeSnsTest` (`S:306`), e o `CreateEndpointTest` o mataria sozinho.

**Mutante equivalente**: inverter a ordem "montar o texto, depois apagar" (NOTIF-25) não muda o resultado, porque o Django mantém os campos do objeto depois do `delete()`. O teste prova o texto (`W:2540`, `W:2680`) e não consegue provar a ordem. Não gera fix task.

**Sensor depth**: lightweight (18 mutações)
**Result**: 18/18 killed - PASS ✅

---

## E2E de API contra servidor real (T19)

Servidor Django da branch na porta 8001, banco descartável `hairmatch_e2e_push`, o MiniStack para o Cognito e o **LocalStack real para o SNS** (sem o fake). **48 de 48** verificações passaram, em três fases, com o LocalStack parado entre a 1ª e a 2ª e reiniciado antes da 3ª.

**Fase 1 (29 de 29), LocalStack no ar:**

- Cliente e cabeleireiro registrados e logados pela API, cada um com um token falso: `POST /api/users/me/push-devices` 201, repetição 200 com o mesmo `id`, token vazio 400, sem sessão 401. Os dois endpoints existem no LocalStack.
- **Reserva (N01)**: `POST /api/reservations` 201. O cabeleireiro tem um alerta `reservation-created` não lido com o texto `E2E Customer reservou Corte E2E para dd/mm às HH:MM.` no relógio de Manaus. O LocalStack guardou o push no endpoint dele, com título `Nova reserva`, o mesmo corpo e `alert_id`/`kind` nos dados. O cliente (autor) não recebeu alerta nem push.
- **Review (N11, N12)**: uma reserva já terminada, `POST /api/reviews` 201, `PUT` 200 (nota 4,5) e `DELETE` 204 gravam `review-created` ("com 4 estrelas"), `review-updated` ("4,5 estrelas") e `review-deleted`, na ordem, e o LocalStack recebe os cinco pushes do cabeleireiro em ordem.
- **Nota (N13, N14)**: `POST /api/customer-ratings` 201, `PUT` 200, `DELETE` 204 gravam os três alertas do cliente com o texto do spec, e o LocalStack recebe os três pushes dele.
- **Caixa**: `GET` devolve 5 alertas, o mais novo primeiro, `unread_count` 5. `PATCH` de um alerta 200 e contador 4. `PATCH` da coleção 204 e contador 0. A caixa do cliente é separada (3 não lidos). O alerta de outro usuário responde 404.

**Fase 2 (6 de 6), LocalStack parado:** `POST /api/reservations` responde 201 em 0,7 s, a reserva e o alerta ficam gravados (NOTIF-23), e o registro de um aparelho responde 503 `push-unavailable` sem gravar linha. O log do servidor tem `sns publish failed: EndpointConnectionError` e `sns create_platform_endpoint failed: EndpointConnectionError`, sem token nem ARN.

**Fase 3 (13 de 13), LocalStack reiniciado (estado vazio):** o init recriou a platform application. Uma reserva nova encontra o endpoint do cabeleireiro morto (`InvalidParameter`), e a linha do aparelho dele é apagada (NOTIF-24). O aparelho do cliente se registra de novo (201, endpoint existe), o `DELETE` do logout responde 204 e o endpoint **sai do LocalStack**, o segundo `DELETE` responde 404. Um novo aparelho é registrado e `DELETE /api/users/me` responde 204: as linhas, os alertas e o **endpoint no LocalStack** somem.

**O E2E achou um defeito** que os testes unitários não pegaram: o LocalStack responde `InvalidParameter` ao publicar num endpoint apagado, e a primeira versão só tratava `NotFound`, então a linha do aparelho morto ficava (fase 3, `N-24`, 1 falha). Corrigi em `fix(notifications): drop the device of an endpoint LocalStack lost`, com dois testes (`S:125`, `S:135`), e refiz as três fases do zero com um servidor novo (o primeiro rerun ainda falava com o servidor antigo, que não tinha morrido: confirmei pelo `ps` e refiz).

O servidor, o banco e os usuários do Cognito foram removidos. O banco de dev não foi tocado. O LocalStack ficou saudável, com a platform application recriada.

---

## App (NOTIF-12 a 18, 31, 34, 37, 47 a 58, 63, 67, 74 a 76)

Sem teste automatizado, por decisão do spec (o app não tem suíte). O que foi verificado sem aparelho:

- `npx tsc --noEmit`: **0 erros**, antes (baseline) e depois, com os tipos de rota regenerados pelo Metro.
- O Metro empacotou **web** (HTTP 200, 9,7 MB) e **android** (HTTP 200, 12,6 MB) com as telas e os módulos novos. O bundle **web não contém** `expo-notifications` (0 ocorrências de `expo-notifications/build` e `ExpoNotifications`), e o android contém (68). É o NOTIF-18 no nível do bundle.
- O comportamento de rede de que as telas dependem (registro, alertas, leitura, contador, logout) está provado no E2E acima.
- `relativeTime` conferido à mão: "agora", "há 5 min", "há 59 min", "há 3 h", "ontem" e `09/10`.

**Não verificado** (UAT da T23, com o dev build, o Firebase e a AWS reais): a permissão pedida uma vez, o token FCM, o push chegando em primeiro e segundo plano e com o app fechado, o toque com o app fechado (risco R4), a troca de conta, o que aparece na tela (destaque do não lido, contador, "99+", lista vazia, `ErrorModal`) e o web sem pedir permissão. Esses requisitos ficam **Implemented**.

---

## Interactive UAT Results

| # | Test | Result | Details |
| - | ---- | ------ | ------- |
| 1 a 7 | Roteiro da T23 no Android e no web | ⏭️ Skip | Pendente com o usuário: depende da T20 (Firebase), da T21 (dev build), da T22 (AWS) e do deploy da branch no preview, que exige o aval do usuário. |

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ Um app novo com 8 arquivos de código; o app mobile ganhou 2 serviços, 3 hooks, 1 componente, 2 telas e 1 módulo nativo |
| Surgical changes | ✅ Cada commit toca só os arquivos da tarefa. O WIP do usuário (`.env.example`, `package.json`, `package-lock.json`, `axios-instance.ts`, `eslint.config.js`, `docs/`, o spec #189) não entrou em nenhum commit |
| No scope creep | ✅ Sem iOS, WhatsApp, lembretes nem opt-in por categoria |
| Matches patterns | ✅ Segue `cognito.py` e `cognito_fake.py`, `favorite`, `useFavoriteHairdressers` e `favorites.tsx` |
| Spec-anchored outcome check (asserted values match spec) | ✅ Tabela acima |
| Per-layer Coverage Expectation met | ✅ Cada rota tem caminho feliz, cada status de erro e "nada mudou"; o `dispatch` cobre NOTIF-19 a 26 e 72/73 |
| Every test maps to a spec requirement | ✅ Os testes citam o NOTIF na docstring ou no nome; os de infraestrutura (`FakeSnsTest`, `test_the_lookup_is_done_once`) sustentam NOTIF-69/70 e o NOTIF-06 |
| Documented guidelines followed | none - strong defaults applied (nenhum `AGENTS.md` nem limite de cobertura) |

**Desvios do desenho, sem `SPEC_DEVIATION`** (nenhum muda um critério):

- `getLastNotificationResponse()` (síncrono) no lugar de `getLastNotificationResponseAsync()`: o SDK 57 marca o segundo como deprecated. Mais `clearLastNotificationResponse()` depois de tratar o toque, para o mesmo toque não voltar.
- `discardPendingAlertTap()` no bootstrap do layout raiz quando não há sessão: o toque que abriu o app sem sessão não pode abrir um alerta depois de um login futuro (NOTIF-76). Não estava no desenho.
- O corpo do alerta é cortado em 300 caracteres (`messages.py`): um serviço de 200 caracteres e dois nomes longos estourariam a coluna e desfariam a reserva. Não estava no desenho.
- A platform application local ganhou `PlatformPrincipal: fake`, porque o LocalStack recusa `PlatformCredential` sem ele, e o `--attributes` usa JSON, porque a sintaxe curta do CLI recusa as aspas da credencial.
- `AlertTap` ficou em `models/Alert.types.ts`, e o union do app é `ProblemSlug` (o `tasks.md` dizia `ApiProblemSlug`).
- `app.config.js` só define `android.googleServicesFile` quando a variável `GOOGLE_SERVICES_JSON` existe ou o arquivo local existe. A primeira versão sempre apontava para o arquivo, e o `expo prebuild` falhava sem ele (reproduzido numa cópia descartável do app: `Cannot copy google-services.json`). Com a correção, o prebuild termina sem o arquivo, o manifesto sai com o canal `default` (`com.google.firebase.messaging.default_notification_channel_id`) e o build sem Firebase só deixa o app sem token (NOTIF-16). O build com push de verdade continua exigindo a T20.
- O REV-28 (`review/tests.py:820`) passou a esperar 2 callbacks de commit (a exclusão dos arquivos e o push). Alterado com o aval explícito do usuário.

---

## Edge Cases

- [x] NOTIF-72: vários aparelhos recebem (`D:61`)
- [x] NOTIF-73: o dono no momento do envio (`D:200`, `D:210`)
- [ ] NOTIF-74: toque com o app fechado. Depende do aparelho; está no UAT (T23)
- [ ] NOTIF-75: toque num push de outra conta abre a caixa. O `PATCH` responde 404 (`V:441`), e o hook abre a caixa; a navegação está no UAT
- [ ] NOTIF-76: toque sem sessão abre o login. No UAT
- [x] NOTIF-77: sem token nem ARN no log (`S:84`, `S:164`, `D:160`, `D:161`, `V:131`)

---

## Gate Check

- **Gate command**: `makemigrations --check --dry-run && coverage run manage.py test --noinput && coverage report -m` no container `hairmatch_backend`, e `npx tsc --noEmit` no app
- **Result**: 1118 passed, 0 failed, 0 skipped. `makemigrations`: sem mudanças. Cobertura total 99%. `tsc`: 0 erros
- **Test count before feature**: 997 (a baseline em `fb3d11a`; o `git grep -c "def test_"` conta 999, e o runner coleta 997)
- **Test count after feature**: 1118
- **Delta**: +121 testes novos (um existente, o REV-28, teve a contagem de callbacks ajustada com o aval do usuário), nenhum removido
- **Skipped tests**: nenhum
- **Failures**: nenhum no gate. Fora do gate, `manage.py test users` sozinho falha em `PopulateHairdressersCommandTest.test_does_not_rewrite_a_gallery_photo_that_is_in_the_bucket` (acontece também sem as mudanças desta branch, porque o teste depende do storage compartilhado do processo); no gate completo ele passa.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| NOTIF-01 a 11, 19 a 30, 32, 33, 35, 36, 38 a 46, 59 a 62, 64 a 66, 68 a 73, 77 | Implemented | ✅ Verified |
| NOTIF-12 a 18, 31, 34, 37, 47 a 58, 63, 67, 74 a 76 | Implemented | Implemented (UAT pendente) |

---

## Summary

**Overall**: ✅ Ready no backend. ⚠️ O app e a entrega ponta a ponta no aparelho dependem da T20 a T23.

**Spec-anchored check**: 50/50 critérios de backend casam com o resultado do spec, 3 spec-precision gaps
**Sensor**: 18/18 mutações mortas
**Gate**: 1118 passed

**What works**: o registro e a remoção de aparelho, o `notify` na transação com a publicação depois do commit, os sete eventos, a caixa de alertas e o contador, a exclusão da conta, o isolamento da falha do SNS, e tudo isso contra um LocalStack e um servidor reais. O app compila (`tsc` 0 erros) e empacota para web e Android, sem `expo-notifications` no web.

**Issues found**: o E2E achou o `InvalidParameter` do LocalStack (corrigido). Os 3 spec-precision gaps acima.

**Next steps**:

1. O usuário faz a T20 (Firebase) e a T22 (AWS de produção).
2. Gerar o dev build (T21) e rodar o UAT (T23) no preview.
3. Confirmar na AWS real o código que o SNS devolve para um endpoint apagado.
