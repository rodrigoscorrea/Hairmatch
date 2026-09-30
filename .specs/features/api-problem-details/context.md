# Erros da API em RFC 9457 Context

**Gathered:** 2026-09-30
**Spec:** `.specs/features/api-problem-details/spec.md`
**Status:** Implementado. Só o UAT das cinco telas do app está pendente (ver `validation.md`).

---

## Feature Boundary

Todo erro sob `/api/` passa a sair em `application/problem+json` (RFC 9457), com um `type` do catálogo do spec. Todo texto da API fica em inglês, e os status seguem a RFC 9110. O app traduz os erros para pt-BR pelo slug do `type`. Nenhuma rota muda de path: isso é a feature `api-restful-routes`.

---

## Implementation Decisions

### Divisão da issue #161

- Duas features. Esta cobre RFC 9457, mensagens em inglês e status corretos. A `api-restful-routes` vem depois e cobre a RFC 3986 e o redesenho das rotas.
- Motivo: formato de erro e tradução reescrevem as mesmas linhas e os mesmos ~80 asserts. Fazer as duas coisas juntas evita tocar cada linha duas vezes.

### Como o app mostra erros

- Um normalizador único converte a resposta de erro em `ApiProblem { slug, status, detail, errors }`. Ele cobre o `axiosInstance`, o axios cru do `signUp` no web e o `fetch` do `signUp` no native.
- Um catálogo pt-BR indexado pelo slug dá o texto que a UI mostra. O `detail` em inglês nunca aparece para o usuário.
- Sem slug conhecido, a tela usa o fallback genérico que já tem hoje.

### Status HTTP

- Corrigidos nesta feature: conflitos 400→409, `Service not found` da agenda 500→404, papel errado 404→403, PUT do bulk de disponibilidade 201→200, DELETE 200→204.
- O app se ajusta onde depende de status: `useServiceManager` passa a olhar o slug `service-has-reservations` em vez do 400. O CEP 404 continua igual.

### Migração

- Corte único: backend e app no mesmo release, sem período de compatibilidade com `{"error"}`. O app é o único cliente da API REST. O webhook do chatbot é chamado pela Evolution API, que não lê o corpo da resposta.

### Agent's Discretion

- A forma da URI do `type`: `https://hairmatch.app/problems/<slug>`, vinda de uma constante em settings.
- Os nomes dos slugs, os `title` em inglês e os textos pt-BR do catálogo. Os textos pt-BR reaproveitam as mensagens que o backend devolve hoje.
- Onde fica o módulo central de problems no backend e como ele se liga ao DRF e ao Django (decisão do Design).

### Declined / Undiscussed Gray Areas → Assumptions

Todas estão no Assumptions & Open Questions do spec:
- Extensão `errors` só em `validation-error`.
- Senha atual incorreta continua 400.
- `GET /api/auth/user` continua 200.
- Troca de e-mail continua 400.
- Gate do app é `tsc` + UAT.

---

## Specific References

- RFC 9457 §3: membros `type`, `title`, `status`, `detail`, `instance`, e o exemplo de extensão `errors` com `pointer` em JSON Pointer.
- A página de erro HTML do Django aparece hoje porque `DEBUG=True` está fixo em `backend/hairmatch/settings.py:28`.
- O DRF 3.15 não tem `REST_FRAMEWORK` configurado. Os erros dele saem como `{"detail": "..."}` pelo `rest_framework.views.exception_handler`.

---

## Deferred Ideas

- Tornar atômicos `CreateMultipleAvailability` e `UpdateMultipleAvailability`, que hoje podem criar ou apagar parcialmente.
- Validar a assinatura do webhook da Evolution API (`chatbot/views.py`).
- Ler `DEBUG` do ambiente em vez de `True` fixo.
- `User.ROLES_CHOICES` invertido (`('CUSTOMER','customer')`) enquanto as views comparam com `'customer'` minúsculo.
- Página HTML para cada `type` do catálogo (URI dereferenciável).
