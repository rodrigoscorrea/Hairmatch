# Configurações da conta: Validation

**Result**: PASS (rodada 2 de 3, HEAD `1ec6d41`). A única lacuna da rodada 1 (ACC-01, `null` em campo obrigatório) foi fechada, e o mutante M02 agora morre. Os ACs de app continuam pendentes de UAT (T21, do usuário).

**Data**: 2026-10-10 (rodadas 1 e 2)
**Spec**: `.specs/features/account-settings/spec.md`
**Diff range**: `develop..HEAD` (`fbf1d08..1ec6d41`, branch `120-editar-dados-da-conta-e-excluir-conta`, 24 commits). A rodada 2 olhou `3115e11..1ec6d41`. O commit `a8fc312` só traz a spec, o RT-88/RT-89 do `api-restful-routes` e o handoff do STATE.
**Verifier**: sub-agent independente (o autor não é o verificador). Nenhum código ou teste foi corrigido, commitado ou staged. Este arquivo é o único criado na árvore real.

Convenções:
- `tests.py` = `backend/users/tests.py`; `views.py` = `backend/users/views.py`.
- Todo `assert_problem(response, slug, ...)` também confere o status HTTP do catálogo e os membros do problem+json.
- `_assert_refused` (`tests.py:5948-5955`) confere o `validation-error`, a lista `errors` exata e que as linhas de `User` e do perfil não mudaram (`self._rows(email) == before`).

**Pointers**: os testes afirmam `#/<campo>`, por exemplo `{'pointer': '#/first_name', ...}`. É o formato de `body_error` (`backend/hairmatch/problems.py:99-101`), que testes anteriores também usam (`tests.py:2432`, `tests.py:2809`). Desde o `1ec6d41`, o spec escreve `#/<campo>` em ACC-01, 03, 04, 05, 07, 38 e 39 (`.specs/features/account-settings/spec.md:77`).

---

## Histórico das rodadas

| Rodada | HEAD | Veredicto | Lacunas | Sensor |
| ------ | ---- | --------- | ------- | ------ |
| 1 | `3115e11` | Reprovada | 1 lacuna de backend: ACC-01, `null` em campo obrigatório sem teste (mutante M02 sobrevivente). 3 lacunas de precisão do spec: ACC-20, ACC-24 e pointer `/` versus `#/`. | 32 mutações: 30 mortas, 1 sobrevivente (M02), 1 equivalente (M12) |
| 2 | `1ec6d41` | Aprovada | Nenhuma. | 33 mutações: 32 mortas, 1 equivalente (M12) |

**Rodada 2: o que mudou (`3115e11..1ec6d41`)**

| Commit | Mudança | Conferido |
| ------ | ------- | --------- |
| `d93ec31` | `(None, 'This field is required.')` entra na tupla do teste do ACC-01, para os 8 campos obrigatórios (`tests.py:5960-5961`). | O M02 agora morre. O M02b novo também morre: ele tira o ramo do `None`, e aí o `null` cai em "must be a string", então o teste fixa também o `detail`. O número de testes não muda (é um subTest a mais). |
| `da0b892` | O comentário da guarda do `PUT` passa a explicar o motivo real (`views.py:858-859`): o storage renomeia numa colisão, e a guarda só protege o caso em que o objeto antigo já sumiu do bucket. | Bate com `Storage.get_available_name`, que o `S3MediaStorage` não sobrescreve (`backend/hairmatch/storage.py:16`). Só muda o comentário. |
| `1ec6d41` | Ajustes no spec: pointers `#/<campo>`; ACC-20 valida só o campo alterado (`spec.md:108`); ACC-24 mantém o valor gravado do campo que a resposta do CEP não traz e apaga só o que a consulta anterior escreveu (`spec.md:124`). | O texto novo bate com o código: `useAccountForm.ts:32-41` e `:81`, e o merge em `useAddressForm.ts:81-101`. `validate_spec.py` sai com exit 0, sem erros nem avisos. |

