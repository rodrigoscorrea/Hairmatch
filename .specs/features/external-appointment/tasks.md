# Atendimento Externo na Agenda Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/external-appointment/spec.md`
**Design**: `.specs/features/external-appointment/design.md`
**Status**: Approved (2026-10-09). Execute ainda não começou: por decisão do usuário, esta etapa produz só os specs.
**Branch**: `113-adicionar-servico-por-fora-na-agenda`, criada a partir de `develop` (`fbf1d08`)

**Pré-requisitos do Execute:**
- `hairmatch_backend` e `hairmatch_db` rodando (`docker start hairmatch_db`).
- Nenhum commit inclui os arquivos que já estavam sujos antes da feature:
  - `frontend-mobile/.env.example`
  - `frontend-mobile/services/axios-instance.ts`
  - `docs/`
  - `.specs/LESSONS.md`
  - `.specs/lessons.json`

  Faça sempre `git add` dos caminhos da tarefa, nunca `git add -A`.
- `typedRoutes: true` (`frontend-mobile/app.json:44`): uma rota nova só entra em `.expo/types/router.d.ts` quando o Metro roda. Depois da T7 e da T9, regenere os tipos antes do App gate. Isso vale também para quem já tem o Metro aberto em 8081. Se ele não estiver aberto, rode `npx expo start --port 8090` em background por cerca de 20 s e encerre esse processo.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem limite de cobertura. Fontes consultadas:
> - `.github/workflows/hairmatch-backend-test.yml`: roda `coverage run manage.py test`, sem limite mínimo;
> - `backend/agenda/tests.py` e `backend/reserve/tests.py`: Django `TestCase` + `APIClient` + `assert_problem`;
> - `frontend-mobile/package.json`: preset `jest-expo`, sem nenhum teste.
>
> App: só teste manual. É o critério confirmado no spec, igual ao das features anteriores. Backend: strong defaults.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend: modelo e migração (`agenda/models.py`, `migrations/0002_*`) | none | Gate de build: `makemigrations --check` limpo e suíte verde | - | Backend Full |
| Backend: view e serializer (`CreateAgenda`, `ListAgenda`, `AgendaSerializer`) | integration | Rotas no escopo: happy path, todo edge case e todo erro de EXT-01 a EXT-14, EXT-18 e EXT-19, 1:1 com os critérios | `backend/agenda/tests.py` (`CreateAgendaTest`, `ListAgendaTest`) | Backend Quick |
| Backend: integração com horários livres e reserva (código existente) | integration | EXT-15 a EXT-17 de ponta a ponta: POST do bloqueio, depois GET `available-slots`, `get_available_slots` e POST da reserva | `backend/reserve/tests.py` (classe nova `ExternalBlockTest`) | Backend Quick |
| App: tipos, serviço, hooks, telas e rotas | none | Decisão confirmada no spec. O gate é `tsc` com exit 0 e lint sem erro nos arquivos tocados. O comportamento é verificado no UAT (T13). | - | App |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas de backend com testes em `agenda` ou `reserve` | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test agenda reserve --noinput'` |
| Full | Modelo e migração, e fim da fase de backend | `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py test --noinput && python manage.py makemigrations --check --dry-run'` |
| App | Tarefas do app (`Tests: none`) | `cd frontend-mobile && npx tsc --noEmit && npx expo lint <arquivos tocados na tarefa>`. Precisa de exit 0 no `tsc` e **0 errors** no lint, com warnings tolerados. |
| Build | Fechamento (T12) | Full + `cd frontend-mobile && npx tsc --noEmit` |

**Baselines**, medidos em `fbf1d08` em 2026-10-09:
- Backend: **722** testes OK no projeto, sendo **68** em `agenda` + `reserve` (`def test_`: 23 em `agenda/tests.py` e 45 em `reserve/tests.py`). Nenhuma tarefa pode reduzir esses números.
- O único teste reescrito de propósito é `test_create_agenda_reports_every_missing_field`, para EXT-14. Ele continua existindo.
- `makemigrations --check`: "No changes detected".
- App: `npx tsc --noEmit` com exit 0. O lint do projeto já tem 6 errors e 67 warnings. O gate olha só os arquivos tocados. `agenda.tsx` já tem 1 error (`react-hooks/static-components`), que a T11 corrige.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend

