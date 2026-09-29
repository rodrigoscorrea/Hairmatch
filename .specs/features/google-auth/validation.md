# Login e Cadastro via Google Validation

**Date**: 2026-09-27
**Spec**: `.specs/features/google-auth/spec.md`
**Diff range**: uncommitted working tree on `develop` vs `HEAD` (`f835c88`). Nothing is committed yet, by explicit user instruction.
**Verifier**: independent sub-agent (author ≠ verifier), read-only on the real tree except this file.
**Scope**: T1–T22. **T23 (manual UAT on web and Android with real Google Cloud Client IDs, plus the RF2/RF5 docs update) is NOT covered here.** The user performs it as a separate step. Every frontend AC below is "code-reviewed" only and still needs T23 to be verified end to end.

---

## Verdict

**Result: PASS ✅ for T1–T22.** Fix 1 (below) was applied after this report was first written, and M14b is now killed. Details:

- All 19 backend ACs are covered by tests that assert the spec-defined outcome.
- 17 of 17 sensor mutants are killed (M14b fixed post-report; see Fix 1).
- Both gates are green (re-run after Fix 1: 256 passed, 0 failed).
- The frontend code review found no AC that is missing or implemented incorrectly.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1–T9 | ✅ Done | Automated Done-when items checked. Verified here: deps pinned, `settings.GOOGLE_OAUTH_CLIENT_IDS` parse, migration `0005`, helpers, verifier. |
| T10, T11, T13, T14, T17–T22 | ✅ Done (code) | Each has one manual Done-when item deferred to T23 because no device, browser or Client ID was available. That is recorded in `tasks.md` and is not a gap for this validation. |
| T12, T15, T16 | ✅ Done | Checked by code reading. |
| T23 | ⏭️ Out of scope | Manual UAT and docs, performed by the user. |

---

## Spec-Anchored Acceptance Criteria: backend (automated)

All citations point to `backend/users/tests.py` unless stated otherwise.

**Precision note (applies to all rows):** the spec pins the exact error text only for GAUTH-11. For the other error ACs it requires `{"error": ...}`, so `assertIn('error', response.json())` is the correct precision. This is not a spec-precision gap.

