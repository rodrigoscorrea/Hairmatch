PASS

# Confirmação de e-mail no cadastro: Validation

**Result**: PASS (rodada 2 de 3, HEAD `004bc4b`)

**Data**: 2026-10-04
**Spec**: `.specs/features/email-confirmation/spec.md`
**Diff range**: `7815a19..HEAD` (HEAD = `c125c9c`, branch `141-confirmacao-de-email-para-criacao-de-conta-no-sistema`). O commit `50153e0` só traz docs de spec.
**Verifier**: sub-agent independente (autor diferente do verificador). Nada foi corrigido, commitado, empilhado ou staged. Este arquivo é o único arquivo criado na árvore real.

Convenção: `tests.py` = `backend/users/tests.py`. Todo `assert_problem(response, slug)` também confere o status HTTP do catálogo, o `Content-Type` e os membros do problem+json (`hairmatch/problem_testing.py:10-33`).

## Re-verificação, rodada 2 de 3 (HEAD = `004bc4b`)

**Veredicto atual: PASS.** O commit `004bc4b` só acrescenta 2 testes em `backend/chatbot/tests.py` (sem mudança de código de produção) e fecha as 2 lacunas da rodada 1.

| Lacuna da rodada 1 | Teste novo | Mutante | Resultado |
| ------------------ | ---------- | ------- | --------- |
| Busca por nome do chatbot (`chatbot/views.py:161`) | `chatbot/tests.py:404` `test_name_search_finds_an_active_hairdresser_and_never_a_pending_one` (ativo: `recommended_or_searched_hairdressers[...] == [hairdresser1.id]` e "Joana Silva" na mensagem; pendente: `None` e "Não encontrei nenhum cabeleireiro") | D1f (tira `is_active`) | Morto |
| Fallback do `except` da recomendação (`chatbot/ai_utils.py:110`) | `chatbot/tests.py:119` `test_the_fallback_after_an_error_skips_a_hairdresser_pending_email_confirmation` (`patch` de `Preferences.objects.filter` com exceção; só 'Joana') | D1c (tira `is_active`), D1g (`is_active=False`) | Mortos |

**Sensor da rodada 2:** 7 mutantes D1 na cópia (D1a, D1b, D1c, D1d, D1e, D1f, D1g), cada um com a suíte inteira (722 testes), um container por vez: **7 de 7 mortos**. Cada ponto do `is_active` do EMC-39 ampliado tem um teste que falha quando ele some: preferência (D1a), recomendação com combinação, sem lista e sem combinação (D1b, D1d, D1e), fallback (D1c, D1g) e busca por nome (D1f).

**Placar acumulado:** os 5 sobreviventes da rodada 0 (R15, E14, L04, X03, A02) e os 2 da rodada 1 (D1c, D1f) estão mortos, exceto os informativos. Sobram, sem exigir ação:
- **A02**: filtro `is_active` do caminho de sessão Google sem teste; fora do texto do EMC-27 e não explorável (conta pendente nunca recebe `google_id`).
- **D3c**: equivalente (tirar `database=` do `createcachetable` não muda nada com um banco só).
- **D4** (EMC-20 decide pelo código `NotAuthorizedException`, sem `AdminGetUser`) e **D5** (o `console.error("Full sign-up error:", error)` já existente em `useDescription.ts:111`; `registrationData.password` fica em memória até o grupo `(auth)` desmontar): aceitos como observação, sem mudar o veredicto.

**Gates da rodada 2:** `makemigrations --check` sem mudanças e **722 testes OK** no container de dev; `npx tsc --noEmit` exit 0; o baseline da cópia também deu 722 OK. `coverage run` não foi executado.

**Integridade de testes:** nenhum teste apagado ou alterado nesta rodada (só 29 linhas adicionadas).

**Isolamento:** `git status --porcelain` igual ao do início da rodada (já com `validation.md`). Cópia, container de teste e dump de env removidos, `git worktree prune` rodado.

**Resumo dos requisitos:** todo AC de backend (EMC-03 a EMC-39, 47 a 50, 52 a 55) tem asserção localizada e o resultado confere com a spec; nenhum mutante sobrevivente aponta asserção que falta; nenhum defeito real aberto. Fica manual: o UAT do T23 (web e Android), por decisão do usuário.

---

## Rodada 1 (histórico, HEAD = `49bec88`): FAIL por 2 lacunas

Correções `bf56350..49bec88` verificadas: R15 (`tests.py:4681`), E14 (teste do 503 vigia todos os loggers), L04 (login com outra caixa), X03 (teste da migração 0011), D3 (`MAX_ENTRIES=100000`, mutantes D3a e D3b mortos), D2 (corrida no cadastro: `views.py:281-286` e `:309`, mutantes D2a a D2g mortos pelos testes de `tests.py:4641-4679`), D1 em `preferences/views.py:69` e `chatbot/ai_utils.py`. Sobraram D1f (busca por nome do chatbot) e D1c (fallback da recomendação) sem teste, fechados na rodada 2. Gate da rodada: 720 testes OK, tsc exit 0. Mutantes: 21 rodados, 18 mortos, 3 vivos (D1c, D1f, D3c equivalente).

