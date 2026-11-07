# Stack de observabilidade local Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/observability-stack/spec.md`
**Context**: `.specs/features/observability-stack/context.md`
**Design**: `.specs/features/observability-stack/design.md`
**Status**: Draft. Aguarda a aprovação do usuário para o Execute.
**Branch**: `193-infra-de-observabilidade`, criada a partir de `origin/develop` em `7f004d9`.

**Pré-requisitos do Execute:**
- Docker 29.1.3 e Compose 2.40.3 no host, com `python3` e `jq`. Os scripts usam só a biblioteca padrão do Python.
- O `docker/.env` local precisa ganhar `OBS_DIR=./observability` (T2) antes de qualquer teste do modo combinado.
- O gate Build (T14) para e sobe o compose principal. Ele só roda com o aval explícito do usuário, nunca usa `down -v` e exige `CONFIRM=1`.
- Nenhum código do backend ou do app muda. A suíte do backend não é afetada e não entra nos gates.
- Uma task cuja verificação contradiga um fato do design (a lista "Fatos de API não verificados" em Risks & Concerns) corrige o design no mesmo commit e registra a correção.

**Ordem que mantém o gate verde a cada commit:**
1. A Phase 1 monta o compose, as variáveis e os backends, cada um com a sua checagem de prontidão.
2. A Phase 2 liga o Collector e a redação.
3. A Phase 3 traz Grafana, Faro e as métricas de infra.
4. A Phase 4 cria os scripts de modo e de destino e a documentação.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: nenhum `AGENTS.md`, `CONTRIBUTING.md` nem teste de infraestrutura no repositório. O CI (`.github/workflows/hairmatch-backend-test.yml`) só roda a suíte do Django. Strong defaults aplicados: cada critério OBS-NN tem uma asserção automatizada num script, contra a stack em execução.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Invariantes estáticas do compose e do `.env.example` | unit (estático) | OBS-02, OBS-06, OBS-07, OBS-08, OBS-09, o padrão `${OBS_DIR:-.}` de OBS-12 e OBS-37: uma checagem por critério, com a mensagem `FAIL <OBS-NN>`. | `docker/observability/scripts/lint_compose.py` | `python3 docker/observability/scripts/lint_compose.py` |
| Serviços e configs da stack (Collector, Loki, Tempo, Prometheus, Pyroscope, Alloy, Grafana, postgres-exporter) | integration | Cada critério da task, com dado sintético pela porta real. A redação compara com a tabela exata de entradas e saídas da spec. A navegação usa as consultas lidas dos data sources provisionados. | `docker/observability/scripts/smoke.py` (uma seção por área) | `python3 docker/observability/scripts/smoke.py --mode standalone` |
| Troca de destino e falha de destino | integration | OBS-34, OBS-36 e OBS-57: path e header por sinal no capture; Collector de pé com destino inexistente; outros sinais seguem com o Loki parado. | `docker/observability/scripts/check_destination.sh` | `bash docker/observability/scripts/check_destination.sh` |
| Modos sozinho e combinado | e2e | OBS-01, OBS-03, OBS-04, OBS-05, OBS-10, OBS-12 (mount efetivo) e OBS-60 contra o compose principal real. | `docker/observability/scripts/check_modes.sh` | `CONFIRM=1 bash docker/observability/scripts/check_modes.sh` |
| Documentação (`docs/observability/`) | none | Checklist de seções da OBS-51 a OBS-56 e da OBS-59, conferido no Verifier. | - | - |
| Specs (`.specs/`) | none | `validate_spec.py` e `validate_tasks.py` com exit 0. | - | - |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks que só mudam o compose, o `.env.example` ou os scripts estáticos | `docker compose -f docker/observability/docker-compose.observability.yml config -q && python3 docker/observability/scripts/lint_compose.py` |
| Full | Tasks que sobem ou mudam um serviço | Quick + `docker compose -f docker/observability/docker-compose.observability.yml up -d --remove-orphans && python3 docker/observability/scripts/smoke.py --mode standalone` |
| Build | Fim da Phase 4 (T14), com o aval do usuário | Full + `bash docker/observability/scripts/check_destination.sh && CONFIRM=1 bash docker/observability/scripts/check_modes.sh && python3 docker/observability/scripts/smoke.py --mode combined` |

