# STATE

## Decisions

### AD-001
- **Decision**: Login e cadastro por provedor de identidade externo (Google hoje) não criam usuário parcial. Para uma conta nova, o backend devolve um token de cadastro pendente e assinado (sem estado no servidor), e a conclusão passa pelo `POST /api/auth/register` existente. Toda emissão de sessão (cookie `jwt`, payload `{id, exp, iat}`) passa por `backend/users/auth_tokens.py`.
- **Reason**: As colunas de telefone e endereço de `User` são NOT NULL, e o app assume que todo usuário logado tem `Customer` ou `Hairdresser`. Um usuário parcial quebraria essas duas premissas. Centralizar a emissão evita um segundo formato de sessão, já que quatro apps decodificam o JWT à mão.
- **Trade-off**: A conta só existe depois do wizard. Um cadastro abandonado não deixa rastro nem pode ser retomado depois que o token de 30 min expira. O `RegisterView` ganha um segundo caminho de entrada.
- **Scope**: `backend/users` (views de auth e helpers de token) e o fluxo de cadastro do `frontend-mobile`. Vale para qualquer provedor externo futuro (Apple, telefone/RF3).
- **Date**: 2026-09-27
- **Status**: superseded by AD-004

### AD-002
- **Decision**: Toda consulta de CEP passa por um proxy no backend (`backend/users/cep_lookup.py`, exposto em `GET /api/address/cep/<cep>`). O proxy consulta o ViaCEP primeiro e usa a BrasilAPI v2 como fallback, e devolve sempre `{postal_code, address, neighborhood, city, state}`. O app nunca chama um provedor de CEP direto. A API oficial dos Correios só entra se houver contrato comercial.
- **Reason**: ViaCEP e BrasilAPI são gratuitos e não pedem cadastro. A API Busca CEP dos Correios exige contrato comercial (serviço 86738), conta no Meu Correios, credenciais no CWS e renovação de token. O proxy concentra timeout, fallback, cache e rate limit, e é testável no Django, onde fica a única suíte automatizada do projeto.
- **Trade-off**: A consulta tem um salto a mais (app → backend → provedor), e o backend passa a depender da internet para esse recurso. O endpoint é anônimo, então depende de throttle e cache para não virar relay e não ter o IP bloqueado pelo ViaCEP.
- **Scope**: `backend/users` e qualquer tela do `frontend-mobile` que use endereço (cadastro hoje; edição de endereço no futuro).
- **Date**: 2026-09-29
- **Status**: active

### AD-003
- **Decision**: Toda imagem enviada por usuário é convertida para WebP no backend, de forma síncrona e em memória, **antes** do único upload ao S3. A conversão fica em um campo de modelo próprio (`hairmatch.images.WebPImageField`, que usa `WebPImageFieldFile.save`). Esse campo limita o maior lado a 1080 px, aplica a orientação EXIF, remove os metadados e codifica com qualidade 80. Nenhuma Lambda, fila ou reprocessamento no bucket é usado para converter mídia.
- **Reason**: A API recebe a foto em multipart (`request.FILES`), e nenhum cliente sobe direto no S3 nem usa URL pré-assinada. Então o backend tem os bytes antes do PUT. Converter ali custa 1 PUT por foto, contra 2 PUT + 1 GET no fluxo "sobe → baixa → converte → sobe" e na Lambda (que ainda cobra compute). Também mantém banco e bucket consistentes na mesma requisição, sem chave `.jpg` à espera de um `.webp` assíncrono. Ter um campo como ponto único cobre views, seed e qualquer caminho futuro que salve pelo modelo, e funciona com o `InMemoryStorage` dos testes. Nos placeholders do seed, o limite de 1080 px reduz 134 MB para 2 MB (−98,5%), contra −50% sem o limite.
- **Trade-off**: A requisição de upload paga a CPU da conversão. Um arquivo que não é imagem agora falha com 400, onde antes subia sem erro. As views precisam tratar `InvalidImage` (subclasse de `ValueError`) antes dos handlers genéricos. Os objetos antigos (`.jpg`/`.png`) continuam como estão.
- **Scope**: Todo `ImageField` que recebe upload de usuário (`User.profile_picture` e `Review.picture` hoje) e o seed `populate_hairdressers`. Um novo campo de imagem com upload deve usar `WebPImageField`.
- **Date**: 2026-09-29
- **Status**: active

