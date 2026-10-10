# Nota do cliente Context

**Gathered:** 2026-10-09
**Spec:** `.specs/features/customer-rating/spec.md`
**Status:** Ready for design

---

## Feature Boundary

O cabeleireiro dá ao cliente uma nota inteira de 1 a 5, com comentário opcional de até 500 caracteres, vinculada a uma reserva. Pode fazer isso uma vez por reserva e só depois do fim do atendimento, a partir do modal da agenda.

`User.rating` do cliente passa a ser a média das avaliações recebidas, ou `null` ("Sem avaliações"). O perfil do cliente mostra essa média, e o cliente pode ler as avaliações que recebeu.

Ficam de fora:
- editar e apagar a avaliação;
- recalcular a nota do cabeleireiro;
- status de reserva;
- notificações.

---

## Implementation Decisions

### Janela para avaliar

- A avaliação abre no **fim** do atendimento, `start_time + service.duration`, e não no início, como a review do cliente.
- O backend é a fonte da verdade (409 `service-not-finished`). O app esconde o botão antes disso usando o relógio do aparelho, mas isso é só conveniência.

### Visibilidade

- A **média e o total são públicos para cabeleireiros**: aparecem no modal da agenda e em `GET /api/customers/{id}/ratings`.
- A **lista com comentários é restrita**:
  - o cliente vê todas as dele;
  - cada cabeleireiro vê só as que escreveu;
  - outro cliente recebe 403.

### Cliente sem avaliação

- `User.rating = null`, e o app mostra "Sem avaliações".
- A migração põe `null` na nota 5 fictícia dos clientes atuais.
- A nota do cabeleireiro não muda: o valor e o default 5 continuam os mesmos.

### Editar e apagar

- Ficam fora desta feature. A avaliação é imutável.
- Para compensar, o app pede confirmação antes de enviar ("A avaliação não pode ser alterada depois de enviada.").

### Agent's Discretion

Decidido pelo agente e registrado nas Assumptions do spec:
- a nota é inteira;
- o comentário tem no máximo 500 caracteres;
- o duplicado reaproveita `review-exists`;
- o slug novo `service-not-finished` responde 409;
- a reserva e o autor apagados não apagam a avaliação (`SET_NULL`), e o cliente apagado leva as avaliações (`CASCADE`);
- `{id}` é o `Customer.id`;
- a lista vem das mais recentes para as mais antigas.

Na UI:
- a tela de avaliação é própria (`hairdresser/rate-customer/[reservationId]`) e não um segundo modal sobre o modal da agenda;
- o componente de estrelas sai da tela de review do cliente e passa a ser compartilhado;
- a lista de avaliações recebidas abre por um item no menu do perfil do cliente.

### Declined / Undiscussed Gray Areas → Assumptions

Todas estão no spec, com o default e o motivo, marcadas com `Confirmed? n`:
- o que acontece com a avaliação quando a reserva é cancelada;
- a conta do autor apagada;
- o prazo máximo, que não existe.

---

## Specific References

- Os padrões visuais e de interação ficam iguais aos da review feita pelo cliente:
  - `app/(app)/customer/review/[id].tsx`, com estrelas FontAwesome `star`/`star-o` em `#FFC107` e `#CCCCCC`, os rótulos "Ruim"/"Ótimo" e o comentário multilinha;
  - `hooks/customerHooks/useReviewForm.ts`.
- O tratamento de erro segue `hooks/hairdresserHooks/useServiceManager.ts:57-61` (`problemMessage` com o `ErrorModal`), e não o `Alert` genérico do `useReviewForm`.
- A confirmação usa o componente já existente em `components/modals/confirmationModal`.

---

## Deferred Ideas

- Recalcular a nota do cabeleireiro a partir das reviews dos clientes (lacuna de RF22), com o mesmo padrão do AD-010.
- Editar e apagar a avaliação pelo cabeleireiro (RF29/RF30).
- Validar no backend o horário da review do cliente (`CreateReview` não confere o horário).
- Notificar o cliente quando receber uma avaliação.
- Mostrar a nota do cliente em outras telas do cabeleireiro, quando elas existirem, como uma lista de reservas.