Nenhum arquivo de app mudou na rodada 2. A leitura dos ACs de app da rodada 1 continua valendo.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1-T6 (backend) | ✅ Done | Commits `67da371` a `051351a`. |
| T7-T20 (app) | ✅ Done | Commits `5c50047` a `3115e11`. Conferidos por leitura (o app não tem suíte, por decisão do spec). |
| Fixes da rodada 1 | ✅ Done | `d93ec31`, `da0b892` e `1ec6d41`. |
| T21 (UAT web e Android) | ⏳ Aberta de propósito | É do usuário. Os ACs de app ficam "pending UAT". |

---

## Spec-Anchored Acceptance Criteria

### Backend (exigem teste automatizado)

| AC | Resultado definido no spec | `file:line` + asserção | Resultado |
| -- | -------------------------- | ---------------------- | --------- |
| ACC-01 | 400 `validation-error`, um item `#/<campo>` por campo, nada gravado, para vazio, espaços ou valor não-string | `tests.py:5957-5965`: laço sobre os 8 obrigatórios × `''`, `'   '`, `None`, `42`, `_assert_refused(..., [{'pointer': f'#/{field}', 'detail': ...}])` (`None` → `'This field is required.'`, `tests.py:5961`); `tests.py:6060`: dois pointers no mesmo 400 | ✅ PASS (rodada 2; na rodada 1 o `null` não era testado) |
| ACC-02 | 400 com pointer, nada gravado, acima do `max_length` (100/150/6) | `tests.py:5967`: `_assert_refused({field: 'a'*(limit+1)}, [{'pointer': f'#/{field}', 'detail': f'... at most {limit} ...'}])` para os 7 campos, e no limite `status == 200` e valor gravado | ✅ PASS |
| ACC-03 | 400 `#/phone` quando os dígitos diferem dos gravados e não casam `^55\d{10,11}$` | `tests.py:5985`: 9 dígitos, 14 dígitos, sem `55`, fixo sem `55` e dígito Unicode largo → `_assert_refused(..., '#/phone')`; `tests.py:5994`: `55`+10 gravado `'559232345678'` | ✅ PASS |
| ACC-04 | 400 `#/postal_code` sem 8 dígitos | `tests.py:6001`: `6905700`, `690570001`, `69057-00`, `abcdefgh` | ✅ PASS |
| ACC-05 | 400 `#/state` sem 2 letras | `tests.py:6010`: `Amazonas`, `A1`, `A` | ✅ PASS |
| ACC-06 | 400 com pointer para CPF ≠ 11 e CNPJ ≠ 14 dígitos | `tests.py:6019` (CPF 10, 12 e inteiro); `tests.py:6027` (CNPJ 13 e 15) | ✅ PASS |
| ACC-07 | 400 `#/resume` para não-string ou > 1000 | `tests.py:6038` (`'a'*1001` e `42`); `tests.py:6050` (1000 e `''` gravados) | ✅ PASS |
| ACC-08 | 200, `phone`/`postal_code`/`cpf`/`cnpj` só dígitos, `state` maiúsculo | `tests.py:6070`: `(user.phone, user.postal_code, user.state) == ('5592999990000', '69057000', 'AM')` e `cpf == '98765432100'`; `tests.py:6082`: `cnpj == '98765432000190'` | ✅ PASS |
| ACC-09 | E-mail em outra caixa ignorado | `tests.py:6091`: `(user.email, user.first_name) == ('nova@example.com', 'Trocado')` | ✅ PASS |
| ACC-10 | 400 `email-change-unsupported`, nada gravado | `tests.py:6101`: `assert_problem(..., 'email-change-unsupported', ...)` e `_rows == before`; também `tests.py:5748` (anterior) | ✅ PASS |
| ACC-11 | 409 `phone-taken`, nada gravado | `tests.py:5828` (anterior): `assert_problem(response, 'phone-taken', detail=...)` e `(phone, first_name) == ('5592991234567', 'Nova')` | ✅ PASS. O mutante M12 é equivalente (ver Sensor). |
| ACC-12 | Conta pendente substituída (`AdminDeleteUser` e depois as linhas), telefone gravado | `tests.py:5857`: `admin_delete_user` com `['pendente@example.com']`, fora de `fake.users`, linha apagada, `phone == '5592977776666'` | ✅ PASS |
| ACC-13 | 503 `auth-unavailable` ou 429 `too-many-requests`, as duas contas intactas | `tests.py:5871`: `assert_auth_unavailable` / `assert_throttled`, pendente ainda com o telefone e no pool, usuário com `('5592991234567', 'Nova')` | ✅ PASS |
| ACC-14 | `IntegrityError` → 409 `phone-taken`, não 500 | `tests.py:5887`: `patch.object(User, 'save', side_effect=IntegrityError)` → `assert_problem(..., 'phone-taken', ...)` e dados antigos | ✅ PASS |
| ACC-15 | Falha no perfil desfaz o `User`; o `GET` seguinte mostra o anterior | `tests.py:6134` (Customer) e `tests.py:6142` (Hairdresser): `internal-error`, e o `GET /api/users/me` devolve `('Nova', '12345678900')` / `('Nova', 'Cachos')` | ✅ PASS |
| ACC-34 | Sessão Google: apaga, 204, sem Cognito | `tests.py:5698` (anterior) e `tests.py:5714`: `204`, linhas apagadas, `max-age == 0` em `jwt` e `refresh_token`, `fake.calls == []` | ✅ PASS |
| ACC-35 | 200 `{"profile_picture": "<url nova>"}`, gravada pelo `WebPImageField` | `tests.py:6178`: nome `profile_pics/<pk>/nova.webp`, `response.json() == {'profile_picture': default_storage.url(name)}`, `stored_image(name).format == 'WEBP'` | ✅ PASS |
| ACC-36 | Arquivo anterior apagado depois do commit | `tests.py:6189`: com `captureOnCommitCallbacks(execute=False)` o antigo ainda existe; depois dos callbacks some, e o novo existe | ✅ PASS |
| ACC-37 | 400 `invalid-image`, foto e arquivo anteriores mantidos | `tests.py:6203`: `assert_problem(..., 'invalid-image', detail=...)` e `_assert_old_picture_kept()` | ✅ PASS |
| ACC-38 | 400 `validation-error` `#/profile_picture` sem o campo | `tests.py:6211` | ✅ PASS |
| ACC-39 | > 5 MiB → 400 `#/profile_picture`, nada gravado | `tests.py:6221`: `MAX_SIZE+1` bytes → `validation-error` com o pointer e a foto antiga mantida; exatamente `MAX_SIZE` segue para a conversão (`invalid-image`) | ✅ PASS |
| ACC-40 | `profile_picture` NULL, arquivo apagado depois do commit, 204, também sem foto | `tests.py:6245`: `204`, corpo vazio, `assertIsNone(...)`, arquivo apagado só depois dos callbacks; `tests.py:6258`: sem foto, `204`, `IsNone`, `storage.delete` não chamado | ✅ PASS |
| ACC-41 | 401 `invalid-session` em `PUT` e `DELETE` | `tests.py:6236` (PUT) e `tests.py:6270` (DELETE): `assert_problem(..., 'invalid-session')` e foto mantida | ✅ PASS |
| ACC-42 | RT-88/RT-89 na tabela, `profile-picture` entre os singulares | `backend/hairmatch/test_routes.py:64-65` e `:70`; `test_api_exposes_exactly_the_route_table` (`test_routes.py:102`); `tests.py:6280`: `GET` → 405 com `Allow` `['DELETE', 'OPTIONS', 'PUT']` | ✅ PASS |
| ACC-56 | Corpo que não é objeto JSON → 400 `malformed-request` | `tests.py:865` (anterior): `'{nope'` e `'[1]'` → `assert_problem(..., 'malformed-request')` | ✅ PASS |
| ACC-57 | `rating`, `role`, `cognito_sub`, `google_id` e `is_active` ignorados | `tests.py:6110`: a tupla dos cinco campos é igual à anterior, e `first_name == 'Trocado'`; também `tests.py:5789` | ✅ PASS |
| ACC-58 | Próprio telefone (mesmos dígitos) aceito sem validar o formato, valor gravado intacto | `tests.py:5896`: o gravado `'74 8985-0719'` enviado cru e só com dígitos → `200`, `(phone, first_name) == ('74 8985-0719', ...)`; `tests.py:5835` | ✅ PASS |
| ACC-60 | Falha depois da substituição: a pendente continua apagada, e a resposta é o erro da gravação | `tests.py:5907`: `internal-error`, a linha pendente não existe, fora do pool, telefone do usuário inalterado | ✅ PASS (o mutante extra M32, que move a substituição para dentro da transação da gravação, morre aqui) |

