# Atendimento Externo na Agenda Specification

**Issue:** [#113](https://github.com/rodrigoscorrea/Hairmatch/issues/113) (RF21 em `docs/requisitos-status.md`, 🟡 Parcial)
**Escopo:** Large (mudança de modelo com migração, contrato da API e uma tela nova no app)
**Plataformas:** Web e Android, perfil cabeleireiro.
**Context:** `.specs/features/external-appointment/context.md`

## Problem Statement

O cabeleireiro também atende fora do app: por telefone, WhatsApp ou quem chega no salão. Hoje ele não tem como bloquear esse horário. Um cliente do app pode reservar o mesmo horário, e o cabeleireiro fica com dois atendimentos ao mesmo tempo.

O backend já tem `POST /api/agenda`, e os horários livres oferecidos ao cliente já descontam as linhas de `Agenda`. Mas nenhuma tela usa esse endpoint, e ele exige um serviço cadastrado, o que não serve para um bloqueio qualquer.

## Goals

- [ ] O cabeleireiro registra um atendimento externo pela agenda em menos de 1 minuto, com ou sem serviço.
- [ ] Um horário bloqueado nunca é oferecido a um cliente (app e chatbot), e uma reserva por cima dele é recusada com 409.
- [ ] O bloqueio aparece na agenda do cabeleireiro logo depois de salvo, sem recarregar o app.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Remover, cancelar ou editar um bloqueio pela agenda | A issue só pede adicionar. `confirmCancelEvent` (`useAgenda.ts`) continua stub, e `DELETE /api/agenda/{id}` já existe para uma feature futura. |
| Lock contra a corrida entre `CreateAgenda` e `CreateReserve` | A corrida já existe hoje nos dois caminhos (nenhum usa `select_for_update`). Resolver exige mexer na reserva do cliente e do chatbot. Fica como follow-up. |
| Manter a grade de 30 min depois de um bloqueio | `generate_time_slots` pula para o fim do bloqueio (`reserve/views.py:316`). É o comportamento atual e vale também para reservas. |
| Validar o bloqueio contra a disponibilidade (`Availability`) | Decisão do usuário: o atendimento externo pode ser fora do expediente. |
| Bloqueio que atravessa a meia-noite ou ocupa vários dias | A tela usa uma data e dois horários HH:mm. Um bloqueio mais longo é registrado dia a dia. |
| Fuso por salão | É o assunto do spike de timezone (`docs/timezone/`). O app continua mandando o horário ingênuo, lido como Manaus. |
| Testes automatizados do app | O app não tem testing-library nem testes. O gate é `npx tsc --noEmit` mais o UAT, como nas features anteriores. |
| Tipo de entrada (`kind`) no modelo | Um bloqueio externo se reconhece por `customer === null` na listagem (AD-009). Um campo novo só valeria com outro tipo de bloqueio. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Serviço do bloqueio | **Opcional**. O cabeleireiro escolhe um serviço próprio **ou** informa um título. | Escolha do usuário ("bloqueio livre"), lida como opcional e não proibida. Um atendimento externo de um serviço cadastrado continua mostrando o nome dele. | y |
| Término | Editável. Com serviço, vem preenchido com início + duração. | Escolha do usuário. O intervalo inteiro deixa de ser oferecido. | y |
| Validações novas | Término depois do início, e início não pode estar no passado. Fora da disponibilidade é aceito. | Escolha do usuário. | y |
| Entrada na tela | Botão "+" e toque em célula nos modos Semana e Dia | Escolha do usuário. | y |
| Nome e limite do campo livre | `title`, de 1 a 100 caracteres depois de `strip()`, obrigatório sem serviço e opcional com serviço | É curto o bastante para o título do evento no calendário. O nome casa com `AgendaEvent.title` do app. | y |
| Mensagens de erro da API | Em inglês, no `detail` do item de `errors` (AD-006). Só usa slugs que já existem. | O app traduz pelo slug e mostra suas próprias mensagens pt-BR. Nenhum slug novo, então não muda o catálogo. | y |
| "Agora" para a regra do passado | `timezone.now()` no backend, comparado com o `start_time` já convertido de Manaus. Um início igual a agora é aceito. | É o mesmo relógio que `ReserveSlot` usa para esconder horários passados. | y |
| Fuso do app | O app monta `YYYY-MM-DDTHH:mm:00` sem offset, e o backend lê como Manaus. A data e a hora da célula tocada vêm do relógio do aparelho. | É o mesmo contrato de `useServiceBooking`. Um aparelho fora de UTC-4 já tem o mesmo desvio hoje (spike N1). | y |
| Bloqueio de um dia só | O término é um HH:mm na mesma data do início | É o caso comum. Cobre o atendimento externo sem um seletor de data e hora completo. | y |
| Concorrência | Fora de escopo, sem lock | A corrida é anterior a esta feature e afeta todos os caminhos de escrita na agenda. | y |
| Serviço apagado depois do bloqueio | Não muda nada aqui. `service/views.py:116` já impede apagar um serviço com linhas na agenda. | É regra existente. | y |
| Título com serviço | Opcional. Quando vem, aparece no lugar do nome do serviço. | Deixa o cabeleireiro anotar "Maria (WhatsApp)" sem perder o serviço. | y |
| Testes do app | Só manual. O gate é `npx tsc --noEmit` mais o roteiro de UAT. | O app não tem testes por decisão (features google-auth, cep-autocomplete e email-confirmation). | y |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

### Implicit-requirement dimensions sweep

| Dimension | Coverage |
| --------- | -------- |
| Input validation & bounds | EXT-04 a EXT-09, EXT-24 a EXT-27 |
| Failure / partial-failure states | EXT-29: erro da API no app. A criação é uma linha só, então não há gravação parcial. |
| Idempotency / retry / duplicate handling | EXT-30 (sem duplo envio). Um reenvio do mesmo bloqueio leva 409 `agenda-overlap` (EXT-10). |
| Auth boundaries & rate limits | EXT-11 e EXT-12. Rate limit: N/A, porque a rota exige sessão de cabeleireiro e só escreve na própria agenda. |
| Concurrency / ordering | N/A por decisão: fora de escopo (Assumptions). |
| Data lifecycle / expiry | N/A, porque um bloqueio é permanente como as outras linhas da agenda, e a remoção está fora de escopo. |
| Observability | N/A, porque os erros já passam por `problem_response` e pelo handler do AD-006, sem log novo necessário. |
| External-dependency failure | N/A, porque a feature não chama serviço externo. |
| State-transition integrity | N/A, porque um bloqueio não tem estados. |

---

## User Stories

### P1: Registrar um bloqueio pela API ⭐ MVP

**User Story**: Como cabeleireiro, quero registrar na minha agenda um atendimento feito fora do app, com ou sem um serviço cadastrado, para que esse horário fique ocupado.

**Why P1**: É o contrato que a tela usa. Hoje ele exige serviço e aceita um bloqueio invertido ou no passado.

**Acceptance Criteria**:

1. **EXT-01** WHEN uma sessão de cabeleireiro faz `POST /api/agenda` com `start_time` futuro, `end_time` posterior e `title` não vazio, sem `service`, THEN o backend SHALL responder 201 com `{"message": "Agenda register created successfully"}` e SHALL criar exatamente uma linha de `Agenda` com:
   - `service` nulo;
   - `title` igual ao enviado, sem espaços nas pontas;
   - `start_time` e `end_time` iguais aos enviados (ingênuos lidos como Manaus);
   - `hairdresser` igual ao da sessão.
2. **EXT-02** WHEN o corpo traz um `service` do próprio cabeleireiro e não traz `end_time` THEN o backend SHALL criar a linha com `end_time = start_time + service.duration` minutos e `title` igual ao enviado sem espaços nas pontas, ou `""` quando ausente.
3. **EXT-03** WHEN o corpo traz um `service` do próprio cabeleireiro e um `end_time` posterior ao início THEN o backend SHALL gravar o `end_time` enviado, mesmo que difira de início + duração.
4. **EXT-04** IF o corpo não traz `service` e `title` está ausente, vazio ou só com espaços THEN o backend SHALL responder 400 `validation-error` com o item `{"pointer": "#/title", "detail": "This field is required."}` e SHALL não criar linha.
5. **EXT-05** IF `title` está presente e não é string THEN o backend SHALL responder 400 `validation-error` com o item `{"pointer": "#/title", "detail": "This field must be a string."}`.
6. **EXT-06** IF `title`, sem espaços nas pontas, tem mais de 100 caracteres THEN o backend SHALL responder 400 `validation-error` com o item `{"pointer": "#/title", "detail": "Ensure this field has no more than 100 characters."}`. Um título de exatamente 100 caracteres SHALL ser aceito.
7. **EXT-07** IF o corpo não traz `service` e não traz `end_time` THEN o backend SHALL responder 400 `validation-error` com o item `{"pointer": "#/end_time", "detail": "This field is required."}`.
8. **EXT-08** IF o `end_time` enviado é igual ou anterior ao `start_time` THEN o backend SHALL responder 400 `validation-error` com o item `{"pointer": "#/end_time", "detail": "The end time must be after the start time."}` e SHALL não criar linha.
9. **EXT-09** IF o `start_time` é anterior a `timezone.now()` THEN o backend SHALL responder 400 `validation-error` com o item `{"pointer": "#/start_time", "detail": "The start time must not be in the past."}` e SHALL não criar linha.
10. **EXT-10** IF o intervalo `[start_time, end_time)` cruza outra linha de `Agenda` do mesmo cabeleireiro, com ou sem serviço, THEN o backend SHALL responder 409 `agenda-overlap` e SHALL não criar linha. Um bloqueio que começa exatamente no término de outro SHALL ser aceito.
11. **EXT-11** IF o corpo traz um `service` de outro cabeleireiro THEN o backend SHALL responder 403 `forbidden`. IF o `service` não existe THEN SHALL responder 404 `not-found`. Esse é o comportamento atual e é mantido.
12. **EXT-12** IF a requisição não tem sessão THEN o backend SHALL responder 401 `invalid-session`. IF a sessão é de cliente THEN SHALL responder 403 `hairdresser-required`. Esse é o comportamento atual e é mantido.
13. **EXT-13** WHEN um bloqueio cai num dia sem `Availability`, fora do horário dela ou no intervalo de almoço THEN o backend SHALL aceitá-lo como em EXT-01 (201).
14. **EXT-14** WHEN o corpo vem vazio (`{}`) THEN o backend SHALL responder 400 `validation-error` com os itens, nesta ordem:
    1. `#/start_time` "This field is required.";
    2. `#/end_time` "This field is required.";
    3. `#/title` "This field is required.".

    **Mudança intencional de contrato**: o item `#/service` deixa de existir, porque o serviço passou a ser opcional. O teste `test_create_agenda_reports_every_missing_field` é reescrito para esta lista.

**Independent Test**: Com o cookie de um cabeleireiro, `curl -X POST /api/agenda -d '{"start_time":"<amanhã>T10:00:00","end_time":"<amanhã>T11:00:00","title":"Cliente do WhatsApp"}'` devolve 201. `GET /api/agenda` mostra a linha com `service: null`.

---

### P1: O horário bloqueado deixa de ser oferecido ⭐ MVP

**User Story**: Como cabeleireiro, quero que um horário bloqueado não apareça para os clientes, para não receber uma reserva em cima de um atendimento externo.

**Why P1**: É o critério de aceite da issue.

**Acceptance Criteria**:

1. **EXT-15** WHEN existe um bloqueio, com ou sem serviço, criado por `POST /api/agenda` THEN `GET /api/hairdressers/{id}/available-slots` daquele dia SHALL omitir todo horário `s` cujo intervalo `[s, s + duração do serviço consultado)` cruze o bloqueio.

    Exemplo: segunda com disponibilidade das 09:00 às 17:00, almoço das 12:00 às 13:00, serviço consultado de 60 min e bloqueio sem serviço das 10:00 às 11:00. Então:
    - `09:30`, `10:00` e `10:30` não aparecem;
    - `09:00` e `11:00` aparecem.
2. **EXT-16** WHEN existe um bloqueio como em EXT-15 THEN `get_available_slots` (o caminho do chatbot, `reserve/views.py`) SHALL omitir os mesmos horários.
3. **EXT-17** IF um cliente faz `POST` de reserva com início dentro de um bloqueio sem serviço THEN o backend SHALL responder 409 `slot-unavailable` e SHALL não criar `Reserve` nem `Agenda`.

**Independent Test**: Com o bloqueio do teste anterior, `GET /api/hairdressers/{id}/available-slots?service=<id>&date=<amanhã>` não lista `10:00`.

---

### P1: Ver o bloqueio na agenda ⭐ MVP

**User Story**: Como cabeleireiro, quero ver os atendimentos externos na minha agenda, separados dos agendamentos de clientes do app.

**Why P1**: Sem isso, o bloqueio salvo some da vista do cabeleireiro. Com `service` nulo, a agenda atual quebra ao ler `ev.service.name`.

**Acceptance Criteria**:

1. **EXT-18** WHEN o cabeleireiro lista a agenda (`GET /api/agenda` ou `GET /api/hairdressers/{id}/agenda`) THEN cada item SHALL ter as chaves `id`, `start_time`, `end_time`, `title`, `service` e `customer`. Um bloqueio sem serviço SHALL vir com `"service": null`, `"customer": null` e o `title` gravado.
2. **EXT-19** WHEN um bloqueio sem serviço tem o mesmo `start_time` de uma `Reserve` existente (de qualquer serviço) THEN o item da listagem SHALL vir com `"customer": null`.
3. **EXT-20** WHEN a agenda do app recebe um item THEN o app SHALL usar como título do evento o `title` quando não vazio, senão `service.name`. A tela SHALL não quebrar quando `service` é `null`.
4. **EXT-21** WHILE a agenda está no modo "Agenda" (lista), o app SHALL mostrar o rótulo "Externo" nos itens com `customer` nulo.
5. **EXT-22** WHEN a tela da agenda volta a ter foco (por exemplo, depois de salvar um bloqueio) THEN o app SHALL buscar a agenda de novo e mostrar o bloqueio recém-criado.

**Independent Test**: Depois de criar um bloqueio "Cliente do WhatsApp" pela API, abrir a agenda mostra o item com esse título e o rótulo "Externo".

---

### P1: Tela para registrar o atendimento externo ⭐ MVP

**User Story**: Como cabeleireiro, quero uma tela simples para escolher a data, os horários e o serviço ou um título, para bloquear o horário sem sair da agenda.

**Why P1**: É a parte Front da issue.

**Acceptance Criteria**:

1. **EXT-23** WHEN o cabeleireiro toca o botão "+" da agenda, em qualquer modo, THEN o app SHALL abrir a tela "Atendimento externo" com:
   - a data de hoje selecionada;
   - os horários de início e término vazios;
   - "Sem serviço" selecionado;
   - o título vazio.
2. **EXT-24** The tela SHALL oferecer:
   - um calendário com os dias anteriores a hoje desabilitados;
   - os campos "Início" e "Término" no formato HH:mm;
   - a opção "Sem serviço" mais um chip para cada serviço do cabeleireiro (`GET /api/hairdressers/{id}/services`);
   - um campo "Título" com no máximo 100 caracteres.
3. **EXT-25** WHEN um serviço está selecionado e o início é um HH:mm válido, e um dos dois acaba de mudar, THEN o app SHALL preencher o término com início + duração do serviço. O cabeleireiro SHALL poder editar o término depois.
4. **EXT-26** IF o cabeleireiro toca "Salvar" com o início ou o término vazio THEN o app SHALL mostrar o `ErrorModal` com "Informe os horários de início e término." e SHALL não chamar a API.
5. **EXT-27** IF o cabeleireiro toca "Salvar" com o término igual ou anterior ao início THEN o app SHALL mostrar o `ErrorModal` com "O término deve ser depois do início." e SHALL não chamar a API.
6. **EXT-28** IF o cabeleireiro toca "Salvar" com data e início anteriores ao momento atual THEN o app SHALL mostrar o `ErrorModal` com "O início não pode estar no passado." e SHALL não chamar a API.
7. **EXT-29** IF o cabeleireiro toca "Salvar" com "Sem serviço" e título vazio ou só com espaços THEN o app SHALL mostrar o `ErrorModal` com "Informe um título ou escolha um serviço." e SHALL não chamar a API.
8. **EXT-30** WHEN o formulário é válido e o cabeleireiro toca "Salvar" THEN o app SHALL chamar `POST /api/agenda` uma vez, com:
   - `start_time` e `end_time` no formato `YYYY-MM-DDTHH:mm:00`;
   - `title` sem espaços nas pontas;
   - `service` só quando um serviço está selecionado.

   Enquanto a requisição está em andamento, o botão "Salvar" SHALL ficar desabilitado.
9. **EXT-31** WHEN a API responde 201 THEN o app SHALL mostrar o alerta "Sucesso!" / "Atendimento externo registrado." e SHALL voltar para a agenda.
10. **EXT-32** IF a API responde com erro ou a rede falha THEN o app SHALL mostrar o `ErrorModal` com `problemMessage(error, "Não foi possível registrar o atendimento externo.")`, por exemplo "Este horário se sobrepõe a outro compromisso." para `agenda-overlap`. O app SHALL manter a tela aberta com os dados preenchidos.

**Independent Test**: Na agenda, tocar "+", escolher amanhã, das 10:00 às 11:00, "Sem serviço" e o título "Cliente do WhatsApp", e salvar. A agenda mostra o bloqueio, e o agendamento de um cliente para amanhã não oferece 10:00.

---

### P2: Abrir a tela a partir de uma célula da agenda

**User Story**: Como cabeleireiro, quero tocar num horário vazio do calendário para bloquear exatamente aquele horário.

**Why P2**: Agiliza o fluxo, mas o botão "+" já cobre o caso.

**Acceptance Criteria**:

1. **EXT-33** WHEN o cabeleireiro toca uma célula nos modos "Semana" ou "Dia" THEN o app SHALL abrir a tela "Atendimento externo" com a data da célula selecionada e o início igual à hora e ao minuto da célula (HH:mm). O término SHALL ficar vazio, e "Sem serviço" selecionado.
2. **EXT-34** WHILE a agenda está no modo "Mês", tocar uma célula SHALL manter o comportamento atual: ir para o modo "Dia" naquela data, sem abrir a tela.

**Independent Test**: No modo "Dia", tocar a célula das 15:00 de amanhã abre a tela com amanhã e Início "15:00".

---

## Edge Cases

- IF o título chega com espaços nas pontas THEN o backend SHALL gravá-lo sem eles (EXT-01, EXT-02).
- IF o bloqueio termina exatamente quando outro começa THEN SHALL ser aceito (EXT-10).
- WHEN o término de um bloqueio sai da grade de 30 min (ex.: 10:45) THEN os horários seguintes oferecidos SHALL começar nesse término (10:45, 11:15, …). É o comportamento atual e não muda nesta feature.
- IF o cabeleireiro não tem nenhum serviço cadastrado THEN a tela SHALL mostrar só "Sem serviço" e SHALL continuar permitindo salvar com título (EXT-24, EXT-29).
- IF a lista de serviços falha ao carregar THEN a tela SHALL continuar permitindo salvar com "Sem serviço" e título.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| EXT-01 | P1: Bloqueio pela API, AC1 | Tasks | Implementing |
| EXT-02 | P1: Bloqueio pela API, AC2 | Tasks | Implementing |
| EXT-03 | P1: Bloqueio pela API, AC3 | Tasks | Implementing |
| EXT-04 | P1: Bloqueio pela API, AC4 | Tasks | Implementing |
| EXT-05 | P1: Bloqueio pela API, AC5 | Tasks | Implementing |
| EXT-06 | P1: Bloqueio pela API, AC6 | Tasks | Implementing |
| EXT-07 | P1: Bloqueio pela API, AC7 | Tasks | Implementing |
| EXT-08 | P1: Bloqueio pela API, AC8 | Tasks | Implementing |
| EXT-09 | P1: Bloqueio pela API, AC9 | Tasks | Implementing |
| EXT-10 | P1: Bloqueio pela API, AC10 | Tasks | Implementing |
| EXT-11 | P1: Bloqueio pela API, AC11 | Tasks | Implementing |
| EXT-12 | P1: Bloqueio pela API, AC12 | Tasks | Implementing |
| EXT-13 | P1: Bloqueio pela API, AC13 | Tasks | Implementing |
| EXT-14 | P1: Bloqueio pela API, AC14 | Tasks | Implementing |
| EXT-15 | P1: Horário deixa de ser oferecido, AC1 | Tasks | Implementing |
| EXT-16 | P1: Horário deixa de ser oferecido, AC2 | Tasks | Implementing |
| EXT-17 | P1: Horário deixa de ser oferecido, AC3 | Tasks | Implementing |
| EXT-18 | P1: Ver o bloqueio na agenda, AC1 | Tasks | Implementing |
| EXT-19 | P1: Ver o bloqueio na agenda, AC2 | Tasks | Implementing |
| EXT-20 | P1: Ver o bloqueio na agenda, AC3 | Tasks | Implementing |
| EXT-21 | P1: Ver o bloqueio na agenda, AC4 | Tasks | Implementing |
| EXT-22 | P1: Ver o bloqueio na agenda, AC5 | Tasks | Implementing |
| EXT-23 | P1: Tela de registro, AC1 | Tasks | Implementing |
| EXT-24 | P1: Tela de registro, AC2 | Tasks | Implementing |
| EXT-25 | P1: Tela de registro, AC3 | Tasks | Implementing |
| EXT-26 | P1: Tela de registro, AC4 | Tasks | Implementing |
| EXT-27 | P1: Tela de registro, AC5 | Tasks | Implementing |
| EXT-28 | P1: Tela de registro, AC6 | Tasks | Implementing |
| EXT-29 | P1: Tela de registro, AC7 | Tasks | Implementing |
| EXT-30 | P1: Tela de registro, AC8 | Tasks | Implementing |
| EXT-31 | P1: Tela de registro, AC9 | Tasks | Implementing |
| EXT-32 | P1: Tela de registro, AC10 | Tasks | Implementing |
| EXT-33 | P2: Abrir pela célula, AC1 | Tasks | Implementing |
| EXT-34 | P2: Abrir pela célula, AC2 | Tasks | Implementing |

**Coverage:** 34 total, 34 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] No UAT, um bloqueio sem serviço criado pela tela some dos horários oferecidos ao cliente naquele dia, e a reserva por cima dele é recusada.
- [ ] Nenhum teste existente do backend deixa de passar, exceto `test_create_agenda_reports_every_missing_field`, que é reescrito para EXT-14. O número de testes só aumenta.
- [ ] `npx tsc --noEmit` termina com exit 0.
