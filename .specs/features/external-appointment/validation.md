# External Appointment Validation

**Result**: PASS (round 2). All backend ACs (EXT-01 to EXT-19) have tests that match the spec outcome, every non-equivalent mutant is killed, and the gates are green. The app ACs (EXT-20 to EXT-34) are verified by code inspection only and stay pending the user's manual UAT (T13).

**Date**: 2026-10-09
**Spec**: `.specs/features/external-appointment/spec.md` (issue #113)
**Diff range**: `develop..HEAD` = `fbf1d08..2d5fb0e` (spec commit `e49c001`, feature commits `0483923` to `ce2b1e2`, validation fixes `ed6d187` to `2d5fb0e`)
**Verifier**: independent sub-agent (author is not the verifier), evidence-or-zero, read-only over the real worktree

---

## Round History

| Round | HEAD | Verdict | Gaps raised | Closed by |
| ----- | ---- | ------- | ----------- | --------- |
| 1 | `ce2b1e2` | Not ready (verdict FAIL) | G1: EXT-09 "start equal to now is accepted" untested, mutant M3 (`<` to `<=`) survived. G2: EXT-05 `title: null` unspecified (spec-precision). G3: EXT-31 `Alert.alert` is a no-op on react-native-web (code inspection). G4: EXT-25 end time filled only on blur (UAT risk). Nit: `tasks.md:13` status text was stale | - |
| 2 | `2d5fb0e` | Ready (verdict PASS, UAT pending) | none blocking; 2 minor notes (see Notes) | G1 `ed6d187`, G2 `2a86a10`, G3 `42977be`, G4 `86a2577`, nit `ed6d187`/`2d5fb0e` |

Round-2 re-check of each fix:
- **G1 (EXT-09)**: `backend/agenda/tests.py:471-480` freezes `agenda.views.timezone.now` at `manaus_in_utc(day, 10)` and posts a naive `10:00` start. It asserts 201, `count == 2` and `start_time == frozen_now`. It kills M3 (see the sensor).
- **G2 (EXT-05)**: the spec was amended at `spec.md:89`: `null` counts as absent; without a service it falls into EXT-04, and with a service it is stored as `""`. `backend/agenda/tests.py:397-411` pins both halves. It kills M19, M20 and M21.
- **G3 (EXT-31)**:
  - On web, `useExternalAppointmentForm.ts:150-151` shows `window.alert('Sucesso!\nAtendimento externo registrado.')`.
  - Elsewhere (Android), `useExternalAppointmentForm.ts:153` keeps `Alert.alert('Sucesso!', 'Atendimento externo registrado.')`.
  - Both paths then call `router.back()` (`:155`).
  - `tsc` passes, and so does eslint (0 problems on the hook).
- **G4 (EXT-25)**:
  - The end time is now filled as soon as the start is complete (`:106-110` calls `fillEndTime(value, serviceId)` on every change).
  - A start counts as complete only as a valid HH:mm or as four digits (`completeTime`, `:36-40`).
  - Past 23:59 the end field is cleared (`:97`). It is no longer left stale.
  - On Save, a field that still has focus is read the same way (`:130-131`), so tapping "Salvar" without leaving the field works.
  - These keep the spec rule "a change of the service or of the start fills end = start + duration, and the end stays editable".

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 | Done (`0483923`) | Model + migration `0002`. `makemigrations --check` is clean |
| T2 | Done (`77dfb21`, + `ed6d187`, `2a86a10`) | `CreateAgenda` validation + optional service; round-2 boundary/null tests |
| T3 | Done (`48ffff8`) | Listing with `title`; external block never paired. The code guards are equivalent mutants (M15) |
| T4 | Done (`fe9c88b`) | `ExternalBlockTest` (EXT-15 to EXT-17) |
| T5-T11 | Done (`0b28a2e` to `8ce9298`, + `42977be`, `86a2577`) | App: types, service, stack, form hook, screen, focus refresh, "+", "Externo" |
| T12 | Done (`ce2b1e2`, + `2d5fb0e`) | AD-009 at `.specs/STATE.md:88`; Handoff refreshed |
| T13 | Open (by design) | Manual UAT on web and Android, run by the user. EXT-20 to EXT-34 stay "pending UAT" |

---

## Spec-Anchored Acceptance Criteria

Paths:
- `agenda/tests.py` = `backend/agenda/tests.py`
- `reserve/tests.py` = `backend/reserve/tests.py`
- `views.py` = `backend/agenda/views.py`
- `form hook` = `frontend-mobile/hooks/hairdresserHooks/useExternalAppointmentForm.ts`

`assert_problem` (`backend/hairmatch/problem_testing.py:10`) checks the exact status, Content-Type, slug and title. When given, it also checks the exact `detail` and the exact `errors` list.

### P1: Register a block through the API

| Criterion | Spec-defined outcome | `file:line` + assertion | Verdict |
| --------- | -------------------- | ----------------------- | ------- |
| EXT-01 | 201 + exact body; one row: service null, trimmed title, Manaus times, session hairdresser | `agenda/tests.py:347-355`: status 201, `response.json() == {'message': 'Agenda register created successfully'}`, `count == 2`, `assertIsNone(created.service_id)`, `created.title == 'Cliente do WhatsApp'` (sent with spaces), `start_time == manaus_in_utc(day,10)`, `end_time == manaus_in_utc(day,11)`, `created.hairdresser == self.hairdresser` | PASS |
| EXT-02 | `end = start + duration`; title trimmed or `""` | `agenda/tests.py:363-367` (subTests without a title and with `' Maria '`): `created.service == self.service`, `end_time == start + 60 min`, `created.title == stored_title` | PASS |
| EXT-03 | sent end_time stored | `agenda/tests.py:376-379`: 201, `created.end_time == manaus_in_utc(day,10,45)` | PASS |
| EXT-04 | 400, exactly `[#/title "This field is required."]`, no row | `agenda/tests.py:381-387` (absent, `''`, `'   '`) via `assert_refused` (`agenda/tests.py:340-341`: exact `errors` + `count == 1`). Other side of the conjunction (with a service, no title gives 201): `agenda/tests.py:363` | PASS |
| EXT-05 (amended `spec.md:89`) | non-string: 400 `#/title "This field must be a string."`; `null` counts as absent (EXT-04 without a service, `""` with one) | `agenda/tests.py:389-395` (`123`, `['x']`); `agenda/tests.py:397-411`: null without a service gives `assert_refused('#/title', 'This field is required.')`; null with a service gives 201, `count == 2`, `created.service == self.service`, `created.title == ''` | PASS |
| EXT-06 | >100 gives 400 with the exact detail; exactly 100 accepted | `agenda/tests.py:417` (101 refused); `agenda/tests.py:419-427` (100, and 100 + spaces, give 201 and `created.title == title.strip()`) | PASS |
| EXT-07 | 400 exactly `[#/end_time "This field is required."]` | `agenda/tests.py:429-433` | PASS |
| EXT-08 | 400 `#/end_time "The end time must be after the start time."`, no row | `agenda/tests.py:435-446` (equal, 1 min before, equal with a service) | PASS |
| EXT-09 | before now gives 400 `#/start_time "The start time must not be in the past."`, no row; equal to now accepted | `agenda/tests.py:448-457` (now - 1 min refused); `agenda/tests.py:459-469` (now + 1 min gives 201); `agenda/tests.py:471-480` (frozen `timezone.now`, start == now gives 201, `start_time == frozen_now`) | PASS |
| EXT-10 | 409 `agenda-overlap` both ways, no row; touching accepted | `agenda/tests.py:491-492`, `:503-504` (exact detail, counts unchanged); `agenda/tests.py:514-515` (touching gives 201) | PASS |
| EXT-11 | foreign service gives 403 `forbidden`; missing gives 404 `not-found` | `agenda/tests.py:175` + no row; `agenda/tests.py:209-210`, `:281` (`detail='Service not found.'`) | PASS |
| EXT-12 | 401 `invalid-session`; customer gives 403 `hairdresser-required` | `agenda/tests.py:188-189`; `agenda/tests.py:293` (exact detail) | PASS |
| EXT-13 | 201 outside availability / after closing / in break | `agenda/tests.py:517-537` (3 subTests; 201 + `assertIsNone(created.service_id)`) | PASS |
| EXT-14 | exactly `[start_time, end_time, title]` "This field is required." in order | `agenda/tests.py:247-252` (exact list equality pins the order; `count == 1`) | PASS |

### P1: The blocked slot is no longer offered

| Criterion | Spec-defined outcome | `file:line` + assertion | Verdict |
| --------- | -------------------- | ----------------------- | ------- |
| EXT-15 | 09:30/10:00/10:30 absent; 09:00/11:00 present | `reserve/tests.py:757-761` (block created through `POST /api/agenda`, 201 at `:740`): `assert_offer(offered=('09:00','11:00'), left_out=('09:30','10:00','10:30'))`; serviced block with an edited end: `reserve/tests.py:763-769` | PASS |
| EXT-16 | chatbot path omits the same slots | `reserve/tests.py:777-778` (same lists + equality with the view) | PASS |
| EXT-17 | 409 `slot-unavailable`; no Reserve nor Agenda | `reserve/tests.py:792-796` | PASS |

### P1: See the block in the agenda

| Criterion | Spec-defined outcome | `file:line` + assertion | Verdict |
| --------- | -------------------- | ----------------------- | ------- |
| EXT-18 | both routes; exact key set; block has service/customer null and its title | `agenda/tests.py:609-624`: `set(item) == ITEM_KEYS`, `service is None`, `customer is None`, `title == 'Cliente do WhatsApp'`; serviced row has the nested service and `title == ''` | PASS |
| EXT-19 | block item has `customer: null` despite a Reserve with the same start | `agenda/tests.py:627-635`; regression `agenda/tests.py:637-649` (a serviced block keeps its exact customer dict) | PASS |

### App ACs (no automated tests by project decision; code inspection, pending UAT T13)

| Criterion | Code evidence (`frontend-mobile/…`) | Verdict |
| --------- | ----------------------------------- | ------- |
| EXT-20 | `hooks/hairdresserHooks/useAgenda.ts:39` `title: ev.title \|\| ev.service?.name \|\| ''`; no other unguarded `.service.` access in the agenda screens | Code OK, pending UAT |
| EXT-21 | `useAgenda.ts:42` `isExternal: ev.customer === null`; `app/(app)/hairdresser/agenda/index.tsx:32` inside `AgendaListView` (rendered only in "Agenda" mode, `index.tsx:118-119`) | Code OK, pending UAT |
| EXT-22 | `useAgenda.ts:27` `useFocusEffect(useCallback(…, [hairdresserId]))` | Code OK, pending UAT |
| EXT-23 | `index.tsx:139` "+" button outside the mode conditional; `useAgenda.ts:70`; form hook `:69-74` (today, empty times, `serviceId` null, empty title) | Code OK, pending UAT |
| EXT-24 | `app/(app)/hairdresser/agenda/create.tsx:55` `minDate={today}`; `:70-88` HH:mm fields; `:33-39` "Sem serviço" + service chips (`services/service.service.ts:12`); `:111` `maxLength={100}` | Code OK, pending UAT |
| EXT-25 | form hook `:100-103` (service change), `:106-110` (start change, fills once complete), `:36-40` (`completeTime`), `:97` (cleared past 23:59); end stays editable (`create.tsx:86`) | Code OK, pending UAT |
| EXT-26..29 | form hook `:45`, `:49`, `:53`, `:56`; early return `:133-136` before any request | Code OK, pending UAT |
| EXT-30 | form hook `:138-143` (`YYYY-MM-DDTHH:mm:00`, `title.trim()`, `service` only when selected); ref lock `:127`/`:145`; `create.tsx:123` `disabled={isSaving}` | Code OK, pending UAT |
| EXT-31 | form hook `:150-155` (web: `window.alert` with title and message; native: `Alert.alert('Sucesso!', 'Atendimento externo registrado.')`; then `router.back()`) | Code OK, pending UAT |
| EXT-32 | form hook `:156-160` `problemMessage(error, 'Não foi possível registrar o atendimento externo.')`; `agenda-overlap` maps to "Este horário se sobrepõe a outro compromisso." (`utils/api-problem.ts:96`); the service rethrows (`services/agenda.service.ts:31`); no navigation on error | Code OK, pending UAT |
| EXT-33 (P2) | `useAgenda.ts:57-69` (push with `date`/`time`); form hook `:70-71` | Code OK, pending UAT |
| EXT-34 (P2) | `useAgenda.ts:58-62` | Code OK, pending UAT |

**Status**: all 19 backend ACs match the spec-defined outcome. No spec-precision gaps remain open (EXT-05 was amended and is pinned). All 15 app ACs have code evidence and are pending UAT.

---

## Discrimination Sensor (round 2)

Scratch: a fresh `git worktree add --detach …/scratchpad/sensor-113 HEAD` at `2d5fb0e`. Tests: `agenda reserve` on DB `hairmatch_wt113v`. The unmutated scratch baseline was 92 OK. For each mutant, the target string was checked to occur exactly once, the scratch diff was printed, and the file was reverted before the next mutant. All round-1 mutants were re-run, and 3 were added for the new EXT-05 behavior.

| # | File:line | Description | Killed? (killing tests) |
| - | --------- | ----------- | ----------------------- |
| M1 | `views.py:54` | EXT-08 boundary `end <= start` to `<` | Killed (3: `end_time_not_after_the_start` subTests) |
| M2 | `views.py:48` | EXT-09 past check removed | Killed (`start_time_in_the_past_is_refused`) |
| M3 | `views.py:48` | EXT-09 boundary `start < now` to `<=` | **Killed** (`test_a_start_time_equal_to_now_is_accepted`). It survived in round 1 |
| M4 | `views.py:79-80` | EXT-11 ownership check removed | Killed (`…service_of_another_hairdresser_is_refused_with_403`) |
| M5 | `views.py:68` | EXT-04/14 title not required without a service | Killed (6, including the null-title subTest and `reports_every_missing_field`) |
| M6 | `views.py:68` | title required even with a service | Killed (19) |
| M7 | `views.py:65` | title not stripped | Killed (4) |
| M8 | `views.py:66` | EXT-06 boundary `> 100` to `>= 100` | Killed (2) |
| M9 | `views.py:56-57` | EXT-07 end not required without a service | Killed (2) |
| M10 | `views.py:96` | EXT-10 overlap skipped | Killed (4) |
| M11 | `views.py:93` | EXT-10 boundary `end_time__gt` to `__gte` | Killed (`starts_when_another_ends_is_accepted`) |
| M12 | `views.py:83-84` | EXT-03 sent end ignored with a service | Killed (3) |
| M13 | `backend/agenda/serializers.py:30` | EXT-18 `title` dropped from fields | Killed (2 routes) |
| M14 | `views.py:123-137` + `serializers.py:37-42` | EXT-19 regression: pairing by start_time only | Killed (`reserve_at_the_start_of_an_external_block_is_not_its_customer`) |
| M15 | `views.py:125` + `serializers.py:37-38` | T3 guards removed | Survived: **equivalent**. `Reserve.service` is NOT NULL (`backend/reserve/models.py:12`), so a `(None, start)` key can never match |
| M16 | `backend/reserve/views.py:224` | EXT-15 slots view ignores blocks without a service | Killed (2) |
| M17 | `backend/reserve/views.py:349` | EXT-16 chatbot slots ignore blocks without a service | Killed (`chatbot_slots_leave_out_the_block_too`) |
| M18 | `backend/reserve/views.py:117` | EXT-17 `CreateReserve` overlap ignores blocks without a service | Killed (`booking_inside_a_block_without_a_service_answers_409`) |
| M19 | `views.py:59-61` | EXT-05: the null-to-absent fallback removed (a missing title also becomes a "not a string" error) | Killed (22, including both `null_title` subTests) |
| M20 | `views.py:59-61` | EXT-05: a null title with a service stored as `'None'` | Killed (7, including both `null_title` subTests) |
| M21 | `views.py:58-61` | EXT-05, sharp version: only an explicit `null` is refused as not a string (`data.get('title', '')`) | Killed (exactly the 2 `null_title` subTests) |

**Sensor depth**: expanded (21 behavior-level mutations: every new `CreateAgenda` branch and boundary, the listing, and each of the 3 reserve-side Agenda queries).
**Sensor outcome**: 20 killed, 1 equivalent (M15), 0 survived.
**Isolation**:
- Before the sensor, the real worktree's `git status --porcelain` was `?? .specs/LESSONS.md`, `?? .specs/features/external-appointment/validation.md`, `?? .specs/lessons.json` and `?? frontend-mobile/eslint.config.js`.
- After `git worktree remove --force` it was identical (compared with `diff`).
- The scratch is no longer listed in `git worktree list`.

App code (EXT-20 to EXT-34) has no test harness by project decision, so no app mutants were run.

---

## Interactive UAT Results

Not performed by the Verifier. T13 belongs to the user (web + Android). Suggested focus points:
1. EXT-31 on web: the browser alert reads "Sucesso!" and then "Atendimento externo registrado.", and the app returns to the agenda.
2. EXT-25 on Android: pick a service, type a start on the numeric keyboard (`1000`), then tap "Salvar" right away. The end should already be 11:00, and the block should save.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | OK. The round-2 fixes are local: 2 tests, one `Platform` branch, and one `completeTime` helper. The T3 guards are defensive but equivalent (M15) |
| Surgical changes | OK. Only the hook, the tests and the docs changed in round 2 |
| No scope creep | OK |
| Matches patterns | OK. `mock.patch` on the view's clock; `formatTimeInput` reused for the four-digit case |
| Spec-anchored outcome check | OK for all 19 backend ACs |
| Per-layer Coverage Expectation (routes: happy + edge + error) | Met |
| Every test maps to a spec requirement | OK. The 24 new tests cite an EXT id; the EXT-19 regression test maps to the T3 Done-when |
| Documented guidelines followed | None found (no AGENTS.md/CONTRIBUTING.md). Strong defaults and the `tasks.md` Test Coverage Matrix were applied |

---

## Edge Cases

- [x] Title with surrounding spaces is stored trimmed: `agenda/tests.py:352`, `:367`, `:427`
- [x] A block ending exactly when another starts is accepted: `agenda/tests.py:506-515`
- [x] Off-grid end: the existing jump behavior is unchanged (`backend/reserve/views.py` is not in the diff); an edited end removes slots up to that end (`reserve/tests.py:763-769`)
- [ ] No services registered: only "Sem serviço" is shown (`create.tsx:33-39`). Code OK, pending UAT
- [ ] Services fail to load: the form still saves with a title (form hook `:86-88`). Code OK, pending UAT
- [x] (extra) Cancelling a reserve never deletes an external block: `cancel_reserve` filters by `service_id` (`backend/reserve/views.py:35-39`)

---

## Gate Check

- **Gate command (Build)**: Full = `python manage.py test --noinput && python manage.py makemigrations --check --dry-run` (isolated container on worktree 113), plus `npx tsc --noEmit`, plus eslint on the changed app files
- **Backend**: `Ran 746 tests`, `OK` (EXIT=0); `makemigrations --check` gave "No changes detected" (exit 0)
- **App**: `tsc --noEmit` exit 0. Eslint on `useExternalAppointmentForm.ts` gave 0 problems. Round 1 linted all 9 changed files: 0 errors and 5 warnings, all on lines that already existed
- **Test count before feature**: 722 (`agenda` + `reserve`: 68)
- **Test count after feature**: 746 (`agenda` + `reserve`: 92)
- **Delta**: +24 (20 in `agenda/tests.py`, 4 in `reserve/tests.py`). No removals. The one intentionally rewritten test is `test_create_agenda_reports_every_missing_field` (EXT-14), and it is stricter than before
- **Skipped tests**: none
- **Failures**: none

---

## Notes (non-blocking)

1. `completeTime` reads any four digits through `formatTimeInput`, which clamps values (form hook `:36-40`; `frontend-mobile/utils/forms.ts:64-74`). A typo such as `2599` silently becomes `23:59`, the same as the existing blur formatting. This is UX only, and the spec does not define it.
2. The EXT-05 amendment (`spec.md:89`) was made by the author to close a spec-precision gap. It matches the existing code and the app never sends `null`. The user should be aware of it as a contract clarification.

---

## Requirement Traceability Update (proposed; spec.md was left untouched by the Verifier)

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| EXT-01 to EXT-19 | Implementing | Verified |
| EXT-20 to EXT-34 | Implementing | Implemented, pending UAT (T13) |

---

## Summary

**Overall**: Ready on the automated side. The backend and contract are verified. The app behavior awaits the user's T13 UAT.

**Spec-anchored check**: 19/19 backend ACs match the spec outcome; 0 open spec-precision gaps; 15/15 app ACs have code evidence (pending UAT).
**Sensor**: 21 mutations: 20 killed, 1 equivalent, 0 survived.
**Gate**: 746 passed, 0 failed, 0 skipped; migrations clean; tsc 0; eslint 0 errors.

**What works**:
- **Create**: the service is optional; a block without one needs a title, which is trimmed, limited to 100 characters, and may be `null` (read as absent).
- **Time rules**: the end must be after the start, and a start in the past is refused, with the start-equal-to-now boundary pinned.
- **Overlap**: refused in both directions; touching blocks are accepted.
- **Listing**: both routes return `title`, with `service`/`customer` null for an external block.
- **Slot offer**: the block is left out of both the app and chatbot slot lists, and a booking over it is refused with 409.
- **App**: the "+" button, cell press, refresh on focus, the "Externo" label, the end time filled live, and a success alert on web and native.

**Next steps**: the user runs the T13 UAT (focus points above), then marks EXT-20 to EXT-34 Verified. Commit this report.
