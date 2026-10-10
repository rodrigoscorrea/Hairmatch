# Cabeleireiros favoritos Context

**Gathered:** 2026-10-10
**Spec:** `.specs/features/favorite-hairdressers/spec.md`
**Status:** Ready for design

---

## Feature Boundary

O cliente favorita e desfavorita um cabeleireiro pelo perfil público, vê os favoritos na tela "Favoritos" do perfil dele e desfavorita direto por essa lista. O backend guarda a relação cliente ↔ cabeleireiro e expõe três rotas: listar, favoritar e desfavoritar. O cabeleireiro não tem nada novo nesta feature.

---

## Implementation Decisions

### Onde favoritar

- Só no perfil público do cabeleireiro (`customer/hairdresser-reservation/[id].tsx`), com um coração no header, à direita do botão voltar.
- Os cards da busca e da home não ganham coração.

### Tela "Favoritos"

- É uma lista de cards no formato dos resultados da busca (`customer/search.tsx:59-79`): foto, nome, nota e "bairro, cidade".
- O toque no card abre o perfil público.
- Cada card tem um coração que desfavorita direto, sem modal de confirmação. O card sai da lista na hora.
- A ordem vai do favoritado mais recente para o mais antigo.

### Item "Favoritos" do cabeleireiro

- O item de `hairdresser/profile/settings.tsx:80` fica como está, sem ação. Ele não entra nesta feature.

### Agent's Discretion

- O desenho das rotas (`/api/customers/me/favorite-hairdressers`, com `PUT` e `DELETE` por `{id}`) e o modelo de dados.
- Como o perfil descobre o estado inicial do coração: pela lista do `GET`, sem rota nova.
- O comportamento otimista com reversão na falha, no perfil e na lista.
- Os textos de lista vazia e de erro.

### Declined / Undiscussed Gray Areas → Assumptions

Os pontos abaixo não foram discutidos e estão registrados em Assumptions & Open Questions do spec:
- a idempotência do `PUT` e do `DELETE`;
- o cabeleireiro pendente (AD-008);
- a ausência de limite e de throttle;
- o coração desabilitado durante a requisição;
- a falha ao carregar o estado do coração.

---

## Specific References

- O card da lista copia o card de cabeleireiro da busca (`frontend-mobile/app/(app)/customer/search.tsx:59-79` e `styles/customer/styles/SearchStyle.ts`).
- A estrutura da tela copia "Avaliações recebidas" (`frontend-mobile/app/(app)/customer/ratings.tsx`): botão "‹ Voltar", título, `FlatList` com `ListEmptyComponent` e `ErrorModal`.

---

## Deferred Ideas

- Coração nos cards da busca e da home.
- Favoritos para o cabeleireiro, que é o item que ficou sem ação nas configurações dele.
