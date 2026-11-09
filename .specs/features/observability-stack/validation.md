# Stack de observabilidade local Validation (rodada 2)

**Verdict**: PASS
**Result**: PASS

Os 60 requisitos têm evidência `file:line` e a asserção bate com o resultado da spec. Os 12 dos 13 gaps de precisão da rodada 1 estão fechados e o 13º (OBS-31) é residual trivial. Os gates estão verdes (lint 12 PASS, smoke 128 PASS / 0 FAIL) e todos os 15 mutantes injetados morreram. Fica uma superfície de privacidade fora do texto da spec (eventos de span, nome do span, escopo, exemplares, atributos map/array), sonda com dado sintético na stack real; ela é a lacuna nº 1 abaixo e precisa de decisão do autor, mas não contradiz nenhum critério OBS-22 a OBS-30.

**Date**: 2026-11-07
**Spec**: `.specs/features/observability-stack/spec.md`
**Diff range**: `7f004d9..HEAD` (HEAD `3f2d7a9`; fixes da rodada 2: `a6e0a67` e `3f2d7a9`)
**Verifier**: sub-agente independente, rodada 2 (author != verifier). Sobrescreve o relatório FAIL da rodada 1.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 a T16 | Done | Todos os checkboxes de `tasks.md` marcados; um commit por task, mais dois commits de correção. |
| `check_destination.sh`, `check_modes.sh` | Não re-executados | Ordem do orquestrador. Revisão estática abaixo. O autor registrou 19 PASS / 0 FAIL e 20 PASS / 0 FAIL. `smoke.py --mode combined` (OBS-43) também não foi executado aqui. |

---

## Spec-Anchored Acceptance Criteria

`S` = `docker/observability/scripts/smoke.py`, `L` = `lint_compose.py`, `M` = `check_modes.sh`, `D` = `check_destination.sh` (todos em `docker/observability/scripts/`), `R` = `docs/observability/README.md`, `C` = `docker/observability/otel/config.yaml`. "Match" compara o valor asserido com o valor definido na spec. `(estático)` = revisão do script, não executado nesta rodada.