> **Baseline:** o repositório não tem teste de infra. O `smoke.py` cresce a cada task. A contagem de checagens (`PASS` impressos) nunca diminui entre os commits, e cada task registra a contagem nova.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Compose, variáveis e backends

```
T1 → T2
T1 → T3 → T4 → T5 → T6
```

### Phase 2: Collector e redação

```
T7 → T8
```

### Phase 3: Grafana, Faro e métricas de infra

```
T9 → T10
T11
T12 → T13
```

### Phase 4: Destino, modos e documentação

```
T14 → T15
T16
```

---

## Task Breakdown

### Phase 1: Compose, variáveis e backends

#### T1: Base do compose de observabilidade e lint estático

**What**: Criar o arquivo de compose sem serviços de backend ainda. Ele traz:
- a âncora `x-logging` (`json-file`, `max-size: 10m`, `max-file: 3`);
- a rede `app_network: {}`;
- a seção de volumes com `name: hairmatch_obs_*`;
- um comentário de cabeçalho com os dois modos de subir;
- nenhum `name:` de projeto.

O `lint_compose.py` checa OBS-02, OBS-06, OBS-07, OBS-08, OBS-09 e o prefixo `${OBS_DIR:-.}` dos bind mounts (OBS-12).
**Where**: `docker/observability/docker-compose.observability.yml` (mais `docker/observability/scripts/lint_compose.py`, o teste da task)
**Depends on**: None
**Reuses**: o estilo do `docker/docker-compose.yml`
**Requirement**: OBS-02, OBS-06, OBS-07, OBS-08, OBS-09, OBS-12

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] O `lint_compose.py` imprime uma linha `PASS`/`FAIL <OBS-NN>` por checagem e sai com código 1 em qualquer `FAIL`.
- [x] Prova de que o lint discrimina: numa cópia temporária do compose com `name: x`, com `image: foo:latest`, com uma porta `"3000:3000"` e com um serviço sem `logging`, o lint falha em cada caso (e o arquivo real passa).
- [x] Gate check passes: Quick.
- [x] Test count: 6 `PASS` do lint (OBS-06, 07, 08, 09, 12, 02) e 8 do `--self-test`.

**Tests**: unit
**Gate**: quick

**Commit**: `feat(observability): add the observability compose base and its static lint`

---

#### T2: Variáveis `OBS_*` no `.env.example`

**What**: Acrescentar ao `docker/.env.example` um bloco `# Observability (docker/observability)`, com um comentário de uma linha por variável:
- `OBS_DIR=./observability`;
- `OBS_TRACES_ENDPOINT=`, `OBS_METRICS_ENDPOINT=` e `OBS_LOGS_ENDPOINT=`;
- `OBS_OTLP_AUTH_HEADER=`.

Estender o `lint_compose.py` para checar a OBS-37: as cinco variáveis estão presentes, só `OBS_DIR` tem valor, e nenhum `glc_` nem `Basic <valor>` aparece em `docker/observability/`.
**Where**: `docker/.env.example` (mais a checagem em `docker/observability/scripts/lint_compose.py`)
**Depends on**: T1
**Reuses**: o formato de comentário do bloco do Cognito no `.env.example`
**Requirement**: OBS-37

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] O lint falha se uma das variáveis faltar ou se `OBS_OTLP_AUTH_HEADER` tiver valor (prova numa cópia temporária).
- [x] O `docker/.env` local do usuário ganha `OBS_DIR=./observability`. O arquivo não é versionado, e o passo fica registrado no README (T16).
- [x] Gate check passes: Quick.
- [x] Test count: 10 `PASS` do lint (os 6 do T1 + 4 de OBS-37) e 16 do `--self-test`. O `docker/.env` local ganhou `OBS_DIR=./observability`.

**Tests**: unit
**Gate**: quick

**Commit**: `chore(observability): document the OBS_* variables in the env example`

---

#### T3: Loki

