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
- **Scope**: Todo `ImageField` que recebe upload de usuário (`User.profile_picture` e `ReviewPicture.picture` hoje; a `Review.picture` saiu no AD-011) e o seed `populate_hairdressers`. Um novo campo de imagem com upload deve usar `WebPImageField`.
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

### AD-009
- **Decision**: Uma linha de `Agenda` com `service` nulo é um bloqueio externo: um atendimento feito fora do app, identificado pelo `title` (de 1 a 100 caracteres depois de `strip()`). O pareamento Agenda↔Reserve por `(service_id, start_time)` nunca considera essa linha: `ListAgenda` tira os itens sem serviço do `reserve_map`, e `AgendaSerializer.get_customer` devolve `None` cedo. Na listagem, `customer === null` identifica toda entrada que não é reserva do app, e o app mostra o rótulo "Externo". Toda nova escrita na `Agenda` sem reserva usa este formato, sem um campo `kind`.
- **Reason**: A issue #113 pede para bloquear na agenda um atendimento externo, com ou sem serviço cadastrado. O cálculo de horários livres (app e chatbot) e a checagem de sobreposição da reserva já leem só `start_time` e `end_time` da `Agenda`, então um bloqueio sem serviço sai da oferta sem mudar esse código. `service` nulo mais `title` é a menor mudança de modelo, com uma migração aditiva (`0002_agenda_title_alter_agenda_service`).
- **Trade-off**:
  - Um bloqueio com serviço continua pareando com uma `Reserve` de mesmo serviço e início. A checagem de sobreposição impede duas linhas no mesmo início para o mesmo cabeleireiro.
  - Um segundo tipo de bloqueio (folga, férias) exigiria um campo `kind` e uma migração.
  - A corrida entre `CreateAgenda` e `CreateReserve` continua sem lock, nos dois caminhos.
- **Scope**: `backend/agenda` (modelo, migração `0002`, `CreateAgenda`, `ListAgenda`, `AgendaSerializer`) e a agenda do cabeleireiro no `frontend-mobile` (`useAgenda`, `agenda/index.tsx`, `agenda/create.tsx`, `useExternalAppointmentForm`). `reserve/views.py` não muda.
- **Date**: 2026-10-09
- **Status**: active

### AD-010
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
- **Status**: active, estendido pelo AD-012

### AD-011
- **Decision**: As fotos de uma avaliação são linhas de `ReviewPicture` (FK `CASCADE` para `Review`, um `WebPImageField` por linha), como o AD-013 prescreve para coleções de imagens.
  - A chave no bucket é `reviews/<review_id>/<uuid4 hex>.webp`.
  - Uma avaliação tem de 0 a 5 fotos, de até 5 MB cada. Tamanho e quantidade são checados antes de abrir qualquer imagem (`review/pictures.py`), e o limite é contado com a linha da `Review` travada (`select_for_update`).
  - A criação usa o campo multipart `pictures`, repetido, e as fotos entram depois pelo sub-recurso `POST /api/reviews/{id}/pictures` (RT-90) e saem por `DELETE /api/reviews/{id}/pictures/{picture_id}` (RT-91). O `PUT /api/reviews/{id}` continua em JSON e não mexe nas fotos.
  - O upload acontece durante o `create`, dentro da transação. Uma requisição que falha apaga na hora os objetos que já enviou, e o apagamento de foto, de avaliação e de conta roda em `on_commit` por `hairmatch.storage.delete_stored_files`.
- **Reason**: O pedido foi de várias fotos em `reviews/<id_da_review>/`. A tabela mantém o AD-003 (conversão, upload e URL no campo) e permite adicionar e remover uma foto sem reescrever um array nem perder escrita concorrente. O sub-recurso mantém o que o commit 527a69a decidiu: só `request.FILES` vira arquivo, nunca uma chave vinda de JSON. O `on_commit` nunca dispara quando a transação é desfeita, por isso a limpeza da requisição que falha é imediata.
- **Trade-off**:
  - Uma listagem de avaliações custa uma query a mais (`prefetch_related('pictures')`).
  - A edição pelo app são três chamadas (PUT, DELETEs, POST) e não é atômica; a tela refaz o estado a partir do servidor quando um passo falha.
  - Uma falha ao apagar o objeto do S3 só vai para o log, e o objeto fica órfão.
  - O limite cheio aqui é 400 `validation-error` em `#/pictures`, e na galeria é 409 `gallery-full`, porque uma requisição leva até 5 arquivos.
  - Não há migração de dados: não havia fotos de avaliação em nenhum ambiente.
- **Scope**: `backend/review` (modelo, `pictures.py`, views, serializers), `backend/reserve` (prefetch), `backend/users` (`_delete_account_rows`), `hairmatch/storage.py` e a tela de avaliação do `frontend-mobile`. Toda foto nova de avaliação passa por `add_review_pictures`.
- **Date**: 2026-10-10
- **Status**: active

