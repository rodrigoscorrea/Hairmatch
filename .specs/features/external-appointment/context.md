# Atendimento externo na agenda Context

**Gathered:** 2026-10-09
**Spec:** `.specs/features/external-appointment/spec.md`
**Status:** Ready for design

---

## Feature Boundary

O cabeleireiro registra na própria agenda um atendimento feito fora do app. O registro é um bloqueio `[início, término)` que deixa de ser oferecido aos clientes. O bloqueio pode usar um dos serviços do cabeleireiro ou só um título livre. A tela nova abre pela agenda.

Nada além disso:
- não remove, cancela nem edita bloqueios;
- não muda o algoritmo de horários livres;
- não trata concorrência entre reserva e bloqueio;
- não muda fuso.

---

## Implementation Decisions

### Serviço do bloqueio

- Bloqueio livre: o serviço é **opcional**. Sem serviço, o bloqueio tem um título livre.
- Com serviço, ele continua tendo que pertencer ao cabeleireiro da sessão.

### Término

- Editável. Com serviço, vem preenchido com início + duração do serviço, e o cabeleireiro pode mudar.
- O usuário sabe que o intervalo inteiro `[início, término)` deixa de ser oferecido aos clientes que consultarem aquele cabeleireiro.

### Validações do `POST /api/agenda`

- O término tem que ser depois do início.
- O início não pode estar no passado.
- Fora da disponibilidade (`Availability`) ou no intervalo de almoço, o bloqueio **é aceito**, porque é um atendimento extra.

### Entrada na tela

- Um botão flutuante "+" na agenda, em qualquer modo.
- Tocar numa célula vazia nos modos Semana e Dia abre a tela com a data e a hora da célula.

### Agent's Discretion

- O nome do campo livre no contrato (`title`) e o limite dele (100 caracteres).
- O layout da tela (calendário para a data, `TextInput` HH:mm para os horários, chips de serviço com "Sem serviço"), reaproveitando os componentes que já existem e sem dependência nativa nova.
- A rota (`agenda/` vira um sub-stack, no padrão de `services/`).
- Os textos pt-BR das mensagens de validação no app.

### Declined / Undiscussed Gray Areas → Assumptions

Registradas no spec, em Assumptions & Open Questions:
- "Bloqueio livre" lido como serviço opcional;
- bloqueio no mesmo dia;
- concorrência fora de escopo;
- horários fora da grade de 30 min mantidos;
- dispositivo no fuso de Manaus;
- app sem teste automatizado.

---

## Specific References

- A issue #113 pede para "usar o serviço já existente no front e o endpoint do backend": `createAgendaApointment` (`frontend-mobile/services/agenda.service.ts`) e `POST /api/agenda` (`backend/agenda/views.py` `CreateAgenda`).
- O seletor de data segue a tela de agendamento do cliente (`app/(app)/customer/service-booking.tsx`, `react-native-calendars`).
- O formulário segue as telas de criar serviço e disponibilidade (`useServiceForms`, `AvailabilityForms`).

---

## Deferred Ideas

- Cancelar ou remover um bloqueio pela agenda (`confirmCancelEvent` é stub, e o backend já tem `DELETE /api/agenda/{id}`).
- Lock contra a corrida entre reserva do cliente e bloqueio (afeta também `CreateReserve`).
- Manter a grade de 30 min depois de um bloqueio com término quebrado.
