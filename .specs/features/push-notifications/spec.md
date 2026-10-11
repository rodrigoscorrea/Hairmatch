# Notificações push Specification

**Issue:** [#182](https://github.com/rodrigoscorrea/Hairmatch/issues/182) · [Feature][Front/Back] Notificações push: infraestrutura, nova reserva e avaliações. Épico [#188](https://github.com/rodrigoscorrea/Hairmatch/issues/188).
**Origem:** spike #172 e o documento "Notificações Push — Hairmatch", itens N01 e N11 a N14.
**Escopo:** Complex (serviço externo novo, persistência, auth, ciclo de vida dos dados, backend e app)
**Plataformas:**
- backend Django;
- app Android: push e caixa de alertas;
- app web: só a caixa de alertas.

## Problem Statement

Uma ação de um usuário que afeta outro não chega a esse outro. O cabeleireiro só descobre uma reserva nova abrindo a agenda, e uma review recebida ele não vê em lugar nenhum. O cliente só descobre que foi avaliado abrindo "Avaliações recebidas".

Hoje o único aviso que o sistema manda é o e-mail de cadastro do Cognito. O app não tem push nem registro de aparelho. Os itens "Notificações" dos menus não fazem nada:
- cliente: `frontend-mobile/app/(app)/customer/profile.tsx:105`, cujo `handleMenuPress` está vazio;
- cabeleireiro: `frontend-mobile/app/(app)/hairdresser/profile/settings.tsx:86`, sem `onPress`.

## Goals

- [ ] O cabeleireiro recebe, num aparelho Android com a permissão concedida, um push e um alerta para cada reserva nova feita pelo app ou pelo chatbot.
- [ ] O cabeleireiro recebe um push e um alerta quando uma review dele é criada, editada ou excluída.
- [ ] O cliente recebe um push e um alerta quando o cabeleireiro dá, edita ou remove a nota dele.
- [ ] O item "Notificações" abre a caixa de alertas, com o número de não lidos, no Android e no web.
- [ ] Nenhuma falha do SNS ou do FCM desfaz ou atrasa com erro a ação que gerou a notificação.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| iOS (APNs) | Decisão do usuário: não há suporte para iOS por enquanto. |
| Push no web | O app web não tem service worker nem Web Push. No web, a caixa de alertas mostra os mesmos alertas. |
| WhatsApp e e-mail | Decisão do usuário. Quem reserva pelo chatbot continua recebendo só a confirmação dele. O SES segue só no Cognito. |
| Cancelamento de reserva (N02, N03) | Cards #183 e #184, que dependem desta feature. |
| Exclusão da conta do cabeleireiro (N04) | Card #171. |
| Lembretes e pedidos de avaliação agendados (N07 a N10) | Card #185. Precisam de scheduler, que ainda será refinado. |
| Confirmação e recusa de reserva (N05, N06) | Spike #187. |
| Engajamento para quem favoritou (N17 a N20) | Spike #186. |
| Tela de reviews recebidas pelo cabeleireiro | Card #189. O toque no alerta de review só passa a abrir essa tela quando ela existir. |
| Chaves de opt-in por categoria | Decisão do usuário: o opt-in é a permissão de notificação do Android. |
| Notificar fotos de review adicionadas ou removidas | Decisão do levantamento. A edição pelo app sempre chama o `PUT /api/reviews/{id}` primeiro (`useReviewForm.ts:135`), e esse `PUT` já notifica. |
| Expurgo de alertas antigos | Exige um job periódico (#185). |
| Excluir um alerta | A issue não pede. |
| Testes automatizados no app | O app não tem suíte. O gate do app é `npx tsc --noEmit` mais o UAT, como na #115 e na #118. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Canal | AWS SNS Mobile Push, entregue pelo FCM (HTTP v1). | Decisão do usuário na spike #172. | y |
| Plataforma do push | Só Android. O app web nunca pede permissão nem registra token. | Decisão do usuário (sem iOS). O web não tem canal de push. | y |
| Histórico | Toda notificação vira uma linha da tabela nova de alertas, com ou sem aparelho registrado. | Decisão do usuário: "gravar em uma nova tabela de alertas". | y |
| Para onde o menu leva | O item "Notificações" (cliente e cabeleireiro) abre a caixa de alertas. | Decisão do usuário. | y |
| Lido e não lido | Um alerta fica não lido até ser tocado. O item do menu mostra o número de não lidos, e a caixa tem "Marcar todas como lidas". | Decisão do usuário. | y |
| Toque no alerta de review (N11, N12) | Marca o alerta como lido e fica na caixa. A navegação para a tela de reviews recebidas entra no card #189. | Decisão do usuário: a tela ainda será criada (#189). | y |
| Projeto Firebase | Ainda não existe. Criá-lo, gerar o `google-services.json` e a chave da service account do FCM é tarefa manual do usuário. | Resposta do usuário. | y |
| Configuração nova | Uma env var, `SNS_PLATFORM_APPLICATION_ARN`. Vazia em dev, quando o backend busca pelo nome a platform application `hairmatch-dev-fcm` que o init do LocalStack cria. A credencial do FCM fica na platform application da AWS, nunca no backend. | O usuário aceita env vars novas neste épico. Buscar pelo nome em dev segue o padrão do Cognito (AD-005). | y |
| Opt-in | A permissão do Android. O app pede uma vez, depois do login. Com a permissão negada, o app não registra token, e os alertas continuam na caixa. | Decisão do usuário: sem chaves por categoria. O Android 13+ exige a permissão `POST_NOTIFICATIONS`. | y |
| Um aparelho, várias contas | O token é único no sistema. Se outra conta registra o mesmo token, o aparelho passa a ser dela, e a conta anterior deixa de receber push nele. | Um celular só tem um usuário logado por vez no app. | n |
| Tamanho do token | De 1 a 1024 caracteres depois de `strip()`. | Um token FCM tem por volta de 160 caracteres, e o índice único do Postgres não aceita chaves acima de ~2700 bytes. | n |
| Onde fica o `google-services.json` | Fora do git. No EAS, ele é uma variável de ambiente do tipo arquivo, `GOOGLE_SERVICES_JSON`. Localmente, é um arquivo em `frontend-mobile/google-services.json`, listado no `.gitignore`. Um `app.config.js` aponta o `android.googleServicesFile` para a variável ou para o arquivo. | O APK de preview é montado na nuvem do EAS e precisa do arquivo. Mantê-lo fora do git segue a postura da auditoria de segurança, e é o caminho que a documentação do Expo indica para arquivos sensíveis. | n |
| Quantos aparelhos por usuário | Sem limite. | N/A: cada aparelho tem um token só, e o token é único no sistema. | n |
| Retorno do registro | 201 `{data: {id}}` para um token novo ou que pertencia a outra conta; 200 `{data: {id}}` para um token que já é da conta. | O app guarda o `id` em memória para remover o aparelho no logout. Como o registro se repete a cada login e a cada sessão restaurada, o `id` não precisa sobreviver ao fechamento do app, e nenhuma dependência de armazenamento entra. | n |
| SNS fora do ar no registro | 503 `push-unavailable` (slug novo) e nenhuma linha gravada. O app ignora a falha e tenta de novo no próximo login. | Sem o endpoint do SNS, a linha não serve para nada. O app não mostra erro de algo que o usuário não pediu. | n |
| SNS fora do ar no envio | O alerta é gravado do mesmo jeito. O push daquele alerta é perdido, sem retentativa, e a falha vai para o log. | Não há fila (#185). A caixa de alertas cobre a perda. | n |
| Endpoint desativado pelo SNS ou token inválido | O backend apaga a linha do aparelho na primeira falha desse tipo. | O FCM não aceita mais aquele token, e o app registra o token novo no próximo login. | n |
| Logout | Antes do logout, o app chama `DELETE /api/users/me/push-devices/{id}`. A falha é ignorada, e o logout segue. | O logout (`POST /api/auth/logout`) não exige sessão (`users/views.py:726`), então o backend não sabe de quem é o aparelho. | n |
| Exclusão da conta | As linhas de aparelho e de alerta saem com o usuário (`CASCADE`). Os endpoints do SNS são apagados depois do commit, sem garantia: a falha só vai para o log. | Segue o padrão de arquivos do S3 (AD-011, AD-013). | n |
| Quantos alertas o `GET` traz | Os 50 mais recentes, do mais novo para o mais antigo (`created_at` desc, `id` desc no empate), mais o total de não lidos. Os mais antigos continuam no banco. | A caixa é um histórico recente. Paginar e expurgar ficam para depois (#185). | n |
| Texto do push | Título e corpo iguais aos do alerta, em pt-BR, com nome e sobrenome da outra parte, o serviço e a data e hora em `America/Manaus`. | Os horários do app são de Manaus (`hairmatch/local_time.py`). | n |
| Formato da nota no texto | A nota da review (float de 1 a 5) sai sem casa decimal quando é inteira e com uma casa e vírgula quando não é ("4,5"). A nota do cliente é inteira. | `Review.rating` é `FloatField` (`review/models.py:16`), e `CustomerRating.rating` é inteiro. | n |
| Push com o app aberto | O Android mostra o push como banner, e o contador de não lidos é atualizado. | O usuário vê o aviso mesmo dentro do app. | n |
| Ordem das checagens nas rotas novas | Primeiro a sessão (401), depois o corpo (400) ou o `{id}` (404). | Segue as rotas existentes e a lição L-019. | n |
| Throttle das rotas novas | Nenhum. | N/A: todas exigem sessão, e nenhuma dispara e-mail nem valida segredo (AD-008). | n |

**Open questions:** none. Todas foram resolvidas ou registradas acima.

---

## Catálogo de notificações

Toda notificação tem um `kind`, um destinatário, um título, um corpo e um destino para o toque. Nos textos:
- `{cliente}` e `{cabeleireiro}` são `first_name last_name` da outra parte;
- `{serviço}` é o `Service.name`;
- `{data}` é `dd/mm` e `{hora}` é `HH:MM`, os dois em `America/Manaus`;
- `{nota}` segue o formato da tabela de assumptions;
- `{estrelas}` é "estrela" quando a nota é 1 e "estrelas" nos outros casos.

| `kind` | Item | Gatilho | Destinatário | Título | Corpo | Toque |
| --- | --- | --- | --- | --- | --- | --- |
| `reservation-created` | N01 | Commit de `CreateReserve` (`reserve/views.py:85`) ou de `create_new_reserve` (`reserve/views.py:377`) | Cabeleireiro do serviço | Nova reserva | `{cliente} reservou {serviço} para {data} às {hora}.` | Agenda do cabeleireiro (`/(app)/hairdresser/agenda`) |
| `review-created` | N11 | Commit de `CreateReview` (`review/views.py:74`) | Cabeleireiro avaliado | Nova avaliação | `{cliente} avaliou seu atendimento com {nota} {estrelas}.` | Marca como lido, sem navegar (#189) |
| `review-updated` | N12 | Commit de `UpdateReview` (`review/views.py:153`) | Cabeleireiro avaliado | Avaliação atualizada | `{cliente} atualizou a avaliação do seu atendimento: {nota} {estrelas}.` | Marca como lido, sem navegar (#189) |
| `review-deleted` | N12 | Commit de `RemoveReview` (`review/views.py:176`) | Cabeleireiro avaliado | Avaliação removida | `{cliente} removeu a avaliação do seu atendimento.` | Marca como lido, sem navegar |
| `customer-rating-created` | N13 | Commit de `record_customer_rating` (`review/customer_ratings.py`) | Cliente avaliado | Você foi avaliado | `{cabeleireiro} deu nota {nota} para você.` | Avaliações recebidas (`/(app)/customer/ratings`) |
| `customer-rating-updated` | N14 | Commit de `update_customer_rating` | Cliente avaliado | Avaliação atualizada | `{cabeleireiro} mudou sua nota para {nota}.` | Avaliações recebidas |
| `customer-rating-deleted` | N14 | Commit de `delete_customer_rating` | Cliente avaliado | Avaliação removida | `{cabeleireiro} removeu a nota que deu a você.` | Avaliações recebidas |

---

## User Stories

### P1: Registro do aparelho ⭐ MVP

**User Story**: Como usuário do app Android, quero que o meu celular fique registrado para receber push, para ser avisado do que os outros usuários fazem comigo.

**Why P1**: Sem o registro, nenhum push chega.

**Acceptance Criteria**:

1. **NOTIF-01** WHEN o usuário da sessão chama `POST /api/users/me/push-devices` com `{"token": "<token FCM>"}` e o token não está registrado THEN o backend SHALL criar um endpoint no SNS para o token, gravar a linha do aparelho e responder 201 `{"data": {"id": <id>}}`.
2. **NOTIF-02** WHEN o usuário chama o `POST` com um token que já é dele THEN o backend SHALL responder 200 `{"data": {"id": <mesmo id>}}` e SHALL manter uma única linha para o token.
3. **NOTIF-03** WHEN o usuário chama o `POST` com um token registrado por outra conta THEN o backend SHALL passar a linha para o usuário da sessão, responder 201 `{"data": {"id": <id>}}`, e a outra conta SHALL deixar de receber push nesse aparelho.
4. The backend SHALL nunca gravar duas linhas com o mesmo token, nem com dois `POST` simultâneos. **(NOTIF-04)**
5. **NOTIF-05** IF o `token` falta, não é string, está vazio depois de `strip()` ou passa de 1024 caracteres THEN o backend SHALL responder 400 `validation-error` com o item `{"pointer": "#/token"}` e SHALL não gravar nenhuma linha.
6. **NOTIF-06** IF o SNS falha ou não responde ao criar o endpoint THEN o backend SHALL responder 503 `push-unavailable`, SHALL não gravar nenhuma linha e SHALL registrar no log a operação e o código do erro, sem o token.
7. **NOTIF-07** WHEN o usuário da sessão chama `DELETE /api/users/me/push-devices/{id}` com um aparelho dele THEN o backend SHALL apagar a linha, responder 204 sem corpo e, depois do commit, apagar o endpoint no SNS.
8. **NOTIF-08** IF o `{id}` do `DELETE` não existe ou é de outra conta THEN o backend SHALL responder 404 `not-found` e SHALL não apagar nenhuma linha.
9. **NOTIF-09** IF o `POST` ou o `DELETE` chega sem sessão válida THEN o backend SHALL responder 401 `invalid-session` e SHALL não mudar nenhuma linha.
10. **NOTIF-10** IF apagar o endpoint no SNS falha THEN o backend SHALL manter a resposta 204, já que a linha já saiu, e SHALL registrar a falha no log.
11. **NOTIF-11** WHEN um usuário exclui a conta (`DELETE /api/users/me`) THEN o backend SHALL apagar todas as linhas de aparelho dele e, depois do commit, os endpoints correspondentes no SNS.
12. **NOTIF-12** WHEN o login termina no Android (e-mail e senha ou Google) THEN o app SHALL pedir a permissão de notificação, se ela ainda não foi respondida.
13. **NOTIF-13** WHILE a permissão de notificação está concedida o app SHALL obter o token FCM do aparelho depois de cada login e no início de cada sessão restaurada, chamar o `POST` e guardar em memória o `id` devolvido.
14. **NOTIF-14** WHEN o sistema troca o token FCM do aparelho com a sessão aberta THEN o app SHALL chamar o `POST` com o token novo e guardar em memória o `id` novo.
15. **NOTIF-15** IF a permissão é negada THEN o app SHALL não chamar o `POST`, SHALL não mostrar erro e SHALL não pedir a permissão de novo na mesma instalação.
16. **NOTIF-16** IF obter o token FCM falha (sem Play Services ou sem `google-services.json` no build) ou o `POST` falha THEN o app SHALL seguir para a tela inicial sem mostrar erro.
17. **NOTIF-17** WHEN o usuário sai da conta THEN o app SHALL chamar o `DELETE` do `id` guardado em memória antes do `POST /api/auth/logout`, esquecer o `id` e SHALL concluir o logout mesmo se o `DELETE` falhar.
18. **NOTIF-18** WHILE o app roda no web ele SHALL nunca pedir a permissão nem chamar o `POST`.

**Independent Test**: num dev build Android, logar e aceitar a permissão. A tabela de aparelhos ganha uma linha do usuário, e o SNS do LocalStack, um endpoint. Sair da conta apaga a linha e o endpoint.

---

### P1: Envio e gravação de alertas ⭐ MVP

**User Story**: Como usuário, quero que cada aviso fique guardado e chegue no meu celular, sem atrapalhar a ação da outra pessoa.

**Why P1**: É o mecanismo que todos os eventos usam.

**Acceptance Criteria**:

1. **NOTIF-19** WHEN uma ação do catálogo termina com commit THEN o backend SHALL gravar um alerta para o destinatário, com o `kind`, o título, o corpo e os dados do catálogo, não lido.
2. **NOTIF-20** IF a ação do catálogo falha ou a transação é desfeita THEN o backend SHALL não gravar alerta e SHALL não enviar push.
3. **NOTIF-21** WHEN um alerta é gravado THEN o backend SHALL publicar, depois do commit, um push com o título e o corpo do alerta em cada endpoint de aparelho do destinatário, com `alert_id` e `kind` nos dados do push.
4. **NOTIF-22** WHILE o destinatário não tem aparelho registrado o backend SHALL gravar o alerta e SHALL não chamar o SNS.
5. **NOTIF-23** IF o SNS falha ao publicar num endpoint THEN o backend SHALL manter o alerta gravado, SHALL manter a resposta da ação de origem e SHALL registrar no log a operação e o código do erro, sem o token.
6. **NOTIF-24** IF o SNS responde que o endpoint está desativado ou não existe THEN o backend SHALL apagar a linha do aparelho e SHALL continuar a publicação nos outros aparelhos do destinatário.
7. **NOTIF-25** WHEN a ação apaga a linha que a notificação descreve (`review-deleted`, `customer-rating-deleted`) THEN o backend SHALL montar o texto antes de apagar a linha.
8. The backend SHALL nunca notificar o autor da ação. **(NOTIF-26)**
9. The texto do alerta e do push SHALL mostrar a data e a hora em `America/Manaus`. **(NOTIF-27)**

**Independent Test**: com o SNS do LocalStack, criar uma reserva por API para um cabeleireiro com aparelho registrado. A tabela de alertas ganha uma linha, e o LocalStack registra uma mensagem para o endpoint. Parar o LocalStack e repetir: a reserva é criada (201), o alerta é gravado, e a falha aparece no log.

---

### P1: Nova reserva (N01) ⭐ MVP

**User Story**: Como cabeleireiro, quero ser avisado quando um cliente reserva um horário comigo, para me organizar sem precisar abrir a agenda.

**Why P1**: Decisão do usuário. É o aviso de maior valor e o mais barato.

**Acceptance Criteria**:

1. **NOTIF-28** WHEN um cliente cria uma reserva pelo `POST /api/reservations` THEN o backend SHALL notificar o cabeleireiro do serviço com `reservation-created`, com o nome do cliente, o serviço e o início da reserva.
2. **NOTIF-29** WHEN o chatbot cria uma reserva por `create_new_reserve` THEN o backend SHALL notificar o cabeleireiro com o mesmo `reservation-created`.
3. **NOTIF-30** IF a reserva não é criada (409 `slot-unavailable`, 409 `customer-schedule-conflict`, 400 ou 404) THEN o backend SHALL não notificar.
4. **NOTIF-31** WHEN o cabeleireiro toca no push ou no alerta `reservation-created` THEN o app SHALL marcar o alerta como lido e abrir a agenda do cabeleireiro.

**Independent Test**: como cliente, reservar um serviço pelo app. O cabeleireiro recebe "Nova reserva", com o nome do cliente e o horário de Manaus, e o toque abre a agenda.

---

### P1: Review recebida (N11) ⭐ MVP

**User Story**: Como cabeleireiro, quero saber quando um cliente avaliou meu atendimento.

**Why P1**: Decisão do usuário.

**Acceptance Criteria**:

1. **NOTIF-32** WHEN um cliente cria uma review pelo `POST /api/reviews` THEN o backend SHALL notificar o cabeleireiro da review com `review-created` e a nota da review.
2. **NOTIF-33** IF a review não é criada (400, 403, 404, 409 `review-exists` ou `invalid-image`) THEN o backend SHALL não notificar.
3. **NOTIF-34** WHEN o cabeleireiro toca no push ou no alerta `review-created` THEN o app SHALL marcar o alerta como lido e manter a caixa de alertas aberta.

**Independent Test**: como cliente, avaliar uma reserva já passada. O cabeleireiro recebe "Nova avaliação" com a nota.

---

### P1: Nota recebida (N13) ⭐ MVP

**User Story**: Como cliente, quero saber quando o cabeleireiro me avaliou.

**Why P1**: Decisão do usuário.

**Acceptance Criteria**:

1. **NOTIF-35** WHEN um cabeleireiro cria a nota de um cliente pelo `POST /api/customer-ratings` THEN o backend SHALL notificar o cliente com `customer-rating-created` e a nota.
2. **NOTIF-36** IF a nota não é criada (400, 403, 404, 409 `review-exists` ou `service-not-finished`) THEN o backend SHALL não notificar.
3. **NOTIF-37** WHEN o cliente toca no push ou no alerta `customer-rating-created` THEN o app SHALL marcar o alerta como lido e abrir "Avaliações recebidas".

**Independent Test**: como cabeleireiro, dar nota a um cliente de um atendimento já terminado. O cliente recebe "Você foi avaliado", e o toque abre "Avaliações recebidas".

---

### P1: Caixa de alertas ⭐ MVP

**User Story**: Como usuário, quero ver numa tela os avisos que recebi, para não perder nenhum, mesmo sem push.

**Why P1**: Decisão do usuário (tabela de alertas). É a única forma de ver os avisos no web e com a permissão negada.

**Acceptance Criteria**:

1. **NOTIF-38** WHEN o usuário da sessão chama `GET /api/users/me/alerts` THEN o backend SHALL responder 200 `{"data": {"alerts": [...], "unread_count": <n>}}`, com os 50 alertas mais recentes dele em `alerts`, cada um no formato `{id, kind, title, body, data, read, created_at}`, e o total de não lidos em `unread_count`.
2. **NOTIF-39** The `GET` SHALL ordenar os alertas do mais novo para o mais antigo (`created_at` desc, `id` desc no empate) e SHALL trazer só os alertas do usuário da sessão.
3. **NOTIF-40** WHEN o usuário chama `PATCH /api/users/me/alerts/{id}` com `{"read": true}` ou `{"read": false}` num alerta dele THEN o backend SHALL gravar o estado e responder 200 `{"data": <alerta>}`.
4. **NOTIF-41** WHEN o usuário chama `PATCH /api/users/me/alerts` com `{"read": true}` THEN o backend SHALL marcar como lidos todos os alertas dele e responder 204 sem corpo.
5. **NOTIF-42** IF o `read` dos `PATCH` falta ou não é booleano THEN o backend SHALL responder 400 `validation-error` com o item `{"pointer": "#/read"}`.
6. **NOTIF-43** IF o `PATCH /api/users/me/alerts` recebe `{"read": false}` THEN o backend SHALL responder 400 `validation-error` com o item `{"pointer": "#/read"}` e SHALL não mudar nenhum alerta.
7. **NOTIF-44** IF o `{id}` do `PATCH` não existe ou é de outra conta THEN o backend SHALL responder 404 `not-found`.
8. **NOTIF-45** IF uma rota de alertas chega sem sessão válida THEN o backend SHALL responder 401 `invalid-session`.
9. **NOTIF-46** WHEN um usuário exclui a conta THEN o backend SHALL apagar todos os alertas dele.
10. **NOTIF-47** WHEN o usuário toca em "Notificações" no menu do perfil (cliente) ou das configurações (cabeleireiro) THEN o app SHALL abrir a tela de alertas, com o título "Notificações" e o botão "‹ Voltar".
11. **NOTIF-48** WHEN a tela de alertas ganha o foco THEN o app SHALL chamar o `GET` e mostrar um item por alerta, na ordem da API, com título, corpo e data relativa ("agora", "há 5 min", "ontem", `dd/mm`).
12. The item de um alerta não lido SHALL ter um destaque visual (fundo e marcador) que o de um alerta lido não tem. **(NOTIF-49)**
13. **NOTIF-50** WHEN o usuário toca num alerta THEN o app SHALL marcar o item como lido na hora, chamar o `PATCH` do alerta com `{"read": true}` e seguir o destino do catálogo.
14. **NOTIF-51** WHEN o usuário toca em "Marcar todas como lidas" THEN o app SHALL marcar todos os itens como lidos na hora e chamar o `PATCH /api/users/me/alerts`.
15. **NOTIF-52** WHILE nenhum alerta está não lido o app SHALL desabilitar "Marcar todas como lidas".
16. **NOTIF-53** WHEN o `GET` responde sem alertas THEN a tela SHALL mostrar "Você ainda não tem notificações.".
17. **NOTIF-54** IF o `GET` da tela falha THEN o app SHALL mostrar o texto do slug (`problemMessage`, fallback "Não foi possível carregar suas notificações.") num `ErrorModal` e SHALL não mostrar a mensagem de lista vazia.
18. **NOTIF-55** IF um `PATCH` falha THEN o app SHALL devolver os itens ao estado anterior e SHALL mostrar o texto do slug (fallback "Não foi possível atualizar suas notificações.") num `ErrorModal`.
19. **NOTIF-56** WHILE `unread_count` é maior que zero o item "Notificações" do menu SHALL mostrar o número, e a partir de 100 SHALL mostrar "99+".
20. **NOTIF-57** WHEN o perfil do cliente ou as configurações do cabeleireiro ganham o foco, ou um push chega com o app aberto, THEN o app SHALL atualizar o número de não lidos com o `GET`.
21. **NOTIF-58** IF o `GET` do contador falha THEN o app SHALL esconder o número e SHALL não mostrar erro.

**Independent Test**: no web, como cabeleireiro com duas reservas novas, abrir "Notificações" pelas configurações. O menu mostra "2", e a caixa lista dois alertas não lidos. Tocar num deles leva à agenda. Ao voltar, o menu mostra "1". "Marcar todas como lidas" zera o contador.

---

### P2: Review editada ou excluída (N12)

**User Story**: Como cabeleireiro, quero saber quando um cliente muda ou apaga a avaliação que deixou.

**Why P2**: Decisão do usuário. Rende menos que o aviso de review nova.

**Acceptance Criteria**:

1. **NOTIF-59** WHEN o cliente edita a review pelo `PUT /api/reviews/{id}` THEN o backend SHALL notificar o cabeleireiro com `review-updated` e a nota nova.
2. **NOTIF-60** WHEN o cliente exclui a review pelo `DELETE /api/reviews/{id}` THEN o backend SHALL notificar o cabeleireiro com `review-deleted`.
3. **NOTIF-61** IF a edição ou a exclusão falha (400 ou 404) THEN o backend SHALL não notificar.
4. **NOTIF-62** WHEN o cliente adiciona ou remove uma foto da review (`POST` ou `DELETE /api/reviews/{id}/pictures...`) THEN o backend SHALL não notificar.
5. **NOTIF-63** WHEN o cabeleireiro toca no push ou no alerta `review-updated` ou `review-deleted` THEN o app SHALL marcar o alerta como lido e manter a caixa aberta.

**Independent Test**: como cliente, editar a nota de uma review e depois excluí-la. O cabeleireiro recebe "Avaliação atualizada" e "Avaliação removida".

---

### P2: Nota editada ou removida (N14)

**User Story**: Como cliente, quero saber quando o cabeleireiro muda ou remove a nota que me deu.

**Why P2**: Decisão do usuário.

**Acceptance Criteria**:

1. **NOTIF-64** WHEN o cabeleireiro edita a nota pelo `PUT /api/customer-ratings/{id}` THEN o backend SHALL notificar o cliente com `customer-rating-updated` e a nota nova.
2. **NOTIF-65** WHEN o cabeleireiro remove a nota pelo `DELETE /api/customer-ratings/{id}` THEN o backend SHALL notificar o cliente com `customer-rating-deleted`.
3. **NOTIF-66** IF a edição ou a remoção falha (400, 403 ou 404) THEN o backend SHALL não notificar.
4. **NOTIF-67** WHEN o cliente toca no push ou no alerta `customer-rating-updated` ou `customer-rating-deleted` THEN o app SHALL marcar o alerta como lido e abrir "Avaliações recebidas".

**Independent Test**: como cabeleireiro, editar a nota de um cliente pela agenda e depois removê-la. O cliente recebe os dois avisos, e o toque abre "Avaliações recebidas".

---

### P1: Ambiente local ⭐ MVP

**User Story**: Como desenvolvedor, quero o SNS no `docker compose`, para testar o envio sem a AWS real.

**Why P1**: Toda feature do projeto roda e é verificada localmente (AD-005).

**Acceptance Criteria**:

1. **NOTIF-68** WHEN o LocalStack sobe pelo `docker compose` THEN o init SHALL criar a platform application `hairmatch-dev-fcm` com credencial falsa.
2. **NOTIF-69** WHILE `SNS_PLATFORM_APPLICATION_ARN` está vazia o backend SHALL usar o ARN da platform application `hairmatch-dev-fcm`, buscada pelo nome.
3. **NOTIF-70** WHILE a suíte de testes roda o backend SHALL usar um fake do SNS, sem rede, como o `FakeCognitoIdp`.
4. **NOTIF-71** The `docker/.env.example` SHALL documentar `SNS_PLATFORM_APPLICATION_ARN`, vazia em dev e com o ARN real em produção.

**Independent Test**: `docker compose up` cria a platform application, e um `POST /api/users/me/push-devices` em dev cria um endpoint nela.

---

## Edge Cases

- **NOTIF-72** IF o destinatário tem mais de um aparelho THEN o backend SHALL publicar em todos eles.
- **NOTIF-73** IF o mesmo alerta é publicado num aparelho que outra conta acabou de registrar THEN o push SHALL ir só para quem é dono da linha no momento do envio.
- **NOTIF-74** WHEN o push chega com o app fechado e o usuário toca nele THEN o app SHALL abrir, restaurar a sessão e seguir o destino do catálogo.
- **NOTIF-75** IF o usuário toca num push de outra conta (o aparelho trocou de conta depois do envio) e o `PATCH` do alerta responde 404 THEN o app SHALL abrir a caixa de alertas.
- **NOTIF-76** IF o usuário toca num push sem sessão válida THEN o app SHALL abrir o login.
- **NOTIF-77** The backend SHALL nunca gravar o token FCM nem o ARN do endpoint no log.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| NOTIF-01 | P1: Registro do aparelho (backend) | T7, T19 | Implemented |
| NOTIF-02 | P1: Registro do aparelho (backend) | T7 | Implemented |
| NOTIF-03 | P1: Registro do aparelho (backend) | T7 | Implemented |
| NOTIF-04 | P1: Registro do aparelho (backend) | T2, T7 | Implemented |
| NOTIF-05 | P1: Registro do aparelho (backend) | T7 | Implemented |
| NOTIF-06 | P1: Registro do aparelho (backend) | T1, T3, T7 | Implemented |
| NOTIF-07 | P1: Registro do aparelho (backend) | T7, T19 | Implemented |
| NOTIF-08 | P1: Registro do aparelho (backend) | T7 | Implemented |
| NOTIF-09 | P1: Registro do aparelho (backend) | T7 | Implemented |
| NOTIF-10 | P1: Registro do aparelho (backend) | T7 | Implemented |
| NOTIF-11 | P1: Registro do aparelho (backend) | T2, T8 | Implemented |
| NOTIF-12 | P1: Registro do aparelho (app) | T15, T21, T23 | Implemented |
| NOTIF-13 | P1: Registro do aparelho (app) | T13, T14, T15, T16, T20, T21, T23 | Implemented |
| NOTIF-14 | P1: Registro do aparelho (app) | T15, T23 | Implemented |
| NOTIF-15 | P1: Registro do aparelho (app) | T15, T23 | Implemented |
| NOTIF-16 | P1: Registro do aparelho (app) | T15, T23 | Implemented |
| NOTIF-17 | P1: Registro do aparelho (app) | T14, T15, T16, T23 | Implemented |
| NOTIF-18 | P1: Registro do aparelho (app) | T15, T23 | Implemented |
| NOTIF-19 | P1: Envio e gravação de alertas | T6 | Implemented |
| NOTIF-20 | P1: Envio e gravação de alertas | T6 | Implemented |
| NOTIF-21 | P1: Envio e gravação de alertas | T3, T6, T19 | Implemented |
| NOTIF-22 | P1: Envio e gravação de alertas | T6 | Implemented |
| NOTIF-23 | P1: Envio e gravação de alertas | T6 | Implemented |
| NOTIF-24 | P1: Envio e gravação de alertas | T3, T6 | Implemented |
| NOTIF-25 | P1: Envio e gravação de alertas | T5 | Implemented |
| NOTIF-26 | P1: Envio e gravação de alertas | T6 | Implemented |
| NOTIF-27 | P1: Envio e gravação de alertas | T5 | Implemented |
| NOTIF-28 | P1: Nova reserva (N01) | T5, T10, T19 | Implemented |
| NOTIF-29 | P1: Nova reserva (N01) | T10, T19 | Implemented |
| NOTIF-30 | P1: Nova reserva (N01) | T10 | Implemented |
| NOTIF-31 | P1: Nova reserva (N01) | T16, T23 | Implemented |
| NOTIF-32 | P1: Review recebida (N11) | T5, T11, T19 | Implemented |
| NOTIF-33 | P1: Review recebida (N11) | T11 | Implemented |
| NOTIF-34 | P1: Review recebida (N11) | T16, T23 | Implemented |
| NOTIF-35 | P1: Nota recebida (N13) | T5, T12, T19 | Implemented |
| NOTIF-36 | P1: Nota recebida (N13) | T12 | Implemented |
| NOTIF-37 | P1: Nota recebida (N13) | T16, T23 | Implemented |
| NOTIF-38 | P1: Caixa de alertas (backend) | T9, T14, T19 | Implemented |
| NOTIF-39 | P1: Caixa de alertas (backend) | T2, T9 | Implemented |
| NOTIF-40 | P1: Caixa de alertas (backend) | T9, T14 | Implemented |
| NOTIF-41 | P1: Caixa de alertas (backend) | T9, T14, T19 | Implemented |
| NOTIF-42 | P1: Caixa de alertas (backend) | T9 | Implemented |
| NOTIF-43 | P1: Caixa de alertas (backend) | T9 | Implemented |
| NOTIF-44 | P1: Caixa de alertas (backend) | T9 | Implemented |
| NOTIF-45 | P1: Caixa de alertas (backend) | T9 | Implemented |
| NOTIF-46 | P1: Caixa de alertas (backend) | T2, T8 | Implemented |
| NOTIF-47 | P1: Caixa de alertas (app) | T17, T18, T23 | Implemented |
| NOTIF-48 | P1: Caixa de alertas (app) | T17, T23 | Implemented |
| NOTIF-49 | P1: Caixa de alertas (app) | T17, T23 | Implemented |
| NOTIF-50 | P1: Caixa de alertas (app) | T17, T23 | Implemented |
| NOTIF-51 | P1: Caixa de alertas (app) | T17, T23 | Implemented |
| NOTIF-52 | P1: Caixa de alertas (app) | T17, T23 | Implemented |
| NOTIF-53 | P1: Caixa de alertas (app) | T17, T23 | Implemented |
| NOTIF-54 | P1: Caixa de alertas (app) | T17, T23 | Implemented |
| NOTIF-55 | P1: Caixa de alertas (app) | T17, T23 | Implemented |
| NOTIF-56 | P1: Caixa de alertas (app) | T18, T23 | Implemented |
| NOTIF-57 | P1: Caixa de alertas (app) | T18, T23 | Implemented |
| NOTIF-58 | P1: Caixa de alertas (app) | T18, T23 | Implemented |
| NOTIF-59 | P2: Review editada ou excluída (N12) | T5, T11, T19 | Implemented |
| NOTIF-60 | P2: Review editada ou excluída (N12) | T5, T11, T19 | Implemented |
| NOTIF-61 | P2: Review editada ou excluída (N12) | T11 | Implemented |
| NOTIF-62 | P2: Review editada ou excluída (N12) | T11 | Implemented |
| NOTIF-63 | P2: Review editada ou excluída (N12) | T16, T23 | Implemented |
| NOTIF-64 | P2: Nota editada ou removida (N14) | T5, T12, T19 | Implemented |
| NOTIF-65 | P2: Nota editada ou removida (N14) | T5, T12, T19 | Implemented |
| NOTIF-66 | P2: Nota editada ou removida (N14) | T12 | Implemented |
| NOTIF-67 | P2: Nota editada ou removida (N14) | T16, T23 | Implemented |
| NOTIF-68 | P1: Ambiente local | T4, T19 | Implemented |
| NOTIF-69 | P1: Ambiente local | T3, T4, T19, T22 | Implemented |
| NOTIF-70 | P1: Ambiente local | T3 | Implemented |
| NOTIF-71 | P1: Ambiente local | T4, T22 | Implemented |
| NOTIF-72 | Edge cases | T6 | Implemented |
| NOTIF-73 | Edge cases | T6 | Implemented |
| NOTIF-74 | Edge cases | T15, T16, T23 | Implemented |
| NOTIF-75 | Edge cases | T16, T23 | Implemented |
| NOTIF-76 | Edge cases | T16, T23 | Implemented |
| NOTIF-77 | Edge cases | T3, T6 | Implemented |

**Coverage:** 77 total, 77 mapped to tasks, 0 unmapped ✅

### Implicit-requirement dimensions

| Dimension | Coverage |
| --------- | -------- |
| Input validation & bounds | NOTIF-05, NOTIF-42, NOTIF-43; 50 alertas no `GET` (NOTIF-38). |
| Failure / partial-failure states | NOTIF-06, NOTIF-10, NOTIF-16, NOTIF-20, NOTIF-23, NOTIF-54, NOTIF-55, NOTIF-58. |
| Idempotency / retry / duplicate handling | NOTIF-02, NOTIF-04, NOTIF-41. Push sem retentativa (assumption). |
| Auth boundaries & rate limits | NOTIF-08, NOTIF-09, NOTIF-39, NOTIF-44, NOTIF-45, NOTIF-26. Throttle N/A (assumption). |
| Concurrency / ordering | NOTIF-04 (token único). Alertas ordenados por `created_at` e `id` (NOTIF-39). |
| Data lifecycle / expiry | NOTIF-07, NOTIF-11, NOTIF-17, NOTIF-24, NOTIF-46. Expurgo de alertas fora do escopo (#185). |
| Observability | NOTIF-06, NOTIF-10, NOTIF-23, NOTIF-77. |
| External-dependency failure | NOTIF-06, NOTIF-23, NOTIF-24. |
| State-transition integrity | Lido e não lido: NOTIF-40, NOTIF-41, NOTIF-43. A ação de origem só notifica depois do commit (NOTIF-19, NOTIF-20). |

---

## Success Criteria

- [ ] Num dev build Android com o projeto Firebase real, cada um dos 7 `kind` do catálogo chega como push ao aparelho do destinatário, e o toque segue o destino do catálogo.
- [ ] Com o SNS fora do ar, as rotas de reserva, review e nota respondem os mesmos status de hoje.
- [ ] No web, a caixa de alertas mostra os mesmos alertas que o Android.
- [ ] A suíte do backend passa sem rede, com o fake do SNS, e `npx tsc --noEmit` sai com exit 0.
