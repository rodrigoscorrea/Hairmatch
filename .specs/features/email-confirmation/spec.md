# Confirmação de e-mail no cadastro Specification

**Issue:** [#141](https://github.com/rodrigoscorrea/Hairmatch/issues/141) · [Feature] Confirmação de email para criação de conta no sistema
**Escopo:** Complex (auth + chamada externa + transição de estado + rate limit + app + ambiente local)
**Plataformas:** backend Django, app (web e Android) e ambiente local (docker compose)

## Problem Statement

Hoje toda conta de e-mail/senha nasce confirmada:
- `CognitoService.sign_up_confirmed` (`backend/users/cognito.py:109-126`) chama `SignUp` e, em seguida, `AdminConfirmSignUp`.
- O código de verificação que o Cognito gera nunca é usado.

Por isso qualquer pessoa, ou bot, cria uma conta com um e-mail que não controla e ocupa esse e-mail e o telefone, que são únicos e respondem 409 para o dono real. Um cabeleireiro criado por bot também aparece nas listagens públicas.

A issue #141 pede que o cadastro só seja oficializado depois que o dono do e-mail o confirmar, tanto para cliente quanto para cabeleireiro. O usuário pediu que a confirmação use o Cognito e o SES da AWS e que o fluxo resista a cadastros em massa de bots. Isso revoga a assumption de auto-confirmação da feature `cognito-auth`, que estava marcada como não confirmada.

## Goals

- [ ] Nenhuma conta de e-mail/senha criada pelo cadastro consegue iniciar sessão nem aparecer nas listagens antes de confirmar o e-mail com o código enviado pelo Cognito.
- [ ] Uma conta não confirmada nunca bloqueia o dono real do e-mail ou do telefone. Um novo cadastro a substitui, e o expurgo a remove em 7 dias.
- [ ] As rotas anônimas que disparam e-mail ou validam código têm throttle por IP e por e-mail, e nenhuma delas revela se uma conta existe além do que o cadastro já revela.
- [ ] Em dev, `docker compose up` entrega o e-mail de verificação no SES embutido do MiniStack, e o fluxo completo roda no web e no Android.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Confirmação por link (no Cognito com `CONFIRM_WITH_LINK`, ou com link próprio enviado pelo backend) | Decisão do usuário: código de 6 dígitos, que é o fluxo nativo do Cognito. O link do Cognito exige um domínio no pool e abre uma página do `amazoncognito.com`, não o app, e o MiniStack não emula essa página. Diverge do texto da issue ("clicar no link") de propósito. |
| CAPTCHA, AWS WAF Bot Control e Cognito Threat Protection | Decisão do usuário: são pagos, ficam só em produção e não são emulados localmente. A defesa desta feature é a confirmação mais throttle. Ficam como ideia adiada. |
| Confirmação de e-mail para contas Google | O Google já verificou o e-mail (`email_verified` no ID token, GAUTH). O caminho `google_signup_token` não muda. |
| "Esqueci minha senha" | Feature separada, já registrada como ideia adiada na `cognito-auth`. |
| Provisionar o pool e o SES reais (console ou IaC) | É um passo operacional. O design e o README documentam a configuração exigida. |
| Agendar o expurgo em um cron hospedado (Render Cron Job) | Mexe em infraestrutura externa e exige autorização explícita. O command roda no boot e fica pronto para ser agendado. |
| Troca de e-mail da conta | Continua recusada (COG-37). |
| Bloquear reserva ou perfil por id de um cabeleireiro pendente | Um cabeleireiro pendente não loga, então não cadastra serviço nem disponibilidade, e por isso não pode ser reservado. Só as listagens são filtradas. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Mecanismo de confirmação | Código de 6 dígitos do Cognito: `ConfirmSignUp` para confirmar e `ResendConfirmationCode` para reenviar. O usuário digita o código numa tela do app. | Escolha do usuário. O Cognito controla a validade e o limite de tentativas, e o MiniStack já entrega o e-mail. | y |
| Conta não confirmada | Um novo cadastro com o mesmo e-mail ou telefone de uma conta pendente a substitui, no Cognito e no Postgres. O command `purge_unconfirmed_users` apaga as contas pendentes com mais de 7 dias. | Escolha do usuário. Evita que um bot ocupe o e-mail ou o telefone de outra pessoa. | y |
| Proteção anti-bot | Throttle por IP e por e-mail mais a confirmação. Nada pago. | Escolha do usuário. | y |
| Como o Postgres marca a conta pendente | `User.is_active=False` até a confirmação. Não há campo nem migração novos. | O autenticador já filtra `is_active=True` (`users/authentication.py:111,130`), então uma conta pendente nunca vira sessão. As contas atuais já têm `True`. | n |
| Bloqueio de login em dev | O backend recusa o login de um `User` inativo mesmo quando o Cognito autentica. | O MiniStack 1.5.18 não levanta `UserNotConfirmedException` no `InitiateAuth` e aceita qualquer código no `ConfirmSignUp`. O Postgres é a segunda barreira, e os erros de código são testados no fake. | n |
| Depois da confirmação | O app faz login sozinho com a senha que ficou em memória (wizard ou tela de login) e vai para a home do papel. Sem a senha em memória, vai para o login com aviso de sucesso. A senha nunca vai para URL, storage nem log. | Evita digitar a senha duas vezes. O endpoint de confirmação não emite sessão porque não recebe a senha. | n |
| Confirmação repetida | Conta já ativa responde 200 sem chamar o Cognito. | Duplo toque ou reenvio de formulário não deve virar erro. Revelar que um e-mail tem conta ativa não vaza mais do que o 409 `email-taken` do cadastro. | n |
| Enumeração | A confirmação de um e-mail sem conta pendente responde 400 `invalid-confirmation-code`, igual a código errado. O reenvio responde sempre 202 com a mesma mensagem. O client do Cognito tem `PreventUserExistenceErrors=ENABLED`. | Essas rotas são anônimas e não podem servir de oráculo de contas. | n |
| Limites de throttle | Confirmar: 10/min por IP e 10/hora por e-mail. Reenviar: 10/hora por IP e 3/hora por e-mail. Cadastrar: os 10/hora por IP atuais mais 3/hora por e-mail. | O limite por e-mail freia o spam contra uma vítima (cada cadastro ou reenvio dispara um e-mail pelo SES e gasta a reputação do remetente). O limite por IP freia a varredura. O Cognito tem o próprio limite de tentativas de código. | n |
| Onde ficam as contagens do throttle | `CACHES['default']` passa a ser `DatabaseCache` (tabela `hairmatch_cache`), criada por uma migração de `users` que chama `createcachetable`. | Hoje não há `CACHES`, então cada processo usa o próprio LocMemCache. As contagens somem a cada deploy e não são compartilhadas entre processos ou instâncias. O banco já existe, então não é preciso infraestrutura nova. A migração garante a tabela em qualquer ambiente que rode `migrate`. Sem a tabela, todo request com throttle (login, cadastro, CEP) quebraria. | n |
| Chave do throttle por e-mail | O e-mail do corpo, sem espaços nas pontas e em minúsculas. Sem e-mail no corpo, o throttle por e-mail não conta (a validação responde 400). | O pool tem `CaseSensitive=false`. `A@x.com` e `a@x.com` são a mesma conta e dividem o mesmo limite. | n |
| Prazo do expurgo | 7 dias contados de `User.date_joined`. | O código do Cognito vale 24 h e pode ser reenviado. Sete dias cobrem quem demora a abrir o e-mail sem deixar lixo por muito tempo. | n |
| Quando o expurgo roda | No `entrypoint.sh`, a cada boot, depois do `migrate`. | Não há cron no projeto. A substituição no cadastro já resolve o squatting na hora, e o expurgo é limpeza. | n |
| Validade do código | 24 h, regra fixa do Cognito. O reenvio gera um código novo. | Não é configurável no Cognito. | n |
| Texto do e-mail | Assunto "Hairmatch: confirme seu e-mail". Corpo "Seu código de confirmação do Hairmatch é {####}. Ele vale por 24 horas." Só texto, sem HTML. | Em pt-BR, como o app. Texto puro segue a regra da auditoria de não montar HTML. | n |
| E-mail em produção | O pool real usa `EmailConfiguration` com `EmailSendingAccount=DEVELOPER`, `SourceArn` de uma identidade SES verificada e `From` do Hairmatch. A conta SES sai do sandbox antes do lançamento. | Com `COGNITO_DEFAULT`, o e-mail não sai pelo SES do projeto e tem cota diária baixa (ver os limites do Cognito). No sandbox, o SES só entrega para endereços verificados. É passo operacional documentado. | n |
| Conta pendente e Google | O login e o cadastro Google nunca vinculam o `google_id` a uma conta pendente. A conta pendente com o mesmo e-mail ou telefone é substituída, como no cadastro por e-mail/senha. | Hoje o `GoogleAuthView` vincula o `google_id` a qualquer `User` com o mesmo e-mail (`users/views.py:421-428`). Uma conta pendente criada por bot seria herdada pela vítima, e a senha escolhida pelo bot passaria a valer se a conta fosse ativada. O Google já provou a posse do e-mail, então substituir é seguro. | n |
| Reenvio para conta confirmada no Cognito e inativa no Postgres | Se o `ResendConfirmationCode` falha com `InvalidParameterException`, o backend consulta `AdminGetUser`. Se o status for `CONFIRMED`, ativa o `User` e responde 202. | O Cognito recusa o reenvio para usuário já confirmado. O código exato (`InvalidParameterException`, "User is already confirmed.") **não foi conferido na AWS real**. Por isso a decisão se apoia no `AdminGetUser`, e não só no código de erro. | n |
| Telefone na substituição | A substituição vale quando o telefone (normalizado) pertence a uma conta pendente, mesmo que o e-mail seja outro. | O telefone também é único e pode ser ocupado por um bot. | n |
| Testes do app | Só teste manual. O gate do app é `npx tsc --noEmit` mais o UAT. | O app não tem testes automatizados. A decisão é herdada do #106 e do #139. | y (herdado) |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## User Stories

### P1: Cognito local envia o código ⭐ MVP

**User Story**: Como dev do Hairmatch, quero que o `docker compose up` deixe o pool local pronto para mandar o código de confirmação, e quero ler esse e-mail sem conta na AWS.

**Why P1**: Sem isso não há como testar o fluxo de ponta a ponta.

**Acceptance Criteria**:
1. **EMC-01** WHEN o script `docker/ministack/init/01-cognito.sh` roda, num pool novo ou num pool já existente THEN ele SHALL deixar o pool `hairmatch-dev` com estes atributos, e o client `hairmatch-backend` com `PreventUserExistenceErrors=ENABLED`, sem criar um segundo pool nem um segundo client:
   - `AutoVerifiedAttributes=["email"]`;
   - a política de senha atual;
   - `VerificationMessageTemplate` com `DefaultEmailOption=CONFIRM_WITH_CODE` e o assunto e o corpo da seção Assumptions.
2. **EMC-02** WHEN o backend cadastra uma conta de e-mail/senha em dev THEN o e-mail de verificação, com o texto da seção Assumptions, SHALL aparecer em `GET http://localhost:4567/_ministack/ses/messages`.

**Independent Test**: com o compose no ar, rodar `aws --endpoint-url http://localhost:4567 cognito-idp describe-user-pool` e ver o template. Cadastrar uma conta e ler o código em `/_ministack/ses/messages`.

---

### P1: Cadastro fica pendente ⭐ MVP

**User Story**: Como cliente ou cabeleireiro novo, quero que minha conta só passe a valer depois que eu provar que o e-mail é meu.

**Why P1**: É o pedido da issue.

**Acceptance Criteria**:
1. **EMC-03** WHEN `POST /api/users` sem `google_signup_token` recebe um cadastro válido THEN o backend SHALL:
   - chamar só o `SignUp` do Cognito, sem `AdminConfirmSignUp`;
   - criar o `User` com `is_active=False`, `cognito_sub` preenchido e o `Customer` ou `Hairdresser`;
   - responder 201 com `{"message": "<role> user registered successfully", "confirmation_required": true}`, sem cookie.
2. **EMC-04** WHEN `POST /api/users` recebe `google_signup_token` válido e nenhuma conta pendente conflita THEN o backend SHALL criar o `User` com `is_active=True` e se comportar como hoje (GAUTH-15 a GAUTH-23), sem chamar o Cognito.
3. **EMC-05** IF o e-mail do cadastro coincide, sem diferenciar maiúsculas, com o de um `User` ativo THEN o backend SHALL responder 409 `email-taken` sem chamar o Cognito.
4. **EMC-06** WHEN `populate_hairdressers` cria ou recria um cabeleireiro THEN o command SHALL continuar usando `sign_up_confirmed` (`SignUp` + `AdminConfirmSignUp`) e criar o `User` com `is_active=True`, e `POST /api/auth/login` com `Senha123` SHALL responder 200 (preserva COG-38 a COG-40).

**Independent Test**: cadastrar um cliente pelo wizard. O usuário aparece como `UNCONFIRMED` no `list-users` do pool, e a linha em `users_user` tem `is_active=false`. Logar com um cabeleireiro do seed continua funcionando.

---

### P1: Conta pendente não bloqueia o dono real ⭐ MVP

**User Story**: Como dono de um e-mail ou de um telefone que alguém cadastrou sem confirmar, quero conseguir me cadastrar mesmo assim.

**Why P1**: Sem isso, um bot ocupa o e-mail ou o telefone de qualquer pessoa.

**Acceptance Criteria**:
1. **EMC-07** WHEN `POST /api/users` (e-mail/senha) recebe um e-mail que coincide, sem diferenciar maiúsculas, com o de um `User` com `is_active=False` e `cognito_sub` preenchido THEN o backend SHALL chamar `AdminDeleteUser` para o e-mail antigo, apagar esse `User` (e, em cascata, o perfil e os vínculos) e seguir o cadastro novo como em EMC-03.
2. **EMC-08** WHEN o telefone normalizado do cadastro pertence a um `User` com `is_active=False` e `cognito_sub` preenchido THEN o backend SHALL substituir essa conta como em EMC-07, mesmo que o e-mail seja outro.
3. **EMC-09** IF o telefone normalizado pertence a um `User` ativo THEN o backend SHALL responder 409 `phone-taken` sem chamar o Cognito.
4. **EMC-10** IF o `SignUp` responde `UsernameExistsException`, nenhum `User` tem aquele e-mail e o `AdminGetUser` mostra `UserStatus=UNCONFIRMED` THEN o backend SHALL chamar `AdminDeleteUser` e repetir o `SignUp` uma única vez. Se o status for outro, ou a segunda tentativa falhar do mesmo jeito, SHALL responder 409 `email-taken`.
5. **EMC-11** IF o `AdminDeleteUser` da conta antiga falha por indisponibilidade do Cognito THEN o backend SHALL responder 503 `auth-unavailable` e manter a conta antiga intacta, no Cognito e no Postgres.
6. **EMC-12** IF o cadastro novo falha depois da substituição THEN o backend SHALL aplicar a compensação de COG-10, e a conta antiga SHALL continuar apagada.

**Independent Test**: nos testes, criar uma conta pendente com `a@x.com` e cadastrar de novo com `A@x.com`. Responde 201, há um único `User` com esse e-mail e o fake registra `admin_delete_user` antes do `sign_up`. Repetir com uma conta ativa: responde 409.

---

### P1: Google não herda conta pendente ⭐ MVP

**User Story**: Como dono de um e-mail Gmail que um bot cadastrou sem confirmar, quero entrar com o Google sem herdar a conta do bot.

**Why P1**: Sem isso, o Goal de "conta pendente nunca bloqueia o dono real" falha pelo caminho Google. O `GoogleAuthView` vincularia o `google_id` à conta do bot, e a sessão seria recusada porque a conta está inativa.

**Acceptance Criteria**:
1. **EMC-52** WHEN `POST /api/auth/google` recebe uma identidade Google válida cujo e-mail coincide (sem diferenciar maiúsculas) com o de um `User` com `is_active=False` e `cognito_sub` preenchido, e nenhum `User` tem aquele `google_id` THEN o backend SHALL chamar `AdminDeleteUser`, apagar esse `User` sem vincular o `google_id` e responder como para uma conta nova (200 com `signup_token`, GAUTH).
2. **EMC-53** WHEN `POST /api/users` com `google_signup_token` encontra o e-mail do token ou o telefone normalizado num `User` com `is_active=False` e `cognito_sub` preenchido THEN o backend SHALL substituir essa conta como em EMC-07 e criar a conta Google ativa (EMC-04).
3. **EMC-55** IF o `AdminDeleteUser` falha por indisponibilidade do Cognito em EMC-52 ou EMC-53 THEN o backend SHALL responder 503 `auth-unavailable` e manter a conta pendente intacta, sem vincular `google_id` nem criar `User`.

**Independent Test**: nos testes, criar uma conta pendente `ana@gmail.com` e chamar `POST /api/auth/google` com uma identidade desse e-mail (o mock atual de `verify_google_id_token`). Responde com `signup_token`, a conta pendente sumiu do fake e do Postgres, e nenhum `User` tem o `google_id`.

---

### P1: Confirmar o e-mail ⭐ MVP

**User Story**: Como usuário que acabou de se cadastrar, quero digitar o código que recebi e ter a conta ativada.

**Why P1**: É o passo que oficializa o cadastro.

**Acceptance Criteria**:
1. **EMC-13** WHEN `POST /api/auth/email-confirmations` recebe `{"email", "code"}` com o código certo de uma conta pendente THEN o backend SHALL chamar `ConfirmSignUp`, marcar o `User` com `is_active=True` e responder 200 com `{"message": "Email confirmed"}`, sem cookie.
2. **EMC-14** IF o Cognito responde `CodeMismatchException` THEN o backend SHALL responder 400 `invalid-confirmation-code` e manter `is_active=False`.
3. **EMC-15** IF o Cognito responde `ExpiredCodeException` THEN o backend SHALL responder 400 `confirmation-code-expired` e manter `is_active=False`.
4. **EMC-16** IF nenhum `User` com `cognito_sub` tem aquele e-mail (sem diferenciar maiúsculas) THEN o backend SHALL responder 400 `invalid-confirmation-code` sem chamar o Cognito, com o mesmo corpo de EMC-14 (exceto `instance`).
5. **EMC-17** IF falta `email` ou `code`, ou o `code` não tem exatamente 6 dígitos THEN o backend SHALL responder 400 `validation-error` com o `pointer` de cada campo inválido, sem chamar o Cognito.
6. **EMC-18** WHILE o `User` daquele e-mail já está ativo, `POST /api/auth/email-confirmations` SHALL responder 200 com `{"message": "Email confirmed"}` sem chamar o Cognito.
7. **EMC-19** IF o Cognito responde `TooManyFailedAttemptsException`, `LimitExceededException` ou `TooManyRequestsException` THEN o backend SHALL responder 429 `too-many-requests` e manter `is_active=False`.
8. **EMC-20** IF o `ConfirmSignUp` responde `NotAuthorizedException` porque a conta já está confirmada no Cognito, e o `User` ainda está inativo no Postgres THEN o backend SHALL marcar o `User` com `is_active=True` e responder 200 como em EMC-13.

**Independent Test**: nos testes, cadastrar, ler o código guardado no fake e confirmar. Responde 200, o `User` fica ativo e o login responde 200. Com um código errado, responde 400 e o login responde 403.

---

### P1: Reenviar o código ⭐ MVP

**User Story**: Como usuário que não recebeu o código, ou cujo código venceu, quero pedir outro.

**Why P1**: O código vale 24 h e o e-mail pode se perder. Sem reenvio, a conta só se recupera pela substituição.

**Acceptance Criteria**:
1. **EMC-21** WHEN `POST /api/auth/confirmation-codes` recebe `{"email"}` de uma conta pendente THEN o backend SHALL chamar `ResendConfirmationCode` e responder 202 com `{"message": "If the account is pending confirmation, a new code was sent"}`.
2. **EMC-22** IF o e-mail não pertence a nenhuma conta pendente (não existe, está ativo ou é conta Google) THEN o backend SHALL responder 202 com o mesmo corpo de EMC-21, sem chamar o Cognito.
3. **EMC-23** IF falta `email` THEN o backend SHALL responder 400 `validation-error` com `pointer` `/email`, sem chamar o Cognito.
4. **EMC-24** IF o Cognito responde `LimitExceededException` ou `TooManyRequestsException` THEN o backend SHALL responder 429 `too-many-requests`.
5. **EMC-54** IF o `ResendConfirmationCode` falha com `InvalidParameterException` e o `AdminGetUser` mostra `UserStatus=CONFIRMED` THEN o backend SHALL marcar o `User` com `is_active=True` e responder 202 com o corpo de EMC-21. Com qualquer outro status, SHALL responder 503 `auth-unavailable`.

**Independent Test**: nos testes, reenviar para uma conta pendente: responde 202 e o fake registra `resend_confirmation_code`. Reenviar para um e-mail inexistente: o corpo é idêntico e o fake não registra nada.

---

### P1: Login de conta pendente ⭐ MVP

**User Story**: Como usuário que se cadastrou e não confirmou, quero que o login me diga isso e me leve à confirmação, em vez de dizer que a senha está errada ou que o serviço caiu.

**Why P1**: Hoje o `UserNotConfirmedException` cai em 503 `auth-unavailable`.

**Acceptance Criteria**:
1. **EMC-25** IF `POST /api/auth/login` recebe a senha correta de uma conta pendente, seja porque o Cognito responde `UserNotConfirmedException`, seja porque o `User` está com `is_active=False` depois de o Cognito autenticar THEN o backend SHALL responder 403 `email-not-confirmed` e não definir cookie.
2. **EMC-26** IF `POST /api/auth/login` recebe a senha errada de uma conta pendente THEN o backend SHALL responder 401 `invalid-credentials`, como para qualquer conta (COG-13).
3. **EMC-27** IF um endpoint protegido recebe um access token válido cujo `sub` pertence a um `User` com `is_active=False` THEN o autenticador SHALL responder 401 `invalid-session` (invariante de `authentication.py:111`, que passa a ter teste).

**Independent Test**: nos testes, cadastrar e logar sem confirmar: responde 403 `email-not-confirmed` sem `Set-Cookie`. No MiniStack, o mesmo login responde 403.

---

### P1: Rate limit contra cadastro em massa ⭐ MVP

**User Story**: Como time do Hairmatch, quero que um bot não consiga criar contas em massa, adivinhar códigos nem usar o nosso SES para mandar spam a uma vítima.

**Why P1**: Pedido explícito do usuário. Cada cadastro e cada reenvio custam um e-mail do SES e afetam a reputação do remetente.

**Acceptance Criteria**:
1. **EMC-28** WHEN um mesmo IP faz a 11ª chamada em 1 minuto a `POST /api/auth/email-confirmations` THEN o backend SHALL responder 429 `too-many-requests` com `Retry-After`, sem chamar o Cognito.
2. **EMC-29** WHEN um mesmo e-mail (normalizado) recebe a 11ª tentativa de confirmação em 1 hora, vinda de qualquer IP THEN o backend SHALL responder 429 `too-many-requests` com `Retry-After`, sem chamar o Cognito.
3. **EMC-30** WHEN um mesmo IP faz a 11ª chamada em 1 hora a `POST /api/auth/confirmation-codes` THEN o backend SHALL responder 429 `too-many-requests` com `Retry-After`, sem chamar o Cognito.
4. **EMC-31** WHEN um mesmo e-mail (normalizado) recebe o 4º pedido de reenvio em 1 hora, vindo de qualquer IP THEN o backend SHALL responder 429 `too-many-requests` com `Retry-After`, sem chamar o Cognito.
5. **EMC-32** WHEN um mesmo e-mail (normalizado) recebe a 4ª tentativa de cadastro por e-mail/senha em 1 hora, vinda de qualquer IP THEN o backend SHALL responder 429 `too-many-requests` com `Retry-After`, sem chamar o Cognito. O limite de 10/hora por IP do `RegisterThrottle` continua valendo.
6. The backend SHALL guardar as contagens de throttle em um cache compartilhado por todos os processos (`DatabaseCache`), que sobrevive a um restart. **(EMC-33)**

**Independent Test**: nos testes, fazer quatro reenvios para `a@x.com` alternando `REMOTE_ADDR` entre dois IPs. O quarto responde 429 e o fake registra só três chamadas.

---

### P1: Expurgo de contas pendentes ⭐ MVP

**User Story**: Como time do Hairmatch, quero que contas nunca confirmadas sumam sozinhas, para não acumular lixo de bot no Cognito e no Postgres.

**Why P1**: Decisão do usuário. Complementa a substituição.

**Acceptance Criteria**:
1. **EMC-34** WHEN `python manage.py purge_unconfirmed_users` roda THEN o command SHALL, para cada `User` com `is_active=False`, `cognito_sub` preenchido e `date_joined` há mais de 7 dias, chamar `AdminDeleteUser` e só então apagar o `User`.
2. The command SHALL não tocar em `User` ativo, em `User` sem `cognito_sub` (Google) nem em `User` pendente com 7 dias ou menos. **(EMC-35)**
3. **EMC-36** IF o `AdminDeleteUser` de uma conta falha por indisponibilidade do Cognito THEN o command SHALL manter aquele `User`, registrar um WARNING com o id do usuário e seguir com os demais, terminando com exit 0.
4. **EMC-37** WHEN o command termina THEN ele SHALL registrar em INFO quantas contas apagou e quantas manteve por falha. Uma segunda execução sem contas elegíveis SHALL apagar zero contas.
5. **EMC-38** WHEN o container do backend sobe THEN o `entrypoint.sh` SHALL rodar `purge_unconfirmed_users` depois do `migrate`.

**Independent Test**: nos testes, criar três contas pendentes (8 dias, 7 dias e 1 hora) e uma ativa de 30 dias, e rodar `call_command`. Só a de 8 dias some, do fake e do Postgres.

---

### P1: Listagens sem cabeleireiro pendente ⭐ MVP

**User Story**: Como cliente, quero ver só cabeleireiros com cadastro oficializado.

**Why P1**: A issue diz que a conta só passa a valer na plataforma depois da confirmação. Hoje um cabeleireiro criado por bot aparece na busca.

**Acceptance Criteria**:
1. **EMC-39** WHEN a busca global (`GlobalSearchView`), a listagem por preferência ou a listagem "para você" monta a lista de cabeleireiros THEN o backend SHALL excluir todo `Hairdresser` cujo `user.is_active` é `False`. O mesmo vale para a listagem de cabeleireiros por preferência (`GET /api/preferences/{id}/users`) e para as listas do chatbot (busca por nome e recomendação por preferência). *(Ampliado depois da verificação: o Verificador achou essas listagens ainda mostrando a conta pendente.)*

**Independent Test**: nos testes, criar um cabeleireiro ativo e um pendente com o mesmo nome. A busca pelo nome devolve só o ativo, e o mesmo vale nas duas listagens.

---

### P1: App guia a confirmação ⭐ MVP

**User Story**: Como usuário do app, quero digitar o código logo depois do cadastro, ou depois de um login de conta pendente, e entrar sem redigitar a senha.

**Why P1**: O backend sozinho não fecha o fluxo para o usuário.

**Acceptance Criteria**:
1. **EMC-40** WHEN o cadastro por e-mail/senha recebe 201 com `confirmation_required: true` THEN o app SHALL guardar o e-mail e a senha só em memória (`RegistrationContext`) e navegar para `/(auth)/confirm-email`, sem o alert de hoje.
2. **EMC-41** WHEN o login recebe 403 `email-not-confirmed` THEN o app SHALL guardar o e-mail e a senha digitados só em memória e navegar para `/(auth)/confirm-email`, sem abrir o `ErrorModal`.
3. **EMC-42** WHEN o usuário envia, na tela de confirmação, um código de 6 dígitos e recebe 200 THEN o app SHALL chamar `signIn` com o e-mail e a senha em memória, limpar a senha da memória e deixar o `RootLayoutNav` levar à home do papel. Sem senha em memória, SHALL navegar para `/(auth)/login` com a mensagem "E-mail confirmado. Entre com sua senha."
4. **EMC-43** WHILE o campo de código não tem exatamente 6 dígitos, o app SHALL manter o botão "Confirmar" desabilitado.
5. **EMC-44** WHEN o usuário toca em "Reenviar código" THEN o app SHALL chamar `POST /api/auth/confirmation-codes`, mostrar "Se a conta estiver pendente, enviamos um novo código." e desabilitar o botão por 60 s, com contagem regressiva visível.
6. **EMC-45** IF a confirmação ou o reenvio respondem com problem+json THEN o app SHALL mostrar a mensagem em pt-BR do slug (`invalid-confirmation-code`, `confirmation-code-expired`, `too-many-requests`, `auth-unavailable`) no `ErrorModal`.
7. The app SHALL listar `POST /api/auth/email-confirmations` e `POST /api/auth/confirmation-codes` em `REFRESH_EXCLUDED` e trazer os três slugs novos em `ProblemSlug` e `PROBLEM_MESSAGES`. **(EMC-46)**

**Independent Test**: no web, cadastrar um cliente, ler o código em `/_ministack/ses/messages`, digitá-lo e cair na home do cliente. Repetir pelo login de uma conta pendente.

---

### P1: Contrato de erro e observabilidade ⭐ MVP

**User Story**: Como time do Hairmatch, quero que os erros novos sigam o contrato problem+json e que as falhas fiquem no log sem segredos.

**Why P1**: É o que o AD-006 exige para toda rota nova.

**Acceptance Criteria**:
1. The backend SHALL ter no `CATALOG` (e o spec `api-problem-details` na tabela) os slugs `email-not-confirmed` (403, "Email not confirmed"), `invalid-confirmation-code` (400, "Invalid confirmation code") e `confirmation-code-expired` (400, "Confirmation code expired"). **(EMC-47)**
2. **EMC-48** IF uma chamada ao Cognito de confirmação, reenvio ou substituição falha por conexão, timeout ou erro não mapeado THEN o backend SHALL responder 503 `auth-unavailable` (COG-47) e não alterar `is_active` nem apagar linhas.
3. The backend SHALL registrar cada falha do Cognito nas operações novas em WARNING, com a operação e o código de erro, sem incluir o código de confirmação, a senha nem tokens (COG-49). **(EMC-49)**
4. The Route Table do spec `api-restful-routes` e o `ROUTE_TABLE` de `hairmatch/test_routes.py` SHALL listar `POST /api/auth/email-confirmations` e `POST /api/auth/confirmation-codes`, anônimas. **(EMC-50)**

**Independent Test**: `hairmatch/test_problems.py` conta 39 slugs, e `hairmatch/test_routes.py` passa com as duas rotas novas. Nos testes, um `EndpointConnectionError` no `confirm_sign_up` gera 503, e o `assertLogs` não contém o código.

---

### P2: Documentação para dev e produção

**User Story**: Como dev ou operador, quero saber onde ler o código em dev e o que configurar na AWS antes de lançar.

**Why P2**: O fluxo funciona sem isso, mas a produção não entrega e-mail sem a configuração.

**Acceptance Criteria**:
1. The README SHALL explicar como ler o código de confirmação em dev (`/_ministack/ses/messages`, código fixo `123456`, `ConfirmSignUp` do MiniStack aceita qualquer código) e listar a configuração de produção:
   - `EmailConfiguration` `DEVELOPER` com o `SourceArn` do SES;
   - SES fora do sandbox;
   - `VerificationMessageTemplate`;
   - `PreventUserExistenceErrors=ENABLED`;
   - como agendar `purge_unconfirmed_users`.

   **(EMC-51)**

**Independent Test**: um dev novo segue o README, cadastra no web e confirma a conta sem ajuda.

---

## Edge Cases

- WHEN o usuário confirma com o e-mail em outra caixa (`A@X.com`) THEN o backend SHALL achar o `User` sem diferenciar maiúsculas e mandar ao Cognito o e-mail normalizado (EMC-13).
- WHEN o usuário pede reenvio depois de o código vencer THEN o Cognito SHALL emitir um código novo, e o antigo SHALL deixar de valer (regra do Cognito, testada no fake).
- IF o bot se cadastra de novo sobre uma conta pendente de outra pessoa THEN a conta antiga SHALL ser substituída (EMC-07), o que não dá acesso ao bot: a conta nova continua pendente e só o dono do e-mail recebe o código.
- IF a conta foi expurgada e o usuário tenta confirmar THEN o backend SHALL responder 400 `invalid-confirmation-code` (EMC-16), e o app SHALL mostrar a mensagem do slug, que orienta a se cadastrar de novo.
- IF uma conta pendente é ativada por EMC-20 ou EMC-54 THEN a senha que vale é a do cadastro pendente. Como só o dono do e-mail recebe o código, só ele chega a esse estado.
- IF o usuário fecha o app na tela de confirmação THEN a senha em memória SHALL se perder. Ao confirmar depois, pelo login com 403 (EMC-41), o app recebe a senha de novo.
- WHEN o MiniStack aceita um código errado em dev THEN a conta SHALL ser confirmada. Esse é um limite aceito do emulador (AD-005), e os erros de código são cobertos pelo fake.
- IF dois cadastros com o mesmo e-mail chegam ao mesmo tempo THEN o segundo SHALL receber 409 `email-taken`, pela `UsernameExistsException` (status `UNCONFIRMED` com `User` existente) ou pela restrição `unique` do Postgres, e a compensação de COG-10 SHALL apagar o usuário do Cognito que ficou órfão.

---

## Implicit-Requirement Dimensions Sweep

| Dimension | Coverage |
| --------- | -------- |
| Input validation & bounds | EMC-17 (código de 6 dígitos), EMC-23, EMC-43, normalização do e-mail (Assumptions) |
| Failure / partial-failure states | EMC-11, EMC-12, EMC-36, EMC-48, EMC-54, EMC-55 |
| Idempotency / retry / duplicate handling | EMC-01 (init idempotente), EMC-10 (uma única repetição), EMC-18 e EMC-20 (confirmação repetida), EMC-37 (expurgo repetido) |
| Auth boundaries & rate limits | EMC-25 a EMC-27, EMC-52 (Google não herda conta pendente), EMC-28 a EMC-33, EMC-16 e EMC-22 (sem enumeração) |
| Concurrency / ordering | EMC-07 (Cognito antes do Postgres na substituição), EMC-34 (Cognito antes do Postgres no expurgo), cadastro simultâneo (Edge Cases) |
| Data lifecycle / expiry | Código de 24 h (Assumptions), EMC-15, EMC-34 (7 dias) |
| Observability | EMC-37, EMC-49 |
| External-dependency failure | EMC-11, EMC-36, EMC-48, e-mail em produção (Assumptions) |
| State-transition integrity | Pendente → ativo só por EMC-13, EMC-18, EMC-20 ou EMC-54. Pendente → apagado por EMC-07, EMC-08, EMC-34, EMC-52 ou EMC-53. Uma conta pendente nunca recebe `google_id`. Ativo nunca volta a pendente. |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| EMC-01 | P1: Cognito local, AC1 | Tasks | Verified |
| EMC-02 | P1: Cognito local, AC2 | Tasks | Verified |
| EMC-03 | P1: Cadastro pendente, AC1 | Tasks | Implementing |
| EMC-04 | P1: Cadastro pendente, AC2 | Tasks | Implementing |
| EMC-05 | P1: Cadastro pendente, AC3 | Tasks | Implementing |
| EMC-06 | P1: Cadastro pendente, AC4 | Tasks | Implementing |
| EMC-07 | P1: Substituição, AC1 | Tasks | Implementing |
| EMC-08 | P1: Substituição, AC2 | Tasks | Implementing |
| EMC-09 | P1: Substituição, AC3 | Tasks | Implementing |
| EMC-10 | P1: Substituição, AC4 | Tasks | Implementing |
| EMC-11 | P1: Substituição, AC5 | Tasks | Implementing |
| EMC-12 | P1: Substituição, AC6 | Tasks | Implementing |
| EMC-13 | P1: Confirmar, AC1 | Tasks | Implementing |
| EMC-14 | P1: Confirmar, AC2 | Tasks | Implementing |
| EMC-15 | P1: Confirmar, AC3 | Tasks | Implementing |
| EMC-16 | P1: Confirmar, AC4 | Tasks | Implementing |
| EMC-17 | P1: Confirmar, AC5 | Tasks | Implementing |
| EMC-18 | P1: Confirmar, AC6 | Tasks | Implementing |
| EMC-19 | P1: Confirmar, AC7 | Tasks | Implementing |
| EMC-20 | P1: Confirmar, AC8 | Tasks | Implementing |
| EMC-21 | P1: Reenviar, AC1 | Tasks | Implementing |
| EMC-22 | P1: Reenviar, AC2 | Tasks | Implementing |
| EMC-23 | P1: Reenviar, AC3 | Tasks | Implementing |
| EMC-24 | P1: Reenviar, AC4 | Tasks | Implementing |
| EMC-25 | P1: Login pendente, AC1 | Tasks | Implementing |
| EMC-26 | P1: Login pendente, AC2 | Tasks | Implementing |
| EMC-27 | P1: Login pendente, AC3 | Tasks | Implementing |
| EMC-28 | P1: Rate limit, AC1 | Tasks | Implementing |
| EMC-29 | P1: Rate limit, AC2 | Tasks | Implementing |
| EMC-30 | P1: Rate limit, AC3 | Tasks | Implementing |
| EMC-31 | P1: Rate limit, AC4 | Tasks | Implementing |
| EMC-32 | P1: Rate limit, AC5 | Tasks | Implementing |
| EMC-33 | P1: Rate limit, AC6 | Tasks | Implementing |
| EMC-34 | P1: Expurgo, AC1 | Tasks | Implementing |
| EMC-35 | P1: Expurgo, AC2 | Tasks | Implementing |
| EMC-36 | P1: Expurgo, AC3 | Tasks | Implementing |
| EMC-37 | P1: Expurgo, AC4 | Tasks | Implementing |
| EMC-38 | P1: Expurgo, AC5 | Tasks | Implementing |
| EMC-39 | P1: Listagens, AC1 | Tasks | Implementing |
| EMC-40 | P1: App, AC1 | Tasks | Implementing |
| EMC-41 | P1: App, AC2 | Tasks | Implementing |
| EMC-42 | P1: App, AC3 | Tasks | Implementing |
| EMC-43 | P1: App, AC4 | Tasks | Implementing |
| EMC-44 | P1: App, AC5 | Tasks | Implementing |
| EMC-45 | P1: App, AC6 | Tasks | Implementing |
| EMC-46 | P1: App, AC7 | Tasks | Implementing |
| EMC-47 | P1: Contrato de erro, AC1 | Tasks | Pending |
| EMC-48 | P1: Contrato de erro, AC2 | Tasks | Implementing |
| EMC-49 | P1: Contrato de erro, AC3 | Tasks | Implementing |
| EMC-50 | P1: Contrato de erro, AC4 | Tasks | Implementing |
| EMC-51 | P2: Documentação, AC1 | Tasks | Implementing |
| EMC-52 | P1: Google, AC1 | Tasks | Implementing |
| EMC-53 | P1: Google, AC2 | Tasks | Implementing |
| EMC-54 | P1: Reenviar, AC5 | Tasks | Implementing |
| EMC-55 | P1: Google, AC3 | Tasks | Implementing |

**ID format:** `EMC-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 55 total, 55 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] UAT manual no web e no Android, com cliente e cabeleireiro:
  - cadastro → código lido em `/_ministack/ses/messages` → confirmação → home, sem redigitar a senha;
  - login de conta pendente → tela de confirmação → home;
  - reenvio com contagem de 60 s;
  - cabeleireiro pendente fora da busca;
  - login Google e login do seed sem regressão;
  - login Google com o e-mail de uma conta pendente cai no wizard Google, sem herdar a conta.
- [ ] A suíte do backend (`coverage run manage.py test`) passa com pelo menos os 619 testes da baseline (`git grep -c "def test_"` em `5ae43b0`) mais os novos, sem nenhum teste removido.
- [ ] Cada critério de backend (EMC-03 a EMC-39, EMC-47 a EMC-50 e EMC-52 a EMC-55) tem pelo menos um teste automatizado que falha se o comportamento for removido.
- [ ] `cd frontend-mobile && npx tsc --noEmit` não ganha nenhum erro novo.
- [ ] `grep -rn "sign_up_confirmed" backend --include=*.py` fora dos testes só encontra `users/cognito.py` e `populate_hairdressers.py`.