### AD-004
- **Decision**: Contas de e-mail/senha autenticam no AWS Cognito, via proxy no backend (boto3, `backend/users/cognito.py`). A sessão delas é o AccessToken do Cognito no cookie `jwt`, e o RefreshToken fica no cookie `refresh_token` (`path=/api/auth/`). Contas Google mantêm a sessão emitida pelo backend, agora com payload `{id, iss: "hairmatch", token_use: "session", iat, exp}` e HS256 com `settings.SECRET_KEY`. Todo endpoint protegido autentica só por `backend/users/authentication.py` (`authenticated_user`), que fixa o algoritmo por emissor (RS256 + JWKS para o Cognito, HS256 para `hairmatch`) e responde 401 `{"error"}` para sessão ausente, inválida ou expirada. Toda escrita de cookie de sessão continua em `backend/users/auth_tokens.py`. Continua valendo o que o AD-001 decidiu sobre provedor externo: não se cria usuário parcial, e o cadastro Google termina pelo `POST /api/auth/register` com o `signup_token`.
- **Reason**: A issue #139 tira do Hairmatch a guarda de senhas e a assinatura de sessão das contas locais. O Google fica como está por decisão do usuário. Um autenticador único elimina os 13 decodes manuais com a chave `'secret'` e dá ao app um sinal único (401) para o refresh.
- **Trade-off**: Passam a existir dois formatos de sessão, em vez do formato único do AD-001. Um access token revogado segue aceito até expirar (≤ 60 min), porque a verificação é local. Contas Google não têm refresh.
- **Scope**: `backend/users`, `backend/availability`, `backend/review`, `backend/preferences` e o contexto de auth e o `axiosInstance` do `frontend-mobile`. Todo endpoint novo que exija login usa `authenticated_user`, e nenhuma view decodifica JWT.
- **Date**: 2026-09-29
- **Status**: active, exceto o corpo `{"error"}` do 401 e do 503, superado pelo AD-006

### AD-005
- **Decision**: Em dev, o Cognito roda no MiniStack (`ministackorg/ministack`, serviço `ministack` do compose, porta 4567 no host, `PERSIST_STATE=1`). S3, SES e o resto da nuvem local continuam no LocalStack. O backend alcança o MiniStack por `AWS_ENDPOINT_URL_COGNITO_IDENTITY_PROVIDER=http://ministack:4566`, definido no compose. Os IDs do pool e do client vêm de `COGNITO_USER_POOL_ID` e `COGNITO_APP_CLIENT_ID`; vazios em dev, o backend busca `hairmatch-dev` e `hairmatch-backend` pelo nome.
- **Reason**: O container do LocalStack ativa uma licença `freemium`, e o `cognito-idp` só existe nos planos Base/Ultimate/Student. O MiniStack é MIT, não pede token, emite tokens RS256 com o `iss` igual ao da AWS e serve o JWKS por pool.
- **Trade-off**: São dois emuladores no compose. O MiniStack não aceita ID fixo de pool, então o estado depende do volume `ministack_state`, e o seed repara os usuários se o volume for apagado. O código de confirmação local é fixo (`123456`). Fatos conferidos no código do MiniStack 1.5.18 em 2026-10-04:
  - o e-mail de verificação vai para o SES embutido do próprio MiniStack (`GET http://localhost:4567/_ministack/ses/messages`), e não para o SES do LocalStack;
  - o `ConfirmSignUp` aceita qualquer código;
  - o `InitiateAuth` não recusa usuário `UNCONFIRMED`.

  Por isso o bloqueio de conta pendente também fica no Postgres (AD-008).
- **Scope**: `docker/docker-compose.yml`, `docker/ministack/init/` e o README. Vale até o projeto ter um plano do LocalStack que inclua o Cognito. Nesse dia, basta trocar o endpoint e o script de init.
- **Date**: 2026-09-29
- **Status**: active

