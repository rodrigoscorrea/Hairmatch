# Preenchimento de Endereço via CEP Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/cep-autocomplete/spec.md`
**Design**: `.specs/features/cep-autocomplete/design.md`
**Status**: Draft (aguardando aprovação para Execute)
**Branch sugerida**: `128-preencher-endereco-via-cep`, criada a partir de `develop`, seguindo o padrão `<issue>-...` do repositório

**Pré-requisitos do Execute:**
- Nenhuma credencial, chave ou cadastro em provedor. ViaCEP e BrasilAPI são abertos, e os testes do backend usam mock.
- Postgres acessível para os testes do backend (`docker compose up db`, com as `DB_*` exportadas), como na google-auth.
- `npm install` em `frontend-mobile/` se `node_modules` não existir, para o gate do app.
- O UAT (T8) precisa de acesso à internet a partir do backend.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas:
> - `.github/workflows/hairmatch-backend-test.yml`: roda `coverage run manage.py test`, sem limite mínimo
> - `backend/users/tests.py`: Django `TestCase` + `APIClient` + `unittest.mock.patch`
> - `frontend-mobile/package.json`: preset `jest-expo`, sem nenhum teste
>
> No frontend vale a mesma decisão confirmada na google-auth (só teste manual). No backend, strong defaults.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: serviço de domínio (`users/cep_lookup.py`) | unit | Todos os ramos; 1:1 com CEP-01 a CEP-08 e CEP-11; todos os edge cases do spec (CEP geral de cidade, `null` da BrasilAPI, `erro` como string e como booleano) | `backend/users/tests.py` (classe nova `CepLookupServiceTest`, mock de `users.cep_lookup.requests.get`) | `cd backend && python manage.py test users` |
| Backend: view e rota (`CepLookupView`) | integration | Rota no escopo: happy path, 400, 404, 503, acesso sem cookie e 429 | `backend/users/tests.py` (classe nova `CepLookupViewTest`, `APIClient` + `reverse('cep_lookup')`, mock de `users.views.lookup_cep`) | `cd backend && python manage.py test users` |
| Frontend: services, hooks, constantes, telas | none | Decisão do usuário. O gate é o `tsc` sem novos erros, mais o roteiro de UAT manual (T8). | - | App gate |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Os testes do backend precisam de Postgres: exporte `DB_HOST/DB_NAME/DB_USER/DB_PASSWORD`, ou rode dentro do container com `docker compose exec django python3 backend/manage.py test users`.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas de backend com testes unit no app `users` | `cd backend && python manage.py test users` |
| Full | Fim da fase de backend (T2) | `cd backend && coverage run manage.py test && coverage report -m` |
| App | Tarefas de frontend (`Tests: none`) | `cd frontend-mobile && npx tsc --noEmit 2>&1 \| grep -c "error TS"`. O resultado precisa ser **≤ baseline** medido antes de T3. |
| Build | Fim da feature (T8) | Full + App |

**Baseline de testes do backend**, contado com `grep -c "def test_"` em `develop` (`297f6d7`):
- **256** métodos `test_` em todo o projeto
- **109** em `backend/users/tests.py`

Nenhuma tarefa pode reduzir esses números. T1 confirma o baseline rodando a suíte antes de mudar qualquer coisa.

**Baseline do App gate**: medir antes de T3 e registrar aqui. A google-auth registrou 4 erros pré-existentes, que servem de referência.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend

```
T1 → T2
```

### Phase 2: App

```
T3 → T5
T4 → T5
T5 → T6
T6 → T7
```

### Phase 3: Fechamento

```
T8
```

---

## Task Breakdown

### Phase 1: Backend (tarefas)

#### T1: Criar o serviço `users/cep_lookup.py`

