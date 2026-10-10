# customer-rating Validation

## Validation: customer-rating - PASS ✅

The backend is PASS: every backend AC has test evidence, the gate is green, and the sensor killed 21 of 21 mutants. The app ACs (CRT-39 to CRT-52, CRT-56 to CRT-60) were checked by reading the code and are **pending the user's UAT (T18)**. That is intentional: the app has no automated test suite, and its gates are `tsc` and eslint. Nothing blocks the PASS. Three items are flagged as non-blocking (see Summary).

**Date**: 2026-10-09
**Spec**: `.specs/features/customer-rating/spec.md` (+ `design.md`, `tasks.md`, `context.md`, AD-010 in `.specs/STATE.md`)
**Diff range**: `develop..HEAD` = `fbf1d08..0436aec` on `104-dar-nota-para-o-cliente` (19 commits; `be9b939` only adds the spec and AD-010)
**Verifier**: independent sub-agent (author ≠ verifier). Read-only on the real tree; mutations ran only in a detached scratch worktree.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1-T7 (backend) | ✅ Done | Every Done-when is ticked and backed by tests (see below). |
| T8-T16 (app) | ✅ Done (code) | `tsc` exit 0. Visual and behavioral checks are deferred to T18. |
| T17 (docs) | ⚠️ Partial | RF23 is not ticked ✅ in `docs/requisitos-status.md`. That file is not versioned and does not exist in the worktree, so the user owns this step. The spec's success criterion #3 stays open. |
| T18 (UAT web + Android) | ⏳ Open by design | Owned by the user. |

---

## Spec-Anchored Acceptance Criteria

Test paths are relative to `backend/`. Production `file:line` is cited where it helps.

### P1: Hairdresser rates via API

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CRT-01 happy path | 201 `{data:{id,reservation,rating,comment,created_at}}`; row has the reservation's customer + hairdresser | `review/tests.py:1051` `assertEqual(set(data), {'id','reservation','rating','comment','created_at'})`; `:1053-1058` values + `(created.customer_id, created.hairdresser_id) == (customer.id, hairdresser.id)` | ✅ PASS |
| CRT-02 end = start + duration, accepted at the exact instant | `now >= end` accepted | `review/tests.py:1062-1071` (now patched to start+30min) `status_code == 201`; `:969` `service_end(...) == 13:30` | ✅ PASS (M1 and M2 killed) |
| CRT-03 not finished → 409, no row | 409 `service-not-finished`, no row | `review/tests.py:1090-1093` `assert_problem(..., 'service-not-finished', detail=...)` + `assertFalse(CustomerRating.objects.exists())` for 3 cases | ✅ PASS |
| CRT-04 start_time null → 409 | 409 `service-not-finished` | `review/tests.py:1100` `assert_problem(..., 'service-not-finished')`; `:975` `assertIsNone(service_end(...))` | ✅ PASS |
| CRT-05 duplicate → 409, nothing changed | 409 `review-exists`; existing rating + `User.rating` unchanged | `review/tests.py:1109-1113` `assert_problem(..., 'review-exists', ...)`, `(rating, comment) == (5,'Primeira')`, `customer_user.rating == 5.0` | ✅ PASS |
| CRT-06 race on the same reservation → one row, 409 not 500 | DB unique wins; 409 `review-exists` | `review/tests.py:1119-1125` (`_is_rated` patched False) `assert_problem(..., 'review-exists')`; `:849` `assertRaises(IntegrityError)`; `:941-950` the outer transaction stays usable | ✅ PASS (M3 killed) |
| CRT-07 another hairdresser's reservation | 403 `forbidden` | `review/tests.py:1137-1138` `assert_problem(..., 'forbidden')` + no row | ✅ PASS (M4 killed) |
| CRT-08 unknown reservation | 404 `not-found` | `review/tests.py:1142` `assert_problem(..., 'not-found', detail='Reservation not found.')` | ✅ PASS |
| CRT-09 no session | 401 `invalid-session` | `review/tests.py:1148` | ✅ PASS |
| CRT-10 customer session | 403 `hairdresser-required` | `review/tests.py:1156` | ✅ PASS |

