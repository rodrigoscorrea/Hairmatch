# Minhas avaliações (cabeleireiro) Validation

**Date**: 2026-10-11
**Spec**: `.specs/features/hairdresser-reviews/spec.md`
**Diff range**: `23d900a..HEAD` (branch `189-avaliacoes-recebidas-cabeleireiro`, 7 commits de código e de status, mais o commit de planejamento `d59a62a`)
**Verifier**: passada independente do mesmo agente, sem sub-agente (o usuário não pediu sub-agentes). Reli o `spec.md` e o diff, derivei a cobertura com evidence-or-zero e rodei o sensor por mutação na própria árvore, com cópia de segurança do `views.py` restaurada a cada rodada (sem `git stash`, sem worktree).

**Overall**: ✅ PASS no backend (HRV-01 a HRV-05). ⚠️ O app (HRV-06 a HRV-30) está **Implemented, não Verified**: o gate é `tsc` (0 erros), o bundle web (200) e o E2E de API. A conferência em tela no web e o toque no push no Android (T8, passos 1 a 6 em tela) ficam PENDENTES com o usuário.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 | ✅ Done | `ListReview` por `-created_at, -id`; 5 testes novos; `test_list_reviews` e a contagem de queries do `ListReviewPicturesTest` (`[2, 3, 1]` → `[1, 3, 2]`) seguem a ordem nova |
| T2 | ✅ Done | `ReceivedReview` e `getHairdresserReviews` |
| T3 | ✅ Done | `useHairdresserReviews` |
| T4 | ✅ Done | `PhotoViewer` extraído; `GalleryStrip` usa o componente |
| T5 | ✅ Done | Tela `reviews.tsx`, `Stack.Screen` e `unstable_settings` |
| T6 | ✅ Done | Card "Minhas avaliações" e `goToReviews` |
| T7 | ✅ Done | `alertRoute` e a emenda da spec e das tasks da #182 |
| T8 | ⚠️ Parcial | E2E de API 22/22 e checagens de render descartáveis passaram; UAT em tela (web) e push (Android) pendentes com o usuário |

---

## Spec-Anchored Acceptance Criteria (backend)

Arquivo de teste: `backend/review/tests.py`.

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| HRV-01 ordem por `created_at` desc | `created_at` reescrito fora da ordem de inserção sai do mais recente ao mais antigo | `tests.py:649` `assertEqual(self._listed_ids(), [newest.id, middle.id, oldest.id])`; `tests.py:617` `assertEqual(reviews[0]['rating'], 5)` (a segunda criada vem primeiro); `tests.py:1840` `[1, 3, 2]` | ✅ PASS |
| HRV-02 empate por `id` desc | mesmo `created_at` lista a de maior `id` primeiro | `tests.py:657` `assertEqual(self._listed_ids(), [third.id, second.id, first.id])` | ✅ PASS (ver sensor: o desempate não é discriminável) |
| HRV-03 formato do item | 7 chaves, `customer` aninhado, fotos por `id` crescente | `tests.py:696` `assertEqual(sorted(item), ['comment', 'created_at', 'customer', 'hairdresser', 'id', 'pictures', 'rating'])`; `tests.py:697-709` valores e `customer == {'id', 'user': {'id', 'first_name', 'last_name'}}`; fotos por `id`: `ListReviewPicturesTest` sem mudança nas asserções de formato | ✅ PASS |
| HRV-04 só as do cabeleireiro | cada `GET` traz só as dele | `tests.py:668` `[mine[1].id, mine[0].id]`; `tests.py:669` `[theirs.id]` | ✅ PASS |
| HRV-05 edição não muda a posição | a mais antiga continua por último, com o valor novo | `tests.py:675` ordem antes; `tests.py:685-687` ordem depois, `data[1]['rating'] == 1` (`:686`) e `comment` novo (`:687`) | ✅ PASS |

**Gate Full**: `makemigrations --check` limpo; 1123 testes passam (baseline 1118, +5); `review/views.py` 100% de cobertura; `def test_` 1120 → 1125. `test_routes.py` não mudou.

## App (Implemented, não Verified)

