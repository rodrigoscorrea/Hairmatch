# Cabeleireiros favoritos Validation

**Date**: 2026-10-10
**Spec**: `.specs/features/favorite-hairdressers/spec.md`
**Diff range**: `bfcec74..c5417be` (branch `115-marcar-cabeleireiro-como-favorito`, 11 commits de código e de status)
**Verifier**: passada independente do mesmo agente, sem sub-agente (fallback do skill: o usuário não pediu sub-agentes). Reli o `spec.md` e o diff do zero, derivei a cobertura com evidence-or-zero e rodei o sensor num `git worktree` descartável.

**Overall**: ✅ PASS no backend. ⚠️ O UAT de tela (web e Android) está PENDENTE com o usuário e não conta como verificado.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 | ✅ Done | Modelo, migração `0001_initial` e 6 testes |
| T2 | ✅ Done | `PUT`/`DELETE` (RT-98, RT-99), 12 testes de detalhe e 1 de corrida |
| T3 | ✅ Done | `GET` (RT-97), 9 testes |
| T4 | ✅ Done | 4 testes de ciclo de vida, sem mudança de código |
| T5 | ✅ Done | Tipo e serviço; gate `tsc` |
| T6 | ✅ Done | `useFavoriteToggle`; gate `tsc` |
| T7 | ✅ Done | Coração no perfil público; gate `tsc` |
| T8 | ✅ Done | `useFavoriteHairdressers`; gate `tsc` |
| T9 | ✅ Done | Tela `customer/favorites` e rota sem aba; gate `tsc` |
| T10 | ✅ Done | Item "Favoritos" do perfil liga a tela; gate `tsc` |
| T11 | ⚠️ Partial | E2E de API (46/46) e bundle do Metro feitos; UAT de tela pendente com o usuário |

---

## Spec-Anchored Acceptance Criteria (backend)