### App (sem suíte por decisão do spec: conferido por leitura, pendente de UAT no T21)

Caminhos relativos a `frontend-mobile/`.

| AC | Evidência (leitura) | Resultado |
| -- | ------------------- | --------- |
| ACC-16 | `hooks/accountHooks/useAccountForm.ts:19-28`: telefone sem o `55` e com máscara, documento com máscara pelo papel. `components/account/AccountSettingScreen.tsx:83`: e-mail com `editable={false}`. Não há campo de senha. | ⏳ pending UAT |
| ACC-17 | `useAccountForm.ts:32-41`: só o diff; `phone` como `` `55${phone}` ``; documento só com dígitos (`:40`) | ⏳ pending UAT |
| ACC-18 | `useAccountForm.ts:92-94`: `updateMe` → `loadSession()` → "Dados atualizados com sucesso." | ⏳ pending UAT |
| ACC-19 | `useAccountForm.ts:76-78`: diff vazio → "Nenhuma alteração para salvar." antes do `updateMe` | ⏳ pending UAT |
| ACC-20 | `useAccountForm.ts:81-86` e `utils/account-validation.ts:56-84`: marca o campo e mostra a primeira mensagem sem chamar a API. Valida só os campos alterados, como o ACC-20 diz desde o `1ec6d41` (`spec.md:108`). | ⏳ pending UAT |
| ACC-21 | `useAccountForm.ts:95-97`: `problemMessage(error, ...)`, e os valores ficam (sem reset no erro) | ⏳ pending UAT |
| ACC-22 | `useAccountForm.ts:73` (`savingRef`); `AccountSettingScreen.tsx:100-102`: `disabled={saving}` e `ActivityIndicator` | ⏳ pending UAT |
| ACC-23 | `components/account/AddressSettingScreen.tsx:57` (CEP primeiro, `maxLength 9`); `hooks/accountHooks/useAddressForm.ts:22`: `formatCEP` | ⏳ pending UAT |
| ACC-24 | `useAddressForm.ts:104-111` (consulta com 8 dígitos) e `:81-101` (merge; número e complemento nunca são tocados). O campo que a resposta não traz mantém o valor gravado (`:91`) e só é apagado se foi a consulta anterior que o escreveu (`:88-89`), como o ACC-24 diz desde o `1ec6d41` (`spec.md:124`). | ⏳ pending UAT |
| ACC-25 | `hooks/authHooks/useCepLookup.ts:22-23` (slug `postal-code-not-found` → `cep_not_found`, senão `cep_lookup_failed`); `AddressSettingScreen.tsx:66`; os campos ficam destravados | ⏳ pending UAT |
| ACC-26 | `useAddressForm.ts:32-42` (diff, CEP só com dígitos `:35`) e `:135-137` (`loadSession` → "Endereço atualizado com sucesso.") | ⏳ pending UAT |
| ACC-27 | `useAddressForm.ts:117-144` (sem mudança, validação, erro, `savingRef`); `AddressSettingScreen.tsx` com `disabled={saving}` e indicador | ⏳ pending UAT |
| ACC-28 | `app/(app)/customer/profile.tsx:116` e `app/(app)/hairdresser/profile/settings.tsx:105`: "Excluir conta" | ⏳ pending UAT |
| ACC-29 | `hooks/accountHooks/useDeleteAccount.ts:8-9` e `:48`: os textos exatos, e o do cabeleireiro concatenado | ⏳ pending UAT |
| ACC-30 | `useDeleteAccount.ts:25`: `deletingRef` barra o segundo toque | ⏳ pending UAT |
| ACC-31 | `useDeleteAccount.ts:41-42`: `router.replace('/(auth)/login')` e `clearSession()`; `app/_layout.tsx:142-145`: `clearSession` só zera o estado, sem requisição | ⏳ pending UAT |
| ACC-32 | `customer/profile.tsx:32`, `hairdresser/profile/settings.tsx:19`, `hairdresser/profile/index.tsx:13`: `return null` depois de todos os hooks (a ordem dos hooks foi conferida). As telas `configs` leem com `?.`. | ⏳ pending UAT |
| ACC-33 | `useDeleteAccount.ts:30-36`: no erro, mantém a sessão e mostra `problemMessage` | ⏳ pending UAT |
| ACC-43 | `AccountSettingScreen.tsx:107-124`: "Escolher nova foto" e, só com foto (`:114`), "Remover foto" | ⏳ pending UAT |
| ACC-44 | `hooks/accountHooks/useProfilePicture.ts:48-66` (recorte `[1,1]`, `quality: 0.5` `:52`, multipart em `services/account.service.ts:33-46`) e `:30` (`loadSession`) | ⏳ pending UAT |
| ACC-45 | `useProfilePicture.ts:42-46`: permissão negada → a mensagem exata, `return` antes da API | ⏳ pending UAT |
| ACC-46 | `useProfilePicture.ts:68-71` → `removeProfilePicture` → `loadSession`; placeholder em `AccountSettingScreen.tsx:44-49` | ⏳ pending UAT |
| ACC-47 | `customer/profile.tsx:81` e `hairdresser/profile/settings.tsx:66` → `configs/preferencesSetting` | ⏳ pending UAT |
| ACC-48 | `hooks/accountHooks/usePreferencesSetting.ts:27-35`: 404 → `[]` (`toApiProblem(...).status`, preenchido em `utils/api-problem.ts:153-162`; o backend responde problem+json `not-found`, `backend/preferences/views.py:47-49`) | ⏳ pending UAT |
| ACC-49 | `usePreferencesSetting.ts:71-83`: só `assign` das adicionadas e `unassign` das removidas | ⏳ pending UAT |
| ACC-50 | `usePreferencesSetting.ts:85` | ⏳ pending UAT |
| ACC-51 | `usePreferencesSetting.ts:86-95`: mensagem e recarga do servidor | ⏳ pending UAT |
| ACC-52 | `usePreferencesSetting.ts:49-53` e `:107`: mensagem e `saveDisabled`. Também desabilita quando a lista do usuário falha com status diferente de 404 (superconjunto seguro). | ⏳ pending UAT |
| ACC-53 | `hairdresser/profile/settings.tsx:73` → `app/(app)/hairdresser/configs/resumeSetting.tsx` (multiline, valor inicial `userInfo.hairdresser.resume`) | ⏳ pending UAT |
| ACC-54 | `resumeSetting.tsx:39` (`maxLength`) e `:42` (`{count}/1000`); `hooks/accountHooks/useResumeForm.ts:28` (corta no limite) | ⏳ pending UAT |
| ACC-55 | `useResumeForm.ts:34-56`: `updateMe({ resume })`, `loadSession`, as mensagens do ACC-18 e do ACC-19, erro com `problemMessage` e `savingRef` | ⏳ pending UAT |
| ACC-59 | Sem mudança. Segue o interceptor de refresh atual (`services/axios-instance.ts:23-60`). | ⏳ pending UAT |

