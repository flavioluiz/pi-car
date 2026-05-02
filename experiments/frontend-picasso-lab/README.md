# PiCASSO Frontend Lab

Area isolada para testar novas interfaces do produto `PiCASSO` sem alterar o frontend atual.

## Como visualizar

Na raiz do projeto:

```bash
python3 -m http.server 8765
```

Depois abra:

`http://localhost:8765/experiments/frontend-picasso-lab/`

## Estrutura

- `index.html`: galeria com os conceitos
- `concept-cockpit.html`: visual mais dramatico, orientado a condução
- `concept-orbit.html`: dashboard modular e mais informacional
- `concept-pulse.html`: interface mais limpa, com foco em musica e navegação
- `styles.css`: estilos compartilhados

## Observacao

Os conceitos usam os logos em `../../logos/` e sao totalmente independentes do codigo existente em `frontend/`.