| Req | Resultado definido na spec | Evidência (`file:line` + asserção) | Match |
| --- | --- | --- | --- |
| OBS-01 | 8 serviços `running` em 60 s, sem reinício | `M:79-88` `[ "$running" -eq 8 ]` em 60 s, usado em `M:167`; `M:91-98` `RestartCount == "0"`, usado em `M:169` | PASS (estático) |
| OBS-02 | compose principal sem referência à stack | `L:130-134` `report(not hits, "OBS-02", ...)` (nomes de serviço e `OBS_\|hairmatch_obs_\|observability`) | PASS |
| OBS-03 | db/localstack/ministack `healthy`, django `running` | `M:101-113` 3 x `Health.Status == healthy` + backend `running`, usado em `M:178`; `M:180` ainda `running` 10 s depois | PASS (estático) |
| OBS-04 | `hairmatch_backend` alcança `otel-collector:4318` e recebe HTTP | `M:187-189` `docker exec hairmatch_backend python` POST, `[ "$status" = "200" ]` | PASS (estático) |
| OBS-05 | app no mesmo estado após `rm -sf` da stack | `M:120-124` identidade por container (`Id`, `State.Status`, `StartedAt`, `RestartCount`); snapshot `M:230`, `rm -sf` `M:231`, comparação `M:234` | PASS (estático). Gap G6 fechado |
| OBS-06 | sem `name:` | `L:80-81` `report(not has_name, "OBS-06", ...)` | PASS |
| OBS-07 | tag exata | `L:84-86` regex `:[vV]?\d+\.\d+\.\d+` | PASS |
| OBS-08 | toda porta em `127.0.0.1` | `L:89-91` `port_host_ip(p) != "127.0.0.1"` | PASS |
| OBS-09 | `json-file`, `10m`, `3` | `L:94-100` driver/max-size/max-file | PASS |
| OBS-10 | dados persistem nos dois sentidos | `M:171` grava marcador 1; `M:222` verifica após sozinho para combinado; `M:225` grava marcador 2 no combinado; `M:264` verifica após combinado para sozinho; `M:146-156` confere Tempo, Loki, Prometheus e Grafana | PASS (estático). Gap G8 fechado |
| OBS-11 | retenção 7 dias nos 3 | `S:127` Loki `in (168h,1w,7d)`; `S:129` compactor; `S:136` Tempo `== "168h0m0s"`; `S:143` Prometheus `in (7d,1w)` | PASS |
| OBS-12 | prefixo `${OBS_DIR:-.}/`, mount real | `L:104-108` prefixo; `M:193-215` todo mount sob `$PWD/docker/observability`, não vazio; `M:213-214` `cmp` do config do Collector | PASS (mounts em `M`: estático) |
| OBS-13 | OTLP/HTTP em `127.0.0.1:4318` e `otel-collector:4318` | `S:306` `all(s == 200)` nos 6 payloads; `M:189` pela rede | PASS |
| OBS-14 | Tempo devolve o span em 30 s | `S:309-311` `wait_for(tempo_trace(TRACE_ID), 30)` e `any(s.get("spanId"))` | PASS |
| OBS-15 | Loki devolve o log em 30 s | `S:313-314` `x[0] == SMOKE_LOG` | PASS |
| OBS-16 | série `..._count{job=}` em 30 s | `S:316-317`; `S:145`, `S:149` receiver OTLP e `out_of_order_time_window: 30m` | PASS |
| OBS-17 | LogQL do data source do Tempo devolve o log | `S:563-573` roda a consulta gerada e exige `SMOKE_LOG in lines`; `S:575-580` com outro `trace_id` o resultado é `== []` | PASS. Gap G2 fechado |
| OBS-18 | `query_exemplars` devolve o `trace_id` | `S:319-327` `TRACE_ID in ids`; `S:146` | PASS |
| OBS-19 | trace→logs para o Loki, `service_name` e `trace_id` | `S:556-560` `datasourceUid == "loki" and query == exact` com `exact = '{service_name="${__span.tags["service.name"]}"} \| trace_id="${__trace.traceId}"'` | PASS. Gap G2 fechado |
| OBS-20 | derived field que vira link para o Tempo | `S:552-555` `name`, `datasourceUid == "tempo"`, `matcherRegex`, `matcherType == "label"` e `url == "${__value.raw}"` | PASS. Gap G5 fechado |
| OBS-21 | exemplar abre `trace_id` no Tempo | `S:549-551` `name == "trace_id" and datasourceUid == "tempo"` | PASS |
| OBS-22 | `contato [email]` | `S:352` + `judge` `S:379-387` (`got == expected`), chamado em `S:432` | PASS |
| OBS-23 | `token [jwt]` | `S:353` + `S:432` | PASS |
| OBS-24 | `cpf [cpf]`, sem `123.456.789-09` | `S:354` (esperado + `forbidden`) | PASS |
| OBS-25 | `cnpj [cnpj]`, sem 3+ dígitos | `S:355-356` esperado + `forbidden r"\d{3}"` | PASS |
| OBS-26 | `tel [telefone]` (2 formas) | `S:357-358` | PASS |
| OBS-27 | `doc [cpf]`; JID sem 4+ dígitos | `S:359` e `S:361` (`expected None`, `forbidden r"\d{4}"`) | PASS |
| OBS-28 | mesma redação em atributo de log, de span e resource | `S:433` atributo de log; `S:441` resource de log; `S:448` resource de métrica (`target_info.pii_resource`); `S:466` atributo de span; `S:467` resource de span; 10 casos cada | PASS. Gap G1 fechado |
| OBS-29 | corpo map, 1º nível | `S:434-439` `json.loads(line)["msg"]` contra a tabela | PASS |
| OBS-30 | 4 chaves de URL removidas de span, log e ponto de métrica | `S:472` log; `S:484` span; `S:490` série de métrica | PASS |
| OBS-31 | redação antes do exporter, mesmos processors | `S:500-503` `pipes == want` com `metrics` agora igual a `order`; `D:219-225` mesmo config nos cenários de destino | PASS. Residual G10 (o `want` espelha a implementação) |
| OBS-32 | `memory_limiter` primeiro, `batch` último | `S:329-332` `p[0] == "memory_limiter" and p[-1] == "batch"`, 3 pipelines | PASS |
| OBS-33 | variáveis vazias ou ausentes = local | `D:85-91` 4 variáveis definidas e vazias + `smoke.py --only signals` | PASS (estático) |
| OBS-34 | path e `Authorization` por sinal | `D:105` `grep -qF "POST /$entry auth=$AUTH"` para 3 paths; `D:112` sem cruzamento | PASS (estático) |
| OBS-35 | mesmo `config.yaml`, destino só por variável | `L:111-124` sem URL fixa e 4 chaves do exporter lidas de `${env:OBS_*}`; `D:72-76,100,127,164` sha do config dentro do container; `D:219-225` sha repo == sha dos 3+ cenários | PASS. Gap G4 fechado |
| OBS-36 | `running`, fila limitada, retry | `S:334-342` `sending_queue` com `enabled: true`, `storage: file_storage`, `0 < queue_size <= 10000`, e `retry_on_failure.enabled: true`; `D:136` `running` 60 s e `RestartCount 0`; `D:146` >= 3 arquivos de fila; `D:152` `will retry` | PASS. Gap G3 fechado (o trecho dinâmico `D:146` é fraco, ver lacuna 4) |
| OBS-37 | sem credencial; 5 variáveis, vazias exceto `OBS_DIR`, comentário | `L:142-170` presentes, valores, comentário acima, varredura `glc_`/`Basic` | PASS |
| OBS-38 | 4 data sources, UIDs fixos, `readOnly` | `S:534-537` `sorted(by_uid) == sorted(DATASOURCE_UIDS)`; `readOnly is True` | PASS |
| OBS-39 | health `OK` nos 4 | `S:541-546` `status == "OK"` por UID | PASS |
| OBS-40 | pasta Hairmatch, "API · RED", variável `service`, 3 painéis | `S:583-601` pasta e título; `variables == ["service"]`; 3 painéis com `http_route`; `5..`; `histogram_quantile(0.95` | PASS |
| OBS-41 | consulta de cada painel devolve série | `S:604-607` por painel, `$service` trocado | PASS |
| OBS-42 | `127.0.0.1:3000`, sem login, Admin | `S:520-529` sem `/login` e `/api/org/users == 200` | PASS |
| OBS-43 | `pg_up == 1` no combinado | `S:686-694` `want = 1.0`; `M:217-220` | Não executado aqui; asserção correta |
| OBS-44 | `pg_up == 0` sozinho, exporter `running` | `S:689-694` amostra dos últimos 75 s com `== 0`; `S:696-707` `running == "true" and restarts == "0"` após 60 s | PASS |
| OBS-45 | `system_memory_usage_bytes`, `system_filesystem_usage_bytes` em 60 s | `S:666-669` `timestamp(m) > time() - 75` | PASS. Gap G7 fechado (ressalva: lacuna 5) |
| OBS-46 | memória por container com nome, incluindo o Collector | `S:672-678` `COLLECTOR_CONTAINER in names` com amostra fresca; `S:150`; `S:681-683` sem erro de versão da API | PASS. Gap G7 fechado |
| OBS-47 | Pyroscope `/ready` 200 | `S:154` `wait_ready` | PASS |
| OBS-48 | log do Faro no Loki, e-mail vira `[email]`, via Collector | `S:631-633` POST aceito; `S:641-642` `"[email]" in log_line and e-mail not in log_line`; `S:643-644` | PASS |
| OBS-49 | CORS da origem permitida | `S:648-650` `== FARO_ORIGIN` | PASS |
| OBS-50 | outra origem sem o header | `S:651-654` `allow not in ("http://evil.example", "*")` | PASS |
| OBS-51 | comandos sozinho e combinado, um modo por vez | `R:16` aviso; `R:22-31` sozinha; `R:33-50` combinado | PASS (checklist) |
| OBS-52 | tabela de portas | `R:52-66`; 7 portas em `127.0.0.1` | PASS (checklist) |
| OBS-53 | tabela `OBS_*` | `R:68-80` | PASS (checklist) |
| OBS-54 | serviço → Grafana Cloud, com Synthetic Monitoring | `R:82-95` | PASS (checklist) |
| OBS-55 | passo a passo da troca, com `OBS_OTLP_AUTH_HEADER` | `R:97-129` | PASS (checklist) |
| OBS-56 | como rodar os scripts e o que provam | `R:131-142` | PASS (checklist) |
| OBS-57 | um backend parado: Collector `running`, outros chegam, retry | `D:166-217` `backend_down` para `loki`, `tempo` e `prometheus` (`D:217`): `D:185-187` os outros dois chegam, `D:194` `running 0`, `D:209` o que foi enviado chega após a volta | PASS (estático). Gap G8 fechado |
| OBS-58 | exporter `pg_up 0` sem sair | `S:694` e `S:706-707` (como OBS-44) | PASS |
| OBS-59 | não string não é redigido; documentado | `S:497` `str(value) == "5592991234567"`; `R:146` | PASS |
| OBS-60 | o segundo `up` falha por conflito; o primeiro segue | `M:242-249` e `M:257-263` exit != 0 e mensagem `already in use\|conflict\|already allocated\|address already in use`; `M:250` e `M:265` o primeiro segue (`main_services_unchanged`, `no_restarts`) | PASS (estático). Gap G6/G8 fechado |

