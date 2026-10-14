# Harvest Moon: Back to Nature — Tradução PT-BR

Patch de tradução para português do Brasil de *Harvest Moon: Back to Nature* (PlayStation,
versão americana), feito do zero. Objetivo: jogável do início ao fim, em emulador.

## Imagem suportada

Só a versão americana. Confira antes de qualquer coisa:

| | |
|---|---|
| Serial | SLUS-01115 |
| Formato | imagem crua MODE2/2352 (o arquivo se chama `.iso`, mas é um `.bin`) |
| Tamanho | 213.954.384 bytes |
| SHA-1 | `cb26381fa1336bdd15f07469e59f1143ccf37b03` |
| MD5 | `424f9fbda58e95f597e39b4bdde239b1` |
| CRC32 | `b0e8f078` |

A imagem do jogo **nunca** entra no repositório, nem o texto original em inglês extraído
dela: aqui ficam só as ferramentas e a tradução. O resultado final é distribuído como
patch (`.xdelta`), e quem for jogar aplica o patch na própria cópia.

## Começando

Requisitos: Python 3.10+ (só biblioteca padrão por enquanto) e git.

```sh
# coloque sua imagem na raiz do projeto como HARVESTMOON.iso
# (ou aponte outro caminho com HMBTN_ISO=/caminho/jogo.bin)

python3 tools/hm.py info      # confere o disco e lista os arquivos
python3 tools/hm.py cue       # cria HARVESTMOON.cue para abrir no emulador
python3 tools/hm.py extract   # extrai tudo para build/ (≈300 MB)
python3 tools/hm.py dump      # exporta os diálogos originais para build/script/ (local)
python3 tools/hm.py build     # aplica translation/*.json -> build/HARVESTMOON-PTBR.bin

python3 tools/hm.py find "Good morning"   # onde está essa fala?
python3 tools/hm.py peek 2 0xEB80A        # decodifica texto a partir de uma posição

python3 -m unittest discover tests        # testes
```

## Estrutura

```
tools/hm.py          linha de comando (info, cue, extract, dump, build, find, peek)
tools/hmbtn/         biblioteca: disco (disc.py), EDC/ECC dos setores (ecc.py), pacote
                     A_FILE (afile.py), tabela (table.py), registros de diálogo (dialog.py)
translation/         a tradução: {"id da fala": "texto em português"}, um JSON por subarquivo
tables/hmbtn.tbl     tabela de caracteres do jogo (valor de 16 bits -> texto)
docs/                o que já descobrimos sobre o jogo, em ordem
tests/               testes automatizados
build/               (ignorado) arquivos extraídos e gerados
```

## Emulador

Os testes são feitos no [DuckStation](https://github.com/stenzek/duckstation), abrindo o
`.cue` gerado por `python3 tools/hm.py cue`.

## Andamento

- [x] **Fase 0 · Setup**: estrutura, leitura do disco, extração, tabela de caracteres, jogo rodando no DuckStation
- [ ] **Fase 1 · Extração do texto**: diálogos (6011 falas) ✅ · menus, itens e minigames (executável e overlays) ⏳
- [x] **Fase 2 · Prova de conceito**: 5 falas da abertura traduzidas, aparecendo no emulador
- [ ] **Fase 3 · Fonte**: acentos e cedilha
- [ ] **Fase 4 · Tradução**: script inteiro em PT-BR
- [ ] **Fase 5 · Gráficos**: menus, título e imagens com texto
- [ ] **Fase 6 · Testes e lançamento**: jogar do início ao fim, gerar o patch