```
T1 → T2 → T3 → T4
```

### Phase 2: App

```
T5 → T6
T7 → T9
T6 → T8
T8 → T9
T9 → T10
T10 → T11
```

### Phase 3: Fechamento

```
T12 → T13
```

---

## Task Breakdown

### Phase 1: Backend (tarefas)

#### T1: Tornar `Agenda.service` opcional e criar `Agenda.title`

**What**: Mudar `service` para `null=True, blank=True` e acrescentar `title = CharField(max_length=100, blank=True, default='')`. Gerar a migração `0002` com `makemigrations agenda`.
**Where**: `backend/agenda/models.py`. A migração gerada `backend/agenda/migrations/0002_*.py` entra no mesmo commit.
**Depends on**: None
**Reuses**: o modelo atual
**Requirement**: EXT-01, EXT-18

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] A migração tem só `AddField(title)` e `AlterField(service, null=True, blank=True)`
- [x] Gate check passes: Full. São 722 testes OK, e `makemigrations --check` dá "No changes detected" depois da migração.
- [x] Test count: 722, sem remoções

**Tests**: none
**Gate**: full

**Commit**: `feat(agenda): allow agenda blocks without a service and with a title`

---

#### T2: Contrato do `POST /api/agenda` para o bloqueio externo

**What**: Reescrever a validação de `CreateAgenda.post` conforme o design. Os erros saem na ordem `start_time`, `end_time`, `title`:
- o serviço passa a ser opcional;
- `title` é obrigatório sem serviço, é string e tem no máximo 100 caracteres depois de `strip()`;
- `end_time` é obrigatório sem serviço;
- `end_time > start_time`;
- `start_time` não pode ser anterior a `timezone.now()`;
- `title` é gravado sem espaços nas pontas.

Os testes ficam na mesma tarefa.
**Where**: `backend/agenda/views.py`. Os testes vão em `backend/agenda/tests.py`, `CreateAgendaTest`.
**Depends on**: T1
**Reuses**: `_parse_local_datetime`, `DATETIME_FORMAT_DETAIL`, `body_error`, `validation_problem` e `assert_problem`; `_post` e `login` de `AgendaTestCase`
**Requirement**: EXT-01, EXT-02, EXT-03, EXT-04, EXT-05, EXT-06, EXT-07, EXT-08, EXT-09, EXT-10, EXT-11, EXT-12, EXT-13, EXT-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes novos em `CreateAgendaTest`, com as datas relativas a `timezone.now()`:
  - [x] Sem serviço, com `title` `"  Cliente do WhatsApp  "`, início amanhã às 10:00 e término às 11:00 (ingênuos): 201 e o corpo exato `{"message": "Agenda register created successfully"}`. A linha criada tem `service_id is None`, `title == "Cliente do WhatsApp"`, `start_time`/`end_time` iguais a 14:00 e 15:00 UTC e `hairdresser` igual ao da sessão (EXT-01).
  - [x] Com serviço e sem `end_time`: `end_time == start + duration`. Sem `title`, grava `""`. Com `" Maria "`, grava `"Maria"` (EXT-02).
  - [x] Com serviço e um `end_time` diferente de início + duração: grava o `end_time` enviado (EXT-03).
  - [x] Sem serviço, com `title` ausente, `""` e `"   "` (subTest): 400 com exatamente `[{'pointer': '#/title', 'detail': 'This field is required.'}]`, e o número de linhas não muda (EXT-04).
  - [x] Com serviço e `title` ausente: 201. Isso prova que o título só é obrigatório sem serviço (EXT-04, um caso de cada condição, L-002).
  - [x] `title` igual a `123` e a `["x"]`: 400 `#/title` "This field must be a string." (EXT-05).
  - [x] `title` com 101 caracteres: 400 `#/title` "Ensure this field has no more than 100 characters.". Com 100 caracteres, e também com 100 mais espaços nas pontas: 201 (EXT-06).
  - [x] Sem serviço e sem `end_time`, com título: 400 com exatamente `[#/end_time "This field is required."]`. Com serviço e sem `end_time`: 201 (EXT-07).
  - [x] `end_time == start_time` e `end_time` 1 min antes: 400 `#/end_time` "The end time must be after the start time.", sem linha nova (EXT-08).
  - [x] `start_time` 1 min no passado: 400 `#/start_time` "The start time must not be in the past.", sem linha nova. `start_time` 1 min no futuro: 201 (EXT-09).
  - [x] Um bloqueio sem serviço que cruza um bloco existente: 409 `agenda-overlap`. Um bloqueio que começa exatamente no `end_time` do bloco existente: 201 (EXT-10).
  - [x] Um bloqueio sem serviço num dia sem `Availability` e outro dentro do almoço de uma `Availability` criada no teste: 201 (EXT-13).
  - [x] `test_create_agenda_reports_every_missing_field` reescrito: `{}` dá exatamente `[#/start_time required, #/end_time required, #/title required]`, nessa ordem (EXT-14).
