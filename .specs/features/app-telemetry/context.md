# Telemetria da aplicação Context

**Gathered:** 2026-11-07
**Spec:** `.specs/features/app-telemetry/spec.md`
**Status:** Ready for design (aguarda a aprovação do spec)

---

## Feature Boundary

O backend Django passa a emitir traces, métricas e logs por OpenTelemetry ao Collector da #193, e o app Expo passa a mandar um `traceparent` em cada chamada à API. Com a telemetria desligada ou fora do ar, a aplicação se comporta igual. Faro, Crashlytics, Pyroscope, alertas, Gunicorn e VPS ficam de fora.

---

## Implementation Decisions

### Métricas de negócio

- Entram os 10 contadores do estudo, menos `hairmatch.chatbot.messages`, porque o chatbot está deprecado por enquanto. São 9:
  - `problems`
  - `reserves.created`
  - `push.results`
  - `auth.rejections`
  - `signup.events`
  - `uploads`
  - `cep.lookups`
  - `ai.requests`
  - `ai.tokens`
- Cada rótulo tem um conjunto fechado de valores, enumerado no spec (TEL-50 a TEL-60).

### `traceparent` no app

- Vale na web e no Android, ligado pela variável nova `EXPO_PUBLIC_TRACE_PROPAGATION=true`. Ela vem desligada por padrão.
- O backend aceita `traceparent` no `CORS_ALLOW_HEADERS` na mesma mudança. Sem isso, o preflight da web quebra todas as chamadas.
- O código fica em `utils/telemetry.ts` e `utils/telemetry.web.ts`, no padrão do `push-registration`.
- O app não ganha dependência nativa nova. O `expo-crypto` fica de fora, para não exigir rebuild do Android.

### Branch

- `194-integracao-telemetria` sai da `193-infra-de-observabilidade` em `b2145f4`, a versão do PR #195.
- Quando o PR #195 entrar na `develop`, a 194 é rebaseada sobre a `develop`.

### Agent's Discretion

- O gancho de inicialização no `runserver` (hoje). Ele precisa respeitar TEL-04 e TEL-05.
- A biblioteca do formatador JSON e as versões fixadas do OpenTelemetry. O Design confere a compatibilidade com o Django 5.2, o Python 3.12 e o psycopg2.
- A rota instrumentada usada na medição de latência de TEL-10.
- Como limitar a frequência dos logs de erro de exportação (TEL-15).

### Declined / Undiscussed Gray Areas → Assumptions

Os itens abaixo não foram discutidos com o usuário e estão na tabela de Assumptions do spec, com o padrão escolhido e o motivo:

- a divisão do AC da reserva (sem S3) e o upload como prova do S3;
- o Gemini com span manual, sem httpx;
- o limite de 50 ms no p95;
- os limites da exportação (2 s, fila de 2048 e desligamento em 5 s);
- os três modos de Collector fora do ar;
- só variáveis `OTEL_*` padrão no backend;
- o `url.path` fora dos spans;
- os rótulos `outcome`, `source`, `reason` e `feature`;
- a rota `/api/health` com o slug `service-unavailable`;
- logs em JSON também em dev;
- o nível `INFO` fixo.

---

## Specific References

- O estudo "Observabilidade Hairmatch", seção 6, nas abas Gunicorn · SDK, LOGGING, métricas e spans manuais, e a seção 7 (LGPD).
- O dashboard `docker/observability/grafana/dashboards/api-red.json` e os atalhos trace → logs de `docker/observability/grafana/provisioning/datasources/datasources.yaml`, ambos da #193. Os nomes das métricas e o campo `trace_id` seguem esses arquivos.
- Os marcadores e a ordem da redação seguem `docker/observability/otel/config.yaml`.

---

## Deferred Ideas

- A chave de idempotência em `POST /api/reserves` e a mensagem "confira sua agenda" no timeout (seção 5 do estudo).
- O contador `hairmatch.chatbot.messages`, quando o chatbot voltar.
- Migrar o Gemini para o `google-genai` e usar a instrumentação do SDK novo.
- Faro na web e Crashlytics no Android, com o `trace_id` salvo no Crashlytics.
