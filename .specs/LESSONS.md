# LESSONS - auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

_none_

## Candidates (under observation - do NOT load as guidance yet)

Seen once or not yet corroborated. Tracked, not trusted.

### L-001 - A rollback test asserting 'zero X rows' does not prove X rows get created on the happy path — pair every such rollback assertion with a happy-path test that asserts the actual created/linked values.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `backend/users/tests.py` · harmful: 0
- features: google-auth
- evidence: M14b (backend/users/tests.py)
- last seen: 2026-09-27T21:37:43Z

### L-002 - When an AC defines a state by two conditions together, test the case where only one holds.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `backend/users/tests.py` · harmful: 0
- features: email-confirmation
- evidence: R15 (users/views.py _PENDING_ACCOUNT) (backend/users/tests.py)
- last seen: 2026-10-04T21:00:59Z

### L-003 - A 'no secret in logs' check must watch every logger the route can write to, not only the service logger.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `backend/users/tests.py` · harmful: 0
- features: email-confirmation
- evidence: E14 (EMC-49) (backend/users/tests.py)
- last seen: 2026-10-04T21:00:59Z

### L-004 - A case-insensitive lookup needs a different-case test on every path that uses it, login included.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `backend/users/tests.py` · harmful: 0
- features: email-confirmation
- evidence: L04 (EMC-25) (backend/users/tests.py)
- last seen: 2026-10-04T21:00:59Z

### L-005 - When an AC lists the surfaces a rule covers, grep every query of that model for the same exposure before closing the AC.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `backend/users/tests.py` · harmful: 0
- features: email-confirmation
- evidence: EMC-39 (backend/users/tests.py)
- last seen: 2026-10-04T21:00:59Z

### L-006 - Test the exact boundary value the spec accepts or refuses, freezing the clock for time comparisons, not only one unit on each side.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `backend,validation,time` · harmful: 0
- features: external-appointment
- evidence: validation.md M3; backend/agenda/views.py:48 (backend,validation,time)
- last seen: 2026-10-10T04:13:11Z

### L-007 - For every optional body field, state in the spec whether JSON null counts as absent or as a wrong type, and pin it with a test.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `backend,api-contract` · harmful: 0
- features: external-appointment
- evidence: EXT-05; backend/agenda/views.py:58 (backend,api-contract)
- last seen: 2026-10-10T04:13:11Z

### L-008 - Alert.alert is a no-op on react-native-web, so feedback the spec requires on web needs another mechanism.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `frontend-mobile,web` · harmful: 0
- features: external-appointment
- evidence: EXT-31; frontend-mobile/node_modules/react-native-web/dist/exports/Alert/index.js:11 (frontend-mobile,web)
- last seen: 2026-10-10T04:13:11Z

### L-009 - Keep display-format examples identical across ACs that share one formatter, or state the per-screen variant explicitly
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `frontend-mobile` · harmful: 0
- features: customer-rating
- evidence: CRT-56 vs CRT-50 (frontend-mobile/app/(app)/hairdresser/agenda.tsx:154) (frontend-mobile)
- last seen: 2026-10-10T04:13:11Z

### L-010 - In tab-navigator screens specify navigation to an explicit tab route instead of router.back, since back history is unreliable across tabs and web refresh
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `frontend-mobile` · harmful: 0
- features: customer-rating
- evidence: SPEC_DEVIATION frontend-mobile/hooks/hairdresserHooks/useRateCustomer.ts:53-55 (frontend-mobile)
- last seen: 2026-10-10T04:13:11Z

### L-011 - Include JSON null among the non-string values in every required-field validation test.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `backend,validation` · harmful: 0
- features: account-settings
- evidence: validation.md M02; backend/users/tests.py:5957 (backend,validation)
- last seen: 2026-10-10T04:13:11Z

### L-012 - State in the AC whether client-side validation covers every field on the screen or only the changed ones.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `frontend-mobile,forms` · harmful: 0
- features: account-settings
- evidence: ACC-20; frontend-mobile/hooks/accountHooks/useAccountForm.ts:81 (frontend-mobile,forms)
- last seen: 2026-10-10T04:13:11Z

### L-013 - Define what autofill does with fields the lookup response omits.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `frontend-mobile,cep` · harmful: 0
- features: account-settings
- evidence: ACC-24; frontend-mobile/hooks/accountHooks/useAddressForm.ts:88-91 (frontend-mobile,cep)
- last seen: 2026-10-10T04:13:11Z

### L-014 - Write error pointers in ACs in the exact form the problem helper emits.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `specs,problem-details` · harmful: 0
- features: account-settings
- evidence: ACC-01..07; backend/hairmatch/problems.py:99-101 (specs,problem-details)
- last seen: 2026-10-10T04:13:11Z

### L-015 - Test the unexpected-exception cleanup path of every endpoint that stores files before a later step, not only the invalid-input path.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `tests,storage` · harmful: 0
- features: review-editing
- evidence: M05 backend/review/views.py:231 (tests,storage)
- last seen: 2026-10-10T18:14:39Z

### L-016 - Test the atomic block of a lock-and-write helper under TransactionTestCase, because TestCase wraps every test in a transaction and hides a missing atomic.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `tests,transactions` · harmful: 0
- features: review-editing
- evidence: M46 backend/review/customer_ratings.py:60 (tests,transactions)
- last seen: 2026-10-10T18:14:39Z

### L-017 - Assert at each call site that a failing storage delete still returns success, not only on the shared delete helper.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `tests,storage` · harmful: 0
- features: review-editing
- evidence: M29 backend/review/views.py:194 (tests,storage)
- last seen: 2026-10-10T18:14:39Z

### L-018 - Pin a declared default ordering by updating a row to move it before reading, because insertion order hides a missing Meta ordering.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `tests,models` · harmful: 0
- features: review-editing
- evidence: M42 backend/review/models.py:30 (tests,models)
- last seen: 2026-10-10T18:14:39Z

### L-019 - State in the spec whether body validation runs before the parent lookup for every new route, because an invalid body on a missing parent is otherwise undefined.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `specs,routes` · harmful: 0
- features: review-editing
- evidence: REV-11 REV-17 validation.md G5 (specs,routes)
- last seen: 2026-10-10T18:14:39Z

### L-020 - When a test checks that an existing storage key is not rewritten, also list the directory: Django storages save a duplicate under another name, so reading the original back proves nothing.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `backend/tests` · harmful: 0
- features: hairdresser-gallery
- evidence: M21 populate_hairdressers.py:70 (backend/tests)
- last seen: 2026-10-10T16:09:46Z

### L-021 - A test of a deterministic choice among N options needs many inputs (not one key and two options), or a random pick passes about half of the runs.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `backend/tests` · harmful: 0
- features: hairdresser-gallery
- evidence: M27 populate_hairdressers.py:72 (backend/tests)
- last seen: 2026-10-10T16:09:46Z

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
