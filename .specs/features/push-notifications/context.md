# Notificações push Context

**Gathered:** 2026-10-11
**Spec:** `.specs/features/push-notifications/spec.md`
**Status:** Ready for design

**Fontes:**
- as decisões e os comentários do usuário no documento "Notificações Push — Hairmatch" (levantamento da spike #172);
- as respostas desta sessão, que também criaram o épico #188 e os cards #182 a #187 e #189.

---

## Feature Boundary

Primeira entrega de notificações do Hairmatch (#182). Ela traz:
- o registro do aparelho Android no AWS SNS (FCM);
- a tabela de alertas, com a caixa de alertas no app;
- sete notificações disparadas por evento:
  - nova reserva (N01);
  - review criada, editada ou excluída (N11, N12);
  - nota do cliente criada, editada ou removida (N13, N14).

A infraestrutura é reaproveitada pelos outros cards do épico.

---

## Implementation Decisions

### Canal e plataformas

- Push via AWS SNS Mobile Push, entregue pelo FCM.
- Só Android. Não há suporte para iOS por enquanto.
- O web não recebe push, mas mostra a caixa de alertas.
- O SES continua só no Cognito. Nenhum outro e-mail é necessário enquanto não houver pagamento.
- WhatsApp fora do escopo: quem reserva pelo chatbot continua recebendo só a confirmação do chatbot. A reserva feita pelo chatbot notifica o cabeleireiro do mesmo jeito (N01).

### Quais eventos entram agora

- **Entram:** N01, N11, N12, N13 e N14. Na triagem, todos ficaram como "Implementar", com os comentários "pode implementar" e "boa, pode implementar".
- **Ficam para outros cards:**
  - N02 (#183) e N03 (#184): cancelamento, com a notificação como critério de aceite;
  - N04 (#171);
  - N07 a N10 (#185): precisam de scheduler, ainda a refinar em arquitetura e custo;
  - N05 e N06 (spike #187);
  - N17 a N20 (spike #186).
- **Para depois, sem card:** N15 e N16.

### Histórico de alertas

- Toda notificação é gravada numa tabela nova de alertas ("gravar em uma nova tabela de alertas").
- O item "Notificações" do menu (cliente e cabeleireiro) abre a caixa de alertas.
- Lido e não lido: o alerta fica não lido até o toque. O item do menu mostra o número de não lidos, e a caixa tem "Marcar todas como lidas".

### Opt-in

- O opt-in é a permissão de notificação do Android.
- Não há chaves por categoria nesta entrega.

### Toque no alerta de review

- O cabeleireiro não tem tela de reviews recebidas.
- O usuário pediu um card para essa tela (#189), e é ela que vai receber o toque do alerta de review quando existir.
- Até lá, tocar em `review-created`, `review-updated` ou `review-deleted` só marca o alerta como lido.

### Configuração e ambiente

- Novas env vars são aceitas neste épico ("creio que até inevitáveis").
- O projeto Firebase ainda não existe. Criá-lo, gerar o `google-services.json` e a chave da service account é tarefa manual do usuário, antes das tarefas que dependem do FCM real.

### Agent's Discretion

- O formato das rotas, dentro do AD-007.
- O nome do app Django e dos modelos.
- O texto exato das mensagens do catálogo.
- O limite de 50 alertas no `GET`.
- O comportamento quando o SNS falha (registrado nas assumptions).
- Como o app guarda o `id` do aparelho.

### Declined / Undiscussed Gray Areas → Assumptions

Os temas abaixo não foram discutidos e estão registrados na tabela de assumptions do spec, com o default e o motivo:
- dono do token quando duas contas usam o mesmo celular;
- retorno do registro (200 ou 201);
- falha do SNS no registro e no envio;
- endpoint desativado;
- logout;
- exclusão da conta;
- formato da nota;
- push com o app aberto.

---

## Specific References

As mensagens de exemplo do levantamento serviram de base para o catálogo:
- "Nova reserva: Ana, Corte, sáb 14:00";
- "Ana avaliou seu atendimento com 5 estrelas";
- "João avaliou você como cliente".

---

## Deferred Ideas

- **Tela de reviews recebidas pelo cabeleireiro** e o toque do alerta de review levando a ela: #189.
- **Chaves de opt-in por categoria:** voltam quando entrarem as notificações de engajamento (#186).
- **Expurgo e paginação de alertas antigos:** dependem de um job periódico (#185).
- **iOS (APNs):** sem card. Volta quando o app tiver suporte a iOS.
