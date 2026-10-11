# Minhas avaliações (cabeleireiro) Context

**Gathered:** 2026-10-11
**Spec:** `.specs/features/hairdresser-reviews/spec.md`
**Status:** Ready for design

---

## Feature Boundary

O cabeleireiro abre "Minhas avaliações" pelo perfil e vê as reviews que recebeu, da mais recente para a mais antiga, com cliente, nota, data, comentário e fotos. O toque no alerta e no push de `review-created` e `review-updated` (#182) passa a abrir essa tela. O backend só muda a ordem da `GET /api/hairdressers/{id}/reviews` (RT-24). Não há modelo, rota nem slug novo.

---

## Implementation Decisions

### Toque no alerta e no push

- O toque abre "Minhas avaliações" no topo, com a lista recarregada. A tela não rola até a review do alerta nem a destaca.
- O payload do push da #182 (`{alert_id, kind}`) não muda.
- Só `review-created` e `review-updated` navegam. `review-deleted` continua só marcando o alerta como lido.

### Agent's Discretion

- A ordem decrescente fica no backend (`order_by('-created_at', '-id')`), e não no app.
- O app reusa a RT-24 com o `id` do `Hairdresser` da sessão, sem rota `me` nova.
- O formato da nota: as estrelas do `StarRating` e o valor ao lado ("4", "4,5").
- O visualizador de fotos em tela cheia é extraído do `GalleryStrip` para um componente comum.
- "‹ Voltar" usa `router.back()` quando há histórico e abre o perfil quando não há.
- Os textos de lista vazia e de erro.

### Declined / Undiscussed Gray Areas → Assumptions

Os pontos abaixo não foram discutidos com o usuário. Eles estão em Assumptions & Open Questions do spec:
- o conteúdo do card, que se limita à lista da issue;
- a data mostrada (`created_at`, mesmo para review editada);
- o comentário vazio, que fica escondido;
- a sequência com a #182: as histórias P1 podem sair antes, e a P2 espera a mesclagem.

---

## Specific References

- A estrutura da tela copia "Avaliações recebidas" do cliente (`frontend-mobile/app/(app)/customer/ratings.tsx`): "‹ Voltar", título, `FlatList` com `ListEmptyComponent` só depois do carregamento, card com `StarRating` e data `DD/MM/YYYY`, e `ErrorModal`.
- O hook copia `useReceivedRatings` (`frontend-mobile/hooks/customerHooks/useReceivedRatings.ts`): `useFocusEffect`, flag `active`, `isLoaded` e `errorModal`.
- O card "Minhas avaliações" do perfil copia o card "Minha galeria" (`frontend-mobile/app/(app)/hairdresser/profile/index.tsx:72-75`).
- As miniaturas e a foto em tela cheia seguem a galeria (`frontend-mobile/components/gallery/GalleryStrip.tsx`).

---

## Deferred Ideas

- Rolar até a review do alerta e destacá-la. Exigiria `review_id` no payload do push ou uma leitura do alerta antes de navegar.
- Nome do serviço e foto do cliente no card.
- Marca "editada", com `Review.updated_at` e migração.
- Média e total de reviews no cabeçalho, junto com a nota derivada do cabeleireiro (AD-010).
- Responder a uma review.