### P1: Input validated

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CRT-11 rating absent / 4.5 / "5" / true / out of range | 400 `validation-error`, `#/rating` | `review/tests.py:1161-1172` exact `errors=[{'pointer':'#/rating', ...}]` for 4.5, '5', True, 0, 6, absent | ✅ PASS (M17 killed) |
| CRT-12 reservation absent / not an int | 400, `#/reservation` | `review/tests.py:1179-1184` | ✅ PASS |
| CRT-13 comment not a string, or >500 after trim | 400, `#/comment`; 500 accepted | `review/tests.py:1189-1197` (7 and 501 chars); `:1202-1205` 500 chars inside spaces → 201 | ✅ PASS (M15 killed) |
| CRT-14 absent / null / blank → null; trimmed otherwise | `comment=None`; `"  ok  "` → `"ok"` | `review/tests.py:1217-1219` response and DB `assertIsNone`; `:1225-1226` `== 'ok'` | ✅ PASS |
| CRT-15 one item per invalid field | 2 items in the same 400 | `review/tests.py:1232` `pointers == ['#/reservation', '#/rating']` | ✅ PASS |
| CRT-16 body is not a JSON object | 400 `malformed-request` | `review/tests.py:1236` | ✅ PASS |
| CRT-17 validation runs before the lookup | invalid input never answers 404/403/409 | `review/tests.py:1243` unknown reservation + rating 0 → `pointers == ['#/rating']` | ✅ PASS (M20 killed) |

### P1: Customer rating is the average

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CRT-18 average with 2 decimals | 5,4,4 → 4.33 | `review/tests.py:916` `assertEqual(customer_user.rating, 4.33)`; `:923` single → 3.0 | ✅ PASS (M7 killed) |
| CRT-19 one transaction; `select_for_update` before the insert; concurrent ratings both count | lock precedes insert; final 3.0 | `review/tests.py:962` `assertLess(lock, insert)`; `:1014-1016` race `rating == 3.0` | ✅ PASS (M21 killed; race test alone 6/6 kills, and 5/5 green unmutated) |
| CRT-20 unrated customer stays null | `None` | `review/tests.py:935` `assertIsNone(customer2_user.rating)` | ✅ PASS |
| CRT-21 new customer null (e-mail + Google); hairdresser 5 | None / 5 | `users/tests.py:5763` `rating == expected` (customer None, hairdresser 5); `:5775` Google `assertIsNone` | ✅ PASS (M8 killed) |
| CRT-22 migration nulls customers by the relation, keeps hairdressers | None for `customer` and `CUSTOMER`; 4.5 kept | `users/tests.py:5828-5829` `assertIsNone(lower/upper.rating)`; `:5838` `== 4.5` | ✅ PASS (M9 killed) |
| CRT-23 serialized as a JSON number or null | float / null in `/api/users/me` (and agenda) | `users/tests.py:5856` `assertIsInstance(rating, float)` + `== 4.33`; `:5840-5847` null; `agenda/tests.py:436-444` `'rating': 4.0` / `None` | ✅ PASS (M16 killed) |
| CRT-24 reservation deleted → rating kept, `reservation=None`, average unchanged | as stated | `review/tests.py:869-872` `assertIsNone(rating.reservation)`, `customer_user.rating == 4.0`; `:1245-1261` the rebooked edge case | ✅ PASS (M18 killed) |
| CRT-25 author account deleted → `hairdresser=None`, average unchanged | as stated | `review/tests.py:883-886` | ✅ PASS (M19 killed) |
| CRT-26 customer deleted → ratings deleted | cascade | `review/tests.py:897-898` | ✅ PASS |
| CRT-27 PATCH `rating` ignored | unchanged | `users/tests.py:5870` `assertIsNone(user.rating)` after `rating: 1` | ✅ PASS |