**What**: Criar o serviço `loki` (`grafana/loki:3.7.9`, `127.0.0.1:3100`, volume `hairmatch_obs_loki`) e a configuração monolítica do design: filesystem, structured metadata, `retention_period: 168h` e compactor com retenção. Criar o `smoke.py`, com o esqueleto de seções, as funções `PASS`/`FAIL` e a seção `ready`, que checa o Loki.
**Where**: `docker/observability/loki/config.yaml` (mais o serviço no compose e `docker/observability/scripts/smoke.py`)
**Depends on**: T1
**Reuses**: o design, seção Loki
**Requirement**: OBS-11 (Loki), OBS-15 (destino pronto)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `smoke.py --only ready` passa para o Loki.
- [x] `GET /config` do Loki mostra `retention_period: 168h` (checado no smoke).
- [x] Gate check passes: Full.
- [x] Test count: 3 `PASS` do `smoke.py --only ready` (Loki ready, retenção de 7 dias, compactor com retenção) e 10 do lint. O Loki imprime `168h` como `1w` no `/config`, e o smoke aceita as duas formas.

**Tests**: integration
**Gate**: full

**Commit**: `feat(observability): add Loki with local retention`

---

#### T4: Tempo

**What**: Criar o serviço `tempo` (`grafana/tempo:2.10.10`, `127.0.0.1:3200`, volume `hairmatch_obs_tempo`) e a configuração monolítica: OTLP/HTTP interno em 4318, storage local e `block_retention: 168h`. Acrescentar o Tempo à seção `ready` do smoke.
**Where**: `docker/observability/tempo/config.yaml` (mais o serviço no compose e a seção do smoke)
**Depends on**: T3
**Reuses**: o design, seção Tempo
**Requirement**: OBS-11 (Tempo)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `smoke.py --only ready` passa para o Tempo, e `GET /status/config` mostra `block_retention: 168h`.
- [x] Gate check passes: Full.
- [x] Test count: 5 `PASS` do `smoke.py --only ready` (3 do Loki + 2 do Tempo) e 10 do lint. O `/status/config` do Tempo também imprime 336h para o `backend_scheduler` e o `backend_worker`, que não são usados; o smoke lê só a seção `compactor`.

**Tests**: integration
**Gate**: full

**Commit**: `feat(observability): add Tempo with local retention`

---

#### T5: Prometheus

**What**: Criar o serviço `prometheus` (`prom/prometheus:v3.15.1`, `127.0.0.1:9090`, volume `hairmatch_obs_prometheus`), com as flags `--web.enable-otlp-receiver`, `--enable-feature=exemplar-storage` e `--storage.tsdb.retention.time=7d`. O `prometheus.yml` traz `out_of_order_time_window: 30m` e `otlp.promote_resource_attributes`, e nenhum `scrape_configs`. Acrescentar o Prometheus à seção `ready`.
**Where**: `docker/observability/prometheus/prometheus.yml` (mais o serviço no compose e a seção do smoke)
**Depends on**: T4
**Reuses**: o design, seção Prometheus
**Requirement**: OBS-11 (Prometheus)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `smoke.py --only ready` passa para o Prometheus.
- [x] `GET /api/v1/status/flags` mostra a retenção de 7d, o receiver OTLP e o `exemplar-storage`.
- [x] Gate check passes: Full.
- [x] Test count: 11 `PASS` do `smoke.py --only ready` (5 anteriores + 6 do Prometheus) e 10 do lint. O Prometheus imprime `7d` como `1w`; o smoke aceita as duas formas.

**Tests**: integration
**Gate**: full

**Commit**: `feat(observability): add Prometheus with the OTLP receiver and exemplars`

---

#### T6: Pyroscope

**What**: Criar o serviço `pyroscope` (`grafana/pyroscope:2.4.3`, `127.0.0.1:4040`, volume `hairmatch_obs_pyroscope`) com a configuração padrão da imagem. Acrescentar a OBS-47 à seção `ready`.
**Where**: `docker/observability/docker-compose.observability.yml` (serviço `pyroscope`, mais a seção do smoke)
**Depends on**: T5
**Reuses**: nada
**Requirement**: OBS-47

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `GET /ready` do Pyroscope responde 200 no smoke.
- [x] Gate check passes: Full.
- [x] Test count: 12 `PASS` do `smoke.py --only ready` (11 anteriores + 1 do Pyroscope) e 10 do lint.

**Tests**: integration
**Gate**: full

**Commit**: `feat(observability): add the Pyroscope server`