### AD-006
- **Decision**: Todo erro sob `/api/` sai em `application/problem+json` (RFC 9457), com `type`, `title`, `status`, `detail` e `instance`, e a extensão `errors` (itens `{pointer}` ou `{parameter}`) só em `validation-error`. O `type` é `https://hairmatch.app/problems/<slug>`, com a base em `settings.PROBLEM_TYPE_BASE_URI`, e o slug vem do catálogo de 36 linhas do spec `api-problem-details`. Tudo passa por `backend/hairmatch/problems.py`: a view devolve `problem_response(request, slug, detail)`, um helper levanta `Problem`, e `exception_handler` (DRF) responde por qualquer exceção, inclusive as inesperadas (500 `internal-error`, logadas com traceback), sem nunca devolver `None`. Uma view no fim do `urlpatterns` responde 404 para `/api/` sem rota, e `ProblemDetailsMiddleware` (`process_exception`, só sob `/api/`) cobre a exceção que escapa do `try` do DRF, como a de `finalize_response` e a de renderização. Os helpers de sessão de `users/authentication.py` mantêm a tupla `(session, error)`, agora com problem+json (401 `invalid-session`, 503 `auth-unavailable`, 403 `hairdresser-required`, `customer-required` e `forbidden`). `detail` e `title` são sempre em inglês e nunca levam texto de exceção. O app traduz pelo slug do `type` (`frontend-mobile/utils/api-problem.ts`) e nunca mostra o `detail`. Um slug novo exige atualizar o catálogo do spec, `CATALOG` e o catálogo do app.
- **Reason**: Cinco formatos de erro conviviam (`{"error"}`, `{"detail"}`, `{"status","message"}`, `str(e)` e HTML de 500 com `DEBUG=True`). Um contrato só deixa o app tratar erro em um ponto. O corpo do 401 mudou de `{"error"}` para problem+json, e o AD-004 fixava o formato antigo. Um handler que devolve `None` faria o DRF relançar a exceção, e o Django serviria HTML com `DEBUG=True` (fixo em `settings.py`), por isso o handler responde por tudo. `handler404` também é ignorado com `DEBUG=True`, por isso a rota catch-all.
- **Trade-off**: A resposta de erro é `JsonResponse`, e não `Response` do DRF: não passa pelos renderers, então o Browsable API nunca devolve HTML de erro, mas os erros também não usam content negotiation. Backend e app mudam no mesmo release, sem período com `{"error"}`. O app depende do slug: um slug fora do catálogo cai no texto genérico da tela.
- **Scope**: Todo o `backend` sob `/api/` (users, reserve, agenda, availability, service, review, preferences, chatbot, `hairmatch/ai_clients`) e o `frontend-mobile`. Fora: as mensagens do chatbot de WhatsApp (pt-BR) e `admin/`. Toda view nova devolve erro por `problem_response` ou `Problem`, e nenhuma monta `JsonResponse({'error': ...})`.
- **Date**: 2026-09-30
- **Status**: active

### AD-007
- **Decision**: As rotas de `/api/` seguem a Route Table do spec `api-restful-routes`: recurso no plural, sem verbo no path, filho sob o pai (`/hairdressers/{id}/services`), filtro na query, `me` para o usuário da sessão e o método HTTP como verbo (`PUT` substitui, `PATCH` atualiza parte, `DELETE` remove). Cada app monta o seu `urls.py` em `api/`, e um path com vários métodos é uma classe que herda das views (`class ServiceDetail(ListService, UpdateService, RemoveService)`), então o `Allow` do 405 sai do DRF. `hairmatch/test_routes.py` compara os `urlpatterns` resolvidos com a tabela e falha se uma rota entra ou sai sem o spec. Rota antiga responde 404 e não há alias nem `/v1`. O app compara as exclusões do refresh por método e pathname exatos (`frontend-mobile/services/auth-routes.ts`). Muda os caminhos citados no AD-002 (`/api/postal-codes/{cep}`) e no AD-004 (`POST /api/users` cadastra; `POST /api/auth/register` deixou de existir); as decisões em si seguem valendo.
- **Reason**: A issue #163 pede rotas avaliadas contra a RFC 3986. A RFC não obriga a trocar nenhuma rota atual, porque todas são URIs válidas; o redesenho segue a hierarquia do path (§3.3), o dado não hierárquico na query (§3.4) e o percent-encoding (§2.1, o que tira o e-mail do path), mais a convenção REST e a RFC 9110 para os métodos.
- **Trade-off**: Corte único: o app antigo quebra contra o backend novo, então os dois saem no mesmo release. A URL do webhook do chatbot mora na Evolution API, fora do repositório, e precisa ser reconfigurada com autorização antes do deploy em produção. `reverse()` acompanha a rota nova, então só `test_routes.py` prova o path.
- **Scope**: Todo o `backend` sob `/api/` e o `frontend-mobile`. Fora: `admin/`. Rota nova entra na Route Table do spec antes de entrar no código.
- **Date**: 2026-09-30
- **Status**: active