| AC | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| GAUTH-01 | 200 `{"status":"authenticated"}`; cookie `jwt`, payload `{id, exp=iat+60min, iat}`, HS256 `'secret'`, httponly, samesite=None, secure | `tests.py:1995` `assertEqual(status_code, 200)`; `:1996` `assertEqual(json(), {'status': 'authenticated'})`; helper `:1978` `assertTrue(cookie['httponly'])`, `:1979` `assertEqual(cookie['samesite'], 'None')`, `:1980` `assertTrue(cookie['secure'])`, `:1981-1983` `jwt.decode(..., 'secret', ['HS256'])`, `payload['id']==user.id`, `exp-iat==3600`; `:1987` `/api/auth/user` → `{'authenticated': True}`. Unit: `:1735-1750` | ✅ PASS |
| GAUTH-02 | same email (case-insensitive), `google_id` empty → store `sub`, respond as in 01 | `tests.py:2002` identity email `'Ana@Gmail.com'` vs stored `'ana@gmail.com'`; `:2007` body `authenticated`; `:2009` `assertEqual(user.google_id, 'google-sub-123')`; `:2010` password untouched; `:2011` `User.objects.count()==1`; `:2012` full cookie check | ✅ PASS |
| GAUTH-03 | missing/empty `id_token` → 400 `{error}`, no cookie | `tests.py:2015` subTests `{}` and `{'id_token': ''}`; `:2019` `==400`; `:2020` `assertIn('error', …)`; `:2021` `assertNotIn('jwt', response.cookies)`; `:2022` verifier not called | ✅ PASS |
| GAUTH-04 | verification failure (signature/expiry/issuer) or `aud` not in list → 401, no cookie, no row changed | View: `tests.py:2031` `==401`; `:2033` no `jwt`; `:2034` `assertEqual(self._users_snapshot(), before)`. Unit: `:1852` `ValueError`→`GoogleTokenError`; `:1858` `GoogleAuthError`→`GoogleTokenError`; `:1864` aud outside list rejected; `:1871` empty list rejects; `:1850` `assertIsNone(kwargs['audience'])` | ✅ PASS |
| GAUTH-05 | `email_verified` not true → 403, no cookie, no row changed | `tests.py:2043` `==403`; `:2045` no `jwt`; `:2046` snapshot unchanged (a same-email unlinked user exists, so a missing gate would link it); unit `:1877-1888` `'false'`/missing → `False`, `'true'`/`True` → `True` | ✅ PASS |
| GAUTH-06 | same email, different `google_id` → 409, no cookie | `tests.py:2055` `==409`; `:2057` no `jwt`; `:2058` snapshot unchanged | ✅ PASS |
| GAUTH-11 | password login on passwordless user → 403, exact message | `tests.py:1917` `==403`; `:1918-1921` `assertEqual(json()['error'], 'Esta conta usa login com Google. Use o botão Entrar com Google.')`; `:1922` no `jwt` | ✅ PASS |
| GAUTH-12 | new account → 200 `{status:'signup_required', signup_token:<str>, prefill:{email, first_name, last_name}}`, no cookie, zero rows | `tests.py:2067` `==200`; `:2069` status; `:2070` `assertIsInstance(signup_token, str)`; `:2071-2075` exact `prefill` dict; `:2076` no `jwt`; `:2077-2079` User/Customer/Hairdresser counts unchanged | ✅ PASS |
| GAUTH-13 | `signup_token` exp = issue + 30 min, contains `email` and `sub` | Unit (frozen clock) `tests.py:1759-1763` `email`, `sub`, `purpose`, `iat==now`, `exp==now+30min`; view `:2087-2089` decoded `email`, `sub`, `exp-iat==1800` | ✅ PASS |
| GAUTH-14 | signed with a different key; `GET /api/auth/user` with it as `jwt` cookie → 200 `{"authenticated": false}`, not 500 | `tests.py:1929-1930` `==200` and `assertEqual(json(), {'authenticated': False})`; `:1794-1803` `'secret'`-signed token rejected by `decode_signup_token`; `:1942-1943` invalid signature → same | ✅ PASS |
| GAUTH-15 | customer: one transaction; `User(email from token, password NULL, google_id=sub, role='customer', phone '55…')` + `Customer.cpf`; 201 + cookie | `tests.py:2160` `==201`; `:2162` email; `:2163` `assertIsNone(user.password)`; `:2164` google_id; `:2165` `role=='customer'`; `:2166` `phone=='5592991234567'`; `:2167` `Customer.cpf=='12345678900'`; `:2169` full cookie check. Atomicity: see GAUTH-22 | ✅ PASS |
| GAUTH-16 | hairdresser: `User(role='hairdresser', google_id, password NULL)` + `Hairdresser(cnpj, experience_time, experiences, products, resume)`; 201 + cookie | `tests.py:2174` `==201`; `:2177-2179` password None, google_id, role; `:2181-2185` all 5 Hairdresser fields exact; `:2187` cookie | ✅ PASS |
| GAUTH-17 | token email used; form `email`/`password`/`confirmPassword` ignored | `tests.py:2192-2194` form sends other email and passwords; `:2201` `user.email=='ana@gmail.com'`; `:2202` password None; `:2203` other email not created | ✅ PASS |
| GAUTH-18 | invalid/tampered/expired token → 401, zero rows | `tests.py:2223` subTests expired and tampered; `:2229` `==401`; `:2231` no `jwt`; `:2232` `_assert_no_new_rows()` (User, Customer, Hairdresser, preference links = 0, `:2138-2142`) | ✅ PASS |
| GAUTH-19 | phone `55`+digits already exists → 409, zero rows | `tests.py:2235` existing `'5592991234567'`, request `'92991234567'`; `:2239` `==409`; `:2242` no new rows | ✅ PASS |
| GAUTH-20 | token email (case-insensitive) or `sub` already exists → 409, zero rows | `tests.py:2246-2247` subTests `'ANA@gmail.com'` and `google_id='google-sub-123'`; `:2255` `==409`; `:2258` no new rows | ✅ PASS |
| GAUTH-21 | role missing/invalid, or any required field missing (incl. cpf/cnpj) → 400, zero rows | `tests.py:2262-2265` each of 10 customer fields plus hairdresser `cnpj`; `:2273` `==400`; `:2275` no rows; `:2277` `role='admin'` (and short phone); `:2282`, `:2284` | ✅ PASS |
| GAUTH-22 | error after `User` inserted → rollback, no User/Customer/Hairdresser/preference links | `tests.py:2286-2296` invalid preferences JSON (customer and hairdresser) → 400 + no rows; `:2298-2308` `Customer.objects.create` raises after preference linked → `:2305` `==500`, `:2306` exact `{'error': 'Erro ao criar a conta.'}`, `:2308` no rows incl. `User.preferences.through` | ✅ PASS (see Fix 1 for the preference-link clause) |
| GAUTH-23 | second call without finishing → `signup_required` again | `tests.py:2098-2099` second `==200`, `status=='signup_required'`; `:2100` no `jwt`; `:2101` `User.objects.count()==0` | ✅ PASS |