Os arquivos de teste são `backend/favorite/tests.py` (`T`) e `backend/hairmatch/test_routes.py`.

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| FAV-01 `PUT` favorita | 204, corpo vazio, uma linha do par | `T:169` `assertEqual(response.status_code, 204)`; `T:170` `assertEqual(response.content, b'')`; `T:172` `assertEqual((favorite.customer_id, favorite.hairdresser_id), (customer_a.id, hairdresser_1.id))` | ✅ PASS |
| FAV-02 `PUT` repetido | 204, uma linha, `created_at` original | `T:181` status 204; `T:182` `assertEqual(self.rows(), before)` (id, par e `created_at`); `T:183` `assertEqual(len(before), 1)` | ✅ PASS |
| FAV-03 par único e `PUT` simultâneo | nunca duas linhas | `T:45` `assertRaises(IntegrityError)`; `T:48` `count() == 1`; `T:320` `assertEqual(statuses, [204] * 4)`; `T:321` `.count(), 1` (5 rodadas) | ✅ PASS |
| FAV-04 `PUT` id inexistente | 404 `not-found`, nenhuma linha | `T:189` `assert_problem(response, 'not-found', 'Hairdresser not found.')`; `T:190` `count() == 0` | ✅ PASS |
| FAV-05 `PUT` cabeleireiro pendente | 404 `not-found`, nenhuma linha | `T:198` `assert_problem(..., 'not-found', ...)`; `T:199` `count() == 0` | ✅ PASS |
| FAV-06 `DELETE` favorito | 204, só o par | `T:208` 204; `T:209` corpo vazio; `T:211` o outro favorito do cliente continua | ✅ PASS |
| FAV-07 `DELETE` de quem não é favorito | 204, nenhuma linha apagada | `T:220` 204; `T:221` `assertEqual(self.rows(), before)` | ✅ PASS |
| FAV-08 `DELETE` id inexistente | 404 `not-found` | `T:240` `assert_problem(response, 'not-found', 'Hairdresser not found.')`; `T:241` linhas intactas | ✅ PASS |
| FAV-09 sem sessão | 401 `invalid-session`, nada muda | `T:250`, `T:251` `assert_problem(..., 'invalid-session')`; `T:253` linhas intactas | ✅ PASS |
| FAV-10 sessão de cabeleireiro | 403 `customer-required`, nada muda | `T:262`, `T:263` `assert_problem(..., 'customer-required')`; `T:265` linhas intactas | ✅ PASS |
| FAV-11 outros clientes | favorito do cliente B continua | `T:275` `assertEqual((remaining.customer_id, remaining.hairdresser_id), (customer_b.id, hairdresser_1.id))` | ✅ PASS |
| FAV-18 formato do item | `{id, user, resume}`, sem CNPJ nem contato | `T:351` `set(response.json()) == {'data'}`; `T:353` `set(item) == {'id','user','resume'}`; `T:359` `assertFalse({'email','phone','postal_code'} & set(item['user']))` | ✅ PASS |
| FAV-19 ordem | recente primeiro, `id` desc no empate | `T:371` ordem pela API com `created_at` reescrito fora da ordem de inserção; `T:69` e `T:85` no modelo | ✅ PASS |
| FAV-20 sem favoritos | 200 `{"data": []}` | `T:380` 200; `T:381` `assertEqual(response.json(), {'data': []})` | ✅ PASS |
| FAV-21 só os do cliente | nunca os de outro | `T:388`, `T:389` `listed_ids` de A e de B | ✅ PASS |
| FAV-22 pendente fora da lista | some e volta ao reativar | `T:397` e `T:400` `assertEqual(self.listed_ids(...), [...])` | ✅ PASS |
| FAV-23 `GET` sem sessão | 401 `invalid-session` | `T:404` `assert_problem(self.anonymous.get(self.URL), 'invalid-session')` | ✅ PASS |
| FAV-24 `GET` de cabeleireiro | 403 `customer-required` | `T:408` `assert_problem(self.hairdresser_client.get(self.URL), 'customer-required')` | ✅ PASS |
| FAV-36 conta do cliente | apaga os dele, mantém os do outro | `T:449` 204; `T:450` `assertEqual(self.pairs(), [(customer_b.id, hairdresser_1.id)])` | ✅ PASS |
| FAV-37 conta do cabeleireiro | apaga os de todos os clientes para ele | `T:460` 204; `T:461` `assertEqual(self.pairs(), [(customer_a.id, hairdresser_2.id)])` | ✅ PASS |
| FAV-38 expurgo | apaga sem erro de FK | `T:472` conta some; `T:473` `pairs() == [(customer_b.id, hairdresser_1.id)]` | ✅ PASS |
| FAV-43 substituição de pendente | apaga sem erro de FK, cadastro 201 | `T:483` `assertEqual(response.status_code, 201)`; `T:484` cliente antigo some; `T:485` pares | ✅ PASS |
| FAV-39 id não inteiro | 404 `not-found` | `T:281` `assert_problem(method('.../abc'), 'not-found')` (`PUT` e `DELETE`); `T:283` `count() == 0` | ✅ PASS |
| FAV-40 favorita, desfavorita, favorita | listado uma vez, na última posição | `T:418` `assertEqual(self.listed_ids(self.client_a), [first.id, second.id])` | ✅ PASS |
| FAV-42 método errado na lista | 405 `method-not-allowed` | `T:422` `assert_problem(self.client_a.put(self.URL), 'method-not-allowed')`; `T:423` `count() == 0` | ✅ PASS |
| RT-97 a RT-99 | rotas na `ROUTE_TABLE`, nenhuma a mais | `backend/hairmatch/test_routes.py:76-78` e `test_api_exposes_exactly_the_route_table` (`assertEqual(sorted(ROUTE_TABLE - found), [])`) | ✅ PASS |

