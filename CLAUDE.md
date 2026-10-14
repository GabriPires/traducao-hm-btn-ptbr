# CLAUDE.md

Tradução PT-BR de Harvest Moon: Back to Nature (PS1, USA, SLUS-01115), feita do zero.
Também é um projeto de aprendizado de romhacking.

## Regras

- `HARVESTMOON.iso` (raiz) é a imagem original: **somente leitura**. Nunca alterar, mover ou sobrescrever.
- Nada derivado do disco entra no git (imagens, `build/`, arquivos extraídos). Distribuição só via patch `.xdelta`.
- O repositório é **público**: o texto original em inglês nunca é versionado. O dump fica em `build/script/` e o git só recebe `translation/*.json` (`{"id": "texto pt"}`). Não colar trechos do script original em docs/commits; nos docs, preferir exemplos inventados.
- Nada sobre BIOS, caminhos locais ou dados pessoais nos arquivos versionados.
- Docs, comentários e mensagens das ferramentas em pt-BR; identificadores de código em inglês.
- Ferramentas em Python 3 só com biblioteca padrão (Pillow do sistema está disponível se for preciso para gráficos).
- Ao explicar conceitos de baixo nível, usar analogias de desenvolvimento web.
- Descobertas sobre formatos vão para `docs/NN-*.md`, separando o que é confirmado do que é hipótese **(?)**.

## Comandos

```sh
python3 tools/hm.py info | cue | extract | dump | build
python3 tools/hm.py find "texto em inglês"
python3 tools/hm.py peek <subarquivo> <offset>
python3 -m unittest discover tests
```

Testes no emulador: abrir `build/HARVESTMOON-PTBR.cue` no DuckStation.

## Onde está o quê

- `tools/hmbtn/disc.py`: setores 2352/ISO9660 · `afile.py`: A_FILE.BIN/HDT · `table.py`: tabela de texto
- `tables/hmbtn.tbl`: tabela de caracteres
- `docs/01-disco-e-texto.md`: estrutura do disco, subarquivos, codificação do texto
- `docs/02-dialogos.md`: registros de 8 KB das falas, limites, códigos de controle, formato do script
- `docs/03-montagem.md`: como o `build` gera a imagem, EDC/ECC, prova de conceito
- `build/script/NN.json` (local): originais (`id`, `prefix`, `en`) · `translation/NN.json` (git): `{id: pt}`
- `build` gera `build/HARVESTMOON-PTBR.bin`: grava as falas no lugar e recalcula EDC/ECC só dos setores alterados