**Status**: ✅ 19/19 backend ACs covered, and every asserted value matches the spec outcome. 0 spec-precision gaps.

End-to-end (Independent Test): `tests.py:2310-2347` runs `POST /auth/google` → `signup_required` → `POST /auth/register` with the returned token → `GET /api/user/authenticated` for both roles. It returns the role profile with the right email and role.

---

## Frontend structural review (no automated tests: user decision, not a gap)

Every row is **code-reviewed only. It still needs T23 UAT.**

| AC | Implementation evidence | Finding |
| -- | ----------------------- | ------- |
| GAUTH-07 | `frontend-mobile/hooks/authHooks/useGoogleAuth.ts:45-47` `authenticated` → `loadSession()`. `frontend-mobile/app/_layout.tsx:59` `GET /api/auth/user` → `:62` `GET /api/user/authenticated` → `setUserToken`. `RootLayoutNav` `_layout.tsx:33-38` redirects from `(auth)` to `/(app)/(customer)/home` or `/(app)/(hairdresser)/agenda` | ✅ Matches spec. Paths are exact. |
| GAUTH-08 | Web `useGoogleIdToken.web.ts:42` non-success → `null`. Android `useGoogleIdToken.ts:32` `cancelled` → `null`. `useGoogleAuth.ts:41` `if (!idToken) return;` with no modal; `finally` `:67-69` resets loading | ✅ |
| GAUTH-09 | `useGoogleAuth.ts:14-19` axios error → `response.data.error` or `'Não foi possível entrar com o Google. Tente novamente.'`. `:65-66` goes to `googleError`, shown by `ErrorModal` in `app/(auth)/login.tsx` and `register/index.tsx` | ✅ One documented `SPEC_DEVIATION`: non-axios errors (for example the Expo Go message) show `error.message`. That is reasonable and in scope of T14. |
| GAUTH-10 | `useGoogleAuth.ts:34-36` `inFlight` ref guard + `setIsGoogleLoading(true)`. `components/GoogleSignInButton.tsx:14,20` `disabled={disabled \|\| loading}`. Screens pass `loading={isGoogleLoading}` | ✅ |
| GAUTH-24 | `useGoogleAuth.ts:55-61` seeds `{...INITIAL_REGISTRATION_DATA, email, first_name, last_name, google_signup_token}`. The keys match `IRegistrationData` and the step-1 inputs (`register/index.tsx` reads `registrationData.first_name/last_name/email`). `:62-63` pushes `/(auth)/register` when not already there. The provider is lifted to `app/(auth)/_layout.tsx`, so the login screen can seed it | ✅ |
| GAUTH-25 | `useRegisterForm.ts:21` `isGoogleMode`. `:74` and `:114` skip all password checks. `app/(auth)/register/index.tsx:149` `editable={!isGoogleMode}`; `:161` password fields not rendered | ✅ |
| GAUTH-26 | `usePreferences.ts:77-80` and `useDescription.ts:56-59` drop `password`/`confirmPassword`/`email` and keep `google_signup_token`. `:117-119` / `:95-97` → `loadSession()`, with no `Alert` and no redirect to login. Web `signUp` uses `withCredentials: true` (`_layout.tsx:94`) | ✅ Cookie persistence on Android native `fetch` is a spec assumption that T23 must confirm. |
| GAUTH-27 | Web `signUp` throws `error.response.data`. Native checks `!response.ok` (`_layout.tsx:109`) and throws the parsed `{error}`. Both catches read `error.error`. The modal close does not redirect in Google mode (`usePreferences.ts:175`, `useDescription.ts:130`, wired through `closeErrorModal`) | ✅ |
| GAUTH-28 | Step 1 inputs read from context, so seeding while on `/register` updates the visible fields. `pathname === '/register'` skips the push. The button is hidden in Google mode (`register/index.tsx:51`) | ✅ Cosmetic: a photo picked before tapping stays in local `profileImage` preview but is not sent (already recorded in `tasks.md` T20). |
| GAUTH-29 | Same `authenticated` → `loadSession` path. `RootLayoutNav` fires for any `(auth)` segment, including `register` | ✅ |
| GAUTH-30 | `useLogin.ts:31` `resetRegistration()` before `router.push`. `RegistrationContext.tsx:84` resets to `INITIAL_REGISTRATION_DATA`, including `google_signup_token: ''` | ✅ |