**Status**: 60/60 requisitos com evidência localizada e resultado que bate com a spec. 0 spec-precision gaps abertos que quebrem um critério. Dos 13 gaps da rodada 1: fechados OBS-05, 10, 17, 19, 20, 28, 35, 36, 45, 46, 57, 60; residual trivial OBS-31.

---

## Superfície de privacidade (sonda independente)

Sonda: um span, 5 logs e 2 pontos de histograma sintéticos para o serviço `obs-probe-ffcc79e5`, com `probe.leak@example.com` e `123.456.789-09` em campos que a spec não nomeia. Lido de volta no Tempo, Loki e Prometheus. Resíduo: esses dados ficam na stack de dev por 7 dias.

| Campo | Resultado gravado | Spec exige? |
| ----- | ----------------- | ----------- |
| corpo string, corpo map 1º nível, atributo string de log e de span, resource de log, span e métrica | redigido (smoke cobre) | Sim, OBS-22 a OBS-29 |
| `url.query` etc. em log, span e ponto de métrica | removido (smoke cobre) | Sim, OBS-30 |
| atributo de span ou de log com valor map (`nested.inner`) | **vazou** (`x probe.leak@example.com`) | Ambíguo: OBS-28 diz "valor string de um atributo"; README só avisa sobre mapa no corpo |
| atributo de log com valor array | **vazou** (`["arr probe.leak@example.com"]`, vira rótulo no Loki) | Não string (OBS-59), não citado no README |
| corpo de log array | **vazou** | Idem |
| corpo map aninhado (`outer.inner`) | vazou | Limitação documentada |
| atributos de evento de span (`exception.message`, `url.query` do evento) | **vazou** (`boom probe.leak@example.com 123.456.789-09`) | Fora do texto ("atributo de span") |
| nome do span (`GET /users/<e-mail>`) e `status.message` | **vazou** | Fora do texto |
| atributos de link de span | **vazou** | Fora do texto |
| nome e atributos de escopo (log, span) | **vazou** (rótulos `scope_name`, `scope_attr` no Loki) | Fora do texto |
| `severityText` | **vazou** (rótulo `severity_text` e `detected_level`) | Fora do texto |
| atributo de ponto de métrica | vazou como rótulo (`dp_attr`) | Limitação documentada (`R:147`) |
| `filteredAttributes` de exemplar | **vazou** (`ex.attr` no `query_exemplars`) | Fora do texto, não documentado |
| chave de atributo com CPF (`key_123_456_789_09`) | vazou | Fora do texto |