> As seções abaixo descrevem o estado da primeira verificação (HEAD `c125c9c`). O estado atual está nas rodadas 1 e 2 acima. Tudo que a primeira rodada marcou como sobrevivente, defeito ou "Needs Fix" foi corrigido, exceto os itens informativos A02, D4 e D5.

## Primeira rodada (histórico, HEAD = `c125c9c`)

## Por que FAIL (rodada 0)

Regra de veredicto: FAIL se um AC de backend não tem asserção, se um mutante sobrevivente aponta asserção que falta, ou se há defeito real.

1. Todo AC de backend tinha teste localizado (nenhum AC sem asserção). Mas o mutante **R15** sobrevivia e apontava uma asserção que faltava em um qualificador explícito dos ACs EMC-07/08/52/53. O mutante **E14** sobrevivia e apontava que o EMC-49 só vigiava o logger `users.cognito`.
2. Defeito real **D1**: cabeleireiro pendente ainda aparecia no chatbot e em `GET /api/preferences/{id}/users` (contradizia o Goal 1 da spec).
3. Defeito real **D2**: o Edge Case "dois cadastros ao mesmo tempo" tinha comportamento diferente da spec e nenhum teste.

## Task Completion

| Task | Status | Notas |
| ---- | ------ | ----- |
| T1 a T22 | Done | Um commit por tarefa em `7815a19..HEAD`; app e docs incluídos. |
| T23 (UAT manual) | Aberta de propósito | O usuário faz o UAT no web e no Android. |
| tasks.md / Traceability | Desatualizados | `tasks.md` ainda diz "Draft" e a Traceability do spec ainda diz "Implementing" (EMC-47 "Pending"). Não alterei, só este arquivo é permitido. |

## Spec-Anchored Acceptance Criteria (backend)