---

### Phase 2: Collector e redação

#### T7: Collector com OTLP, exporter por sinal e fila

**What**: Criar o serviço `otel-collector`. Detalhes:
- imagem `otel/opentelemetry-collector-contrib:0.164.0`, porta `127.0.0.1:4318`;
- `user: "0:0"`, `mem_limit: 300m` e volume `hairmatch_obs_otel_queue`;
- `OBS_*` repassadas com `${VAR:-}`;
- `depends_on` do Loki, do Tempo e do Prometheus.

O `config.yaml` traz:
- o receiver `otlp`, só HTTP;
- `memory_limiter` e `batch`;
- o `otlphttp` com os endpoints por sinal e os padrões locais;
- o `Authorization` por variável;
- `file_storage` e `sending_queue`.

Acrescentar ao smoke a seção `signals`. Ela manda um span, um log com o mesmo `trace_id` e um histograma `http.server.request.duration` com exemplar, e confere OBS-13 a OBS-16 e OBS-18.
**Where**: `docker/observability/otel/config.yaml` (mais o serviço no compose e a seção do smoke)
**Depends on**: None
**Reuses**: a aba "Collector" do estudo
**Requirement**: OBS-13, OBS-14, OBS-15, OBS-16, OBS-18, OBS-32, OBS-33, OBS-35

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] As checagens da seção `signals` passam: o span no Tempo, o log no Loki por `service_name`, a série `_count` com `job` e o exemplar em `query_exemplars`, cada uma em até 30 s.
- [ ] O smoke confere no `config.yaml` (parse do YAML) a ordem `memory_limiter` primeiro e `batch` por último em toda pipeline (OBS-32).
- [ ] Se o Prometheus 3.15 não gravar exemplars vindos de OTLP, a task para e leva a decisão ao usuário, em vez de enfraquecer a OBS-18.
- [ ] O destino local vale com as `OBS_*` ausentes (stack sozinha) e com as `OBS_*` definidas e vazias (`OBS_TRACES_ENDPOINT= … up -d`). Os padrões ficam na interpolação do Compose, como manda o design.
- [ ] Gate check passes: Full.
- [ ] Test count: os `PASS` anteriores + os novos.

**Tests**: integration
**Gate**: full

**Commit**: `feat(observability): add the OTel Collector with per-signal OTLP export`

---

#### T8: Redação de dado pessoal

**What**: Acrescentar ao `config.yaml` os processors `attributes/pii` (nas três pipelines) e `transform/pii` (logs e traces), com as regras e a ordem do design. Eles atuam no corpo string, no primeiro nível do corpo map, nos atributos de log, nos de span e nos do resource. Acrescentar ao smoke a seção `redaction`. Ela usa exatamente a tabela de entradas e saídas da spec e manda cada entrada em quatro lugares: corpo string, corpo map, atributo de log e atributo de span. Também manda as chaves `url.*` e `http.*` em span, log e ponto de métrica.
**Where**: `docker/observability/otel/config.yaml` (mais a seção do smoke)
**Depends on**: T7
**Reuses**: `transform/pii` e `attributes/pii` do estudo
**Requirement**: OBS-22, OBS-23, OBS-24, OBS-25, OBS-26, OBS-27, OBS-28, OBS-29, OBS-30, OBS-31

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Para cada linha da tabela de referência, o valor gravado no Loki e no Tempo é igual à saída esperada. Para OBS-25 e OBS-27, nenhum trecho de 3 ou mais (CNPJ) e de 4 ou mais (11 dígitos e JID) dígitos do valor original aparece.
- [ ] As quatro chaves `url.*`/`http.*` não aparecem no span, no log nem na série da métrica.
- [ ] Um texto sem PII (`pedido 42 ok`) chega intacto, o que prova que a redação não apaga tudo. A outra direção (a redação desligada deixa o teste vermelho) é coberta pelo sensor de mutação do Verifier.
- [ ] Gate check passes: Full.
- [ ] Test count: os `PASS` anteriores + os novos.

**Tests**: integration
**Gate**: full

**Commit**: `feat(observability): redact personal data in the Collector`

---

### Phase 3: Grafana, Faro e métricas de infra

#### T9: Grafana e data sources provisionados

