# Radar de Ofertas

MVP de automação de divulgação de ofertas de marketplace em canais de WhatsApp e Telegram.

## Problema

A afiliada de marketplace que trabalha sozinha gasta entre um e quinze minutos por
divulgação, cerca de três vezes ao dia, em trabalho manual: garimpar preço, gerar link de
afiliado, conferir se o link funciona, publicar em cada grupo e tentar lembrar o que já foi
publicado. O gargalo não é a demanda nem a capacidade de achar boas ofertas: é o custo de
execução. A repetição só é descoberta pelo cliente, e o link quebrado destrói a
credibilidade do canal.

## Solução

O Radar de Ofertas automatiza a coleta, a geração de link de afiliado, a verificação de
validade e o registro do que foi publicado. A decisão de publicar continua com a usuária;
o que a máquina assume é o trabalho repetitivo e a memória que hoje não existe.

O diferencial é a **regra de não repetir**: a mesma oferta nunca é publicada duas vezes no
mesmo canal. Essa regra é garantida por restrição de unicidade no banco, e não por
conferência no código, porque duas execuções simultâneas do agendador passariam juntas
pela mesma conferência.

## Arquitetura

Monolito em camadas, com quatro camadas e uma fronteira de contratos entre elas:

| Camada | Responsabilidade |
|---|---|
| Apresentação | Telas renderizadas no servidor (Jinja2), responsivas, para celular |
| Aplicação | Casos de uso: coletar, aprovar, gerar link, validar, publicar, consultar |
| Domínio | Regras: unicidade de oferta por canal, validação de link como pré-condição |
| Infraestrutura | Adaptadores de loja, gerador de link, validador, publicador, repositório |

## Stack

Python 3.11 · FastAPI · Pydantic · SQLAlchemy · APScheduler · httpx · Jinja2 ·
PostgreSQL em produção, SQLite em desenvolvimento e testes

## Entidades

- **loja** — marketplace de origem, com padrão de link por origem
- **oferta** — produto coletado, com preço e chave normalizada que evita duplicata
- **canal** — destino da divulgação (WhatsApp, Telegram)
- **publicacao** — registro do que foi enviado, quando e com qual link

## Como rodar

```bash
uv sync --all-extras
uv run uvicorn app.main:app --reload
```

## Testes

```bash
uv run pytest -v
```

## Integração contínua

O pipeline em `.github/workflows/ci.yml` roda análise estática e a suíte de testes em
todo push e em todo pull request contra a branch principal.

## Contexto acadêmico

Projeto desenvolvido para a Experiência Prática da disciplina de Projeto de Software,
conectado ao ODS 8 (Trabalho Decente e Crescimento Econômico), meta 8.3.