| AC | `file:line` + asserção | Resultado esperado pela spec | Resultado |
| -- | ---------------------- | ---------------------------- | --------- |
| EMC-03 | `tests.py:4327-4338` (`status==201`; `json()=={'message': '<role> user registered successfully','confirmation_required': True}`; `len(cookies)==0`; `user.cognito_sub==fake sub`; `assertFalse(user.is_active)`; fake `confirmed` False). `tests.py:4346` `assertNotIn('admin_confirm_sign_up', names)` | 201, corpo exato, sem cookie, só SignUp, `is_active=False` | Coberto |
| EMC-04 | `tests.py:4646-4648` (`calls==[]`, `cognito_sub` None, `is_active` True); `tests.py:2584-2586` | Google ativo, sem Cognito | Coberto |
| EMC-05 | `tests.py:4356-4358` (`assert_email_taken` 409 com detail, `calls==[]`, `User.count()==1`) com `A@X.com` sobre `a@x.com` ativo | 409 `email-taken`, sem Cognito | Coberto |
| EMC-06 | `tests.py:3204-3208` (40 ativos, `count('admin_confirm_sign_up')==40`, sem `confirm_sign_up`, login 200) | seed continua `sign_up_confirmed` | Coberto |
| EMC-07 | `tests.py:4506-4515` (201; 1 `User` iexact; e-mail novo; `cognito_sub` mudou; `index('admin_delete_user') < index('sign_up')`; `Customer.count()==1`) | AdminDelete do antigo antes do SignUp, cascata | Coberto. Gap leve: vínculos (preferências, reservas) não são asseridos |
| EMC-08 | `tests.py:4525-4528` (telefone mascarado; só `b@x.com` resta, no Postgres e no fake) | substitui por telefone com e-mail diferente | Coberto |
| EMC-09 | `tests.py:4538-4540` (`assert_phone_taken`, `calls==[]`); `tests.py:4551-4554` (pendente do e-mail intacto) | 409 `phone-taken` sem Cognito | Coberto |
| EMC-10 | `tests.py:4564-4572` (ordem `['sign_up','admin_delete_user','sign_up']`, sub novo); `tests.py:4582-4584` (409, 3 `sign_up`); `tests.py:4446-4447` (status CONFIRMED: 409) | repetir uma vez só se UNCONFIRMED e **nenhum `User` tem o e-mail** | Parcial. A precondição "nenhum User tem o e-mail" não existe no código nem em teste (D2) |
| EMC-11 | `tests.py:4594-4598` (`assert_auth_unavailable`; operações `['admin_delete_user']`; antigo mantido, no fake e no Postgres) | 503 e conta antiga intacta | Coberto |
| EMC-12 | `tests.py:4607-4609` (500 `internal-error`; `fake.users=={}`; sem linhas) | compensação COG-10, antiga continua apagada | Coberto |
| EMC-13 | `tests.py:4765-4769` (200; `{'message':'Email confirmed'}`; sem cookie; ativo; fake confirmado); `tests.py:4780-4781` (login 200 depois) | 200 + ativa | Coberto |
| EMC-14 | `tests.py:4787-4789` (`invalid-confirmation-code` com detail; inativo; fake não confirmado) | 400 e continua pendente | Coberto |
| EMC-15 | `tests.py:4797-4798` (`confirmation-code-expired`; inativo) | 400 `confirmation-code-expired` | Coberto |
| EMC-16 | `tests.py:4807-4810` (type/title/status/detail iguais ao de código errado; `calls==[]`); `tests.py:4818-4819` (conta Google) | mesmo corpo, sem Cognito | Coberto |
| EMC-17 | `tests.py:4838-4843` (8 corpos, `errors` com `pointer` por campo e detail; `calls==[]`) | 400 `validation-error` por campo | Coberto |
| EMC-18 | `tests.py:4861-4863` (200, corpo, `calls==[]`) | 200 sem Cognito | Coberto |
| EMC-19 | `tests.py:4870-4875` (3 códigos de pool; `assert_throttled`; inativo) | 429 `too-many-requests` | Coberto |
| EMC-20 | `tests.py:4883-4885` (200, corpo, ativo) | ativa a conta já confirmada no pool | Coberto |
| EMC-21 | `tests.py:4978-4993` (202; corpo; `Username` minúsculo; código novo; antigo vira `invalid-confirmation-code`; novo dá 200) | 202 + Resend | Coberto |
| EMC-22 | `tests.py:5016-5018` (inexistente, ativo e Google: 202, corpo, `calls==[]`) | 202 igual, sem Cognito | Coberto |
| EMC-23 | `tests.py:5026-5029` (`{}` e `''`: `validation-error`, pointer `#/email`; `calls==[]`) | 400 `/email` | Coberto |
| EMC-24 | `tests.py:5036-5038` (`LimitExceeded` e `TooManyRequests`: `assert_throttled`) | 429 | Coberto |
| EMC-25 | `tests.py:5213-5216` (UserNotConfirmed: 403 `email-not-confirmed`, sem cookie); `tests.py:5225-5228` (pool confirmado, `User` inativo: 403, sem cookie, sessão falsa) | 403, sem cookie | Coberto. Gap: caixa do e-mail no login (L04) |
| EMC-26 | `tests.py:5236-5238` (401 `invalid-credentials`) | 401 | Coberto |
| EMC-27 | `tests.py:5248-5250` (401 `invalid-session`; `session` false) | 401 `invalid-session` | Coberto |
| EMC-28 | `tests.py:4904-4907` (10x 400, 11ª `too-many-requests`, `Retry-After>0`, `calls==[]`) | 429 + Retry-After | Coberto |
| EMC-29 | `tests.py:4919-4923` (10 tentativas de 2 IPs, 11ª de um 3º IP: 429, `Retry-After`, `calls==[]`, inativo) | 429 por e-mail | Coberto |
| EMC-30 | `tests.py:5047-5050` | 429 na 11ª/hora/IP | Coberto |
| EMC-31 | `tests.py:5061-5064` (3x 202 com caixa/espaço/IP diferentes; 4ª 429; 3 Resend) | 429 na 4ª/hora/e-mail | Coberto |
| EMC-32 | `tests.py:4624-4628` (3x 201 de IPs trocando; 4ª 429, `Retry-After`, `calls==[]`); `tests.py:4316-4319` (10/h por IP continua) | 429 na 4ª | Coberto |
| EMC-33 | `hairmatch/tests.py:458-459` (`DatabaseCache`, tabela `hairmatch_cache`); `:467-470` (valor lido e `COUNT(*)==1` no banco) | cache no banco | Coberto. A migração 0011 não é exercitada (X03) |
| EMC-34 | `tests.py:3303-3305` (só a de 8 dias some); `tests.py:3315` (`AdminDeleteUser` com o e-mail); `tests.py:3328-3334` (falha do Cognito mantém a linha: Cognito antes do Postgres) | Cognito antes de apagar, 7 dias | Coberto |
| EMC-35 | `tests.py:3295-3305` (7 dias exatos, 1 h, ativa e Google ficam, no Postgres e no fake) | não toca nesses | Coberto |
| EMC-36 | `tests.py:3328-3334` (1 WARNING, id na mensagem, o outro foi apagado, exit 0) | mantém, WARNING com id, segue | Coberto |
| EMC-37 | `tests.py:3346-3353` (`['purge_unconfirmed_users deleted=1 kept=1']` em INFO, stdout, 2ª `kept=0`, 3ª `deleted=0 kept=0`) | INFO com contagem, 2ª execução apaga zero | Coberto |
| EMC-38 | `tests.py:3371` (`assertLess(index(migrate), index(purge))` lendo `entrypoint.sh`) | purge depois do migrate | Coberto só por leitura do script. Boot real é manual |
| EMC-39 | `tests.py:4700` (busca); `:4705-4707` (home por preferência); `:4719-4722` (for_you e por preferência); `:4731-4732` (pendente não ocupa vaga entre 10) | só o ativo, filtro antes do `[:10]` | Coberto. Mas ver D1 |
| EMC-47 | `hairmatch/test_problems.py:38` (`len(CATALOG)==39`); `:42-44` (slug, status e título dos 3) | 3 slugs com status/título | Coberto |
| EMC-48 | `tests.py:4932-4933` e `:4946-4947` (confirmação: 503, inativo); `:5070-5071` e `:5090-5091` (reenvio); `:4594-4598` (substituição) | 503 e sem alterar estado | Coberto. "Não apagar linhas" na confirmação não é asserido de forma explícita |
| EMC-49 | `tests.py:4934-4938` (1 WARNING com operação e `EndpointConnectionError`; sem código, sem e-mail); `tests.py:3875-3882` (serviço: operação + código de erro; sem código, senha, e-mail) | WARNING sem segredo | Coberto, mas fraco: só o logger `users.cognito` é vigiado (E14) |
| EMC-50 | `hairmatch/test_routes.py:61-62` + `:102-103` (`ROUTE_TABLE - found == []` e `found - ROUTE_TABLE == []`) | 2 rotas anônimas | Coberto |
| EMC-52 | `tests.py:2365-2372` (200 `signup_required`, `signup_token`, sem cookie, 0 `User`, sem `google_id`, fake vazio, operações `['admin_delete_user']`) | substitui sem vincular | Coberto |
| EMC-53 | `tests.py:2581-2589` (e-mail do token); `:2597-2600` (telefone); `:2610-2613` (ativo com o telefone: 409, `calls==[]`) | substitui e cria Google ativo | Coberto |
| EMC-54 | `tests.py:5079-5082` (202, corpo, ativo, `admin_get_user` chamado); `tests.py:5090-5091` (outro status: 503 e inativo) | ativa se CONFIRMED, senão 503 | Coberto |
| EMC-55 | `tests.py:2382-2388` (503, sem `jwt`, `google_id` None, ainda inativo, ainda no fake); `tests.py:2622-2626` | 503 e pendente intacto | Coberto |