- [x] Os testes atuais de 403/404/401/`hairdresser-required` continuam passando sem alteração (EXT-11, EXT-12)
- [x] Gate check passes: Quick
- [x] Test count: ≥ 68 + os testes novos em `agenda`+`reserve`, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `feat(agenda): accept external blocks without a service and validate their times`

---

#### T3: Listar bloqueios sem serviço com `title`

**What**: Fazer `ListAgenda` ignorar `service_id` nulo no `reserve_map`. Em `AgendaSerializer`, `service` passa a aceitar nulo, `title` entra em `fields` e `get_customer` devolve `None` para `service_id` nulo. Os testes ficam na mesma tarefa.
**Where**: `backend/agenda/serializers.py`. A linha do filtro fica em `ListAgenda.get` (`backend/agenda/views.py`). Os testes vão em `backend/agenda/tests.py`, `ListAgendaTest`.
**Depends on**: T2
**Reuses**: `SimpleServiceSerializer` e `reserve_map`
**Requirement**: EXT-18, EXT-19

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `GET /api/agenda` com um bloqueio sem serviço e um bloco com serviço:
  - os dois itens têm exatamente as chaves `{id, start_time, end_time, title, service, customer}`;
  - o bloqueio sem serviço vem com `service is None`, `customer is None` e `title == "Cliente do WhatsApp"`;
  - o bloco com serviço vem com `service == {"id", "name"}` e `title == ""` (EXT-18).
- [x] `GET /api/hairdressers/{id}/agenda` devolve as mesmas chaves (EXT-18)
- [x] Uma `Reserve`, de qualquer serviço, com o mesmo `start_time` de um bloqueio sem serviço: o item do bloqueio vem com `customer is None` (EXT-19)
- [x] Um bloco com serviço pareado a uma `Reserve` continua com o `customer` preenchido (regressão)
- [x] Gate check passes: Quick
- [x] Test count: ≥ o total da T2 + os novos, sem remoções

**Tests**: integration
**Gate**: quick

**Commit**: `feat(agenda): list external blocks with their title and no customer`

---

#### T4: Aceite: o bloqueio sai da oferta e recusa a reserva

**What**: Criar a classe `ExternalBlockTest(ReserveTestCase)` com o fluxo de ponta a ponta: o cabeleireiro faz POST `/api/agenda` e o cliente consulta e tenta reservar. É só teste, sem código de produção.
**Where**: `backend/reserve/tests.py`
**Depends on**: T3
**Reuses**: `ReserveTestCase` (segunda das 09:00 às 17:00 com almoço das 12:00 às 13:00), `next_monday()`, `reserve_views()`, `login`/`logout` e `assert_problem`
**Requirement**: EXT-15, EXT-16, EXT-17

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Um bloqueio sem serviço das 10:00 às 11:00 em `next_monday()`, criado por `POST /api/agenda` como cabeleireiro (201). Depois, `GET available-slots` com um serviço de 60 min, como anônimo:
  - `09:30`, `10:00` e `10:30` **não** aparecem;
  - `09:00` e `11:00` aparecem (EXT-15).

  Se o serviço da fixture não tiver 60 min, o teste cria um serviço de 60 min.