### P1: List a customer's ratings

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CRT-28 customer sees all, newest first | 200 `{average,count,ratings}`, `created_at` desc | `review/tests.py:1311-1313` `count == 2`, `ids == [first, second]` after `first.created_at` moved to the future | ✅ PASS (M13 killed). Minor: `average` is not asserted on the customer's own call, but `review/views.py:261` returns it for every role. |
| CRT-29 hairdresser: average and count over all ratings, only their own items | `(4.5, 2)`, 1 item | `review/tests.py:1328-1329` | ✅ PASS (M5 and M14 killed) |
| CRT-30 another customer | 403 `forbidden` | `review/tests.py:1335`; pending-customer edge case `:1407` | ✅ PASS (M6 killed) |
| CRT-31 unknown customer | 404 `not-found` | `review/tests.py:1343` | ✅ PASS |
| CRT-32 no session | 401 `invalid-session` | `review/tests.py:1347` | ✅ PASS |
| CRT-33 item shape; names null once the reservation or the author is gone | exact keys; `service_name`/`hairdresser_name` null | `review/tests.py:1356-1365` exact key set + values; `:1378-1382` nulls | ✅ PASS |
| CRT-34 no ratings | `{average:null,count:0,ratings:[]}` | `review/tests.py:1391` exact JSON equality | ✅ PASS |
| CRT-35 average = stored `User.rating` | 4.33 when the stored value differs from the rows | `review/tests.py:1416` | ✅ PASS (M14 killed) |

### P1: Agenda exposes reservation and rating

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CRT-36 `reservation_id`, `customer{id,user{first_name,last_name,rating},ratings_count}`, `customer_rating` | exact payload on both agenda routes | `agenda/tests.py:435-444` full dict equality for rated and unrated items, on `/api/agenda` and `/api/hairdressers/{id}/agenda` | ✅ PASS (M10, M11, M16 killed) |
| CRT-37 no reservation → three nulls | `(None, None, None)` | `agenda/tests.py:454-456` | ✅ PASS |
| CRT-38 constant query count, 1 vs 5 | same `assertNumQueries` | `agenda/tests.py:458-467` | ✅ PASS (M12 killed) |

### P1: Contract (errors and routes)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CRT-53 slug `service-not-finished` 409 "Service not finished"; app text | catalog of 40; app message | `hairmatch/test_problems.py:37-38` `len(CATALOG) == 40`; `:40-45` `(status, title) == (409, 'Service not finished')`; `backend/hairmatch/problems.py:58`; `.specs/features/api-problem-details/spec.md:113`; `frontend-mobile/utils/api-problem.ts:41,103` | ✅ PASS |
| CRT-54 RT-86 and RT-87 in the Route Table and `ROUTE_TABLE` | both rows | `hairmatch/test_routes.py:64-65` + `:102` `test_api_exposes_exactly_the_route_table`; `.specs/features/api-restful-routes/spec.md:153-154` | ✅ PASS |
| CRT-55 other methods → 405 + `Allow` | `POST, OPTIONS` / `GET, HEAD, OPTIONS` | `review/tests.py:1269-1270`, `:1424-1425` | ✅ PASS |

### P1/P2: App (code inspection; pending UAT T18)

Paths are relative to `frontend-mobile/`.