**Status**: ✅ Os 28 ACs de backend estão cobertos e batem com o resultado do spec. As 3 lacunas de precisão do spec da rodada 1 foram resolvidas no `1ec6d41`. Os ACs de app aguardam o T21.

---

## Discrimination Sensor

**Rodada 2** (HEAD `1ec6d41`): um scratch novo (`git worktree add --detach <scratchpad>/sensor-120 HEAD`). As 32 mutações da rodada 1 rodaram de novo, mais a M02b, uma por vez em `views.py` e restauradas antes da próxima. Cada uma rodou contra `ProfileUpdateValidationTest`, `UpdateProfilePhoneTest`, `ProfilePictureViewTest`, `CognitoDeleteAccountTest`, `UserInfoCookieViewTest` e `UpdateProfileEmailTest`: 58 testes, todos verdes sem mutação. O banco foi `hairmatch_wt120v`, com `--keepdb`.

| # | AC | Mutação (em `views.py`) | Morto por | Resultado |
| - | -- | ----------------------- | --------- | --------- |
| M01 | ACC-01 | `if not value:` depois do `strip()` → `if False:` | `test_an_empty_blank_or_non_string...` (`tests.py:5957`) | ✅ Killed |
| M02 | ACC-01 | `value is None` em campo obrigatório → grava `None` em vez de recusar | `tests.py:5957` (subTest `None`) | ✅ Killed na rodada 2. Na rodada 1 sobreviveu: a sonda mostrou `{"first_name": null}` saindo de 400 `validation-error` para 409 `phone-taken`. |
| M02b | ACC-01 | ramo `value is None` removido (o `null` passa a dar "must be a string") | `tests.py:5957` | ✅ Killed (nova na rodada 2) |
| M03 | ACC-02 | `len(value) > limit` → `> limit + 1` | `tests.py:5967` | ✅ Killed |
| M04 | ACC-03 | `55[0-9]{10,11}` → `{10,12}` | `tests.py:5985` | ✅ Killed |
| M05 | ACC-04 | `len != 8` → `< 8` | `tests.py:6001` | ✅ Killed |
| M06 | ACC-05 | `[A-Za-z]{2}` → `{2,}` | `tests.py:6010`, `:6060` | ✅ Killed |
| M07 | ACC-06 | tamanho do CNPJ 14 → 13 | `tests.py:6027`, `:6082` | ✅ Killed |
| M08 | ACC-07 | `len(resume) > 1000` → `>=` | `tests.py:6050` | ✅ Killed |
| M09 | ACC-08 | sem o `.upper()` da UF | `tests.py:6070` | ✅ Killed |
| M10 | ACC-08 | documento gravado com máscara | `tests.py:6070`, `:6082` | ✅ Killed |
| M11 | ACC-09 | e-mail comparado diferenciando maiúsculas | `tests.py:6091` | ✅ Killed |
| M12 | ACC-11 | checagem do titular ativo → `if False:` | (nenhum) | ⚪ Equivalente: `phone` é `unique=True`, e o `save` levanta `IntegrityError` dentro do `atomic`. O resultado é o mesmo 409 `phone-taken`, sem gravar nada, como `tests.py:5828` afirma. |
| M13 | ACC-12 | `holders.exclude(_PENDING_ACCOUNT)` → `holders` (pendente dá 409) | `tests.py:5857`, `:5871`, `:5907` | ✅ Killed |
| M14 | ACC-13 | `except CognitoError` → `pass` | `tests.py:5871` | ✅ Killed |
| M15 | ACC-14 | `except IntegrityError` → outra exceção | `tests.py:5887` | ✅ Killed |
| M16 | ACC-15 | `transaction.atomic()` → `nullcontext()` | `tests.py:6134`, `:6142` | ✅ Killed |
| M17 | ACC-58 | atalho do próprio telefone → `if False:` | `tests.py:5896` | ✅ Killed |
| M18 | ACC-57 | `rating` lido do corpo | `tests.py:6110` | ✅ Killed |
| M19 | ACC-35 | `PUT` responde o nome antigo | `tests.py:6178` | ✅ Killed |
| M20 | ACC-36 | arquivo antigo apagado antes do commit (sem `on_commit`) | `tests.py:6189` | ✅ Killed |
| M21 | ACC-36 | arquivo antigo nunca apagado | `tests.py:6189` | ✅ Killed |
| M22 | ACC-37 | `except InvalidImage` → outra exceção | `tests.py:6203`, `:6221` | ✅ Killed |
| M23 | ACC-38 | campo ausente não recusado | `tests.py:6211` | ✅ Killed |
| M24 | ACC-39 | `size > 5 MiB` → `>=` | `tests.py:6221` | ✅ Killed |
| M25 | ACC-39 | limite de tamanho removido | `tests.py:6221` | ✅ Killed |
| M26 | ACC-40 | `DELETE` grava `''` em vez de NULL | `tests.py:6245` | ✅ Killed |
| M27 | ACC-40 | `DELETE` nunca apaga o arquivo | `tests.py:6245` | ✅ Killed |
| M28 | ACC-41 | `PUT` sem checar a sessão | `tests.py:6236` | ✅ Killed |
| M29 | ACC-34 | `_delete_account` sem limpar os cookies | `tests.py:5714` (e o anterior do Cognito) | ✅ Killed |
| M30 | ACC-12 | substituição da pendente pulada | `tests.py:5857`, `:5871`, `:5907` | ✅ Killed |
| M31 | ACC-41 | `DELETE` sem checar a sessão | `tests.py:6270` | ✅ Killed |
| M32 | ACC-60 | substituição movida para dentro do `atomic` da gravação | `tests.py:5907` (e `:5871`) | ✅ Killed |