Other frontend observations (non-blocking):
- `AuthContext` is `createContext<any>` (`_layout.tsx:18`), so `tsc` cannot check `loadSession` call sites. I checked them by hand: `useGoogleAuth`, `usePreferences` and `useDescription` all destructure an existing member.
- **UAT watch item (not a gap):** the app's `signOut` does not call `GoogleSignin.signOut()` on Android. Already flagged as unverified in `design.md`. It may make UAT steps 5, 7 and 8 silently reuse the previous Google account instead of showing the account picker.
- The phone is stripped to digits client-side before submit (`usePreferences.ts:71`, `useDescription.ts:50`). The backend's `f"55{phone}"` does not strip. GAUTH-19's "55 + dígitos" therefore holds end to end, but only because the client strips.

---

## Discrimination Sensor

- **Method:** `backend/` was rsync'd to the scratchpad, excluding `.venv`, `media` and `__pycache__`. Mutants ran there one at a time with the real venv and `.env`. The real tree was never edited.
- **Checks per mutant:** each mutant was asserted to match exactly once in the copy. After each run the file was restored and compared byte for byte.
- **Baseline:** the unmutated scratch copy passed 109/109.
- **Kill quality:** every kill came from assertion failures in the expected test class, or uncaught exceptions where the spec demands "not 500". There were no import or syntax errors.

| # | File:line (real) | Mutation | Killed? | Killing test(s) |
| - | ---------------- | -------- | ------- | --------------- |
| M1 | `backend/users/google_auth.py:18` | Drop the `aud` allow-list check | ✅ Killed | `GoogleAuthVerifierTest.test_audience_outside_list_is_rejected`, `…test_empty_client_id_list_rejects_everything` |
| M2 | `backend/users/google_auth.py:25` | `email_verified` → `bool(raw)` (`'false'` becomes True) | ✅ Killed | `…test_email_verified_is_normalized_to_bool` |
| M3 | `backend/users/views.py:233` | Remove the `email_verified` gate in `GoogleAuthView` | ✅ Killed | `GoogleAuthViewTest.test_unverified_email_returns_403_without_changes` |
| M4 | `backend/users/views.py:238` | `email__iexact` → `email` | ✅ Killed | `…test_existing_email_with_different_case_is_linked_and_authenticated` |
| M5 | `backend/users/views.py:240` | Remove the 409 branch (relink over a different `google_id`) | ✅ Killed | `…test_email_linked_to_another_google_account_returns_409` |
| M6 | `backend/users/views.py:128` | Remove `transaction.atomic` | ✅ Killed | `GoogleRegisterTest.test_invalid_preferences_json_rolls_back_everything`, `…test_error_after_preferences_are_linked_rolls_back_everything` |
| M7 | `backend/users/views.py:124` | Duplicate-phone check without the `55` prefix | ✅ Killed | `…test_phone_already_registered_with_country_prefix_returns_409` |
| M8 | `backend/users/auth_tokens.py:44,49` | Sign and decode the signup token with the session key `'secret'` | ✅ Killed | `LoginViewGoogleAccountTest.test_auth_user_with_signup_token_cookie_is_not_authenticated`, `AuthTokensTest.test_decode_rejects_token_signed_with_session_key`, `…test_signup_token_claims_and_30_minute_expiry` |
| M9 | `backend/users/views.py:215` | Narrow `except` back to `ExpiredSignatureError` | ✅ Killed | both `LoginViewGoogleAccountTest` `auth_user` tests (500 instead of `{authenticated: false}`) |
| M10 | `backend/users/auth_tokens.py:6` | `SIGNUP_TOKEN_TTL` 30 → 60 min | ✅ Killed | 4 tests (unit expiry, view `exp-iat==1800`, expired → 401 ×2) |
| M11 | `backend/users/views.py:192` | Remove the passwordless 403 guard | ✅ Killed | `…test_password_login_on_google_only_account_returns_403` |
| M12 | `backend/users/views.py:122` | Remove the `sub` duplicate check in register | ✅ Killed | `…test_email_or_google_sub_already_registered_returns_409` |
| M13 | `backend/users/views.py:248` | Set a session cookie on the `signup_required` response | ✅ Killed | `…test_new_account_returns_signup_required_without_creating_rows`, `…test_new_account_calling_again_is_still_signup_required` |
| M14 | `backend/users/views.py:149` | Google path passes `preferences='[]'` (also neutralizes invalid JSON) | ✅ Killed (incidental) | `…test_invalid_preferences_json_rolls_back_everything`. Killed only because invalid JSON stopped failing; see M14b. |
| M14b | `backend/users/views.py:160` (`_create_role_profile`) | Google path validates the preferences JSON but **never links** the preferences | ✅ Killed (post-fix, re-run) | `GoogleRegisterTest.test_google_customer_signup_creates_user_customer_and_session` (now asserts `user.preferences` equals the sent ids); also fails the classic `RegisterViewTest.test_register_with_preferences`, since both paths share `_create_role_profile` |
| M15 | `backend/users/views.py:118` | Use the form `email` over the token email | ✅ Killed | `…test_form_email_and_password_are_ignored` |

