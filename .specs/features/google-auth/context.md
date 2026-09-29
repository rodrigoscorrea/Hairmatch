# Login e Cadastro via Google Context

**Gathered:** 2026-09-27
**Spec:** `.specs/features/google-auth/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Qualquer pessoa, cliente ou cabeleireiro, consegue se cadastrar e entrar no Hairmatch com a conta Google, no web e no Android. O backend verifica o ID token do Google e emite a mesma sessão do login por senha. No primeiro acesso, a pessoa passa pelo wizard de cadastro que já existe para informar o que o Google não fornece. Nada além disso: nem iOS, nem foto do Google, nem gestão de senha ou de vínculo.

---

## Implementation Decisions

### Plataformas

- Web e Android. O Android é o APK gerado pelo perfil `preview` do EAS, um build nativo.
- iOS e Expo Go ficam fora. Não há `ios.bundleIdentifier` em `frontend-mobile/app.json`.

### Primeiro acesso: reusar o wizard de cadastro

- O fluxo é o mesmo de hoje: dados → endereço → preferências → (cabeleireiro) história profissional → descrição.
- Nome, sobrenome e e-mail chegam preenchidos pelo Google. O e-mail fica somente leitura.
- Os campos de senha e confirmação somem, e a senha deixa de ser validada.
- O usuário escolhe o papel (Cliente/Profissional) e informa CPF ou CNPJ, telefone e foto opcional na etapa 1, como já faz.
- Ao final, o usuário sai logado e vai para a home do papel, em vez de voltar para a tela de login.

### Testes do app

- Sem testes automatizados no `frontend-mobile`. O gate do app é `npx tsc --noEmit` mais o roteiro de UAT manual do `tasks.md`.
- Os testes automatizados ficam no backend (Django `TestCase`), com a verificação do Google mockada.

### Agent's Discretion

- Posição e visual do botão. No login, entre "Entrar" e o link "Cadastre-se" (`frontend-mobile/app/(auth)/login.tsx:69-78`), com um divisor "ou". No cadastro, logo abaixo do subtítulo "Cadastre-se" da etapa 1.
- Textos: "Entrar com Google" no login e "Cadastrar com Google" no cadastro.
- Biblioteca cliente de Google Sign-In, desde que cubra web e Android. Decidida no design.

### Declined / Undiscussed Gray Areas → Assumptions

- **Conta existente com o mesmo e-mail:** vínculo automático quando `email_verified=true`. Registrado nas Assumptions do spec como assumido, e o usuário pode corrigir.
- **Validade do token de cadastro pendente:** 30 minutos. Registrado nas Assumptions do spec.

---

## Specific References

- A issue cita "Expo AuthSession ou equivalente" para o botão.
- O critério de aceite da issue é o teste de aceitação: cadastrar e entrar com Google nos dois perfis.

---

## Deferred Ideas

- Suporte a iOS (exige bundle identifier e Client ID iOS).
- Importar a foto de perfil do Google no cadastro.
- Permitir que uma conta criada via Google defina uma senha depois.
- Desvincular a conta Google nas configurações do perfil.