- [x] O mesmo cenário com um bloqueio **com serviço** e término editado: os horários que cruzam o término editado também somem (EXT-15)
- [x] `reserve_views().get_available_slots(hairdresser.id, service.id, 'YYYY-MM-DD')` omite os mesmos horários (EXT-16)
- [x] Um cliente faz POST de reserva às 10:30 do mesmo dia: 409 `slot-unavailable`, e `Reserve.objects.count()` e `Agenda.objects.count()` não mudam (EXT-17)
- [x] Gate check passes: Full. São ≥ 722 + os novos no projeto, e `makemigrations --check` limpo.
- [x] Test count: sem remoções

**Tests**: integration
**Gate**: full

**Commit**: `test(reserve): prove an external block leaves the slot offer and refuses bookings`

---

### Phase 2: App (tarefas)

#### T5: Tipos do contrato da agenda

**What**: Acrescentar `AgendaEntryResponse` e `CreateAgendaRequest`, como no design, a `models/Agenda.types.ts`. `AgendaEvent` passa a ter `id: number` e `isExternal: boolean`, e `useAgenda` ganha a mesma propriedade no mapeamento atual (`isExternal: ev.customer === null`), para o `tsc` continuar verde.
**Where**: `frontend-mobile/models/Agenda.types.ts`. A linha do mapeamento fica em `useAgenda.ts` (merge backward, porque sem ela o `tsc` quebra).
**Depends on**: T4
**Reuses**: tipos existentes
**Requirement**: EXT-18, EXT-20, EXT-21

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `AgendaEntryResponse.service` e `.customer` aceitam `null`
- [x] Em `CreateAgendaRequest`, `title` e `service` são opcionais
- [x] Gate check passes: App, com os arquivos tocados

**Tests**: none
**Gate**: App

**Commit**: `feat(mobile): type the agenda API contract`

---

#### T6: Tipar `agenda.service.ts`

**What**: `listAgendaByHairdresser` passa a devolver `Promise<{ data: AgendaEntryResponse[] } | undefined>`, e `createAgendaApointment` passa a receber `CreateAgendaRequest`. Sai o `import axios` que não é usado.
**Where**: `frontend-mobile/services/agenda.service.ts`
**Depends on**: T5
**Reuses**: `axiosInstance`
**Requirement**: EXT-30

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Nenhum `any` nas assinaturas exportadas
- [x] Gate check passes: App

**Tests**: none
**Gate**: App

**Commit**: `refactor(mobile): type the agenda service functions`

---

#### T7: Sub-stack da agenda

**What**: Mover `app/(app)/hairdresser/agenda.tsx` para `agenda/index.tsx` com `git mv`, sem mudar o conteúdo além dos imports relativos, e criar `agenda/_layout.tsx` (um `Stack` sem header, com `index` e `create`) no padrão de `services/_layout.tsx`.
**Where**: `frontend-mobile/app/(app)/hairdresser/agenda/_layout.tsx`. O `index.tsx` vem do `git mv`.
**Depends on**: None
**Reuses**: `app/(app)/hairdresser/services/_layout.tsx`
**Requirement**: EXT-23

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `utils/routes.ts` (`HAIRDRESSER_HOME`) e `constants/tabsConfig.ts` continuam apontando para `/(app)/hairdresser/agenda`, sem edição
- [ ] Os tipos de rota foram regenerados (pré-requisito)
- [ ] Gate check passes: App

**Tests**: none
**Gate**: App

**Commit**: `refactor(mobile): turn the hairdresser agenda into a stack`

---

#### T8: Hook `useExternalAppointmentForm`

**What**: Criar o hook do design com:
- o estado e os params `date` e `time`;
- os serviços carregados;
- as funções puras exportadas `computeEndTime` e `validateExternalAppointment`;
- `handleSave`, com a trava `isSaving`, `Alert` e `router.back()`, e `problemMessage` com `ErrorModal`.

