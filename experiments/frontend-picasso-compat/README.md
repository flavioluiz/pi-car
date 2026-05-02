# PiCASSO Compat Template

Template de frontend em ingles, isolado em `experiments/`, com estrutura mais proxima do frontend atual para facilitar substituicao futura.

## Objetivo

Simular a estrutura real do produto `PiCASSO` com ids, classes e organizacao mais compativeis com o frontend atual:

- Home
- Music
- Navigation
- Vehicle
- SDR Radio
- Settings

Com paginas clicaveis, subtabs e suporte a themes.

## Themes

Por enquanto, a unica configuracao exposta e `Themes`, com tres opcoes:

- `PiCASSO Red`
- `Signal Cyan`
- `Amber Dusk`

## Como abrir

Na raiz do projeto:

```bash
python3 -m http.server 8765
```

Abra:

`http://localhost:8765/experiments/frontend-picasso-compat/`