---

## Discrimination Sensor

Profundidade: caminho de redação (crítico para privacidade) e as asserções alteradas nas correções. Scratch: `git worktree` do HEAD; stack real derrubada sem `-v`, stack do worktree no lugar, `up -d --force-recreate` por mutante; worktree restaurado com `git checkout -- .` entre mutantes e removido no fim.

| # | Mutação (arquivo) | Check | Resultado |
| - | ----------------- | ----- | --------- |
| 1 | tirar `transform/pii` da pipeline de métricas (`C:145`) | smoke `redaction` | Killed: OBS-28 metric resource em 9 casos (controle passa), OBS-31 |
| 2 | apagar só a regra de e-mail de `metric_statements` (`C:111`) | smoke `redaction` | Killed: OBS-28 `contato [email]` e `jid` |
| 3 | regra `[cpf]` do resource de métrica só casa CPF mascarado (`C:113`) | smoke `redaction` | Killed: OBS-28 `doc 12345678909` |
| 4 | Tempo `tracesToLogsV2.query` com `\| trace_id=~".+"` (`datasources.yaml:45`) | smoke `grafana` | Killed: OBS-19 (query exata) e OBS-17 negativo (outro `trace_id` devolve o log) |
| 5 | derived field `url` para `${__value.formatted}` (`datasources.yaml:32`) | smoke `grafana` | Killed: OBS-20 |
| 6 | `sending_queue.enabled: false` (`C:127`) | smoke `signals` | Killed: OBS-36 fila |
| 7 | `queue_size: 100000` (`C:129`) | smoke `signals` | Killed: OBS-36 fila |
| 8 | `retry_on_failure.enabled: false` (`C:131`) | smoke `signals` | Killed: OBS-36 retry |
| 9 | remover `storage: file_storage` (`C:128`) | smoke `signals` | Killed: OBS-36 fila |
| 10 | `traces_endpoint: http://x` (`C:121`) | `lint_compose.py` | Killed: OBS-35 (2 FAIL, 10 PASS) |
| 11 | `metrics_path: http://x` no scrape do postgres (`C:38`) | `lint_compose.py` | Killed: OBS-35 sem URL fixa |
| 12 | `logs_endpoint: loki:3100/...` sem esquema (`C:123`) | `lint_compose.py` | Killed: OBS-35 chave não lida de variável |
| 13 | remover o scraper `memory` do `host_metrics` (`C:20`) | smoke `infra` | Killed: OBS-45 `system_memory_usage_bytes` (a de disco passa) |
| 14 | tirar `docker_stats` dos receivers de métricas (`C:144`) | smoke `infra` | Killed: OBS-46 |
| 15 | scrape do postgres-exporter para `:9999` (`C:38`) | smoke `infra` | Killed: OBS-44 `pg_up is None` |

