# Autenticação via AWS Cognito Context

**Gathered:** 2026-09-29
**Spec:** `.specs/features/cognito-auth/spec.md`
**Status:** Ready for design

---

## Feature Boundary

O cadastro, o login, a troca de senha e a exclusão de conta por e-mail/senha passam a usar o AWS Cognito. O Hairmatch deixa de guardar e comparar senhas e de assinar a sessão dessas contas. Todo endpoint que hoje lê o cookie `jwt` passa a autenticar por um único componente, que aceita o access token do Cognito e a sessão própria das contas Google. O app ganha refresh transparente, logout que revoga a sessão e restauração da sessão no boot. Em dev, o Cognito roda no MiniStack, e todo o resto continua no LocalStack.

Nada além disso: nem "esqueci a senha", nem troca de e-mail, nem migração de hashes, nem auth nos endpoints que hoje já não autenticam.

---

## Implementation Decisions

### Cognito no ambiente local

- O LocalStack continua servindo S3 e SES. O Cognito roda em um container `ministack` (`ministackorg/ministack`, MIT) no mesmo `docker-compose.yml`.
- Motivo: o container do LocalStack ativa uma licença `freemium`, e o `cognito-idp` só existe nos planos pagos (Base/Ultimate/Student).
- A decisão fica documentada no README e no AD-005.

### Arquitetura: backend faz proxy do Cognito

- O app continua mandando e-mail e senha ao Django. O backend chama o Cognito via boto3 (`SignUp`, `AdminConfirmSignUp`, `InitiateAuth`, `ChangePassword`, `RevokeToken`, `AdminDeleteUser`) e devolve os tokens em cookies httpOnly.
- O app não ganha SDK da AWS (sem Amplify) e não recebe nenhuma env var nova.

### Sessão das contas Google

- O fluxo do #106 (`POST /api/auth/google` + `signup_token` + cadastro pelo wizard) não muda.
- Contas Google continuam com sessão emitida pelo backend. Ela deixa de usar a chave `'secret'` e passa a ser HS256 com `settings.SECRET_KEY`, `iss="hairmatch"` e `token_use="session"`.
- Um único autenticador aceita os dois emissores, com o algoritmo fixo por emissor.
- Isso supera o AD-001 no ponto "um só formato de sessão". O AD-004 registra a nova regra.

### Contas existentes

- Não há migração dos hashes bcrypt. Os dados atuais são de teste e o banco é re-seedado.
- Em dev: `docker compose down -v` (ou apagar os usuários) e subir de novo.
- No Render: o reset do banco é um passo operacional fora das tarefas de código e só acontece com autorização explícita do usuário.

### Agent's Discretion

- Confirmação de e-mail: auto-confirmar com `AdminConfirmSignUp`, sem tela de código.
- Contrato de erro: 401 para autenticação ausente, inválida ou expirada; 403 para falta de permissão.
- Nome e atributos dos cookies (`jwt` para o access token, `refresh_token` com `path=/api/auth/`).
- Resolução de IDs em dev pelo nome do pool e do client.
- Fake de Cognito nos testes, ligado como o `InMemoryStorage`.
- Onde o app faz o refresh: interceptor do `axiosInstance`.

### Declined / Undiscussed Gray Areas → Assumptions

- **Confirmação de e-mail por código:** não foi discutida. O padrão é a auto-confirmação, registrada nas Assumptions do spec como `n`.
- **Contrato 401:** não foi discutido e muda o status de hoje (403 ou 500) nos endpoints protegidos. Registrado nas Assumptions como `n`.
- **Política de senha:** alinhada ao app (8+, maiúscula, minúscula, número, sem símbolo). Registrado como `n`.
- **Senha do seed `Senha123`:** registrado como `n`.

---

## Specific References

- A issue pede JWT, redução do risco de segurança da autenticação local, impacto no frontend e o máximo possível de nuvem local no LocalStack "por enquanto".
- Preferências do projeto (memória): boto3 direto, sem django-storages; o mínimo de env vars novas; endpoints internos definidos no compose, e não no `.env`; seed pelo mesmo caminho de um usuário real.
- A decisão de testes do app herda do #106: sem testes automatizados no `frontend-mobile`, e o gate é `npx tsc --noEmit` mais o UAT.

---

## Deferred Ideas

- "Esqueci minha senha" com `ForgotPassword` e `ConfirmForgotPassword`. O MiniStack já suporta, e o código local é `654321`.
- Confirmação de e-mail por código no wizard.
- Troca de e-mail com verificação no Cognito.
- Federar o Google no Cognito (Hosted UI), ficando com um só formato de sessão.
- Refresh da sessão Google.
- Autenticar `reserve`, `agenda`, `service` e os endpoints "NoCookie" e admin de `availability`, `preferences` e `review`.
- Provisionar o user pool real por IaC (Terraform/CDK).
