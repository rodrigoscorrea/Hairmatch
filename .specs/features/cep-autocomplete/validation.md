# CEP Autocomplete Validation

**Date**: 2026-09-29
**Spec**: `.specs/features/cep-autocomplete/spec.md`
## Validation: FAIL

**Diff range**: `297f6d7..HEAD` (HEAD e008817, branch 128-preencher-endereco-via-cep)
**Verifier**: independent sub-agent (author != verifier)

**Verdict: FAIL** (two fix tasks: a frontend defect and a surviving mutant). Backend ACs CEP-01..CEP-11 are covered and match the spec outcomes.

## Gate

- `cd backend && manage.py test users`: 133 run, 133 OK, 0 failed.
- `cd frontend-mobile && npx tsc --noEmit | grep -c "error TS"`: 4 (limit 4), OK.
- Live curl (reported by author, not re-run by the Verifier): 69057-000 -> 200, 78175-000 -> 200 with empty street/neighborhood, 123 -> 400, 00000000 -> 404, 429 after 30 requests.

## Spec-Anchored ACs, backend (tests in `backend/users/tests.py`, impl in `backend/users/cep_lookup.py` and `views.py`)

| AC | Spec-defined outcome | file:line + assertion | Result |
| -- | -------------------- | --------------------- | ------ |
| CEP-01 | 200, exactly 5 keys, postal_code 8 digits | tests.py:2391-2393 `assertEqual(lookup_cep('69057-000'), EXPECTED)`; :2517-2521 view 200 `response.json() == ADDRESS`; keys :2395-2400 | PASS |
| CEP-02 | 400 `CEP inválido. Informe 8 dígitos.`, no provider call | tests.py:2402-2407 (`'123','123456789',''` raise InvalidCep, `mock_get.assert_not_called()`); :2524-2528 status 400 + exact body | PASS |
| CEP-03 | Fallback to BrasilAPI on timeout/conn/non-200/bad JSON/erro | tests.py:2409-2431 (6 tests, `call_count == 2`, url contains brasilapi, result == EXPECTED) | PASS with weak spot (see sensor mutant 15) |
| CEP-04 | 404 `CEP não encontrado.` when none finds and one says not-found | tests.py:2433-2441 (`assertRaises(CepNotFound)`, both erro+404 and timeout+404); :2530-2534 404 + exact body | PASS |
| CEP-05 | 503 exact message when both fail | tests.py:2443-2446 `CepServiceUnavailable`; :2536-2543 503 + exact body | PASS |
| CEP-06 | `timeout=3` on every call | tests.py:2448-2453 `assertEqual(call.kwargs['timeout'], 3)` for both calls | PASS |
| CEP-07 | null/absent -> "", never `complemento` or extra keys | tests.py:2455-2460 (null -> ''), :2462-2468 (city-wide exact dict), :2395-2400 (fixture has `complemento`, keys == 5) | PASS |
| CEP-08 | cache key `cep:<8 digits>`, 86400 s, second call no provider | tests.py:2470-2477 `spy_set.assert_called_once_with('cep:69057000', EXPECTED, 86400)`, `mock_get.assert_not_called()` | PASS |
| CEP-09 | no `jwt` cookie needed | tests.py:2517-2522 (APIClient, no cookie, 200). Impl views.py:260-266 sets only throttle_classes | PASS |
| CEP-10 | 429 after 30 per 60 s | tests.py:2545-2549 30x200 then `assertEqual(..., 429)` | PASS |
| CEP-11 | `logger.warning` with `viacep` / `brasilapi` and reason | tests.py:2489-2495 `assertLogs('users.cep_lookup','WARNING')`, `'viacep' in line`, `'brasilapi' in line` (reason text not asserted; spec says "e o motivo") | PASS (reason unasserted, minor) |

Not-cached-404 (spec assumption): tests.py:2479-2487 (`call_count == 4`).
Edge cases: city-wide CEP :2462; BrasilAPI null :2455; ViaCEP HTML/400 -> falls back :2421 (status 500 stand-in).

## Frontend ACs, code reading only (no automated tests by user decision)

| AC | Evidence | Result |
| -- | -------- | ------ |
| CEP-12 | useAddress.ts `handlePostalCodeChange`: `digits.length === 8` -> `lookup(digits, ...)`; else `cancel()`. cep.service.ts:12 calls `/api/address/cep/${cep}` | PASS |
| CEP-13 | useAddress.ts `applyCepAddress` (non-empty writes; empty clears only if `current === lastAutofill`; else keeps) | **GAP** (see below) |
| CEP-14 | `applyCepAddress` merges only address/neighborhood/city/state; number/complement untouched | PASS |
| CEP-15 | address.tsx `{cepLoading && <ActivityIndicator/>}`; no `disabled`/`editable` props on inputs or Próximo | PASS |
| CEP-16 | useCepLookup.ts:12-27 `latestCepRef` compare after await, in both try and catch; `cancel()` on <8 digits | PASS |
| CEP-17 | useCepLookup.ts:22-23 404 -> `cep_not_found`; errorMessages.ts text matches spec char for char; no ErrorModal call | PASS |
| CEP-18 | useCepLookup.ts:23 all other errors -> `cep_lookup_failed`; text matches spec | PASS |
| CEP-19 | Inputs remain plain editable; `validateFields` unchanged; `setErrors` clears the 4 autofilled field errors only | PASS |
| CEP-20 | address.tsx CEP row is the first child of `styles.form`, above Endereço/Número | PASS |
| CEP-21 | `numberInputRef.current?.focus()` at end of `applyCepAddress`, which runs only on non-stale 200 | PASS |