Os mutantes 13 a 15 foram aplicados juntos num só `up`, com 85 s de espera antes do smoke, e cada um morreu na sua própria asserção.

**Total**: 15 injetadas (8 contra a stack do worktree em execução, com Collector ou Grafana recriados: mutantes 1 a 5 e 13 a 15; 7 estáticas: mutantes 6 a 12), 15 killed, 0 survived. O `--self-test` do lint (19 PASS) cobre os casos de OBS-35 além disso.

Observação sobre o sensor: o 1º smoke do mutante Grafana rodou logo após recriar o Collector e deu falsos FAIL em OBS-17 positivo e OBS-41 (os envios foram antes de o Collector escutar). Re-rodado com a stack quente, OBS-17 negativo, OBS-19 e OBS-20 falharam como esperado. É a lacuna 6.

---

## Code Quality

| Principle | Status | Nota |
| --------- | ------ | ---- |
| Minimum code | OK | Sem abstração de uso único. `backend_down()` em `D:168-216` serve 3 backends. |
| Surgical changes | OK | Fora de `docker/observability/`, `docs/observability/` e `.specs/`: só `docker/.env.example` (+12 linhas). Compose principal intocado. Os dois commits de correção só mexem em scripts, config, README e design. |
| Test integrity | OK | Nenhuma asserção afrouxada: OBS-19 virou igualdade exata, OBS-20 ganhou `url`, OBS-45/46/43/44 ganharam frescor, OBS-60 ganhou causa. `S:502` agora exige `transform/pii` em métricas (mais forte). |
| Secrets | OK | Varredura do diff `7f004d9..HEAD` por `glc_[A-Za-z0-9]`, `Basic [A-Za-z0-9+/=]{8,}`, `AKIA...`: só o dummy `dGVzdDp0ZXN0` (`test:test`) e strings de self-test e exemplos de README. `docker/.env` não está versionado. A senha do postgres-exporter vem de `${POSTGRES_PASSWORD:-hairmatch}` (padrão de dev). |
| Comment accuracy | OK | G9 e G11 corrigidos: `C:53-55` ("The \b anchors already keep the CPF pattern from matching inside a 14-digit CNPJ"), `docker-compose.observability.yml:7-12` e `:40`. Resta `spec.md:60`, que ainda justifica CNPJ antes de CPF com o corte em 11 dígitos (lacuna 7). |
| Matches patterns | OK | Mesmo estilo dos scripts anteriores. |
| README x comportamento | Parcial | `R:12` afirma que o Collector apaga os dados pessoais antes de exportar; `R:144-155` não lista eventos de span, nome do span, escopo, `severityText`, exemplares, atributos map/array (lacuna 1). |
| `.specs/STATE.md` | Não verificado | O orquestrador atualiza. |

