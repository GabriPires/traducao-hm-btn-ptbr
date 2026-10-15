# Harvest Moon: Back to Nature — Tradução PT-BR

Tradução de fã para português do Brasil de *Harvest Moon: Back to Nature* (PlayStation,
2000), feita do zero, com ferramentas próprias e documentação aberta.

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-orange)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Plataforma](https://img.shields.io/badge/plataforma-PlayStation-lightgrey)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-green)

> **English:** Brazilian Portuguese fan translation of *Harvest Moon: Back to Nature*
> (PS1, USA). This repository contains only original tools, documentation and the
> translation; no game data is distributed.

## Sobre o projeto

- **Tradução completa:** a meta é um jogo jogável do início ao fim em português,
  incluindo diálogos, menus, itens e gráficos com texto.
- **Do zero:** tradução própria, sem reaproveitar trabalhos anteriores.
- **Aberto e documentado:** cada descoberta sobre os formatos do jogo vira um documento
  em [`docs/`](docs/), para que outros projetos também possam aproveitar.
- **Ferramentas simples:** Python puro, sem dependências externas, com testes
  automatizados.

## Progresso

| Etapa | Status |
|---|---|
| Ferramentas de extração e remontagem do disco | ✅ Concluído |
| Mapeamento dos diálogos (6.011 falas) | ✅ Concluído |
| Prova de conceito no emulador | ✅ Concluído |
| Fonte com acentos e cedilha | ✅ Concluído |
| Caixas de mensagem: falas, placas, cartas, descrições de itens, ajuda, TV (6.011 textos) | ✅ Traduzidos (5.873; os outros 138 são vazios, "Dummy" ou iguais em português) |
| Textos fixos do executável: nomes de menus, comidas, itens de loja, memory card, dias da semana e estações (387 textos) | ✅ Traduzidos (lojas e data do diário a confirmar no jogo) |
| Textos dos minigames (16 textos) | ✅ Traduzidos |
| Gráficos com texto (título, menus) | ⏳ Pendente |
| Testes do início ao fim e lançamento | ⏳ Pendente |

## Como jogar

O patch ainda **não foi lançado**. Quando estiver pronto, o processo será:

1. Tenha sua própria cópia do jogo, na versão compatível (abaixo).
2. Confira o checksum da sua imagem.
3. Aplique o patch `.xdelta` com uma ferramenta como o
   [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/) (no navegador) ou o `xdelta3`.
4. Abra a imagem traduzida no emulador de sua preferência. Os testes são feitos no
   [DuckStation](https://github.com/stenzek/duckstation).

### Versão compatível

Somente a versão americana (NTSC-U), em imagem BIN/CUE de faixa única:

| | |
|---|---|
| Serial | SLUS-01115 |
| Formato | MODE2/2352, faixa única |
| Tamanho | 213.954.384 bytes |
| CRC32 | `b0e8f078` |
| MD5 | `424f9fbda58e95f597e39b4bdde239b1` |
| SHA-1 | `cb26381fa1336bdd15f07469e59f1143ccf37b03` |

## Para desenvolvedores

### Requisitos

- Python 3.10 ou mais recente
- Sua própria imagem do jogo (versão compatível acima)

### Primeiros passos

```sh
# coloque sua imagem na raiz do projeto como HARVESTMOON.iso
# (ou indique outro caminho com HMBTN_ISO=/caminho/jogo.bin)

python3 tools/hm.py info      # confere a imagem e lista os arquivos do disco
python3 tools/hm.py extract   # extrai os arquivos para build/
python3 tools/hm.py dump      # exporta os diálogos originais para build/script/
python3 tools/hm.py check     # confere as traduções contra o original e as regras do jogo
python3 tools/hm.py font      # prévia da fonte com os acentos em build/fonte.png
python3 tools/hm.py build     # gera build/HARVESTMOON-PTBR.bin (+ .cue) com a tradução

python3 -m unittest discover tests
```

Também há `find` (procura uma fala) e `peek` (decodifica texto numa posição).
Use `python3 tools/hm.py --help` para ver todos os comandos.

### Como a tradução é organizada

O texto original do jogo **nunca** é versionado: ele é extraído localmente, da sua
cópia, para `build/script/`. O repositório guarda só a tradução, em
`translation/NN.json`, ligando cada fala pelo seu identificador:

```json
{
  "03-1899": "E entao, o que achou?\nEsta era a fazenda do seu avo…"
}
```

Quem traduz segue o [guia de tradução](docs/05-guia-de-traducao.md). Falas sem
tradução continuam no idioma original. O comando `check` confere cada
tradução contra o original: códigos de controle, caracteres permitidos, tamanho das
linhas e das páginas. O `build` aplica as mesmas regras, grava cada fala no lugar dela
no disco e recalcula os códigos de correção de erro dos setores alterados.

### Estrutura

```
tools/hm.py        linha de comando
tools/hmbtn/       biblioteca: imagem de disco, EDC/ECC, pacote A_FILE, tabela de texto,
                   diálogos, regras da tradução, fonte e acentos
tables/hmbtn.tbl   tabela de caracteres do jogo
tables/personagens.tsv  quem é cada retrato (personagem e gênero)
translation/       a tradução: um JSON por subarquivo de diálogos, exe.json (executável)
                   e overlays.json (minigames)
prompts/           instruções para agentes de IA que ajudam na tradução
docs/              documentação técnica
tests/             testes automatizados
```

### Documentação técnica

1. [O disco e o texto](docs/01-disco-e-texto.md): estrutura da imagem, o pacote
   `A_FILE`, a codificação de 16 bits do texto
2. [Os diálogos](docs/02-dialogos.md): registros de 8 KB, limites, códigos de controle
3. [Montando a imagem traduzida](docs/03-montagem.md): gravação no lugar, EDC/ECC,
   prova de conceito
4. [A fonte e os acentos](docs/04-fonte.md): onde a fonte fica, a compressão RLE, as
   letras acentuadas e a medida da caixa de diálogo
5. [Guia de tradução](docs/05-guia-de-traducao.md): regras, estilo, quem fala e glossário
6. [Textos do executável e dos minigames](docs/06-textos-do-executavel.md): menus,
   itens e minigames, como o jogo os acha e por que são traduzidos no mesmo tamanho

## Licença

As ferramentas, os testes e a documentação deste repositório estão sob a
[licença MIT](LICENSE).

Os textos da tradução, em `translation/`, não estão cobertos pela licença MIT, por
serem obra derivada do jogo original.

## Aviso legal

Este é um projeto de fã, gratuito e sem fins lucrativos, sem qualquer afiliação com
Natsume Inc., Victor Interactive Software Inc. ou seus sucessores. *Harvest Moon* é
marca registrada da Natsume Inc.; *Harvest Moon: Back to Nature* © 2000 Natsume Inc. /
Victor Interactive Software Inc.

Este repositório não contém nem distribui o jogo ou qualquer outro material protegido
por direitos autorais de terceiros. Para usar o patch, é necessário possuir uma cópia
original do jogo.
