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
- **Trade-off**: São dois emuladores no compose. O MiniStack não aceita ID fixo de pool, então o estado depende do volume `ministack_state`, e o seed repara os usuários se o volume for apagado. O código de confirmação local é fixo (`123456`).
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

## Handoff

- **Feature**: `api-problem-details` (issue #161, parte RFC 9457, mensagens em inglês e status corretos). A parte de rotas da issue é a feature `api-restful-routes`, que depende desta.
- **Phase / Task**: Execute concluído (T1 a T18) e validado. `validation.md` com PASS nos gates automatizados. Falta o UAT das cinco telas do app.
- **Completed**:
  - Backend: `hairmatch/problems.py`, handler do DRF, rota catch-all, middleware para a exceção que escapa do DRF, e todas as views de users, reserve, agenda, availability, service, review, preferences e chatbot em problem+json. 590 testes, nenhum removido ou pulado (463 antes).
  - App: `utils/api-problem.ts` (normalizador e catálogo pt-BR), `_layout.tsx`, as cinco telas, `useServiceManager` e `useCepLookup` por slug. `npx tsc --noEmit` com exit 0 (os 4 erros antigos foram corrigidos só nos tipos).
  - Sensor: 30 de 30 mutantes mortos. Servidor real (`DEBUG=True`) verificado por `curl`.
  - AD-006 registrado.
- **In-progress** (file:line): none
- **Next step**:
  - UAT no app: login com senha errada (`E-mail ou senha inválidos.`), reserva em conflito (`Você já tem outra reserva agendada para o mesmo horário.`), exclusão de serviço com agendamento, CEP inexistente, e login/cadastro por Google. Depois disso, marcar PD-80 a PD-87 e PD-101 como Verified.
  - Feature `api-restful-routes`: o Design dela parte do problem+json daqui. Os specs dela ainda não estão commitados.
- **Blockers**: none. A troca do webhook do chatbot (RT-49, feature de rotas) exige autorização explícita antes do deploy em produção.
- **Uncommitted files**: `.specs/features/api-restful-routes/` (specs da issue #162, de propósito fora deste PR). Já estavam pendentes antes: `frontend-mobile/.env.example`, `.specs/LESSONS.md`, `.specs/lessons.json` e `docs/`.
- **Branch**: 161-padronizacao-das-respostas-de-apis-para-rfcs-adequadas
