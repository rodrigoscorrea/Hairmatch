# Configurações da conta Specification

**Issue:** [#120](https://github.com/rodrigoscorrea/Hairmatch/issues/120) · [Feature] Editar dados da conta, endereço, preferências, resumo e foto, e excluir conta
**Escopo:** Complex (auth + chamada externa ao S3 + transição de estado na exclusão + backend e app)
**Plataformas:** backend Django e app (web e Android)

## Problem Statement

Depois do cadastro, cliente e cabeleireiro não conseguem mudar nada da própria conta:
- As quatro telas de `configs` (conta e endereço, para cada papel) são somente leitura. Os `onChangeText` estão comentados e o "Salvar" não faz nada (`frontend-mobile/app/(app)/hairdresser/configs/accountSetting.tsx:91`).
- Não existe tela de preferências, de resumo nem de foto.
- O app também não oferece a exclusão de conta, embora o backend já a faça.

No backend:
- O `PATCH /api/users/me` existe, mas não valida o corpo (`backend/users/views.py:692-742`):
  - aceita string vazia em campo obrigatório;
  - não confere o formato do telefone;
  - compara o e-mail diferenciando maiúsculas;
  - responde 500 numa corrida pelo mesmo telefone.
- A foto de perfil só é gravada no cadastro.

A troca de senha e de e-mail saiu desta feature e foi para a #175, porque passa pelo Cognito.

## Goals

- [ ] Cliente e cabeleireiro alteram pelo app os dados da conta, o endereço, as preferências e a foto, e o cabeleireiro altera o resumo. Cada alteração aparece no `GET /api/users/me` seguinte.
- [ ] O `PATCH /api/users/me` recusa com 400 `validation-error` todo valor que o cadastro não aceitaria, e nunca responde 500 por conflito de telefone.
- [ ] O usuário exclui a própria conta pelo app e cai no login, sem crash e sem sessão.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Alterar a senha logado | Foi para a #175, junto com "esqueci minha senha", por decisão do usuário. O backend (`PUT /api/users/me/password`) fica como está. |
| "Esqueci minha senha" | #175. É uma rota anônima que dispara e-mail pelo Cognito e exige os throttles do AD-008. |
| Trocar o e-mail | #175. O e-mail é o username no Cognito. O `PATCH` continua respondendo `email-change-unsupported`. |
| Avisar os clientes quando um cabeleireiro exclui a conta | #171, que depende da spike de notificações (#172). |
| Regenerar o resumo por IA depois do cadastro | `experience_time`, `experiences` e `products` não são guardados, e o rascunho por IA precisa deles. |
| Editar `experience_years` | O `GET /api/users/me` não devolve o campo, e a issue não pede. |
| Responder 200 `[]` em `GET /api/users/{id}/preferences` sem preferências | Muda o contrato de uma rota pública. O app trata o 404 como lista vazia. |
| Testes automatizados no app | O app não tem suíte. O gate do app é `npx tsc --noEmit` mais o UAT, como no #139 e no #141. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| O que sai da #120 | Alterar senha, "esqueci minha senha" e trocar e-mail vão para a #175. | Escolha do usuário. Tudo isso passa pelo Cognito e deve ser projetado junto. | y |
| Foto de perfil | Fica nesta feature, com rota nova `PUT`/`DELETE /api/users/me/profile-picture`. | Escolha do usuário. | y |
| Rota da foto | `profile-picture` entra como segmento singular permitido no RT-54, como `password`. São as rotas RT-88 e RT-89 do `api-restful-routes`. | A foto é um sub-recurso único do usuário, e não uma coleção. Um `PATCH` multipart em `/users/me` misturaria JSON e arquivo na mesma rota. | n |
| CPF e CNPJ | Continuam editáveis, só com a contagem de dígitos (11 e 14). | A tela e o `PATCH` já os expõem. O cadastro também não valida o dígito verificador no backend. | n |
| Formato gravado | O backend tira o que não é dígito de `phone`, `postal_code`, `cpf` e `cnpj` antes de validar e gravar. `state` é gravado em maiúsculas. | O cadastro já grava só os dígitos (`useDescription.ts:52` e `normalize_phone`), e o chatbot busca o usuário pelo telefone só com dígitos. | n |
| Telefone no `PATCH` | O contrato continua sendo o número completo, com o `55` e como o `GET` devolve. O app mostra o número sem o `55` e o recoloca ao enviar. | É o comentário de `views.py:704`. Mudar o contrato quebraria quem já usa a rota. | n |
| Telefone gravado fora do formato | O telefone que volta igual ao gravado (mesmos dígitos) não passa pela validação de formato (ACC-58), e o app só manda o telefone quando o usuário o muda. | O seed (`populate_hairdressers.py:239`) grava `fake.unique.phone_number()` cru: no banco de dev, 40 de 42 usuários têm telefones como `74 8985-0719` e `0300 341 5528`. Sem essa regra, essas contas não salvariam nenhuma outra mudança. | n |
| Limite do resumo | No máximo 1000 caracteres. Vazio é permitido. | `Hairdresser.resume` é `TextField` sem limite. 1000 cabe no perfil do app e limita o abuso. | n |
| Limite da foto | No máximo 5 MB antes da conversão. | Não há limite hoje. A conversão para WebP roda na requisição (AD-003), e 5 MB cobre a foto de um celular com qualidade 0.5. | n |
| Sair sem salvar | As alterações são descartadas sem aviso. | É o comportamento atual das telas, e a issue não pede aviso. | n |
| Resposta do `PATCH` | Continua `200 {"message": ...}`. O app recarrega o usuário com `GET /api/users/me` (`loadSession`). | Mantém o contrato do RT-58. | n |
| Preferências sem nenhuma atribuída | O app trata o 404 de `GET /api/users/{id}/preferences` como lista vazia. | Ver Out of Scope. | n |
| Confirmação da exclusão | Só o modal de confirmação, sem pedir a senha. | A conta Google não tem senha, e a issue pede só "com confirmação". | n |
| Conta pendente com o telefone pedido | É substituída, como no cadastro (AD-008): `AdminDeleteUser` e depois a remoção das linhas. | AD-008: uma conta não confirmada nunca ocupa o telefone de outra pessoa. | n |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## User Stories

### P1: Validar o `PATCH /api/users/me` ⭐ MVP

**User Story**: Como usuário logado, quero que o backend recuse dados inválidos na edição da conta, para que meu perfil nunca fique com campo vazio ou com telefone que o chatbot não reconhece.

**Why P1**: As telas desta feature passam a escrever pelo `PATCH`, que hoje grava qualquer valor.

**Acceptance Criteria**:
1. **ACC-01** IF o corpo do `PATCH /api/users/me` traz `first_name`, `last_name`, `phone`, `address`, `neighborhood`, `city`, `state` ou `postal_code` vazio, só com espaços ou com valor que não é string THEN o backend SHALL responder 400 `validation-error` com um item `{"pointer": "/<campo>"}` por campo e SHALL não gravar nenhum campo.
2. **ACC-02** IF um campo de texto do corpo passa do `max_length` do modelo (`first_name` e `last_name` 100, `address`, `neighborhood`, `city` e `complement` 150, `number` 6) THEN o backend SHALL responder 400 `validation-error` com o pointer do campo e SHALL não gravar nenhum campo.
3. **ACC-03** IF `phone`, sem os caracteres que não são dígitos, difere dos dígitos do telefone gravado e não casa com `^55\d{10,11}$` THEN o backend SHALL responder 400 `validation-error` com o pointer `/phone`.
4. **ACC-04** IF `postal_code`, só com os dígitos, não tem exatamente 8 dígitos THEN o backend SHALL responder 400 `validation-error` com o pointer `/postal_code`.
5. **ACC-05** IF `state` não tem exatamente 2 letras THEN o backend SHALL responder 400 `validation-error` com o pointer `/state`.
6. **ACC-06** IF um cliente envia `cpf` que, só com os dígitos, não tem 11 dígitos, ou um cabeleireiro envia `cnpj` que não tem 14 THEN o backend SHALL responder 400 `validation-error` com o pointer do campo.
7. **ACC-07** IF um cabeleireiro envia `resume` que não é string ou que passa de 1000 caracteres THEN o backend SHALL responder 400 `validation-error` com o pointer `/resume`.
8. **ACC-08** WHEN o `PATCH` recebe um corpo válido THEN o backend SHALL gravar `phone`, `postal_code`, `cpf` e `cnpj` só com os dígitos e `state` em maiúsculas, e responder 200.
9. **ACC-09** WHEN o `PATCH` recebe `email` igual ao atual sem diferenciar maiúsculas THEN o backend SHALL ignorar o campo e manter o e-mail gravado.
10. **ACC-10** IF o `PATCH` recebe `email` diferente do atual sem diferenciar maiúsculas THEN o backend SHALL responder 400 `email-change-unsupported` e SHALL não gravar nenhum campo.
11. **ACC-11** IF o `phone` normalizado pertence a outra conta ativa THEN o backend SHALL responder 409 `phone-taken` e SHALL não gravar nenhum campo.
12. **ACC-12** WHEN o `phone` normalizado pertence a uma conta pendente (`is_active=False` e `cognito_sub` preenchido) THEN o backend SHALL substituí-la como no cadastro (`AdminDeleteUser` e depois a remoção das linhas) e gravar o telefone novo.
13. **ACC-13** IF o `AdminDeleteUser` da conta pendente de ACC-12 falha THEN o backend SHALL responder 503 `auth-unavailable` (ou 429 `too-many-requests`) e SHALL manter intactas a conta pendente e a do usuário.
14. **ACC-14** IF a gravação levanta `IntegrityError` porque outra requisição tomou o telefone depois da checagem THEN o backend SHALL responder 409 `phone-taken`, e não 500.
15. **ACC-15** IF a gravação do `Customer` ou do `Hairdresser` falha depois da gravação do `User` THEN o backend SHALL desfazer as duas, e o `GET /api/users/me` seguinte SHALL devolver os valores anteriores.

**Independent Test**: logar e chamar `PATCH /api/users/me` com `{"first_name": ""}`, `{"phone": "123"}` e `{"state": "Amazonas"}`. Cada um responde 400 `validation-error` com o pointer certo, e o `GET` mostra os dados antigos. Chamar com `{"phone": "55 (92) 99999-0000"}` grava `5592999990000`.

---

### P1: Editar os dados da conta no app ⭐ MVP

**User Story**: Como cliente ou cabeleireiro, quero alterar meu nome, telefone e documento pelo app, para manter meu perfil certo sem refazer o cadastro.

**Why P1**: É o primeiro item da issue.

**Acceptance Criteria**:
1. **ACC-16** WHEN a tela `configs/accountSetting` abre, para qualquer dos dois papéis THEN o app SHALL mostrar nome, sobrenome, telefone (com máscara e sem o `55`) e CPF ou CNPJ (com máscara) preenchidos e editáveis, mostrar o e-mail sem permitir edição e não mostrar campo de senha.
2. **ACC-17** WHEN o usuário toca em "Salvar" com campos alterados e válidos THEN o app SHALL enviar ao `PATCH /api/users/me` só os campos alterados, com o telefone como `55` + dígitos e os documentos só com os dígitos.
3. **ACC-18** WHEN o `PATCH` responde 200 THEN o app SHALL recarregar o usuário (`loadSession`) e mostrar a mensagem "Dados atualizados com sucesso.".
4. **ACC-19** WHEN o usuário toca em "Salvar" sem ter alterado nenhum campo THEN o app SHALL não chamar a API e SHALL mostrar a mensagem "Nenhuma alteração para salvar.".
5. **ACC-20** IF um campo da tela está vazio ou em formato inválido (as regras de ACC-01, ACC-03 e ACC-06) THEN o app SHALL marcar o campo, mostrar o primeiro erro no `ErrorModal` e não chamar a API.
6. **ACC-21** IF o `PATCH` responde com erro THEN o app SHALL mostrar a mensagem do slug pelo `problemMessage` e manter na tela os valores digitados.
7. **ACC-22** WHILE o `PATCH` está em andamento o app SHALL deixar o "Salvar" desabilitado e mostrar um indicador de carregamento.

**Independent Test**: no web, trocar o nome e salvar. A mensagem de sucesso aparece, e a tela de perfil mostra o nome novo. Apagar o sobrenome e salvar: aparece o erro, e nenhuma requisição vai para a API.

---

### P1: Editar o endereço no app ⭐ MVP

**User Story**: Como cliente ou cabeleireiro que mudou de endereço, quero atualizá-lo pelo app com o mesmo autofill do cadastro.

**Why P1**: É o primeiro item da issue.

**Acceptance Criteria**:
1. **ACC-23** WHEN a tela `configs/addressSetting` abre THEN o app SHALL mostrar o CEP primeiro, com máscara, seguido de logradouro, número, complemento, bairro, cidade e UF, preenchidos com o endereço atual.
2. **ACC-24** WHEN o CEP digitado chega a 8 dígitos THEN o app SHALL consultar `GET /api/postal-codes/{cep}` pelo `useCepLookup` e preencher logradouro, bairro, cidade e UF com a resposta, sem apagar número nem complemento.
3. **ACC-25** IF a consulta do CEP responde 404 `postal-code-not-found` ou falha THEN o app SHALL mostrar a mensagem do slug e deixar os campos editáveis à mão.
4. **ACC-26** WHEN o usuário toca em "Salvar" com o endereço alterado e válido THEN o app SHALL enviar ao `PATCH /api/users/me` só os campos de endereço alterados, com o CEP só com os dígitos, e, no 200, SHALL recarregar o usuário e mostrar "Endereço atualizado com sucesso.".
5. The tela de endereço SHALL aplicar ACC-19 a ACC-22 aos campos dela. **(ACC-27)**

**Independent Test**: no web, digitar o CEP `69057-000`. Os campos são preenchidos, e o número continua o mesmo. Salvar e reabrir a tela: o endereço novo aparece.

---

### P1: Excluir a conta ⭐ MVP

**User Story**: Como cliente ou cabeleireiro, quero excluir minha conta pelo app e sair dele, para que meus dados deixem o Hairmatch.

**Why P1**: É critério de aceite da issue.

**Acceptance Criteria**:
1. The menu de configurações do cliente (`customer/profile.tsx`) e o do cabeleireiro (`hairdresser/profile/settings.tsx`) SHALL ter o item "Excluir conta". **(ACC-28)**
2. **ACC-29** WHEN o usuário toca em "Excluir conta" THEN o app SHALL abrir o `ConfirmationModal` com o texto "Esta ação é permanente. Sua conta, suas reservas e suas avaliações serão apagadas." e, para o cabeleireiro, também com "As reservas dos seus clientes serão canceladas.".
3. **ACC-30** WHEN o usuário confirma THEN o app SHALL chamar `DELETE /api/users/me` uma única vez, mesmo que toque de novo durante a requisição.
4. **ACC-31** WHEN o `DELETE` responde 204 THEN o app SHALL limpar `userToken` e `userInfo` sem chamar outra rota da API e SHALL levar o usuário à tela de login.
5. **ACC-32** WHEN `userInfo` fica nulo depois da exclusão ou do logout THEN as telas de perfil e de configurações SHALL não lançar erro de renderização (sem acesso a `.user` de um valor nulo).
6. **ACC-33** IF o `DELETE` responde com erro (503 `auth-unavailable`, 429 `too-many-requests` ou falha de conexão) THEN o app SHALL manter a sessão e mostrar a mensagem do slug pelo `problemMessage`.
7. **ACC-34** WHEN `DELETE /api/users/me` é chamado com uma sessão Google (`cognito_sub` nulo) THEN o backend SHALL apagar a conta, responder 204 e SHALL não chamar o Cognito.

**Independent Test**: no web, criar uma conta de teste, excluí-la pelo menu e confirmar. O app vai para o login, e logar com a mesma conta falha. No compose, o usuário some do pool do MiniStack.

---

### P2: Trocar e remover a foto de perfil

**User Story**: Como cliente ou cabeleireiro, quero trocar ou remover minha foto depois do cadastro.

**Why P2**: A issue pede, mas o perfil funciona sem foto.

**Acceptance Criteria**:
1. **ACC-35** WHEN `PUT /api/users/me/profile-picture` recebe multipart com uma imagem válida no campo `profile_picture` THEN o backend SHALL gravá-la pelo `WebPImageField` e responder 200 `{"profile_picture": "<url da foto nova>"}`.
2. **ACC-36** WHEN o `PUT` grava uma foto nova e o usuário já tinha uma THEN o backend SHALL apagar o arquivo anterior do storage depois do commit.
3. **ACC-37** IF o arquivo do `PUT` não é imagem THEN o backend SHALL responder 400 `invalid-image` e SHALL manter a foto e o arquivo anteriores.
4. **ACC-38** IF o `PUT` não traz o campo `profile_picture` THEN o backend SHALL responder 400 `validation-error` com o pointer `/profile_picture`.
5. **ACC-39** IF o arquivo do `PUT` tem mais de 5 MB (5 × 1024 × 1024 bytes) THEN o backend SHALL responder 400 `validation-error` com o pointer `/profile_picture` e SHALL não gravar nada.
6. **ACC-40** WHEN `DELETE /api/users/me/profile-picture` é chamado THEN o backend SHALL deixar `profile_picture` nulo, apagar o arquivo depois do commit e responder 204, inclusive quando o usuário já não tinha foto.
7. **ACC-41** IF `PUT` ou `DELETE /api/users/me/profile-picture` é chamado sem sessão válida THEN o backend SHALL responder 401 `invalid-session`.
8. The backend SHALL expor `PUT` e `DELETE /api/users/me/profile-picture` na Route Table (RT-88 e RT-89) e no `ROUTE_TABLE` de `backend/hairmatch/test_routes.py`, com `profile-picture` entre os segmentos singulares do RT-54. **(ACC-42)**
9. **ACC-43** WHEN o usuário toca na foto da tela de conta THEN o app SHALL oferecer "Escolher nova foto" e, se houver foto, também "Remover foto".
10. **ACC-44** WHEN o usuário escolhe uma imagem na galeria (recorte quadrado, qualidade 0.5) THEN o app SHALL enviá-la ao `PUT` em multipart e, no 200, SHALL recarregar o usuário e mostrar a foto nova.
11. **ACC-45** IF a permissão da galeria é negada THEN o app SHALL mostrar "Permita o acesso às fotos para trocar a foto de perfil." e SHALL não chamar a API.
12. **ACC-46** WHEN o usuário escolhe "Remover foto" THEN o app SHALL chamar o `DELETE` e, no 204, SHALL recarregar o usuário e mostrar a imagem padrão.

**Independent Test**: no web, trocar a foto. A foto nova aparece no perfil, e o bucket do LocalStack tem só o arquivo novo em `profile_pics/<id>/`. Remover a foto: a imagem padrão aparece, e o arquivo some.

---

### P2: Editar as preferências

**User Story**: Como cliente ou cabeleireiro, quero mudar minhas preferências depois do cadastro, para receber recomendações que combinam comigo.

**Why P2**: A issue pede. As recomendações continuam funcionando com as preferências do cadastro.

**Acceptance Criteria**:
1. The menu de configurações dos dois papéis SHALL ter o item "Preferências", que abre a tela `configs/preferencesSetting`. **(ACC-47)**
2. **ACC-48** WHEN a tela de preferências abre THEN o app SHALL mostrar o catálogo de `GET /api/preferences` com as preferências do usuário (`GET /api/users/{id}/preferences`) marcadas, e SHALL tratar o 404 dessa rota como nenhuma marcada.
3. **ACC-49** WHEN o usuário toca em "Salvar" THEN o app SHALL chamar `PUT /api/users/me/preferences/{id}` para cada preferência marcada que não estava e `DELETE /api/users/me/preferences/{id}` para cada uma desmarcada que estava, e nenhuma outra chamada.
4. **ACC-50** WHEN todas as chamadas de ACC-49 respondem 204 THEN o app SHALL mostrar "Preferências atualizadas com sucesso.".
5. **ACC-51** IF alguma chamada de ACC-49 falha THEN o app SHALL mostrar a mensagem do slug e recarregar as preferências do servidor, para que a tela mostre o que ficou gravado.
6. **ACC-52** IF o catálogo não carrega THEN o app SHALL mostrar a mensagem do slug e deixar o "Salvar" desabilitado.

**Independent Test**: no web, marcar uma preferência, desmarcar outra e salvar. Reabrir a tela: as duas mudanças aparecem. Com o backend parado, salvar mostra o erro de conexão.

---

### P2: Editar o resumo do cabeleireiro

**User Story**: Como cabeleireiro, quero reescrever o resumo do meu perfil, para que os clientes leiam uma apresentação atual.

**Why P2**: A issue pede. O perfil funciona com o resumo do cadastro.

**Acceptance Criteria**:
1. The menu de configurações do cabeleireiro SHALL ter o item "Resumo", que abre a tela `hairdresser/configs/resumeSetting` com o resumo atual em um campo de várias linhas. **(ACC-53)**
2. **ACC-54** WHILE o usuário digita no resumo o app SHALL mostrar a contagem "N/1000" e SHALL não aceitar mais de 1000 caracteres.
3. **ACC-55** WHEN o usuário toca em "Salvar" com o resumo alterado THEN o app SHALL enviar `PATCH /api/users/me` com `{"resume": "<texto>"}` e aplicar ACC-18 a ACC-22.

**Independent Test**: no web, como cabeleireiro, reescrever o resumo e salvar. O perfil público do cabeleireiro mostra o texto novo.

---

## Edge Cases

- IF o `PATCH` recebe um corpo que não é objeto JSON THEN o backend SHALL responder 400 `malformed-request`, como hoje (`json_object`). **(ACC-56)**
- IF o `PATCH` recebe `rating`, `role`, `cognito_sub`, `google_id` ou `is_active` THEN o backend SHALL ignorar esses campos. **(ACC-57)**
- WHEN o `PATCH` recebe `phone` cujos dígitos são iguais aos dígitos do telefone gravado do próprio usuário THEN o backend SHALL aceitar o corpo sem validar o formato do telefone, sem responder `phone-taken` e sem mudar o valor gravado. **(ACC-58)**
- IF a gravação falha depois que ACC-12 substituiu a conta pendente THEN a conta pendente SHALL continuar apagada, e o backend SHALL responder o erro da gravação, como no cadastro (EMC-12). **(ACC-60)**
- IF a sessão expira enquanto uma tela de configuração está aberta THEN o app SHALL seguir o fluxo atual do `axiosInstance` (refresh e, se falhar, login). **(ACC-59)**
- IF o `PUT` da foto recebe uma imagem que o `WebPImageField` não converte (arquivo corrompido) THEN o backend SHALL responder 400 `invalid-image` (coberto por ACC-37).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| ACC-01 | P1: Validar PATCH, AC1 | Tasks | Implementing |
| ACC-02 | P1: Validar PATCH, AC2 | Tasks | Implementing |
| ACC-03 | P1: Validar PATCH, AC3 | Tasks | Implementing |
| ACC-04 | P1: Validar PATCH, AC4 | Tasks | Implementing |
| ACC-05 | P1: Validar PATCH, AC5 | Tasks | Implementing |
| ACC-06 | P1: Validar PATCH, AC6 | Tasks | Implementing |
| ACC-07 | P1: Validar PATCH, AC7 | Tasks | Implementing |
| ACC-08 | P1: Validar PATCH, AC8 | Tasks | Implementing |
| ACC-09 | P1: Validar PATCH, AC9 | Tasks | Implementing |
| ACC-10 | P1: Validar PATCH, AC10 | Tasks | Implementing |
| ACC-11 | P1: Validar PATCH, AC11 | Tasks | Implementing |
| ACC-12 | P1: Validar PATCH, AC12 | Tasks | Implementing |
| ACC-13 | P1: Validar PATCH, AC13 | Tasks | Implementing |
| ACC-14 | P1: Validar PATCH, AC14 | Tasks | Implementing |
| ACC-15 | P1: Validar PATCH, AC15 | Tasks | Implementing |
| ACC-16 | P1: Dados da conta, AC1 | Tasks | Pending |
| ACC-17 | P1: Dados da conta, AC2 | Tasks | Implementing |
| ACC-18 | P1: Dados da conta, AC3 | Tasks | Pending |
| ACC-19 | P1: Dados da conta, AC4 | Tasks | Pending |
| ACC-20 | P1: Dados da conta, AC5 | Tasks | Implementing |
| ACC-21 | P1: Dados da conta, AC6 | Tasks | Pending |
| ACC-22 | P1: Dados da conta, AC7 | Tasks | Pending |
| ACC-23 | P1: Endereço, AC1 | Tasks | Pending |
| ACC-24 | P1: Endereço, AC2 | Tasks | Pending |
| ACC-25 | P1: Endereço, AC3 | Tasks | Pending |
| ACC-26 | P1: Endereço, AC4 | Tasks | Implementing |
| ACC-27 | P1: Endereço, AC5 | Tasks | Implementing |
| ACC-28 | P1: Excluir conta, AC1 | Tasks | Pending |
| ACC-29 | P1: Excluir conta, AC2 | Tasks | Pending |
| ACC-30 | P1: Excluir conta, AC3 | Tasks | Implementing |
| ACC-31 | P1: Excluir conta, AC4 | Tasks | Implementing |
| ACC-32 | P1: Excluir conta, AC5 | Tasks | Implementing |
| ACC-33 | P1: Excluir conta, AC6 | Tasks | Pending |
| ACC-34 | P1: Excluir conta, AC7 | Tasks | Implementing |
| ACC-35 | P2: Foto, AC1 | Tasks | Implementing |
| ACC-36 | P2: Foto, AC2 | Tasks | Implementing |
| ACC-37 | P2: Foto, AC3 | Tasks | Implementing |
| ACC-38 | P2: Foto, AC4 | Tasks | Implementing |
| ACC-39 | P2: Foto, AC5 | Tasks | Implementing |
| ACC-40 | P2: Foto, AC6 | Tasks | Implementing |
| ACC-41 | P2: Foto, AC7 | Tasks | Implementing |
| ACC-42 | P2: Foto, AC8 | Tasks | Implementing |
| ACC-43 | P2: Foto, AC9 | Tasks | Pending |
| ACC-44 | P2: Foto, AC10 | Tasks | Implementing |
| ACC-45 | P2: Foto, AC11 | Tasks | Pending |
| ACC-46 | P2: Foto, AC12 | Tasks | Implementing |
| ACC-47 | P2: Preferências, AC1 | Tasks | Pending |
| ACC-48 | P2: Preferências, AC2 | Tasks | Pending |
| ACC-49 | P2: Preferências, AC3 | Tasks | Implementing |
| ACC-50 | P2: Preferências, AC4 | Tasks | Pending |
| ACC-51 | P2: Preferências, AC5 | Tasks | Pending |
| ACC-52 | P2: Preferências, AC6 | Tasks | Pending |
| ACC-53 | P2: Resumo, AC1 | Tasks | Pending |
| ACC-54 | P2: Resumo, AC2 | Tasks | Implementing |
| ACC-55 | P2: Resumo, AC3 | Tasks | Pending |
| ACC-56 | Edge Cases | Tasks | Implementing |
| ACC-57 | Edge Cases | Tasks | Implementing |
| ACC-58 | Edge Cases | Tasks | Implementing |
| ACC-59 | Edge Cases | Tasks | Pending |
| ACC-60 | Edge Cases | Tasks | Implementing |

**ID format:** `ACC-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 60 total, 60 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] UAT manual no web e no Android, com um cliente e um cabeleireiro: editar os dados, o endereço (com autofill), as preferências e a foto; editar o resumo (cabeleireiro); excluir a conta e cair no login.
- [ ] A suíte do backend passa com todos os testes da baseline (`git grep -c "def test_"` em `fbf1d08`) mais os novos, sem nenhum teste removido.
- [ ] Cada critério de backend (ACC-01 a ACC-15, ACC-34 a ACC-42, ACC-56 a ACC-58 e ACC-60) tem pelo menos um teste automatizado que falha se o comportamento for removido.
- [ ] `cd frontend-mobile && npx tsc --noEmit` não ganha nenhum erro novo.