| Criterion | `file:line` | Evidência | Result |
| --------- | ----------- | --------- | ------ |
| HRV-06, HRV-30 chamada com o `id` da sessão, sem `id` não chama | `useHairdresserReviews.ts:21`, `:23` | render descartável: `getHairdresserReviews` chamado com 7; sem `userInfo`, nunca chamado | ⚠️ Implemented |
| HRV-07 título e "‹ Voltar" | `reviews.tsx` (header) | render descartável | ⚠️ Implemented |
| HRV-08 a HRV-10 nome, estrelas + valor, data | `reviews.tsx:42`, `:46`, `:47`, `:49` | render descartável: "Ana Lima", "5", "4,5", "4", "11/10/2026" | ⚠️ Implemented |
| HRV-11, HRV-12 comentário | `reviews.tsx:51` | render descartável: `null` e `"   "` não geram texto; comentário real aparece | ⚠️ Implemented |
| HRV-13, HRV-29 miniaturas | `reviews.tsx:53`, `:59` | render descartável: 6 miniaturas "Abrir foto" na ordem da API, uma faixa `horizontal` por review com fotos | ⚠️ Implemented |
| HRV-14 foto em tela cheia | `PhotoViewer.tsx:13`, `:20` | render descartável: o toque abre o `Modal` com a `uri` da miniatura, "Fechar foto" fecha | ⚠️ Implemented |
| HRV-15, HRV-16 vazio e falha | `reviews.tsx:36`, `useHairdresserReviews.ts:32` | render descartável: vazio só depois do carregamento; falha mostra "MSG:Não foi possível carregar suas avaliações." sem a mensagem de vazio | ⚠️ Implemented |
| HRV-17, HRV-21 voltar | `useHairdresserReviews.ts:41` | render descartável: `router.back()` chamado uma vez | ⚠️ Implemented |
| HRV-18 voltar sem histórico | `_layout.tsx:4` | só por `unstable_settings`; comportamento do expo-router 57 **não provado** (UAT, passo 6) | ⏭️ Pendente |
| HRV-19, HRV-20 card no perfil | `index.tsx:77`, `useHairdresserProfile.ts:37` | `tsc` 0 erros; bundle web 200; toque em tela pendente | ⚠️ Implemented |
| HRV-22 a HRV-24, HRV-26, HRV-27 destino do toque | `alert-routes.ts:25` | teste descartável de `alertRoute`: `review-created` e `review-updated` → `/(app)/hairdresser/profile/reviews`, `review-deleted` → `null`, `reservation-created` → `HAIRDRESSER_HOME`, `customer-rating-*` → `/(app)/customer/ratings`. Os `PATCH` e a navegação são da #182. Push no Android pendente | ⚠️ Implemented |
| HRV-25 lista desde o topo, recarregada | `useHairdresserReviews.ts` (`useFocusEffect`) | `router.push` cria a tela nova; E2E de API mostra o `GET` seguinte trazendo a review | ⚠️ Implemented |
| HRV-28 review excluída some no próximo foco | `useHairdresserReviews.ts:26` | E2E de API: depois do `DELETE`, o `GET` lista só a restante | ⚠️ Implemented |

**E2E de API** (servidor da branch num banco descartável, LocalStack/MiniStack reais, 22/22 passaram): lista vazia pública e com cookie; `POST` com 2 fotos (4, sem comentário) e `POST` (5, com comentário) → `GET` `[5, 4]`; 7 chaves e `customer` aninhado; comentário vazio e 2 fotos por `id` crescente; as 2 URLs de miniatura respondem 200; `PUT` 4→3 mantém `[5, 3]`; outro cabeleireiro lista `[]`; alertas `review-created` ×2 e `review-updated`, `PATCH` de leitura 200; `DELETE` → só a restante e alerta `review-deleted`. Servidor, banco e usuários do Cognito removidos depois.

---

## Discrimination Sensor (backend, `ListReview`)

Mutantes aplicados em `backend/review/views.py` com cópia de segurança restaurada a cada rodada (`git diff` limpo no fim).

| Mutante | Resultado |
| ------- | --------- |
| `order_by('id')` (ordem antiga) | ☠️ morto (6 testes: 4 de `ListReviewOrderTest`, `test_list_reviews`, a contagem de queries) |
| `order_by('-id')` | ☠️ morto (`test_reviews_are_listed_by_created_at_descending_whatever_the_insertion_order`) |
| `order_by('created_at', '-id')` | ☠️ morto (6 testes) |
| `order_by('-created_at', 'id')` | ☠️ morto (`test_reviews_with_the_same_created_at_are_listed_by_id_descending`) |
| `order_by('-created_at')` (sem desempate) | 🧟 **sobrevive** |

O sobrevivente é uma limitação, não um teste fraco: com `created_at` igual, o Postgres deste plano devolve as linhas por `id` decrescente por conta própria, mesmo com 12 linhas empatadas e com o `UPDATE` em uma única instrução. Tentei dois formatos mais fortes do teste e nenhum o matou, então voltei ao de 3 linhas. O `-id` no `order_by` garante o determinismo que o plano não garante; o HRV-02 é provado pelo mutante `'id'` crescente, que morre.

Sensor do app: não há suíte no app (decisão herdada do #106, #115, #118 e #120). As checagens de render e de `alertRoute` foram descartáveis (`__tmp_hrv__/`, removidas), então não há mutante de app.

## Gaps

1. **HRV-18** (voltar sem histórico) e **HRV-24** (push no Android) dependem do UAT do usuário. O design registra o fallback se o `initialRouteName` não montar o perfil por baixo: `handleGoBack` passa a `router.replace('/(app)/hairdresser/profile')` quando `router.canGoBack()` é falso.
2. O sobrevivente do desempate acima.

## Verdict

✅ PASS no backend. O app fica Implemented até o usuário rodar o roteiro do T8 em tela.
