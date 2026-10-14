# 02 · Os diálogos

Achados da Fase 1. Ferramentas: `tools/hmbtn/dialog.py` e `python3 tools/hm.py dump`.
O que ainda é hipótese está marcado com **(?)**.

## Registros de 8 KB

Os subarquivos **02, 03, 04, 05 e 06** do A_FILE são uma sequência de registros, todos
com exatamente 0x2000 bytes (8 KB, 4 setores do CD). Cada registro é **uma fala**:

```
0x0000 ┌──────────────────────────────┐
       │ retrato: ID (4 bytes) + imagem│  ou FF FF FF FF quando a fala não tem retrato
       │   (pode ocupar até 0x1800)    │
0x1800 ├──────────────────────────────┤
       │ texto: valores de 16 bits     │  até 1023 valores + FFFF
       │ ... FFFF 0000 0000 ...        │  o resto é sempre zero
0x2000 └──────────────────────────────┘
```

| Subarquivo | Registros | O que aparece numa amostra aleatória |
|---|---|---|
| 02 | 1850 | conversas com moradores (aniversários, clima, dia a dia) |
| 03 | 2061 | conversas e pensamentos do protagonista |
| 04 | 651 | lojas, avisos, escolhas, livros |
| 05 | 1393 | descrições de itens, programas de TV (os textos mais longos) |
| 06 | 56 | festivais e minigames (corrida de cães, regras) |

Todos os 6011 registros têm um único FFFF no setor de texto e nada depois dele.

> Analogia web: é como uma tabela de banco de dados com linhas de tamanho fixo. Para
> achar a linha 117 o jogo calcula `117 × 0x2000` e lê dali. Não precisa de índice.

### Consequência: dá para traduzir sem mexer em ponteiros

Como cada fala tem seu espaço reservado, o texto traduzido é gravado **no mesmo
lugar**. Nada muda de posição, então nenhum ponteiro precisa ser corrigido.
Confirmado na Fase 2: trocamos falas no lugar e o jogo mostrou o texto novo sem
problemas ([03-montagem.md](03-montagem.md)).

### Limites

- **Por fala:** 1023 valores (cada letra, espaço, quebra ou código conta 1). No inglês,
  a mediana é 71, 90% ficam abaixo de 191 e 99% abaixo de 705. Os maiores (1023, no
  limite exato) são programas de TV no subarquivo 05, como `05-0610`, `05-0390` e
  `05-0374`. Em português esses vão precisar de texto mais enxuto.
- **Por linha:** no inglês quase todas têm até 31 caracteres (raramente 32 ou 33).
  Medindo a caixa na tela (Fase 3, [04-fonte.md](04-fonte.md)), o limite é
  **31 caracteres por linha**.
- **Por página:** a caixa de diálogo mostra 4 linhas.

## Códigos de controle

Cada fala começa com um **prefixo** de códigos, por exemplo
`{0FE4}{0FF7}{0FF4}{0FF5}{0E2E}`. O exportador separa o prefixo do texto.

| Código | Significado |
|---|---|
| `{0FFC}{0FFB}` | Espera o botão e começa página nova. `0FFC` = esperar, `0FFB` = limpar a caixa |
| `{0Fxx}{0FF7}…` | No começo da página: `0Fxx` é o **retrato de quem fala** (cada personagem tem uma faixa de códigos, uma por expressão; ver [`tables/personagens.tsv`](../tables/personagens.tsv)). O código depois de `0FF7`, quando existe, é outro retrato da cena **(?)** |
| `0FF4`, `0FF5` | Quase sempre juntos no prefixo: abrir a janela? **(?)** |
| `0E2A`–`0E2F` | Último código do prefixo: tipo ou posição da caixa? **(?)** |
| `0FF1` | Começa os programas de TV e textos "de tela cheia" **(?)** |
| `0FF3` | Prefixo de descrições de itens e avisos do sistema **(?)** |
| `0FF6` | Prefixo de falas sem retrato, como pensamentos do protagonista **(?)** |
| `0FFA` | Prefixo de menus de escolha (cada opção numa linha) **(?)** |
| `{jogador}` (`400A`) | Nome do jogador |
| `400D` | Nome da fazenda ("{400D} Farm") **(?)** |
| `4000`, `4001`, `400E`, `400F` | Outros nomes variáveis: cachorro, cavalo, competidores **(?)** |

Símbolos ainda sem desenho conhecido, que aparecem como `{XXXX}` e devem ser mantidos:

| Código | Onde aparece |
|---|---|
| `006D`–`0070` | Antes da palavra "button": ícones dos botões do controle |
| `0071` | Separador entre duas ações de botão |
| `0087`–`008A` | Ao lado de nomes de lugares no mapa: setas? |
| `0082`–`0085` | Partitura de uma música (notas) |
| `001B`, `001E` | Em volta de opções de menu: aspas? |
| `0065`, `0068`, `0074`, `0077`, `0080` | Marcadores e enfeites (`0080` depois de nomes: "♪"?) |

Também existem 9 falas em que o jogo escreveu `'` + `s` como dois caracteres, em vez do
caractere único `'s`. Nelas o apóstrofo aparece como `{008D}` para preservar os bytes.

## Quem fala

Cada registro com retrato traz a imagem do personagem (80×80, 256 cores, comprimida
com o mesmo RLE da fonte, [04-fonte.md](04-fonte.md)). Renderizando o retrato de cada
um dos 231 códigos foi possível dizer de quem é cada um, e as falas em que os
personagens se apresentam confirmaram a tabela. O resultado está em
[`tables/personagens.tsv`](../tables/personagens.tsv), e o `dump` acrescenta a cada
fala o campo `speakers`, com quem fala em cada página
([05-guia-de-traducao.md](05-guia-de-traducao.md)).

## Original e tradução ficam separados

O repositório é público, então **o texto original em inglês nunca entra no git**.

**Original (local, fora do git):** `python3 tools/hm.py dump` gera
`build/script/NN.json`, com uma entrada por fala:

```json
{
  "id": "02-0117",
  "prefix": "{0FE4}{0FF7}{0FF4}{0FF5}{0E2E}",
  "en": "(texto original da fala, com \n nas quebras de linha)"
}
```

- `id`: subarquivo-registro. É a "chave primária" e nunca muda.
- `prefix`: códigos do início. Não se traduz, o `build` reaplica a partir do disco.
- O exportador confere que codificar `prefix + en` devolve exatamente os bytes do jogo.

**Tradução (versionada):** `translation/NN.json` guarda só `id → texto em português`:

```json
{
  "03-1899": "E entao, o que achou?\nEsta era a fazenda do seu avo…"
}
```

Uma fala ausente ou vazia continua em inglês no jogo. Ferramentas de revisão juntam
os dois arquivos pelo `id`.

Números: **6011 falas, 5641 textos únicos, cerca de 112 mil palavras**. 96 delas são
`Dummy` ou vazias e não aparecem no jogo **(?)**.

## Texto fora dos diálogos (próxima frente)

Menus, nomes de itens, dias da semana, estações, lojas e minigames **não** estão nesses
registros. Eles ficam no executável `SLUS_011.15` (ex.: "Rucksack", "Is this OK?",
nomes das estações) e nos overlays 17, 19, 21, 23 e 25 (corrida, nomes de
competidores, etc.). Lá os textos ficam colados um no outro e são achados por
**ponteiros** no código, então mudar o tamanho exige corrigir esses ponteiros.