**Status**: nenhum AC de backend sem asserção. Gaps de precisão e sobreviventes listados abaixo.

### Edge Cases

- [x] Confirmar com `A@X.com`: `tests.py:4887-4893` (200; o pool recebe `nova@example.com`).
- [x] Reenvio depois do código vencer: `tests.py:4995-5004` (fake emite código novo e o confirma).
- [x] Bot cadastra de novo sobre conta pendente: EMC-07 (`tests.py:4506-4515`); conta nova continua `is_active=False` (`:4511`).
- [x] Conta expurgada e confirmação: EMC-16 (`tests.py:4807-4810`).
- [x] Ativação por EMC-20/54: ativa, senha do cadastro pendente (comportamento do fake).
- [ ] Limite do emulador aceitar código errado (AD-005): não é testável no fake, documentado no README. Aceito.
- [ ] **Dois cadastros ao mesmo tempo**: sem teste, e o comportamento difere da spec (D2).
- [ ] Fechar o app na tela de confirmação: manual (app).

## Sensor de discriminação (mutation)

Escopo: cópia `git worktree` em `/tmp/claude-1000/mut/wt` (fora do repo), um container por vez com o recipe da memória. Baseline na cópia: 711 testes OK. Cada mutante rodou a suíte inteira (711 testes).

**Resultado: 94 mutantes injetados (92 em `mutate.py` + 2 do autenticador), 89 mortos, 5 sobreviventes.**

Áreas: RegisterView 17 (R01-R17), LoginView 4 (L01-L04), Google 6 (G01-G06), EmailConfirmationView 14 (E01-E14), ConfirmationCodeView 8 (C01-C08), throttles 13 (T01-T13), expurgo e entrypoint 11 (P01-P11), listagens 4 (Q01-Q04), CognitoService 9 (S01-S09), settings/migração/catálogo/rotas 6 (X01-X06), autenticador 2 (A01-A02). Os mutantes que "morreram" por erro de execução (por exemplo P11, X06) também contam como mortos: a suíte ficou vermelha.

