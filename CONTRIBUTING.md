# Como contribuir

Projeto individual da Experiência Prática, mas conduzido com o processo que se usaria em
equipe. As regras abaixo existem para que o histórico do repositório conte o que
aconteceu e por quê.

## Branches

Nada é commitado direto na `master`. Cada mudança nasce em uma branch com prefixo de tipo:

- `feat/` — funcionalidade nova
- `fix/` — correção de defeito
- `test/` — teste que faltava ou que precisou mudar
- `docs/` — documentação
- `ci/` — pipeline
- `refactor/` — reorganização sem mudança de comportamento

O nome usa hífen e descreve o efeito, não a atividade: `feat/health-e-cobertura-validador`,
não `feat/trabalho-de-hoje`.

## Commits

Padrão convencional: `tipo(escopo opcional): descrição no imperativo`.

O corpo explica o **porquê**, não o **o quê** — o diff já mostra o quê. Um commit faz uma
coisa. Se a mensagem precisa de "e" para descrever, provavelmente são dois commits.

```
feat(domain): garantir unicidade de publicação por canal no banco

A conferência em código não protege contra duas execuções simultâneas do
agendador, que passariam juntas pela mesma verificação. A restrição de
unicidade resolve no nível que interessa e transforma a corrida em erro de
integridade tratável.
```

## Pull requests

Toda branch entra por PR, mesmo sendo uma pessoa. O valor não é a aprovação de outra
pessoa, é a **leitura do próprio diff antes do merge**, que é quando os erros aparecem.

A PR precisa de:

1. Título no padrão dos commits
2. Descrição com o que mudou, por que mudou e como foi verificado
3. Auto-revisão: comentários no próprio diff apontando o que merece atenção, o que ficou
   de fora e o que poderia ser feito diferente
4. CI verde — `ruff` e `pytest` com cobertura mínima de 80%

## Verificação local antes de abrir a PR

```bash
uv sync --all-extras
uv run ruff check .
uv run pytest -v --cov=app --cov-fail-under=80
```

Se `ruff` ou os testes falharem, a PR não é aberta. Empurrar para o CI para descobrir o
que já se sabia é desperdício.

## O que não entra

- Segredo, token ou senha no código ou no histórico
- Dependência nova sem justificativa na descrição
- Alteração de comportamento escondida em commit de `refactor`
- Supressão de teste com `skip` sem comentário dizendo quando volta
