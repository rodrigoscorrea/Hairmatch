# Preenchimento de Endereço via CEP Specification

**Issue:** [#128](https://github.com/rodrigoscorrea/Hairmatch/issues/128)
**Escopo:** Large (chamada externa, endpoint anônimo e concorrência no app)
**Plataformas:** Web e Android. A tela de endereço é a mesma nos cadastros por e-mail/senha e por Google.

## Problem Statement

Hoje a etapa de endereço do cadastro (`frontend-mobile/app/(auth)/register/address.tsx`) pede sete campos digitados à mão, e o CEP só aparece na terceira linha. Isso deixa o cadastro lento e abre espaço para erros de digitação em rua, bairro, cidade e UF.

A issue #128 pede que esses campos sejam preenchidos a partir do CEP, usando uma API pública de CEP, e que as dependências dessa API sejam investigadas.

## Goals

- [ ] Ao digitar um CEP válido e existente, o usuário vê rua, bairro, cidade e UF preenchidos em até 6 s, e só digita número e complemento.
- [ ] Uma falha da consulta (CEP inexistente, provedor fora do ar, rate limit) nunca impede o cadastro: o usuário sempre pode preencher o endereço à mão.
- [ ] A integração não exige cadastro, chave nem contrato com nenhum provedor.

## Investigação da API de CEP (dependências e contrato)

Consultas feitas com curl em 2026-09-29.

| Provedor | Quem opera | Cadastro / chave | Contrato de resposta | Decisão |
| -------- | ---------- | ---------------- | -------------------- | ------- |
| ViaCEP (`https://viacep.com.br/ws/{cep}/json/`) | Projeto independente, com base IBGE/Correios | Nenhum | 200 com `logradouro, complemento, bairro, localidade, uf, ...`. CEP inexistente devolve **200 com `{"erro": "true"}`**. Formato inválido devolve 400 em HTML. CORS aberto. | **Principal** |
| BrasilAPI v2 (`https://brasilapi.com.br/api/cep/v2/{cep}`) | Projeto comunitário que agrega Correios, ViaCEP, WideNet e OpenCEP | Nenhum | 200 com `cep, state, city, neighborhood, street, location`. CEP inexistente devolve 404, e formato inválido devolve 400, ambos em JSON `CepPromiseError`. Campos ausentes vêm como `null`. | **Fallback** |
| API Busca CEP dos Correios (`https://api.correios.com.br/cep/v2/enderecos`) | Correios, empresa estatal | **Exige** contrato comercial com o serviço 86738, conta no Meu Correios, credenciais no CWS (`cws.correios.com.br`) e um token Bearer gerado em `/v1/autentica/contrato`, que precisa ser renovado quando expira | Bearer + JSON | **Descartada**. Não há contrato. |

Política de uso: ViaCEP e BrasilAPI proíbem uso massivo e varredura da base, e o ViaCEP bloqueia o IP por tempo indeterminado quando isso acontece. O proxy mitiga esse risco com cache e rate limit (CEP-08, CEP-10).

### Mapeamento dos campos do formulário

| Campo do form (`User`) | ViaCEP | BrasilAPI v2 | Preenchido automaticamente? |
| ---------------------- | ------ | ------------ | --------------------------- |
| `address` (rua) | `logradouro` | `street` | Sim. Vem vazio em CEP geral de cidade, como 78175-000 (Poconé/MT). |
| `neighborhood` | `bairro` | `neighborhood` | Sim. Também vem vazio em CEP geral de cidade. |
| `city` | `localidade` | `city` | Sim |
| `state` (UF) | `uf` | `state` | Sim |
| `postal_code` | `cep` | `cep` | Normalizado para 8 dígitos. O campo já foi digitado pelo usuário. |
| `number` | — | — | **Não**. Só o usuário sabe. |
| `complement` | `complemento` | — | **Não**. O `complemento` do ViaCEP descreve a faixa do CEP ("até 436/437", "lado ímpar") e não o apartamento ou bloco do usuário. |
| latitude/longitude | — | `location.coordinates` | Não. O modelo `User` não tem esses campos (ver Out of Scope). |

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| API oficial dos Correios | Exige contrato comercial, cadastro no Meu Correios e no CWS e renovação de token. Nada disso existe hoje. |
| Telas `configs/addressSetting.tsx` (cliente e cabeleireiro) | Hoje são somente leitura e o botão Salvar não faz nada (RF-EXT-13, parcial em `docs/requisitos-status.md`). A edição de endereço é outra feature. |
| Validação ou consulta de CEP em `UserInfoCookieView.put` | Depende da edição de endereço acima. |
| Validar o formato de `postal_code` no `RegisterView` | Mudaria cerca de 20 fixtures `'12345'` em `backend/users/tests.py`. Fica como follow-up. O app já exige 9 caracteres com máscara (`useAddress.ts`). |
| Guardar latitude e longitude | O modelo não tem esses campos, e nenhuma feature os usa hoje. |
| Cache persistente (Redis) | `CACHES` não está configurado. O `LocMemCache` padrão basta para o volume do cadastro. |
| Busca reversa (endereço → CEP) | Não foi pedida na issue. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Provedor | ViaCEP como principal e BrasilAPI v2 como fallback | Escolha do usuário. Os dois são gratuitos e não pedem cadastro, e o fallback cobre quedas do ViaCEP. | y |
| Arquitetura | O app chama um proxy no backend (`GET /api/address/cep/<cep>`), nunca o provedor | Escolha do usuário. Dá um contrato único, timeout, fallback, cache, rate limit e testes no Django. Condiz com o rótulo Back/Front da issue. | y |
| Comportamento dos campos preenchidos | Continuam editáveis | Escolha do usuário. A base de CEP pode estar desatualizada. | y |
| Valor vazio vindo do provedor | Limpa o campo se ele ainda tem o valor do preenchimento automático anterior; mantém se o usuário digitou algo (CEP-13) | Não apaga o que o usuário digitou e não deixa a rua de um CEP anterior junto com a cidade de outro. | n |
| Onde mostrar erros da consulta | Texto inline abaixo do CEP, sem `ErrorModal` | Uma falha na consulta não é erro de validação e não deve interromper o preenchimento. | n |
| Timeout por provedor | 3 s (no pior caso, 6 s com o fallback) | Fica abaixo do timeout de 10 s de `frontend-mobile/services/axios-instance.ts`. | n |
| Cache | `django.core.cache` (LocMemCache padrão), por 24 h, só para CEP encontrado | Não precisa de infraestrutura nova. Não cachear 404 deixa um CEP recém-criado ser encontrado sem esperar o TTL. Cada worker tem o próprio cache, o que é aceitável. | n |
| Rate limit | 30 requisições por minuto por IP (throttle DRF) | Um cadastro faz de 1 a 3 consultas. O limite corta varredura sem atrapalhar o uso real. | n |
| Quando um provedor diz "não encontrado" | Ainda tenta o próximo, e responde 404 só se nenhum encontrar | As bases diferem, e um CEP novo pode existir em uma e não na outra. | n |
| Testes do app | Só manual. O gate é `npx tsc --noEmit` mais o roteiro de UAT. | O app não tem nenhum teste nem testing-library. É o mesmo critério confirmado na feature google-auth. | y |
| Mensagens | Em português. No backend vão no campo `error` do JSON, como nas views atuais. | Mantém o contrato do app. | n |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## User Stories

### P1: Consulta de CEP no backend ⭐ MVP

**User Story**: Como app do Hairmatch, quero um endpoint próprio que devolva o endereço de um CEP num formato fixo, para não depender do contrato de nenhum provedor externo.

**Why P1**: É a metade Back da issue. Sem o endpoint, o app não tem de onde tirar o endereço.

**Acceptance Criteria**:

1. **CEP-01** WHEN `GET /api/address/cep/<cep>` recebe um CEP de 8 dígitos (com ou sem hífen) que o ViaCEP encontra THEN o backend SHALL responder 200 com exatamente as chaves `postal_code`, `address`, `neighborhood`, `city` e `state`, com `postal_code` em 8 dígitos e sem hífen. Exemplo: `69057-000` → `{"postal_code": "69057000", "address": "Avenida Mário Ypiranga", "neighborhood": "Adrianópolis", "city": "Manaus", "state": "AM"}`.
2. **CEP-02** IF o CEP, sem os caracteres não numéricos, não tem exatamente 8 dígitos THEN o backend SHALL responder 400 com `{"error": "CEP inválido. Informe 8 dígitos."}` sem chamar nenhum provedor.
3. **CEP-03** IF o ViaCEP estourar o timeout, der erro de conexão, responder com status diferente de 200, devolver JSON inválido ou responder `{"erro": "true"}` THEN o backend SHALL consultar a BrasilAPI v2 e, se ela encontrar o CEP, responder 200 no formato do CEP-01.
4. **CEP-04** IF nenhum provedor encontrar o CEP e pelo menos um deles responder "não encontrado" (ViaCEP `{"erro": "true"}` ou BrasilAPI 404) THEN o backend SHALL responder 404 com `{"error": "CEP não encontrado."}`.
5. **CEP-05** IF os dois provedores falharem por timeout, erro de conexão, status inesperado ou JSON inválido THEN o backend SHALL responder 503 com `{"error": "Serviço de CEP indisponível. Preencha o endereço manualmente."}`.
6. **CEP-06** The backend SHALL passar `timeout=3` (segundos) em toda chamada HTTP a um provedor de CEP.
7. **CEP-07** The backend SHALL converter todo campo de endereço `null` ou ausente vindo de um provedor em `""`, e SHALL nunca incluir `complemento` nem outras chaves do provedor na resposta.
8. **CEP-08** WHEN um CEP é encontrado THEN o backend SHALL guardar a resposta normalizada no cache do Django, na chave `cep:<8 dígitos>`, por 24 h (86400 s). Uma nova consulta do mesmo CEP nesse período SHALL responder sem chamar nenhum provedor.
9. **CEP-09** The endpoint SHALL responder sem exigir o cookie `jwt`, porque o cadastro acontece antes do login.
10. **CEP-10** IF o mesmo IP fizer mais de 30 requisições ao endpoint em 60 s THEN o backend SHALL responder 429 às requisições excedentes.
11. **CEP-11** WHEN um provedor falha (timeout, conexão, status inesperado ou JSON inválido) THEN o backend SHALL registrar um `logger.warning` com o nome do provedor (`viacep` ou `brasilapi`) e o motivo.

**Independent Test**: `curl http://localhost:8000/api/address/cep/69057-000` devolve 200 com o JSON do CEP-01, sem cookie. `.../cep/123` devolve 400, e `.../cep/00000000` devolve 404.

---

### P1: Preenchimento automático na tela de endereço ⭐ MVP

**User Story**: Como cliente ou cabeleireiro se cadastrando, quero que rua, bairro, cidade e UF sejam preenchidos quando eu digitar o CEP, para terminar o cadastro mais rápido e sem erro de digitação.

**Why P1**: É a metade Front da issue e o valor que o usuário enxerga.

**Acceptance Criteria**:

1. **CEP-12** WHEN o campo CEP da tela de endereço passa a ter 8 dígitos THEN o app SHALL chamar `GET /api/address/cep/<8 dígitos>` uma vez para aquele valor.
2. **CEP-13** WHEN o endpoint responde 200 THEN o app SHALL aplicar, para cada campo `address`, `neighborhood`, `city` e `state` do `RegistrationContext`, as regras abaixo e guardar os valores gravados como "último preenchimento automático":
   - valor não vazio na resposta → grava esse valor
   - valor vazio na resposta, com o campo ainda igual ao último preenchimento automático → grava `""`
   - valor vazio na resposta, com o campo contendo algo que o usuário digitou → mantém o campo
3. **CEP-14** The app SHALL nunca alterar `number` nem `complement` como resultado de uma consulta de CEP.
4. **CEP-15** WHILE uma consulta de CEP está em andamento, o app SHALL mostrar um `ActivityIndicator` junto ao campo CEP e SHALL manter todos os campos e o botão "Próximo" habilitados.
5. **CEP-16** IF a resposta de uma consulta chegar depois que o campo CEP mudou para outro valor THEN o app SHALL descartar essa resposta, sem alterar campos nem mensagens.
6. **CEP-17** IF o endpoint responder 404 THEN o app SHALL mostrar abaixo do CEP o texto "CEP não encontrado. Confira o número ou preencha o endereço manualmente." e SHALL não abrir o `ErrorModal`.
7. **CEP-18** IF o endpoint responder 400, 429 ou 503, ou a requisição falhar por rede ou timeout, THEN o app SHALL mostrar abaixo do CEP o texto "Não foi possível buscar o CEP. Preencha o endereço manualmente." e SHALL não abrir o `ErrorModal`.
8. **CEP-19** The app SHALL manter editáveis os campos preenchidos pela consulta, e a validação de "Próximo" (`useAddress.validateFields`) SHALL continuar sendo a única regra para avançar.

**Independent Test**: No cadastro, digitar `69057-000` preenche "Avenida Mário Ypiranga", "Adrianópolis", "Manaus" e "AM", e deixa Número e Complemento vazios. Digitar `00000-000` mostra o texto de CEP não encontrado.

---

### P2: Ergonomia da tela de endereço

**User Story**: Como usuário no cadastro, quero começar pelo CEP e cair direto no campo Número, para digitar só o que a consulta não sabe.

**Why P2**: A consulta funciona com o CEP em qualquer posição, mas começar pela rua e depois achar o CEP embaixo anula o ganho.

**Acceptance Criteria**:

1. **CEP-20** The tela de endereço SHALL mostrar o campo CEP como primeiro campo do formulário, acima de Endereço e Número.
2. **CEP-21** WHEN uma consulta de CEP responde 200 e a resposta não foi descartada (CEP-16) THEN o app SHALL mover o foco para o campo Número.

**Independent Test**: Abrir a tela de endereço mostra o CEP no topo. Após uma consulta bem-sucedida, o teclado fica no campo Número.

---

## Edge Cases

- WHEN o CEP é geral de cidade (ex.: `78175-000`) THEN o backend SHALL responder 200 com `address: ""` e `neighborhood: ""`, e o app SHALL preencher só cidade e UF, mantendo o que o usuário já digitou em rua e bairro (CEP-07, CEP-13).
- WHEN o usuário troca `69057-000` (já preenchido automaticamente) por `78175-000` sem editar rua nem bairro THEN o app SHALL limpar rua e bairro e gravar "Poconé" e "MT" (CEP-13).
- IF a BrasilAPI devolver `null` em `street` ou `neighborhood` THEN o backend SHALL devolver `""` nesses campos (CEP-07).
- IF o ViaCEP devolver HTML com status 400 THEN o backend SHALL tratar como falha do provedor e seguir para a BrasilAPI (CEP-03). Esse caso só ocorre com formato inválido, que o CEP-02 já barra antes.
- WHEN o usuário apaga um dígito depois de uma consulta THEN o app SHALL não disparar nova consulta até voltar a ter 8 dígitos, e SHALL descartar a resposta em andamento (CEP-12, CEP-16).
- WHEN o usuário cola `69057000` sem hífen THEN o `formatCEP` existente SHALL mascarar para `69057-000` e a consulta SHALL ocorrer normalmente (CEP-12).
- IF a consulta falhar THEN o usuário SHALL conseguir preencher tudo à mão e avançar, com as mesmas validações de hoje (CEP-18, CEP-19).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| CEP-01 | P1: Consulta de CEP no backend, AC1 | Tasks | Pending |
| CEP-02 | P1: Consulta de CEP no backend, AC2 | Tasks | Pending |
| CEP-03 | P1: Consulta de CEP no backend, AC3 | Tasks | Pending |
| CEP-04 | P1: Consulta de CEP no backend, AC4 | Tasks | Pending |
| CEP-05 | P1: Consulta de CEP no backend, AC5 | Tasks | Pending |
| CEP-06 | P1: Consulta de CEP no backend, AC6 | Tasks | Pending |
| CEP-07 | P1: Consulta de CEP no backend, AC7 | Tasks | Pending |
| CEP-08 | P1: Consulta de CEP no backend, AC8 | Tasks | Pending |
| CEP-09 | P1: Consulta de CEP no backend, AC9 | Tasks | Pending |
| CEP-10 | P1: Consulta de CEP no backend, AC10 | Tasks | Pending |
| CEP-11 | P1: Consulta de CEP no backend, AC11 | Tasks | Pending |
| CEP-12 | P1: Preenchimento automático, AC1 | Tasks | Pending |
| CEP-13 | P1: Preenchimento automático, AC2 | Tasks | Pending |
| CEP-14 | P1: Preenchimento automático, AC3 | Tasks | Pending |
| CEP-15 | P1: Preenchimento automático, AC4 | Tasks | Pending |
| CEP-16 | P1: Preenchimento automático, AC5 | Tasks | Pending |
| CEP-17 | P1: Preenchimento automático, AC6 | Tasks | Pending |
| CEP-18 | P1: Preenchimento automático, AC7 | Tasks | Pending |
| CEP-19 | P1: Preenchimento automático, AC8 | Tasks | Pending |
| CEP-20 | P2: Ergonomia, AC1 | Tasks | Pending |
| CEP-21 | P2: Ergonomia, AC2 | Tasks | Pending |

**Coverage:** 21 total, 21 mapped to tasks, 0 unmapped.

---

## Success Criteria

- [ ] Com o CEP `69057-000`, o cadastro completo (cliente e cabeleireiro, por senha e por Google) exige digitar só Número e, se houver, Complemento na etapa de endereço.
- [ ] Com o backend sem acesso à internet, a etapa de endereço mostra a mensagem do CEP-18 e o cadastro termina com preenchimento manual.
- [ ] Nenhum teste existente do backend deixa de passar, e o número de testes só aumenta.