Mutações descartadas de propósito:
- A guarda `old_name != new_name` do `PUT` não tem AC (ver Code Quality).
- O `if old_name:` do `DELETE` não muda o resultado do ACC-40, porque o NULL já está gravado.

**Sensor depth**: expandido (P0: mutação de conta, apagar arquivo, transações). 33 mutações.
**Result**: 32 killed, 0 survived, 1 equivalent (M12). Todas as mortes da rodada 1 continuam valendo.

**Isolamento**: nas duas rodadas, o `git status --porcelain` da árvore real antes do sensor e depois do `worktree remove --force` + `worktree prune` é o mesmo. Rodada 1: `?? frontend-mobile/eslint.config.js`. Rodada 2: esse arquivo mais `?? .specs/features/account-settings/validation.md`. Os worktrees 104 e 113 continuam listados. O banco de teste `hairmatch_wt120v` ficou (`--keepdb`) e não foi apagado.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code / sem scope creep | ✅ Telas compartilhadas em `components/account/`, um serviço só e nenhuma env var ou migração nova. |
| Surgical changes | ✅ Os arquivos de rota ficaram com uma linha; os menus só ganharam os itens. |
| Matches patterns | ✅ `body_error`/`validation_problem`, `_replace_pending_account`, `_delete_stored_files` e `on_commit`, como no cadastro. |
| Spec-anchored outcome check | ✅ Os valores afirmados batem com o spec, incluindo o `null` do ACC-01 desde a rodada 2. |
| Per-layer coverage (backend: happy, edge e erro por rota) | ✅ Completa. |
| Every test maps to a requirement | ✅ Cada teste novo cita o ACC na docstring. `test_a_landline_phone...` é a borda válida do ACC-03. |
| Guidelines | none (nenhum `AGENTS.md`/`CONTRIBUTING.md`); defaults fortes aplicados. Gate do app = `tsc` + eslint, como o spec decide. |