### AD-008
- **Decision**: Toda conta de e-mail/senha criada por `POST /api/users` nasce pendente: `UNCONFIRMED` no Cognito (só `SignUp`, sem `AdminConfirmSignUp`) e `User.is_active=False` no Postgres. Ela só passa a ativa por `ConfirmSignUp` com o código de 6 dígitos que o Cognito envia (`POST /api/auth/email-confirmations`). O reenvio é `POST /api/auth/confirmation-codes`.

  Enquanto está pendente, a conta:
  - não loga (403 `email-not-confirmed`);
  - não vira sessão (o autenticador filtra `is_active=True`);
  - não aparece em listagem;
  - é substituída por um novo cadastro com o mesmo e-mail ou telefone;
  - é expurgada por `purge_unconfirmed_users` depois de 7 dias.

  Rota anônima que dispara e-mail ou valida código leva throttle por IP e por e-mail alvo (SHA-256 do e-mail normalizado), com as contagens em `DatabaseCache` (`hairmatch_cache`, tabela criada por migração). O login e o cadastro Google nunca vinculam o `google_id` a uma conta pendente: substituem a conta. O e-mail sai sempre pelo Cognito: o backend não chama o SES, e em produção o pool usa `EmailConfiguration` `DEVELOPER` com uma identidade SES verificada. As únicas contas criadas já ativas são as do seed (`sign_up_confirmed`) e as do Google.
- **Reason**: A issue #141 exige que o cadastro só valha depois da confirmação do e-mail. O usuário pediu Cognito + SES e defesa contra cadastro em massa de bots. O espelho em `is_active` reaproveita o filtro do autenticador sem migração e cobre o MiniStack, que não recusa `UNCONFIRMED` (AD-005). A substituição e o expurgo impedem que uma conta não confirmada ocupe o e-mail ou o telefone de outra pessoa. O cache em banco divide as contagens entre processos e sobrevive a deploy.
- **Trade-off**:
  - Diverge do texto da issue (código digitado em vez de link), por decisão do usuário.
  - Uma conta pendente legítima é apagada se outra pessoa se cadastrar com o mesmo e-mail ou telefone.
  - Cada requisição throttled grava no Postgres.
  - Em dev, qualquer código confirma (limite do MiniStack), então os erros de código só são testados no fake.
  - CAPTCHA e proteção paga ficam de fora.
- **Scope**: `backend/users` (cadastro, login, confirmação, reenvio, listagens, expurgo, throttles), `backend/hairmatch/settings.py` (`CACHES`), `backend/entrypoint.sh`, `docker/ministack/init/` e o fluxo de auth do `frontend-mobile`. Supera a assumption de auto-confirmação da feature `cognito-auth` (COG-05). COG-38 a COG-40 (seed) continuam valendo. Toda rota anônima nova que envie e-mail ou valide segredo segue o mesmo par de throttles.
- **Date**: 2026-10-04
- **Status**: active

