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
- **Status**: active

### AD-005
- **Decision**: Em dev, o Cognito roda no MiniStack (`ministackorg/ministack`, serviço `ministack` do compose, porta 4567 no host, `PERSIST_STATE=1`). S3, SES e o resto da nuvem local continuam no LocalStack. O backend alcança o MiniStack por `AWS_ENDPOINT_URL_COGNITO_IDENTITY_PROVIDER=http://ministack:4566`, definido no compose. Os IDs do pool e do client vêm de `COGNITO_USER_POOL_ID` e `COGNITO_APP_CLIENT_ID`; vazios em dev, o backend busca `hairmatch-dev` e `hairmatch-backend` pelo nome.
- **Reason**: O container do LocalStack ativa uma licença `freemium`, e o `cognito-idp` só existe nos planos Base/Ultimate/Student. O MiniStack é MIT, não pede token, emite tokens RS256 com o `iss` igual ao da AWS e serve o JWKS por pool.
- **Trade-off**: São dois emuladores no compose. O MiniStack não aceita ID fixo de pool, então o estado depende do volume `ministack_state`, e o seed repara os usuários se o volume for apagado. O código de confirmação local é fixo (`123456`).
- **Scope**: `docker/docker-compose.yml`, `docker/ministack/init/` e o README. Vale até o projeto ter um plano do LocalStack que inclua o Cognito. Nesse dia, basta trocar o endpoint e o script de init.
- **Date**: 2026-09-29
- **Status**: active

## Handoff

- **Feature**: cognito-auth (`.specs/features/cognito-auth/`), issue #139
- **Phase / Task**: Tasks concluído. Aguardando aprovação do usuário para Execute (Phase 1 / T1).
- **Completed**: `spec.md` (49 requisitos COG-01 a COG-49), `context.md`, `design.md` e `tasks.md` (24 tarefas em 5 fases).
  - `validate_spec.py`: exit 0, sem avisos.
  - `validate_tasks.py`: exit 0, com 8 avisos esperados (`Tests: none` nas camadas model, infra e app, conforme a matriz).
  - AD-004 (supera o AD-001) e AD-005 registrados.
  - Decisões do usuário: MiniStack para o Cognito, proxy no backend, sessão própria só para Google, descartar e re-seedar as contas bcrypt.
- **In-progress** (file:line): none
- **Next step**: Confirmar o Test Coverage Matrix e os Gate Commands. Oferecer sub-agentes (cerca de 4 lotes) e executar T1–T24 na branch `139-troca-autenticacao-para-aws-cognito`. O reset do banco do Render é passo operacional e exige autorização explícita.
- **Blockers**: none. Os testes precisam de Postgres. O T24 precisa do `docker compose up` com LocalStack (token atual) e MiniStack.
- **Uncommitted files**: `.specs/features/cognito-auth/` (novo), `.specs/STATE.md`. Já estavam pendentes antes desta feature: `frontend-mobile/.env.example`, `.specs/LESSONS.md`, `.specs/lessons.json` e `docs/`.
- **Branch**: 139-troca-autenticacao-para-aws-cognito