**Sensor depth**: P0 (auth). 16 behavior-level manual mutations covering every branch of `GoogleAuthView`, `_register_with_google`, `LoginView` changes, `auth_tokens` and `google_auth`, plus 1 probe.

**Result: 17/17 killed** after Fix 1. M14b was re-applied to `backend/users/views.py:160` (disabled the `if` body that links preferences), the strengthened test failed as expected (`user.preferences` empty), the mutation was reverted, and `git diff`/`grep MUTATION` confirmed no leftover.

**Isolation**: the real tree was verified after the sensor run:
- `git status --porcelain` matched the pre-sensor capture.
- `git diff` was byte-identical (`cmp`).
- `sha256sum -c` passed on every `backend/users/*.py`, including the untracked `auth_tokens.py` and `google_auth.py`, which git cannot see.

---

## Gate Check

- **Quick gate** (`python manage.py test users`, before the sensor): 109 passed, 0 failed.
- **Full gate** (`coverage run manage.py test && coverage report -m`, final): **256 passed, 0 failed, 0 skipped**.
  - Coverage: `users/auth_tokens.py` 100%, `users/google_auth.py` 100%, `users/views.py` 91%.
  - Uncovered new-code lines: `views.py:147-148`, the `profile_picture` save in the Google path.
- **App gate** (`npx tsc --noEmit | grep -c "error TS"`): **4**, baseline 4. All 4 errors are in pre-existing files (`app/(app)/(customer)/_layout.tsx`, `hairdresser-reservation/[id].tsx`, `app/(app)/(hairdresser)/_layout.tsx`, `components/BottomBar.tsx`).
- **Test count**: 219 → 256 in the project (+37) and 72 → 109 in `users` (+37).
- **Test integrity**: the only change to a pre-existing test line is `tests.py:1702`, where a trailing newline was added (the assertion is identical). The import line gained `SimpleTestCase, override_settings`. No test was removed or weakened.
- **Gate artifacts left in the tree** (created by running the gates; not deleted, per the read-only constraint):
  - `backend/.coverage`
  - `backend/media/profile_pics/profile_54hJNtE.jpg`
  - `backend/media/profile_pics/profile_mLlCLYg.jpg`

  The images come from pre-existing `RegisterViewTest` uploads. The user may delete all three.

---

## Edge Cases

- [x] Missing `given_name`/`family_name` → `''` in `prefill`. Unit test `tests.py:1890-1899`. The view passes the value through (`views.py:249-255`), and the wizard requires the names.
- [x] Email with different case → same user (`tests.py:2000-2012`, GAUTH-02; `tests.py:2246`, GAUTH-20).
- [x] Signup token expires mid-wizard → 401 (`tests.py:2205-2232`), and the app shows the error and stays in the wizard (GAUTH-27 code review).
- [x] Both roles accepted in Google mode (`tests.py:2157`, `:2171`, `:2310`).

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code / no scope creep in feature files | ✅ Helpers and view follow `design.md` 1:1. `_create_role_profile` is extracted without changing classic behavior. |
| Surgical changes | ⚠️ Two unattributed non-feature changes are in the diff surface; see Fix 3. |
| Matches existing patterns | ✅ `JsonResponse({'error': …})` in Portuguese, `APIClient` + `reverse` tests, `EXPO_PUBLIC_*` env |
| Spec-anchored outcome check | ✅ |
| Per-layer coverage (domain 1:1; routes happy + edge + error) | ✅ All 3 routes have happy, edge and 400/401/403/409 paths, plus "no rows" and "no Set-Cookie" |
| Every test maps to an AC, edge case or Done-when | ✅ All 37 new tests map to T4–T8 Done-when items or GAUTH ACs |
| Documented guidelines followed | none found (no AGENTS.md/CONTRIBUTING.md). Strong defaults applied. |