**What**: Criar o serviço `grafana`:
- imagem `grafana/grafana:13.2.5`, porta `127.0.0.1:3000`, volume `hairmatch_obs_grafana`;
- variáveis de acesso anônimo de Admin;
- `depends_on` dos backends.

O `datasources.yaml` traz os quatro data sources com UIDs fixos, `editable: false`, o `tracesToLogsV2` do Tempo, o derived field do Loki e o destino de exemplar do Prometheus. Acrescentar ao smoke a seção `grafana`, parte 1: OBS-17, OBS-19 a OBS-21, OBS-38, OBS-39 e OBS-42. A consulta da OBS-17 é montada a partir do `tracesToLogsV2.query` lido em `/api/datasources/uid/tempo`, com as variáveis do span e do trace do smoke.
**Where**: `docker/observability/grafana/provisioning/datasources/datasources.yaml` (mais o serviço no compose e a seção do smoke)
**Depends on**: None
**Reuses**: o design, seção Grafana
**Requirement**: OBS-17, OBS-19, OBS-20, OBS-21, OBS-38, OBS-39, OBS-42

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `/api/health` do Grafana responde sem autenticação, e `/api/datasources` lista os quatro UIDs, com `readOnly: true`.
- [ ] O health de cada data source responde `OK`.
- [ ] A LogQL derivada do `tracesToLogsV2` devolve o log do smoke.
- [ ] O derived field e o destino de exemplar apontam para o UID `tempo`.
- [ ] Gate check passes: Full.
- [ ] Test count: os `PASS` anteriores + os novos.

**Tests**: integration
**Gate**: full

**Commit**: `feat(observability): provision Grafana with linked data sources`

---

#### T10: Dashboard "API · RED"

**What**: Criar o provider de dashboards (pasta "Hairmatch") e o `api-red.json` do design: a variável `service` e os três painéis por `http_route`. Acrescentar à seção `grafana`:
- a OBS-40, buscando o dashboard por `/api/search`;
- a OBS-41, extraindo cada `expr` do JSON, trocando `$service` pelo `service.name` do smoke e rodando a consulta no Prometheus. Se não houver série 5xx, o smoke manda antes um ponto com status 500.
**Where**: `docker/observability/grafana/dashboards/api-red.json` (mais `docker/observability/grafana/provisioning/dashboards/dashboards.yaml` e a seção do smoke)
**Depends on**: T9
**Reuses**: as consultas da seção 8 do estudo
**Requirement**: OBS-40, OBS-41

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O dashboard existe na pasta "Hairmatch", com a variável `service` e três painéis.
- [ ] Cada uma das três consultas devolve ao menos uma série para o serviço do smoke.
- [ ] Gate check passes: Full.
- [ ] Test count: os `PASS` anteriores + os novos.

**Tests**: integration
**Gate**: full

**Commit**: `feat(observability): add the API RED dashboard`

---

#### T11: Receiver do Faro (Alloy)

**What**: Criar o serviço `alloy` (`grafana/alloy:v1.21.3`, `127.0.0.1:12347`) e o `config.alloy` do design:
- `faro.receiver` com CORS só para `http://localhost:8081`;
- `otelcol.receiver.loki`;
- `otelcol.exporter.otlphttp` para o Collector.

Acrescentar ao smoke a seção `faro`. Ela faz um `POST /collect` com um log e uma exceção, cuja mensagem tem um e-mail e um marcador único, e dois preflights `OPTIONS`.
**Where**: `docker/observability/alloy/config.alloy` (mais o serviço no compose e a seção do smoke)
**Depends on**: None
**Reuses**: nada
**Requirement**: OBS-48, OBS-49, OBS-50

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O log com o marcador aparece no Loki em até 30 s, com o e-mail trocado por `[email]`.
- [ ] O preflight com `Origin: http://localhost:8081` devolve esse `Access-Control-Allow-Origin`, e o preflight com `Origin: http://evil.example` não devolve essa origem.
- [ ] O schema do payload foi conferido na doc do Alloy 1.21, e a fonte está citada num comentário do smoke.
- [ ] Gate check passes: Full.
- [ ] Test count: os `PASS` anteriores + os novos.

**Tests**: integration
**Gate**: full

