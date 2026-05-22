# Integrador de Publicações - Agent Instructions

## Projeto
Sistema Django para gestão de publicações de veículos em múltiplas redes sociais.

## Stack
- Python
- Django
- Django ORM/Admin/Forms/Templates
- Cloudflare R2 via Worker
- OpenAI estruturado preparado
- Publishers fake e reais
- JavaScript vanilla nos templates

## Domínio atual
O projeto já possui:
- Vehicle com raw_input
- MediaAsset vinculado a Vehicle, com media_type, file e public_url
- SocialPost vinculado a Vehicle, com post_type: single_image, carousel, video
- PostMedia para mídias escolhidas e ordenadas
- PlatformPost por plataforma
- Review por SocialPost
- PublicationTarget por plataforma
- SocialAccount para tokens/IDs externos
- Upload para R2 funcionando
- IA/fallback estruturado
- Publishers fake e reais
- Tela /posts/create-from-vehicle/
- Tela /posts/<post_id>/review/

## Regras permanentes
- Não recriar arquitetura do zero.
- Não renomear models sem pedir.
- Não remover publisher fake.
- Não quebrar admin.
- Não quebrar R2.
- Não exigir tokens externos durante desenvolvimento.
- Não fazer chamadas reais a OpenAI/Meta/Google/TikTok/YouTube nos testes.
- Manter fallback quando integração externa não estiver configurada.
- Não commitar `.env`, `db.sqlite3`, `vehicle_media/`, `media/`, `node_modules/`.
- Mudanças devem ser incrementais e focadas.
- Preferir services para regra de negócio.
- Validar no backend mesmo quando houver validação no frontend.
- Quando uma integração real não estiver pronta, falhar controladamente com `error_message` útil.

## Comandos de verificação
Rodar ao final de blocos relevantes:

```bash
python manage.py check
python manage.py test
```

## Critério de sucesso
- Fluxo existente continua funcionando.
- Testes passam.
- Usuário consegue cadastrar veículo, subir mídia, criar post, revisar, aprovar e publicar fake.
- Integrações reais devem ficar preparadas sem quebrar fluxo local.
