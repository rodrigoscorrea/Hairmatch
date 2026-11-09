# Hairmatch — Stack de observabilidade local

Issue [#193](https://github.com/rodrigoscorrea/Hairmatch/issues/193). A stack mora em `docker/observability/` e é o destino local da telemetria que o backend e o app geram desde a #194. Ela também é o ensaio da implantação no Grafana Cloud: o mesmo Collector e a mesma configuração, trocando só variáveis de ambiente.

```
app / navegador ──OTLP/HTTP──▶ OTel Collector ──▶ Tempo      (traces)
                              (redige PII)    ──▶ Prometheus (métricas)
Faro (navegador) ─▶ Alloy ───OTLP──▶ Collector ──▶ Loki       (logs)
                                                    └────────▶ Grafana lê os três + Pyroscope
```

O Collector é o único ponto de entrada. Ele apaga e-mail, JWT, CPF, CNPJ e telefone antes de exportar, qualquer que seja o destino.

## Subir e derrubar

Rode **um modo por vez**: os dois publicam as mesmas portas e os mesmos nomes de container, e o segundo `up` falha.

### Preparação (uma vez, no modo combinado)

O `docker/.env` precisa de `OBS_DIR=./observability` (já está no `docker/.env.example`). No modo combinado, o Compose resolve os caminhos relativos a partir de `docker/`, e sem essa variável os mounts viram diretórios vazios. Se o seu `docker/.env` é antigo, acrescente a linha.

### Sozinha

```bash
docker compose -f docker/observability/docker-compose.observability.yml up -d
docker compose -f docker/observability/docker-compose.observability.yml down
```

O projeto se chama `observability`. Sem `docker/observability/.env`, valem os padrões do compose (destino local, `OBS_DIR=.`). Nesse modo o postgres-exporter não alcança o banco, e o Prometheus mostra `pg_up 0`. Isso é esperado.

> Nunca passe `--env-file docker/.env` neste modo: o `OBS_DIR=./observability` do arquivo faria os mounts apontarem para `docker/observability/observability/…`.

### Junto do app (modo combinado)

```bash
docker compose -f docker/docker-compose.yml -f docker/observability/docker-compose.observability.yml up -d
docker compose -f docker/docker-compose.yml -f docker/observability/docker-compose.observability.yml down
```

Os dois arquivos viram um projeto só (`hairmatch`) e dividem a `app_network`. É o modo em que o `hairmatch_backend` alcança o Collector em `http://otel-collector:4318` e o postgres-exporter alcança o banco (`pg_up 1`). O compose principal nunca depende da stack: derrubar só a observabilidade não afeta o app.

```bash
# tirar só a observabilidade, mantendo o app
docker compose -f docker/docker-compose.yml -f docker/observability/docker-compose.observability.yml \
  rm -sf otel-collector loki tempo prometheus pyroscope alloy grafana postgres-exporter
```

Os dados ficam em volumes nomeados `hairmatch_obs_*`, iguais nos dois modos. Trocar de modo mantém métricas, logs, traces e o estado do Grafana. Nunca use `down -v` se quiser guardá-los.

Na primeira subida, o Grafana 13 baixa os plugins dos data sources em segundo plano e precisa de internet. Nesse intervalo o data source do Prometheus pode responder `Plugin not registered`. Os plugins ficam no volume.

## Ligar o backend e o app (#194)

O backend e o app emitem telemetria por padrão **desligada**. Sem as variáveis abaixo, nada sai do processo e nenhuma resposta muda.

### 1. Backend

1. Suba no **modo combinado** (o backend só alcança o Collector por ele; veja acima).
2. No `docker/.env`, defina:

   ```
   OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
   # opcionais: vazio usa hairmatch-api e "dev"
   OTEL_SERVICE_NAME=
   OTEL_RESOURCE_ATTRIBUTES=
   ```

3. Recrie o backend para ler o `.env`:

   ```bash
   docker compose -f docker/docker-compose.yml -f docker/observability/docker-compose.observability.yml up -d django
   ```

4. Confira: `docker exec hairmatch_backend env | grep OTEL` mostra o endpoint, e o log do container sai em JSON, uma linha por evento.

O serviço aparece como `hairmatch-api`. Se o Collector estiver fora do ar, o backend segue respondendo igual: cada envio desiste em 2 s, a fila descarta o excesso e há no máximo uma linha de aviso por sinal a cada 60 s.

### 2. App

No `frontend-mobile/.env`, defina `EXPO_PUBLIC_TRACE_PROPAGATION=true` e reinicie o Metro (variáveis `EXPO_PUBLIC_*` são lidas na hora do bundle). Cada requisição passa a levar um cabeçalho W3C `traceparent` (`00-<trace_id>-<id do span>-01`), e o trace do backend começa nesse `trace_id`. Vazio, ou qualquer valor diferente de `true`, não envia nada. O refresh de sessão (401, `POST /api/auth/refresh` e nova tentativa) gera três `traceparent` distintos.

Na web, o `trace_id` é o segundo trecho do cabeçalho `traceparent` da requisição, visível na aba Network do navegador. No Android o app não mostra o cabeçalho: ache o trace pela rota, como no passo 3.

### 3. Achar o trace e os logs de uma reserva

1. Faça uma reserva no app (ou `POST /api/reservations` com um cabeçalho `traceparent` seu).
2. Abra o Grafana em <http://localhost:3000> → **Explore** → data source **Tempo**.
3. Busque pelo `trace_id` (tipo de consulta *TraceID*) ou, sem ele, em *TraceQL* por `{ name = "POST api/reservations" }`. O trace mostra, nesta ordem de aninhamento:
   - o span `POST api/reservations` (SERVER), com `hairmatch.reserve_id` e `hairmatch.hairdresser_id`;
   - as queries do banco, sem valores (`WHERE id = %s`);
   - `SNS.Publish`, quando o cabeleireiro tem um aparelho registrado.
4. Do span, o botão **Logs for this span** abre o Loki nos logs do mesmo `trace_id`. No caminho inverso, em **Explore → Loki**, `{service_name="hairmatch-api"} | trace_id="<trace_id>"` lista os logs do trace, e o campo `trace_id` vira link para o Tempo.
5. Os contadores de negócio ficam no **Prometheus**: `hairmatch_reserves_created_total{channel="app"}`, `hairmatch_push_results_total`, `hairmatch_problems_total`, `hairmatch_auth_rejections_total`, `hairmatch_signup_events_total`, `hairmatch_uploads_total`, `hairmatch_cep_lookups_total`, `hairmatch_ai_requests_total` e `hairmatch_ai_tokens_total`. O dashboard **API · RED** usa `http_server_request_duration_seconds` com `job="hairmatch-api"`, e os exemplares do histograma levam ao trace.

Dois limites para não estranhar:

- Um log só carrega `trace_id` se foi escrito **dentro** do span da requisição. O log de acesso do servidor (`django.server`) e o `django.request` ("Not Found: …") são escritos depois que o span fecha, por isso não têm `trace_id`. Uma reserva bem-sucedida não escreve log nenhum; o log aparece quando algo falha dentro dela (por exemplo, o SNS fora do ar).
- Dados chegam ao Tempo cerca de 15 s depois da requisição (o ingester espera esse tempo para ficar pronto).

Nenhum e-mail, telefone, CPF, CEP, token ou ARN deve aparecer em span, métrica ou log. Se aparecer, é um defeito: o teste `hairmatch/test_telemetry_privacy.py` cobre os fluxos principais.

### 4. Dashboards do Grafana

Na pasta **Hairmatch** (<http://localhost:3000/dashboards>) ficam oito dashboards, todos provisionados por `docker/observability/grafana/dashboards/` e não editáveis pela interface. Cada sinal coletado tem um:

| Dashboard | Fonte | O que mostra |
| --- | --- | --- |
| **API · RED** | Prometheus | Taxa, 5xx e p95 por rota. |
| **App · Negócio** | Prometheus | Os nove contadores `hairmatch_*`, o HTTP do servidor (status, latência) e do cliente (Gemini, ViaCEP, SNS...) e o `target_info` de cada instância. |
| **Host** | Prometheus (`system_*`) | CPU por estado, load contra os CPUs, memória, disco e inodes por ponto de montagem, rede e conexões TCP. |
| **Containers** | Prometheus (`container_*`) | Resumo por container e CPU, memória contra o limite, rede e block I/O. Variável `container`. |
| **Postgres** | Prometheus (`pg_*`) | Conexões, locks, transações, cache hit, WAL, tabelas, saúde do exporter e, numa seção recolhida, as 270 configurações (`pg_settings_*`). |
| **Logs** | Loki | Volume por nível, serviço e origem, erros e avisos, e todos os logs com filtro por nível e busca por regex. |
| **Traces** | Tempo | Traces recentes, com erro, lentos e de banco, e a latência do servidor. |
| **Profiles** | Pyroscope | Flame graph de CPU do backend. |

Painéis de eventos que nunca aconteceram (Gemini, CEP, push, uploads, 5xx) mostram "No data" até o primeiro evento. Isso não é defeito.

`python3 docker/observability/scripts/check_dashboards.py --live` roda a consulta de cada painel pelo Grafana e falha em qualquer erro.

### 5. Profiling do backend (Pyroscope)

Defina `PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040` no `docker/.env` e recrie o backend (`docker compose -f docker/docker-compose.yml -f docker/observability/docker-compose.observability.yml up -d --build django`; é preciso reconstruir a imagem na primeira vez, por causa do `pyroscope-io`). O agente roda dentro do processo que atende as requisições e envia os profiles direto ao Pyroscope, sem passar pelo Collector. O serviço aparece como `hairmatch-api` (o mesmo nome da telemetria), com a tag `env`. Vazio, não faz nada: nada é importado, nenhuma thread sobe e nenhuma conexão abre. Uma falha ao iniciar vira um único WARNING e o app segue sem profiling.

## Portas

Todas publicadas só em `127.0.0.1`.

| Serviço | Porta no host | Para que serve |
| --- | --- | --- |
| grafana | 3000 | Interface (acesso anônimo de Admin, sem login) |
| otel-collector | 4318 | Entrada OTLP/HTTP da telemetria |
| alloy | 12347 | Receiver do Faro (`POST /collect`) |
| prometheus | 9090 | API e UI, para depuração |
| loki | 3100 | API, para depuração |
| tempo | 3200 | API, para depuração |
| pyroscope | 4040 | API e UI de profiles |

O postgres-exporter (9187) e o OTLP interno do Tempo (4318) só existem dentro da rede do compose. Nenhuma porta colide com as do compose principal (8000, 5432, 5050, 4566, 4567).

## Variáveis `OBS_*`

Ficam no `docker/.env` (modo combinado) ou no shell do comando (modo sozinho). Todas, exceto `OBS_DIR`, são vazias por padrão, e vazio significa "destino local".

| Variável | Padrão | Valor no Grafana Cloud |
| --- | --- | --- |
| `OBS_DIR` | `.` (sozinha) ou `./observability` (no `docker/.env`) | não muda |
| `OBS_TRACES_ENDPOINT` | `http://tempo:4318/v1/traces` | `<OTLP gateway>/v1/traces` |
| `OBS_METRICS_ENDPOINT` | `http://prometheus:9090/api/v1/otlp/v1/metrics` | `<OTLP gateway>/v1/metrics` |
| `OBS_LOGS_ENDPOINT` | `http://loki:3100/otlp/v1/logs` | `<OTLP gateway>/v1/logs` |
| `OBS_OTLP_AUTH_HEADER` | vazio | `Basic <base64(instanceID:token)>` |

O prefixo `OBS_` evita colisão com as `OTEL_*` que os SDKs leem.

## Serviço local → equivalente no Grafana Cloud

| Local | Grafana Cloud |
| --- | --- |
| OTel Collector (contrib) | Continua rodando na sua máquina ou VPS e exporta ao OTLP gateway (Grafana Cloud OTLP endpoint) |
| Tempo | Grafana Cloud Traces |
| Prometheus (receiver OTLP) | Grafana Cloud Metrics |
| Loki | Grafana Cloud Logs |
| Pyroscope | Grafana Cloud Profiles. O SDK do Pyroscope envia direto, sem passar pelo Collector |
| Grafana | Grafana Cloud (instância hospedada). Data sources e dashboard vêm do Cloud |
| Alloy (receiver do Faro) | Frontend Observability. No Cloud, o Faro do navegador envia direto ao endpoint dele, sem passar pelo Alloy nem pelo Collector |
| postgres-exporter | Continua local; as métricas seguem pelo Collector |
| `hostmetrics` e `docker_stats` | Continuam no Collector; as métricas seguem ao Cloud |
| — | **Synthetic Monitoring**: sem equivalente local. Só existe no Grafana Cloud |

## Trocar o destino para o Grafana Cloud

Só variáveis de ambiente mudam. O `otel/config.yaml` é o mesmo.

1. No Grafana Cloud, abra a stack e vá em **Connections → OpenTelemetry → Configure**. Anote o **OTLP endpoint** (ex.: `https://otlp-gateway-<região>.grafana.net/otlp`) e o **Instance ID**.
2. Crie um token (Access Policy com os escopos de escrita `metrics:write`, `logs:write` e `traces:write`). O token começa com `glc_`.
3. Monte o header com o Instance ID e o token:

   ```bash
   echo -n "<instanceID>:<token>" | base64 -w0
   ```

   O valor de `OBS_OTLP_AUTH_HEADER` é `Basic ` mais o resultado.
4. Defina as variáveis. No modo combinado, no `docker/.env` (arquivo ignorado pelo Git):

   ```
   OBS_TRACES_ENDPOINT=https://otlp-gateway-<região>.grafana.net/otlp/v1/traces
   OBS_METRICS_ENDPOINT=https://otlp-gateway-<região>.grafana.net/otlp/v1/metrics
   OBS_LOGS_ENDPOINT=https://otlp-gateway-<região>.grafana.net/otlp/v1/logs
   OBS_OTLP_AUTH_HEADER=Basic <base64>
   ```

   Na stack sozinha, passe as mesmas variáveis no shell do comando, nunca por `--env-file`:

   ```bash
   OBS_TRACES_ENDPOINT=… OBS_METRICS_ENDPOINT=… OBS_LOGS_ENDPOINT=… OBS_OTLP_AUTH_HEADER="Basic …" \
     docker compose -f docker/observability/docker-compose.observability.yml up -d
   ```
5. Suba de novo (`up -d` recria o Collector). Para voltar ao destino local, esvazie as variáveis e repita.

Nunca commite o token nem o header. O `lint_compose.py` falha se um `glc_` ou um `Basic <valor>` aparecer em `docker/observability/`.

Se o destino não responde, o Collector continua de pé, guarda os dados numa fila em disco limitada e tenta de novo. Quando a fila enche, descarta. O app não é afetado.

## Scripts de verificação

Todos ficam em `docker/observability/scripts/` e usam só a biblioteca padrão do Python (e `docker`, `bash`).

| Script | Comando | O que prova |
| --- | --- | --- |
| `lint_compose.py` | `python3 docker/observability/scripts/lint_compose.py` | Estático, sem containers. Compose sem `name:`, imagens com tag exata, portas só em `127.0.0.1`, rotação de log, mounts com `${OBS_DIR:-.}`, compose principal sem referência à stack, `.env.example` com as `OBS_*` vazias e nenhuma credencial no repositório. `--self-test` prova que o lint reprova cada violação. |
| `smoke.py` | `python3 docker/observability/scripts/smoke.py --mode standalone` (ou `--mode combined`) | Com a stack no ar, manda dados sintéticos e confere: prontidão, os três sinais (OBS-13 a OBS-18), a redação (OBS-22 a OBS-31), métricas de infra e do banco, data sources e dashboard do Grafana e o receiver do Faro. `--only <seção>` roda uma seção (`ready`, `signals`, `redaction`, `infra`, `grafana`, `faro`). |
| `check_destination.sh` | `bash docker/observability/scripts/check_destination.sh` | A troca de destino: aponta as `OBS_*` para um receptor local que registra as requisições e confere o path e o `Authorization` de cada sinal. Depois, com um destino inexistente, o Collector segue `running`. Com o Loki parado, os traces seguem chegando ao Tempo. |
| `check_modes.sh` | `CONFIRM=1 bash docker/observability/scripts/check_modes.sh` | Os modos sozinho e combinado contra o compose principal real. **Para e sobe o ambiente de dev** (nunca com `-v`) e o devolve ao estado em que estava. |

Depois de subir a stack do zero, o `smoke.py` leva alguns minutos, em boa parte esperando o Grafana instalar os plugins.

## Limitações conhecidas

- **Valores não string não são redigidos** (OBS-59). Um telefone enviado como inteiro passa. A #194 proíbe dado pessoal na origem, e a redação é a terceira camada de defesa.
- **Atributos de ponto de dados das métricas não são redigidos.** Os atributos de resource das métricas são. Os de ponto viram os rótulos da série e devem ser de baixa cardinalidade (rota, status); nunca ponha dado pessoal neles.
- **Só os campos da spec são redigidos.** Ficam de fora os eventos de span (por exemplo `exception.message`, que a instrumentação Django do OTel preenche), o nome e o `status.message` do span, os atributos de escopo, o `severityText` e os valores dentro de arrays ou de mapas aninhados. Um dado pessoal numa mensagem de exceção passaria. A #194 deve manter dado pessoal fora dessas mensagens; ampliar a redação a esses campos é uma decisão pendente (card próprio).
- **Mapas aninhados não são redigidos.** Num corpo de log map, só os valores string do primeiro nível passam pela redação.
- **Falsos positivos.** Uma sequência de 10 a 14 dígitos numa string é redigida, mesmo quando não é dado pessoal (ID de conta da AWS num ARN, timestamp em ms). Redigir a mais é o lado seguro.
- **Número de 11 dígitos sem máscara** vira `[cpf]`, seja CPF ou celular: os dois são indistinguíveis.
- **O JID do WhatsApp** (`<dígitos>@s.whatsapp.net`) vira `[email]`.
- **Chaves de URL.** `url.query`, `url.full`, `http.url` e `http.target` são apagadas em spans, logs e métricas.
- **O Faro segue sem dados reais.** Nada no app alimenta o receiver do Faro; ele só foi testado com dados sintéticos. O Pyroscope recebe os profiles do backend quando `PYROSCOPE_SERVER_ADDRESS` está definido.
- **Profiling sem autenticação.** O SDK só fala com o Pyroscope local. Enviar ao Grafana Cloud Profiles exige usuário e senha do Basic Auth, que ainda não têm variável.
- **Logs de acesso sem `trace_id`.** Veja "Dois limites" acima: o painel "Com trace_id" do dashboard Logs conta só os logs escritos dentro de um span.
- **Sem métricas do próprio Collector e do Alloy.** Nenhum dashboard os mostra porque nada os coleta; só o consumo dos containers deles (dashboard Containers).
- **O Collector roda como root e monta o `docker.sock`** (somente leitura) para ler as métricas dos containers. Quem controla o Collector controla o Docker do host. É uma conveniência local.
- **Grafana anônimo com Admin**, sem login. Só é seguro porque a porta fica em `127.0.0.1`.

## O que muda na VPS

Esta stack é de desenvolvimento. Na implantação, o que muda:

- **Grafana sem acesso anônimo.** Remova `GF_AUTH_ANONYMOUS_*` e `GF_AUTH_DISABLE_LOGIN_FORM`. Nunca leve o Admin anônimo para um servidor.
- **Papel `pg_monitor` no Postgres** para o postgres-exporter, em vez do usuário do banco de dev. Opcionalmente, `pg_stat_statements` (exige `shared_preload_libraries`).
- **Socket do Docker opcional.** Sem o `docker.sock`, o Collector perde só as métricas por container.
- **`mem_limit` e TLS** ajustados ao servidor, e leitura dos logs de Nginx e Postgres (`filelog`).
- **Armazenamento no Grafana Cloud.** Tempo, Loki e Prometheus locais deixam de ser usados.