### Revisão estática dos scripts não executados

- `check_modes.sh` pegaria uma regressão de OBS-01, 03, 04, 05 (agora por `Id`/`StartedAt`/`RestartCount`), 10 (dois sentidos), 12 e 60 (com causa). `hairmatch_db` ausente é tolerado: `docker inspect ... 2>/dev/null` omite a linha do container inexistente em `M:122`.
- `check_destination.sh` pegaria perda de path ou header por sinal (OBS-34), queda do Collector (OBS-36) e config diferente entre cenários (OBS-35). O trecho `D:141-150` não prova que há dado na fila (lacuna 4).

---

## Gate Check

- **Quick**: `docker compose -f docker/observability/docker-compose.observability.yml config -q` rc 0; `lint_compose.py` 12 PASS, 0 FAIL; `--self-test` 19 PASS, 0 FAIL.
- **Full** (stack sozinha no ar): `smoke.py --mode standalone` 128 PASS, 0 FAIL, duas vezes: antes do sensor e depois da restauração.
- **Estado inicial**: a stack de observabilidade estava derrubada ao começar (o `check_modes.sh` do autor termina com ela fora do ar). O Verifier a subiu com `up -d` e esperou 75 s antes do primeiro smoke.
- **Build**: `check_destination.sh`, `check_modes.sh` e `smoke.py --mode combined` não executados (ordem do orquestrador).
- **Isolamento**: `git status --porcelain` igual ao baseline do início (mais este `validation.md` já presente); `git worktree list` só com a árvore real; volumes `hairmatch_obs_grafana`, `_loki`, `_otel_queue`, `_prometheus`, `_pyroscope`, `_tempo`, `hairmatch_postgres_data`, `hairmatch_pgadmin_data` e `hairmatch_ministack_state` preservados; compose principal (backend, localstack, ministack, pgadmin) não tocado.
- **Resíduo**: os mutantes e a sonda deixaram dados sintéticos no Loki, no Tempo e no Prometheus de dev (e-mail fictício `probe.leak@example.com` e séries `target_info{pii_resource=...}` de mutantes), expiram em 7 dias.

