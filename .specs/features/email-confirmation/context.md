# Confirmação de e-mail no cadastro Context

**Gathered:** 2026-10-04
**Spec:** `.specs/features/email-confirmation/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Toda conta de e-mail/senha criada pelo cadastro (cliente ou cabeleireiro) nasce pendente: está no Cognito como `UNCONFIRMED` e no Postgres com `is_active=False`. Ela só passa a valer quando o dono do e-mail digita no app o código de 6 dígitos que o Cognito mandou.

Enquanto está pendente, a conta:
- não loga;
- não vira sessão;
- não aparece nas listagens;
- é substituída por um novo cadastro com o mesmo e-mail ou telefone;
- é expurgada em 7 dias.

As rotas anônimas que confirmam, reenviam e cadastram têm throttle por IP e por e-mail.

Nada além disso:
- contas Google não mudam;
- não há link de confirmação;
- não há CAPTCHA;
- não há "esqueci a senha";
- o pool e o SES de produção não são provisionados aqui.

---

## Implementation Decisions

### Mecanismo de confirmação

- É um código de 6 dígitos nativo do Cognito: `ConfirmSignUp` confirma e `ResendConfirmationCode` reenvia. O usuário digita o código numa tela do app.
- Diverge do "clicar no link" da issue, por escolha do usuário. As alternativas foram descartadas:
  - `CONFIRM_WITH_LINK` exige domínio no pool, abre uma página do `amazoncognito.com` fora do app e o MiniStack não a emula;
  - link próprio enviado pelo backend pelo SES exigiria token, validade e `email_verified` feitos à mão, além de desligar o e-mail do Cognito.
- O envio continua a cargo do Cognito. Em produção, o pool usa o SES do projeto (`EmailConfiguration` `DEVELOPER`). Em dev, o MiniStack registra o e-mail no SES embutido dele.

### Contas não confirmadas

- Um novo cadastro com o mesmo e-mail ou telefone de uma conta pendente a substitui: `AdminDeleteUser` mais a remoção das linhas, e depois o cadastro segue.
- O command `purge_unconfirmed_users` apaga as contas pendentes com mais de 7 dias.
- Motivo: um bot que cadastra o e-mail ou o telefone de outra pessoa bloquearia o dono real com 409, porque os dois campos são únicos.

### Anti-bot

- A defesa é a confirmação mais throttle por IP e por e-mail no cadastro, na confirmação e no reenvio.
- Nada pago: sem CAPTCHA, WAF Bot Control nem Cognito Threat Protection.

### Agent's Discretion

- **Rotas:**
  - `POST /api/auth/email-confirmations` `{email, code}`;
  - `POST /api/auth/confirmation-codes` `{email}`.
  - São substantivos no plural, sem verbo, como exige o AD-007.
- **Estado pendente:** `User.is_active=False`, sem migração. O autenticador já filtra `is_active=True`.
- **Login bloqueado também pelo Postgres:** o MiniStack não bloqueia `UNCONFIRMED` no `InitiateAuth`.
- **Limites:**
  - confirmar: 10/min por IP e 10/hora por e-mail;
  - reenviar: 10/hora por IP e 3/hora por e-mail;
  - cadastrar: 10/hora por IP (atual) e 3/hora por e-mail.
- **Contagens do throttle:** em `DatabaseCache` (`hairmatch_cache`), com a tabela criada por migração.
- **Google sobre conta pendente:** o login e o cadastro Google substituem a conta pendente com o mesmo e-mail ou telefone e nunca vinculam o `google_id` a ela. Sem isso, a vítima herdaria a conta do bot. Decorre da escolha "substituir" do usuário.
- **Depois da confirmação:** o app faz login sozinho com a senha que ficou em memória.
- **Confirmação repetida:** 200 idempotente.
- **Contra enumeração:**
  - e-mail sem conta pendente na confirmação recebe o mesmo 400 de código errado;
  - o reenvio sempre responde 202;
  - o client tem `PreventUserExistenceErrors=ENABLED`.
- **Expurgo:** roda no boot (`entrypoint.sh`).
- **Texto do e-mail:** em pt-BR, só texto.
- **Listagens:** a busca e as listagens filtram o cabeleireiro pendente.

### Declined / Undiscussed Gray Areas → Assumptions

Todas as decisões de Agent's Discretion estão nas Assumptions do spec com `Confirmed? = n`. As três decisões discutidas estão com `y`. Ritmo da discussão: as três questões independentes foram decididas numa única rodada (Guided).

---

## Specific References

- **Issue #141:** "um email de confirmação - verificação seja disparado para o email cadastrado. Caso o usuário clique no link, o cadastro é oficializado na plataforma. Válido tanto para o perfil de hairdresser quanto de customer."
- **Pedido do usuário:** "terminar o fluxo da implementação na qual o usuário confirma a conta para redobrarmos nossa segurança. Atenção aos rate limits de cadastros possivelmente fraudulentos de bots e afins. O foco é usar o cognito e o SES da AWS."
- **O usuário supôs que o Cognito "já lança o email via SES".** A confirmação é parcial:
  - o `SignUp` já dispara o código;
  - o backend o descarta com `AdminConfirmSignUp`;
  - o pool só usa o SES do projeto com `EmailConfiguration` `DEVELOPER`, que é configuração de produção ainda não feita.
- **MiniStack 1.5.18**, conferido no código do container em `/opt/ministack/ministack/services/cognito.py`:
  - o `SignUp` e o `ResendConfirmationCode` entregam ao SES embutido (`GET /_ministack/ses/messages`);
  - o código é fixo, `123456`;
  - o `ConfirmSignUp` aceita qualquer código;
  - o `InitiateAuth` não recusa `UNCONFIRMED`;
  - o `PreventUserExistenceErrors` é emulado.
- **Preferências do projeto (memória):**
  - boto3 direto;
  - nenhuma env var nova;
  - endpoint interno definido no compose;
  - seed pelo caminho real (aqui, o seed continua auto-confirmado, como já era desde a COG-38);
  - testes do backend dentro do container `hairmatch_backend`.

---

## Deferred Ideas

- Link de confirmação (do Cognito ou próprio) e deep link no app.
- CAPTCHA (Turnstile/hCaptcha), AWS WAF Bot Control e Cognito Threat Protection (plano Plus).
- Agendar `purge_unconfirmed_users` como Render Cron Job.
- Relay SMTP do MiniStack (`SMTP_HOST`) para um Mailpit no compose, para ver os e-mails numa caixa de entrada.
- Template de e-mail em HTML com a marca do Hairmatch.
- "Esqueci minha senha" (`ForgotPassword`/`ConfirmForgotPassword`).
- Bloquear perfil e reserva por id de cabeleireiro pendente.