**Commit**: `feat(observability): receive Faro through Alloy into the Collector`

---

#### T12: Métricas do host e dos containers

**What**: Acrescentar ao `config.yaml` os receivers `hostmetrics` (`root_path: /hostfs`) e `docker_stats` (`api_version: "1.44"`) na pipeline de métricas. Montar `/:/hostfs:ro` e `/var/run/docker.sock:/var/run/docker.sock:ro` no `otel-collector`. Acrescentar ao smoke a seção `infra`, com OBS-45 e OBS-46. Se o nome real das séries ou do rótulo do container diferir do design, corrigir o design no mesmo commit.
**Where**: `docker/observability/otel/config.yaml` (mais os mounts no compose e a seção do smoke)
**Depends on**: None
**Reuses**: os receivers da aba "Collector" do estudo
**Requirement**: OBS-45, OBS-46

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `system_memory_usage_bytes` e `system_filesystem_usage_bytes` aparecem em até 60 s.
- [ ] Uma série de memória por container aparece com o rótulo do nome do container, incluindo o do Collector.
- [ ] O log do Collector não tem erro de versão da API do Docker.
- [ ] Gate check passes: Full.
- [ ] Test count: os `PASS` anteriores + os novos.

**Tests**: integration
**Gate**: full

**Commit**: `feat(observability): collect host and container metrics`

---

#### T13: postgres-exporter

**What**: Criar o serviço `postgres-exporter`:
- imagem `prometheuscommunity/postgres-exporter:v0.20.1`, sem porta publicada;
- `DATA_SOURCE_URI=db:5432/${POSTGRES_DB:-hairmatch}?sslmode=disable`;
- usuário e senha de `POSTGRES_USER` e `POSTGRES_PASSWORD`.

Acrescentar ao `config.yaml` o receiver `prometheus` (job `postgres`, alvo `postgres-exporter:9187`). Acrescentar à seção `infra` a OBS-44 (stack sozinha: `pg_up == 0` e o container `running`) e a OBS-43, que só roda com `--mode combined`.
**Where**: `docker/observability/otel/config.yaml` (mais o serviço no compose e a seção do smoke)
**Depends on**: T12
**Reuses**: as variáveis `POSTGRES_*` do `docker/.env.example`
**Requirement**: OBS-43, OBS-44, OBS-58

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Com a stack sozinha, `pg_up == 0`, e o `postgres-exporter` segue `running` depois de 60 s, sem reinícios (`RestartCount` 0).
- [ ] A checagem `pg_up == 1` existe no modo `combined`. Ela é provada no T14.
- [ ] Gate check passes: Full.
- [ ] Test count: os `PASS` anteriores + os novos.

**Tests**: integration
**Gate**: full

**Commit**: `feat(observability): scrape Postgres metrics through the Collector`

---

### Phase 4: Destino, modos e documentação

#### T14: Matriz de modos

**What**: Criar o `check_modes.sh`, que exige `CONFIRM=1` e nunca usa `-v`, com a sequência do design:
1. stack sozinha (OBS-01) e uma métrica gravada;
2. derruba e sobe só o compose principal (OBS-03);
3. modo combinado: POST do backend ao Collector (OBS-04), `smoke.py --mode combined` (inclui `pg_up == 1`), a métrica do passo 1 ainda presente (OBS-10) e os mounts que são arquivos (OBS-12);
4. `rm -sf` dos serviços de observabilidade, e o app continua saudável (OBS-05);
5. com um modo no ar, o `up` do outro falha (OBS-60);
6. ao fim, restaura o estado em que encontrou o compose principal.
**Where**: `docker/observability/scripts/check_modes.sh`
**Depends on**: None
**Reuses**: `smoke.py`
**Requirement**: OBS-01, OBS-03, OBS-04, OBS-05, OBS-10, OBS-12, OBS-43, OBS-60

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O script roda até o fim com o aval do usuário e imprime `PASS` para cada requisito listado.
- [ ] O compose principal termina no mesmo estado (`docker compose ps`) em que começou.
- [ ] Gate check passes: Build (sem o `check_destination.sh`, que é do T15).
- [ ] Test count: registrar os `PASS` do script.

**Tests**: e2e
**Gate**: build

**Commit**: `test(observability): verify standalone and combined compose modes`

