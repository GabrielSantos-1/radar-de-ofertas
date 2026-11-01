## O que muda

<!-- Uma frase. Se precisar de duas, provavelmente são duas PRs. -->

## Por que muda

<!-- O problema que existia. O que acontecia antes e o que passa a acontecer. -->

## Como foi verificado

<!-- Comandos rodados e resultado. Não escrever "testado" sem dizer como. -->

```
uv run ruff check .
uv run pytest -v --cov=app --cov-fail-under=80
```

## Auto-revisão

<!-- Leitura do próprio diff. O que merece atenção do revisor,
     o que ficou de fora de propósito, o que poderia ser melhor. -->

- [ ] Li o diff completo antes de abrir
- [ ] Cada commit faz uma coisa e a mensagem explica o porquê
- [ ] Nenhum segredo, token ou dado real no código
- [ ] Cobertura de teste não caiu
- [ ] Documentação atualizada quando o comportamento mudou

## Fora de escopo

<!-- O que foi notado e deliberadamente não foi feito aqui. -->