Observações que não bloqueiam:
1. ~~Comentário errado na guarda do `PUT`~~: resolvido no `da0b892` (`views.py:858-859`). Agora diz o motivo real, o caso em que o objeto antigo já sumiu do bucket. A guarda em si (`views.py:860`) sempre esteve certa.
2. **`except IntegrityError` → `phone-taken` pega tudo** (`views.py:827-829`).
   - Hoje nenhum caminho chega a uma falha de integridade que não seja o telefone: todo NOT NULL é validado antes, e `cpf`/`cnpj` não são únicos.
   - Mas qualquer regressão na validação viraria um 409 enganoso, e não um 500 (foi o que o M02 mostrou na rodada 1; o teste do `null` agora a pega).
   - Opcional: conferir a constraint (`'phone' in str(err)`) antes de responder `phone-taken`.
3. **A troca de foto descarta edições não salvas na tela de conta.**
   - O `useProfilePicture` chama `loadSession()` (`useProfilePicture.ts:30`). O `useAccountForm` recomeça do novo `userInfo` sempre que o perfil muda (`useAccountForm.ts:57-63`) e perde o nome ou telefone digitado e ainda não salvo.
   - Nenhum AC protege isso (o ACC-21 só cobre o erro do `PATCH`, e a Assumption "Sair sem salvar" fala de sair da tela). Fica como observação para o UAT.