---

#### T15: Troca e falha de destino

**What**: Criar o `otlp_capture.py` e o serviço `otlp-capture` (`python:3.12.15-alpine`, `profiles: [verify]`, mount `${OBS_DIR:-.}/scripts/otlp_capture.py`), mais o `check_destination.sh` com os três cenários do design (OBS-34, OBS-36 e OBS-57). As `OBS_*` vão como variáveis do shell no comando do Compose, nunca por `--env-file docker/.env`. Ao fim, o script restaura a stack com o destino local.
**Where**: `docker/observability/scripts/check_destination.sh` (mais `docker/observability/scripts/otlp_capture.py` e o serviço com profile no compose)
**Depends on**: T14
**Reuses**: as funções de envio do `smoke.py`
**Requirement**: OBS-34, OBS-35, OBS-36, OBS-57

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] O capture registra `/v1/traces`, `/v1/metrics` e `/v1/logs` nos endpoints configurados, cada um com `Authorization: Basic dGVzdDp0ZXN0`.
- [ ] O `config.yaml` não muda entre os cenários: o script compara o sha256 antes e depois (OBS-35).
- [ ] Com o destino `http://nao-existe.invalid`, o Collector segue `running` por 60 s, sem reinícios.
- [ ] Com o Loki parado, um span novo chega ao Tempo.
- [ ] O `smoke.py --mode standalone` passa de novo depois da restauração.
- [ ] Gate check passes: Build.
- [ ] Test count: os `PASS` anteriores + os novos.

**Tests**: integration
**Gate**: build

**Commit**: `test(observability): verify the destination switch and destination failures`

---

#### T16: Documentação

**What**: Escrever o `docs/observability/README.md`, com:
- os comandos dos dois modos e o aviso de um modo por vez;
- o passo do `OBS_DIR` no `docker/.env`;
- a tabela de portas;
- a tabela das variáveis `OBS_*` (padrão e valor no Grafana Cloud);
- a tabela "serviço local → Grafana Cloud", inclusive o Synthetic Monitoring sem equivalente local e o Faro, que no Cloud vai direto ao Frontend Observability;
- o passo a passo da troca de destino, com a montagem do `OBS_OTLP_AUTH_HEADER`;
- os scripts de verificação;
- as limitações (OBS-59 e falsos positivos);
- o que muda na VPS: `pg_monitor`, Grafana sem acesso anônimo e o socket do Docker opcional.
**Where**: `docs/observability/README.md`
**Depends on**: None
**Reuses**: as tabelas de portas e de mapeamento do design
**Requirement**: OBS-51, OBS-52, OBS-53, OBS-54, OBS-55, OBS-56, OBS-59

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Cada item da OBS-51 a OBS-56 e a OBS-59 tem uma seção ou uma tabela no README, conferido pelo checklist do Verifier.
- [ ] Os comandos do README são os mesmos que os scripts usam (copiados, não reescritos).
- [ ] Gate check passes: Quick.

**Tests**: none
**Gate**: quick

**Commit**: `docs(observability): explain how to run the stack and map it to Grafana Cloud`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4

Phase 1:  T1 → T2
          T1 → T3 → T4 → T5 → T6
Phase 2:  T7 → T8
Phase 3:  T9 → T10
          T11
          T12 → T13
Phase 4:  T14 → T15
          T16