**Spec-precision gaps**: nenhum no backend. O `Allow` do 405 não é fixado de propósito (o DRF acrescenta `HEAD`, como no GAL-43), e o spec não o define.

**Critérios de app** (FAV-12 a FAV-17, FAV-25 a FAV-35, FAV-41): sem teste automatizado por decisão do spec (o app não tem suíte). O gate é `npx tsc --noEmit` (0 erros) mais o UAT. Verificado sem navegador: o app compila e empacota com as telas novas, e o comportamento de rede de que eles dependem foi provado no E2E de API (abaixo). **Não verificado**: o que aparece na tela (coração preenchido, card que some, modal, mensagem de lista vazia, voltar do perfil para a lista). Isso fica para o UAT do usuário.

**Status**: ✅ Backend completo / ⚠️ App aguarda UAT

---

## Discrimination Sensor

Rodado em `git worktree` descartável (`.verify-wt`, removido no fim), contra `favorite` e `hairmatch.test_routes` (41 testes). `git status --porcelain` da árvore real idêntico antes e depois.

| # | File | Mutation | Killed? |
| - | ---- | -------- | ------- |
| 1 | `backend/favorite/views.py` | `get_or_create` do `PUT` trocado por `create` | ✅ Killed (6 falhas) |
| 2 | `backend/favorite/views.py` | `DELETE` de id inexistente responde 204 em vez de 404 | ✅ Killed (1 falha) |
| 3 | `backend/favorite/views.py` | a lista usa o serializer completo, que vaza CNPJ e e-mail | ✅ Killed (1 falha) |
| 4 | `backend/favorite/views.py` | a lista sem a checagem da sessão de cliente | ✅ Killed (8 falhas) |
| 5 | `backend/favorite/models.py` | só o nome da constraint muda (controle, sem efeito de comportamento) | Sobreviveu, como esperado |
| 6 | `backend/favorite/views.py` | o `PUT` responde 200 em vez de 204 | ✅ Killed (16 falhas) |
| 7 | `backend/favorite/urls.py` | `<int:hairdresser_id>` vira `<hairdresser_id>` (aceita `abc`) | ✅ Killed (5 falhas) |

Durante o desenvolvimento, 12 mutações adicionais foram mortas na árvore real e restauradas (sem `Meta.ordering`, sem desempate por `id`, lista sem filtro de cliente, lista com pendente, `PUT` com pendente, `DELETE` sem escopo de cliente, check-then-create no `PUT` com o teste de corrida falhando em 3 de 3 execuções, `PROTECT` no lugar de `CASCADE` nas duas FKs).

**Sensor depth**: lightweight, ampliado (6 de comportamento mais 1 de controle)
**Result**: 6/6 mutações de comportamento mortas ✅ PASS

---

## E2E de API contra servidor real

