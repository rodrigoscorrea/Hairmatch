# Configurações da conta Context

**Gathered:** 2026-10-09
**Spec:** `.specs/features/account-settings/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Cliente e cabeleireiro mudam pelo app, depois do cadastro:
- os dados da conta (nome, sobrenome, telefone e CPF ou CNPJ);
- o endereço;
- as preferências;
- a foto de perfil;
- o resumo (só o cabeleireiro).

Os dois também excluem a própria conta e saem do app.

O e-mail aparece somente leitura. Nada aqui troca credencial: senha e e-mail ficam no card [#175](https://github.com/rodrigoscorrea/Hairmatch/issues/175).

---

## Implementation Decisions

### Divisão da issue #120 depois do Cognito

A #120 foi escrita antes do Cognito (#139) e da confirmação de e-mail (#141). O usuário decidiu tirar dela **tudo o que é senha e e-mail**, que agora fica no card #175:
- alterar a senha logado;
- "esqueci minha senha";
- trocar o e-mail.

Motivos:
- O e-mail é o username no Cognito. Trocá-lo exige `AdminUpdateUserAttributes` e verificação, e o `admin_delete_user` e o `admin_get_*` buscam o usuário pelo e-mail.
- "Esqueci minha senha" é uma rota anônima que dispara e-mail, então exige o par de throttles do AD-008.
- A troca de senha logado já tem backend (`PUT /api/users/me/password`). Mesmo assim, foi para o card novo, para que todo o fluxo de senha seja projetado junto. Isso inclui saber se a conta é Google, que não tem senha.

### Foto de perfil

- Fica nesta feature. O backend ganha `PUT` e `DELETE /api/users/me/profile-picture`, porque hoje a foto só é gravada no cadastro.
- A rota entra na Route Table do `api-restful-routes` (RT-88 e RT-89). `profile-picture` vira um segmento singular permitido, como `password`.

### Exclusão de conta

- O backend já faz tudo:
  - cancela as reservas;
  - apaga o usuário no Cognito;
  - apaga as fotos depois do commit;
  - limpa os cookies.
- Esta feature só cobre o app e um teste que faltava, o da conta Google.
- A confirmação é só o modal: não se pede a senha, porque a conta Google não tem senha.

### Agent's Discretion

- O layout das telas novas (preferências e resumo) segue o das telas de `configs` e do wizard.
- Os nomes dos hooks e dos serviços novos.
- Como o app escolhe entre trocar e remover a foto: um modal com as duas opções.

### Declined / Undiscussed Gray Areas → Assumptions

Todas estão registradas na seção Assumptions do spec, com o padrão escolhido:
- CPF e CNPJ continuam editáveis;
- limite de 1000 caracteres no resumo;
- limite de 5 MB na foto;
- sair da tela sem salvar descarta as alterações;
- o `PATCH` continua respondendo `{message}`;
- o app trata o 404 de preferências vazias;
- a exclusão não pede senha.

---

## Specific References

- A tela de endereço repete o comportamento do cadastro (`app/(auth)/register/address.tsx`): CEP primeiro, autofill e travamento dos campos (feature `cep-autocomplete`).
- O seletor de preferências repete o do cadastro (`app/(auth)/register/preferences.tsx`).
- A foto usa o mesmo seletor do cadastro (`useRegisterForm.ts`) e o mesmo upload multipart da avaliação (`useReviewForm.ts`).

---

## Deferred Ideas

- Alterar a senha, "esqueci minha senha" e trocar o e-mail: #175.
- Avisar os clientes quando um cabeleireiro exclui a conta: #171, que depende de #172.
- Regenerar o resumo por IA depois do cadastro. Exige guardar `experience_time`, `experiences` e `products`, que hoje se perdem.
- Editar `experience_years`.
- Responder 200 `[]` em vez de 404 em `GET /api/users/{id}/preferences` sem preferências. É uma mudança de contrato da API, fora daqui.