**Where**: `frontend-mobile/hooks/hairdresserHooks/useExternalAppointmentForm.ts` (novo)
**Depends on**: T6
**Reuses**: `listServicesByHairdresser`, `createAgendaApointment`, `problemMessage`, `formatTimeInput` e `useAuth`; o padrão de `useServiceForms`
**Requirement**: EXT-23, EXT-25, EXT-26, EXT-27, EXT-28, EXT-29, EXT-30, EXT-31, EXT-32, EXT-33

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] As mensagens são exatamente as do spec (EXT-26 a EXT-29, EXT-31, EXT-32)
- [ ] O corpo enviado omite `service` com "Sem serviço" e envia `title.trim()` (EXT-30)
- [ ] Gate check passes: App

**Tests**: none
**Gate**: App

**Commit**: `feat(mobile): add the external appointment form hook`

---

#### T9: Tela "Atendimento externo"

**What**: Criar a tela `agenda/create.tsx` com `Calendar` (`minDate` igual a hoje), "Início" e "Término" HH:mm, chips "Sem serviço" e um por serviço, "Título" (`maxLength` 100), "Cancelar" e "Salvar" desabilitado durante o envio, e `ErrorModal`. Os estilos ficam num arquivo próprio.
**Where**: `frontend-mobile/app/(app)/hairdresser/agenda/create.tsx` (novo, com o arquivo de estilos `styles/hairdresser/agenda/ExternalAppointmentStyles.ts`)
**Depends on**: T7, T8
**Reuses**: `Calendar` + `ptBR` (padrão de `service-booking.tsx`), `FormInput` e `ErrorModal`; o layout de botões de `HaidresserServiceCreation.ts`
**Requirement**: EXT-23, EXT-24, EXT-30

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os tipos de rota foram regenerados, e `/(app)/hairdresser/agenda/create` existe em `.expo/types/router.d.ts`
- [ ] Gate check passes: App

**Tests**: none
**Gate**: App

**Commit**: `feat(mobile): add the external appointment screen`

---

#### T10: `useAgenda` recarrega no foco e abre a tela

**What**: Em `useAgenda`:
- trocar o `useEffect` por `useFocusEffect(useCallback(...))`;
- o título passa a ser `title || service?.name`;
- criar `handleAddPress`;
- `handlePressCell` abre a tela com `date` e `time` nos modos Semana e Dia, e mantém o comportamento atual no modo Mês.

**Where**: `frontend-mobile/hooks/hairdresserHooks/useAgenda.ts`
**Depends on**: T9
**Reuses**: o padrão de `useServiceManager.ts:20` e `dayjs`
**Requirement**: EXT-20, EXT-22, EXT-23, EXT-33, EXT-34

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Nenhum acesso a `ev.service.name` sem `?.` (EXT-20)
- [ ] Gate check passes: App

**Tests**: none
**Gate**: App

**Commit**: `feat(mobile): refresh the agenda on focus and open the external appointment form`

---

#### T11: FAB "+" e rótulo "Externo" na agenda

**What**: Em `agenda/index.tsx`:
- acrescentar o FAB "+" ligado a `handleAddPress`;
- mostrar o rótulo "Externo" nos itens da lista com `isExternal`;
- mover o `Header` para fora do componente, o que corrige o lint error que já existia.

Os estilos `fab` e `externalBadge` entram em `AgendaManagerStyles.ts`.
**Where**: `frontend-mobile/app/(app)/hairdresser/agenda/index.tsx`. Os estilos vão em `styles/hairdresser/agenda/AgendaManagerStyles.ts`.
**Depends on**: T10
**Reuses**: `Ionicons` e os estilos atuais da agenda
**Requirement**: EXT-21, EXT-23, EXT-33

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O lint de `agenda/index.tsx` tem 0 errors
- [ ] Gate check passes: App

**Tests**: none
**Gate**: App

**Commit**: `feat(mobile): add the external appointment button and label to the agenda`

---

### Phase 3: Fechamento (tarefas)

#### T12: Registrar o AD-009 e a rastreabilidade

**What**: Acrescentar o AD-009 do design em `.specs/STATE.md`, atualizar o Handoff e marcar a rastreabilidade do spec.
**Where**: `.specs/STATE.md`
**Depends on**: T11
**Reuses**: formato dos AD-001 a AD-008
**Requirement**: EXT-18, EXT-19

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O AD-009 tem Decision, Reason, Trade-off, Scope, Date e Status
- [ ] Gate check passes: Build