---

## Remaining Gaps (ranked)

1. **Privacidade, fora do texto de OBS-28; decisão do autor.** Atributos de evento de span (`exception.message`), nome e `status.message` do span, links, nome e atributos de escopo, `severityText`, `filteredAttributes` de exemplar e valores map ou array de atributo e de corpo chegam ao Tempo, Loki e Prometheus sem redação (tabela acima). O OTel de Django da #194 grava exceções como evento de span, então é o vazamento mais provável. `R:12` promete redação total; `R:144-155` omite esses campos. Fix: ou estender `transform/pii` (`C:88-114`) com contextos `spanevent`, `scope` e `span` (`name`, `status.message`), ou documentar a lista em `R:144-155` e na seção "Onde a redação atua" da spec (`spec.md:63`). Importância: Major.
2. **OBS-28, atributo com valor map.** `nested.inner` de atributo de log e de span vaza, e `R:149` só avisa sobre mapa no corpo. Fix: documentar ou usar OTTL recursivo. Minor, ligado à lacuna 1.
3. **OBS-31 / `S:502`.** O `want` repete a implementação. Trivial; o sha de `D:219-225` já cobre "mesmos processors para qualquer destino".
4. **OBS-36 dinâmico, `D:141-150`.** Os arquivos bbolt de `/var/lib/otelcol/queue` têm tamanho > 0 mesmo vazios (32 a 524 KB) e o volume `hairmatch_obs_otel_queue` persiste entre execuções, então `queued -ge 3` prova que o `file_storage` está ligado, não que há dado não enviado; a mensagem "the unsent data sits in the on-disk queue" promete mais. A fila limitada em si só é asserida na configuração (`S:338-342`). Minor.
5. **OBS-45/46/44, frescor de 75 s (`S:668`, `S:674`, `S:691`).** Só mata a regressão se o smoke rodar mais de 75 s depois da última amostra boa; os mutantes 13 a 15 só morreram porque o Verifier esperou 85 s. Num ciclo "recriar o Collector e rodar o smoke logo" a amostra anterior passa. Minor.
6. **Smoke não espera o Collector.** `smoke.py` não aguarda a porta 4318 (`section_ready` não olha o Collector); após recriar o Collector, `--only grafana` ou `--only signals` dá falso FAIL (envios com status 0). Um `up` completo tem folga porque Loki e Tempo demoram. Trivial.
7. **`spec.md:60`.** Ainda justifica a ordem CNPJ antes de CPF com "perde só 11 dígitos", o que os `\b` já impedem (mutante R4 equivalente da rodada 1). Só texto. Trivial.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| OBS-01 a OBS-60 | Pending / Needs Fix | Verified (OBS-01, 03, 04, 05, 10, 12, 33, 34, 43, 57, 60 por revisão estática dos scripts de ambiente e `check_destination.sh`, `check_modes.sh` já verdes no autor) |

---

## Summary

**Overall**: Ready (PASS), com a lacuna 1 para decisão do autor antes da #194.

**Spec-anchored check**: 60/60 batem, 0 gaps de precisão abertos (12 dos 13 da rodada 1 fechados; OBS-31 residual trivial)
**Sensor**: 15/15 killed, 0 survived
**Gate**: lint 12 PASS / 0 FAIL, smoke 128 PASS / 0 FAIL