### AD-010
> O número AD-009 está reservado para a feature `external-appointment` (#113), que o registra na T12 dela.
- **Decision**: `User.rating` é um valor **derivado**: a média aritmética das avaliações que o usuário recebeu, arredondada para 2 casas, ou `null` enquanto ele não recebeu nenhuma.
  - O campo é `FloatField(null=True, default=5)`.
  - A média é recalculada só no ponto de escrita da avaliação, na mesma transação do insert, com a linha `User` do avaliado travada por `select_for_update`.
  - Nenhum endpoint de edição de perfil grava `rating`.
  - Para o cliente, as avaliações são `CustomerRating` (feature `customer-rating`, #104), e o cliente nasce com `null`. O cabeleireiro mantém o default 5 até a feature que recalcular a nota dele a partir das `Review`, que deve seguir o mesmo padrão.
- **Reason**: O inteiro truncava a média, e um `Decimal` sai como string no `JsonResponse` e no DRF, o que quebra o `toFixed` do app. Sem o lock, duas avaliações simultâneas do mesmo usuário fazem a última escrita descartar uma nota. O 5 fixo dos clientes era fictício: nenhuma avaliação existia.
- **Trade-off**:
  - Avaliações do mesmo usuário são serializadas pelo lock.
  - A média gravada pode divergir das linhas se alguém escrever avaliações fora de `record_customer_rating` (seed, admin).
  - Cliente e cabeleireiro dividem um campo com semânticas diferentes até a nota do cabeleireiro também ser derivada.
- **Scope**: `backend/users` (modelo e cadastro), `backend/review` e toda tela do `frontend-mobile` que mostra a nota de cliente. Toda avaliação nova que afete `User.rating` passa por uma função de domínio com o mesmo padrão.
- **Date**: 2026-10-09
- **Status**: active

## Handoff

- **Feature**: `customer-rating` (issue #104, RF23).
- **Phase / Task**: Execute de T1 a T17 concluído. T18 (UAT manual no web e no Android) está aberto de propósito: é do usuário. O Verificador independente (`validation.md`) ainda não rodou.
- **Completed**:
  - Backend (T1 a T7): `User.rating` em `FloatField`, com `null` para cliente sem avaliação; modelo `CustomerRating`; `record_customer_rating` com lock e savepoint (AD-010); slug `service-not-finished`; RT-86 `POST /api/customer-ratings`; RT-87 `GET /api/customers/{id}/ratings`; agenda com `reservation_id`, `customer.user.rating`, `customer.ratings_count` e `customer_rating`. Suíte: 777 testes OK, `makemigrations --check` limpo.
  - App (T8 a T16): types, service e `formatCustomerRating`; slug no `api-problem.ts`; `StarRating` compartilhado; `useAgenda` com `useFocusEffect` e `canRate`; modal da agenda com o cliente, a nota, "Sua avaliação: N★" e "Avaliar cliente"; tela `hairdresser/rate-customer/[reservationId]`; média no perfil do cliente; tela "Avaliações recebidas". `npx tsc --noEmit` com exit 0, e nenhum erro novo de `eslint` nos arquivos tocados.
- **Desvios registrados**:
  - Design: a tela de avaliação vai para a agenda com `router.push` em vez de `router.back()` (`useRateCustomer.ts`, `SPEC_DEVIATION`). O voltar das abas pode cair em outra aba, e um refresh do web não tem histórico.
  - O CRT-56 dá o exemplo "4.3 (3 avaliações)", mas o design e o T18 usam "4.0 (1)". O modal mostra "Nota do cliente: 4.3 (3)" com a função compartilhada.
  - `docs/requisitos-status.md` não está versionado e não existe no worktree. A marcação de RF23 como ✅ e as observações de RF29/RF30 ficam para o usuário fazer no checkout principal, ou para autorizar o versionamento do arquivo.
- **In-progress** (file:line): none
- **Next step**:
  - UAT do T18 (roteiro no `tasks.md`), no web e no Android. Depois, marcar CRT-39 a CRT-52 e CRT-56 a CRT-60 como Verified.
  - Rodar o Verificador da feature e gravar `validation.md`.
  - Atualizar RF23 em `docs/requisitos-status.md` (ver desvios).
- **Pendências de features anteriores**:
  - `email-confirmation` (#141): UAT do T23 e a configuração de produção do SES (README).
  - `api-restful-routes` (#163): UAT manual (RT-70 a RT-75). A reconfiguração do webhook da Evolution API só acontece com autorização explícita.
  - `cognito-auth` (#139): sem `validation.md`.
- **Blockers**: none
- **Uncommitted files**: `frontend-mobile/eslint.config.js` é do usuário e fica fora dos commits. No checkout principal continuam pendentes, fora deste PR, `frontend-mobile/.env.example`, `frontend-mobile/services/axios-instance.ts`, `.specs/LESSONS.md`, `.specs/lessons.json` e `docs/`.
- **Branch**: 104-dar-nota-para-o-cliente