| Criterion | Spec-defined outcome | Evidence (`file:line`) | Result |
| --------- | -------------------- | ---------------------- | ------ |
| CRT-39 modal shows the customer's name + service/date/time | name and surname | `app/(app)/hairdresser/agenda.tsx:147-152`; name built in `hooks/hairdresserHooks/useAgenda.ts:44` | ⏳ Code OK, pending UAT |
| CRT-40 "Avaliar cliente" when reserved, ended, not rated | button shown | `useAgenda.ts:62-63` `!!reservationId && !customerRating && new Date() >= end`; `agenda.tsx:162-167` | ⏳ Code OK, pending UAT |
| CRT-41 hidden before the end or without a reservation | hidden | same `canRate` guard (`useAgenda.ts:63`) | ⏳ Code OK, pending UAT |
| CRT-42 "Sua avaliação: N★", no button | text, no button | `agenda.tsx:158-160`; `canRate` excludes rated items | ⏳ Code OK, pending UAT |
| CRT-43 rate screen: name, service, date, 5 stars, comment max 500 with `n/500` | as stated; "Cliente" fallback | `app/(app)/hairdresser/rate-customer/[reservationId].tsx:36-38,45,56,62`; fallback `hooks/hairdresserHooks/useRateCustomer.ts:18`; route `agenda.tsx:62-69` | ⏳ Code OK, pending UAT |
| CRT-44 submit disabled with no star | disabled | `[reservationId].tsx:30,72`; `useRateCustomer.ts:58,65` | ⏳ Code OK, pending UAT |
| CRT-45 confirmation "A avaliação não pode ser alterada depois de enviada." before the POST | POST only after confirm | `[reservationId].tsx:71` (opens confirm), `:79-85` (text; `onConfirm={submit}` at `:84`) | ⏳ Code OK, pending UAT |
| CRT-46 "Enviando..." + disabled while posting | as stated | `[reservationId].tsx:30,74`; double tap blocked by a ref in `useRateCustomer.ts:27,65-66` | ⏳ Code OK, pending UAT |
| CRT-47 on 201, back to the agenda, which shows "Sua avaliação" without a restart | as stated | `useRateCustomer.ts:55,73` `router.push('/(app)/hairdresser/agenda')` (**SPEC_DEVIATION** vs the design's `router.back()`); refetch on focus `useAgenda.ts:27-59`. The spec outcome ("voltar para a agenda" + updated item) is met by inspection; the deviation is from the design, not the spec. | ⏳ Code OK, pending UAT |
| CRT-48 on failure: ErrorModal with `problemMessage`, form kept | as stated | `useRateCustomer.ts:74-76` (only success resets the form, `:71-72`); `[reservationId].tsx:87` | ⏳ Code OK, pending UAT |
| CRT-49 agenda refetches on focus | as stated | `useAgenda.ts:27-59` (`useFocusEffect`) | ⏳ Code OK, pending UAT |
| CRT-50 profile: average with 1 decimal + count, "4.3 (3)" | `toFixed(1)` + `(count)` | `utils/rating.ts:4`; `hooks/customerHooks/useCustomerProfile.ts:16-31`; `app/(app)/customer/profile.tsx:51` | ⏳ Code OK, pending UAT |
| CRT-51 count 0 → "Sem avaliações" | as stated | `utils/rating.ts:3` | ⏳ Code OK, pending UAT |
| CRT-52 failure → "Nota indisponível", rest of the screen works | as stated | `useCustomerProfile.ts:24-26` | ⏳ Code OK, pending UAT |
| CRT-56 (P2) modal: average with 1 decimal + total, e.g. "4.3 (3 avaliações)" | spec example has the word "avaliações" | `agenda.tsx:153-155` renders `Nota do cliente: 4.3 (3)` via `formatCustomerRating` | ⚠️ Spec-precision gap: the CRT-56 example ("4.3 (3 avaliações)") conflicts with the CRT-50 example ("4.3 (3)"), which the shared formatter follows. The substance (1 decimal + total) is met. Non-blocking (P2, "por exemplo"). |
| CRT-57 (P2) `ratings_count` 0 → "Sem avaliações" | as stated | `utils/rating.ts:3` with `ratingsCount` from `useAgenda.ts:46` | ⏳ Code OK, pending UAT |
| CRT-58 (P2) received list: stars, comment, service, `DD/MM/YYYY`, name or "Cabeleireiro removido" | as stated | `app/(app)/customer/ratings.tsx:36-41`; menu entry `profile.tsx:75` | ⏳ Code OK, pending UAT |
| CRT-59 (P2) empty → "Você ainda não recebeu avaliações." | as stated | `ratings.tsx:30-32` (only after a successful fetch, `hooks/customerHooks/useReceivedRatings.ts:16`) | ⏳ Code OK, pending UAT |
| CRT-60 (P2) failure → ErrorModal with `problemMessage` | as stated | `useReceivedRatings.ts:30-32`; `ratings.tsx:46` | ⏳ Code OK, pending UAT |

**Status**:
- ✅ All 41 backend ACs (CRT-01 to CRT-38 and CRT-53 to CRT-55) are covered, with spec-exact assertions.
- ⏳ 18 app ACs (CRT-39 to CRT-52 and CRT-57 to CRT-60) are verified by code inspection and await UAT.
- ⚠️ 1 spec-precision gap (CRT-56).

**Test integrity check (`RatingIsNotUserSettableTest`)**: the two edited assertions (`users/tests.py:5763,5775`) changed from `5` to `None` for customers only. This is mandated by CRT-21. The payloads still carry `rating=1` / `rating=32767`, so each test still proves the request body is ignored: the stored value differs from the value sent. The hairdresser case still expects 5. This is not a weakening. The other assertion change (`test_catalog_has_the_39…` → `_40…`) is mandated by CRT-53. No test was deleted.

---

## Discrimination Sensor

Scratch: `git worktree add --detach <scratchpad>/sensor-104 HEAD`, DB `hairmatch_wt104v`. Unmutated baseline in the scratch: `review agenda users hairmatch`, 595 tests OK. Each mutation was applied by exact-string replacement, confirmed with `git diff --stat`, and restored with `git checkout` before the next one. A kill was counted only when the failing test was the one targeting that AC.

| # | File:line | Mutation | Killed by | Killed? |
| - | --------- | -------- | --------- | ------- |
| M1 | `backend/review/views.py:226` | `now < end` → `now <= end` (boundary) | `test_a_reservation_that_ends_exactly_now_is_accepted` (CRT-02) | ✅ |
| M2 | `backend/review/customer_ratings.py:23` | `service_end` ignores the duration | `test_a_reservation_that_has_not_ended_answers_409` ×3, `test_service_end_is_the_start_plus_the_duration` | ✅ |
| M3 | `backend/review/customer_ratings.py:44` | `except IntegrityError` → `except ZeroDivisionError` (duplicate → 500) | `test_a_duplicate_that_passes_the_check_answers_409_not_500`, `test_rating_a_rated_reservation_raises_review_exists…` | ✅ |
| M4 | `backend/review/views.py:221` | ownership check removed (`if False:`) | `test_the_reservation_of_another_hairdresser_answers_403` (CRT-07) | ✅ |
| M5 | `backend/review/views.py:257` | author-only filter for hairdressers removed | `test_each_hairdresser_sees_…only_their_own_ratings` ×2 (CRT-29) | ✅ |
| M6 | `backend/review/views.py:255-256` | 403 for a non-owner non-hairdresser removed | `test_another_customer_answers_403`, `test_a_pending_customer_is_answered_like_any_other` (CRT-30) | ✅ |
| M7 | `backend/review/customer_ratings.py:48` | `round(avg, 2)` → `round(avg, 1)` | `test_the_average_is_stored_with_2_decimals` (CRT-18) | ✅ |
| M8 | `backend/users/views.py:415-416` | the customer sign-up no longer nulls `rating` | 4 tests (CRT-21, CRT-23, CRT-27), e-mail and Google | ✅ |
| M9 | `backend/users/migrations/0013_null_customer_ratings.py:8` | select by `role='customer'` instead of the relation | `test_the_data_migration_nulls_every_customer_by_the_profile` (CRT-22) | ✅ |
| M10 | `backend/agenda/serializers.py:51` | `customer_rating` always `None` | `test_a_booked_item_has_…` ×2 routes (CRT-36) | ✅ |
| M11 | `backend/agenda/serializers.py:23` | `ratings_count` always 0 | `test_a_booked_item_has_…` ×2 (CRT-36) | ✅ |
| M12 | `backend/agenda/views.py:107` | `select_related('customer_rating')` removed (N+1) | `test_the_number_of_queries_does_not_grow_with_the_reservations` (CRT-38); confirms the author's claim | ✅ |
| M13 | `backend/review/views.py:259` | `-created_at` → `created_at` (oldest first) | `test_the_customer_sees_every_rating_most_recent_first` (CRT-28) | ✅ |
| M14 | `backend/review/views.py:261` | `average` recomputed from the visible rows instead of the stored `User.rating` | CRT-29 ×2, `test_the_average_is_the_stored_user_rating` (CRT-35) | ✅ |
| M15 | `backend/review/views.py:193` | length checked before the trim | `test_a_comment_of_500_characters_after_the_trim_is_accepted` (CRT-13) | ✅ |
| M16 | `backend/agenda/serializers.py:11` | `rating` dropped from the agenda's customer user | `test_a_booked_item_has_…` ×2 (CRT-36, CRT-23) | ✅ |
| M17 | `backend/review/views.py:187` | `bool` no longer refused (`true` accepted as 1) | `test_a_rating_that_is_not_an_integer_from_1_to_5_answers_400` [rating=True] (CRT-11) | ✅ |
| M18 | `backend/review/models.py:19` | reservation FK `SET_NULL` → `CASCADE` | CRT-24 tests (3 errors from `DoesNotExist` on the deleted row, 1 failure on the rebooked edge case) | ✅ |
| M19 | `backend/review/models.py:24` | hairdresser FK `SET_NULL` → `CASCADE` | `test_deleting_the_author_account_keeps_…`, `test_the_names_are_null_…` (CRT-25, CRT-33) | ✅ |
| M20 | `backend/review/views.py:212-213` | invalid input with an unknown reservation answers 404 (lookup before validation) | `test_invalid_input_is_reported_before_the_reservation_is_looked_up` (CRT-17) + 2 others | ✅ |
| M21 | `backend/review/customer_ratings.py:33` | `select_for_update()` removed | `test_the_customer_row_is_locked_before_the_insert` + `test_concurrent_ratings_of_the_same_customer_both_count` (CRT-19). Race test alone: 6/6 kills (1.0 or 5.0 ≠ 3.0); unmutated: 5/5 green. Confirms the author's claim. | ✅ |

Not used as a mutant: removing the `_is_rated` pre-check. It is behavior-equivalent, because the savepoint plus the `IntegrityError` path still answer 409 `review-exists` and roll back.

**Sensor depth**: expanded / P0 (auth, visibility, derived rating), 21 behavior-level mutations.
**Result**: 21/21 killed - PASS ✅
**Isolation**: the scratch was removed with `git worktree remove --force`. Real-tree `git status --porcelain` before = after = `?? frontend-mobile/eslint.config.js`, and HEAD stayed `0436aec`.

---

## Interactive UAT Results

Not performed by the Verifier. T18 belongs to the user, on web and Android, following the script in `tasks.md`. Until then, CRT-39 to CRT-52 and CRT-56 to CRT-60 stay "Implementing / pending UAT".

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ One domain function (`review/customer_ratings.py`), two views, and serializers. No speculative abstraction. |
| Surgical changes | ✅ The diff touches only the files the tasks list. The `review/[id].tsx` refactor is T10 (shared `StarRating`), and it removed a pre-existing eslint error. |
| No scope creep | ✅ No edit/delete endpoint, no hairdresser-rating recalculation (out of scope per the spec). |
| Matches patterns | ✅ `problem_response` / `assert_problem` / `body_error`, the `APIView` + `authenticated_*` helpers, and the service `try/await/catch` pattern in the app. |
| Spec-anchored outcome check | ✅ Backend assertions target the exact slug, detail, pointer, value and payload. One ⚠️ (CRT-56). |
| Per-layer Coverage Expectation | ✅ Domain: every branch (average, `IntegrityError`, lock order, real race, `service_end` null and boundary). Routes: happy path + 400/401/403/404/405/409 + "no row" + validation order. Agenda: with and without a reservation, rated and unrated, constant queries. |
| Every test maps to a spec requirement | ✅ Every new test carries a CRT id or a named edge case in its docstring. `CustomerRatingModelTest:840` (DB check constraint 1-5) maps to the Implicit-Requirement sweep ("`CheckConstraint` no banco") and T2's Done-when. |
| Documented guidelines followed | ✅ None versioned (no AGENTS.md/CONTRIBUTING). Strong defaults plus the project memory (tests in Docker) were applied. |

---

## Edge Cases

- [x] POST at the exact instant `start_time + duration` is accepted: `review/tests.py:1062`.
- [x] Device clock ahead → 409 `service-not-finished` (backend `review/tests.py:1074`), and the app shows the slug text (`useRateCustomer.ts:76` + `utils/api-problem.ts:103`). The app side is pending UAT.
- [x] Comment of 500 characters after the trim is accepted; 501 → 400: `review/tests.py:1200`, `:1191`.
- [x] Rate, cancel, rebook the same slot → the new reservation can be rated: `review/tests.py:1245-1261`.
- [x] Two hairdressers rate the same customer concurrently → both count: `review/tests.py:987-1016`.
- [x] Pending customer (`is_active=False`) → 200 empty for a hairdresser, 403 for another customer: `review/tests.py:1393-1407`.
- [x] Web refresh loses the route params → "Cliente"; service and date come from `GET /api/reservations/{id}`: `useRateCustomer.ts:18,39-51`. The hairdresser may read it (`backend/reserve/views.py:29,73`). Pending UAT.
- [x] Repeating average 13/3 → 4.33 stored (`review/tests.py:916`), shown as 4.3 (`utils/rating.ts:4`, `toFixed(1)`).

---

## Gate Check

- **Backend gate** (real tree, read-only container, DB `hairmatch_wt104`): `python manage.py test --noinput` exits 0. **777 run, 777 passed, 0 failed, 0 skipped.** `makemigrations --check --dry-run`: "No changes detected" (exit 0).
- **Test count before feature**: 722 executed (`def test_` count 724 on `fbf1d08`).
- **Test count after feature**: 777 executed (`def test_` count 779).
- **Delta**: +55 executed tests. No test removed. The 3 changed assertions are mandated by the spec (see the integrity check above).
- **App gate**: `npx tsc --noEmit` exits 0 with the generated typed routes, and the output is empty.
- **eslint** on the 18 changed app files: exits 1, with **0 new errors vs develop**. The single error is the `react-hooks/static-components` error for `Header` in `app/(app)/hairdresser/agenda.tsx:107`. It already exists on develop (line 95 there). The develop error in `app/(app)/customer/review/[id].tsx` is now gone. All 16 warnings are pre-existing: unused imports/vars in `profile.tsx` and `review/[id].tsx`, the duplicate dayjs locale import in `agenda.tsx`, and axios `isAxiosError` in `api-problem.ts`. Net effect vs develop: one error and one warning (`AgendaEvent` unused) fewer.
- **Skipped tests**: none.
- **Failures**: none.

---

## Fix Plans (non-blocking)

### Fix 1: CRT-56 example vs implementation (Cosmetic, P2)
- **Root cause**: the spec's CRT-56 example "4.3 (3 avaliações)" conflicts with CRT-50's "4.3 (3)". The implementation reuses `formatCustomerRating`, which gives "4.3 (3)".
- **Fix task**: choose one. Either amend CRT-56's example in `spec.md` to "4.3 (3)", or add a modal-only suffix in `agenda.tsx:154`. Confirm the choice during the T18 UAT.

### Fix 2: RF23 tick in `docs/requisitos-status.md` (user-owned)
- **Root cause**: the file is not versioned and does not exist in the worktree.
- **Fix task**: the user either ticks RF23 ✅ in the main checkout or authorizes versioning the file (success criterion #3).

### Fix 3: SPEC_DEVIATION recorded (no action needed)
- `useRateCustomer.ts:53-55` uses `router.push` to the agenda instead of `router.back()`. This deviates from the design, not from the spec. CRT-47 is met by inspection. The T18 UAT should confirm that the agenda modal shows "Sua avaliação: N★" after returning, on both web and Android.

---

## Requirement Traceability Update

The Verifier does not edit `spec.md`. These are the proposed statuses:

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| CRT-01 … CRT-38 | Implementing | ✅ Verified |
| CRT-53 … CRT-55 | Implementing | ✅ Verified |
| CRT-39 … CRT-52 | Implementing | ⏳ Code verified, pending UAT (T18) |
| CRT-56 | Implementing | ⚠️ Pending UAT + spec example to reconcile |
| CRT-57 … CRT-60 | Implementing | ⏳ Code verified, pending UAT (T18) |

---

## Summary

**Overall**: ✅ Ready for UAT. The backend is verified; the app is verified by inspection and awaits T18.

**Spec-anchored check**: 41/41 backend ACs matched the spec outcome. 18 app ACs pass code inspection and are pending UAT. 1 spec-precision gap is flagged (CRT-56). Total: 60.
**Sensor**: 21/21 mutations killed.
**Gate**: 777 passed, 0 failed. Migrations clean. `tsc` exits 0. eslint has 0 new errors.

**What works**:
- The POST with every rule: window, ownership, duplicates (pre-check and DB race), validation order.
- The derived average with the lock.
- The migration and sign-up nulls.
- List visibility for the customer, the author, other hairdressers, and other customers.
- The agenda payload at a constant query count.
- The contract (slug, routes, 405).

**Issues found (non-blocking)**:
1. CRT-56 example mismatch (Fix 1).
2. RF23 not ticked, user-owned (Fix 2).
3. T13 SPEC_DEVIATION, design-level only, to be confirmed in UAT (Fix 3).

**Next steps**:
- The user runs the T18 UAT (web + Android).
- Reconcile CRT-56.
- Tick RF23.
- After UAT, mark the app CRTs Verified.