**What**: Criar o módulo `lookup_cep` com normalização do CEP, cache de 24 h, ViaCEP com fallback para BrasilAPI v2, timeout de 3 s, as exceções `InvalidCep`, `CepNotFound` e `CepServiceUnavailable` e `logger.warning` por falha de provedor. Tudo conforme `design.md`. Os testes unitários ficam na mesma tarefa.
**Where**: `backend/users/cep_lookup.py` (novo). Os testes co-localizados seguem o Location Pattern da matriz.
**Depends on**: None
**Reuses**: formato de `backend/users/google_auth.py`; `requests` já declarado em `backend/requirements.txt`
**Requirement**: CEP-01, CEP-02, CEP-03, CEP-04, CEP-05, CEP-06, CEP-07, CEP-08, CEP-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `CepLookupServiceTest` (com `cache.clear()` no `setUp`) cobre, com `patch('users.cep_lookup.requests.get')`:
  - [x] ViaCEP encontra `69057-000` → devolve exatamente `{postal_code: "69057000", address, neighborhood, city, state}` (CEP-01)
  - [x] A resposta não tem `complemento` nem nenhuma outra chave (CEP-07)
  - [x] `"123"`, `"123456789"` e `""` → `InvalidCep`, com `requests.get` não chamado (CEP-02)
  - [x] ViaCEP com `requests.Timeout`, `requests.ConnectionError`, status 500, JSON inválido, `{"erro": "true"}` e `{"erro": true}` → BrasilAPI é chamada e o resultado dela é devolvido (CEP-03), um teste por causa
  - [x] ViaCEP `erro` + BrasilAPI 404 → `CepNotFound` (CEP-04)
  - [x] ViaCEP timeout + BrasilAPI 404 → `CepNotFound` (CEP-04)
  - [x] ViaCEP timeout + BrasilAPI 500 → `CepServiceUnavailable` (CEP-05)
  - [x] Toda chamada a `requests.get` recebe `timeout=3` (CEP-06)
  - [x] BrasilAPI com `street: null` e `neighborhood: null` → `""` nos dois; ViaCEP de CEP geral com `logradouro: ""` → `""` (CEP-07)
  - [x] A segunda chamada de `lookup_cep('69057000')` não chama `requests.get` (CEP-08)
  - [x] Um `CepNotFound` não é cacheado: a segunda chamada volta a consultar
  - [x] Falha de provedor gera `logger.warning` com `viacep` ou `brasilapi` na mensagem (CEP-11, via `assertLogs('users.cep_lookup', 'WARNING')`)
- [x] Gate check passes: `cd backend && python manage.py test users`
- [x] Test count: ≥ 109 + novos testes em `users`, sem remoções

**Tests**: unit
**Gate**: quick

**Commit**: `feat(backend): add CEP lookup client with ViaCEP and BrasilAPI fallback`

---

#### T2: Expor `GET /api/address/cep/<cep>`

**What**: Criar `CepLookupThrottle` (`AnonRateThrottle` com `scope='cep_lookup'` e `rate='30/min'`) e `CepLookupView`, que traduz as exceções de `lookup_cep` em 200/400/404/503 com as mensagens do spec. Registrar a rota `address/cep/<str:cep>` (name `cep_lookup`) em `users/urls.py`. Os testes de integração ficam na mesma tarefa.
**Where**: `backend/users/views.py`, com a linha da rota em `backend/users/urls.py` (merge backward: sem a rota, a view não é testável)
**Depends on**: T1
**Reuses**: padrão `APIView` + `JsonResponse({'error': ...})` de `backend/users/views.py`; mock `patch('users.views.lookup_cep')` como em `GoogleAuthViewTest`
**Requirement**: CEP-01, CEP-02, CEP-04, CEP-05, CEP-09, CEP-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `CepLookupViewTest` (com `cache.clear()` no `setUp`) cobre:
  - [ ] `GET /api/address/cep/69057-000`, sem cookie, com o serviço devolvendo o dict → 200 com o JSON exato (CEP-01, CEP-09)
  - [ ] `InvalidCep` → 400 `{"error": "CEP inválido. Informe 8 dígitos."}` (CEP-02)
  - [ ] `CepNotFound` → 404 `{"error": "CEP não encontrado."}` (CEP-04)
  - [ ] `CepServiceUnavailable` → 503 `{"error": "Serviço de CEP indisponível. Preencha o endereço manualmente."}` (CEP-05)
  - [ ] 30 requisições seguidas → 200; a 31ª → 429 (CEP-10)