```

Execution is strictly sequential, in task-number order. **16 tasks.** Empacotadas em lotes de cerca de 7 tasks com fases inteiras, dão 3 lotes:
1. Phase 1 (T1 a T6);
2. Phases 2 e 3 (T7 a T13);
3. Phase 4 (T14 a T16).

Antes do Execute, a skill oferece sub-agentes por lote, e eles só são usados com o aceite do usuário. O T14 e o T15 param o compose principal e só rodam com o aval do usuário.

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Base do compose + lint | 1 arquivo de compose + o script que o testa | ⚠️ OK: o lint é o teste co-locado da base |
| T2: `.env.example` | 1 arquivo + 1 checagem no lint | ✅ Granular |
| T3: Loki | 1 config + 1 serviço + o esqueleto do smoke | ⚠️ OK: o smoke nasce com a primeira checagem |
| T4: Tempo | 1 config + 1 serviço | ✅ Granular |
| T5: Prometheus | 1 config + 1 serviço | ✅ Granular |
| T6: Pyroscope | 1 serviço | ✅ Granular |
| T7: Collector base | 1 config + 1 serviço | ✅ Granular |
| T8: Redação | 2 processors no mesmo config | ✅ Granular |
| T9: Grafana + data sources | 1 arquivo de provisionamento + 1 serviço | ✅ Granular |
| T10: Dashboard RED | 1 dashboard + o provider dele | ⚠️ OK: o provider só existe para o dashboard |
| T11: Alloy/Faro | 1 config + 1 serviço | ✅ Granular |
| T12: Host e containers | 2 receivers + os 2 mounts que eles exigem | ✅ Granular |
| T13: postgres-exporter | 1 serviço + 1 receiver | ✅ Granular |
| T14: Matriz de modos | 1 script | ✅ Granular |
| T15: Destino | 1 script + o capture que ele usa | ⚠️ OK: o capture só existe para o script |
| T16: README | 1 arquivo | ✅ Granular |

Toda task de serviço também acrescenta a sua seção ao `smoke.py`: é o teste co-locado, e não um arquivo de produção a mais.

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | início da Phase 1 | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T1 | T1 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | None (Phase 1 inteira antes) | início da Phase 2 | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | None (Phases 1 e 2 antes) | início da Phase 3 | ✅ Match |
| T10 | T9 | T9 → T10 | ✅ Match |
| T11 | None (Phases 1 e 2 antes) | sem seta | ✅ Match |
| T12 | None (Phases 1 e 2 antes) | sem seta | ✅ Match |
| T13 | T12 | T12 → T13 | ✅ Match |
| T14 | None (Phases 1 a 3 antes) | início da Phase 4 | ✅ Match |
| T15 | T14 | T14 → T15 | ✅ Match |
| T16 | None (Phases 1 a 3 antes) | sem seta | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | Invariantes estáticas | unit | unit | ✅ OK |
| T2 | Invariantes estáticas (`.env.example`) | unit | unit | ✅ OK |
| T3 | Serviços e configs | integration | integration | ✅ OK |
| T4 | Serviços e configs | integration | integration | ✅ OK |
| T5 | Serviços e configs | integration | integration | ✅ OK |
| T6 | Serviços e configs | integration | integration | ✅ OK |
| T7 | Serviços e configs | integration | integration | ✅ OK |
| T8 | Serviços e configs | integration | integration | ✅ OK |
| T9 | Serviços e configs | integration | integration | ✅ OK |
| T10 | Serviços e configs | integration | integration | ✅ OK |
| T11 | Serviços e configs | integration | integration | ✅ OK |
| T12 | Serviços e configs | integration | integration | ✅ OK |
| T13 | Serviços e configs | integration | integration | ✅ OK |
| T14 | Modos sozinho e combinado | e2e | e2e | ✅ OK |
| T15 | Troca e falha de destino | integration | integration | ✅ OK |
| T16 | Documentação | none | none | ✅ OK |

---

## Requirement → Task

| Requirements | Task |
| --- | --- |
| OBS-02, OBS-06, OBS-07, OBS-08, OBS-09 | T1 |
| OBS-12 | T1 (prefixo), T14 (mount efetivo) |
| OBS-37 | T2 |
| OBS-11 | T3, T4, T5 |
| OBS-47 | T6 |
| OBS-13 a OBS-16, OBS-18, OBS-32, OBS-33 | T7 |
| OBS-35 | T7, T15 |
| OBS-22 a OBS-31 | T8 |
| OBS-17, OBS-19 a OBS-21, OBS-38, OBS-39, OBS-42 | T9 |
| OBS-40, OBS-41 | T10 |
| OBS-48 a OBS-50 | T11 |
| OBS-45, OBS-46 | T12 |
| OBS-43, OBS-44, OBS-58 | T13 (OBS-43 provado no T14) |
| OBS-01, OBS-03, OBS-04, OBS-05, OBS-10, OBS-60 | T14 |
| OBS-34, OBS-36, OBS-57 | T15 |
| OBS-51 a OBS-56, OBS-59 | T16 |

As 60 linhas estão cobertas. Nenhum requisito fica sem task.