Servidor Django da branch na porta 8001, banco descartável `hairmatch_e2e_fav` e o MiniStack para o Cognito (como na #118). **46 de 46** verificações passaram: as três rotas com cookies reais, 401 e 403, o formato público, a ordem, o `PUT` repetido (mesma linha e `created_at`), 6 `PUT` simultâneos (uma linha), 404 de id desconhecido, pendente e `abc`, o 405, o isolamento entre clientes, o pendente que sai da lista e volta, o preflight de CORS de `PUT` e `DELETE` a partir do `:8081` (com credenciais) e a exclusão da conta dos dois lados. O servidor, o banco e os usuários do Cognito foram removidos. O banco de dev não foi tocado.

O bundle do Metro (`Web Bundled … 2400 modules`) compila com `customer/favorites`, `useFavoriteToggle`, `useFavoriteHairdressers` e o serviço, sem erro.

---

## Interactive UAT Results

| # | Test | Result | Details |
| - | ---- | ------ | ------- |
| 1 a 7 | Roteiro do T11 em tela, no web e no Android | ⏭️ Skip | Pendente com o usuário. O Claude in Chrome não foi usado, a pedido, e o Android depende do usuário. |

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ Backend: 1 app de 3 arquivos de código, 2 views e 2 rotas. App: 1 serviço, 2 hooks, 1 tela |
| Surgical changes | ✅ Cada commit toca só os arquivos da tarefa; as alterações que já estavam no worktree do usuário não entraram em nenhum commit |
| No scope creep | ✅ Nenhum coração em busca ou home, nada no item do cabeleireiro |
| Matches patterns | ✅ Segue `UserPreferenceView`, `gallery.service.ts`, `useReceivedRatings` e `ratings.tsx` |
| Spec-anchored outcome check (asserted values match spec) | ✅ Tabela acima |
| Per-layer Coverage Expectation met | ✅ Cada rota tem caminho feliz, cada erro e "nada mudou" |
| Every test maps to a spec requirement | ✅ 31 dos 32 testes citam um FAV na docstring; o outro (`DELETE` de pendente responde 204) cobre a premissa registrada no spec |
| Guidelines followed | none - strong defaults applied (nenhum `AGENTS.md` nem limite de cobertura) |

**Ajuste de desenho, sem desvio do spec**: o design descreve o card como um `TouchableOpacity` com o coração dentro. A tela usa a área do perfil e o coração como irmãos dentro do card, para que o toque no coração nunca abra o perfil. FAV-28 e FAV-31 continuam atendidos. Não há `SPEC_DEVIATION`.

---

## Edge Cases

- [x] FAV-39: id não inteiro responde 404
- [x] FAV-40: favorita, desfavorita e favorita de novo lista uma vez
- [ ] FAV-41: voltar do perfil para a lista mostra a mudança. Depende da tela, está no UAT. O hook lê a lista a cada foco.
- [x] FAV-42: `PUT` no path da lista responde 405

---

## Gate Check

- **Gate command**: `makemigrations --check --dry-run && coverage run manage.py test --noinput && coverage report` no container `hairmatch_backend`, e `npx tsc --noEmit` no app
- **Result**: 997 passed, 0 failed, 0 skipped. `makemigrations`: sem mudanças. `tsc`: 0 erros
- **Test count before feature**: 965 (a baseline em `c5d5242`; o `git grep -c "def test_"` conta 967, e o runner coleta 965)
- **Test count after feature**: 997
- **Delta**: +32 testes novos, nenhum removido
- **Cobertura de `favorite/`**: `models.py`, `urls.py` e `views.py` em 100%
- **Skipped tests**: nenhum
- **Failures**: nenhuma

**Nota sobre o `tsc`**: a baseline tinha 9 erros, todos de rotas tipadas que o `.expo/types/router.d.ts` (ignorado pelo git) não conhecia. Subir o Metro regenerou o arquivo, e o `tsc` fechou com 0 erros no projeto inteiro. Quem rodar o gate sem o Metro regenerado verá erros de rota tipada, entre eles o de `/(app)/customer/favorites`.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| FAV-01 a FAV-11, FAV-18 a FAV-24, FAV-36 a FAV-40, FAV-42, FAV-43 | Implemented | ✅ Verified |
| FAV-12 a FAV-17, FAV-25 a FAV-35, FAV-41 | Implemented | Implemented (aguardam o UAT de tela) |

---

## Summary

**Overall**: ✅ Backend pronto / ⚠️ App aguarda UAT

**Spec-anchored check**: 26/26 critérios de backend com a asserção no valor do spec, 0 spec-precision gaps
**Sensor**: 6/6 mutações de comportamento mortas
**Gate**: 997 passed, `tsc` com 0 erros

**What works**: as três rotas, a idempotência, a corrida de `PUT`, o ciclo de vida das contas, o CORS do web, e o app que compila com as telas novas.

**Issues found**: nenhum.

**Next steps**: o UAT do roteiro do T11 no web e no Android. Ao passar, os critérios de app viram Verified.
