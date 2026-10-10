# Galeria de fotos do cabeleireiro Context

**Gathered:** 2026-10-10
**Spec:** `.specs/features/hairdresser-gallery/spec.md`
**Status:** Ready for design

---

## Feature Boundary

O cabeleireiro vê, adiciona e remove as fotos da própria galeria. O cliente, e qualquer visitante, só vê. Não há edição: trocar uma foto é remover e adicionar.

As fotos ficam no bucket de mídia sob `hairdresser/gallery/`, passam pelo `WebPImageField` (AD-003) e saem do bucket quando são removidas ou quando a conta é excluída.

---

## Implementation Decisions

### Armazenamento no bucket

- A chave é `hairdresser/gallery/<hairdresser_id>/<uuid4 hex>.webp`, com uma subpasta por cabeleireiro, como `profile_pics/<id>/`.
- O nome original do arquivo não entra na chave.

### Persistência: tabela própria

- O usuário perguntou se uma tabela nova é mais performática que um campo JSONB.
- A decisão é a tabela `GalleryPhoto`, com FK para `Hairdresser`. Os motivos estão no `design.md` e no AD-013:
  - o `WebPImageField` é campo de modelo;
  - o insert por foto não perde escrita concorrente;
  - a remoção é por PK;
  - a leitura de até 30 linhas por índice custa o mesmo que ler um JSONB.

### Limites

- No máximo 30 fotos por cabeleireiro, garantido no backend mesmo com envios em paralelo.
- No máximo 5 MB por foto antes da conversão, o mesmo limite da foto de perfil.

### Gestão no app

- O card "Minha galeria" no perfil do cabeleireiro, ao lado de "Meus horários de atendimento" e "Meus serviços", abre uma tela própria.
- A tela própria é uma grade com o botão "Adicionar fotos", o contador "N/30" e um botão de remover em cada foto, com modal de confirmação.
- O perfil do cabeleireiro mostra a mesma faixa horizontal que o cliente vê.

### Envio de várias fotos

- O seletor aceita várias fotos (`allowsMultipleSelection`), limitadas às vagas restantes.
- O app manda uma requisição por foto, em sequência, mostra o progresso e informa quantas falharam.

### Agent's Discretion

- Ordem da galeria: da mais nova para a mais antiga.
- Envio em sequência, e não em paralelo: evita disputar o lock do limite e mantém o progresso legível.
- Visualização em tela cheia: um `Modal` com a imagem em `contain` e um botão de fechar. Sem zoom nem deslizar entre fotos.
- Grade de 3 colunas com fotos quadradas (`cover`).
- Local da tela: `app/(app)/hairdresser/profile/gallery.tsx`, na pilha do perfil, para manter a aba Perfil ativa.
- O seed sobe de 0 a 6 fotos por cabeleireiro pelo modelo, a partir das imagens que hoje ficam em `frontend-mobile/assets/hairdressers/gallery/`, e essa pasta sai do app.
- Slug novo `gallery-full` (409), no lugar de reaproveitar `validation-error`. A galeria cheia é um conflito com o estado do recurso, e não um dado inválido, como `availability-exists` e `review-exists`.

### Declined / Undiscussed Gray Areas → Assumptions

Ficaram registradas como assumptions no spec, com `Confirmed? n`:
- a ordem;
- a galeria vazia escondida no perfil;
- o cabeleireiro pendente;
- o modal de remoção;
- a qualidade 0.5 no seletor;
- a resposta do `POST`;
- o seed.

---

## Specific References

- A seção comentada do perfil público (`frontend-mobile/app/(app)/customer/hairdresser-reservation/[id].tsx:78-86`) e os estilos `gallery` e `galleryImage` (`styles/customer/reservation/styles/HairdresserProfileReservationStyle.ts:55-63`) são o ponto de partida visual da faixa: miniaturas de 100 × 100 com bordas arredondadas.
- A foto de perfil (#120) é a referência de fluxo:
  - `ProfilePictureView` (`backend/users/views.py:840`);
  - `uploadProfilePicture` (`frontend-mobile/services/account.service.ts:33`);
  - `useProfilePicture` (`frontend-mobile/hooks/accountHooks/useProfilePicture.ts`).

---

## Deferred Ideas

- Legenda e reordenação das fotos.
- Zoom e deslizar entre as fotos na tela cheia.
- Moderação das imagens enviadas.
