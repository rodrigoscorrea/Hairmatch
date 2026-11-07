# Telemetria da aplicação Specification

**Issue:** [#194](https://github.com/rodrigoscorrea/Hairmatch/issues/194) · [Feature][Back/Front] Integrar a aplicação à telemetria (OpenTelemetry) sem depender dela.
**Origem:** o estudo "Observabilidade Hairmatch" (artifact GFDsHBv9zK8q3jDtJyu2tu) e a spike #192.
**Depende de:** #193 (`observability-stack`, PR #195). O backend manda tudo ao Collector em `http://otel-collector:4318`, como diz o AD-015.
**Escopo:** Complex. Toca backend e app, tem regra de resiliência própria e redação de dado pessoal na origem.
**Plataformas:** backend Django e app Expo (web e Android).

## Problem Statement

O backend não tem `LOGGING` nem OpenTelemetry. O chatbot e a rota de reservas usam `print()`, e não existe rota de saúde. O app não manda nenhum identificador de rastreio. Quando algo quebra, não dá para seguir uma requisição do app até o banco, o SNS ou o S3.

A #193 deixou a stack local pronta para receber os sinais. Falta ligar a aplicação a ela sem criar uma dependência nova: a telemetria é acessório. Com o Collector, o Grafana ou o Grafana Cloud fora do ar, a aplicação responde igual.

## Goals

- [ ] Uma reserva criada pelo app gera um trace único: a requisição, as queries e o publish do SNS. Os logs da requisição trazem o mesmo `trace_id`.
- [ ] Um upload de foto gera um trace com a conversão para WebP e o `PutObject` do S3.
- [ ] Com o Collector parado, ou sem o endpoint configurado, toda rota responde com o mesmo status e o mesmo corpo. O p95 sobe no máximo 50 ms.
- [ ] Nenhum e-mail, CPF, CNPJ, nome, telefone, CEP, endereço ou token aparece em log, span ou atributo dos fluxos cobertos.
- [ ] Nove contadores de negócio, com rótulos fechados, chegam ao Prometheus.
- [ ] O app abre e navega igual com a telemetria ligada, desligada ou com o Collector fora do ar.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Faro no app web (`@grafana/faro-web-sdk`) | Fase 1 do estudo, fora da issue. |
| Crashlytics no Android | Fase 1 do estudo, fora da issue. |
| SDK do Pyroscope (profiling contínuo) | Fora da issue. |
| Regras de alerta e dashboards de produção | Fora da issue. O dashboard `api-red.json` da #193 é usado como está. |
| Gunicorn, `gunicorn.conf.py` e a VPS | Fora da issue. A integração só deixa o ponto de entrada idempotente pronto para o `post_fork`. |
| Migrar o Gemini de `google.generativeai` para `google-genai` | Troca de SDK sem relação com a telemetria. O span do Gemini é manual. |
| Contador `hairmatch.chatbot.messages` | Decisão do usuário: o chatbot está deprecado por enquanto. |
| `tail_sampling` e amostragem abaixo de 100% | Fase 2 do estudo, quando o volume se aproximar da franquia. |
| Chave de idempotência em `POST /api/reserves` | Sugestão do estudo para o incidente da seção 5. Muda o contrato da API, vira outro card. |
| Tirar o push da requisição (fila) | Card #185 (AD-014). Aqui o push continua no `on_commit` e aparece no mesmo trace. |
| Spans e métricas gerados no aparelho | Sem Faro e sem Crashlytics, o app só propaga o `traceparent`. O trace começa no backend, filho do ID que o app gerou. |
| Instrumentar o cron do host (backup, expurgo) | Depende da VPS. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Métricas de negócio | Os 10 contadores do estudo menos `chatbot.messages`: `problems`, `reserves.created`, `push.results`, `auth.rejections`, `signup.events`, `uploads`, `cep.lookups`, `ai.requests` e `ai.tokens`. | Decisão do usuário. O chatbot está deprecado. | y |
| `traceparent` no app | Na web e no Android, ligado por `EXPO_PUBLIC_TRACE_PROPAGATION=true` e desligado por padrão. O backend acrescenta `traceparent` ao `CORS_ALLOW_HEADERS` na mesma mudança. | Decisão do usuário. Hoje um header fora do `CORS_ALLOW_HEADERS` (`settings.py:205`) faz o preflight da web (`:8081` → `:8000`) falhar e derruba toda chamada. | y |
| Variável nova no app | `EXPO_PUBLIC_TRACE_PROPAGATION`. | A issue autoriza: "sem a variável configurada, o app abre normalmente". É a exceção desta feature à regra de não criar variáveis. | y |
| Reserva × S3 | O AC da issue ("liga a requisição, as queries, o SNS e o S3") vira dois. O trace da reserva tem requisição, queries e SNS (TEL-22). O S3 é provado por um upload de foto (TEL-23). | `CreateReserve.post` (`reserve/views.py:87`) não toca o S3. O S3 só aparece no upload de imagem (`hairmatch/storage.py`). | n |
| SNS no trace da reserva | O span do SNS só existe se o cabeleireiro tiver um aparelho registrado (`PushDevice`). O teste registra um. | O seed não cria aparelhos, e `publish_alert` não chama o SNS sem eles. | n |
| Gemini | Span manual em volta de cada chamada ao Gemini, sem instrumentação de httpx. | O código usa `google.generativeai` (`gemini_client.py:3`, `chatbot/ai_utils.py:4`), que não passa por httpx. A dependência citada na issue não cobriria nada. | n |
| Onde a telemetria inicia | Só no processo que serve requisições (TEL-05). O ponto de entrada é idempotente e chamável do `post_fork` do Gunicorn no futuro. O design escolhe o gancho (hoje, o WSGI do `runserver`). | O `entrypoint.sh` roda `migrate`, `purge_unconfirmed_users` e os `populate_*` antes do `runserver`, e os testes rodam no mesmo container. Se cada comando iniciasse o SDK, ele exportaria e esperaria o flush contra um Collector que pode estar parado. | n |
| Limite de latência | Com o Collector inalcançável, o p95 de 50 requisições sequenciais fica no máximo 50 ms acima do p95 da mesma série com a telemetria desligada. | A issue pede "um limite definido". A exportação é assíncrona, então o custo esperado é perto de zero. 50 ms deixa margem para o ruído do container e ainda pega um envio síncrono (que custaria ≥ 2 s). | n |
| Limites da exportação | Desiste de cada envio em até 2 s, retentativas incluídas. Fila de 2048 itens por sinal, que descarta quando enche. Desligamento em até 5 s. Métricas exportadas a cada 15 s. | Um Collector parado não pode prender o restart do `runserver` nem crescer a memória sem limite. Os valores ficam perto dos padrões do SDK, com o timeout mais curto. | n |
| Três modos de "Collector fora do ar" | Conexão recusada (container parado), nome que não resolve (compose principal sem a stack) e IP que não responde (blackhole). | Cada um falha de um jeito: o blackhole espera o timeout, os outros falham na hora. A issue fala só em "Collector parado". | n |
| Variáveis do backend | Só as padrão do OTel: `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME` e `OTEL_RESOURCE_ATTRIBUTES` (com `service.version` e `deployment.environment.name`). Sem `GIT_SHA`, `APP_ENV` nem `LOG_LEVEL`. | A issue autoriza variáveis `OTEL_*`. O estudo usa `GIT_SHA` e `APP_ENV`, mas `OTEL_RESOURCE_ATTRIBUTES` cobre os dois sem criar nomes novos. | n |
| Nomes estáveis das métricas HTTP | O backend emite `http.server.request.duration` com `http.route`, os nomes estáveis da convenção semântica. | O dashboard `api-red.json` da #193 consulta `http_server_request_duration_seconds_*` por `http_route`. | n |
| Amostragem | 100% dos traces, respeitando a decisão de amostragem do `traceparent` recebido (parent-based). O app sempre manda a flag `01`. | O volume inicial cabe na franquia, como diz o estudo. | n |
| `url.path` no span do servidor | O span do servidor não leva `url.path`. A rota fica em `http.route` (template) e no nome do span. | `GET /api/postal-codes/{cep}` põe o CEP no path, e o CEP é dado pessoal na issue. O template já identifica a rota, e os IDs úteis vão como atributos `hairmatch.*`. | n |
| Marcadores, expressões e ordem da redação | `[email]`, `[jwt]`, `[cpf]`, `[cnpj]`, `[telefone]`, na ordem JWT → e-mail → CNPJ → CPF → telefone, com as mesmas expressões do Collector (`docker/observability/otel/config.yaml`, #193). | O mesmo dado é redigido igual nas duas barreiras e procurado pelo mesmo marcador no Loki. | n |
| Falsos positivos da redação | Um número com formato de telefone, CPF ou CNPJ vira marcador mesmo quando não é dado pessoal. O app acrescenta uma regra que o Collector não tem: o identificador do WhatsApp (`<dígitos>@s.whatsapp.net`). | É o lado seguro, como na #193. O padrão de telefone do Collector não casa com os 13 dígitos seguidos do identificador do WhatsApp. IDs internos vão como atributos inteiros, que o filtro não toca. | n |
| Logs em JSON também em dev | O stdout é JSON em todo ambiente. | A issue pede logs em JSON no stdout. Um formato por ambiente deixaria o dev sem testar o que roda em produção. | n |
| Nível de log | O logger raiz fica em `INFO`. | Sem variável nova. Mudar o nível é mudar o `settings.py`. | n |
| Rótulo `outcome` do push | `published`, `endpoint_gone` ou `unavailable` por aparelho. `error`, uma vez, quando `publish_alert` falha fora do laço (`dispatch.py:47`). | Cobre os três ramos de `publish_alert` sem confundir a falha de um aparelho com a falha da função toda. | n |
| Rótulo `source` do CEP | `cache`, `viacep`, `brasilapi`, `not_found` ou `unavailable`. | O `none` do estudo junta dois casos com ações diferentes: o CEP que não existe e os dois provedores fora. | n |
| Rótulo `reason` da sessão recusada | `missing` (sem cookie), `expired`, `invalid` (assinatura, emissor ou formato) e `unavailable` (JWKS do Cognito fora). | Uma onda de `invalid` aponta rotação de chave. Uma de `expired` aponta o refresh do app. | n |
| Rótulo `feature` do Gemini | `profile` (`hairdresser_profile_ai_completion`) e `chatbot` (as três chamadas do chatbot). | O chatbot está deprecado, mas ainda chama o Gemini e gasta tokens. | n |
| `GET /api/health` | Anônima e sem throttle. Checa só o Postgres (`SELECT 1`). Fica fora da instrumentação. O 503 usa o slug novo `service-unavailable`. A rota vira RT-105. | A issue pede "checa o Postgres" e "excluído da instrumentação". O Synthetic Monitoring chama a rota a cada minuto. Nenhum slug do catálogo (AD-006) descreve "o serviço não está pronto". | n |
| Validação de corpo × busca do pai (L-019) | N/A para a única rota nova. | `GET /api/health` não tem corpo nem recurso pai. | n |
| Gerador do `traceparent` no app | Na web, `crypto.getRandomValues`. No Android, um gerador que não exige pacote nativo novo. | Um ID de trace não é segredo. Evitar o `expo-crypto` dispensa rebuild do Android. O Hermes não garante `crypto.getRandomValues`. | n |
| Testes dos modos de Collector fora do ar | TEL-09 a TEL-11 rodam cada modo num processo separado (um subprocesso do servidor ou do Python por modo), e não dentro do processo do test runner. | Os providers globais e a inserção do middleware do Django não voltam atrás dentro de um processo. Com TEL-04, uma segunda inicialização é no-op. | n |
| Testes que dependem do botocore | TEL-18, TEL-22, TEL-23, TEL-48 e o login de TEL-49 são verificados contra o LocalStack e o MiniStack (E2E de API) ou com um client boto3 real e o `Stubber`, nunca contra o `sns_fake` nem o `InMemoryStorage`. | Os fakes dos testes não passam pelo botocore, e um teste contra eles passaria sem provar nada. | n |
| Contexto do `on_commit` | O push do `on_commit` roda no mesmo thread da requisição e cai no mesmo trace. O design confere isso no `runserver`. | Diz o estudo, mas ninguém mediu no código atual. | n |

**Open questions:** none. Tudo está resolvido ou registrado acima.

---

## User Stories

### P1: A aplicação não depende da telemetria ⭐ MVP

**User Story**: Como cliente ou cabeleireiro, quero que o app funcione igual quando a stack de observabilidade está desligada ou quebrada.

**Why P1**: É a regra principal da issue. Uma telemetria que derruba a aplicação é pior que nenhuma.

**Acceptance Criteria**:

1. **TEL-01** WHERE `OTEL_EXPORTER_OTLP_ENDPOINT` está ausente ou vazia, the backend SHALL não instalar `TracerProvider`, `MeterProvider` nem `LoggerProvider` do SDK, e os providers globais SHALL continuar os no-op da API.
2. **TEL-02** WHILE a telemetria está desligada, the backend SHALL não abrir nenhuma conexão de rede para exportar telemetria nem escrever nenhuma linha de log sobre exportação.
3. **TEL-03** IF o import ou a inicialização do SDK lança uma exceção THEN the backend SHALL registrar um único log `WARNING` com o tipo da exceção, sem a mensagem, e seguir servindo com a telemetria desligada.
4. **TEL-04** WHEN o ponto de entrada da telemetria é chamado mais de uma vez no mesmo processo THEN the backend SHALL ignorar as chamadas seguintes, sem duplicar providers, processors nem instrumentações.
5. **TEL-05** The backend SHALL iniciar a telemetria a partir do ambiente só no processo que serve requisições, e nunca nos comandos do `manage.py` (`migrate`, `test`, `purge_unconfirmed_users`, `populate_*`) nem no test runner. Os testes instalam os próprios providers, com exporters em memória.
6. **TEL-06** The backend SHALL exportar spans, métricas e logs em lote, num thread que não é o da requisição.
7. **TEL-07** The exportador de cada sinal SHALL desistir de um envio em até 2 s, retentativas incluídas.
8. **TEL-08** IF a fila de spans ou a de logs chega a 2048 itens THEN the backend SHALL descartar os itens novos sem bloquear o thread que os produz.
9. **TEL-09** IF o Collector está inalcançável (conexão recusada, nome que não resolve ou IP que não responde) THEN each rota coberta pelos testes SHALL devolver o mesmo status e o mesmo corpo que devolve com a telemetria desligada.
10. **TEL-10** IF o Collector está inalcançável THEN the p95 de 50 requisições sequenciais a uma mesma rota instrumentada, que emite pelo menos um log por requisição, SHALL ficar no máximo 50 ms acima do p95 da mesma série com a telemetria desligada.
11. **TEL-11** WHEN o processo encerra (SIGTERM ou reinício do autoreload) com o Collector inalcançável THEN the desligamento do SDK SHALL terminar em até 5 s.
12. **TEL-12** WHILE o SDK não está inicializado, the helpers de métrica e de span (`hairmatch/telemetry.py`) SHALL funcionar como no-op, sem lançar exceção.
13. **TEL-13** IF uma chamada ao SDK feita dentro de um helper de métrica ou de span lança uma exceção THEN the helper SHALL não propagá-la, e a view SHALL devolver a mesma resposta que devolveria sem telemetria.
14. **TEL-14** The logs dos loggers `opentelemetry.*` SHALL ir só para o stdout, nunca para o handler OTLP.
15. **TEL-15** WHILE o Collector continua inalcançável, the backend SHALL escrever no máximo uma linha de erro de exportação por sinal a cada 60 s.

**Independent Test**: rodar a suíte de resiliência com o endpoint vazio, apontado para uma porta fechada, para um nome que não resolve e para um IP que não responde. Comparar status, corpo e p95 com a telemetria desligada, e medir o tempo de desligamento.

---

### P1: Uma requisição vira um trace ⭐ MVP

**User Story**: Como desenvolvedor, quero ver no Tempo por onde uma requisição passou: banco, AWS, provedores HTTP e Gemini.

**Why P1**: É o primeiro critério de aceite da issue e o motivo da instrumentação.

**Acceptance Criteria**:

1. **TEL-16** WHEN o backend atende uma requisição sob `/api/` com a telemetria ligada THEN it SHALL criar um span `SERVER` cujo `http.route` é o template da rota em `urls.py` (ex.: `api/hairdressers/<int:hairdresser_id>/gallery-photos`), nunca o path cru.
2. **TEL-17** WHEN uma query SQL roda dentro da requisição THEN the backend SHALL criar um span `CLIENT` filho do span da requisição, com a query parametrizada e sem os valores dos parâmetros.
3. **TEL-18** WHEN o backend chama a AWS por boto3 (S3, SNS ou Cognito) dentro da requisição THEN it SHALL criar um span `CLIENT` filho, com o serviço e a operação (ex.: `SNS.Publish`).
4. **TEL-19** WHEN o backend chama um serviço HTTP pelo `requests` (ViaCEP, BrasilAPI ou Evolution API) THEN it SHALL criar um span `CLIENT` filho, com método, host e status da resposta.
5. **TEL-20** WHEN a requisição chega com um `traceparent` W3C válido THEN the span da requisição SHALL usar o `trace_id` recebido e ter o `parent-id` recebido como pai.
6. **TEL-21** IF o `traceparent` recebido é inválido THEN the backend SHALL ignorá-lo, abrir um trace novo e responder como responderia sem o header.
7. **TEL-22** WHEN `POST /api/reserves` cria uma reserva para um cabeleireiro com um aparelho registrado THEN the trace da requisição SHALL ter, sob o mesmo `trace_id`, o span da requisição, os spans das queries e o span `SNS.Publish` do `on_commit`.
8. **TEL-23** WHEN `POST /api/hairdressers/{id}/gallery-photos` grava uma foto THEN the trace da requisição SHALL ter os spans `image.to_webp` e `S3.PutObject`, filhos do span da requisição.
9. **TEL-24** The span `image.to_webp` SHALL ter os atributos inteiros `image.bytes_in` e `image.bytes_out`, e nenhum outro dado da imagem.
10. **TEL-25** WHEN o backend chama o Gemini THEN it SHALL criar um span `gemini generate_content` com `gen_ai.request.model` e `hairmatch.ai.feature`, sem o prompt e sem a resposta.
11. **TEL-26** WHEN a resposta do Gemini traz a contagem de tokens THEN the span do Gemini SHALL ter `gen_ai.usage.input_tokens` e `gen_ai.usage.output_tokens`.
12. **TEL-27** IF a chamada ao Gemini lança uma exceção THEN the span SHALL terminar com status de erro e o tipo da exceção, e a exceção SHALL seguir para o tratamento que o código já faz.
13. **TEL-28** WHEN `POST /api/reserves` cria uma reserva THEN the span da requisição SHALL ter os atributos inteiros `hairmatch.reserve_id` e `hairmatch.hairdresser_id`.
14. **TEL-29** The resource de todo sinal do backend SHALL ter `service.name` igual a `OTEL_SERVICE_NAME`, ou `hairmatch-api` quando ela está vazia.
15. **TEL-30** The resource de todo sinal do backend SHALL ter `service.version` e `deployment.environment.name` vindos de `OTEL_RESOURCE_ATTRIBUTES`, ou `dev` quando ausentes.
16. **TEL-31** The resource de todo sinal do backend SHALL ter um `service.instance.id` único por processo.
17. **TEL-32** The backend SHALL emitir a duração das requisições no histograma `http.server.request.duration` (unidade `s`) com o atributo `http.route`, que o Prometheus guarda como `http_server_request_duration_seconds` com o rótulo `http_route`.
18. **TEL-33** WHEN uma requisição é medida dentro de um span amostrado THEN the ponto do histograma `http.server.request.duration` SHALL levar um exemplar com o `trace_id` desse span.
19. **TEL-34** WHEN a requisição é `GET /api/health` THEN the backend SHALL não criar span nem registrar ponto de métrica HTTP para ela.
20. **TEL-35** The backend SHALL guardar 100% dos traces que não chegam com a flag de amostragem `00` no `traceparent`.

**Independent Test**: com a stack da #193 no ar, criar uma reserva com um aparelho registrado e enviar uma foto da galeria. Abrir os dois traces no Tempo e conferir os spans e o histograma no dashboard `api-red.json`. Nos testes automatizados, usar um exporter em memória.

---

### P1: Logs em JSON ligados ao trace ⭐ MVP

**User Story**: Como desenvolvedor, quero sair de um span direto para os logs dele, e ter o stdout como plano B quando a telemetria cair.

**Why P1**: A issue pede `LOGGING` em JSON com `trace_id`, sem `print()`. Os atalhos trace → logs da #193 dependem disso.

**Acceptance Criteria**:

1. **TEL-36** The backend SHALL configurar `LOGGING` com um handler de stdout que escreve uma linha JSON por registro, com os campos `ts`, `level`, `name` e `message`.
2. **TEL-37** WHEN um log é emitido dentro de um span ativo THEN the linha JSON SHALL trazer `trace_id` (32 hex) e `span_id` (16 hex) iguais aos do span.
3. **TEL-38** WHILE a telemetria está desligada, the handler de stdout SHALL escrever a mesma linha JSON sem os campos `trace_id` e `span_id`, e sem erro de formatação.
4. **TEL-39** WHERE a telemetria está ligada, the backend SHALL mandar cada registro também ao Collector por OTLP, com o contexto do trace no registro.
5. **TEL-40** WHEN um log carrega uma exceção THEN the linha JSON SHALL trazer o traceback no campo `exc_info` da mesma linha.
6. **TEL-41** The código do backend fora dos testes SHALL ter zero chamadas a `print()`.
7. **TEL-42** The logs que substituem os `print()` de `chatbot/ai_utils.py`, `chatbot/views.py` e `reserve/views.py` SHALL trazer só o evento, IDs internos e o tipo da exceção, nunca o número do WhatsApp, o texto da mensagem nem a resposta do Gemini.
8. **TEL-43** The access log do `runserver` (logger `django.server`) SHALL sair no mesmo formato JSON, com o path sem a query string.

**Independent Test**: emitir um log dentro e fora de um span, com a telemetria ligada e desligada, e validar cada linha do stdout como JSON. Com a stack no ar, abrir "Logs for this span" de um trace de reserva e ver as linhas dele.

---

### P1: Nenhum dado pessoal sai do processo ⭐ MVP

**User Story**: Como titular dos dados, quero que meu CPF, telefone, e-mail ou endereço não sejam copiados para um fornecedor de observabilidade.

**Why P1**: A issue proíbe dado pessoal em log, span ou atributo. O código é a primeira das três barreiras do estudo: o código não loga, o filtro do `LOGGING` redige e o Collector redige de novo.

**Acceptance Criteria**:

1. **TEL-44** The filtro de redação SHALL trocar, na mensagem final do registro, o JWT por `[jwt]`, o e-mail por `[email]`, o CNPJ por `[cnpj]`, o CPF por `[cpf]` e o telefone por `[telefone]`, nessa ordem, com as mesmas expressões de `docker/observability/otel/config.yaml`. The filtro também troca o número do WhatsApp (`<dígitos>@s.whatsapp.net`) por `[telefone]`.
2. **TEL-45** The filtro de redação SHALL valer também para o texto do traceback (`exc_info`) e para o texto da pilha (`stack_info`).
3. **TEL-46** The filtro de redação SHALL estar no handler de stdout e no handler OTLP.
4. **TEL-47** The spans do backend SHALL não ter os atributos `url.query`, `url.full`, `url.path`, `http.url`, `http.target`, `client.address`, `enduser.id` nem `http.request.header.*`.
5. **TEL-48** The span do SNS SHALL não ter o ARN do endpoint, o token do aparelho nem o corpo da mensagem em nenhum atributo.
6. **TEL-49** WHEN os fluxos cobertos rodam com um exporter em memória (cadastro, login, consulta de CEP, o preflight `OPTIONS` da consulta de CEP, reserva com push, upload de foto e geração de perfil pelo Gemini) THEN nenhum nome de span, descrição de status, atributo de span, de evento de span ou de resource, e nenhum registro de log, SHALL conter o e-mail, o CPF, o CNPJ, o nome, o telefone, o CEP, o endereço ou o token usados no teste.
7. **TEL-86** WHEN uma exceção é registrada num span THEN the `exception.message` e o `exception.stacktrace` do evento, e a descrição do status do span, SHALL passar pela mesma redação de TEL-44. O Collector da #193 não redige eventos de span nem o status.

**Independent Test**: testes do filtro com uma tabela de entradas (e-mail, JWT, CPF e CNPJ com e sem máscara, telefone e número do WhatsApp) e um teste por fluxo coberto, que procura os valores do teste em todos os atributos exportados.

---

### P1: Métricas de negócio com rótulos fechados ⭐ MVP

**User Story**: Como desenvolvedor, quero saber por número o que está dando errado: que slug de erro subiu, quantos pushes falharam e quantos tokens o Gemini gastou.

**Why P1**: A issue pede o contador por slug em `problem_response` e o resultado do push. O usuário ampliou para os 9 contadores do estudo.

**Acceptance Criteria**:

1. **TEL-50** WHEN `problem_response` monta uma resposta THEN the backend SHALL somar 1 em `hairmatch.problems`, com os rótulos `slug` e `status` dessa resposta.
2. **TEL-51** WHEN a transação que cria uma reserva confirma THEN the backend SHALL somar 1 em `hairmatch.reserves.created`, com `channel` igual a `app` (`CreateReserve`) ou `whatsapp` (`create_new_reserve`).
3. **TEL-52** WHEN `publish_alert` termina a tentativa de um aparelho THEN the backend SHALL somar 1 em `hairmatch.push.results`, com `outcome` igual a `published`, `endpoint_gone` ou `unavailable`.
4. **TEL-53** IF `publish_alert` falha fora do laço dos aparelhos THEN the backend SHALL somar 1 em `hairmatch.push.results`, com `outcome` igual a `error`.
5. **TEL-54** WHEN o autenticador recusa uma sessão THEN the backend SHALL somar 1 em `hairmatch.auth.rejections`, com `reason` igual a `missing`, `expired`, `invalid` ou `unavailable`.
6. **TEL-55** WHEN um passo do cadastro por e-mail termina THEN the backend SHALL somar 1 em `hairmatch.signup.events`, com `step` igual a `created` (cadastro aceito), `confirmed` (código aceito), `resent` (código reenviado) ou `throttled` (429 numa dessas três rotas).
7. **TEL-56** WHEN um upload de imagem termina THEN the backend SHALL somar 1 em `hairmatch.uploads`, com `kind` igual a `profile`, `review` ou `gallery` e `outcome` igual a `stored`, `invalid_image` ou `failed`.
8. **TEL-57** WHEN `lookup_cep` termina THEN the backend SHALL somar 1 em `hairmatch.cep.lookups`, com `source` igual a `cache`, `viacep`, `brasilapi`, `not_found` ou `unavailable`.
9. **TEL-58** WHEN uma chamada ao Gemini termina THEN the backend SHALL somar 1 em `hairmatch.ai.requests`, com `feature` igual a `profile` ou `chatbot` e `outcome` igual a `ok` ou `error`.
10. **TEL-59** WHEN a resposta do Gemini traz a contagem de tokens THEN the backend SHALL somar os tokens em `hairmatch.ai.tokens`, com `feature` e `direction` igual a `input` ou `output`.
11. **TEL-60** The métricas de negócio SHALL ter só os rótulos listados de TEL-50 a TEL-59, cada um com um valor do conjunto fechado listado, e nunca ID, e-mail, path cru nem texto livre.

**Independent Test**: com um leitor de métricas em memória, provocar cada caso (um erro de cada tipo, uma reserva por canal, push com sucesso, endpoint morto e SNS fora, cada motivo de sessão recusada, cada passo do cadastro, cada tipo e resultado de upload, cada fonte de CEP, Gemini com sucesso e com erro) e conferir o contador e os rótulos.

---

### P2: Rota de saúde

**User Story**: Como operador, quero uma rota que diga se a API está de pé e alcança o banco, para a sonda externa e o `docker compose`.

**Why P2**: A issue pede a rota. Ela não depende da telemetria, mas é o alvo do Synthetic Monitoring.

**Acceptance Criteria**:

1. **TEL-61** WHEN `GET /api/health` chega e o Postgres responde a `SELECT 1` THEN the backend SHALL responder 200 com o corpo `{"status": "ok"}`.
2. **TEL-62** IF o Postgres não responde ao `SELECT 1` THEN the backend SHALL responder 503 em `application/problem+json`, com o slug `service-unavailable`.
3. **TEL-63** The rota `GET /api/health` SHALL responder sem sessão e sem throttle.
4. **TEL-64** The resposta de `GET /api/health` SHALL não depender do Collector, da AWS nem de provedor externo.
5. **TEL-65** IF a rota recebe um método diferente de `GET`, `HEAD` ou `OPTIONS` THEN the backend SHALL responder 405 `method-not-allowed`, com `GET` no header `Allow`.
6. **TEL-66** The rota SHALL entrar como RT-105 na Route Table do spec `api-restful-routes` e no `ROUTE_TABLE` de `hairmatch/test_routes.py`.
7. **TEL-67** The slug `service-unavailable` (503, `Service unavailable`) SHALL entrar no catálogo do spec `api-problem-details`, no `CATALOG` de `hairmatch/problems.py` e no catálogo do app (`frontend-mobile/utils/api-problem.ts`).

**Independent Test**: chamar `GET /api/health` com o banco de pé e com a conexão quebrada no teste. Rodar `test_routes.py`.

---

### P2: O app propaga o trace

**User Story**: Como desenvolvedor, quero achar no Tempo o trace de uma chamada que o app fez, a partir do ID que o app gerou.

**Why P2**: A issue pede o `traceparent` no interceptor. Sem Faro e sem Crashlytics, o trace ainda começa no backend.

**Acceptance Criteria**:

1. **TEL-68** WHERE `EXPO_PUBLIC_TRACE_PROPAGATION` é `true`, the `axiosInstance` SHALL acrescentar a toda requisição o header `traceparent` no formato `00-<32 hex>-<16 hex>-01`, em minúsculas.
2. **TEL-69** The `trace-id` e o `parent-id` gerados pelo app SHALL nunca ser todos zeros.
3. **TEL-70** WHEN o app faz duas requisições THEN each requisição SHALL levar um `trace-id` diferente.
4. **TEL-71** WHERE `EXPO_PUBLIC_TRACE_PROPAGATION` está ausente ou tem valor diferente de `true`, the app SHALL não acrescentar o header `traceparent`.
5. **TEL-72** IF a geração do `traceparent` lança uma exceção THEN the requisição SHALL sair sem o header, com o mesmo resultado.
6. **TEL-73** The código de telemetria do app SHALL ficar em `frontend-mobile/utils/telemetry.ts` (nativo) e `frontend-mobile/utils/telemetry.web.ts` (web), com as mesmas exportações.
7. **TEL-74** The app SHALL não ganhar nenhuma dependência nativa nova por causa da telemetria.
8. **TEL-75** The backend SHALL incluir `traceparent` em `CORS_ALLOW_HEADERS`.
9. **TEL-76** WHILE `EXPO_PUBLIC_TRACE_PROPAGATION` é `true` e o Collector está fora do ar, the app SHALL abrir e completar login, busca, perfil do cabeleireiro e reserva com o mesmo resultado de quando a variável está desligada.

**Independent Test**: testes do gerador e do interceptor no Jest, com a variável ligada e desligada e com o gerador quebrado. Na web, conferir o preflight com o header ligado. No Android, achar no Tempo o `trace_id` do header que o app mandou.

---

### P2: Configuração e documentação

**User Story**: Como desenvolvedor, quero ligar e desligar a telemetria só com variáveis, e ter um passo a passo.

**Why P2**: A issue pede as variáveis no `.env.example` e no compose, vazias por padrão.

**Acceptance Criteria**:

1. **TEL-77** The `docker/docker-compose.yml` SHALL passar ao serviço `django` as variáveis `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME` e `OTEL_RESOURCE_ATTRIBUTES`, vazias quando não definidas.
2. **TEL-78** The `docker/.env.example` SHALL listar as três `OTEL_*` vazias, com um comentário que indica `http://otel-collector:4318` para o modo combinado da #193.
3. **TEL-79** The `frontend-mobile/.env.example` SHALL listar `EXPO_PUBLIC_TRACE_PROPAGATION` vazia.
4. **TEL-80** The `backend/requirements.txt` SHALL fixar a versão exata de cada pacote OpenTelemetry e do formatador JSON de log.
5. **TEL-81** The `docs/observability/README.md` SHALL ter uma seção que explica como ligar o backend e o app à stack e como achar no Grafana o trace e os logs de uma reserva.

**Independent Test**: subir o compose principal sem `docker/.env` e conferir que o backend sobe com a telemetria desligada. Seguir a seção do README do zero.

---

## Edge Cases

- **TEL-82** IF o `traceparent` recebido tem a flag de amostragem `00` THEN the backend SHALL propagar a decisão, sem exportar o trace, e responder normalmente.
- **TEL-83** IF a requisição está fora de `/api/` (ex.: `admin/`) THEN the backend SHALL instrumentá-la com as mesmas regras de redação de TEL-47 e TEL-49.
- **TEL-84** IF o Collector volta depois de ficar fora THEN the backend SHALL voltar a exportar os sinais novos sem reiniciar o processo.
- **TEL-85** IF o refresh de sessão do app (401 → `POST /api/auth/refresh` → nova tentativa) acontece com a variável ligada THEN each uma das três requisições SHALL levar o seu próprio `traceparent`.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| TEL-01 | P1: Não depende da telemetria | Execute | Done |
| TEL-02 | P1: Não depende da telemetria | Execute | Done |
| TEL-03 | P1: Não depende da telemetria | Execute | Done |
| TEL-04 | P1: Não depende da telemetria | Execute | Done |
| TEL-05 | P1: Não depende da telemetria | Execute | Done |
| TEL-06 | P1: Não depende da telemetria | Execute | Done |
| TEL-07 | P1: Não depende da telemetria | Execute | Done |
| TEL-08 | P1: Não depende da telemetria | Execute | Done |
| TEL-09 | P1: Não depende da telemetria | Specify | Pending |
| TEL-10 | P1: Não depende da telemetria | Specify | Pending |
| TEL-11 | P1: Não depende da telemetria | Specify | Pending |
| TEL-12 | P1: Não depende da telemetria | Execute | Done |
| TEL-13 | P1: Não depende da telemetria | Execute | Done |
| TEL-14 | P1: Não depende da telemetria | Execute | Done |
| TEL-15 | P1: Não depende da telemetria | Execute | Done |
| TEL-16 | P1: Requisição vira trace | Execute | Done |
| TEL-17 | P1: Requisição vira trace | Execute | Done |
| TEL-18 | P1: Requisição vira trace | Execute | Done |
| TEL-19 | P1: Requisição vira trace | Execute | Done |
| TEL-20 | P1: Requisição vira trace | Execute | Done |
| TEL-21 | P1: Requisição vira trace | Execute | Done |
| TEL-22 | P1: Requisição vira trace | Execute | Done |
| TEL-23 | P1: Requisição vira trace | Execute | Done |
| TEL-24 | P1: Requisição vira trace | Execute | Done |
| TEL-25 | P1: Requisição vira trace | Execute | Done |
| TEL-26 | P1: Requisição vira trace | Execute | Done |
| TEL-27 | P1: Requisição vira trace | Execute | Done |
| TEL-28 | P1: Requisição vira trace | Execute | Done |
| TEL-29 | P1: Requisição vira trace | Execute | Done |
| TEL-30 | P1: Requisição vira trace | Execute | Done |
| TEL-31 | P1: Requisição vira trace | Execute | Done |
| TEL-32 | P1: Requisição vira trace | Execute | Done |
| TEL-33 | P1: Requisição vira trace | Execute | Done |
| TEL-34 | P1: Requisição vira trace | Execute | Done |
| TEL-35 | P1: Requisição vira trace | Execute | Done |
| TEL-36 | P1: Logs em JSON | Execute | Done |
| TEL-37 | P1: Logs em JSON | Execute | Done |
| TEL-38 | P1: Logs em JSON | Execute | Done |
| TEL-39 | P1: Logs em JSON | Specify | Pending |
| TEL-40 | P1: Logs em JSON | Execute | Done |
| TEL-41 | P1: Logs em JSON | Execute | Done |
| TEL-42 | P1: Logs em JSON | Execute | Done |
| TEL-43 | P1: Logs em JSON | Execute | Done |
| TEL-44 | P1: Sem dado pessoal | Execute | Done |
| TEL-45 | P1: Sem dado pessoal | Execute | Done |
| TEL-46 | P1: Sem dado pessoal | Execute | Done |
| TEL-47 | P1: Sem dado pessoal | Execute | Done |
| TEL-48 | P1: Sem dado pessoal | Execute | Done |
| TEL-49 | P1: Sem dado pessoal | Specify | Pending |
| TEL-50 | P1: Métricas de negócio | Execute | Done |
| TEL-51 | P1: Métricas de negócio | Execute | Done |
| TEL-52 | P1: Métricas de negócio | Execute | Done |
| TEL-53 | P1: Métricas de negócio | Execute | Done |
| TEL-54 | P1: Métricas de negócio | Execute | Done |
| TEL-55 | P1: Métricas de negócio | Execute | Done |
| TEL-56 | P1: Métricas de negócio | Execute | Done |
| TEL-57 | P1: Métricas de negócio | Execute | Done |
| TEL-58 | P1: Métricas de negócio | Execute | Done |
| TEL-59 | P1: Métricas de negócio | Execute | Done |
| TEL-60 | P1: Métricas de negócio | Execute | Done |
| TEL-61 | P2: Rota de saúde | Execute | Done |
| TEL-62 | P2: Rota de saúde | Execute | Done |
| TEL-63 | P2: Rota de saúde | Execute | Done |
| TEL-64 | P2: Rota de saúde | Execute | Done |
| TEL-65 | P2: Rota de saúde | Execute | Done |
| TEL-66 | P2: Rota de saúde | Execute | Done |
| TEL-67 | P2: Rota de saúde | Execute | Done |
| TEL-68 | P2: App propaga o trace | Specify | Pending |
| TEL-69 | P2: App propaga o trace | Specify | Pending |
| TEL-70 | P2: App propaga o trace | Specify | Pending |
| TEL-71 | P2: App propaga o trace | Specify | Pending |
| TEL-72 | P2: App propaga o trace | Specify | Pending |
| TEL-73 | P2: App propaga o trace | Specify | Pending |
| TEL-74 | P2: App propaga o trace | Specify | Pending |
| TEL-75 | P2: App propaga o trace | Execute | Done |
| TEL-76 | P2: App propaga o trace | Specify | Pending |
| TEL-77 | P2: Configuração e documentação | Specify | Pending |
| TEL-78 | P2: Configuração e documentação | Specify | Pending |
| TEL-79 | P2: Configuração e documentação | Specify | Pending |
| TEL-80 | P2: Configuração e documentação | Execute | Done |
| TEL-81 | P2: Configuração e documentação | Specify | Pending |
| TEL-82 | Edge Cases | Execute | Done |
| TEL-83 | Edge Cases | Execute | Done |
| TEL-84 | Edge Cases | Specify | Pending |
| TEL-85 | Edge Cases | Specify | Pending |
| TEL-86 | P1: Sem dado pessoal | Execute | Done |

**Coverage:** 86 total, nenhum mapeado para tasks ainda (o `tasks.md` sai depois do Design).

---

## Critérios de aceite da issue → requisitos

| Critério da issue | Requisitos |
| --- | --- |
| Uma reserva criada pelo app gera um trace único com requisição, queries, SNS e S3, e os logs trazem o mesmo `trace_id` | TEL-16 a TEL-23, TEL-37, TEL-39 (o S3 está em TEL-23; ver Assumptions) |
| O erro de `problem_response` incrementa o contador por slug | TEL-50 |
| Com o Collector parado, mesmo status, sem aumento perceptível de latência, e o servidor reinicia | TEL-07 a TEL-11 |
| Sem a variável de endpoint, backend e app sobem sem conectar nem logar erro | TEL-01, TEL-02, TEL-71 |
| Teste: SDK com destino inalcançável não faz a view falhar nem atrasar; vale para o handler de log | TEL-09, TEL-10 (a rota medida emite log), TEL-13, TEL-39 |
| Teste do filtro de redação e de que nenhum atributo de span carrega dado pessoal | TEL-44 a TEL-49, TEL-86 |
| O app abre e navega com a telemetria desligada ou fora do ar | TEL-71, TEL-72, TEL-76 |
| Sem `print()` nas rotas cobertas; logs em JSON no stdout | TEL-36, TEL-41, TEL-42 |
| Specs em `.specs/features/` | este diretório |

---

## Success Criteria

- [ ] A suíte de resiliência passa nos três modos de Collector fora do ar, com o p95 dentro do limite de TEL-10.
- [ ] No Tempo, o trace de uma reserva criada pelo app tem o `trace_id` do header do app, e "Logs for this span" mostra os logs dela.
- [ ] Nenhum valor de dado pessoal usado nos testes aparece no exporter em memória, no stdout, no Loki ou no Tempo.
- [ ] O dashboard `api-red.json` da #193 mostra taxa, erros e duração do `hairmatch-api` sem nenhuma mudança no dashboard.
- [ ] `grep -rn "print(" backend --include=*.py`, sem os testes e o `.venv`, não devolve nada.
