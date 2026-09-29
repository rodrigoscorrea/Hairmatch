# Autenticação por e-mail e senha via AWS Cognito Specification

**Issue:** [#139](https://github.com/rodrigoscorrea/Hairmatch/issues/139) · [Refactor] Troca do sistema de autenticação proprietário para AWS Cognito
**Escopo:** Complex (auth + chamada externa + persistência + transição de estado + dev env novo)
**Plataformas:** backend Django, app (web e Android) e ambiente local (docker compose)

## Problem Statement

Hoje o Hairmatch autentica e-mail e senha por conta própria:
- O backend guarda um hash bcrypt em `User.password`.
- A sessão é um JWT HS256 assinado com a chave fixa `'secret'`.
- O token é decodificado à mão em 13 pontos de quatro apps (`users`, `availability`, `review`, `preferences`). Um token com assinatura inválida derruba a maioria desses pontos com erro 500.

A issue #139 pede que a autenticação local passe para o AWS Cognito, com JWT, para tirar do time o custo e o risco de manter senhas e sessões. O login Google (#106) continua como está, e o app se adapta ao novo contrato. Localmente, a nuvem roda no LocalStack. A exceção é o Cognito, que não entra na licença `freemium` do LocalStack e por isso roda no MiniStack.

## Goals

- [ ] Nenhuma senha é guardada nem comparada no backend. Cadastro, login, troca de senha e exclusão de conta por e-mail/senha passam pelo Cognito.
- [ ] Todo endpoint protegido autentica por um único componente central, que aceita o access token do Cognito e a sessão própria das contas Google, e nunca responde 500 por token ruim.
- [ ] O app mantém o usuário logado além dos 60 minutos do access token (refresh transparente) e continua funcionando no web e no Android.
- [ ] `docker compose up` sobe o Cognito local (MiniStack) já configurado, e o seed cria cabeleireiros que conseguem fazer login.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| "Esqueci minha senha" (ForgotPassword/ConfirmForgotPassword) | Não pedido na issue. Hoje não há tela nem endpoint para isso. É uma feature separada. |
| Confirmação de e-mail por código na UI | Decisão desta feature: auto-confirmação via `AdminConfirmSignUp` (ver Assumptions). |
| Troca de e-mail da conta | Exige verificar o novo e-mail no Cognito. O endpoint passa a recusar a troca (COG-37). |
| Federar o Google no Cognito (Hosted UI) | Decisão do usuário: o fluxo do #106 fica igual e mantém sessão própria. |
| Migrar os hashes bcrypt existentes | Decisão do usuário: contas antigas são descartadas e o banco é re-seedado. |
| Provisionar o user pool real na AWS (IaC, console) | É um passo operacional. O design documenta a configuração exigida. |
| Autenticar `reserve`, `agenda`, `service` e os endpoints sem cookie de hoje | Esses endpoints já não autenticam hoje. Protegê-los muda o contrato do app e fica para outra issue. |
| Refresh da sessão Google | A sessão Google continua com 60 minutos e sem refresh, como hoje. Ao expirar, o app volta ao login. |
| MFA, login por telefone (RF3), grupos do Cognito | Não pedidos. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Onde fica a integração | O backend faz proxy do Cognito via boto3. O app continua mandando e-mail/senha ao Django, e os tokens vão para cookies httpOnly. | Escolha do usuário. Segue a preferência por boto3 direto, dá para mockar no CI (que não tem LocalStack) e muda pouco o app. | y |
| Sessão das contas Google | O fluxo do #106 não muda. O backend emite a própria sessão só para contas Google (HS256, `settings.SECRET_KEY`, `iss="hairmatch"`, `token_use="session"`). | Escolha do usuário. Supera o AD-001 (ver AD-004). | y |
| Contas e-mail/senha existentes | Não há migração. Os dados atuais são descartados e o banco é re-seedado. O reset do banco do Render é passo operacional e exige autorização explícita. | Escolha do usuário. Os dados atuais são de teste. | y |
| Cognito local | MiniStack (`ministackorg/ministack`) só para `cognito-idp`. S3 e SES continuam no LocalStack. | Escolha do usuário. A licença `freemium` do LocalStack não inclui o Cognito (conferido no log de ativação do container). | y |
| Confirmação de e-mail no cadastro | O backend chama `AdminConfirmSignUp` logo após o `SignUp`. Não há tela de código. | Mantém o wizard atual sem etapa nova. O Cognito continua sendo a fonte das credenciais. | n (assumido; o usuário pode corrigir) |
| Onde ficam os tokens | Cookie `jwt` com o AccessToken (httpOnly, `samesite=None`, `secure`, `max_age=3600`). Cookie `refresh_token` com o RefreshToken (mesmos atributos, `path=/api/auth/`, `max_age=2592000`, 30 dias). O IdToken não é usado. | Mantém o nome `jwt` que o app, os testes e o `GET /api/auth/user` já usam. O refresh token não sai para as outras rotas. | n |
| Contrato de falha de autenticação | Token ausente, inválido ou expirado em endpoint protegido responde **401** `{"error": "Sessão inválida ou expirada."}`. O 403 fica para falta de permissão. | O app precisa de um sinal único para disparar o refresh. Hoje a mistura de 403 e 500 impede isso. Os testes que afirmam 403 nesses casos passam a afirmar 401. | n |
| Política de senha | Mínimo 8 caracteres, com maiúscula, minúscula e número, sem exigir símbolo. Vale no pool local e no pool real. | Igual à validação que o app já faz (`frontend-mobile/utils/forms.ts:1-8`). A política padrão do Cognito exige símbolo e recusaria senhas que o app aceita. | n |
| Senha enviada ao Cognito | Exatamente como digitada. O `replace(' ', '')` do cadastro atual é removido. | Hoje o cadastro tira espaços e o login não, e isso quebra senhas com espaço. | n |
| Identificador do usuário no Cognito | Pool com `UsernameAttributes=["email"]` e `CaseSensitive=false`. O vínculo com o Postgres é `User.cognito_sub`, igual ao `sub` do Cognito. | O `sub` é imutável. O e-mail pode diferir em maiúsculas. | n |
| IDs do pool e do client | Env vars `COGNITO_USER_POOL_ID` e `COGNITO_APP_CLIENT_ID`. Vazias em dev: o backend busca o pool `hairmatch-dev` e o client `hairmatch-backend` pelo nome. | O MiniStack não aceita ID fixo. Em produção, os IDs vêm do env, sem busca. São as duas únicas env vars novas. | n |
| Endpoint do Cognito em dev | `AWS_ENDPOINT_URL_COGNITO_IDENTITY_PROVIDER=http://ministack:4566`, definido no `docker-compose.yml`, e não no `.env`. | O boto3 lê o endpoint por serviço nativamente. O `AWS_ENDPOINT_URL` genérico continua apontando o S3 para o LocalStack. | n |
| Senha do seed | `Senha123` para todos os cabeleireiros do seed | Atende a política. A senha atual `senha123` não atende, e hoje nem funciona (hash PBKDF2 contra bcrypt). | n |
| Mensagens de erro | Em português, no campo `error` do JSON, como nas views atuais | Mantém o contrato que o `ErrorModal` exibe. | n |
| Testes do app | Só teste manual. O gate do app é `npx tsc --noEmit` mais o roteiro de UAT. | O app não tem nenhum teste hoje. Mesma decisão do #106. | y (herdado do #106) |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## User Stories

### P1: Cognito no ambiente local ⭐ MVP

**User Story**: Como dev do Hairmatch, quero que o `docker compose up` suba um Cognito local já configurado para rodar e testar a autenticação sem conta paga.

**Why P1**: Sem isso, nenhum outro critério roda fora dos testes com fake.

**Acceptance Criteria**:
1. **COG-01** WHEN `docker compose -f docker/docker-compose.yml --env-file docker/.env up` sobe o ambiente THEN o serviço `ministack` SHALL ter um user pool `hairmatch-dev` (`UsernameAttributes=["email"]`, `CaseSensitive=false`, política da seção Assumptions) e um app client `hairmatch-backend` (sem secret, com `ALLOW_USER_PASSWORD_AUTH` e `ALLOW_REFRESH_TOKEN_AUTH`, access token de 60 min e refresh de 30 dias), criados por um script de init idempotente.
2. **COG-02** WHEN o container `ministack` reinicia THEN o pool, o client, os usuários e a chave de assinatura SHALL continuar os mesmos (`PERSIST_STATE=1` com volume nomeado), e o script de init SHALL não criar um segundo pool.
3. **COG-03** WHERE `COGNITO_USER_POOL_ID` e `COGNITO_APP_CLIENT_ID` estão vazias o backend SHALL resolver os IDs buscando o pool `hairmatch-dev` e o client `hairmatch-backend` pelo nome. WHERE estão definidas, SHALL usá-las sem nenhuma chamada de listagem.
4. The backend SHALL enviar as chamadas do Cognito ao endpoint de `AWS_ENDPOINT_URL_COGNITO_IDENTITY_PROVIDER` quando ele está definido, enquanto o S3 continua no endpoint do LocalStack. **(COG-04)**

**Independent Test**: subir o compose, rodar `aws --endpoint-url http://localhost:4567 cognito-idp list-user-pools --max-results 10` e ver exatamente um `hairmatch-dev`. Reiniciar o `ministack` e ver o mesmo `Id`.

---

### P1: Cadastro por e-mail e senha no Cognito ⭐ MVP

**User Story**: Como cliente ou cabeleireiro novo, quero me cadastrar com e-mail e senha como hoje, com a senha guardada pelo Cognito, e não pelo Hairmatch.

**Why P1**: É metade do fluxo local que a issue manda substituir.

**Acceptance Criteria**:
1. **COG-05** WHEN `POST /api/auth/register` sem `google_signup_token` recebe `role`, `email`, `password`, `phone` e os campos de perfil válidos THEN o backend SHALL:
   - chamar `SignUp` (`Username=email`, `Password` exatamente como recebida, atributo `email`) e depois `AdminConfirmSignUp`;
   - criar em uma transação o `User` (`cognito_sub` = `UserSub`, `password` nulo) e o `Customer` ou `Hairdresser`;
   - responder 201 com `{"message": "<role> user registered successfully"}` e sem cookie.
2. The backend SHALL nunca gravar hash de senha nem comparar senha localmente. Todo `User` criado por e-mail/senha tem `password` nulo, e `bcrypt` sai das dependências. **(COG-06)**
3. **COG-07** WHEN o e-mail ou o telefone já existe no Postgres, ou falta `role`, `email`, `password` ou `phone`, ou o telefone tem menos de 10 dígitos THEN o backend SHALL responder com o status e a mensagem de hoje (409 ou 400) sem chamar o Cognito.
4. **COG-08** IF o Cognito recusa a senha (`InvalidPasswordException`) THEN o backend SHALL responder 400 com `{"error": "A senha deve ter ao menos 8 caracteres, com letra maiúscula, letra minúscula e número."}` e não criar nenhuma linha.
5. **COG-09** IF o Cognito responde `UsernameExistsException` THEN o backend SHALL responder 409 com `{"error": "Usuário já está cadastrado na nossa base de dados"}` e não criar nenhuma linha.
6. **COG-10** IF qualquer erro ocorre depois que o `SignUp` teve sucesso (`AdminConfirmSignUp`, foto inválida, JSON de preferências inválido ou falha no insert) THEN o backend SHALL chamar `AdminDeleteUser` para aquele e-mail, desfazer a transação sem deixar `User`, `Customer`, `Hairdresser` nem vínculos de preferência, e responder com o status do erro original (400 para foto ou preferências, 500 para os demais).
7. **COG-11** WHEN o caminho Google do cadastro (`google_signup_token`) é usado THEN o backend SHALL se comportar como hoje (GAUTH-15 a GAUTH-23), sem nenhuma chamada ao Cognito.

**Independent Test**: com o compose no ar, cadastrar um cliente pelo wizard. O usuário aparece no `list-users` do pool, e a linha em `users_user` tem `cognito_sub` preenchido e `password` nulo. Nos testes, forçar erro no insert depois do `SignUp` e ver o `AdminDeleteUser` no fake.

---

### P1: Login por e-mail e senha no Cognito ⭐ MVP

**User Story**: Como usuário cadastrado por e-mail/senha, quero entrar como hoje, recebendo a sessão emitida pelo Cognito.

**Why P1**: É a outra metade do fluxo local.

**Acceptance Criteria**:
1. **COG-12** WHEN `POST /api/auth/login` recebe `email` e `password` corretos de uma conta Cognito THEN o backend SHALL:
   - chamar `InitiateAuth` com `USER_PASSWORD_AUTH`;
   - responder 200 com `{"message": "Login successful"}`;
   - definir o cookie `jwt` com o AccessToken e o cookie `refresh_token` com o RefreshToken, com os atributos da seção Assumptions.
2. **COG-13** IF o Cognito responde `NotAuthorizedException` ou `UserNotFoundException` THEN o backend SHALL responder 401 com `{"error": "E-mail ou senha inválidos."}` e não definir cookie.
3. **COG-14** IF existe um `User` com aquele e-mail, `google_id` preenchido e `cognito_sub` nulo THEN o backend SHALL responder 403 com `{"error": "Esta conta usa login com Google. Use o botão Entrar com Google."}` sem chamar o Cognito (preserva GAUTH-11).
4. **COG-15** IF o Cognito autentica, mas nenhum `User` tem `cognito_sub` igual ao `sub` do token THEN o backend SHALL responder 401 com `{"error": "E-mail ou senha inválidos."}` e não definir cookie.
5. **COG-16** IF o corpo não traz `email` ou `password`, ou algum deles é vazio THEN o backend SHALL responder 400 com `{"error": "Informe e-mail e senha."}` sem chamar o Cognito.

**Independent Test**: logar no app com o cliente recém-cadastrado e cair na home. Nos testes, o login com o fake devolve dois cookies, e o `jwt` é aceito por `GET /api/auth/user`.

---

### P1: Autenticador central nos endpoints protegidos ⭐ MVP

**User Story**: Como time do Hairmatch, quero que todo endpoint protegido valide a sessão em um único lugar, para não manter 13 cópias de decode com chave fixa.

**Why P1**: Sem ele, o token do Cognito não é aceito em nenhum endpoint, e o risco citado na issue continua.

**Acceptance Criteria**:
1. **COG-17** WHEN um endpoint protegido recebe no cookie `jwt` um token com todas as condições abaixo THEN o backend SHALL autenticar a requisição como o `User` com `cognito_sub == sub`:
   - assinatura RS256 válida por uma chave do JWKS do pool;
   - `iss == "https://cognito-idp.<região>.amazonaws.com/<pool_id>"`;
   - `token_use == "access"`;
   - `client_id` igual ao app client;
   - `exp` no futuro.
2. **COG-18** WHEN um endpoint protegido recebe no cookie `jwt` uma sessão Google válida (HS256 com `settings.SECRET_KEY`, `iss == "hairmatch"`, `token_use == "session"`, `exp` no futuro) THEN o backend SHALL autenticar a requisição como o `User` com `id` igual ao do token.
3. **COG-19** IF o cookie `jwt` falta, a assinatura é inválida, o token expirou, o `iss` ou o `client_id` não confere, o `token_use` é `id` ou `refresh`, o algoritmo não é o do emissor (HS256 com `iss` do Cognito, RS256 com `iss` hairmatch, `none`) ou o usuário não existe THEN o endpoint protegido SHALL responder 401 com `{"error": "Sessão inválida ou expirada."}` e nunca 500.
4. **COG-20** IF o token está no formato antigo (HS256 assinado com `'secret'`, payload `{id, exp, iat}`) ou é o `signup_token` do Google THEN o autenticador SHALL recusá-lo como em COG-19.
5. **COG-21** WHEN `GET /api/auth/user` é chamado THEN o backend SHALL responder 200 com `{"authenticated": true}` se o autenticador aceita o cookie `jwt`, e 200 com `{"authenticated": false}` em qualquer outro caso, inclusive com o `signup_token` no cookie (preserva GAUTH-14).
6. The backend SHALL autenticar pelo componente central, sem nenhum `jwt.decode` na view, estas rotas: **(COG-22)**
   - `PUT auth/change-password`;
   - `GET`/`PUT`/`DELETE user/authenticated`;
   - `POST availability/create`;
   - `POST review/register`, `PUT review/update/<id>` e `DELETE review/remove/<id>`;
   - `POST preferences/assign/cookie/<id>` e `POST preferences/unassign/<id>`.
7. **COG-23** IF o `kid` do token não está no JWKS em cache THEN o backend SHALL buscar o JWKS de novo uma única vez na requisição e, se o `kid` continuar ausente, responder 401 como em COG-19.
8. **COG-24** IF o JWKS não pode ser obtido (erro de rede ou resposta não-200) THEN o endpoint protegido SHALL responder 503 com `{"error": "Serviço de autenticação indisponível. Tente novamente em instantes."}`.

**Independent Test**: nos testes, cada rota de COG-22 aceita um access token assinado pela chave do fake, recusa com 401 um token assinado com `'secret'` e recusa um refresh token. No app, criar uma review e trocar uma preferência depois de logar por e-mail/senha e depois pelo Google.

---

### P1: Refresh e logout ⭐ MVP

**User Story**: Como usuário logado, quero continuar logado depois dos 60 minutos do access token e, ao sair, que a sessão seja revogada.

**Why P1**: O access token do Cognito dura 60 minutos. Sem refresh, o app deslogaria o usuário a cada hora.

**Acceptance Criteria**:
1. **COG-25** WHEN `POST /api/auth/refresh` recebe um cookie `refresh_token` válido THEN o backend SHALL chamar `InitiateAuth` com `REFRESH_TOKEN_AUTH`, responder 200 com `{"message": "Session refreshed"}` e definir um novo cookie `jwt`, mantendo o `refresh_token`.
2. **COG-26** IF `POST /api/auth/refresh` não recebe o cookie `refresh_token` THEN o backend SHALL responder 401 com `{"error": "Sessão expirada. Entre novamente."}` sem chamar o Cognito.
3. **COG-27** IF o Cognito recusa o refresh token (`NotAuthorizedException`) THEN o backend SHALL responder 401 com `{"error": "Sessão expirada. Entre novamente."}` e apagar os cookies `jwt` e `refresh_token`.
4. **COG-28** WHEN `POST /api/auth/logout` recebe o cookie `refresh_token` THEN o backend SHALL chamar `RevokeToken` com ele, apagar os cookies `jwt` e `refresh_token` e responder 200 com `{"message": "User logged out"}`.
5. **COG-29** IF o `RevokeToken` falha por qualquer motivo, ou não há cookie `refresh_token` (sessão Google) THEN `POST /api/auth/logout` SHALL mesmo assim apagar os dois cookies e responder 200 com `{"message": "User logged out"}`.

**Independent Test**: nos testes, o refresh com o fake devolve um `jwt` novo aceito por `GET /api/auth/user`, e depois do logout o mesmo refresh token recebe 401. No app, apagar o cookie `jwt` no DevTools, navegar e continuar logado.

---

### P1: Troca de senha e exclusão de conta ⭐ MVP

**User Story**: Como usuário de e-mail/senha, quero que trocar a senha ou apagar a conta aconteça também no Cognito, para as credenciais não ficarem órfãs.

**Why P1**: Os dois endpoints existentes mexem em `User.password` ou apagam só a linha do Postgres.

**Acceptance Criteria**:
1. **COG-30** WHEN `PUT /api/auth/change-password`, autenticado por access token do Cognito, recebe `{"old_password", "password"}` THEN o backend SHALL chamar `ChangePassword` com o access token do cookie e responder 200 com `{"message": "Password updated successfully"}`, sem gravar nada em `User.password`.
2. **COG-31** IF o Cognito recusa a senha atual (`NotAuthorizedException`) THEN o backend SHALL responder 400 com `{"error": "Senha atual incorreta."}`.
3. **COG-32** IF a nova senha não atende à política (`InvalidPasswordException`) THEN o backend SHALL responder 400 com a mensagem de COG-08.
4. **COG-33** IF falta `old_password` ou `password` THEN o backend SHALL responder 400 com `{"error": "Informe a senha atual e a nova senha."}` sem chamar o Cognito.
5. **COG-34** IF a requisição está autenticada por sessão Google THEN `PUT /api/auth/change-password` SHALL responder 403 com `{"error": "Esta conta usa login com Google e não tem senha."}`.
6. **COG-35** WHEN `DELETE /api/user/authenticated` é chamado por um usuário com `cognito_sub` THEN o backend SHALL chamar `AdminDeleteUser` e só então apagar o `User`, apagar os cookies `jwt` e `refresh_token` e responder 200 com `{"message": "user deleted"}`. `UserNotFoundException` do Cognito conta como sucesso.
7. **COG-36** WHEN `DELETE /api/user/<email>` apaga um usuário com `cognito_sub` THEN o backend SHALL chamar `AdminDeleteUser` antes de apagar o `User`, com a mesma regra de `UserNotFoundException`. IF o Cognito está indisponível THEN a rota SHALL responder 503 (COG-47) e manter o `User`.
8. **COG-37** IF o corpo de `PUT /api/user/authenticated` traz `email` diferente do e-mail atual THEN o backend SHALL responder 400 com `{"error": "A troca de e-mail não é suportada."}` e não alterar nenhum campo.

**Independent Test**: nos testes, trocar a senha e logar com a nova (fake). Apagar a conta e ver o usuário sumir do fake e do Postgres. Um `PUT` com outro e-mail responde 400.

---

### P1: Seed pelo caminho real ⭐ MVP

**User Story**: Como dev, quero que os cabeleireiros do seed existam no Cognito e consigam fazer login, criados pelo mesmo caminho de um cadastro real.

**Why P1**: O seed roda em todo boot do container (`backend/entrypoint.sh`). Sem isso, o ambiente local nasce sem nenhuma conta que faça login.

**Acceptance Criteria**:
1. **COG-38** WHEN `populate_hairdressers` cria um cabeleireiro THEN o command SHALL criar o usuário no Cognito pela mesma função de serviço usada pelo `RegisterView` (`SignUp` + `AdminConfirmSignUp`) com a senha `Senha123`, gravar o `cognito_sub` e deixar `password` nulo. `POST /api/auth/login` com aquele e-mail e `Senha123` SHALL responder 200.
2. **COG-39** WHEN o command roda e um cabeleireiro do seed (e-mail no padrão `hairdresser<N>_...`, `google_id` nulo) tem `cognito_sub` nulo, ou o Cognito não tem usuário com aquele e-mail (`AdminGetUser` → `UserNotFoundException`) THEN o command SHALL recriar o usuário no Cognito com `Senha123` e atualizar o `cognito_sub`, sem duplicar linhas no Postgres. Usuários fora desse padrão não são tocados.
3. **COG-40** WHEN o command roda de novo sem mudança no estado do Cognito THEN ele SHALL não criar usuário no Cognito, não alterar `cognito_sub` e terminar sem erro.

**Independent Test**: `docker compose up` com o banco limpo, depois login no app com um e-mail do seed e `Senha123`. Apagar o volume do `ministack`, reiniciar e logar de novo com o mesmo e-mail.

---

### P1: App em consonância com a nova sessão ⭐ MVP

**User Story**: Como usuário do app, quero não ser deslogado a cada hora e quero que sair da conta encerre a sessão de verdade.

**Why P1**: A issue pede que o frontend acompanhe a mudança, e o access token de 60 minutos exige refresh.

**Acceptance Criteria**:
1. **COG-41** WHEN uma chamada feita pelo `axiosInstance` recebe 401, e a rota não é `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout` nem `/api/auth/google` THEN o app SHALL chamar `POST /api/auth/refresh` uma vez e, se receber 200, repetir a chamada original uma única vez.
2. **COG-42** IF o refresh responde algo diferente de 2xx THEN o app SHALL limpar `userToken` e `userInfo` e navegar para `/(auth)/login` sem exibir o `ErrorModal`. Chamadas que recebem 401 ao mesmo tempo SHALL compartilhar uma única chamada de refresh.
3. **COG-43** WHEN o usuário confirma "Sair" THEN o app SHALL chamar `POST /api/auth/logout` pelo `axiosInstance` (com credenciais no web) e limpar o estado local mesmo se a chamada falhar.
4. The app SHALL fazer toda chamada a endpoint protegido pelo `axiosInstance`. Isso inclui `createReview`, `deleteReview` e o logout, e o `axios` cru deixa de ser usado para eles. **(COG-44)**

**Independent Test**: no web, logar, apagar só o cookie `jwt` no DevTools e abrir uma tela que chama `/api/user/authenticated`. A tela carrega, e a aba Network mostra um `/api/auth/refresh` seguido do retry. Apagar também o `refresh_token` e navegar: o app vai para o login.

---

### P2: Sessão restaurada ao abrir o app

**User Story**: Como usuário que já fez login, quero reabrir o app e continuar logado enquanto o refresh token for válido.

**Why P2**: Hoje a restauração no boot é código morto (o AsyncStorage nunca é gravado). O refresh token de 30 dias torna a restauração possível, mas o app funciona sem ela.

**Acceptance Criteria**:
1. **COG-45** WHEN o app inicia THEN ele SHALL chamar `loadSession()`. Se o resultado não é autenticado, SHALL chamar `POST /api/auth/refresh` e, se receber 200, chamar `loadSession()` de novo e ir para a home do papel. Caso contrário, SHALL ficar na tela de login. O bootstrap por `AsyncStorage` e `Bearer` é removido.
2. **COG-46** WHILE o bootstrap está em andamento o app SHALL manter `isLoading = true` e não renderizar a tela de login.

**Independent Test**: no web, logar, fechar a aba, abrir de novo e cair na home. No Android (APK), matar o app, abrir de novo e cair na home.

---

### P1: Falhas do Cognito (transversal) ⭐ MVP

**User Story**: Como usuário, quero uma mensagem clara quando o serviço de autenticação falhar, e não um erro 500 nem uma tela travada.

**Why P1**: Toda rota de auth passa a depender de um serviço externo.

**Acceptance Criteria**:
1. **COG-47** IF uma chamada ao Cognito falha por erro de conexão, timeout ou erro inesperado do serviço (`InternalErrorException` ou `ClientError` não mapeado) em qualquer endpoint THEN o backend SHALL responder 503 com `{"error": "Serviço de autenticação indisponível. Tente novamente em instantes."}` e não criar, alterar nem apagar linhas no Postgres.
2. **COG-48** IF o Cognito responde `TooManyRequestsException` ou `LimitExceededException` THEN o backend SHALL responder 429 com `{"error": "Muitas tentativas. Aguarde e tente novamente."}`.
3. The backend SHALL registrar em log (`logging`, nível WARNING) a operação e o código de erro de cada falha do Cognito, sem incluir senha, tokens nem o corpo da requisição. **(COG-49)**

**Independent Test**: nos testes, o fake configurado para levantar `EndpointConnectionError` gera 503 no cadastro, no login, no refresh, na troca de senha e na exclusão, e o `assertLogs` mostra a operação sem a senha.

---

## Edge Cases

- WHEN o e-mail do login difere só em maiúsculas do e-mail cadastrado THEN o Cognito SHALL autenticar (pool `CaseSensitive=false`), e o login SHALL seguir COG-12.
- IF o volume do MiniStack é apagado e o Postgres mantém os usuários THEN o login desses usuários SHALL responder 401 (COG-13). O seed repara os cabeleireiros do seed (COG-39). Contas criadas à mão precisam ser recriadas, o que é aceito em dev.
- IF um access token é revogado por logout em outro aparelho THEN ele SHALL continuar aceito até expirar (≤ 60 min), porque a verificação é local via JWKS. Risco aceito e registrado no design.
- IF o cookie `jwt` traz um refresh token (`token_use == "refresh"`) THEN o autenticador SHALL recusá-lo (COG-19).
- IF um usuário Google chama `POST /api/auth/refresh` THEN SHALL receber 401 (COG-26), e o app SHALL voltar ao login (COG-42), como já acontece hoje quando a sessão expira.
- WHEN `PUT /api/user/authenticated` traz `email` igual ao atual THEN o backend SHALL processar os outros campos normalmente (COG-37 só vale para e-mail diferente).

---

## Implicit-Requirement Dimensions Sweep

| Dimension | Coverage |
| --------- | -------- |
| Input validation & bounds | COG-07, COG-08, COG-16, COG-32, COG-33, COG-37 |
| Failure / partial-failure states | COG-10 (compensação com `AdminDeleteUser`), COG-29, COG-35, COG-36, COG-47 |
| Idempotency / retry / duplicate handling | COG-02 e COG-40 (init e seed idempotentes), COG-09 (duplicado no Cognito), COG-41 (retry único) |
| Auth boundaries & rate limits | COG-17 a COG-22 e COG-34. Rate limit do Cognito em COG-48. Os endpoints sem auth de hoje ficam fora (Out of Scope). |
| Concurrency / ordering | COG-42 (refresh único para 401 concorrentes), COG-10 (ordem SignUp → insert → compensação), COG-35 (Cognito antes do Postgres) |
| Data lifecycle / expiry | Access token de 60 min, refresh de 30 dias (Assumptions), COG-27, COG-28, COG-35 |
| Observability | COG-49 |
| External-dependency failure | COG-24, COG-47, COG-48 |
| State-transition integrity | COG-05 (UNCONFIRMED → CONFIRMED na mesma requisição), COG-28 e COG-29 (logado → deslogado sempre concluído) |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| COG-01 | P1: Cognito local, AC1 | Tasks | Pending |
| COG-02 | P1: Cognito local, AC2 | Tasks | Pending |
| COG-03 | P1: Cognito local, AC3 | Tasks | Pending |
| COG-04 | P1: Cognito local, AC4 | Tasks | Pending |
| COG-05 | P1: Cadastro, AC1 | Tasks | Pending |
| COG-06 | P1: Cadastro, AC2 | Tasks | Pending |
| COG-07 | P1: Cadastro, AC3 | Tasks | Pending |
| COG-08 | P1: Cadastro, AC4 | Tasks | Pending |
| COG-09 | P1: Cadastro, AC5 | Tasks | Pending |
| COG-10 | P1: Cadastro, AC6 | Tasks | Pending |
| COG-11 | P1: Cadastro, AC7 | Tasks | Pending |
| COG-12 | P1: Login, AC1 | Tasks | Pending |
| COG-13 | P1: Login, AC2 | Tasks | Pending |
| COG-14 | P1: Login, AC3 | Tasks | Pending |
| COG-15 | P1: Login, AC4 | Tasks | Pending |
| COG-16 | P1: Login, AC5 | Tasks | Pending |
| COG-17 | P1: Autenticador, AC1 | Tasks | Pending |
| COG-18 | P1: Autenticador, AC2 | Tasks | Pending |
| COG-19 | P1: Autenticador, AC3 | Tasks | Pending |
| COG-20 | P1: Autenticador, AC4 | Tasks | Pending |
| COG-21 | P1: Autenticador, AC5 | Tasks | Pending |
| COG-22 | P1: Autenticador, AC6 | Tasks | Pending |
| COG-23 | P1: Autenticador, AC7 | Tasks | Pending |
| COG-24 | P1: Autenticador, AC8 | Tasks | Pending |
| COG-25 | P1: Refresh e logout, AC1 | Tasks | Pending |
| COG-26 | P1: Refresh e logout, AC2 | Tasks | Pending |
| COG-27 | P1: Refresh e logout, AC3 | Tasks | Pending |
| COG-28 | P1: Refresh e logout, AC4 | Tasks | Pending |
| COG-29 | P1: Refresh e logout, AC5 | Tasks | Pending |
| COG-30 | P1: Senha e conta, AC1 | Tasks | Pending |
| COG-31 | P1: Senha e conta, AC2 | Tasks | Pending |
| COG-32 | P1: Senha e conta, AC3 | Tasks | Pending |
| COG-33 | P1: Senha e conta, AC4 | Tasks | Pending |
| COG-34 | P1: Senha e conta, AC5 | Tasks | Pending |
| COG-35 | P1: Senha e conta, AC6 | Tasks | Pending |
| COG-36 | P1: Senha e conta, AC7 | Tasks | Pending |
| COG-37 | P1: Senha e conta, AC8 | Tasks | Pending |
| COG-38 | P1: Seed, AC1 | Tasks | Pending |
| COG-39 | P1: Seed, AC2 | Tasks | Pending |
| COG-40 | P1: Seed, AC3 | Tasks | Pending |
| COG-41 | P1: App, AC1 | Tasks | Pending |
| COG-42 | P1: App, AC2 | Tasks | Pending |
| COG-43 | P1: App, AC3 | Tasks | Pending |
| COG-44 | P1: App, AC4 | Tasks | Pending |
| COG-45 | P2: Sessão no boot, AC1 | Tasks | Pending |
| COG-46 | P2: Sessão no boot, AC2 | Tasks | Pending |
| COG-47 | P1: Falhas do Cognito, AC1 | Tasks | Pending |
| COG-48 | P1: Falhas do Cognito, AC2 | Tasks | Pending |
| COG-49 | P1: Falhas do Cognito, AC3 | Tasks | Pending |

**ID format:** `COG-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 49 total, 49 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] UAT manual no web e no Android, com cliente e cabeleireiro:
  - cadastro e login por e-mail/senha pelo Cognito (MiniStack);
  - login Google sem regressão;
  - refresh transparente depois de apagar o cookie `jwt`;
  - logout;
  - sessão restaurada ao reabrir o app.
- [ ] `grep -rn "jwt.decode" backend --include=*.py` fora de `.venv` e dos testes só encontra `users/authentication.py` e `users/auth_tokens.py`. `grep -rn bcrypt backend --include=*.py` fora de `.venv` não encontra nada.
- [ ] A suíte do backend (`coverage run manage.py test`) passa com pelo menos 330 testes, a baseline da `develop` em `b93baa5`. Nenhum teste é removido. Os testes que afirmavam 403 ou 500 para token ausente, inválido ou expirado passam a afirmar 401, conforme COG-19.
- [ ] Cada critério de backend (COG-03 a COG-40 e COG-47 a COG-49) tem pelo menos um teste automatizado que falha se o comportamento for removido.
