# Hairdresser Gallery Validation

**Date**: 2026-10-10
**Spec**: `.specs/features/hairdresser-gallery/spec.md`
**Diff range**: `2948100..HEAD` = `2948100..054a493` (feature commits `9af4add..HEAD`; `9af4add` only adds the specs)
**Verifier**: independent sub-agent (author != verifier)

## Validation: hairdresser-gallery - PASS

**Overall**: ✅ Ready for the backend and the code-level checks of the app. The manual web/Android UAT (T18) is still PENDING, so the app-only ACs stay "Needs manual UAT".

**Round**: 2 (round 1 at `e290334` found two weak GAL-45 tests, M21 survived and M27 was flaky; both fixed test-only in `054a493`; HEAD = `054a493`).
**Spec-anchored check**: 38 of 38 backend ACs matched the spec outcome (GAL-45 now included); 3 spec-precision notes. App ACs: 0 deviations found reading the code against the spec literally.
**Sensor**: 30 mutations injected, 30 killed, 0 survived (M21 killed once, M27 killed 6 of 6 runs; M14 and M26 re-checked, still killed).
**Gate**: 882 passed, 0 failed; `makemigrations --check` clean; `npx tsc --noEmit` 0 errors.

Ranked gaps: none open. (Round-1 gaps: M21 `populate_hairdressers.py:70` and M27 `populate_hairdressers.py:72`, resolved by `054a493`, see Fix Plans.)

**Scope note**: every `file:line` below is against committed `HEAD` `054a493`. The only change since round 1 is `backend/users/tests.py` (+14/-8 in `054a493`), so the GAL-45 test lines shifted (cited below at their new numbers) and no production file changed.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 to T17 | ✅ Done | Marked `[x]` in `tasks.md`; commits `50a1686` to `c3acaad` map one-to-one (T1 `50a1686`, T2 `ecdefa2`, T3 `b0bcf54`, T4 `1be178a`, T5 `3eb98d8`, T6 `ee72f14`, T7 `9ce0f90`, T8 `46a0e04`, T9 `06dfcd8`, T10 `14e1264`, T11 to T17 `4415810`..`c3acaad`). |
| T18 | ⚠️ Partial | The automated half (author-run API E2E, 56 checks) is done; the manual web/Android UAT is PENDING (see Interactive UAT). |

---

## Spec-Anchored Acceptance Criteria