Mortos incluem: R01 `is_active=True` no cadastro; R02 apaga Postgres antes do Cognito; R03/R04/R05/R06 checagens de e-mail e telefone; R07/R08/R09 retry do órfão (sem checar UNCONFIRMED, sem limite de uma repetição, sem apagar o órfão); R11 falha do Cognito engolida; R12 sem throttle por e-mail no cadastro; R13 cadastro volta a usar `sign_up_confirmed`; L01 sem bloqueio do `User` inativo; L02 `UserNotConfirmed` vira 401; L03 verifica pendência antes da senha; G01 vincula em vez de substituir; G02/G03/G04/G05/G06 variantes do Google; E01 a E13 (cada mapeamento de erro, 200 idempotente, mesmo corpo para e-mail desconhecido, AlreadyConfirmed ativa, remover `.strip()`, regex de 6 dígitos); C01 a C08 (sempre 202, ResendRejected e checagem de status); T01 a T13 (normalização da chave, e-mail em claro, escopo repetido, taxas, throttle removido de cada view); P01 a P11 (limite de 7 dias com `<=` e 6 dias, Postgres antes do Cognito, apagar mesmo com falha, filtros, log, contagem, entrypoint); Q01 a Q04 (filtro `is_active` nas 3 listagens e filtro depois do `[:10]`); S01 a S09 (mapeamentos do `CognitoService`, `admin_get_status`); X01/X02/X04/X05/X06 (CACHES, catálogo, rota); A01 (autenticador Cognito deixa de filtrar `is_active`).

### Sobreviventes

| Mutante | `file:line` | Falha injetada | AC que deveria matar | Observação |
| ------- | ----------- | -------------- | -------------------- | ---------- |
| R15 | `backend/users/views.py:164` | `_PENDING_ACCOUNT = Q(is_active=False)` (sem `cognito_sub__isnull=False`) | EMC-07, EMC-08, EMC-52, EMC-53 ("`is_active=False` **e `cognito_sub` preenchido**") | Nenhum teste cria um `User` inativo sem `cognito_sub` (Google, legado) com o e-mail ou telefone do cadastro. Com o mutante, essa conta seria apagada em vez de dar 409, e o login/confirmação/reenvio a tratariam como pendente. Falta uma asserção. |
| E14 | `backend/users/views.py:472` (início do `post` de `EmailConfirmationView`, antes de `confirmed = ...`) | `logger.warning('confirm code=%s', code)` | EMC-49 ("sem incluir o código de confirmação") | Os testes só usam `assertLogs('users.cognito')` (`tests.py:4929`); um log do código no logger `users.views` passa. |
| L04 | `backend/users/views.py:441` | barreira do login compara o e-mail com `email=` (sem `iexact`) | EMC-25 | O teste do pool confirmado/`User` inativo usa a mesma caixa do cadastro (`tests.py:5218-5228`). Com a falha, `PENDENTE@x.com` cairia em 401 `invalid-credentials` e o app não abriria a confirmação. |
| X03 | `backend/users/migrations/0011_create_cache_table.py:7` | a migração não cria a tabela | EMC-33 / Assumption da migração | O runner de teste do Django cria a tabela de cache sozinho (`Cache table 'hairmatch_cache' already exists`), então nenhum teste exercita a migração. Em dev ela está aplicada (`showmigrations`: `[X] 0011`). |
| A02 | `backend/users/authentication.py:130` | caminho de sessão Google deixa de filtrar `is_active` | fora do texto do EMC-27 (só cita o caminho Cognito, `:111`) | Defesa em profundidade. Conta pendente nunca recebe `google_id` (G01 morto), então não é explorável hoje. |

## Defeitos encontrados (leitura crítica + sondas na cópia)

**D1 (média): cabeleireiro pendente ainda aparece fora das 3 listagens do EMC-39.** O Goal 1 da spec diz que nenhuma conta pendente "aparece nas listagens". Sonda na cópia com um cabeleireiro `is_active=False`:
- `GET /api/preferences/{id}/users` (`backend/preferences/views.py:69`, `preference.users.filter(role='hairdresser')`) devolveu 200 com o pendente (`{'id': 1, 'first_name': 'Pendente', ...}`).
- `AiUtils.get_hairdressers_by_preferences` (`backend/chatbot/ai_utils.py:82,94,99,109`, `User.objects.filter(role='hairdresser')`, serializer completo) devolveu o pendente com ou sem preferências. O webhook `POST /api/chatbot/webhook` é anônimo.
O EMC-39 só enumera 3 listagens, então a spec também tem um furo. Correção sugerida: `is_active=True` nesses dois caminhos e ampliar o EMC-39.