- [ ] `reverse('cep_lookup', args=['69057000'])` resolve para `/api/address/cep/69057000`
- [ ] Gate check passes: `cd backend && coverage run manage.py test && coverage report -m`
- [ ] Test count: ≥ 256 + novos testes no projeto, sem remoções

**Tests**: integration
**Gate**: full

**Commit**: `feat(backend): expose GET /api/address/cep endpoint`

---

### Phase 2: App (tarefas)

#### T3: Criar `services/cep.service.ts`

**What**: Exportar o tipo `CepAddress` e `lookupCep(cep)`, que faz `axiosInstance.get<CepAddress>('/api/address/cep/<cep>')` e propaga o erro do axios.
**Where**: `frontend-mobile/services/cep.service.ts` (novo)
**Depends on**: T2
**Reuses**: `frontend-mobile/services/axios-instance.ts`
**Requirement**: CEP-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Baseline do App gate medido e registrado neste arquivo antes da mudança
- [ ] `CepAddress` tem exatamente `postal_code`, `address`, `neighborhood`, `city` e `state` (todos `string`)
- [ ] Gate check passes: App gate ≤ baseline

**Tests**: none
**Gate**: App

**Commit**: `feat(mobile): add CEP lookup service`

---

#### T4: Adicionar as mensagens de consulta de CEP

**What**: Acrescentar a `ERROR_MESSAGES`:
- `cep_not_found`: "CEP não encontrado. Confira o número ou preencha o endereço manualmente."
- `cep_lookup_failed`: "Não foi possível buscar o CEP. Preencha o endereço manualmente."

**Where**: `frontend-mobile/constants/errorMessages.ts`
**Depends on**: None
**Reuses**: objeto `ERROR_MESSAGES` existente
**Requirement**: CEP-17, CEP-18

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os dois textos batem, caractere por caractere, com CEP-17 e CEP-18 do spec
- [ ] Gate check passes: App gate ≤ baseline

**Tests**: none
**Gate**: App

**Commit**: `feat(mobile): add CEP lookup messages`

---

#### T5: Criar o hook `useCepLookup`

**What**: Criar o hook com `loading`, `message`, `lookup(digits, onFound)` e `cancel()`:
- `latestCepRef` descarta respostas de um CEP que já não é o atual
- 404 → `cep_not_found`
- qualquer outro erro → `cep_lookup_failed`

Comportamento conforme `design.md`.
**Where**: `frontend-mobile/hooks/authHooks/useCepLookup.ts` (novo)
**Depends on**: T3, T4
**Reuses**: padrão `useRef` de `frontend-mobile/hooks/customerHooks/useSearch.ts`
**Requirement**: CEP-12, CEP-16, CEP-17, CEP-18

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Uma resposta com `digits !== latestCepRef.current` não chama `onFound` nem altera `loading` ou `message`
- [ ] `error.response?.status === 404` → `message = ERROR_MESSAGES.cep_not_found`. Qualquer outro erro, inclusive sem `response`, → `cep_lookup_failed`
- [ ] Nenhum caminho abre `ErrorModal`
- [ ] Gate check passes: App gate ≤ baseline

**Tests**: none
**Gate**: App

**Commit**: `feat(mobile): add useCepLookup hook with stale-response guard`

---

#### T6: Ligar a consulta ao `useAddress`

**What**: Acrescentar ao `useAddress`:
- `handlePostalCodeChange(text)`: máscara com `formatCEP`, `lookup` no 8º dígito e `cancel` abaixo de 8
- `applyCepAddress`: merge só dos valores não vazios em `address`, `neighborhood`, `city` e `state`, limpeza dos erros desses campos e foco em `numberInputRef`
- `cepLoading`, `cepMessage` e `numberInputRef` no retorno

Remover também o literal solto `69020405` de `validateFields`.
**Where**: `frontend-mobile/hooks/authHooks/useAddress.ts`
**Depends on**: T5
**Reuses**: `handleInputChange`; `formatCEP` e `stripNonDigits` de `frontend-mobile/utils/forms.ts`
**Requirement**: CEP-12, CEP-13, CEP-14, CEP-19, CEP-21

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `applyCepAddress` nunca escreve em `number` nem em `complement`
- [ ] Um valor `""` na resposta limpa o campo se ele ainda é igual a `lastAutofillRef`, e mantém o campo se o usuário digitou outro valor (CEP-13)
- [ ] `handlePostalCodeChange` chama `lookup` sempre que o campo chega a 8 dígitos, sem dedupe por "último CEP consultado", e chama `cancel` abaixo de 8
- [ ] `validateFields` não muda de regra. Só o literal solto sai.
- [ ] Gate check passes: App gate ≤ baseline

