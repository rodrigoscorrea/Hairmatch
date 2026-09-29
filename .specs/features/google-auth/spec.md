# Login e Cadastro via Google Specification

**Issue:** [#106](https://github.com/rodrigoscorrea/Hairmatch/issues/106) · RF2 (Login via Google) e RF5 (Cadastro via Google) em `docs/requisitos-status.md`
**Escopo:** Complex (auth + chamada externa + persistência + transição de estado)
**Plataformas:** Web e Android (APK do perfil `preview` do EAS)

## Problem Statement

Hoje o Hairmatch só aceita cadastro e login por e-mail e senha. Clientes e cabeleireiros precisam criar e lembrar mais uma senha. A issue #106 pede que qualquer pessoa, nos dois perfis, consiga se cadastrar e entrar com a conta Google. No primeiro acesso, a pessoa completa os dados obrigatórios que o Google não fornece: papel, telefone, endereço e CPF/CNPJ.

## Goals

- [ ] Um cliente e um cabeleireiro conseguem criar conta com Google e caem logados na home do seu papel, sem digitar senha.
- [ ] Uma conta existente, criada por Google ou por e-mail/senha com o mesmo e-mail verificado, entra com Google em um toque.
- [ ] A sessão emitida pelo login Google é idêntica à do login por senha (cookie `jwt`, payload `{id, exp, iat}`). Nenhum endpoint existente muda.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| iOS e Expo Go | Decisão do usuário. Não existe `ios.bundleIdentifier`, e as bibliotecas nativas de Google Sign-In não rodam no Expo Go. |
| Importar a foto de perfil do Google | Exige baixar a imagem no backend. O usuário escolhe a foto no wizard, como hoje. |
| Definir senha para uma conta criada via Google | Feature separada, porque exige um fluxo de "criar senha" sem senha antiga. |
| Desvincular a conta Google | Não pedido na issue. |
| Trocar a chave `'secret'` do JWT ou mover o token para `settings` | Mudaria o decode feito à mão em quatro apps. É dívida técnica registrada no design. |
| Persistir a sessão entre reinícios do app | Comportamento atual do login por senha. Não muda nesta feature. |
| Corrigir a checagem de telefone duplicado no cadastro por senha | Bug pré-existente. Aqui a checagem normalizada vale só para o caminho Google (ver design). |
| Login via celular (RF3) | Outro requisito. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Plataformas-alvo | Web + Android (build EAS, não Expo Go) | Escolha do usuário. O perfil `preview` do EAS já gera APK. | y |
| Como completar os dados no primeiro acesso | Reusar o wizard de cadastro atual, com nome e e-mail vindos do Google e sem campos de senha | Escolha do usuário. O perfil sai igual ao do cadastro normal: preferências e, para cabeleireiro, história e descrição. | y |
| Testes do frontend | Só teste manual. O gate do app é `npx tsc --noEmit` mais o roteiro de UAT. | Escolha do usuário. O app não tem nenhum teste nem testing-library hoje. | y |
| Conta e-mail/senha existente com o mesmo e-mail | Vincular automaticamente (grava o `sub` do Google) quando `email_verified=true` | O Google já provou a posse do e-mail. Bloquear obrigaria o usuário a um fluxo manual que não existe. | n (assumido; o usuário pode corrigir) |
| Credenciais do Google Cloud | O time cria os OAuth Client IDs: um Web, com Authorized JavaScript origins e redirect URIs para cada origem web (`http://localhost:8081` e a URL publicada), e um Android (pacote `com.rodrigosc615.frontendmobile` + SHA-1 do keystore EAS) | Não há como criar pelo código. Sem eles, a feature não roda fora dos testes com mock. | n (pré-requisito) |
| Variáveis de ambiente | Backend: `GOOGLE_OAUTH_CLIENT_IDS` (lista separada por vírgula). App: `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID`. | Segue o padrão `os.getenv` do backend e `EXPO_PUBLIC_*` do app. No Android, o ID token nativo sai com audience igual ao Client ID Web. | n |
| Validade do token de cadastro pendente | 30 minutos | Cobre com folga o wizard mais longo (cinco etapas do cabeleireiro), sem deixar um token de cadastro válido por dias. | n |
| Mensagens de erro | Em português, no campo `error` do JSON, como nas views atuais | Mantém o contrato que o `ErrorModal` já exibe. | n |
| Cookie no Android | O `jwt` devolvido por `POST /api/auth/google` e pelo `register` é guardado pelo cookie store nativo, igual ao login por senha | É o mecanismo em que o login atual já se apoia no Android. Confirmado no UAT manual. | n |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## User Stories

### P1: Entrar com Google (conta existente) ⭐ MVP

**User Story**: Como cliente ou cabeleireiro com conta no Hairmatch, quero entrar tocando em "Entrar com Google" para não precisar digitar e-mail e senha.

**Why P1**: Metade do critério de aceite da issue ("entrar com uma conta Google, nos dois perfis").

**Acceptance Criteria**:
1. **GAUTH-01** WHEN `POST /api/auth/google` recebe um `id_token` válido cujo `sub` é igual ao `google_id` de um usuário THEN o backend SHALL responder 200 com `{"status": "authenticated"}` e definir o cookie `jwt` com payload `{id, exp = iat + 60 min, iat}`, HS256, `httponly`, `samesite=None` e `secure`, igual ao `LoginView`.
2. **GAUTH-02** WHEN `POST /api/auth/google` recebe um `id_token` válido com `email_verified=true`, nenhum usuário tem aquele `sub`, e existe um usuário com o mesmo e-mail (comparação sem diferenciar maiúsculas) e `google_id` vazio THEN o backend SHALL gravar o `sub` em `google_id` e responder como no critério 1.
3. **GAUTH-03** IF o corpo de `POST /api/auth/google` não traz `id_token` ou ele é vazio THEN o backend SHALL responder 400 com `{"error": ...}` e não definir cookie.
4. **GAUTH-04** IF o `id_token` falha na verificação (assinatura, expiração ou emissor) ou o `aud` não está em `GOOGLE_OAUTH_CLIENT_IDS` THEN o backend SHALL responder 401 com `{"error": ...}`, não definir cookie e não alterar nenhuma linha.
5. **GAUTH-05** IF o `id_token` é válido mas `email_verified` não é `true` THEN o backend SHALL responder 403 com `{"error": ...}`, não definir cookie e não alterar nenhuma linha.
6. **GAUTH-06** IF o usuário com o mesmo e-mail já tem um `google_id` diferente do `sub` recebido THEN o backend SHALL responder 409 com `{"error": ...}` e não definir cookie.
7. **GAUTH-07** WHEN o usuário toca em "Entrar com Google" na tela de login, conclui o consentimento e o backend responde `authenticated` THEN o app SHALL carregar a sessão (`GET /api/auth/user` e depois `GET /api/user/authenticated`) e navegar para `/(app)/(customer)/home` se o papel for cliente, ou para `/(app)/(hairdresser)/agenda` se for cabeleireiro.
8. **GAUTH-08** IF o usuário cancela ou fecha o consentimento do Google THEN o app SHALL permanecer na tela atual sem exibir o `ErrorModal`.
9. **GAUTH-09** IF o backend responde 4xx ou 5xx ao `POST /api/auth/google` THEN o app SHALL exibir o `ErrorModal` com o texto de `error` da resposta, ou "Não foi possível entrar com o Google. Tente novamente." se não houver texto.
10. **GAUTH-10** WHILE a requisição do Google está em andamento o app SHALL manter o botão do Google desabilitado.
11. **GAUTH-11** IF um usuário sem senha (conta criada via Google) envia e-mail e senha para `POST /api/auth/login` THEN o backend SHALL responder 403 com `{"error": "Esta conta usa login com Google. Use o botão Entrar com Google."}`, em vez de erro 500.

**Independent Test**: com um usuário cliente e um cabeleireiro já vinculados ao Google, tocar em "Entrar com Google" na tela de login leva cada um à sua home. Nos testes do backend, `POST /api/auth/google` com o verificador mockado devolve 200 e um cookie `jwt` que `GET /api/auth/user` aceita.

---

### P1: Cadastrar com Google (primeiro acesso, nos dois perfis) ⭐ MVP

**User Story**: Como pessoa sem conta no Hairmatch, quero me cadastrar com o Google e preencher só o que falta (papel, telefone, endereço, CPF/CNPJ e as etapas seguintes), para sair do cadastro já logado.

**Why P1**: A outra metade do critério de aceite ("se cadastrar ... com uma conta Google, nos dois perfis").

**Acceptance Criteria**:
1. **GAUTH-12** WHEN `POST /api/auth/google` recebe um `id_token` válido com `email_verified=true` e nenhum usuário tem aquele `sub` nem aquele e-mail THEN o backend SHALL responder 200 com `{"status": "signup_required", "signup_token": <str>, "prefill": {"email", "first_name", "last_name"}}`, não definir cookie e não criar nenhuma linha.
2. The backend SHALL emitir o `signup_token` com expiração de 30 minutos a partir da emissão, contendo o `email` e o `sub` do Google. **(GAUTH-13)**
3. The backend SHALL assinar o `signup_token` com uma chave diferente da chave de sessão, de modo que `GET /api/auth/user` com esse token no cookie `jwt` responda 200 com `{"authenticated": false}`, e não 500. **(GAUTH-14)**
4. **GAUTH-15** WHEN `POST /api/auth/register` recebe um `google_signup_token` válido, `role=customer`, `cpf`, telefone e os campos de endereço obrigatórios, sem `password` THEN o backend SHALL criar em uma única transação um `User` (e-mail do token, `password` nulo, `google_id` igual ao `sub`, `role='customer'`, telefone com prefixo `55`) e um `Customer` com o CPF, responder 201 e definir o cookie `jwt` como no login.
5. **GAUTH-16** WHEN `POST /api/auth/register` recebe um `google_signup_token` válido, `role=hairdresser`, `cnpj`, telefone, os campos de endereço obrigatórios e os campos profissionais THEN o backend SHALL criar em uma única transação um `User` (`role='hairdresser'`, `google_id` igual ao `sub`, `password` nulo) e um `Hairdresser` com CNPJ, `experience_time`, `experiences`, `products` e `resume`, responder 201 e definir o cookie `jwt`.
6. **GAUTH-17** WHILE a requisição de cadastro traz `google_signup_token` o backend SHALL usar o e-mail do token e ignorar os campos `email`, `password` e `confirmPassword` do formulário.
7. **GAUTH-18** IF o `google_signup_token` é inválido, adulterado ou expirado THEN o backend SHALL responder 401 com `{"error": ...}` e não criar nenhuma linha.
8. **GAUTH-19** IF o telefone informado, normalizado como `55` + dígitos, já pertence a um usuário THEN o backend SHALL responder 409 com `{"error": ...}` e não criar nenhuma linha.
9. **GAUTH-20** IF o e-mail ou o `sub` do token já pertence a um usuário no momento do cadastro THEN o backend SHALL responder 409 com `{"error": ...}` e não criar nenhuma linha.
10. **GAUTH-21** IF `role` falta ou não é `customer` nem `hairdresser`, ou falta um dos campos `first_name`, `last_name`, `phone`, `address`, `neighborhood`, `city`, `state`, `postal_code`, `cpf` (cliente) ou `cnpj` (cabeleireiro) THEN o backend SHALL responder 400 com `{"error": ...}` e não criar nenhuma linha.
11. **GAUTH-22** IF qualquer erro ocorre depois que o `User` foi inserido no caminho Google THEN o backend SHALL desfazer a transação, sem deixar `User`, `Customer`, `Hairdresser` nem vínculos de preferências.
12. **GAUTH-23** WHEN a mesma conta Google chama `POST /api/auth/google` de novo sem ter concluído o cadastro THEN o backend SHALL responder `signup_required` novamente, porque abandonar o wizard não cria conta.
13. **GAUTH-24** WHEN o backend responde `signup_required` THEN o app SHALL abrir `/(auth)/register` com `first_name`, `last_name` e `email` preenchidos a partir do `prefill` e com o `google_signup_token` guardado no `RegistrationContext`.
14. **GAUTH-25** WHILE o `RegistrationContext` tem um `google_signup_token` a etapa 1 do cadastro SHALL exibir o e-mail somente leitura, esconder os campos de senha e confirmação e não validar senha.
15. **GAUTH-26** WHEN o envio final do wizard em modo Google (etapa de preferências do cliente ou de descrição do cabeleireiro) recebe 201 THEN o app SHALL carregar a sessão e navegar para a home do papel, sem passar pela tela de login.
16. **GAUTH-27** IF o envio final do wizard em modo Google recebe 4xx ou 5xx, no web ou no Android THEN o app SHALL exibir o `ErrorModal` com o texto de `error` e permanecer no wizard.

**Independent Test**: com uma conta Google nova, cadastrar um cliente pelo wizard e terminar logado na home de cliente. Repetir com outra conta Google como cabeleireiro e terminar na agenda. Nos testes do backend, o fluxo `google` → `register`, com o verificador mockado, cria as linhas certas para os dois papéis e devolve o cookie.

---

### P1: Botão do Google na tela de cadastro ⭐ MVP

**User Story**: Como pessoa que abriu a tela de cadastro, quero o botão "Cadastrar com Google" ali mesmo, para não voltar ao login.

**Why P1**: A issue pede o botão "nas telas de login e cadastro".

**Acceptance Criteria**:
1. **GAUTH-28** WHEN o usuário toca em "Cadastrar com Google" na etapa 1 do cadastro e o backend responde `signup_required` THEN o app SHALL preencher a etapa 1 com o `prefill` e entrar no modo Google descrito na história anterior.
2. **GAUTH-29** WHEN o usuário toca em "Cadastrar com Google" e o backend responde `authenticated` THEN o app SHALL carregar a sessão e navegar para a home do papel.
3. **GAUTH-30** WHEN o usuário abre o cadastro pelo link "Cadastre-se" da tela de login THEN o app SHALL limpar o `RegistrationContext`, sem manter `google_signup_token` nem dados de uma tentativa anterior.

**Independent Test**: abrir o cadastro pelo link, tocar em "Cadastrar com Google" com uma conta nova e ver nome e e-mail preenchidos, sem os campos de senha. Voltar ao login, abrir o cadastro de novo e ver o formulário vazio, com os campos de senha.

---

## Edge Cases

- IF `given_name` ou `family_name` não vierem no `id_token` THEN o backend SHALL devolver string vazia no `prefill`, e o wizard exige o preenchimento como hoje (coberto por GAUTH-12 e GAUTH-21).
- IF o `id_token` traz um e-mail com maiúsculas diferentes de um usuário existente THEN o backend SHALL tratar como o mesmo usuário (coberto por GAUTH-02).
- IF o `signup_token` expira enquanto o usuário ainda está no wizard THEN o envio final SHALL receber 401, e o app SHALL exibir o erro (coberto por GAUTH-18 e GAUTH-27).
- WHEN o usuário escolhe o papel no wizard em modo Google THEN o backend SHALL aceitar tanto `customer` quanto `hairdresser`, porque o papel não vem do Google (coberto por GAUTH-15 e GAUTH-16).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| GAUTH-01 | P1: Entrar com Google, AC1 | Tasks | Verified |
| GAUTH-02 | P1: Entrar com Google, AC2 | Tasks | Verified |
| GAUTH-03 | P1: Entrar com Google, AC3 | Tasks | Verified |
| GAUTH-04 | P1: Entrar com Google, AC4 | Tasks | Verified |
| GAUTH-05 | P1: Entrar com Google, AC5 | Tasks | Verified |
| GAUTH-06 | P1: Entrar com Google, AC6 | Tasks | Verified |
| GAUTH-07 | P1: Entrar com Google, AC7 | Tasks | Implementing |
| GAUTH-08 | P1: Entrar com Google, AC8 | Tasks | Implementing |
| GAUTH-09 | P1: Entrar com Google, AC9 | Tasks | Implementing |
| GAUTH-10 | P1: Entrar com Google, AC10 | Tasks | Implementing |
| GAUTH-11 | P1: Entrar com Google, AC11 | Tasks | Verified |
| GAUTH-12 | P1: Cadastrar com Google, AC1 | Tasks | Verified |
| GAUTH-13 | P1: Cadastrar com Google, AC2 | Tasks | Verified |
| GAUTH-14 | P1: Cadastrar com Google, AC3 | Tasks | Verified |
| GAUTH-15 | P1: Cadastrar com Google, AC4 | Tasks | Verified |
| GAUTH-16 | P1: Cadastrar com Google, AC5 | Tasks | Verified |
| GAUTH-17 | P1: Cadastrar com Google, AC6 | Tasks | Verified |
| GAUTH-18 | P1: Cadastrar com Google, AC7 | Tasks | Verified |
| GAUTH-19 | P1: Cadastrar com Google, AC8 | Tasks | Verified |
| GAUTH-20 | P1: Cadastrar com Google, AC9 | Tasks | Verified |
| GAUTH-21 | P1: Cadastrar com Google, AC10 | Tasks | Verified |
| GAUTH-22 | P1: Cadastrar com Google, AC11 | Tasks | Verified |
| GAUTH-23 | P1: Cadastrar com Google, AC12 | Tasks | Verified |
| GAUTH-24 | P1: Cadastrar com Google, AC13 | Tasks | Implementing |
| GAUTH-25 | P1: Cadastrar com Google, AC14 | Tasks | Implementing |
| GAUTH-26 | P1: Cadastrar com Google, AC15 | Tasks | Implementing |
| GAUTH-27 | P1: Cadastrar com Google, AC16 | Tasks | Implementing |
| GAUTH-28 | P1: Botão no cadastro, AC1 | Tasks | Implementing |
| GAUTH-29 | P1: Botão no cadastro, AC2 | Tasks | Implementing |
| GAUTH-30 | P1: Botão no cadastro, AC3 | Tasks | Implementing |

**ID format:** `GAUTH-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 30 total, 30 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] O critério de aceite da issue #106 passa no UAT manual: web e Android, cliente e cabeleireiro, cadastro e login com Google.
- [ ] Todos os testes existentes do backend continuam passando (`coverage run manage.py test`), sem nenhum teste alterado para acomodar a feature.
- [ ] Cada critério de backend (GAUTH-01 a 06, 11 a 23) tem pelo menos um teste automatizado que falha se o comportamento for removido.