### Gap: CEP-13 records user-kept values as "last autofill"
`applyCepAddress` sets `lastAutofillRef.current = merged`, and `merged[field]` also holds the kept user-typed value in the third branch. Repro: user types "Rua X" by hand, looks up a city-wide CEP (empty street) -> "Rua X" kept and stored as autofill; user then looks up another CEP with empty street -> `current === lastAutofill` -> "Rua X" is cleared. Spec rule 3 says the user's typed value is kept, and "último preenchimento automático" means values the lookup wrote. Fix: store in lastAutofillRef only fields the lookup wrote (non-empty writes and `''` clears), and for kept fields set it to `undefined`.

## Discrimination Sensor

Isolated `git worktree` at HEAD in the scratchpad (removed afterwards). Real tree `git status --porcelain` matched the pre-sensor baseline. The only drift was `backend/media/profile_pics/profile_TYdnl34.jpg`, a file created by the full `manage.py test users` run, which the Verifier removed. Suites run per mutant: CepLookupServiceTest + CepLookupViewTest (24 tests).

Depth: 22 mutations, 21 killed, 1 survived.

| # | File | Mutation | Result |
| - | ---- | -------- | ------ |
| 1 | cep_lookup.py:38 | timeout removed (`timeout=None`) | Killed |
| 2 | cep_lookup.py:38 | timeout 10 | Killed |
| 3 | cep_lookup.py:64 | `complemento` leaked into result | Killed (4 failures) |
| 4 | cep_lookup.py:58 | `erro:'true'` string not treated as not-found | Killed |
| 5 | cep_lookup.py:58 | `erro: true` boolean not treated as not-found | Killed |
| 6 | cep_lookup.py:109 | 404 cached (`cache.set` before `CepNotFound`) | Killed |
| 7 | cep_lookup.py:12 | TTL 1 h | Killed |
| 8 | cep_lookup.py:90 | cache key `cep_<digits>` | Killed |
| 9 | cep_lookup.py:100 | warning log removed | Killed |
| 10 | cep_lookup.py:100 | wrong provider name in log | Killed |
| 11 | cep_lookup.py:32 | null not coerced to "" | Killed |
| 12 | cep_lookup.py:87 | length check `!= 8` -> `< 8` | Killed |
| 13 | cep_lookup.py:103 | `not_found = True` dropped | Killed |
| 14 | cep_lookup.py:46-47 | BrasilAPI 404 treated as failure | Killed |
| 15 | cep_lookup.py:44-45 | non-200 status check removed | **SURVIVED** |
| 16 | views.py:262 | rate 31/min | Killed |
| 17 | views.py:262 | rate 10/min | Killed |
| 18 | views.py:266 | 404 message text changed | Killed |
| 19 | views.py:264 | 400 message text changed | Killed |
| 20 | views.py:268 | 503 message text changed | Killed |
| 21 | views.py:265 | 404 status -> 400 | Killed |
| 22 | views.py:260 | throttle removed | Killed |

Mutant 15: every non-200 test mock returns `json=None` (tests.py:2422, 2434, 2444), so the `isinstance(dict)` guard masks the removed status check. A real 500/503 with a JSON dict body (e.g. `{"message": "..."}`) would be treated as a found address with empty fields. Fix: add a test where ViaCEP returns 500 with a dict body and assert fallback (CEP-03/05).

## Interactive UAT

NOT RUN. The frontend UI UAT (tasks.md T8 script steps 1-8, web and Android) has not been executed by a human. Steps 2, 5 and 9 backend parts were curl-verified live by the author (results above), which does not cover the UI behavior. Frontend ACs CEP-12..CEP-21 are verified by code reading only.

## Other observations

- tasks.md:13 still reads `**Status**: Draft (aguardando aprovação para Execute)`, and spec.md traceability rows are all `Pending`. Both are stale.
- Test count before feature: not re-measured by the Verifier; tasks.md records the baseline. Post-feature `users` run: 133 tests, 0 removed in the diff.
- Code quality: diff touches only feature files (address.tsx, useAddress.ts, useCepLookup.ts, cep.service.ts, errorMessages.ts, AdressStyle.ts, cep_lookup.py, views.py, urls.py, tests.py); follows the existing google_auth module pattern. No unrelated changes.
- CEP-11 test does not assert the reason string.

## Summary

**Overall**: Not ready (FAIL).
**Spec-anchored check**: 11/11 backend ACs matched spec outcome; frontend 9/10 by reading (CEP-13 gap).
**Sensor**: 21/22 killed.
**Gate**: 133 passed, tsc errors 4/4.

Ranked gaps: 1. CEP-13 lastAutofill bug (useAddress.ts applyCepAddress). 2. Surviving mutant 15 (missing test for non-200 with dict body). 3. Human UAT not run. 4. Stale Draft/Pending statuses. 5. CEP-11 reason unasserted.