**Tests**: none
**Gate**: App

**Commit**: `feat(mobile): autofill address fields from CEP lookup`

---

#### T7: Reorganizar a tela de endereço

**What**: Em `address.tsx`:
- mover o CEP para a primeira linha, com `onChangeText={handlePostalCodeChange}`, `ActivityIndicator` quando `cepLoading` e um `<Text>` com `cepMessage` abaixo
- deixar a antiga linha "Bairro + CEP" só com Bairro
- ligar `ref={numberInputRef}` ao campo Número
- remover o import de `formatCEP`, que deixa de ser usado

Se precisar de estilo para a mensagem, acrescentar `cepHint` em `styles/register/styles/AdressStyle.ts`.
**Where**: `frontend-mobile/app/(auth)/register/address.tsx`
**Depends on**: T6
**Reuses**: estilos existentes de `AdressStyle`; `ActivityIndicator` do `react-native`
**Requirement**: CEP-15, CEP-19, CEP-20, CEP-21

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O CEP é o primeiro `TextInput` do formulário
- [ ] Nenhum `TextInput` da tela tem `editable={false}`, e o botão "Próximo" não fica desabilitado durante a consulta
- [ ] Gate check passes: App gate ≤ baseline

**Tests**: none
**Gate**: App

**Commit**: `feat(mobile): move CEP to top of address step and show lookup status`

---

### Phase 3: Fechamento (tarefas)

#### T8: Build gate e UAT manual

**What**: Rodar o Build gate, executar o roteiro de UAT abaixo no web e no Android e marcar a traceability do spec. Se o usuário quiser, atualizar a issue #128 com o resumo da investigação, o que exige confirmação explícita por ser uma ação externa.
**Where**: `.specs/features/cep-autocomplete/spec.md` (traceability)
**Depends on**: T2, T7
**Reuses**: roteiro abaixo
**Requirement**: CEP-12, CEP-13, CEP-14, CEP-15, CEP-16, CEP-17, CEP-18, CEP-19, CEP-20, CEP-21

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Build gate passa: Full e App ≤ baseline
- [ ] Os 11 passos do roteiro (1–9, 4b e 4c) passam no web e no Android
- [ ] Traceability de CEP-01 a CEP-21 atualizada em `spec.md`

**Tests**: none
**Gate**: build

**Commit**: `docs(specs): record CEP autocomplete UAT results`

---

## Roteiro de UAT manual (T8)

Pré-requisitos: backend com acesso à internet e app apontando para ele (`EXPO_PUBLIC_API_BACKEND_URL`). Rodar o roteiro no **web** e no **Android**.

| # | Passo | Resultado esperado | Req |
| - | ----- | ------------------ | --- |
| 1 | Cadastro → etapa de endereço | O CEP é o primeiro campo | CEP-20 |
| 2 | Digitar `69057-000` | O spinner aparece; depois rua "Avenida Mário Ypiranga", bairro "Adrianópolis", cidade "Manaus" e UF "AM" são preenchidos. Número e Complemento ficam vazios, e o foco vai para Número. | CEP-12, 13, 14, 15, 21 |
| 3 | Editar a rua preenchida e tocar em Próximo com número preenchido | O campo aceita a edição e o fluxo avança | CEP-19 |
| 4 | Voltar, digitar a rua "Rua Teste" e depois o CEP `78175-000` | Cidade "Poconé" e UF "MT" são preenchidas, e a rua continua "Rua Teste" | CEP-13 |
| 4b | Limpar o formulário, digitar `69057-000` (preenche) e trocar por `78175-000` sem editar rua nem bairro | Rua e bairro ficam vazios, e a cidade vira "Poconé" e a UF "MT" | CEP-13 |
| 4c | Digitar `69057-00`, completar com `0`, apagar o último dígito e redigitar `0` | O preenchimento acontece nas duas vezes em que o CEP chega a 8 dígitos | CEP-12 |
| 5 | Digitar `00000-000` | Aparece o texto "CEP não encontrado. Confira o número ou preencha o endereço manualmente.", sem modal | CEP-17 |
| 6 | Parar o backend e digitar `01001-000` | Aparece o texto "Não foi possível buscar o CEP. Preencha o endereço manualmente.", sem modal. Preencher tudo à mão avança. | CEP-18, 19 |
| 7 | Com o backend lento (DevTools com throttling "Slow 3G" no web), digitar `69057-000` e, antes da resposta, trocar para `01001-000` | Só o endereço de `01001-000` (Praça da Sé, São Paulo/SP) aparece | CEP-16 |
| 8 | Repetir o passo 2 dentro do cadastro via Google | Mesmo resultado do passo 2 | CEP-19 |
| 9 | `curl -i http://<backend>/api/address/cep/69057000` 31 vezes em menos de 1 min | As 30 primeiras respondem 200 e a 31ª responde 429 | CEP-10 |

