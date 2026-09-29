# Conversão de Fotos para WebP Specification

**Issue:** [#138](https://github.com/rodrigoscorrea/Hairmatch/issues/138)
**Escopo:** Large (persistência em S3, falha parcial no cadastro, seed, migrations)
**Plataformas:** só backend. O app já usa as URLs absolutas devolvidas pela API (`e3cff5d`), e Android e iOS 14+ exibem WebP nativamente.

## Problem Statement

Desde a #135, as fotos enviadas pelos usuários ficam no bucket S3 de mídia no formato original (JPEG, PNG, etc.). Esses arquivos ocupam mais armazenamento e mais tráfego de saída do S3 do que o necessário.

A issue #138 pede que toda foto enviada, e também as do seed de desenvolvimento, seja guardada como `.webp`, no mesmo caminho do bucket ligado ao usuário. A conversão deve ser feita pelo backend, e não por Lambda.

## Goals

- [ ] Toda foto salva por `User.profile_picture` e `Review.picture` fica no bucket só como `.webp`, e o formato original nunca é enviado ao S3.
- [ ] Cada foto gera exatamente um upload para o S3, sem GET, sem segundo PUT e sem Lambda.
- [ ] Nenhuma foto guardada tem o maior lado acima de 1080 px.
- [ ] Um arquivo que não é imagem gera 400 e nunca deixa um usuário ou uma review pela metade no banco.

## Decisão de arquitetura: converter no backend antes do único PUT

A API recebe a foto em multipart (`request.FILES`), e nenhum cliente sobe direto no S3 nem usa URL pré-assinada. O único acesso ao S3 é o `upload_fileobj` em `S3MediaStorage._save`. Como o backend já tem os bytes em memória, a conversão acontece **antes** desse upload. O fluxo descrito na issue ("sobe → baixa → converte → sobe") não é necessário.

| Abordagem | Chamadas S3 por foto | Compute | Custo por 1.000 fotos (requests + compute) |
| --------- | -------------------- | ------- | ------------------------------------------ |
| **Converter no backend antes do PUT (escolhida)** | 1 PUT | CPU do Django | ~US$ 0,005 |
| Fluxo literal da issue (PUT → GET → PUT → DELETE) | 2 PUT + 1 GET | CPU do Django | ~US$ 0,0104 |
| Lambda disparada por evento do S3 | 2 PUT + 1 GET | Lambda (512 MB × ~0,5 s) | ~US$ 0,015 |

Os preços são de referência (S3 Standard e Lambda em us-east) e devem ser confirmados na página de preços da AWS. A Lambda também tornaria a conversão assíncrona: o banco guardaria a chave original enquanto o `.webp` só apareceria depois. Ver AD-003 em `.specs/STATE.md`.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Converter objetos que já estão no bucket ou no banco (chaves `.jpg`/`.png` antigas) | Não foi pedido. Fica para um management command separado, se for preciso. |
| `Preferences.picture` | Nunca recebe upload: `CreatePreferences` lê JSON e grava uma string (`preferences/views.py:19`). Uma string atribuída ao campo nunca passa por `FieldFile.save`. |
| Gerar várias resoluções (thumbnails, srcset) | Uma versão de até 1080 px (WEBP-09) atende todas as telas atuais do app. |
| Limite de tamanho do upload | O comportamento de hoje continua igual. Só a proteção contra decompression bomb entra (WEBP-13). |
| Lambda, fila ou conversão assíncrona | Decisão do usuário (issue #138 e AD-003). |
| Mudanças no app mobile | As URLs já são absolutas e o WebP é suportado pelo `Image` do React Native. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Onde converter | No backend, em memória, antes do único PUT. Nada de Lambda. | Decisão do usuário na issue e nesta conversa. É 1 PUT contra 2 PUT + 1 GET (+ compute) nas alternativas. | y |
| Em que camada | Em um `ImageFieldFile` próprio (`WebPImageFieldFile.save`), usado por `User.profile_picture` e `Review.picture` | Cobre atribuição + `model.save()` e `field.save()` do seed. Não depende do backend de storage (os testes usam `InMemoryStorage`). | n |
| Qualidade do WebP | `quality=80`, `method=4`, com perdas | É o padrão comum para fotos. Reduz bem o tamanho sem perda visível em foto de perfil. | n |
| Redimensionamento | O maior lado fica limitado a 1080 px, com `Image.thumbnail` (LANCZOS), e imagens menores nunca são ampliadas | Decisão do usuário, a partir da medição nos 40 placeholders do seed (fotos de 20 a 36 MP, 134 MB). Só converter dá 67 MB (−50%), mas 4 dos 40 arquivos ficam maiores que o JPEG e cada codificação leva ~1,07 s. Com 1080 px, o total cai para 2,06 MB (−98,5%). | y |
| Transparência | Preservada (canal alfa vira WebP RGBA) | Um PNG com fundo transparente não deve ganhar fundo preto. | n |
| Orientação EXIF | Aplicada aos pixels antes de codificar (`ImageOps.exif_transpose`) | O WebP gerado não carrega EXIF. Sem esse passo, fotos de celular ficariam giradas. | n |
| Metadados | Nenhum EXIF (inclusive GPS) é copiado para o WebP, e a remoção é explícita (`exif=b""`), sem depender do padrão da versão do Pillow. O perfil de cor ICC é preservado. | Privacidade: fotos de celular trazem localização. O ICC não é dado pessoal, e removê-lo desbota fotos Display-P3 de celular. | n |
| HEIC/HEIF (iPhone) | Tratado como imagem inválida (400). Suporte via `pillow-heif` fica como follow-up. | O Pillow não decodifica HEIC sem plugin. O app ainda não tem seletor de imagem, então o risco hoje é baixo. | n |
| Arquivo que já é WebP | Recodificado mesmo assim | Deixa o comportamento uniforme e remove metadados. O custo é baixo. | n |
| GIF ou WebP animado | Só o primeiro quadro é guardado | Foto de perfil e de review são estáticas. | n |
| Nome do arquivo | Mantém o stem original e troca a extensão por `.webp` minúsculo. Colisões ficam com o `get_available_name` do storage. | Mantém o path `profile_pics/<user_id>/` pedido na issue e o comportamento atual de colisão. | n |
| Mensagem de erro de imagem inválida | Cadastro: `"Imagem de perfil inválida."`. Review: `"Imagem inválida."`. Ambas no campo `error`. | Segue o contrato das views atuais e o português das mensagens do cadastro Google. | n |
| Status de imagem inválida | 400 | É erro do cliente. Hoje o cadastro por senha devolveria 500. | n |
| Seed com chave `.jpg` antiga (banco de dev persiste) | O restore continua subindo o JPEG original nessa chave | Não quebra ambientes de dev que já têm dados. Converter os dados antigos está fora do escopo. | n |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## User Stories

### P1: Fotos enviadas viram WebP ⭐ MVP

**User Story**: Como operador do Hairmatch, quero que toda foto enviada seja guardada como WebP, para pagar menos armazenamento e tráfego de saída do S3.

**Why P1**: É o objetivo da issue.

**Acceptance Criteria**:

1. **WEBP-01** The backend SHALL gravar todo arquivo salvo por `User.profile_picture` ou `Review.picture` como WebP (`Image.open(...).format == 'WEBP'`), com nome terminando em `.webp`.
2. **WEBP-02** WHEN um cadastro (`POST /api/auth/register`, por senha ou por Google) envia `profile_picture` com uma imagem decodificável pelo Pillow THEN o backend SHALL gravar `profile_picture.name` como `profile_pics/<user_id>/<stem original>.webp`. Exemplo: `profile.jpg` → `profile_pics/7/profile.webp`.
3. **WEBP-03** WHEN um cliente cria uma review com `picture` decodificável THEN o backend SHALL gravar `picture.name` como `reviews/images/<stem original>.webp`.
4. **WEBP-04** The backend SHALL fazer exatamente uma chamada `upload_fileobj` ao S3 por foto salva, com `ContentType: image/webp`, e SHALL nunca enviar ao S3 os bytes do arquivo original nem chamar `get_object` para converter.
5. **WEBP-05** WHEN a imagem enviada tem a tag EXIF `Orientation` diferente de 1 THEN o backend SHALL gravar os pixels já rotacionados. Exemplo: um JPEG 20×10 com `Orientation=6` vira WebP 10×20.
6. **WEBP-06** WHEN a imagem enviada tem canal alfa (modos `RGBA`, `LA` ou `P` com transparência) THEN o backend SHALL gravar um WebP em modo `RGBA`. Em qualquer outro modo (`CMYK`, `L`, `RGB`, etc.) SHALL gravar em `RGB`.
7. **WEBP-07** The backend SHALL codificar o WebP com `quality=80` e SHALL não copiar metadados EXIF da imagem original: `Image.open(webp).getexif()` fica vazio.
8. **WEBP-08** WHEN a imagem enviada é animada (GIF ou WebP com mais de 1 quadro) THEN o backend SHALL gravar um WebP estático só com o primeiro quadro (`n_frames == 1`).
9. **WEBP-09** WHEN o maior lado da imagem (já com a orientação EXIF aplicada) passa de 1080 px THEN o backend SHALL reduzi-la proporcionalmente até o maior lado ter exatamente 1080 px. Uma imagem com maior lado de até 1080 px SHALL manter as dimensões originais e nunca ser ampliada. Exemplos: 4000×6000 → 720×1080; 6000×4000 → 1080×720; 800×600 → 800×600.

**Independent Test**: Cadastrar um usuário via `curl -F profile_picture=@foto.jpg ...` gera, no LocalStack, só a chave `profile_pics/<id>/foto.webp`, servida com `Content-Type: image/webp`.

---

### P1: Upload inválido é rejeitado sem deixar lixo ⭐ MVP

**User Story**: Como usuário, quero receber um erro claro quando o arquivo enviado não é uma imagem, sem ficar com uma conta ou review quebrada.

**Why P1**: A conversão faz um arquivo inválido, que hoje sobe sem erro, levantar exceção. Sem este tratamento, o cadastro por senha deixa um usuário órfão e devolve 500.

**Acceptance Criteria**:

1. **WEBP-10** IF o `profile_picture` do cadastro por senha não é uma imagem decodificável pelo Pillow THEN o backend SHALL responder 400 com `{"error": "Imagem de perfil inválida."}` e SHALL não criar `User`, `Customer` nem `Hairdresser`.
2. **WEBP-11** IF o `profile_picture` do cadastro por Google não é uma imagem decodificável THEN o backend SHALL responder 400 com `{"error": "Imagem de perfil inválida."}`, SHALL não criar `User` e SHALL não definir o cookie `jwt`.
3. **WEBP-12** IF o `picture` de uma nova review não é uma imagem decodificável THEN o backend SHALL responder 400 com `{"error": "Imagem inválida."}`, SHALL não criar `Review` e SHALL manter `reserve.review` nulo.
4. **WEBP-13** IF a imagem ultrapassa o limite de pixels do Pillow (`Image.DecompressionBombError`) THEN o backend SHALL tratá-la como imagem inválida, com a mesma resposta de WEBP-10, WEBP-11 ou WEBP-12.

**Independent Test**: `curl -F profile_picture=@notas.txt ...` no cadastro por senha devolve 400 com a mensagem acima, e o e-mail usado continua livre para um novo cadastro.

---

### P2: Seed de desenvolvimento em WebP

**User Story**: Como desenvolvedor, quero que os cabeleireiros do seed tenham fotos WebP criadas pelo mesmo fluxo de um cadastro real, para o ambiente de dev refletir a produção.

**Why P2**: A issue pede isso explicitamente, mas o seed só roda em dev.

**Acceptance Criteria**:

1. **WEBP-14** WHEN `populate_hairdressers` cria os cabeleireiros THEN cada `profile_picture.name` SHALL ser `profile_pics/<user_id>/<stem do placeholder>.webp`, com conteúdo WebP.
2. **WEBP-15** WHEN a chave `.webp` de uma foto do seed não existe no bucket THEN `restore_missing_pictures` SHALL gravar nessa mesma chave o WebP convertido do placeholder de mesmo stem.
3. **WEBP-16** WHEN a chave de uma foto do seed termina em `.jpg` (dado antigo) e não existe no bucket THEN `restore_missing_pictures` SHALL gravar nessa chave os bytes originais do placeholder, como faz hoje.
4. **WEBP-17** WHEN `populate_hairdressers` roda duas vezes seguidas THEN cada diretório `profile_pics/<user_id>/` SHALL conter exatamente um arquivo.

**Independent Test**: Com um banco **sem cabeleireiros** (volume novo) e o bucket vazio, `docker compose up` seguido de `awslocal s3 ls s3://<bucket>/profile_pics/ --recursive` lista só arquivos `.webp`. Em um banco de dev que já tem o seed antigo, o restore recria os `.jpg` legados (WEBP-16), e isso é o esperado.

---

## Edge Cases

- WHEN o arquivo enviado se chama `FOTO.JPG` THEN o backend SHALL gravar `.../FOTO.webp` (WEBP-02).
- WHEN o arquivo enviado não tem extensão (`foto`) THEN o backend SHALL gravar `.../foto.webp` (WEBP-02).
- WHEN já existe `profile_pics/<id>/foto.webp` e outro `foto.png` é salvo no mesmo diretório THEN o storage SHALL gerar um nome disponível com sufixo, ainda terminando em `.webp` (WEBP-01).
- WHEN um JPEG 6000×4000 com `Orientation=6` é enviado THEN o backend SHALL aplicar primeiro a rotação e depois a redução, gravando 720×1080 (WEBP-05, WEBP-09).
- WHEN a imagem tem exatamente 1080 px no maior lado THEN o backend SHALL manter as dimensões (WEBP-09).
- WHEN o arquivo enviado já é WebP THEN o backend SHALL recodificá-lo e remover os metadados (WEBP-07).
- WHEN um PNG em paleta (`P`) com transparência é enviado THEN o backend SHALL gravar `RGBA` (WEBP-06).
- WHEN um JPEG CMYK é enviado THEN o backend SHALL gravar `RGB` (WEBP-06).
- IF o arquivo tem extensão `.jpg` mas o conteúdo é texto THEN o backend SHALL responder com a mensagem de imagem inválida (WEBP-10, WEBP-11, WEBP-12).
- IF o arquivo é um JPEG truncado THEN o backend SHALL responder com a mensagem de imagem inválida (WEBP-10, WEBP-11, WEBP-12).
- WHEN o cadastro não envia `profile_picture` THEN o backend SHALL criar o usuário com `profile_picture` vazio, como hoje.

## Implicit-Requirement Dimensions

| Dimension | Coverage |
| --------- | -------- |
| Input validation & bounds | WEBP-10 a WEBP-13 |
| Failure / partial-failure states | WEBP-10 (cadastro atômico), WEBP-11, WEBP-12 |
| Idempotency / retry / duplicate handling | WEBP-17. Colisão de nome coberta nos edge cases. |
| Auth boundaries & rate limits | N/A: nenhuma rota nova e nenhuma regra de acesso muda. |
| Concurrency / ordering | N/A: a conversão é síncrona, na mesma requisição, antes do PUT. Não há evento assíncrono que possa chegar fora de ordem. |
| Data lifecycle / expiry | WEBP-04 (o original nunca é guardado). A conversão dos objetos antigos está fora do escopo. |
| Observability | N/A: as views atuais não fazem log de uploads, e o 400 já informa o cliente. |
| External-dependency failure | N/A: uma falha do S3 no upload continua com o comportamento atual. A feature não adiciona chamadas externas. |
| State-transition integrity | N/A: não há máquina de estados. |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| WEBP-01 | P1: Fotos viram WebP, AC1 | Tasks | Pending |
| WEBP-02 | P1: Fotos viram WebP, AC2 | Tasks | Pending |
| WEBP-03 | P1: Fotos viram WebP, AC3 | Tasks | Pending |
| WEBP-04 | P1: Fotos viram WebP, AC4 | Tasks | Pending |
| WEBP-05 | P1: Fotos viram WebP, AC5 | Tasks | Done |
| WEBP-06 | P1: Fotos viram WebP, AC6 | Tasks | Done |
| WEBP-07 | P1: Fotos viram WebP, AC7 | Tasks | Done |
| WEBP-08 | P1: Fotos viram WebP, AC8 | Tasks | Done |
| WEBP-09 | P1: Fotos viram WebP, AC9 | Tasks | Pending |
| WEBP-10 | P1: Upload inválido, AC1 | Tasks | Pending |
| WEBP-11 | P1: Upload inválido, AC2 | Tasks | Pending |
| WEBP-12 | P1: Upload inválido, AC3 | Tasks | Pending |
| WEBP-13 | P1: Upload inválido, AC4 | Tasks | Pending |
| WEBP-14 | P2: Seed em WebP, AC1 | Tasks | Pending |
| WEBP-15 | P2: Seed em WebP, AC2 | Tasks | Pending |
| WEBP-16 | P2: Seed em WebP, AC3 | Tasks | Pending |
| WEBP-17 | P2: Seed em WebP, AC4 | Tasks | Pending |

**Coverage:** 17 total, 17 mapped to tasks, 0 unmapped.

---

## Success Criteria

- [ ] Com um banco sem cabeleireiros e o bucket vazio, depois de `docker compose up` e de um cadastro com foto, `awslocal s3 ls --recursive` lista só objetos `.webp`.
- [ ] Nesse mesmo cenário, os 40 objetos do seed somam no máximo 5 MB. Hoje os JPEGs originais somam 134 MB, e a medição com 1080 px deu 2,06 MB.
- [ ] Nenhum objeto criado depois desta feature tem o maior lado acima de 1080 px. Objetos antigos estão fora do escopo.
- [ ] Nenhum teste existente do backend deixa de passar, e o número de testes só aumenta (baseline de 292 em `c445197`).
