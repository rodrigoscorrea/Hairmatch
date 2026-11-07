# Stack de observabilidade local Context

**Gathered:** 2026-11-07
**Spec:** `.specs/features/observability-stack/spec.md`
**Status:** Ready for design

**Fontes:**
- a issue #193;
- o estudo "Observabilidade Hairmatch" (artifact GFDsHBv9zK8q3jDtJyu2tu), seções 2, 3, 6 (abas "Collector" e "Compose") e 7;
- as respostas do usuário nesta sessão.

---

## Feature Boundary

Um compose separado, em `docker/observability/`, com:
- OTel Collector (contrib), Loki, Tempo, Prometheus, Pyroscope, Grafana Alloy (receiver do Faro) e Grafana;
- postgres-exporter, mais os receivers `hostmetrics` e `docker_stats` no Collector.

O Collector redige dado pessoal e exporta para a stack local ou, só por variáveis, para o Grafana Cloud. O Grafana vem provisionado com os data sources e o dashboard RED. A documentação fica em `docs/observability/`.

Nenhum código do backend ou do app muda. A instrumentação é da #194.

---

## Implementation Decisions

### Fases desta rodada

- Specify, Design e Tasks. O Execute começa só depois da aprovação das tasks.

### Armazenamento de métricas

- Só Prometheus, com o receiver OTLP. O Mimir não entra na stack local.
- O estudo também troca Mimir por Prometheus onde descreve a stack do Hairmatch: o diagrama do mapa, o chip "Entra" e o card de sinal. As menções genéricas à sigla LGTM ficam como estão.

### Faro e Synthetic Monitoring

- Faro: receiver local via Grafana Alloy (`faro.receiver`).
- Synthetic Monitoring: sem serviço local. Aparece só na tabela "serviço local → Grafana Cloud".

### Extras

- Entram os três: postgres-exporter, `hostmetrics` e `docker_stats`.
- O usuário pediu antes a diferença entre eles e o Pyroscope:
  - os três são métricas vistas de fora do código (banco, máquina, containers) e funcionam assim que a stack sobe;
  - o Pyroscope é profiling de dentro do processo, depende de um SDK no backend e sobe vazio.

### Agent's Discretion

Não houve "você decide" explícito. As escolhas técnicas abaixo estão registradas como assumptions na spec:
- a mecânica do modo combinado;
- os nomes das variáveis `OBS_*`;
- os marcadores e a ordem da redação;
- a retenção;
- o acesso anônimo ao Grafana;
- as versões das imagens.

### Declined / Undiscussed Gray Areas → Assumptions

- **Como o backend alcança o Collector:** com os dois arquivos no mesmo comando (`-f … -f …`), um projeto só. Foi testado: dois projetos dividindo uma rede de nome fixo quebram nas duas ordens.
- **Credencial do postgres-exporter em dev:** o usuário do banco de dev.
- **Onde a redação atua:** corpo de log, atributos string, primeiro nível de um corpo map e resource. A limitação para valores não string está aceita.
- **Falsos positivos aceitos:** sequências de 10 a 14 dígitos, como o ID de conta da AWS e timestamps em ms.

---

## Specific References

- O Collector, os processors e a redação partem da aba "Collector" do estudo:
  - acrescentam CNPJ e telefone com máscara;
  - trocam o exporter único `otlphttp/grafana` por endpoints por sinal com padrão local.
- A rotação de log (`max-size: 10m`, `max-file: 3`) e a versão fixa das imagens vêm da aba "Compose" do estudo.
- O dashboard RED parte das consultas da seção 8 do estudo (`http_server_request_duration_seconds_*`, `http_route`).

---

## Deferred Ideas

- `pg_stat_statements` e um papel `pg_monitor` para o postgres-exporter: exigem mudar o Postgres do compose principal. Ficam para a VPS.
- `filelog` do Nginx e do Postgres: ficam para a VPS.
- Regras de alerta, SLOs e `tail_sampling`: fases 1 e 2 do estudo.
- Checks com script (k6) no Synthetic Monitoring: fase 2 do estudo.