### AD-012
- **Decision**: A média do AD-010 (`User.rating` do cliente) também é recalculada quando a nota é editada ou excluída: `update_customer_rating` e `delete_customer_rating`, em `backend/review/customer_ratings.py`, travam a linha `User` do cliente (`select_for_update`) e chamam o mesmo `_store_average` do `record_customer_rating`. Sem notas restantes, a média vira `null`. Só o cabeleireiro autor edita ou exclui (`PUT` e `DELETE /api/customer-ratings/{id}`, RT-92 e RT-93), e uma nota cujo autor apagou a conta não é editável por ninguém. Excluir libera a reserva para uma nova nota.
- **Reason**: A #105 pede editar e excluir a nota do cabeleireiro, o que desfaz a imutabilidade da #104. Qualquer escrita em `CustomerRating` que não recalcule a média deixaria `User.rating` divergente. Reusar o lock do AD-010 serializa as escritas do mesmo cliente, e reusar `_store_average` mantém um só cálculo.
- **Trade-off**:
  - Edições e exclusões do mesmo cliente passam a esperar umas pelas outras.
  - O app deixa de avisar que a nota "não pode ser alterada".
  - A média continua podendo divergir das linhas se alguém escrever fora dessas funções (seed, admin).
- **Scope**: `backend/review` (`customer_ratings.py`, `CustomerRatingDetail`), `backend/agenda` (o `customer_rating` traz o `id`) e a agenda e a tela de nota do cliente no `frontend-mobile`. Toda escrita futura em `CustomerRating` passa por essas funções.
- **Date**: 2026-10-10
- **Status**: active

### AD-013
> Os números AD-011 e AD-012, e as rotas RT-90 a RT-93, estão reservados para a feature `review-editing` (#105), cuja spec está em andamento.
- **Decision**: Uma coleção de imagens de um dono é uma tabela filha, com FK para o dono e um `WebPImageField` por linha, e nunca um array de chaves em `JSONField`. A primeira é `GalleryPhoto` (feature `hairdresser-gallery`, #118):
  - a FK é para `Hairdresser`, com `CASCADE`;
  - a chave é `hairdresser/gallery/<hairdresser_id>/<uuid4 hex>.webp`;
  - o limite é de 30 fotos por cabeleireiro.

  O limite por dono é garantido numa transação, com `select_for_update` na linha do dono antes de contar e inserir, como no AD-010. Os arquivos saem do bucket em `transaction.on_commit`: na remoção da linha e na exclusão da conta (`_delete_account_rows`), porque o `CASCADE` não apaga arquivo.
- **Reason**:
  - O `WebPImageField` é um campo de modelo. Um array JSONB obrigaria a chamar `to_webp` e o storage à mão, fora do ponto único do AD-003.
  - Com vários uploads em paralelo, o insert por linha não perde escrita, e o array reescrito perderia.
  - A remoção é por PK, e a posse é um filtro de FK.
  - Na escala de dezenas de imagens, ler uma tabela indexada custa o mesmo que ler o JSONB, e a coleção não pesa nas listagens do dono.
- **Trade-off**:
  - Os uploads do mesmo dono ficam serializados pelo lock, que dura a conversão e o upload de uma foto.
  - Toda nova coleção de mídia precisa de uma migração.
  - O apagamento do arquivo depois do commit é best-effort: a falha só fica no log (`_delete_stored_files`).
- **Scope**: `backend/users` (modelo, views da galeria, exclusão de conta e seed). Vale para qualquer coleção de mídia futura (fotos de serviço, por exemplo).
- **Date**: 2026-10-10
- **Status**: active

## Handoff

- **Feature**: `review-editing` (issue #105, RF29 e RF30), branch `105-editar-e-excluir-avaliacao`.
- **Phase / Task**: Execute concluído em 2026-10-10 (T1 a T24, mais o substituto automatizado da T25). A suíte do backend passa, `makemigrations --check` fica limpo e `npx tsc --noEmit` não tem erro. O UAT manual no web e no Android (T25) está **PENDENTE**.
- **Completed**:
  - Backend: `ReviewPicture`, `review/pictures.py`, RT-90 a RT-93, média do cliente recalculada na edição e na exclusão (AD-011 e AD-012), `customer_rating.id` na agenda.
  - App: tela de avaliação com várias fotos e modo edição, detalhe da reserva com as fotos, agenda e tela de nota do cabeleireiro com editar e excluir.
  - Verificação ponta a ponta por API (curl, servidor do worktree, bucket próprio), registrada em `validation.md`.
- **In-progress** (file:line): none
- **Next step**:
  1. Fazer o UAT manual da T25 (web e Android) e marcar REV-60 a REV-81 como Verified.
  2. Antes do deploy: conferir o limite de corpo do proxy de produção. Uma criação pode levar 5 fotos de até 5 MB, cerca de 25 MB numa requisição.
  3. Decidir a canonicidade entre o AD-011 e o AD-013 (as duas decisões tratam de coleções de imagens, em branches diferentes) e tirar do AD-013 a nota que reserva os números AD-011, AD-012 e RT-90 a RT-93.
- **Blockers**:
  - A T1 renomeou `_delete_stored_files` para `hairmatch.storage.delete_stored_files`. A branch da `hairdresser-gallery` (#118) ainda usa o nome antigo: quem entrar depois troca a referência.
  - Os dois PRs editam `test_routes.py` e a Route Table do `api-restful-routes`: o segundo a entrar resolve o conflito.
- **Uncommitted files**: `.specs/LESSONS.md` e `.specs/lessons.json` (estado local do skill, fora dos commits).
- **Branch**: `105-editar-e-excluir-avaliacao`