Backend. Test file is `backend/users/tests.py` unless another is named. `assert_problem(response, slug, ...)` (`backend/hairmatch/problem_testing.py:10-26`) asserts the catalog status code, the `application/problem+json` content type, the member set, the `type` URI and the title, so a `gallery-full` check is a real 409 check.

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| GAL-01 list order | 200 `{"data": [...]}`, items `{id,image,created_at}`, `created_at` desc then `id` desc | `tests.py:6729` `assertEqual([item['id'] for item in data], [photos[2].pk, photos[1].pk, photos[0].pk, oldest.pk])`; `:6730` `assertEqual(set(data[0]), {'id','image','created_at'})`; tie `:6741` `[second.pk, first.pk]`; model order `:6696`; other owner excluded `:6750` | ✅ PASS |
| GAL-02 empty | 200 `{"data": []}` | `tests.py:6756-6757` `assertEqual(response.json(), {'data': []})` | ✅ PASS |
| GAL-03 unknown id | 404 `not-found` | `tests.py:6763` `assert_problem(response, 'not-found', detail='Hairdresser not found.')`; customer id `:6772` | ✅ PASS |
| GAL-04 anonymous GET | 200 with photos, no cookie | `tests.py:6777` `assertFalse(self.client.cookies)`; `:6781` `assertEqual((status, len(data)), (200, 1))` | ✅ PASS |
| GAL-05 key and URL | `default_storage.url` of `hairdresser/gallery/<id>/<32 hex>.webp`, no original name | `tests.py:6789` `assertRegex(image, rf'hairdresser/gallery/{pk}/[0-9a-f]{{32}}\.webp$')`; `:6731` `data[0]['image'] == default_storage.url(name)`; model `:6667`; name hidden (`assertNotIn('praia', ...)`) | ✅ PASS |
| GAL-09 create | 201 `{"data": {id,image,created_at}}` | `tests.py:6855` `assertEqual(response.status_code, 201)`; `:6857-6863` full body equality; `:6876` `assertEqual(listed, [created])` | ✅ PASS |
| GAL-10 WebP, 1080 px, key | stored object is WebP, longest side <= 1080, on the gallery key | `tests.py:6868` `assertEqual((stored.format, max(stored.size)), ('WEBP', 1080))` for a 2000x1500 source; `:6865` key regex; `:6866` only that object in the directory | ✅ PASS |
| GAL-11 no `image` field | 400 `validation-error`, pointer `#/image`, no row, no file | `tests.py:6882-6885` `assert_problem(..., 'validation-error', errors=[{'pointer': '#/image', 'detail': 'This field is required.'}])`; `:6886` `_assert_nothing_stored()` | ✅ PASS |
| GAL-12 over 5 MB | 400 `validation-error`, pointer `#/image`, nothing stored | `tests.py:6902-6906` same assertion for 5 MB + 1 (non-image bytes, so the size check runs first); `:6910` 5 MB exactly goes on to `invalid-image` (boundary) | ✅ PASS |
| GAL-13 not an image | 400 `invalid-image`, nothing stored | `tests.py:6916` `assert_problem(response, 'invalid-image', detail='The photo is not a valid image.')`; `:6917` nothing stored | ✅ PASS |
| GAL-14 30 photos | 409 `gallery-full`, nothing stored | `tests.py:6925` `assert_problem(response, 'gallery-full')`; `:6926` `_assert_nothing_stored(rows=30)`; boundary 30th ok / 31st refused `:6935-6936`; other owner's photos not counted `:6946` | ✅ PASS |
| GAL-15 concurrency | at most `30 - N` stored, the rest 409 `gallery-full` | `tests.py:7054-7057` `assertEqual(sorted(results), sorted([(201,'')]*2 + [(409,'https://hairmatch.app/problems/gallery-full')]*2))`; `:7058` 30 rows; `:7059` 2 objects; lock-before-count-before-insert order `:6999-7010` | ✅ PASS |
| GAL-16 no session | 401 `invalid-session`, nothing stored | `tests.py:6954` `assert_problem(response, 'invalid-session')`; `:6955` | ✅ PASS |
| GAL-17 customer | 403 `hairdresser-required` | `tests.py:6963` `assert_problem(response, 'hairdresser-required')`; `:6964` | ✅ PASS |
| GAL-18 foreign id | 403 `forbidden`, nothing stored | `tests.py:6970` `assert_problem(response, 'forbidden')`; `:6971-6972` both hairdressers untouched | ✅ PASS |
| GAL-19 storage failure | 500 `internal-error`, no row | `tests.py:6980-6981` `assert_problem(response, 'internal-error')` with `default_storage.save` raising; no rows, no files; `:6989-6990` insert failure after upload also removes the file | ✅ PASS |
| GAL-31 delete | 204, row gone, file removed after commit | `tests.py:7085` 204; `:7086` `response.content == b''`; `:7087` row gone; `:7088` file still there before callbacks; `:7091` `assertFalse(default_storage.exists(...))` after callbacks | ✅ PASS |
| GAL-32 not found / other owner | 404 `not-found`, nothing deleted | `tests.py:7099-7100` (other's photo under own id), `:7107-7108` (unknown id) with `execute=True` callbacks and `_assert_untouched()` (2 rows, 2 files) | ✅ PASS |
| GAL-33 auth order | 401 / 403 `hairdresser-required` / 403 `forbidden`, nothing deleted | `tests.py:7124`, `:7134`, `:7142` + `_assert_untouched()` | ✅ PASS (see precision note 1) |
| GAL-34 storage failure after commit | 204 kept, failure logged with the key | `tests.py:7152` 204; `:7153` row gone; `:7154` `assertIn(f'Could not delete {name} from the media storage', logs.output[0])` | ✅ PASS |
| GAL-39 account deletion | gallery rows deleted, files deleted after commit | `tests.py:5795` rows `== [other.pk]`; `:5797` files still exist before callbacks; `:5802` `assertFalse(default_storage.exists(name))` after callbacks; `:5803` other owner's file kept | ✅ PASS |
| GAL-40 rolled back | rows and files kept on Cognito error | `tests.py:5806` test; `:5814` 503, `:5815` `assertEqual(GalleryPhoto.objects.filter(hairdresser=hairdresser).count(), 2)`, `:5818` `assertTrue(default_storage.exists(name))` | ✅ PASS |
| GAL-41 routes | RT-94..96 in `ROUTE_TABLE`, no extra route | `hairmatch/test_routes.py:69-71` entries; `:111-112` `assertEqual(sorted(ROUTE_TABLE - found), [])` and `sorted(found - ROUTE_TABLE) == []`; spec rows in `api-restful-routes/spec.md` (diff) | ✅ PASS |
| GAL-42 slug | `gallery-full`, 409, "Gallery is full", in 3 catalogs | `hairmatch/test_problems.py:51-53` `assert_problem(response, 'gallery-full', detail='Full.')`, title `'Gallery is full'`, `type` ends `/gallery-full`; `:38` `len(CATALOG) == 41`; `backend/hairmatch/problems.py:59`; app `frontend-mobile/utils/api-problem.ts:42,105` (text compared literally, `Record<ProblemSlug,string>` makes tsc enforce it); spec row in `api-problem-details/spec.md` | ✅ PASS |
| GAL-43 405 + `Allow` | `GET, HEAD, OPTIONS, POST` on the collection, `DELETE, OPTIONS` on the item | `tests.py:6996-6997` `assertEqual(sorted(response['Allow'].split(', ')), ['GET','HEAD','OPTIONS','POST'])`; `:7160-7161` `['DELETE','OPTIONS']` | ✅ PASS (deviation (a) accepted) |
| GAL-44 seed | 0 to 6 photos per hairdresser, via `image.save`, from the seed assets | `tests.py:3204` `len(counts) == 40`, `:3205` `all(0 <= count <= 6)`, `:3206` `assertGreater(sum(counts), 0)`, `:3207` `assertIn(6, counts)`, `:3208` `assertIn(0, counts)`; `:3211` key regex, `:3213` `WEBP`, `:3214` size in the two asset shapes | ✅ PASS (see precision note 2) |
| GAL-45 restore | missing key re-uploaded on the same key as WebP; a present key is left alone; stable placeholder | `tests.py:3231` `stored_image(key).format == 'WEBP'`, `:3233` row name unchanged; `:3248-3254` non-seed hairdresser not restored; `:3269` `assertEqual(stored.read(), b'already there')` and `:3271` `assertEqual(default_storage.listdir('hairdresser/gallery/77')[1], ['dddd.webp'])` (no duplicate object); `:3248` `assertEqual({key: stored_image(key).size for key in keys}, sizes)` over 12 keys restored twice | ✅ PASS (round 2) |
| GAL-47 `abc` | 404 `not-found` | `tests.py:7114` `assert_problem(response, 'not-found')`; `:7115` untouched | ✅ PASS |
| GAL-48 JSON body | 400 `validation-error`, pointer `#/image` | `tests.py:6892-6895` `assert_problem(..., errors=[{'pointer': '#/image', 'detail': 'This field is required.'}])`; `:6896` nothing stored | ✅ PASS |

App ACs (no suite by design; judged by code reading plus `npx tsc --noEmit`, 0 errors). "Needs manual UAT" because the visual and picker behavior cannot be proved by reading.

| Criterion | Spec-defined outcome | `file:line` evidence | Result |
| --------- | -------------------- | -------------------- | ------ |
| GAL-06 | profile calls the GET, "Galeria" between summary and "Técnicas", horizontal strip in API order | `customer/hairdresser-reservation/[id].tsx:30` hook, `:82-83` `<GalleryStrip photos={photos} />` right after the bio and before the `Accordion` "Técnicas"; `components/gallery/GalleryStrip.tsx:19-27` title "Galeria" + horizontal `FlatList` on `photos`; `hooks/useGalleryPhotos.ts:24-28` | ✅ PASS by reading (UAT) |
| GAL-07 | `[]` or failure hides the section, rest of profile normal | `GalleryStrip.tsx:15` `if (photos.length === 0) return null`; `useGalleryPhotos.ts:22-24` catch sets `[]`, no throw | ✅ PASS by reading (UAT) |
| GAL-08 | tap opens full screen, close button returns | `GalleryStrip.tsx:25` `onPress={() => setOpened(item)}`; `:32-46` `Modal` with `Image resizeMode="contain"` and close button `setOpened(null)` | ✅ PASS by reading (UAT) |
| GAL-20 | card "Minha galeria" opens `hairdresser/profile/gallery` | `hairdresser/profile/index.tsx:73-76` card text; `useHairdresserProfile.ts:36` `router.push('/(app)/hairdresser/profile/gallery')`; `_layout.tsx:8` | ✅ PASS by reading |
| GAL-21 | 3-column grid in API order, counter "N/30" | `gallery.tsx:11` `COLUMNS = 3`, `:72` `numColumns={COLUMNS}`, `:44-46` `{count}/{GALLERY_MAX_PHOTOS}` | ✅ PASS by reading (UAT) |
| GAL-22 | empty: "Você ainda não adicionou fotos." + "Adicionar fotos" | `gallery.tsx:75` `ListEmptyComponent`; `:56` button text | ✅ PASS by reading (UAT) |
| GAL-23 | permission, images only, multiple, `selectionLimit = 30 - N`, no crop, quality 0.5 | `useGalleryManager.ts:63` `requestMediaLibraryPermissionsAsync`, `:69` `slots = 30 - count`, `:71-76` `mediaTypes: ['images']`, `allowsMultipleSelection: true`, `selectionLimit: slots`, `quality: 0.5`; no `allowsEditing` | ✅ PASS by reading (UAT) |
| GAL-24 | denied: "Permita o acesso às fotos para adicionar fotos à galeria.", no API call | `useGalleryManager.ts:64-67` message then `return` before any service call | ✅ PASS by reading |
| GAL-25 | K POSTs, one per request, sequential, "Enviando i de K" | `useGalleryManager.ts:89-97` `for` loop with `await uploadGalleryPhoto`, `:91` `setProgress({current: index + 1, total: assets.length})`; `gallery.tsx:58-61` "Enviando {current} de {total}" | ✅ PASS by reading (UAT) |
| GAL-26 | reload by GET at the end | `useGalleryManager.ts:105` `await reload()` after the loop (also when every upload failed) | ✅ PASS by reading |
| GAL-27 | "F de K fotos não foram enviadas." + first slug message | `useGalleryManager.ts:99-100` count and first message via `problemMessage`; `:106` `` `${failures} de ${assets.length} fotos não foram enviadas. ${firstFailure}` `` | ✅ PASS by reading |
| GAL-28 | at 30: button disabled + "Limite de 30 fotos atingido." | `useGalleryManager.ts:28` `canAdd = count < 30 && !busy`; `gallery.tsx:52` `disabled={!canAdd}`, `:63` message when `full` | ✅ PASS by reading (UAT) |
| GAL-29 | busy disables add and remove, no repeat call | `useGalleryManager.ts:46-57` `runLocked` with `busyRef`; `:111` `requestRemove` guarded; `gallery.tsx:82` remove `disabled={busy}` | ✅ PASS by reading |
| GAL-30 | own profile shows the same strip | `hairdresser/profile/index.tsx:15,52` `useGalleryPhotos(hairdresser?.id)` + `<GalleryStrip>`; hook runs before the `if (!hairdresser) return null` (rules of hooks respected) | ✅ PASS by reading (UAT); deviation (b) accepted |
| GAL-35 | remove button opens "Remover esta foto da galeria?" with "Cancelar" and "Remover" | `gallery.tsx:79-87` button; `:93-100` `ConfirmationModal title="Remover esta foto da galeria?" confirmText="Remover"`; "Cancelar" is fixed text in `components/modals/confirmationModal/ConfirmationModal.tsx:36` | ✅ PASS by reading (UAT) |
| GAL-36 | on 204 drop the photo, counter updates | `useGalleryManager.ts:122-123` `await removeGalleryPhoto` then `setPhotos(filter)`; `count` derives from `photos.length` (`:27`) | ✅ PASS by reading |
| GAL-37 | 404 reloads silently | `useGalleryManager.ts:126-127` `toApiProblem(error)?.slug === 'not-found'` then `await reload()`, no message | ✅ PASS by reading |
| GAL-38 | other error: slug message, photo stays | `useGalleryManager.ts:129` `showMessage(problemMessage(...))`; the photo is only removed on success (`:123`) | ✅ PASS by reading |
| GAL-46 | gallery assets dir and commented block gone | `git diff -M 2948100..HEAD` shows the 5 jpgs as `R100 frontend-mobile/assets/hairdressers/gallery/galery[1-5].jpg -> backend/users/management/commands/seed_assets/gallery/`; `git grep galleryImages` in `frontend-mobile` finds nothing; the old block is replaced in `[id].tsx:82` | ✅ PASS |
| GAL-49 | more than `30 - N` picked: send first V, "Só cabem mais V fotos. As outras não foram enviadas." | `useGalleryManager.ts:80` `result.assets.slice(0, slots)`, `:82-84` message with `slots` | ✅ PASS by reading |
| GAL-50 | expired session follows the `axiosInstance` flow; finished uploads stay | no app code (correct): `services/axios-instance.ts:28-37,58-65` shared refresh on 401; uploads already done are server-side rows | ✅ PASS by reading |
| GAL-51 | 409 `gallery-full` during a batch counts as a failure | `useGalleryManager.ts:98-101` any thrown upload error increments `failures`; `api-problem.ts:105` supplies the gallery-full text | ✅ PASS by reading |

**Status**: ✅ All backend ACs covered and matched to the spec outcome (GAL-45 strengthened in `054a493`).

**Spec-precision notes** (not failures):

1. GAL-33 says "nessa ordem de checagem" but no test combines a customer session with a foreign id (expecting `hairdresser-required`, not `forbidden`). The order lives in the shared `authenticated_hairdresser` helper (pre-existing, tested in other features), so the risk is low.
2. GAL-44 "enviadas por `GalleryPhoto.image.save` a partir de `seed_assets/gallery/`": the test proves it through the key shape (only the model produces it) and the asset shapes; it does not look at the production `GALLERY_DIR` contents (patched to a temp dir). Acceptable.
3. GAL-42 app catalog text has no automated test (the app has no suite by design); tsc only forces the key to exist. Verified by reading `api-problem.ts:105` against the spec string.

**Judgement of the author-reported deviations**:

- (a) `Allow` includes HEAD on the GET collection (GAL-43): ACCEPTED. DRF adds HEAD to every GET view, `api_routes()` strips it (`test_routes.py:102`), the other GET routes behave the same, and the spec text was amended to say so (`spec.md` GAL-43). The `Allow` assertion is exact.
- (b) `useGalleryPhotos` reloads on focus inside the hook (T12/T17): ACCEPTED. It satisfies GAL-06 and GAL-30 (the strip reloads on every focus, covering the return from the gallery screen), keeps the profile screens free of refresh plumbing, and the hook stays before any early return.
- (c) `test_catalog_has_the_40_slugs_of_the_spec` renamed to 41: ACCEPTED and necessary. It is the only `-def test_` line in `git diff 2948100..HEAD -- backend`; the assertion moved from 40 to 41 exactly because `gallery-full` was added.
- (d) 835 executed vs 837 `def test_`: ACCEPTED, and independently reproduced. `git archive 2948100 backend` ran in a scratch gave `Ran 835 tests ... OK` (two `def test_` lines are not collected at base); the feature adds 48 `+def test_` minus the 1 rename = 47 and the suite now runs 882 = 835 + 47.

---

## Discrimination Sensor

Method: copy of `backend/` in `$SP/gal/ver/scratch` (outside the repo), one mutation at a time, the full suite (882 tests) after each one, the copy re-created from the real tree between mutants and removed at the end. `git status --porcelain` of the real tree before and after is identical (`?? .specs/LESSONS.md`, `?? .specs/lessons.json`, plus this report written afterwards).

| # | File:line | Description | Killed? (failing tests) |
| - | --------- | ----------- | ----------------------- |
| M01 | `users/views.py:917` | removed the `select_for_update` lock in POST | ✅ Killed (`GalleryPhotoRaceTest` and `test_the_hairdresser_row_is_locked_before_the_photo_is_inserted`); the race test also fails 6 of 6 repeated runs with the lock removed and passes 6 of 6 with it |
| M02 | `users/views.py:918` | `>= GALLERY_MAX_PHOTOS` to `>` | ✅ Killed (31st, 30th/next, race) |
| M03 | `users/views.py:904` | dropped the ownership check in POST | ✅ Killed (`test_the_id_of_another_hairdresser_answers_403_forbidden_and_stores_nothing`) |
| M04 | `users/views.py:941` | dropped the ownership check in DELETE | ✅ Killed (`..._answers_403_forbidden_and_deletes_nothing`) |
| M05 | `users/views.py:944` | DELETE lookup loses `hairdresser=hairdresser` (cross-owner delete) | ✅ Killed (`test_the_photo_of_another_hairdresser_under_the_own_id_answers_404_and_keeps_it`) |
| M06 | `users/views.py:951` | DELETE never removes the file | ✅ Killed (2 tests) |
| M07 | `users/views.py:951` | file removed immediately instead of `on_commit` | ✅ Killed (`tests.py:7088` file-still-there check) |
| M08 | `users/views.py:254` | removed `pictures.extend(GalleryPhoto...)` in `_delete_account_rows` | ✅ Killed (`test_a_hairdresser_account_is_deleted_with_its_gallery_rows_and_files`, 2 subtests) |
| M09 | `users/views.py:926` | removed the cleanup after a failed insert | ✅ Killed (`test_a_failed_insert_after_the_upload_deletes_the_uploaded_file`) |
| M10 | `users/views.py:911` | size check `>` to `>=` | ✅ Killed (5 MB exact boundary, `tests.py:6910`) |
| M11 | `users/models.py` ordering | `['created_at', 'id']` (ascending) | ✅ Killed (3 tests) |
| M12 | `users/models.py` ordering | tie-break `id` ascending | ✅ Killed (2 tests) |
| M13 | `users/serializers.py` | serializer exposes an extra field `hairdresser` | ✅ Killed (`:6730` and the 201 body) |
| M14 | `populate_hairdressers.py:68` | restore also covers non-seed hairdressers | ✅ Killed (`tests.py:3248`; re-run in round 2) |
| M15 | `populate_hairdressers.py:19` | seed bound 6 to 7 | ✅ Killed (`tests.py:3205`) |
| M16 | `users/views.py:911` | removed the 5 MB check | ✅ Killed |
| M17 | `users/views.py:895` | GET without the 404 for an unknown hairdresser | ✅ Killed (2 tests) |
| M18 | `users/models.py:22` | key keeps the original filename instead of the uuid | ✅ Killed (several, including the seed test) |
| M19 | `users/views.py:918` | limit counts photos of every hairdresser | ✅ Killed (`:6946`) |
| M20 | `users/views.py:897` | GET lists the photos of every hairdresser | ✅ Killed (`:6750`) |
| M21 | `populate_hairdressers.py:70` | restore drops the `default_storage.exists(key)` guard (rewrites a key that is present) | ✅ Killed in round 2 (`test_does_not_rewrite_a_gallery_photo_that_is_in_the_bucket`, the `listdir` assertion at `tests.py:3271`); round 1: ❌ survived |
| M22 | `users/views.py:952` | DELETE answers 200 | ✅ Killed |
| M23 | `users/views.py:931` | POST answers 200 | ✅ Killed |
| M24 | `users/views.py:919` | a full gallery raises the wrong slug | ✅ Killed |
| M25 | `users/views.py:928` | `InvalidImage` not handled in POST | ✅ Killed |
| M26 | `populate_hairdressers.py` (`handle`) | `restore_missing_gallery_photos()` not called on boot | ✅ Killed (re-run in round 2) |
| M27 | `populate_hairdressers.py:72` | stable `crc32(key)` choice replaced by `random.choice(files)` | ✅ Killed 6 of 6 runs in round 2 (`test_a_missing_gallery_photo_gets_the_same_placeholder_every_time`, 12 keys); round 1: ⚠️ 3 of 5 |
| M28 | `users/views.py:950` | DELETE does not delete the row | ✅ Killed |
| M29 | `users/views.py:946` | DELETE of a missing photo answers 204 | ✅ Killed |
| M30 | `users/views.py:909` | wrong pointer (`photo`) for a missing image | ✅ Killed |

**Why M21 mattered** (round 1): with the guard removed the command saves the placeholder under an alternative name, because the key is taken, so the original bytes survive while a duplicate object is created. The fixed test lists the directory and expects only `dddd.webp`.

**Sensor depth**: P0-full (data integrity, auth and concurrency), 30 manual mutations; round 2 re-ran M14, M21, M26 and M27 (6x) against `054a493`.
**Sensor outcome**: 30 of 30 killed, 0 survived - PASS ✅

---

## Interactive UAT Results

The T18 manual UAT on web and Android is PENDING and was NOT done. The user forbade Claude in Chrome and Android depends on it. In its place, the author ran an API E2E against a worktree server with MiniStack (Cognito) and a LocalStack bucket. I did not rerun it (the server container is shared); I read the outputs as supporting evidence only:

- `$SP/gal/e2e_output.txt`: `56 passed, 0 failed` (all of RT-94 to RT-96, error paths, limit, 6 parallel POSTs with 2 places left giving exactly two 201 and four 409, ownership, account deletion with bucket key checks).
- `$SP/gal/e2e_seed_output.txt`: seed creates the photos, then `Restored 3 seeded gallery photos to the media bucket.` and the restored keys are the same, WebP, with unchanged rows (GAL-44, GAL-45).
- `$SP/gal/curl_smoke_output.txt`: curl smoke of the routes.

| # | Test | Result | Details |
| - | ---- | ------ | ------- |
| 1 | Hairdresser adds several photos, counter, 30 limit, removal (web) | ⏭️ Skip | PENDING manual UAT |
| 2 | Customer sees the strip and opens a photo full screen (web) | ⏭️ Skip | PENDING manual UAT |
| 3 | Same flows on Android (`selectionLimit` honored) | ⏭️ Skip | PENDING manual UAT |

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ Model + 2 views + 1 serializer + 1 command function; no extra abstraction. `IMAGE_UPLOAD_MAX_SIZE` is a rename of `PROFILE_PICTURE_MAX_SIZE` that the spec asks for ("um limite só para as duas rotas"), covered by the unchanged profile-picture tests. |
| Surgical changes | ✅ Backend touched files are all in the feature surface; assets moved with `R100` renames. Observation: the planning commit `9af4add` also carries `.specs/features/review-editing/{spec,design,tasks}.md` (#105), unrelated to #118; harmless, but it will appear in this PR's diff. |
| No scope creep | ✅ No throttle, pagination, reordering or captions (all Out of Scope). Unused local `session` in the two views is trivial. |
| Matches patterns | ✅ `authenticated_hairdresser`/`forbidden`, `validation_problem`/`body_error`, `_delete_stored_files` on commit, `select_for_update` as in AD-010, service + hook + screen layering of #120. |
| Spec-anchored outcome check (asserted values match spec) | ✅ for 37 backend criteria; ⚠️ GAL-45 (M21/M27) |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy + edge + error) | ✅ Every route in RT-94..96 has happy, 401/403/404/405 and edge tests. |
| Every test maps to a spec requirement, no unclaimed tests | ✅ 47 new tests; 45 carry a `GAL-` tag in their docstring. The two untagged ones (`test_two_photos_never_share_a_key` `tests.py:6679`, `test_deleting_the_hairdresser_deletes_the_rows` `:6698`) back GAL-05 (uuid key) and AD-013 (CASCADE, needed by GAL-39); acceptable. |
| No skipped or deleted tests | ✅ `git diff 2948100..HEAD -- backend \| grep '^-.*def test_'` prints only the renamed catalog-size test; 0 skipped in the run. |
| Documented guidelines followed | none - strong defaults applied (tasks.md Test Coverage Matrix: no `AGENTS.md` or `CONTRIBUTING.md`; CI runs `coverage run manage.py test` without a threshold) |

---

## Edge Cases

- [x] GAL-47 `/gallery-photos/abc` answers 404 `not-found`: `tests.py:7114` `assert_problem(response, 'not-found')`.
- [x] GAL-48 JSON body answers 400 `validation-error` `#/image`: `tests.py:6892`.
- [x] GAL-49 picker returns more than `30 - N`: `useGalleryManager.ts:80-84` (slice + message); web ignores `selectionLimit`, hence the slice (Needs manual UAT on web).
- [x] GAL-50 session expiry mid-batch: `services/axios-instance.ts:28-65` (shared refresh, then login); finished uploads are server rows.
- [x] GAL-51 batch loses the race: `useGalleryManager.ts:98-101` counts the 409 as a failure; backend side proved by the race test `tests.py:7054`.

---

## Gate Check

- **Gate command**: Full backend gate against the worktree (read-only mount, DB `hairmatch_wt_gallery_verifier`): `python manage.py makemigrations --check --dry-run && coverage run manage.py test --noinput && coverage report -m`, plus App gate `cd frontend-mobile && npx tsc --noEmit`.
- **Result**: 882 passed, 0 failed, 0 errors, 0 skipped (`Ran 882 tests in 10.7s`, `OK`, round 2 at `054a493`; round 1 gave the same counts); `makemigrations`: `No changes detected`; `tsc`: exit 0, no output.
- **Test count before feature**: 835 executed (reproduced by running `git archive 2948100` in a scratch: `Ran 835 tests ... OK`; 837 `def test_` lines).
- **Test count after feature**: 882. **Delta**: +47 new tests (48 added, 1 renamed).
- **Skipped tests**: none.
- **Failures**: none.
- **Coverage of the touched files** (whole suite): `hairmatch/problems.py` 100%; `users/models.py` 98% (miss `:57`, pre-existing); `users/serializers.py` 99% (miss `:107`, pre-existing raise); `users/views.py` 99% (miss `140-141, 302-303`, pre-existing, no gallery line missed); `users/management/commands/populate_hairdressers.py` 92% (missing `63, 66` are the new defensive early returns of `restore_missing_gallery_photos`, the rest `96-98, 107-108, 242-243, 354-355` pre-existing); `users/migrations/0014_galleryphoto.py` 100%. Project total 98% (11043 statements, 170 missed). Unchanged between the rounds.

---

## Fix Plans

### Fix 1: M21 - the GAL-45 "present key is not rewritten" test could not see a duplicate upload (Minor) - RESOLVED in `054a493`

- **Root cause**: the test only read the original key back; a rewrite lands on an alternative name, so it stayed green with the `exists` guard removed.
- **Fix**: the test now uses its own directory (`hairdresser/gallery/77/`, because the in-memory storage is shared by the tests of the process) and asserts `default_storage.listdir('hairdresser/gallery/77')[1] == ['dddd.webp']` (`backend/users/tests.py:3271`). Test-only.
- **Re-verification**: M21 killed; gate 882 OK.

### Fix 2: M27 - the "same placeholder every time" test was a coin flip (Minor) - RESOLVED in `054a493`

- **Root cause**: one key and two assets, so a random pick agreed by chance about half of the time.
- **Fix**: 12 keys restored twice, the full key-to-size mapping compared (`backend/users/tests.py:3235-3250`). Test-only.
- **Re-verification**: M27 killed in 6 of 6 runs (chance of a random pick surviving 12 keys with 2 assets is about 1 in 4096).

**Residual note (not a gap)**: the fixed `does_not_rewrite` test keys its photo under `hairdresser/gallery/77/` and the in-memory storage is not cleared between tests; a later test whose hairdresser gets primary key 77 and lists its directory would see `dddd.webp`. The sequences are deterministic and the full suite passes, but a fixture-level cleanup would remove the coupling.

---

## API End-to-End Evidence (author-run, replaces the browser UAT)

The user forbade Claude in Chrome, so the T18 roteiro could not run in a browser. In its place the author ran the real API against a server container of this worktree (`runserver` on :8018, database `hairmatch_wt_gallery_e2e`), MiniStack (Cognito: real register, admin confirm, login) and a LocalStack bucket `wt-gallery-e2e`. Everything was removed afterwards (server container, database, bucket, Cognito test users). Scripts and outputs are outside the repo, in the session scratchpad `.../scratchpad/gal/`:

| Script | Output | What it proved |
| ------ | ------ | -------------- |
| `e2e_gallery.py` (runs in a throwaway container) | `e2e_output.txt`: 56 passed, 0 failed | GET/POST/DELETE (RT-94 to RT-96): empty list, 404 for unknown and customer ids, anonymous GET, every POST error (401, 403 customer, 403 other id, missing field, JSON body, 5 MB + 1 byte, text renamed .jpg) leaving no row and no object; a 2000x1500 PNG stored as one `hairdresser/gallery/<id>/<32 hex>.webp` object (RIFF/WEBP, longest side 1080, content type image/webp, original name absent, public URL serves the WebP); newest-first order; 30 sequential photos then 409 `gallery-full` with 30 rows / 30 objects; DELETE 204 removing row and object, repeat 404, cross-owner 404/403, 401, customer 403, unknown and `abc` ids 404; 405 `Allow` for PUT on the collection and GET/PATCH on the item; 6 parallel POSTs with 2 places left giving exactly two 201 and four 409 and 30 rows = 30 objects; account deletion of a hairdresser with 30 photos (204, rows and objects gone, the other hairdresser untouched) |
| `run_seed.sh` + `e2e_seed.py` | `e2e_seed_output.txt` | GAL-44: 40 seeded hairdressers with 0 to 6 photos each (117 photos, every object WebP at its key); GAL-45: 3 objects deleted from the bucket, the next command run printed "Restored 3 seeded gallery photos" and the same keys were back as WebP |
| `curl_smoke.sh` | `curl_smoke_output.txt` | The same routes by hand with curl on :8018: anonymous GET, 401, 405 `Allow`, 201 with multipart `-F image=@...`, HEAD on the public URL (200 image/webp), 400 invalid-image, 403, 204, object gone (404), second DELETE 404, account deletion |

Not covered by the E2E (covered by unit tests only): a failing S3 (GAL-19, GAL-34) and a rolled-back account deletion (GAL-40).

Typed routes: `.expo/types/router.d.ts` was regenerated with `npx expo start --port 8090` (stopped after 45 s), it contains `/(app)/hairdresser/profile/gallery`, and `npx tsc --noEmit` still exits 0, so the gate was not hollow.

**Manual UAT on web and Android: PENDING, not done.** The roteiro items that depend on the screens (1 to 5, and 7 in the app) remain with the user.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| GAL-01 to GAL-05 | Implementing | ✅ Verified |
| GAL-06, GAL-07, GAL-08 | Implementing | Needs manual UAT |
| GAL-09 to GAL-19 | Implementing | ✅ Verified |
| GAL-20 | Implementing | Needs manual UAT (code read; link is a one-line card) |
| GAL-21 to GAL-30 | Implementing | Needs manual UAT |
| GAL-31 to GAL-34 | Implementing | ✅ Verified |
| GAL-35 to GAL-38 | Implementing | Needs manual UAT |
| GAL-39, GAL-40 | Implementing | ✅ Verified |
| GAL-41, GAL-42, GAL-43 | Implementing | ✅ Verified (GAL-42 app text verified by reading) |
| GAL-44, GAL-45 | Implementing | ✅ Verified |
| GAL-46 | Implementing | ✅ Verified |
| GAL-47, GAL-48 | Implementing | ✅ Verified |
| GAL-49, GAL-50, GAL-51 | Implementing | Needs manual UAT |

---

## Summary

**Overall**: ✅ Ready (backend and code-level app checks); the manual UAT (T18) remains PENDING

**Spec-anchored check**: 38 of 38 backend ACs matched the spec outcome; 3 spec-precision notes
**Sensor**: 30 of 30 mutations killed
**Gate**: 882 passed, 0 failed; tsc 0 errors; coverage of touched files 92% to 100%

**What works**: the whole backend contract (routes, statuses, problem types, ownership, ordering, 5 MB boundary, 30-photo limit under real concurrency, after-commit file deletion, account deletion lifecycle, seed and its restore); the app code matches the spec texts and behavior literally and compiles.

**Issues found**: none open. Round-1 gaps (M21, M27) are resolved by `054a493`.

**Next steps**: run the pending T18 manual UAT on web and Android; the "Needs manual UAT" ACs become Verified after it.