**Tests**: none
**Gate**: build

**Commit**: `docs(specs): record the external agenda block decision`

---

#### T13: UAT manual (web e Android)

**What**: O usuário roda o roteiro de UAT do plano (passos 1 a 6) e marca EXT-20 a EXT-34 como Verified.
**Where**: `.specs/features/external-appointment/validation.md` (seção UAT)
**Depends on**: T12
**Reuses**: o roteiro do plano; [[expo-web-smoke-needs-visible-tab]] (Metro em 8081, aba visível)
**Requirement**: EXT-20, EXT-21, EXT-22, EXT-23, EXT-24, EXT-25, EXT-26, EXT-27, EXT-28, EXT-29, EXT-30, EXT-31, EXT-32, EXT-33, EXT-34

**Tools**:

- MCP: `claude-in-chrome` (opcional, para o smoke web)
- Skill: NONE

**Done when**:

- [ ] Os seis passos do roteiro passam no web
- [ ] O passo 2 e o passo 4 passam no Android

**Tests**: none
**Gate**: build

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3

Phase 1:  T1 → T2 → T3 → T4
Phase 2:  T5 → T6 → T8 ─┐
          T7 ───────────┴→ T9 → T10 → T11
Phase 3:  T12 → T13
```

A execução é estritamente sequencial, na ordem T5, T6, T7, T8, T9, T10, T11.

**Lotes**: são 13 tarefas.
- Lote 1 = Phase 1 (4 tarefas).
- Lote 2 = Phase 2 + Phase 3 (7 + 2 = 9 tarefas, das quais a T13 é do usuário).

Isso dá dois lotes, então os sub-agentes são oferecidos antes do Execute.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: modelo + migração | 1 modelo (a migração é gerada) | ✅ Granular |
| T2: contrato do `CreateAgenda` | 1 endpoint + os testes dele | ✅ Granular |
| T3: listagem | 1 serializer + 1 linha da view | ⚠️ OK (coeso) |
| T4: aceite em `reserve` | 1 classe de teste | ✅ Granular |
| T5: tipos | 1 arquivo de tipos + 1 linha que mantém o `tsc` | ⚠️ OK (coeso) |
| T6: serviço tipado | 1 arquivo | ✅ Granular |
| T7: sub-stack | 1 layout + 1 `git mv` | ✅ Granular |
| T8: hook do formulário | 1 hook | ✅ Granular |
| T9: tela | 1 tela + os estilos dela | ⚠️ OK (coeso) |
| T10: `useAgenda` | 1 hook | ✅ Granular |
| T11: FAB e rótulo | 1 tela + os estilos dela | ⚠️ OK (coeso) |
| T12: AD-009 | 1 doc | ✅ Granular |
| T13: UAT | manual | ✅ |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | início da Phase 1 | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 (fase anterior) | início da Phase 2 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | None | início da Phase 2 | ✅ Match |
| T8 | T6 | T6 → T8 | ✅ Match |
| T9 | T7, T8 | T7 → T9, T8 → T9 | ✅ Match |
| T10 | T9 | T9 → T10 | ✅ Match |
| T11 | T10 | T10 → T11 | ✅ Match |
| T12 | T11 (fase anterior) | início da Phase 3 | ✅ Match |
| T13 | T12 | T12 → T13 | ✅ Match |

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Backend: modelo e migração | none | none | ✅ OK |
| T2 | Backend: view (`CreateAgenda`) | integration | integration | ✅ OK |
| T3 | Backend: view + serializer | integration | integration | ✅ OK |
| T4 | Backend: integração (só testes) | integration | integration | ✅ OK |
| T5 | App: tipos | none | none | ✅ OK |
| T6 | App: serviço | none | none | ✅ OK |
| T7 | App: rotas | none | none | ✅ OK |
| T8 | App: hook | none | none | ✅ OK |
| T9 | App: tela | none | none | ✅ OK |
| T10 | App: hook | none | none | ✅ OK |
| T11 | App: tela | none | none | ✅ OK |
| T12 | Docs | none | none | ✅ OK |
| T13 | UAT manual | none | none | ✅ OK |