**D2 (baixa a média): Edge Case "dois cadastros ao mesmo tempo" e precondição do EMC-10.** `RegisterView._sign_up` (`backend/users/views.py:293-304`) apaga o usuário UNCONFIRMED do pool e repete o SignUp sem checar se algum `User` tem aquele e-mail. A spec diz "nenhum `User` tem aquele e-mail" (EMC-10) e que o segundo cadastro recebe 409 `email-taken` pelo `unique` do Postgres. Sonda: o cadastro A já chamou SignUp e sua linha no Postgres entra entre o SignUp e o insert do cadastro B. Resultado observado (sonda): B responde **500 `internal-error`** (o `IntegrityError` cai no `except Exception`, `views.py:281-283`), e as operações foram `sign_up` (existe), `admin_get_user`, `admin_delete_user` (**apaga o usuário Cognito do A**), `sign_up`, `admin_delete_user`. Inferido, não observado (na sonda o insert do A ficou dentro da transação do B e foi revertido): numa corrida real o A ficaria com a linha no Postgres e sem usuário no Cognito, com código inútil, recuperável só cadastrando de novo (a substituição resolve). Sem teste para esse Edge Case.

**D3 (baixa, operacional): contagens de throttle podem ser descartadas pela poda do `DatabaseCache`.** `CACHES` não define `OPTIONS` (`backend/hairmatch/settings.py:220-227`), então valem `MAX_ENTRIES=300` e `CULL_FREQUENCY=3`. Pela fonte do Django (`DatabaseCache._cull`), acima de 300 linhas vivas ele apaga o terço de menor `cache_key`, ordem alfabética, sem olhar importância. A mesma tabela guarda o cache de CEP (`backend/users/cep_lookup.py:90-106`, 1 linha por CEP, TTL 24 h). Sob carga, contadores `throttle_confirm_*`, `throttle_login_*` e `throttle_register_*` (que ordenam antes de `throttle_resend_*`) podem sumir antes de vencer. Não é AC, mas enfraquece EMC-28 a EMC-33 em produção. Sugestão: `OPTIONS: {'MAX_ENTRIES': ...}` maior ou alias separado para o CEP.

**D4 (baixa, observação): EMC-20 decide só pelo código `NotAuthorizedException`.** `views.py:483-484` ativa o `User` sem conferir `AdminGetUser`, ao contrário do EMC-54, que confirma o status. A spec aceita ("porque a conta já está confirmada") e na prática esse código significa usuário já CONFIRMED no pool; só registro a diferença de tratamento.

**D5 (baixa, app, observação):**
- `frontend-mobile/hooks/authHooks/useDescription.ts:111` já tinha `console.error("Full sign-up error:", error)`, que loga o AxiosError inteiro (a `config.data` é o `FormData` com a senha). Não é do diff, mas a regra "senha nunca em log" não vale de fato enquanto isso existir.
- `RegistrationContext` limpa `pendingConfirmation` depois do código (`useConfirmEmail.ts:72`), mas `registrationData.password` (o wizard) só é limpo ao desmontar o grupo `(auth)`; no caminho de volta ao login ele continua em memória.
- Nada do app grava a senha em storage ou URL (`grep` de `AsyncStorage|SecureStore|localStorage` sem resultado). O parâmetro de rota `confirmed=1` não carrega dado.

**Não encontrado:** sessão para usuário inativo (barreira dupla: `LoginView` e `authenticate_token`; A01 e L01 mortos); Google vinculando a conta pendente (G01 morto); colisão de chave de throttle (T04 morto, escopos distintos); e-mail em claro na chave (hash SHA-256, T03 morto); vazamento de enumeração além do aceito (E03, E07, E08, C02, C05 mortos). A defesa `AnonRateThrottle` vale porque o DRF não tem autenticadores configurados: `request.user` é anônimo.

## Observações de spec e testes (não bloqueiam)

- Spec-precision: EMC-07 ("e, em cascata, o perfil e os vínculos") só asserida para o perfil. EMC-48 não define "não apagar linhas" para a confirmação.
- Observação: EMC-24 e EMC-54 deixam 429/503 só para contas pendentes, então distinguem pendente de inexistente. A spec aceita.
- `is_active=False` + `cognito_sub` é o único marcador de pendente. Uma conta desativada pelo admin do Django passaria a ser substituível, confirmável e expurgável. É consequência da decisão do design (não confirmada, Assumption 4).

## Infra, README e app (sem teste automatizado)

