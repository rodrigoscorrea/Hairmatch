# STATE

## Decisions

### AD-001
- **Decision**: Login e cadastro por provedor de identidade externo (Google hoje) não criam usuário parcial. Para uma conta nova, o backend devolve um token de cadastro pendente e assinado (sem estado no servidor), e a conclusão passa pelo `POST /api/auth/register` existente. Toda emissão de sessão (cookie `jwt`, payload `{id, exp, iat}`) passa por `backend/users/auth_tokens.py`.
- **Reason**: As colunas de telefone e endereço de `User` são NOT NULL, e o app assume que todo usuário logado tem `Customer` ou `Hairdresser`. Um usuário parcial quebraria essas duas premissas. Centralizar a emissão evita um segundo formato de sessão, já que quatro apps decodificam o JWT à mão.
- **Trade-off**: A conta só existe depois do wizard. Um cadastro abandonado não deixa rastro nem pode ser retomado depois que o token de 30 min expira. O `RegisterView` ganha um segundo caminho de entrada.
- **Scope**: `backend/users` (views de auth e helpers de token) e o fluxo de cadastro do `frontend-mobile`. Vale para qualquer provedor externo futuro (Apple, telefone/RF3).
- **Date**: 2026-09-27
- **Status**: active

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

## Handoff

- **Feature**: webp-conversion (`.specs/features/webp-conversion/`), issue #138
- **Phase / Task**: Tasks concluído. Aguardando aprovação do usuário para Execute (Phase 1 / T1).
- **Completed**: spec.md, design.md e tasks.md escritos e validados (`validate_spec.py` com exit 0; `validate_tasks.py` com exit 0 e 1 aviso esperado: T9 com `Tests: none`, porque é um roteiro manual sem código). Não houve `context.md`: as decisões (backend em vez de Lambda, redimensionamento para 1080 px) estão na tabela de Assumptions do spec e no AD-003. A cep-autocomplete (#128) tem `validation.md` e branch própria.
- **In-progress** (file:line): none
- **Next step**: Criar a branch `138-conversao-de-foto-para-webp` a partir de `develop`, confirmar o Test Coverage Matrix e os Gate Commands e executar T1–T9. São 9 tarefas, então há 2 lotes e é preciso oferecer sub-agentes antes de começar.
- **Blockers**: none. Os testes precisam de Postgres. O T9 precisa do `docker compose up` com LocalStack.
- **Uncommitted files**: `.specs/features/webp-conversion/` (novo), `.specs/STATE.md`
- **Branch**: develop
