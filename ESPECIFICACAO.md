# Especificação de implementação — Radar de Ofertas

Implemente o MVP completo neste repositório. Todos os arquivos devem ser criados aqui.
Python 3.11, gerenciado com `uv`. Não use Docker.

## Regra geral

Código em inglês (identificadores, nomes de arquivo, mensagens de log).
Mensagens de interface e textos visíveis ao usuário em **português do Brasil**.
Sem comentários supérfluos: comente apenas o porquê de decisões não óbvias.

## Estrutura de diretórios obrigatória

```
app/
  __init__.py
  main.py                 # FastAPI app, monta rotas e templates
  config.py               # Settings via pydantic-settings (DATABASE_URL, etc)
  domain/
    __init__.py
    models.py             # dataclasses/pydantic do domínio
    rules.py              # regras puras: chave normalizada, não-repetição, validação de link
  application/
    __init__.py
    services.py           # casos de uso: coletar, aprovar, gerar_link, validar, publicar, historico
  infrastructure/
    __init__.py
    db.py                 # engine, SessionLocal, Base
    orm.py                # modelos SQLAlchemy
    repositories.py       # repositórios (loja, oferta, canal, publicacao)
    collectors.py         # adaptador de coleta (fake para MVP, interface estável)
    affiliate.py          # gerador de link de afiliado (fake determinístico)
    link_validator.py     # validação de link via httpx (com timeout)
    publishers.py         # publicador WhatsApp/Telegram (fake registrando envio)
  web/
    __init__.py
    routes.py             # rotas Jinja2
    templates/
      base.html
      fila.html
      previa.html
      historico.html
tests/
  __init__.py
  conftest.py
  test_rules.py           # unitários: chave normalizada, não-repetição, validação
  test_services.py        # unitários dos casos de uso com fakes
  test_api.py             # integração: fluxo completo via TestClient
scripts/
  seed.py                 # popula banco com dados fictícios
.github/workflows/ci.yml
pyproject.toml
README.md                 # JÁ EXISTE — não sobrescrever, apenas acrescente seção "Uso" se faltar
```

## Modelo de dados (4 entidades)

**loja**: `id` (UUID str), `nome`, `slug` (único), `url_base`, `padrao_link`, `ativo` (bool), `criado_em`.

**oferta**: `id` (UUID str), `loja_id` (FK), `id_externo`, `id_externo_normalizado`,
`titulo`, `url_produto`, `imagem_url` (nullable), `preco_original` (Numeric 10,2),
`preco_desconto` (Numeric 10,2, nullable), `coletado_em`, `status` (enum: pendente,
aprovada, publicada, descartada), `criado_em`, `atualizado_em`.
Restrição: **UNIQUE (loja_id, id_externo_normalizado)**.

**canal**: `id`, `tipo` (enum: whatsapp, telegram), `nome`, `identificador_externo`,
`ativo`, `limite_caracteres` (nullable), `criado_em`.
Restrição: **UNIQUE (tipo, identificador_externo)**.

**publicacao**: `id`, `oferta_id` (FK), `canal_id` (FK), `link_afiliado`,
`link_validado_em` (nullable), `mensagem_enviada` (nullable), `publicada_em`,
`status_envio` (enum: ok, falha), `erro_detalhe` (nullable), `criado_em`.
Restrição: **UNIQUE (oferta_id, canal_id)** — esta é a garantia central do produto.

## Regras de domínio (funções puras em `app/domain/rules.py`)

1. `normalize_external_id(raw: str) -> str` — remove querystring, fragmento, espaços,
   converte para minúsculas e remove barra final. Ex.: `"MLB123?ref=abc"` → `"mlb123"`.
2. `build_offer_key(loja_id, id_externo_normalizado) -> tuple` — chave natural.
3. `is_link_valid(status_code: int, elapsed_ms: int, max_ms: int) -> bool` — válido se
   200 <= status < 400 e elapsed <= max.
4. `can_publish(oferta, canal, ja_publicada: bool, link_validado: bool) -> tuple[bool, str]`
   — retorna (permitido, motivo). Deve recusar: oferta já publicada no canal,
   link não validado, link inválido, oferta em status descartada.

## Casos de uso (`app/application/services.py`)

- `coletar_ofertas(loja, coletor, repo) -> ColetaResultado` — coleta, normaliza,
  insere apenas inéditas, ignora duplicatas sem erro, retorna contagens.
- `aprovar_oferta(oferta_id, repo) -> Oferta` — só de pendente para aprovada.
- `gerar_e_validar_link(oferta, gerador, validador, repo) -> LinkResultado`
- `publicar(oferta_id, canal_id, publicador, repo) -> Publicacao` — aplica as regras de
  domínio; grava publicação **na mesma transação** que atualiza o status da oferta;
  propaga IntegrityError de unicidade como `OfertaJaPublicadaError`.
- `consultar_historico(canal_id, repo, page, per_page=20) -> list[Publicacao]`

## Interface web (3 telas, Jinja2 + CSS embutido)

- `GET /` → fila de ofertas (paginada, 20 por página), seletor de canal
- `GET /ofertas/{id}/previa` → prévia da mensagem, link validado, botão publicar
- `POST /ofertas/{id}/aprovar` · `POST /ofertas/{id}/publicar`
- `GET /historico?canal_id=` → histórico paginado

Acessibilidade obrigatória nas três telas: `lang="pt-BR"`, link "pular para o conteúdo",
`label` associado a todo campo, alvos de toque de 44 px, contraste mínimo 4,5:1,
foco visível, e status **nunca apenas por cor** (sempre com texto).

## Testes (pytest) — o que precisa existir

`test_rules.py`: normalização da chave, `is_link_valid` nos limites, `can_publish` nos
quatro casos de recusa.

`test_services.py`: coleta ignora duplicata; aprovar oferta inexistente falha; publicar
sem link validado recusa; publicar duas vezes no mesmo canal levanta
`OfertaJaPublicadaError`; publicar em canais diferentes funciona.

`test_api.py` (TestClient, banco SQLite em memória): fluxo completo — coletar, listar na
fila, aprovar, ver prévia, publicar, ver no histórico — e a tentativa de publicar a mesma
oferta de novo recebendo erro tratado.

Cobertura mínima: 80% em `app/`.

## CI (`.github/workflows/ci.yml`)

GitHub Actions, em push para `master` e em pull request. Passos: checkout, setup-python
3.11, instalar uv, `uv sync --all-extras`, `uv run ruff check .`, `uv run pytest -v
--cov=app --cov-fail-under=80`.

## pyproject.toml

Nome `radar-de-ofertas`, requires-python >=3.11. Dependências: fastapi, uvicorn[standard],
sqlalchemy, pydantic, pydantic-settings, jinja2, apscheduler, httpx, python-multipart.
Dev: pytest, pytest-cov, pytest-asyncio, ruff, httpx.

## Aceite

- `uv run pytest -v` passa com cobertura >= 80%
- `uv run ruff check .` sem erros
- `uv run uvicorn app.main:app` sobe e as três telas abrem
- Nenhum segredo no código; configuração por variável de ambiente
- Commit final com mensagem convencional (feat:/test:/ci:)