| AC | Verificação por leitura | Resultado |
| -- | ----------------------- | --------- |
| EMC-01 | `docker/ministack/init/01-cognito.sh`: `create` só se faltar, depois `update-user-pool` com `--auto-verified-attributes email`, política de senha e `--verification-message-template` (`CONFIRM_WITH_CODE`, assunto e corpo da spec); `update-user-pool-client` com `--prevent-user-existence-errors ENABLED` e o resto dos atributos. Leitura somente do MiniStack no ar: 1 pool, 1 client, `AutoVerifiedAttributes=["email"]`, template correto, política igual, `PreventUserExistenceErrors=ENABLED`. | Confere |
| EMC-02 | `GET http://localhost:4567/_ministack/ses/messages` (somente leitura) tem mensagens `CognitoVerificationMessage` com assunto "Hairmatch: confirme seu e-mail" e corpo "Seu código de confirmação do Hairmatch é 123456. Ele vale por 24 horas." | Confere (mensagens de uma execução anterior) |
| EMC-38 | `backend/entrypoint.sh` roda `purge_unconfirmed_users` depois do `migrate`; teste só lê o arquivo | Confere. Boot real: manual |
| EMC-40 | `useDescription.ts:107-108` e `usePreferences.ts:129-130`: `setPendingConfirmation({email, password})` e `router.replace('/(auth)/confirm-email')`, sem Alert; Google retorna antes | Confere |
| EMC-41 | `useLogin.ts:65-72`: slug `email-not-confirmed` guarda e-mail e senha e faz `router.push` sem `ErrorModal`; `_layout.tsx` expõe `slug` | Confere |
| EMC-42 | `useConfirmEmail.ts:53-82`: após 200, `clearPendingConfirmation()`, `signIn(email, password)`; sem senha ou se o login falha, vai a `/(auth)/login?confirmed=1`, que mostra "E-mail confirmado. Entre com sua senha." (`useLogin.ts:15`) | Confere |
| EMC-43 | `useConfirmEmail.ts:31` `canSubmit = code.length === 6 && ...`; `confirm-email.tsx` `disabled={!canSubmit}` | Confere |
| EMC-44 | `useConfirmEmail.ts:84-98` chama `resendConfirmationCode`, mostra `RESEND_NOTICE`, `cooldown=60` e `Reenviar código (${cooldown}s)` | Confere |
| EMC-45 | `problemMessage(error, ...)` no `ErrorModal`; mensagens dos 4 slugs em `utils/api-problem.ts` | Confere |
| EMC-46 | `services/auth-routes.ts` (2 rotas em `REFRESH_EXCLUDED`), `utils/api-problem.ts` (3 slugs em `ProblemSlug` e `PROBLEM_MESSAGES`) | Confere |
| EMC-51 | README: seção "E-mail confirmation" com leitura do código em dev (`/_ministack/ses/messages`, `123456`, limites do emulador) e "Before the launch" (`DEVELOPER`/`SourceArn`, sair do sandbox, `VerificationMessageTemplate`, `PreventUserExistenceErrors`, agendar o purge) | Confere |

**Fica manual (UAT do usuário, T23):** fluxo completo no web e no Android, com cliente e cabeleireiro: cadastro, e-mail no SES do MiniStack, código, home sem redigitar a senha; login de conta pendente; reenvio com contagem de 60 s; cabeleireiro pendente fora da busca; login Google e do seed sem regressão; log do boot com `purge_unconfirmed_users deleted=… kept=…`; Google com o e-mail de uma conta pendente cai no wizard Google.

## Gate

- `docker exec hairmatch_backend sh -c 'cd /app/backend && python manage.py makemigrations --check --dry-run && python manage.py test --noinput'`: **711 testes, OK, 0 falhas, 0 skips**; `makemigrations --check` sem mudanças.
- `cd frontend-mobile && npx tsc --noEmit`: **exit 0**.
- `coverage run` (Full gate do tasks.md) não foi executado; a suíte sem coverage passou.
- Critério "sem teste removido": baseline `7815a19` tem 619 `def test_`, HEAD tem 713 (711 executados). Nenhum teste foi apagado; 3 foram renomeados (abaixo).
- `grep -rn sign_up_confirmed backend --include=*.py` fora dos testes: só `users/cognito.py` e `users/management/commands/populate_hairdressers.py`.

### Integridade de testes pré-existentes (corpo alterado)

Linhas removidas: 7 em `backend/users/tests.py` e 4 em `backend/hairmatch/test_*.py` (2 em `test_problems.py`, 1 comentário em `test_routes.py`, 1 em `test_runner.py`), todas listadas abaixo. Todas as demais mudanças em testes pré-existentes só acrescentam `activate_account(...)` (35 linhas em `users`, `availability`, `preferences`, `review`) ou `cache.clear()` (6 linhas).

