# Review Editing Validation

**Date**: 2026-10-10
**Spec**: `.specs/features/review-editing/spec.md` (REV-01 to REV-81, issue #105)
**Diff range**: `2948100..HEAD` (HEAD = `1456fba`, branch `105-editar-e-excluir-avaliacao`; the first commit `9af4add` only adds specs)
**Verifier**: independent sub-agent (author != verifier), second attempt (the first Verifier died of an API rate limit before writing anything)

---

## Validation

**Result**: PASS

Backend: every AC REV-01 to REV-56 has a `file:line` assertion that matches the spec outcome, with the exceptions listed under "Gaps" (one partial AC, no uncovered AC). App: REV-60 to REV-81 are verified by `tsc` and code reading only. **The manual web and Android UAT (T25) was NOT done and is PENDING.** The API was exercised end to end instead (section "E2E API run"), which replaces the UAT for the backend contract only.

| Check | Outcome |
| ----- | ------- |
| Full backend gate (`makemigrations --check` plus the whole suite with coverage) | 913 tests, 0 failed, 0 skipped. `No changes detected`. |
| `npx tsc --noEmit` in `frontend-mobile` | 0 errors (exit 0, no output) |
| Discrimination sensor | 47 mutants, 41 killed, 6 survived (1 equivalent, 5 are gaps G1 to G4), see "Discrimination Sensor" |
| E2E API run | 113 checks, 0 failures |
| Manual UAT (web and Android) | PENDING, not run |
| `eslint` | skipped by instruction (unavailable on this branch) |

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 to T24 (backend phases 1 to 3, app phases 4 and 5) | Done | 25 commits in `2948100..HEAD`, all boxes in `tasks.md` are checked up to T24 |
| T25 (manual UAT, web and Android) | PENDING | Replaced by an automated API run for the backend only. The app screens were never run by a person. |

The gate commands of `tasks.md` use `docker exec hairmatch_backend`, which is a different checkout here, so the gate ran in a throwaway container that mounts the worktree (database `hairmatch_wt_review_verify2`).

---

## Spec-Anchored Acceptance Criteria (backend, REV-01 to REV-56)

Paths are relative to the repository root. Rows say what the asserted value is and that it matches the spec outcome.

### P1: Customer sends several pictures with the review

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| REV-01 1 to 5 files in `pictures` | 201, one `ReviewPicture` per file in the order received | `backend/review/tests.py:244` status 201, `:247` `len(pictures) == 3`, `:254` `image.size == (20 + index, 10)` proves the upload order | PASS |
| REV-02 key and content | `reviews/<review_id>/<32 hex>.webp`, WebP content | `backend/review/tests.py:250` `assertRegex(name, ^reviews/{id}/[0-9a-f]{32}\.webp$)`, `:253` `image.format == 'WEBP'`, model level `:1582`, `:1584`, `:1590` (distinct keys) | PASS |
| REV-03 no file | review created without pictures | `backend/review/tests.py:264` 201, `:265` `pictures.count() == 0` | PASS |
| REV-04 more than 5 | 400 `validation-error` item `#/pictures`, no row, no object | `backend/review/tests.py:274` `assert_problem(... errors=[{'pointer': '#/pictures', ...}])`, `:277` calls `_assert_nothing_created` (`:231`, `:232`, `:234`, `:235`) | PASS |
| REV-05 over 5 MB | 400 `#/pictures`, no image opened, nothing created | `backend/review/tests.py:288`, `:291` `to_webp.assert_not_called()`, `:292`; unit `:1636` to `:1641` (5 MB + 1 refused, exactly 5 MB passes) and `:1650` to `:1658` (no file opened/read/seeked) | PASS |
| REV-06 undecodable | 400 `invalid-image` with the exact detail, no review, reservation unreviewed, no object left including earlier valid pictures | `backend/review/tests.py:305` `assert_problem(response, 'invalid-image', detail='The review picture is not a valid image.')`, `:306` -> `:231` to `:235` (`review_keys() == keys_before`); pixel bomb `:316`; unexpected failure after the upload `:328` and `:329`; helper `:1666` to `:1679` | PASS |
| REV-07 field and picture errors together | one 400 with one item per field | `backend/review/tests.py:337` two items `#/rating` then `#/pictures` | PASS |
| REV-08 old `picture` field | ignored, no picture | `backend/review/tests.py:352` 201, `:353` `pictures.count() == 0`, `:354` storage unchanged | PASS |

### P1: Customer adds and removes pictures

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| REV-10 POST adds | 201 `{data: [{id, url}]}` with all pictures by ascending id | `backend/review/tests.py:1775` 201, `:1778` `response.json() == {'data': [{id, url: default_storage.url(name)} ...]}`, `:1781` ascending ids | PASS |
| REV-11 absent or empty | 400 `#/pictures` | `backend/review/tests.py:1791` (subTest for `None` and `[]`), `:1794` | PASS |
| REV-12 over 5 in total | 400 `#/pictures`, nothing created | `backend/review/tests.py:1804` to `:1806` (4 + 2), `:1813` and `:1816` to `:1817` (full review refuses, then accepts after one removal), `:1823` (6 at once) | PASS |
| REV-13 over 5 MB | 400 `#/pictures`, no conversion, nothing created | `backend/review/tests.py:1835`, `:1838`, `:1839`, `:1840` | PASS |
| REV-14 undecodable | 400 `invalid-image`, no row, no object | `backend/review/tests.py:1850`, `:1851`, `:1852` | PASS |
| REV-15 lock before count, never above 5 | `select_for_update` before the count; two parallel requests of 3 give one 201 and one 400 | `backend/review/tests.py:1864` `assertLess(lock, count)`; real threads `:1953` `sorted(statuses) == [201, 400]`, `:1954` `count() == 3` | PASS |
| REV-16 DELETE one picture | 204, row removed, object deleted after commit | `backend/review/tests.py:1980` 204, `:1981` empty body, `:1982` only the second id left, `:1983` first object gone, `:1984` second kept | PASS |
| REV-17 review of someone else or missing | 404 `not-found`, nothing changed (both routes) | POST `backend/review/tests.py:1875` to `:1877`; DELETE `:2011` to `:2013` | PASS |
| REV-18 picture of another review or missing | 404, nothing removed | `backend/review/tests.py:2025` `detail='Picture not found.'`, `:2027`, `:2028` (the picture belongs to another review of the same customer) | PASS |
| REV-19 401 and 403 | 401 `invalid-session`, 403 `customer-required` (both routes) | POST `backend/review/tests.py:1890`, `:1897`; DELETE `:2035`, `:2045` | PASS |
| REV-20 PUT keeps its contract | PUT never touches pictures | `backend/review/tests.py:563` 200, `:565` rating 5, `:566` the same picture ids `[kept.id]` | PASS |

### P1: No orphan file

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| REV-25 delete review | rows gone, objects deleted after commit | `backend/review/tests.py:803` 204, `:804` `ReviewPicture.objects.count() == 0`, `:807` `assertFalse(default_storage.exists(name))` | PASS |
| REV-26 delete account (written and received) | objects of every review written and received are deleted after commit | received side `backend/users/tests.py:5658` (`ReviewPicture` empty) and `:5661`; written side `:5682` and `:5685` | PASS |
| REV-27 storage failure | logged with traceback, success response kept | helper level `backend/hairmatch/tests.py:481` to `:486` (one ERROR record, `exc_info` set, the next name still deleted). The route-level "success response" is not asserted anywhere | Partial, see gap G3 |
| REV-28 rollback keeps the objects | no object deleted when the transaction does not commit | review `backend/review/tests.py:818`, `:821`; picture `:1997`, `:1999`; account (Cognito outage rolls back) `backend/users/tests.py:5706`, `:5710`; create failure `backend/review/tests.py:328`, `:329` | PASS |

### P1: Responses carry the pictures

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| REV-30 `pictures: [{id, url}]`, no `picture` | RT-24, RT-43, RT-45, RT-46 | RT-24 `backend/review/tests.py:1717`, `:1722`, empty list `:1729`; RT-43, RT-45, RT-46 `backend/reserve/tests.py:838` to `:840` (subTest per route), no review `:847` | PASS |
| REV-31 public URL | the same URL the storage gives | `backend/review/tests.py:1717` to `:1720` and `:1778` use `default_storage.url(name)`; `backend/reserve/tests.py:839` | PASS |
| REV-32 constant query count | same count with 1 and with 3 reviews | RT-24 `backend/review/tests.py:1742`; RT-46 `backend/reserve/tests.py:861` | PASS |
| REV-33 cascade and order | rows removed with the review; ascending id | `backend/review/tests.py:1612` (only the other review's picture is left), `:1600`, `:1601` | PASS, order weakly pinned (gap G4) |

### P1: Hairdresser edits and deletes the rating

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| REV-40 PUT stores and answers | 200 `{data: {id, reservation, rating, comment, created_at}}` | `backend/review/tests.py:2207`, `:2209` exact key set, `:2210` ids/rating/comment, `:2215` stored | PASS |
| REV-41 comment normalization | absent, null or blank gives null; otherwise trimmed | `backend/review/tests.py:2227`, `:2230` `assertIsNone`; trimmed `:2210` (`'  Pontual  '` becomes `'Pontual'`) | PASS |
| REV-42 invalid rating | 400 `#/rating` for missing, 4.5, `"5"`, true, 0, 6 | `backend/review/tests.py:2238` pointers equal `['#/rating']` per subTest, `:2240` untouched | PASS |
| REV-43 invalid comment | 400 `#/comment` for non-string and over 500 after trim | `backend/review/tests.py:2248` (7, 501 chars, space + 501 chars), boundary 500 accepted `:2262` | PASS |
| REV-44 not a JSON object | 400 `malformed-request` | `backend/review/tests.py:2266` | PASS |
| REV-45 validate before lookup | invalid body never answers 404 or 403 | `backend/review/tests.py:2272` (missing rating), `:2275` (other author) both `validation-error` | PASS |
| REV-46 not found | 404 `not-found` on PUT and DELETE | `backend/review/tests.py:2282`, `:2356` to `:2360` | PASS |
| REV-47 not the author, author gone | 403 `forbidden`, rating and average unchanged | PUT `backend/review/tests.py:2288`, `:2289`, `:2295` to `:2298`; DELETE `:2366`, `:2367`, `:2373` to `:2375` | PASS |
| REV-48 401 and 403 | 401 `invalid-session`; 403 `hairdresser-required` | PUT `backend/review/tests.py:2304`, `:2312`; DELETE `:2381`, `:2389` | PASS |
| REV-49 DELETE | 204, rating removed | `backend/review/tests.py:2323` 204, `:2324` empty body, `:2325` | PASS |
| REV-50 average, 2 decimals, lock, same transaction | mean of the remaining, rounded to 2; `User` row locked before the write | `backend/review/tests.py:2076` (4.5), `:2088` (3.67), `:2102` (3.5), lock before UPDATE `:2144`, lock before DELETE `:2156`. "Same transaction" has no discriminating test | PASS, atomicity gap G2 |
| REV-51 last rating removed | `User.rating` is null | `backend/review/tests.py:2115`, `:2337`, `:2128` | PASS |
| REV-52 reservation freed | POST answers 201 after the DELETE | `backend/review/tests.py:2347` 409 before, `:2349` 204, `:2351` 201, `:2352` average 3.5 | PASS |
| REV-53 other ratings untouched | unchanged | `backend/review/tests.py:2081`, `:2328`, `:2104` to `:2106`, `:2125`, `:2129` | PASS |

### P1: Agenda and Route Table

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| REV-55 agenda `customer_rating` | `{id, rating, comment}` | `backend/agenda/tests.py:738` to `:741` `== {'id': rated.customer_rating.id, 'rating': 4, 'comment': 'Pontual'}` | PASS |
| REV-56 RT-90 to RT-93 | in the spec table and in `ROUTE_TABLE` | `backend/hairmatch/test_routes.py:70` to `:73`, enforced by `:110` to `:114` (exact equality with the routed API); spec table `.specs/features/api-restful-routes/spec.md:157` to `:160` | PASS |

**Status**: all 43 backend ACs map to a passing assertion with the spec outcome. Gaps are non-blocking (G1 to G6 below), no AC is without evidence.

---

## App ACs (REV-60 to REV-81): code read plus `tsc`, UAT PENDING

The app has no automated tests. Each row says whether the code satisfies the AC text. None of this has been run by a person.

| AC | Implementing code | Satisfies the AC text? |
| -- | ----------------- | ---------------------- |
| REV-60 title "Avaliar Atendimento", empty form | `frontend-mobile/app/(app)/customer/review/[id].tsx:44`; initial state `frontend-mobile/hooks/customerHooks/useReviewForm.ts:18` to `:23`, `:33` | Yes |
| REV-61 "Editar avaliação" opens the filled form | menu `frontend-mobile/app/(app)/customer/reserves/[id].tsx:142`, `frontend-mobile/hooks/customerHooks/useReserveDetails.ts:69` to `:73`; title `review/[id].tsx:44`; prefill `useReviewForm.ts:46` to `:52` | Yes |
| REV-62 picker options | `useReviewForm.ts:76` to `:81` (`allowsMultipleSelection`, `selectionLimit: remaining`, `quality: 0.5`, no `allowsEditing`); `remaining` `:34` | Yes |
| REV-63 keep the first that fit and warn | `useReviewForm.ts:90` to `:93` ("Você pode enviar até 5 fotos.") | Yes |
| REV-64 hide the add button at 5 | `useReviewForm.ts:180`, `review/[id].tsx:96` | Yes |
| REV-65 "x" removes without calling the backend | `useReviewForm.ts:97` to `:104`; the DELETE only happens at save `:136` to `:140` | Yes |
| REV-66 one POST with all pictures | `useReviewForm.ts:146` to `:152`, `frontend-mobile/services/review.service.ts:30` to `:40` (repeated `pictures` field) | Yes |
| REV-67 PUT, then DELETEs, then POST, skipping empty steps, back to the detail | `useReviewForm.ts:133` to `:144` and `:162`; services `review.service.ts:43` to `:63` | Yes |
| REV-68 failure handling | `useReviewForm.ts:163` to `:166` (ErrorModal with `problemMessage`), `:107` to `:119` (reload, still-stored removals stay hidden and marked, queue and typed text kept) | Yes |
| REV-69 "Enviando..." and ignore taps | `review/[id].tsx:109` to `:113`; guard `useReviewForm.ts:122`, `:128` to `:129` | Yes |
| REV-70 horizontal row of all pictures, placeholder when none | `reserves/[id].tsx:120` to `:130`; type `frontend-mobile/models/Review.types.ts:113` to `:127` | Yes |
| REV-75 "Sua avaliação: N★" with edit and delete buttons | `frontend-mobile/app/(app)/hairdresser/agenda/index.tsx:182` (text), `:193` to `:208` (buttons) | Yes |
| REV-76 edit opens the screen with the params and current values | `frontend-mobile/hooks/hairdresserHooks/useAgenda.ts:106` to `:120`; read by id `frontend-mobile/hooks/hairdresserHooks/useRateCustomer.ts:66` to `:97`; title `frontend-mobile/app/(app)/hairdresser/rate-customer/[reservationId].tsx:36` | Yes |
| REV-77 missing rating or failed read | `useRateCustomer.ts:71` to `:75`, `:83`, `:87` to `:92` (message "Não foi possível carregar a avaliação."), back to the agenda on close `:150` to `:156` | Yes |
| REV-78 PUT after the confirmation, back to the agenda | `rate-customer/[reservationId].tsx:85` (text "Salvar as alterações da avaliação?"); `useRateCustomer.ts:116` to `:124` (empty comment becomes null) | Yes |
| REV-79 create confirmation wording | `rate-customer/[reservationId].tsx:86` | Yes |
| REV-80 delete flow | `useAgenda.ts:122` to `:148`; confirmation `agenda/index.tsx:221` to `:228` (title "Excluir avaliação?") | Yes |
| REV-81 failure shows ErrorModal, edit screen keeps the text | `useRateCustomer.ts:125` to `:130` (the form is only cleared on success `:122` to `:123`); delete `useAgenda.ts:141` to `:145`, `agenda/index.tsx:229` | Yes |

`tsc --noEmit`: 0 errors. Leftover references to `Review.picture`, `review.picture`, `reviews/images` or `_delete_stored_files` in `backend/` and `frontend-mobile/`: none (grep clean outside migrations).

---

## Discrimination Sensor

Depth: expanded (P0 data-integrity and storage paths). Faults were injected only in an exported copy of `HEAD` (`git archive`), the app tests ran against that copy in a throwaway container, and the copy was deleted afterwards. Tests: `review` app (154 tests, about 3 s) unless another target is named.

| # | File | Fault | Killed? / killing test |
| - | ---- | ----- | ---------------------- |
| M01 | `backend/review/views.py` | `ReviewPictureCollection`: drop `select_for_update` | Killed: `test_the_review_row_is_locked_before_the_pictures_are_counted` (`review/tests.py:1854`) and the thread race `:1913` |
| M02 | `backend/review/views.py` | `CreateReview`: drop `delete_stored_files(saved_names)` on `InvalidImage` | Killed: `test_create_review_with_a_file_that_is_not_an_image_returns_400_and_cleans_the_earlier_pictures` (`:294`) |
| M03 | `backend/review/views.py` | `CreateReview`: drop the cleanup on an unexpected error | Killed: `test_an_unexpected_failure_after_the_upload_leaves_no_object_in_the_storage` (`:319`) |
| M04 | `backend/review/views.py` | RT-90: drop the cleanup on `InvalidImage` | Killed: `test_an_undecodable_file_answers_400_and_leaves_no_row_and_no_object` (`:1842`) |
| M05 | `backend/review/views.py:231` | RT-90: drop the cleanup on an unexpected error | **Survived** (gap G1) |
| M06 | `backend/review/pictures.py:22` | count limit `>` to `>=` | Killed: `:1808`, `:1628` |
| M07 | `backend/review/pictures.py:24` | 5 MB limit `>` to `>=` | Killed: `test_a_file_over_5_mb_is_one_error_and_exactly_5_mb_passes` (`:1636`) |
| M08 | `backend/review/pictures.py:24` | 5 MB check removed | Killed: `:1826` and `:279` |
| M09 | `backend/review/views.py` | `CustomerRatingDetail`: ownership check removed | Killed: `:2362`, `:2369`, `:2284`, `:2291` |
| M10 | `backend/review/customer_ratings.py` | `update_customer_rating` skips `_store_average` | Killed: `:2069`, `:2083` |
| M11 | `backend/review/customer_ratings.py` | `delete_customer_rating` skips `_store_average` | Killed: `:2330`, `:2319` |
| M12 | `backend/review/customer_ratings.py` | `update_customer_rating`: drop the `User` lock | Killed: `test_the_customer_row_is_locked_before_the_update` (`:2134`) |
| M13 | `backend/review/customer_ratings.py` | `delete_customer_rating`: drop the `User` lock | Killed: `test_the_customer_row_is_locked_before_the_delete` (`:2146`) |
| M14 | `backend/review/customer_ratings.py:29` | `round(average, 2)` to 1 decimal | Killed: `:2083` (3.67) |
| M15 | `backend/review/customer_ratings.py:29` | no rounding | Killed: `:2083` |
| M16 | `backend/review/views.py:194` | `RemoveReview` deletes objects at once instead of `on_commit` | Killed: `:809` |
| M17 | `backend/review/views.py:257` | `ReviewPictureDetail` deletes the object at once | Killed: `:1989` |
| M18 | `backend/review/views.py:194` | `RemoveReview` never deletes the objects | Killed: `:795` |
| M19 | `backend/users/views.py:246` | `_delete_account_rows`: written side (`customer__user`) dropped | Killed: `users.tests.CognitoDeleteAccountTest` customer test (`users/tests.py:5664`) |
| M20 | `backend/users/views.py:246` | `_delete_account_rows`: received side (`hairdresser__user`) dropped | Killed: hairdresser test (`users/tests.py:5644`) |
| M21 | `backend/users/views.py:245` | review picture names not collected at all | Killed: `users/tests.py:5664` and `:5644` |
| M22 | `backend/review/views.py:145` | `ListReview`: drop `prefetch_related('pictures')` | Killed: `:1731` |
| M23 | `backend/reserve/views.py:72` | `ReserveById` (RT-43): drop `prefetch_related('review__pictures')` | **Survived, equivalent**: a single reservation costs the same number of queries with or without the prefetch, and REV-32 only names RT-24 and RT-46 |
| M24 | `backend/reserve/views.py:164` | `ListReserve` (RT-45, RT-46): drop `prefetch_related('review__pictures')` (re-run after a first attempt hit RT-43 by mistake) | Killed: `reserve/tests.py:849` |
| M25 | `backend/review/views.py:146` | `ListReview`: drop `.order_by('id')` | Killed: `:1731` (asserts the review order `[2, 3, 1]`) |
| M26 | `backend/review/views.py` | customer-rating PUT looks the rating up before validating the body | Killed: `test_an_invalid_body_answers_400_before_the_rating_is_looked_up` (`:2269`) |
| M27 | `backend/review/views.py:249` | `ReviewPictureDetail`: picture lookup without `review=review` | Killed: `:2015` |
| M28 | `backend/review/customer_ratings.py` | rating DELETE keeps the row (reservation not freed) | Killed: `:2146`, `:2319`, `:2339` |
| M29 | `backend/review/views.py:194` | `RemoveReview` calls `default_storage.delete` raw, without the swallow/log helper | **Survived** (gap G3) |
| M30 | `backend/hairmatch/storage.py:85` | `delete_stored_files` re-raises | Killed: `hairmatch/tests.py:469` |
| M31 | `backend/review/views.py:83` | `CreateReview` also reads the old `picture` field | Killed: `:342` |
| M32 | `backend/review/views.py:224` | RT-90 count ignores the existing pictures | Killed: `:1854` and `:1796` |
| M33 | `backend/agenda/serializers.py:51` | `customer_rating` without `id` | Killed: `agenda/tests.py:725` |
| M34 | `backend/review/pictures.py:37` | `add_review_pictures` stops recording the stored names | Killed: `:1842`, `:294` |
| M35 | `backend/review/views.py:355` | customer-rating PUT does not trim the comment | Killed: `:2203` and `:2221` |
| M36 | `backend/review/models.py:12` | picture path loses the uuid (fixed name) | Killed: `:1586` |
| M37 | `backend/review/views.py:221` | RT-90 review lookup without the customer filter | Killed: `:1866` |
| M38 | `backend/review/views.py:246` | RT-91 review lookup without the customer filter | Killed: `:2001` |
| M39 | `backend/review/views.py:257` | RT-91 never deletes the object | Killed: `:1973` |
| M40 | `backend/review/serializers.py:15` | picture `url` is the storage name | Killed: `:1768` |
| M41 | `backend/review/serializers.py:25` | `ReviewLiteSerializer` without `pictures` | Killed: `reserve/tests.py:849` |
| M42 | `backend/review/models.py:30` | `Meta.ordering = ['id']` removed | **Survived** (gap G4) |
| M43 | `backend/review/views.py:235` | RT-90 answers only the new pictures | Killed: `:1768` |
| M44 | `backend/review/views.py:192` | `RemoveReview` reads the picture names after `review.delete()` | Killed: `:795` |
| M46 | `backend/review/customer_ratings.py:60` | `update_customer_rating` without `transaction.atomic()` | **Survived** (gap G2) |
| M47 | `backend/review/customer_ratings.py:71` | `delete_customer_rating` without `transaction.atomic()` | **Survived** (gap G2) |
| M48 | `backend/review/views.py:192` | `RemoveReview` collects no picture names | Killed: `:795` |

(There is no M45: it was a duplicate of M05 and is not counted.)

**Sensor depth**: expanded (more than 5 mutations, all branches of the new storage and average code).
**Sensor outcome**: 47 mutants run (M01 to M44, M46, M47 and M48; the first M24 hit RT-43 by mistake and was re-run as the real M24; M45 was a duplicate of M05 and is not counted). 41 killed, 6 survived: M05, M29, M42, M46, M47 (gaps G1 to G4, non-blocking) and M23 (equivalent). Kill rate 41 of 46 non-equivalent mutants.

---

## Interactive UAT

| # | Test | Outcome | Details |
| - | ---- | ------- | ------- |
| 1 to N | Create a review with 3 pictures, edit removing 1 and adding 2, check the 4 pictures and the bucket (web and Android) | PENDING | Not run by a person (T25) |
| - | Hairdresser edits 5 to 3 and sees "Sua avaliação: 3★"; deletes and sees "Avaliar cliente" again (web and Android) | PENDING | Not run by a person (T25) |

REV-60 to REV-81 are therefore verified by `tsc` and code reading only. The Success Criteria boxes of the spec that need the app (edit without restarting, "Sem avaliações" in the profile) stay unchecked until the UAT is done.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code, no scope creep | Yes: one shared helper (`delete_stored_files`) replaced the private `_delete_stored_files` in `users/views.py`; the pictures module and the customer-rating module hold the new logic |
| Surgical changes | Yes: only `review`, `reserve`, `users`, `agenda`, `hairmatch` tests/storage and the app files of the feature changed |
| Matches patterns | Yes: `problem_response`, `validation_problem`, `on_commit` deletion and `select_for_update`, as in #104 and #120 |
| Spec-anchored outcome check | Yes, see the AC tables |
| Every test maps to a requirement | Yes: new tests cite REV ids in their docstrings or sit in REV-named classes |
| Documented guidelines followed | none - strong defaults applied |

One `SPEC_DEVIATION` marker exists in `frontend-mobile/hooks/hairdresserHooks/useRateCustomer.ts:99`. It predates this feature (it is in `2948100`) and is consistent with REV-78 ("voltar para a agenda").

---

## Edge Cases

- [x] 6 files in `POST /api/reviews` give a 400 and nothing is created (`backend/review/tests.py:274`, `:277`).
- [x] The third of three pictures is invalid: the first two leave the storage (`backend/review/tests.py:305`, `:306`, `:1850` to `:1852`).
- [x] A review with 5 pictures refuses RT-90 until one is removed (`backend/review/tests.py:1813` to `:1817`).
- [x] Two parallel requests of 3 pictures on a review with 0 give one 201 and one 400 (`backend/review/tests.py:1953`, `:1954`; also in the E2E run with real processes).
- [x] A `picture_id` of another review of the same customer gives 404 (`backend/review/tests.py:2025` to `:2028`).
- [x] The only rating removed gives `User.rating = null` (`backend/review/tests.py:2115`, `:2337`).
- [x] A rating whose author deleted the account cannot be edited or removed by anyone (`backend/review/tests.py:2295`, `:2373`).
- [ ] Edit that fails at the DELETE step shows the real state of the pictures (REV-68): code-read only (`useReviewForm.ts:107` to `:119`), UAT pending.

---

## Gate Check

- **Gate command** (replaces the `docker exec` of `tasks.md`): throwaway container, worktree mounted, database `hairmatch_wt_review_verify2`: `python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput && coverage report -m`
- **Outcome**: `No changes detected`; `Ran 913 tests`, `OK`; 0 failed, 0 skipped
- **Test count before the feature**: 835. **After**: 913. **Delta**: +78 tests. No test was deleted. The WEBP-03, WEBP-12 and WEBP-13 tests were rewritten for `pictures` without losing their WebP and invalid-image assertions (`backend/review/tests.py:237`, `:294`, `:308`).
- **Coverage of the touched files** (statements missed): `review/views.py` 261/0 (100%), `review/pictures.py` 19/0 (100%), `review/customer_ratings.py` 38/0 (100%), `review/models.py` 28/0 (100%), `review/serializers.py` 38/0 (100%), `review/urls.py` 100%, `agenda/serializers.py` 100%, `hairmatch/storage.py` 58 statements, 3 missed (lines 42, 43, 66, all in `S3MediaStorage`, none in the new `delete_stored_files`), `reserve/views.py` 236 statements, 23 missed (none in the changed lines; they are the pre-existing cancel and external-block paths), `users/views.py` 622 statements, 4 missed (137, 138, 287, 288, outside `_delete_account_rows`). Total 99% (11396 statements, 170 missed).
- **Porcelain before and after**: only `?? .specs/LESSONS.md` and `?? .specs/lessons.json`; after this report, plus `.specs/features/review-editing/validation.md`.

---

## E2E API run (replacement for the manual UAT of the backend contract)

Script and output live outside the repository in the scratchpad: `e2e/e2e_review_editing.py` and `e2e/e2e_output.txt`. The run used a real server, a real database and a real S3-compatible bucket, now torn down, and was not rerun by this Verifier. Output summary line: `SUMMARY: 113 passed, 0 failed of 113`.

- Accounts, services and reservations were created through the public routes (register, confirm, login, `POST /api/services`, `POST /api/reservations`).
- `POST /api/reviews`: 401 `invalid-session`, 403 `customer-required`, 400 for 6 pictures, 400 for a picture over 5 MB, 400 `invalid-image` for `[png, png, not an image]` (the two uploaded pictures are gone from the bucket and the reservation stays unreviewed), a combined 400 with `#/rating` and `#/pictures`, 409 `review-exists`, and 201 with 3 pictures, with none, and with the old `picture` field (no picture, no object).
- After the upload the bucket held 3 keys `reviews/<review_id>/<32 hex>.webp`, each object starting `RIFF....WEBP`; every `url` pointed at its key; RT-24, RT-43, RT-45 and RT-46 listed the 3 pictures as `{id, url}` with no `picture` key.
- `PUT /api/reviews/{id}`: 200 (a `picture`/`pictures` body changed nothing, bucket unchanged), 400 without rating, 404 for another customer, 403 `customer-required`, 401.
- RT-90: 201 with all 5 pictures by ascending id and 5 WebP keys; the 6th gave 400 and added nothing; `invalid-image` on a review with room left no row and no object; an invalid body for a missing review gave 400; two parallel requests of 3 pictures gave one 201 and one 400 and exactly 3 pictures and 3 objects.
- RT-91: 204 with an empty body and the object gone while the other 4 stayed; repeat gave 404; a picture of another review of the same customer gave 404; unknown ids gave 404.
- `DELETE /api/reviews/{id}`: another customer 404 with objects kept; the owner 204 with all 4 objects gone, the reservation unreviewed again and re-reviewable (201 with 2 pictures); other reviews' objects untouched.
- RT-92 and RT-93: ratings 5 and 3 gave an average of 4.0, an edit gave 4.5 and the other rating stayed; invalid ratings (missing, 4.5, `"5"`, true, 0, 6), invalid comments and non-object bodies gave 400 (`validation-error` or `malformed-request`), also for a missing rating (400 before 404) and for another author (400 before 403); then 404, 403 `forbidden`, 403 `hairdresser-required`, 401; the average stayed 4.5 through every refused call; DELETE gave 204 and the average of the rest (5.0), deleting the last rating gave 204 and a null average with count 0, the agenda showed no `customer_rating` again, and the reservation was rated again with 201 (average 2.0); another hairdresser's rating raised the average to 3.0; the agenda carried `customer_rating {id, rating, comment}` (REV-55).
- Account deletion: the customer's and the hairdresser's accounts were deleted (written and received sides) and every `reviews/` object of their reviews left the bucket, other reviews' objects stayed; at the end no object remained under `reviews/`; a rating whose author deleted the account answered 403 `forbidden` to PUT and DELETE from another hairdresser and kept the 3.0 average.

---

## Gaps (all non-blocking; no AC without evidence)

| ID | Gap | AC | Evidence | Proposed test (not written, the real tree is read-only for the Verifier) |
| -- | --- | -- | -------- | ------------------------------------------------------------------------ |
| G1 | No test that RT-90 deletes the already stored objects when a later step fails unexpectedly (500). Mutant M05 survived. The create route has this test (`:319`), RT-90 does not. Spec: Goals ("no operation leaves an orphan"), Implicit dimension "External-dependency failure", REV-14. | REV-14, REV-28 | `backend/review/views.py:231` | In `AddReviewPicturesTest`: patch `review.views.add_review_pictures` with a wrapper that calls the real one and then raises `RuntimeError`, post two valid PNGs, expect `assert_problem(response, 'internal-error')`, no new `ReviewPicture` row and `review_keys() == before`. |
| G2 | The "same transaction" part of REV-50 is not discriminated: every test runs inside the `TestCase` transaction, so removing `transaction.atomic()` from `update_customer_rating` or `delete_customer_rating` survives (M46, M47). There is no `ATOMIC_REQUESTS`, so in production a missing block makes `select_for_update` raise. The E2E run (real autocommit) covers it, the suite does not. | REV-50 | `backend/review/customer_ratings.py:60`, `:71` | A `TransactionTestCase` that patches `_store_average` to raise after the write, calls `update_customer_rating` and `delete_customer_rating`, and asserts the rating row and `User.rating` are unchanged (rollback). `CustomerRatingRaceTest` (`review/tests.py:1120`) is the model for it. |
| G3 | REV-27 "keep the success response" is asserted only on the shared helper. A call site that bypasses `delete_stored_files` (M29) survives. | REV-27 | `backend/review/views.py:194`, `:257` | In `RemoveReview` and `RemoveReviewPictureTest`: patch `default_storage.delete` to raise `OSError`, run with `captureOnCommitCallbacks(execute=True)`, expect 204 and an ERROR log from `hairmatch.storage`. |
| G4 | The ascending-id order of `review.pictures` is not pinned independently of insertion order: dropping `Meta.ordering` survives (M42), because PostgreSQL returns rows in heap order. | REV-30, REV-33 | `backend/review/models.py:30` | Create 3 pictures, `ReviewPicture.objects.filter(pk=first.pk).update(created_at=timezone.now())` (an UPDATE moves the tuple), then assert `list(review.pictures.values_list('id', flat=True)) == sorted(ids)`. |
| G5 | Spec-precision: the spec does not say whether RT-90 validates the body before looking the review up. The code validates first (`views.py:211` to `:215`) and the test `review/tests.py:1884` pins it, but only REV-45 states this order, for the customer-rating PUT. | REV-11, REV-17 | `backend/review/views.py:211` | Add one line to the spec: "RT-90 validates `pictures` before looking up the review". |
| G6 | Spec-precision: the order of the reviews in `GET /api/hairdressers/{id}/reviews` is not defined. The code orders by `id` (`views.py:146`), only an incidental assertion (`review/tests.py:1741`) covers it. | REV-30 | `backend/review/views.py:146` | State the order in the spec and assert it directly. |

Not a gap: M23 (RT-43 prefetch) is an equivalent mutant for a single reservation.

### Observations (not defects of the AC set)

- Narrow race: `PUT /api/customer-ratings/{id}` looks the rating up outside the transaction. If a `DELETE` of the same rating commits in between, `save(update_fields=...)` raises and the client gets a 500 instead of a 404 (`backend/review/customer_ratings.py:64`).
- Narrow race: `DELETE /api/reviews/{id}` does not lock the review, while RT-90 does. A picture added between reading the names (`views.py:192`) and `review.delete()` can leave its object in the bucket or fail the delete on a foreign key.
- Pre-existing: `CreateReview` does not lock the reservation, so two parallel creations for the same reservation can leave a review that no reservation references, and its pictures stay in the bucket (`backend/review/views.py:107`).
- Pre-existing and stale: the review screen subtitle is hard-coded to "até 31/12/2025" (`frontend-mobile/app/(app)/customer/review/[id].tsx:45`).
- The spec Success Criteria checkboxes stay unchecked until the UAT is done.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| REV-01 to REV-26, REV-28, REV-30 to REV-33, REV-40 to REV-56 | Implemented | Verified (REV-50 with gap G2, REV-33 with gap G4) |
| REV-27 | Implemented | Verified at helper level, route level partial (G3) |
| REV-60 to REV-81 | Implemented | Verified by `tsc` and code reading only, UAT PENDING |

---

## Summary

**Overall**: Ready for review with non-blocking gaps and a pending manual UAT.

**Spec-anchored check**: 42 of 43 backend ACs fully matched the spec outcome, REV-27 partially (G3); 2 spec-precision gaps (G5, G6)
**Sensor**: 41 of 46 non-equivalent mutants killed (survivors M05, M29, M42, M46, M47)
**Gate**: 913 passed, 0 failed; `tsc` 0 errors; E2E 113 of 113

**What works**: the picture model, limits and cleanup, the edit and delete of the customer rating with the recalculated average, the lists and the Route Table, and the whole API contract against a real bucket.

**Issues found**: G1 to G6 above, none blocking.

**Next steps**: run the manual UAT (T25) on web and Android; optionally add the tests proposed for G1 to G4.

## Follow-up after the Verifier (gaps G1 to G4 closed)

The author added tests for the surviving mutants that were real gaps, with no change to production code:

- G1 (M05): `backend/review/tests.py` `test_an_unexpected_failure_after_the_upload_leaves_no_row_and_no_object` (RT-90, REV-14).
- G2 (M46, M47): `CustomerRatingAtomicityTest` in `backend/review/tests.py` (REV-50). Removing the `atomic` of `update_customer_rating` now fails it.
- G3 (M29): `test_a_storage_failure_when_deleting_is_logged_and_the_answer_stays_204` for `RemoveReview` and for RT-91 (REV-27).
- G4 (M42): `test_the_order_by_id_does_not_depend_on_where_the_rows_sit` (REV-33).

Full gate after the follow-up: 918 tests OK, `makemigrations --check` clean. G5 and G6 stay as spec-precision notes. The manual web and Android UAT is still PENDING.
