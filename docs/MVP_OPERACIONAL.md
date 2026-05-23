# MVP Operacional

## Visao geral
O sistema permite cadastrar veiculos, subir midias, criar publicacoes, revisar textos, aprovar o conteudo e preparar a publicacao em multiplas plataformas.

## Fluxo principal sem tokens reais
1. Abrir `/`.
2. Criar um veiculo.
3. Subir as midias do veiculo.
4. Abrir o detalhe do veiculo.
5. Criar uma publicacao a partir do veiculo.
6. Selecionar o formato da publicacao.
7. Selecionar as plataformas de destino.
8. Selecionar e ordenar as midias vinculadas ao post.
9. Revisar o texto gerado.
10. Aprovar a revisao.
11. Ver os `PublicationTarget` em `/publications/`.
12. Consultar o readiness antes de tentar publicacao real.
13. Usar publish fake quando o objetivo for validar o fluxo local.

## Fluxo de configuracao de integracoes
Use `/integrations/` para abrir a area de configuracao das contas sociais.

Cada plataforma exige os seguintes dados base:
- `account_name`
- `status`
- `external_account_id`
- `access_token`
- `token_expires_at` quando existir expiracao
- `metadata` quando houver dados extras
- `page_id` apenas quando a integracao usar esse identificador

Plataformas:
- Instagram: exige conta profissional conectada a uma pagina do Facebook e `Instagram Business Account ID`.
- Facebook: exige `Facebook Page ID` e `Page Access Token`.
- Google Business: exige `accounts/{accountId}/locations/{locationId}` e token OAuth com permissao de gestao.
- YouTube: exige `channel_id` e OAuth com permissao de upload.
- TikTok: exige `open_id/creator id` e user access token com Content Posting API.

## System check
Use `/system-check/` para validar o estado geral do ambiente.

O painel consolida:
- R2
- OpenAI
- integracoes sociais
- prontidao para publicacao real

## O que ainda nao testar agora
- OpenAI real
- tokens reais
- publicacao real externa
- OAuth real

## Ordem futura de testes reais
1. Instagram `single_image`
2. Facebook `single_image`
3. Instagram `carousel`
4. Instagram `video` / Reels
5. Google Business `single_image`
6. YouTube `video`
7. TikTok `video`

## Regras de Git
- nao commitar `.env`
- nao commitar `db.sqlite3`
- nao commitar `vehicle_media/`
- nao commitar `node_modules/`

## Comandos padrao
```bash
python manage.py check
python manage.py test
python manage.py runserver
```