| Teste | Mudança | Julgamento |
| ----- | ------- | ---------- |
| `hairmatch/test_problems.py` `test_catalog_has_the_36_slugs_of_the_spec` | renomeado e `36 -> 39` | Permitido (EMC-47 mudou a spec) |
| `tests.py:4321` `test_customer_and_hairdresser_are_created_...` | renomeado para `..._pending_...`; corpo ganha `confirmation_required: True` e `assertFalse(is_active)`; `confirmed` `True -> False` | Permitido (EMC-03) |
| `tests.py:4480` `test_failed_confirmation_answers_503_...` | renomeado para `test_failed_sign_up_...`; `fail_next('admin_confirm_sign_up') -> 'sign_up'` | Permitido: o cadastro não chama mais `AdminConfirmSignUp`; a compensação de `sign_up_confirmed` segue testada em `tests.py:3684` (`test_failed_confirmation_deletes_the_user_and_propagates`) |
| `tests.py:4440` `test_email_that_only_exists_in_cognito_answers_409_...` | acrescenta `admin_confirm_sign_up` ao usuário órfão | Permitido (EMC-10: só UNCONFIRMED é repetido) |
| `tests.py:4639` `test_google_signup_makes_no_cognito_call` | acrescenta `assertTrue(is_active)` | Reforço |
| `tests.py` import | `populate_hairdressers` ganha `purge_unconfirmed_users` | Neutro |
| `hairmatch/test_runner.py` | `cache.clear()` só para testes com banco `default` | Infra de teste, necessária com `DatabaseCache`; não enfraquece asserção |

Nenhuma asserção foi enfraquecida.

## Isolamento

`git status --porcelain` antes e depois do sensor: idêntico (` M frontend-mobile/.env.example`, ` M frontend-mobile/services/axios-instance.ts`, `?? .specs/LESSONS.md`, `?? .specs/lessons.json`, `?? docs/requisitos-status.md`, `?? docs/security-audit/`, `?? docs/timezone/`). A cópia foi removida com `docker run ... rm -rf` e `git worktree prune`. Este `validation.md` é o único arquivo novo.

## Fix Plans sugeridos (para o orquestrador)

1. (D1) Filtrar `is_active=True` em `preferences/views.py:69` e em `chatbot/ai_utils.py` (4 consultas); ampliar o EMC-39 e testar os dois caminhos.
2. (R15) Teste: `User` inativo, sem `cognito_sub`, com o e-mail (e outro com o telefone) do cadastro e do cadastro Google: 409 e a linha continua. Teste de login/confirmação/reenvio com esse usuário: não é tratado como pendente.
3. (D2) Antes de apagar o UNCONFIRMED no `_sign_up`, exigir que nenhum `User` tenha o e-mail; mapear `IntegrityError` do e-mail para 409 `email-taken`; teste do Edge Case.
4. (E14) Teste de EMC-49 com `assertNoLogs`/`assertLogs` em `users.views` sem o código nem a senha.
5. (L04) Teste de login com o e-mail de conta pendente em outra caixa: 403.
6. (X03) Teste da migração 0011 (por exemplo `MigrationExecutor` com a tabela removida).
7. (D3) Definir `OPTIONS` do `CACHES` ou separar o cache de CEP.

## Requirement Traceability Update (proposto, spec.md não alterado)

| Requisito | Status atual | Proposto |
| --------- | ------------ | -------- |
| EMC-03 a EMC-06, EMC-11 a EMC-24, EMC-26 a EMC-37, EMC-39, EMC-47, EMC-48, EMC-50, EMC-54 | Implementing | Verified (testes e sensor) |
| EMC-07 a EMC-09, EMC-52, EMC-53, EMC-55 | Implementing | Needs Fix (R15 aponta asserção que falta) |
| EMC-10 | Implementing | Needs Fix (D2) |
| EMC-25 | Implementing | Verified com gap menor (L04) |
| EMC-49 | Implementing | Needs Fix (E14, asserção só no logger do serviço) |
| EMC-38, EMC-40 a EMC-46, EMC-51 | Implementing | Verificado por leitura; UAT manual pendente (T23) |
| EMC-01, EMC-02 | Verified | Confere (observado no MiniStack no ar) |

## Summary

**Overall (primeira rodada, HEAD `c125c9c`)**: Not Ready (FAIL). Veredicto atual: PASS (rodada 2).

**Spec-anchored check**: 45 de 45 ACs de backend com asserção localizada (EMC-03 a EMC-39, EMC-47 a EMC-50 e EMC-52 a EMC-55; EMC-38 só por leitura do script), 2 com gap parcial (EMC-10, EMC-49), 1 mutante de qualificador explícito sobrevivente (R15)
**Sensor**: 89 de 94 mutantes mortos, 5 sobreviventes (R15, E14, L04, X03, A02)
**Gate**: 711 testes OK, `tsc` exit 0

**O que funciona**: substituição de conta pendente em ordem Cognito-antes-do-Postgres (R02, R11 mortos), confirmação e reenvio sem enumeração além do aceito, throttle por IP e por e-mail com chave em hash, expurgo com limite de 7 dias e Cognito antes do Postgres, Google nunca herda conta pendente, login bloqueado em duas barreiras, listagens com filtro antes do `[:10]`.

**Próximos passos**: fix tasks 1 a 7 acima, depois re-verificar (iteração 1 de 3).
