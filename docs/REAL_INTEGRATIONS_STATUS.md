# Real Integrations Status

| Plataforma | O que já está implementado | Credenciais necessárias | Está pronto para testar com token? | Primeiro teste recomendado | Bloqueios conhecidos |
| --- | --- | --- | --- | --- | --- |
| OpenAI | `OPENAI_POST_AI_ENABLED` usa OpenAI quando a flag está ativa e a API key existe; se falhar, cai no fallback. | `OPENAI_API_KEY`, `OPENAI_POST_AI_ENABLED`, `OPENAI_MODEL` | Sim, com fallback preservado | Validar `single_image` e `carousel` com a flag ligada | Dependência externa e chave ausente; se falhar, cai para fallback |
| Instagram | `InstagramRealPublisher` está implementado para `single_image`, `carousel` e `video/Reels`, usando `public_url` e `external_account_id`. | `Instagram Business Account ID` + Meta access token | Sim | `single_image` primeiro | Erros de Graph API, mídia sem `public_url`, conta não conectada |
| Facebook | `FacebookRealPublisher` já publica foto única em Page usando `/\{page_id\}/photos` com `url`, `caption`, `published=true` e `access_token`. | `Facebook Page ID` + Page Access Token | Sim, para `single_image` | `single_image` | `carousel` e `video` continuam não suportados no publisher real |
| Google Business | `GoogleBusinessRealPublisher` já publica Local Post com imagem principal; `carousel` usa apenas a primeira imagem. | `accounts/{accountId}/locations/{locationId}` + OAuth token com `business.manage` | Sim, para `single_image`; parcial para `carousel` | `single_image` primeiro | `video` não suportado; `carousel` usa apenas a primeira imagem |
| YouTube | `YouTubeRealPublisher` faz upload real de vídeo via `videos.insert` com mídia local ou download temporário seguro. | OAuth access token + vídeo local ou `public_url`; `external_account_id` é opcional para identificação | Sim, para `video` | `video` primeiro, com `privacyStatus=private` | `single_image` e `carousel` não são suportados |
| TikTok | `TikTokRealPublisher` faz init real de vídeo via Content Posting API com `PULL_FROM_URL`. | `open_id/creator id` + TikTok user token + `metadata.source=PULL_FROM_URL` + scopes `video.publish`/`video.upload` | Sim, para `video` | `video` primeiro, com metadata mínima configurada | Requer app TikTok, scopes de posting, vídeo público/verificado e init pode retornar apenas `publish_id` |

## Leitura prática
- Instagram é a única plataforma já pronta para um teste real com token.
- Facebook e Google Business estão prontos para `single_image`; YouTube está pronto para `video`; TikTok está pronto para `video` com metadata mínima configurada e app autorizado.
- Nenhuma tela deve sugerir `ready` para uma plataforma cujo publisher real ainda esteja bloqueado ou incompleto.
