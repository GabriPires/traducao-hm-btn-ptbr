# CLAUDE.md

Tradução PT-BR de Harvest Moon: Back to Nature (PS1, USA, SLUS-01115), feita do zero.
Também é um projeto de aprendizado de romhacking.

## Regras

- `HARVESTMOON.iso` (raiz) é a imagem original: **somente leitura**. Nunca alterar, mover ou sobrescrever.
- Nada derivado do disco entra no git (imagens, `build/`, arquivos extraídos). Distribuição só via patch `.xdelta`.
- Docs, comentários e mensagens das ferramentas em pt-BR; identificadores de código em inglês.
- Ferramentas em Python 3 só com biblioteca padrão (Pillow do sistema está disponível se for preciso para gráficos).
- Ao explicar conceitos de baixo nível, usar analogias de desenvolvimento web.
- Descobertas sobre formatos vão para `docs/NN-*.md`, separando o que é confirmado do que é hipótese **(?)**.

## Comandos

```sh
python3 tools/hm.py info | cue | extract
python3 tools/hm.py find "texto em inglês"
python3 tools/hm.py peek <subarquivo> <offset>
python3 -m unittest discover tests
```

## Onde está o quê

- `tools/hmbtn/disc.py`: setores 2352/ISO9660 · `afile.py`: A_FILE.BIN/HDT · `table.py`: tabela de texto
- `tables/hmbtn.tbl`: tabela de caracteres
- `docs/01-disco-e-texto.md`: estrutura do disco, subarquivos, codificação do texto