---

## Phase Execution Map

Phases run in sequence, and tasks within a phase run in order. The dependency arrows are the ones in the Execution Plan above.

```
Phase 1 → Phase 2 → Phase 3

Phase 1:  T1 ------→ T2
Phase 2:  T3, T4 --→ T5 ------→ T6 ------→ T7
Phase 3:  T8
```

**Batches:** são 8 tarefas, que cabem num lote só. A execução é inline, sem sub-agentes. O Verifier roda automaticamente depois de T8.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: `cep_lookup` | 1 módulo + a classe de teste dele | ✅ Granular |
| T2: `CepLookupView` + rota | 1 endpoint + 1 linha em `urls.py` | ⚠️ OK (merge backward: sem a rota, a view não é testável) |
| T3: `cep.service.ts` | 1 função + 1 tipo | ✅ Granular |
| T4: mensagens | 2 constantes | ✅ Granular |
| T5: `useCepLookup` | 1 hook | ✅ Granular |
| T6: `useAddress` | 1 hook (2 funções coesas) | ✅ Granular |
| T7: `address.tsx` | 1 tela (mais 1 estilo, opcional) | ✅ Granular |
| T8: gate + UAT | 1 arquivo de spec | ✅ Granular |

---

## Diagram-Definition Cross-Check

A paridade vale dentro de cada fase. Dependências entre fases apontam sempre para trás.

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | nenhuma seta de entrada | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 (fase 1) | nenhuma seta intra-fase | ✅ Match |
| T4 | None | nenhuma seta de entrada | ✅ Match |
| T5 | T3, T4 | T3 → T5, T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | T6 | T6 → T7 | ✅ Match |
| T8 | T2, T7 (fases 1 e 2) | nenhuma seta intra-fase | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1: `cep_lookup` | serviço de domínio | unit | unit | ✅ OK |
| T2: `CepLookupView` | view/rota | integration | integration | ✅ OK |
| T3–T7 | frontend | none (decisão do usuário) | none | ✅ OK |
| T8: UAT + traceability | documentação | none | none | ✅ OK |

---

## Requirement Coverage

| Requirement | Tasks |
| ----------- | ----- |
| CEP-01 | T1, T2 |
| CEP-02 | T1, T2 |
| CEP-03 | T1 |
| CEP-04 | T1, T2 |
| CEP-05 | T1, T2 |
| CEP-06 | T1 |
| CEP-07 | T1 |
| CEP-08 | T1 |
| CEP-09 | T2 |
| CEP-10 | T2, T8 |
| CEP-11 | T1 |
| CEP-12 | T3, T5, T6, T8 |
| CEP-13 | T6, T8 |
| CEP-14 | T6, T8 |
| CEP-15 | T7, T8 |
| CEP-16 | T5, T8 |
| CEP-17 | T4, T5, T8 |
| CEP-18 | T4, T5, T8 |
| CEP-19 | T6, T7, T8 |
| CEP-20 | T7, T8 |
| CEP-21 | T6, T7, T8 |

**Coverage:** 21 requisitos, 21 mapeados, 0 sem tarefa.
