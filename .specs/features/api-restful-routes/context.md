# Rotas da API em RFC 3986 Context

**Gathered:** 2026-09-30
**Spec:** `.specs/features/api-restful-routes/spec.md`
**Status:** Ready for design (aguardando confirmação do spec)

---

## Feature Boundary

Todas as rotas sob `/api/` passam para a Route Table do spec: recursos no plural, hierarquia no path, filtros na query e métodos HTTP corretos. As regras de negócio, a autenticação e os corpos de sucesso não mudam, exceto os itens da coluna "Mudança além do path". O app passa a usar só as rotas novas. O formato de erro vem da `api-problem-details`, que precisa estar entregue antes.

---

## Implementation Decisions

### Migração

- Corte único. Backend e app saem no mesmo release, as rotas antigas somem e não há `/v1`.
- Uma rota antiga responde 404 `not-found` em problem+json, como qualquer rota inexistente.

### RFC 3986 × convenção

- A RFC 3986 não obriga a trocar nenhuma rota atual, porque todas são URIs válidas. O que ela orienta:
  - Hierarquia no path (§3.3).
  - Dado não hierárquico na query (§3.4).
  - Percent-encoding de dado variável (§2.1). Esse item tira o e-mail do path.
- Plural, kebab-case e ausência de verbo são convenção REST. Métodos seguros e idempotentes vêm da RFC 9110.
- O spec registra essa separação na seção "Avaliação RFC 3986", como a issue pede ("deve ser avaliado").

### Webhook do chatbot

- Passa de `/api/chatbot/test` para `/api/chatbot/webhook`.
- A URL do webhook fica na instância da Evolution API, fora do repositório. Reconfigurá-la é passo operacional e exige autorização explícita antes do deploy em produção.

### Agent's Discretion

Os nomes dos recursos foram escolhidos pelo agente. O usuário pode trocar qualquer um na confirmação do spec:
- `reservations`
- `agenda`
- `postal-codes`
- `description-drafts`
- `available-slots`
- `search?q=`
- `customers/me/home` e `home`

### Declined / Undiscussed Gray Areas → Assumptions

Todas estão no Assumptions & Open Questions do spec:
- Remoção de `user/<email>`.
- `auth/*` mantidos como controllers de sessão.
- PATCH nos updates parciais.
- `parameter` em vez de `pointer` para erro de query.
- CEP com a mesma normalização de hoje.

---

## Specific References

**Notas para o Design:**
- Um mesmo path com vários métodos (`/api/agenda`: GET e POST; `/api/services/{id}`: GET, PUT e DELETE) exige juntar views que hoje são classes separadas (`ListAgenda` + `CreateAgenda`, `ListService` + `UpdateService` + `RemoveService`) ou um dispatcher por path.
- As rotas `/api/hairdressers/{id}/...` atravessam apps (`users`, `review`, `availability`, `agenda`, `service`, `reserve`). O `backend/hairmatch/urls.py` deixa de montar um prefixo por app.
- O `AUTH_EXCLUDED` do app (`services/axios-instance.ts:7`) compara por `includes`. Com `POST /api/users` na lista, uma comparação por substring excluiria `/api/users/me` do refresh. Por isso o RT-71 exige comparação exata.
- Os serviços do app montam URLs absolutas (`${API_BACKEND_URL}/api/...`) e relativas. A comparação exata do RT-71 precisa antes normalizar as duas para o pathname, sem host e sem query string.
- O refresh está duplicado em `services/axios-instance.ts:33` e `app/_layout.tsx:150` (RT-73).
- Rotas que o app não chama e podem mudar sem ajuste no app (mapa do app, §1):
  - `auth/change-password`
  - `user/<email>`
  - `service/list` sem id
  - `availability/create`, `availability/update/<id>`, `availability/remove/<id>`
  - `reserve/list` sem id, `reserve/remove/<id>`
  - `agenda/*`
  - `review/list`, `review/update`
  - `preferences/list/users`, `preferences/assign`, `preferences/unassign`
  - `chatbot/test`
  - `customer/home` sem e-mail

---

## Deferred Ideas

- Validar a assinatura do webhook da Evolution API (F9 da auditoria de segurança).
- Uniformizar os envelopes de sucesso: `data` em toda resposta, e fim das listas cruas nas preferências.
- Devolver o recurso criado e o header `Location` nos 201.