4. O "Salvar" das preferências também fica desabilitado quando a lista do usuário falha com status diferente de 404 (`usePreferencesSetting.ts:43-53`). É um superconjunto seguro do ACC-52.
5. `experience_years` continua sem validação (fora do escopo, registrado no design).

---

## Edge Cases

- [x] ACC-56 (corpo que não é objeto): `tests.py:865`.
- [x] ACC-57 (campos alheios ignorados): `tests.py:6110`.
- [x] ACC-58 (próprio telefone cru): `tests.py:5896`.
- [x] ACC-60 (falha depois da substituição): `tests.py:5907`, e o M32 morre.
- [ ] ACC-59 (sessão expira na tela): sem mudança de código, pendente de UAT.
- [x] Imagem corrompida → `invalid-image`: `tests.py:6203` (bytes que não são imagem) e `:6221` (5 MiB de zeros).
- Ramos sem AC próprio: `complement`/`number` como `''` ou `None` respondem 200 e gravam (os campos são `null=True`, conferido por sonda). `number` inteiro responde 400. Nenhum deles é lacuna.

---

## Gate Check

- **Backend (Full, na árvore real, container isolado `bt.sh 120`)**: rodada 2 (HEAD `1ec6d41`): `python manage.py test --noinput` → `Ran 756 tests`, `OK`, `EXIT=0`. `makemigrations --check --dry-run` → `No changes detected` (`MIG=0`). A rodada 1 deu o mesmo resultado em `3115e11`.
- **Test count**: `git grep -c "def test_"` em `backend` dá 724 em `develop` e 758 em `HEAD` (+34). `git diff develop..HEAD -- backend | grep -c '^-\s*def test_'` = 0: nenhum teste removido. Executados: 722 → 756.
- **Skipped**: nenhum.
- **Spec**: `validate_spec.py --root <worktree> account-settings` → 0 erros e 0 avisos (rodada 2, depois do `1ec6d41`).
- **App**: `npx tsc --noEmit` → exit 0 nas duas rodadas (com as rotas tipadas geradas em `.expo/types/router.d.ts`). Não houve mudança de app na rodada 2. `npx eslint <23 arquivos de app alterados>` → 0 erros e 14 warnings.
  - Os 14 warnings estão em `customer/profile.tsx`, `hairdresser/profile/index.tsx`, `hairdresser/profile/settings.tsx` e `_layout.tsx`.
  - O conjunto é idêntico ao da versão de `develop` desses arquivos (`git show develop:<arquivo> | npx eslint --stdin`). Os arquivos novos não têm nenhum warning.