Minor code note (non-blocking): `_register_with_google` catches any `ValueError` at `views.py:150` as "As preferências enviadas são inválidas." (400). A non-numeric `rating` would get that mislabeled message. This is low risk because the app always sends `rating=5`.

---

## Fix Plans

### Fix 1: Prove that preferences are linked in the Google sign-up path (surviving mutant M14b) — ✅ Applied
- **Root cause**:
  - Every `GoogleRegisterTest` happy path sent `preferences=[]`.
  - The rollback test asserted zero preference links, but never proved a link was created, so its preference clause was vacuous.
  - Dropping the preference linking in the Google path went undetected.
- **Fix applied**: `backend/users/tests.py::GoogleRegisterTest.test_google_customer_signup_creates_user_customer_and_session` now creates 2 `Preferences`, sends `preferences=json.dumps([pref1.id, pref2.id])`, and asserts `assertCountEqual(user.preferences.values_list('id', flat=True), [pref1.id, pref2.id])`.
- **Verified**: M14b re-run against `_create_role_profile` and killed (fails both the Google test above and the classic `test_register_with_preferences`, since the code path is shared). Mutation reverted; `git diff`/`grep MUTATION` confirm the real tree is clean. Full suite re-run: 256 passed, 0 failed (test count unchanged — an existing test gained an assertion, no new test method was added).
- **Priority**: Minor. Test-only change, no production code touched.

### Fix 2 (optional): Cover the profile picture in the Google path
- **Root cause**: `views.py:147-148` is uncovered.
- **Fix task**: add `SimpleUploadedFile` to one Google sign-up test and assert that `user.profile_picture` is set.
- **Priority**: Minor.

### Fix 3: Confirm the unattributed non-feature changes before committing — ✅ Resolved, no action needed
- Checked against the git status captured at the very start of this session (before any batch worker touched a file): `.env.example` (repo root), `frontend-mobile/.env.example` and `frontend-mobile/app.json` were **already modified, uncommitted, by the user, before this feature's implementation began.** None of the three batch workers introduced these lines.
- The only feature-attributable additions are: `GOOGLE_OAUTH_CLIENT_IDS=` (root `.env.example`, T2) and `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=` (`frontend-mobile/.env.example`, T9). The `web.output: "single"` change and the concrete local defaults in the root `.env.example` predate this session and are the user's own prior work.
- **Priority**: N/A — not a feature concern. No action taken.

---

## Requirement Traceability Update (proposed; `spec.md` not edited by the Verifier)

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| GAUTH-01 … GAUTH-06 | Implementing | ✅ Verified (automated) |
| GAUTH-11 … GAUTH-23 | Implementing | ✅ Verified (automated) |
| GAUTH-07 … GAUTH-10 | Implementing | Code-reviewed; pending UAT (T23) |
| GAUTH-24 … GAUTH-30 | Implementing | Code-reviewed; pending UAT (T23) |

---

## Summary

**Overall**: ✅ Ready for T23 (manual UAT). Fix 1 is recommended first because it is cheap and test-only.

**Spec-anchored check**: 19/19 backend ACs match the spec outcome, with 0 spec-precision gaps. All 11 frontend ACs are implemented as specified by code review.
**Sensor**: 16/17 mutations killed. One survivor is outside the AC surface and is routed to Fix 1.
**Gate**: backend 256 passed, 0 failed. App `tsc` 4 errors, baseline 4.

**What works**:
- Existing-account login, including case-insensitive linking of password accounts.
- Every rejection path (400/401/403/409), with no cookie and no DB change.
- The pending signup token: separate key, 30-minute expiry, never accepted as a session.
- Atomic Google registration for both roles, with the session cookie issued on 201.
- The passwordless password-login 403.
- The app flow wiring for login, sign-up, cancellation, errors, the reset link and wizard completion.

**Next steps**:
1. Optionally apply Fix 1 (and Fix 2), then re-run M14b.
2. The user resolves Fix 3.
3. The user runs T23 on web (including a published `expo export` build) and on the Android `preview` APK with real Client IDs.

Lesson distillation (`lessons.py add`) is deferred. The Verifier was restricted to writing only this file. Candidate lesson: "Any rollback test that asserts 'no X rows' must also have a sibling happy-path test proving X rows are created. Otherwise the clause is vacuous."
