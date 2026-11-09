# Stack de observabilidade local Specification

**Issue:** [#193](https://github.com/rodrigoscorrea/Hairmatch/issues/193) · [Feature][Infra] Infra de observabilidade: docker-compose com Collector, Loki, Tempo, Prometheus e Grafana.
**Origem:** o estudo "Observabilidade Hairmatch" (artifact GFDsHBv9zK8q3jDtJyu2tu), que complementa a proposta de arquitetura, e a spike #192. O estudo decidiu OpenTelemetry no código, um OTel Collector na frente e o Grafana como destino; em produção, o armazenamento fica no Grafana Cloud.
**Bloqueia:** #194 (integração da aplicação).
**Escopo:** Complex (infra nova, vários serviços, destino externo trocável, redação de dado pessoal)
**Plataformas:** só infraestrutura local (Docker Compose). Nenhum código do backend ou do app muda.

## Problem Statement

O Hairmatch não tem logs estruturados, métricas nem traces. O `docker/docker-compose.yml` só tem app, banco, pgAdmin, LocalStack e MiniStack. Quando algo quebra, não há como saber onde nem por quê.

A #194 vai instrumentar o backend com OpenTelemetry e precisa de um destino local para desenvolver e testar. Esse destino também é o ensaio da implantação no Grafana Cloud: o mesmo Collector e a mesma configuração, trocando só o destino.

## Goals

- [ ] Um compose separado sobe a stack sozinha, ou junto do compose principal, sem que o compose principal dependa dela.
- [ ] Um span, um log e uma métrica enviados por OTLP aparecem no Grafana, com navegação trace → logs e exemplar → trace.
- [ ] Nenhum e-mail, JWT, CPF, CNPJ ou telefone do log de exemplo sai do Collector.
- [ ] Trocar o destino para o Grafana Cloud muda só variáveis de ambiente.
- [ ] `docs/observability/` explica como subir e como cada serviço local se mapeia para o Grafana Cloud.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Instrumentar o backend e o app (SDK OTel, `LOGGING` em JSON, `traceparent`, `GET /api/health`) | Card #194. |
| Profiling contínuo no backend (SDK do Pyroscope) | Fora da #194 também. O servidor Pyroscope sobe vazio até um card futuro. |
| Faro no app web (SDK `@grafana/faro-web-sdk`) | Fase 1 do estudo. O receiver local do Faro sobe e é testado com um payload sintético. |
| Crashlytics (Android) | Fora do escopo da issue. |
| Mimir | Decisão do usuário: só Prometheus, tanto no ambiente local quanto no estudo. |
| Synthetic Monitoring local | Decisão do usuário. Ele só existe no Grafana Cloud e aparece na tabela de mapeamento como "sem equivalente local". |
| Regras de alerta e contact points | Fora do escopo da issue (alertas de produção). |
| Criar a conta e a stack no Grafana Cloud | Fora do escopo da issue. A troca de destino é testada contra um receptor local que captura as requisições. |
| `pg_stat_statements` no postgres-exporter | Exige `shared_preload_libraries` no Postgres do compose principal, e esta feature não muda o compose principal. |
| Ler arquivos de log do Nginx e do Postgres (`filelog`) | Não há Nginx em dev, e o Postgres de dev não escreve `jsonlog`. Fica para a VPS. |
| `tail_sampling` | Fase 2 do estudo, quando o volume se aproximar da franquia. |
| Endurecer o Collector para produção (usuário de monitoramento do Postgres, `mem_limit` da VPS, TLS) | Implantação na VPS, depois da spike #192. A documentação lista o que muda. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Armazenamento de métricas | Só Prometheus 3, com o receiver OTLP (`--web.enable-otlp-receiver`) e `exemplar-storage` ligados. | Decisão do usuário: o Mimir sai da stack local e do estudo. | y |
| Faro local | Grafana Alloy com `faro.receiver`. Ele converte os logs e reenvia logs e traces por OTLP ao Collector, para que passem pela redação. | Decisão do usuário. O Collector contrib não é o receiver de referência do Faro, e o Alloy é. | y |
| Synthetic Monitoring | Sem serviço local. Só a linha na tabela de mapeamento. | Decisão do usuário. | y |
| Extras | Entram postgres-exporter, `hostmetrics` e `docker_stats`. | Decisão do usuário, depois de comparar com o Pyroscope. | y |
| Como a stack sobe "junto" do app | Com os dois arquivos no mesmo comando: `docker compose -f docker/docker-compose.yml -f docker/observability/docker-compose.observability.yml up -d`. Os dois viram um projeto só (`hairmatch`) e dividem a `app_network`. | Testado em 2026-11-07 com o Compose 2.40.3. Dois projetos separados que declaram a mesma rede com `name:` fixo quebram nas duas ordens: o segundo `up` tenta recriar a rede e falha com "network ... has active endpoints". Com `external: true`, a stack não sobe sozinha. | n |
| Caminhos no modo combinado | Todo bind mount do compose de observabilidade usa `${OBS_DIR:-.}/...`. O `docker/.env.example` define `OBS_DIR=./observability`. | No modo combinado, o Compose resolve os caminhos relativos a partir do diretório do primeiro arquivo (`docker/`), e o mount vira um diretório vazio (conferido em 2026-11-07). Sozinha, a stack lê o `.env` de `docker/observability/`, que não existe, e o padrão `.` vale. | n |
| Nome do projeto | O compose de observabilidade não declara `name:`. | No modo combinado, o `name:` do último arquivo vence. Um `name:` próprio renomearia o projeto e trocaria os volumes do banco (`hairmatch_postgres_data`) por volumes vazios. | n |
| Volumes | Volumes nomeados com `name:` fixo (`hairmatch_obs_*`). | Os dados continuam os mesmos entre o modo sozinho e o combinado, já que o nome do projeto muda entre eles. | n |
| Um modo por vez | A stack sozinha e a combinada não rodam ao mesmo tempo. A documentação manda derrubar uma antes de subir a outra. | As duas publicam as mesmas portas no host. | n |
| Variáveis novas | `OBS_DIR`, `OBS_TRACES_ENDPOINT`, `OBS_METRICS_ENDPOINT`, `OBS_LOGS_ENDPOINT` e `OBS_OTLP_AUTH_HEADER` entram no `docker/.env.example`, vazias, exceto `OBS_DIR`. Elas não usam o prefixo `OTEL_`. | A issue pede credenciais por variável e o `.env.example` atualizado. A issue é do usuário e autoriza as variáveis, como o épico #188 autorizou as dele. O prefixo `OTEL_` é lido pelos SDKs, e a #194 vai usar `OTEL_EXPORTER_OTLP_ENDPOINT` no backend. | n |
| Destino na stack sozinha | Sem `.env`, o destino é o local. Para mandar ao Grafana Cloud com a stack sozinha, as `OBS_*` vão como variáveis do shell no mesmo comando (`OBS_TRACES_ENDPOINT=… docker compose -f docker/observability/docker-compose.observability.yml up -d`), nunca com `--env-file docker/.env`. | O AC da issue usa o comando sem `--env-file`, que precisa funcionar só com os padrões. O `docker/.env` traz `OBS_DIR=./observability`, que na stack sozinha resolveria os mounts para `docker/observability/observability/…` e os transformaria em diretórios vazios. | n |
| Onde ficam os padrões locais do destino | Na interpolação do compose (`${OBS_TRACES_ENDPOINT:-http://tempo:4318/v1/traces}`), que trata variável vazia como ausente. O `config.yaml` lê `${env:OBS_TRACES_ENDPOINT}` sem padrão. | O compose e o `docker/.env` repassam as variáveis vazias ao container. Um padrão só no `config.yaml` talvez não valha para variável definida e vazia: isso não foi verificado no Collector 0.164. | n |
| OTLP só por HTTP | O Collector escuta só `4318` (OTLP/HTTP). Sem gRPC. | A issue pede "receiver OTLP HTTP", e o estudo usa só HTTP. | n |
| Marcadores de redação | `[email]`, `[jwt]`, `[cpf]`, `[cnpj]`, `[telefone]`. | Legíveis no Loki e fáceis de procurar. | n |
| Ordem das regras de redação | JWT → e-mail → CNPJ → CPF → telefone. | O JWT carrega trechos que parecem e-mail e números. A ordem é a da spec. Os `\b` do padrão de CPF já impedem que um CNPJ de 14 dígitos sem máscara perca só 11 dígitos, então trocar CNPJ e CPF não muda o resultado (verificado por mutação). | n |
| Número de 11 dígitos sem máscara | É redigido como `[cpf]`, seja CPF ou celular. O critério é que os dígitos originais nunca apareçam, e não o rótulo. | Sem máscara, os dois são indistinguíveis. | n |
| Falsos positivos aceitos | Uma sequência de 10 a 14 dígitos numa string é redigida, mesmo quando não é dado pessoal. Exemplos: o ID de conta da AWS (12 dígitos) dentro de um ARN e um timestamp em ms (13 dígitos). | Redigir a mais é o lado seguro. Esses valores raramente importam para o debug, e a #194 manda IDs internos como atributos inteiros, que a redação não toca. | n |
| Onde a redação atua | No corpo de log string, nos valores string do primeiro nível de um corpo de log map, nos atributos string de logs e spans e nos atributos de resource. Valores não string (int, double, bool) e mapas aninhados não são redigidos. | Os logs do Python chegam com corpo string. Redigir mapas aninhados exige OTTL recursivo, e a #194 proíbe dado pessoal na origem. | n |
| Chaves de URL apagadas | `url.query`, `url.full`, `http.url` e `http.target`, em spans, logs e pontos de métrica. | A issue lista `url.query` e `url.full`. `http.url` e `http.target` são os nomes antigos da semântica HTTP e carregam a mesma informação. | n |
| Retenção local | 7 dias no Prometheus, no Loki e no Tempo. | O ambiente é de desenvolvimento, e o disco é do notebook. | n |
| Acesso ao Grafana | Anônimo com papel Admin, sem tela de login, publicado só em `127.0.0.1:3000`. | É local, e o Explore precisa de Editor ou mais. O loopback impede acesso pela rede. | n |
| Credencial do postgres-exporter | O usuário e a senha do banco de dev (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` do `docker/.env`). | Em dev, o banco só tem esse usuário. A documentação manda usar um papel `pg_monitor` na VPS. | n |
| Docker API do `docker_stats` | `api_version: "1.44"` explícito. | O Docker Engine 29 (o local é o 29.1.3) recusa APIs abaixo de 1.44. | n |
| Versões das imagens | `otel/opentelemetry-collector-contrib:0.164.0`, `grafana/loki:3.7.9`, `grafana/tempo:2.10.10`, `prom/prometheus:v3.15.1`, `grafana/pyroscope:2.4.3`, `grafana/alloy:v1.21.3`, `grafana/grafana:13.2.5`, `prometheuscommunity/postgres-exporter:v0.20.1`. O serviço de teste `otlp-capture` usa `python:3.12.15-alpine`. | O último patch de cada linha, conferido no Docker Hub em 2026-11-07. Fica de fora só o que saiu no próprio dia (Collector 0.165.0, Loki 3.6.20). O Tempo fica na linha 2.10, porque a 3.x mudou a arquitetura e a configuração não foi verificada. | n |
| Sem dados até a #194 | Pyroscope, o receiver do Faro e o dashboard RED sobem vazios para o backend. Eles só são testados com dados sintéticos. | A instrumentação está fora do escopo. | n |
| Gate de teste | O repositório não tem testes de infra. O gate desta feature são scripts versionados em `docker/observability/scripts/`, que sobem a stack, mandam dados sintéticos e consultam as APIs. | Segue a postura das features anteriores: o critério é provado por execução, não por leitura. | n |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## User Stories

### P1: Stack isolada, que não afeta o app ⭐ MVP

**User Story**: Como desenvolvedor, quero subir a observabilidade sozinha ou junto do app, sem que o app passe a depender dela.

**Why P1**: A issue exige que o compose principal continue funcionando sem a stack. A #194 depende de o backend alcançar o Collector pelo nome.

**Acceptance Criteria**:

1. **OBS-01** WHEN `docker compose -f docker/observability/docker-compose.observability.yml up -d` roda sem nenhum outro container do Hairmatch no ar THEN o Compose SHALL deixar `otel-collector`, `loki`, `tempo`, `prometheus`, `pyroscope`, `alloy`, `grafana` e `postgres-exporter` no estado `running` em até 60 s, sem nenhum em loop de reinício.
2. **OBS-02** The `docker/docker-compose.yml` SHALL continuar sem `depends_on`, rede, volume ou variável que referencie um serviço da stack de observabilidade.
3. **OBS-03** WHEN `docker compose -f docker/docker-compose.yml up -d` roda sem a stack THEN `db`, `localstack` e `ministack` SHALL ficar `healthy` e `django` SHALL ficar `running`, como antes desta feature.
4. **OBS-04** WHEN a stack sobe junto do app, com os dois `-f` no mesmo comando, THEN o container `hairmatch_backend` SHALL alcançar `http://otel-collector:4318` pelo nome e receber uma resposta HTTP do Collector.
5. **OBS-05** WHEN, com o modo combinado no ar, os serviços de observabilidade são parados e removidos (`rm -sf` com a lista deles) THEN `db`, `localstack`, `ministack` e `django` SHALL continuar no mesmo estado.
6. **OBS-06** The `docker/observability/docker-compose.observability.yml` SHALL não declarar `name:` no nível do projeto.
7. **OBS-07** The compose de observabilidade SHALL fixar cada imagem numa tag de versão exata, nunca `latest` nem só a versão maior.
8. **OBS-08** The compose de observabilidade SHALL publicar toda porta só em `127.0.0.1`.
9. **OBS-09** The compose de observabilidade SHALL configurar em todo serviço o log driver `json-file` com `max-size: 10m` e `max-file: 3`.
10. **OBS-10** WHEN a stack troca do modo sozinho para o combinado, ou o contrário, THEN os dados já gravados no Prometheus, no Loki, no Tempo e no Grafana SHALL continuar disponíveis.
11. **OBS-11** The Prometheus, o Loki e o Tempo SHALL reter os dados locais por 7 dias.
12. **OBS-12** WHEN a stack sobe no modo combinado THEN os bind mounts SHALL apontar para os arquivos de `docker/observability/`, e nenhum mount SHALL virar um diretório vazio.

**Independent Test**: subir a stack sozinha e listar os containers. Derrubar, subir só o compose principal e conferir a saúde. Subir o modo combinado, fazer um `curl` de dentro do backend para `otel-collector:4318`, remover os serviços de observabilidade e conferir que o app continua de pé.

---

### P1: Os três sinais chegam ao Grafana, com navegação ⭐ MVP

**User Story**: Como desenvolvedor, quero mandar um span, um log e uma métrica por OTLP e navegar entre eles no Grafana.

**Why P1**: É o critério de aceite central da issue e o contrato que a #194 vai usar.

**Acceptance Criteria**:

1. **OBS-13** The Collector SHALL receber OTLP/HTTP em `127.0.0.1:4318` no host e em `otel-collector:4318` na rede do compose.
2. **OBS-14** WHEN um span é enviado ao Collector THEN o Tempo SHALL devolvê-lo pelo `trace_id` (`GET /api/traces/<trace_id>`) em até 30 s.
3. **OBS-15** WHEN um log é enviado ao Collector com `service.name` no resource THEN o Loki SHALL devolvê-lo na consulta `{service_name="<service.name>"}` em até 30 s.
4. **OBS-16** WHEN um histograma `http.server.request.duration` (unidade `s`, atributo `http.route`) é enviado ao Collector com `service.name` no resource THEN o Prometheus SHALL devolver a série `http_server_request_duration_seconds_count{job="<service.name>"}` em até 30 s.
5. **OBS-17** WHEN um log é enviado com `trace_id` THEN a consulta LogQL que o data source do Tempo gera para "trace → logs" SHALL devolver esse log.
6. **OBS-18** WHEN o ponto do histograma carrega um exemplar com `trace_id` THEN `GET /api/v1/query_exemplars` do Prometheus SHALL devolver esse `trace_id`.
7. **OBS-19** The data source do Tempo SHALL ter "trace → logs" apontando para o Loki, filtrando por `service_name` e `trace_id` do span.
8. **OBS-20** The data source do Loki SHALL ter um derived field que transforma o `trace_id` do log num link para o trace no Tempo.
9. **OBS-21** The data source do Prometheus SHALL ter um destino de exemplar que abre o `trace_id` no Tempo.

**Independent Test**: rodar o smoke, que manda os três sinais com o mesmo `trace_id` e consulta Tempo, Loki e Prometheus. No Grafana, abrir o trace e clicar em "Logs for this span".

---

### P1: Redação de dado pessoal no Collector ⭐ MVP

**User Story**: Como responsável pelos dados, quero que o Collector apague dado pessoal antes de gravar ou enviar, qualquer que seja o destino.

**Why P1**: É a terceira camada de defesa do estudo (LGPD) e um critério de aceite da issue. Ela vale igual no ambiente local e no Grafana Cloud.

**Acceptance Criteria**:

Os exemplos usam os valores da tabela de entradas abaixo. "Gravado" é o que o Loki ou o Tempo devolvem.

1. **OBS-22** WHEN um log com o corpo `contato joao.silva@example.com` chega ao Collector THEN o corpo gravado SHALL ser `contato [email]`.
2. **OBS-23** WHEN um log tem no corpo um JWT (`eyJ….eyJ….<assinatura>`) THEN o corpo gravado SHALL trazer `[jwt]` no lugar do token inteiro.
3. **OBS-24** WHEN um log tem no corpo o CPF `123.456.789-09` THEN o corpo gravado SHALL trazer `[cpf]` e SHALL não conter `123.456.789-09`.
4. **OBS-25** WHEN um log tem no corpo o CNPJ `12.345.678/0001-95` ou `12345678000195` THEN o corpo gravado SHALL trazer `[cnpj]` no lugar de cada um e SHALL não conter nenhum trecho de 3 ou mais dígitos desses valores.
5. **OBS-26** WHEN um log tem no corpo o telefone `+55 (92) 99123-4567` ou `(92) 99123-4567` THEN o corpo gravado SHALL trazer `[telefone]` no lugar de cada um.
6. **OBS-27** WHEN um log tem no corpo `12345678909` (11 dígitos sem máscara) ou o JID `5592991234567@s.whatsapp.net` THEN o corpo gravado SHALL não conter nenhuma sequência de 4 ou mais dígitos desses valores.
7. **OBS-28** WHEN um valor string de um atributo de log, de um atributo de span ou do resource contém um dos dados de OBS-22 a OBS-27 THEN o valor gravado SHALL passar pela mesma redação.
8. **OBS-29** WHEN um log tem corpo map THEN cada valor string do primeiro nível SHALL passar pela mesma redação.
9. **OBS-30** WHEN um span, um log ou um ponto de métrica chega com os atributos `url.query`, `url.full`, `http.url` ou `http.target` THEN o Collector SHALL removê-los antes de exportar.
10. **OBS-31** The Collector SHALL aplicar a redação e a remoção de chaves antes do exporter, com os mesmos processors para qualquer destino.
11. **OBS-32** The Collector SHALL rodar `memory_limiter` como primeiro processor e `batch` como último em toda pipeline.

**Entradas e saídas de referência** (o teste usa exatamente estas):

| Entrada no corpo | Saída esperada |
| --- | --- |
| `contato joao.silva@example.com` | `contato [email]` |
| `token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJl` | `token [jwt]` |
| `cpf 123.456.789-09` | `cpf [cpf]` |
| `cnpj 12.345.678/0001-95` | `cnpj [cnpj]` |
| `cnpj 12345678000195` | `cnpj [cnpj]` |
| `tel +55 (92) 99123-4567` | `tel [telefone]` |
| `tel (92) 99123-4567` | `tel [telefone]` |
| `doc 12345678909` | `doc [cpf]` |
| `jid 5592991234567@s.whatsapp.net` | nenhum dos dígitos (o rótulo pode ser `[email]`) |

**Independent Test**: o smoke manda um log com todas as entradas da tabela no corpo, em atributos e num span. Depois lê o que o Loki e o Tempo gravaram e compara com as saídas esperadas.

---

### P2: Destino trocável por variável de ambiente

**User Story**: Como quem vai implantar na VPS, quero mandar a telemetria ao Grafana Cloud mudando só variáveis, para que a configuração testada localmente seja a de produção.

**Why P2**: É o motivo de a stack servir de referência, mas a stack local funciona sem isso.

**Acceptance Criteria**:

1. **OBS-33** WHERE `OBS_TRACES_ENDPOINT`, `OBS_METRICS_ENDPOINT` e `OBS_LOGS_ENDPOINT` estão vazias ou ausentes, o Collector SHALL exportar traces ao Tempo, métricas ao Prometheus e logs ao Loki da stack local.
2. **OBS-34** WHEN as três variáveis de endpoint e `OBS_OTLP_AUTH_HEADER` estão definidas THEN o Collector SHALL enviar cada sinal ao endpoint da sua variável, com o header `Authorization` igual a `OBS_OTLP_AUTH_HEADER`.
3. **OBS-35** The `otel/config.yaml` SHALL ser o mesmo arquivo para os dois destinos. Trocar de destino SHALL não editar receivers, processors nem pipelines.
4. **OBS-36** IF o destino não responde THEN o Collector SHALL continuar `running`, guardar os dados numa fila limitada e tentar de novo, sem derrubar o processo.
5. **OBS-37** The repositório SHALL não conter credencial do Grafana Cloud. O `docker/.env.example` SHALL listar as variáveis `OBS_*` com valor vazio, exceto `OBS_DIR=./observability`, e um comentário de uma linha para cada uma.

**Independent Test**: apontar as três variáveis para um receptor local que registra as requisições e conferir o path e o header de cada sinal. Depois apontar para um host que não existe e conferir que o Collector segue de pé.

---

### P2: Grafana provisionado por arquivos

**User Story**: Como desenvolvedor, quero abrir o Grafana e já encontrar os data sources ligados e um painel da API.

**Why P2**: Sem provisionamento, cada pessoa configura à mão, e a navegação entre os sinais deixa de ser reproduzível.

**Acceptance Criteria**:

1. **OBS-38** WHEN o Grafana sobe THEN ele SHALL ter os data sources Prometheus, Loki, Tempo e Pyroscope, com os UIDs fixos `prometheus`, `loki`, `tempo` e `pyroscope`, lidos de arquivos versionados e não editáveis pela interface.
2. **OBS-39** WHEN o Grafana sobe THEN o health check de cada um dos quatro data sources (`GET /api/datasources/uid/<uid>/health`) SHALL responder `OK`.
3. **OBS-40** WHEN o Grafana sobe THEN ele SHALL ter, na pasta "Hairmatch", o dashboard "API · RED", com uma variável `service` (valores de `job`) e três painéis por `http_route`: taxa de requisições, taxa de respostas 5xx e p95 da duração.
4. **OBS-41** WHEN o histograma do smoke foi recebido THEN a consulta de cada painel do dashboard, com `service` igual ao `service.name` do smoke, SHALL devolver ao menos uma série.
5. **OBS-42** The Grafana SHALL abrir em `http://127.0.0.1:3000` sem tela de login, com acesso anônimo de Admin.

**Independent Test**: subir a stack, consultar a API do Grafana pelos data sources e pelo dashboard e rodar as consultas dos painéis depois do smoke.

---

### P2: Pyroscope, Faro e métricas de infra

**User Story**: Como desenvolvedor, quero os outros sinais do estudo já disponíveis localmente: métricas do banco, do host e dos containers, profiles e o receiver do Faro.

**Why P2**: A issue lista Pyroscope e Faro, e o usuário escolheu os três extras. Nenhum deles bloqueia a #194.

**Acceptance Criteria**:

1. **OBS-43** WHILE o modo combinado está no ar, o Prometheus SHALL ter `pg_up == 1` em até 60 s.
2. **OBS-44** WHILE a stack roda sozinha, o Prometheus SHALL ter `pg_up == 0`, e o container `postgres-exporter` SHALL continuar `running`.
3. **OBS-45** WHEN a stack sobe THEN o Prometheus SHALL ter, em até 60 s, as séries de memória do host (`system_memory_usage_bytes`) e de uso de disco por sistema de arquivos (`system_filesystem_usage_bytes`).
4. **OBS-46** WHEN a stack sobe THEN o Prometheus SHALL ter, em até 60 s, uma série de memória por container com o nome do container como rótulo, incluindo o do Collector.
5. **OBS-47** WHEN a stack sobe THEN o `GET /ready` do Pyroscope SHALL responder 200.
6. **OBS-48** WHEN um payload do Faro com um log e uma exceção é enviado por `POST` a `http://127.0.0.1:12347/collect` THEN o log SHALL aparecer no Loki em até 30 s, depois de passar pelo Collector, com um e-mail da mensagem trocado por `[email]`.
7. **OBS-49** WHEN um preflight `OPTIONS` chega ao receiver do Faro com `Origin: http://localhost:8081` THEN a resposta SHALL trazer `Access-Control-Allow-Origin: http://localhost:8081`.
8. **OBS-50** IF o preflight chega com outra origem THEN a resposta SHALL não trazer `Access-Control-Allow-Origin` com essa origem.

**Independent Test**: com a stack sozinha e com o modo combinado, consultar `pg_up`, as séries do host e dos containers e o `/ready` do Pyroscope. Mandar um payload do Faro e procurar o log no Loki.

---

### P3: Documentação da stack e do mapeamento para o Grafana Cloud

**User Story**: Como quem vai implantar, quero um guia de como subir a stack e de qual serviço do Grafana Cloud substitui cada peça local.

**Why P3**: É critério de aceite da issue, mas não muda o comportamento da stack.

**Acceptance Criteria**:

1. **OBS-51** The `docs/observability/README.md` SHALL trazer:
   - os comandos para subir e derrubar a stack sozinha e no modo combinado;
   - o aviso de rodar um modo por vez.
2. **OBS-52** The README SHALL trazer uma tabela de portas: serviço, porta no host e para que serve.
3. **OBS-53** The README SHALL trazer uma tabela das variáveis `OBS_*`: nome, padrão e valor no Grafana Cloud.
4. **OBS-54** The README SHALL trazer a tabela "serviço local → equivalente no Grafana Cloud", com uma linha para cada serviço da stack e uma para o Synthetic Monitoring, marcado sem equivalente local.
5. **OBS-55** The README SHALL descrever, passo a passo, a troca do destino para o Grafana Cloud só com variáveis de ambiente, incluindo como montar o `OBS_OTLP_AUTH_HEADER`.
6. **OBS-56** The README SHALL explicar como rodar os scripts de verificação e o que cada um prova.

**Independent Test**: seguir o README do zero numa máquina com o repositório e o Docker, sem outra fonte.

---

## Edge Cases

- **OBS-57** IF o Loki, o Tempo ou o Prometheus estão parados THEN o Collector SHALL continuar `running` e tentar de novo, e os outros sinais SHALL continuar chegando aos destinos que estão de pé.
- **OBS-58** IF o banco não está acessível (stack sozinha) THEN o postgres-exporter SHALL responder `pg_up 0` sem sair do processo (coberto por OBS-44).
- **OBS-59** IF um atributo carrega dado pessoal num valor não string (por exemplo, um telefone como inteiro) THEN o Collector SHALL não redigi-lo. É uma limitação aceita e documentada no README; a #194 proíbe esse dado na origem.
- **OBS-60** IF os dois modos são subidos ao mesmo tempo THEN o segundo `up` SHALL falhar por conflito (nome de container ou porta já em uso), sem afetar o modo que já está no ar. O README manda derrubar um antes de subir o outro.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| OBS-01 | P1: Stack isolada | Tasks | Verified |
| OBS-02 | P1: Stack isolada | Tasks | Verified |
| OBS-03 | P1: Stack isolada | Tasks | Verified |
| OBS-04 | P1: Stack isolada | Tasks | Verified |
| OBS-05 | P1: Stack isolada | Tasks | Verified |
| OBS-06 | P1: Stack isolada | Tasks | Verified |
| OBS-07 | P1: Stack isolada | Tasks | Verified |
| OBS-08 | P1: Stack isolada | Tasks | Verified |
| OBS-09 | P1: Stack isolada | Tasks | Verified |
| OBS-10 | P1: Stack isolada | Tasks | Verified |
| OBS-11 | P1: Stack isolada | Tasks | Verified |
| OBS-12 | P1: Stack isolada | Tasks | Verified |
| OBS-13 | P1: Três sinais | Tasks | Verified |
| OBS-14 | P1: Três sinais | Tasks | Verified |
| OBS-15 | P1: Três sinais | Tasks | Verified |
| OBS-16 | P1: Três sinais | Tasks | Verified |
| OBS-17 | P1: Três sinais | Tasks | Verified |
| OBS-18 | P1: Três sinais | Tasks | Verified |
| OBS-19 | P1: Três sinais | Tasks | Verified |
| OBS-20 | P1: Três sinais | Tasks | Verified |
| OBS-21 | P1: Três sinais | Tasks | Verified |
| OBS-22 | P1: Redação | Tasks | Verified |
| OBS-23 | P1: Redação | Tasks | Verified |
| OBS-24 | P1: Redação | Tasks | Verified |
| OBS-25 | P1: Redação | Tasks | Verified |
| OBS-26 | P1: Redação | Tasks | Verified |
| OBS-27 | P1: Redação | Tasks | Verified |
| OBS-28 | P1: Redação | Tasks | Verified |
| OBS-29 | P1: Redação | Tasks | Verified |
| OBS-30 | P1: Redação | Tasks | Verified |
| OBS-31 | P1: Redação | Tasks | Verified |
| OBS-32 | P1: Redação | Tasks | Verified |
| OBS-33 | P2: Destino trocável | Tasks | Verified |
| OBS-34 | P2: Destino trocável | Tasks | Verified |
| OBS-35 | P2: Destino trocável | Tasks | Verified |
| OBS-36 | P2: Destino trocável | Tasks | Verified |
| OBS-37 | P2: Destino trocável | Tasks | Verified |
| OBS-38 | P2: Grafana provisionado | Tasks | Verified |
| OBS-39 | P2: Grafana provisionado | Tasks | Verified |
| OBS-40 | P2: Grafana provisionado | Tasks | Verified |
| OBS-41 | P2: Grafana provisionado | Tasks | Verified |
| OBS-42 | P2: Grafana provisionado | Tasks | Verified |
| OBS-43 | P2: Pyroscope, Faro e infra | Tasks | Verified |
| OBS-44 | P2: Pyroscope, Faro e infra | Tasks | Verified |
| OBS-45 | P2: Pyroscope, Faro e infra | Tasks | Verified |
| OBS-46 | P2: Pyroscope, Faro e infra | Tasks | Verified |
| OBS-47 | P2: Pyroscope, Faro e infra | Tasks | Verified |
| OBS-48 | P2: Pyroscope, Faro e infra | Tasks | Verified |
| OBS-49 | P2: Pyroscope, Faro e infra | Tasks | Verified |
| OBS-50 | P2: Pyroscope, Faro e infra | Tasks | Verified |
| OBS-51 | P3: Documentação | Tasks | Verified |
| OBS-52 | P3: Documentação | Tasks | Verified |
| OBS-53 | P3: Documentação | Tasks | Verified |
| OBS-54 | P3: Documentação | Tasks | Verified |
| OBS-55 | P3: Documentação | Tasks | Verified |
| OBS-56 | P3: Documentação | Tasks | Verified |
| OBS-57 | Edge cases | Tasks | Verified |
| OBS-58 | Edge cases | Tasks | Verified |
| OBS-59 | Edge cases | Tasks | Verified |
| OBS-60 | Edge cases | Tasks | Verified |

**ID format:** `OBS-NN`.

**Coverage:** 60 total, mapeados para tasks em `tasks.md`.

---

## Critérios de aceite da issue → requisitos

| Critério da issue | Requisitos |
| --- | --- |
| A stack sobe sozinha | OBS-01 |
| O compose principal funciona sem a stack | OBS-02, OBS-03, OBS-05 |
| Span, log e métrica aparecem no Grafana, com trace → logs | OBS-13 a OBS-21 |
| O Collector redige e-mail, JWT, CPF, CNPJ e telefone | OBS-22 a OBS-31 |
| A troca para o Grafana Cloud muda só variáveis (documentada) | OBS-33 a OBS-35, OBS-55 |
| Configuração versionada, sem segredo, `.env.example` atualizado | OBS-35, OBS-37, OBS-38, OBS-40 |
| `docs/observability/` explica como subir e o mapeamento | OBS-51 a OBS-56 |

---

## Success Criteria

- [ ] O script de verificação passa do zero (stack derrubada e volumes apagados) em até 5 minutos.
- [ ] Nenhum valor da tabela de entradas de redação aparece no Loki nem no Tempo.
- [ ] O compose principal sobe sem a stack com o mesmo resultado de antes da feature.