---

## Fix Plans

Nenhum aberto. Os da rodada 1 estão fechados:
- **Fix 1** (ACC-01, `null` sem teste): `d93ec31`. O M02 morre (`tests.py:5960-5961`).
- **Fix 2** (comentário da guarda do `PUT`): `da0b892` (`views.py:858-859`).
- **Spec**: `1ec6d41` resolve as 3 lacunas de precisão (pointers, ACC-20 e ACC-24).

Opcional, sem bloquear: conferir a constraint antes de responder `phone-taken` no `except IntegrityError` (Code Quality 2).

---

## Requirement Traceability Update

O Verifier não editou o `spec.md` (ele não muda a árvore real). Status proposto:

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| ACC-01 a ACC-15, ACC-34 a ACC-42, ACC-56 a ACC-58, ACC-60 | Implementing | ✅ Verified |
| ACC-16 a ACC-33, ACC-43 a ACC-55 | Implementing | ⏳ Implementing (conferido por leitura; Verified só depois do UAT do T21) |
| ACC-59 | Pending | ⏳ Pending (UAT) |

---

## Summary

**Overall**: ✅ Ready, falta só o UAT. O backend está verificado. Os ACs de app foram conferidos por leitura e esperam o T21 (UAT no web e no Android, do usuário).

**Spec-anchored check**: 28 de 28 ACs de backend batem com o resultado do spec. As lacunas de precisão do spec foram resolvidas no `1ec6d41`.
**Sensor**: 33 mutações, 32 mortas, 0 sobreviventes, 1 equivalente (M12).
**Gate**: 756 testes, 0 falhas, `makemigrations` limpo, `validate_spec` 0, `tsc` 0 e eslint com 0 erros.

**What works**:
- Validação e normalização do `PATCH`, incluindo o `null`.
- Conflito de telefone, com substituição da pendente e corrida tratada.
- Gravação atômica.
- `PUT`/`DELETE` da foto, com apagamento no `on_commit` e limite de 5 MiB.
- Exclusão Google limpando os cookies.
- Route Table.
- No app: as seis telas e os hooks conferem com os ACs por leitura.

**Observações que não bloqueiam**:
- O `except IntegrityError` → `phone-taken` pega tudo (`views.py:827-829`).
- Trocar a foto descarta as edições não salvas da tela de conta (`useAccountForm.ts:57-63`). Fica como observação de UAT.

**Next steps**: o T21 (UAT), com estes itens a mais:
- Um CEP de cidade inteira mantém o logradouro e o bairro gravados (ACC-24).
- Trocar a foto com uma edição não salva na tela de conta.

Depois do UAT, marcar ACC-16 a ACC-33, ACC-43 a ACC-55 e ACC-59 como Verified.
