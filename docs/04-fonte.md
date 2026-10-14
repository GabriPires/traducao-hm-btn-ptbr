# 04 · A fonte e os acentos

Fase 3. Ferramentas: `tools/hmbtn/font.py`, `tools/hmbtn/accents.py`,
`python3 tools/hm.py font` (prévia) e o `build`, que aplica a fonte nova.

## Como a fonte foi encontrada

Procurar os desenhos das letras direto no disco não deu resultado. Então fomos pelo
caminho inverso: com o jogo parado numa fala, salvamos um *save state* sem compressão
no DuckStation (`SaveStateCompression = Uncompressed`). Ele contém uma cópia exata da
RAM e da memória de vídeo (VRAM) do console naquele instante.

- A **RAM** foi localizada procurando um trecho do código do executável, que sempre
  fica no mesmo endereço (`0x80010000`).
- A **VRAM** foi localizada procurando a paleta do retrato do prefeito, que o jogo
  copia para a linha 490.

Na VRAM a fonte aparece como uma folha de letras na posição `(896, 0)`. Com os bytes
exatos da folha em mãos, procuramos no código um bloco com esse destino e o achamos
no começo do subarquivo 00 do `A_FILE`, comprimido.

> Analogia web: é como achar um asset minificado olhando o que o navegador já
> renderizou no DevTools e depois procurar a origem no bundle.

## A folha

| | |
|---|---|
| Posição na VRAM | `x = 896, y = 0`, 32×120 unidades de 16 bits |
| Tamanho | 128×120 pixels, 4 bits por pixel |
| Grade | 16 caracteres por linha, cada um com 8×12 pixels |
| Código do caractere | a posição na grade: `0x00` = A, `0x10` = Q, `0x20` = a... |
| Pixels | intensidade da tinta, suavizada: `0` = fundo, `1` = mais forte, `9` = mais fraca |

É uma fonte **monoespaçada**: toda letra avança 8 pixels. Pontuação e símbolos,
confirmados pelo desenho: `; + / ~ & ♥ %`, os botões ○ × △ □ (`006D`–`0070`), setas
(`0087`–`008A`), números em caixinhas (`0079`–`007E`). `0064` é outra versão das
reticências, no alto da linha.

## Pacotes de imagem e compressão

O jogo guarda imagens em pacotes que listam cópias para a VRAM:

```
u16 0x100D, u16 quantidade de blocos
bloco: u32 (tipo << 24 | tamanho), u16 x, u16 y, u16 largura, u16 altura, dados
       (o próximo bloco começa alinhado a 4 bytes)
```

Tipo 6 são dados crus (paletas); tipo 0 são dados comprimidos com **RLE**:

| Byte de comando `n` | Significado |
|---|---|
| `0x80`–`0xFF` | copia os próximos `256 − n` bytes como estão |
| `0x01`–`0x7F` | repete o próximo byte `n` vezes |

O formato foi deduzido comparando a entrada comprimida com a folha já descomprimida
da VRAM. A descompressão reproduz a VRAM byte a byte. O primeiro pacote do
subarquivo 00 tem 5 paletas, 4 imagens pequenas e, por último, a fonte.

## Onde os acentos entraram

A folha tinha espaços vazios e letras alemãs que o jogo americano não usa:

| Códigos | Antes | Agora |
|---|---|---|
| `001A`, `001C`, `001D` | vazio | `Â Ã Õ` |
| `003A`–`003F` | vazio | `á à â ã é ê` |
| `004A`–`004F` | vazio | `í ó ô õ ú ç` |
| `0057`–`005D` | `Ä Ö Ü ä ö ü ß` | `É À Á Ó Ç Ê Í` |
| `005E`, `005F` | vazio | `Ú Ô` |

`001B` e `001E` também estão vazios, mas aparecem no texto original em volta de opções
de menu. Podem ter alguma função especial no jogo, por isso ficaram de fora.

As letras novas **não são desenhadas do zero e não ficam no repositório**: o `build`
pega a letra base da fonte do próprio disco e acrescenta a marca, que é desenho nosso
(`accents.py`). O estilo segue o que o próprio jogo fez nas letras alemãs:

- **minúsculas:** corpo intacto, acento nas linhas 1 e 2 (no `í`, o pingo do `i` sai);
- **maiúsculas:** a letra perde duas linhas iguais do meio e o acento entra no topo;
- **cedilha:** embaixo da letra, na linha 11.

## O limite de espaço

O pacote da fonte ocupa os 4 primeiros setores do subarquivo 00. Depois dele, até o
fim do quarto setor (`0x2000`), só havia zeros: 1288 bytes de folga. Como o CD é lido
em setores inteiros, a fonte pode crescer até esse limite sem mexer em mais nada.

| | Bytes |
|---|---|
| Pacote original | 6904 |
| Pacote com os 24 acentos | 7056 |
| Limite | 8192 |

Nosso compressor RLE é mais eficiente que o original (a mesma folha fica com 5012
bytes em vez de 5546), o que compensa boa parte dos desenhos novos. O `build` recusa
gerar a imagem se o pacote passar do limite.

## A caixa de diálogo, medida na tela

| | |
|---|---|
| Área interna da caixa | `x = 28` a `290` |
| Início do texto | `x = 30` |
| Largura de cada letra | 8 pixels |
| Linhas por página | 4 |

Cabem 32 letras por linha, mas na última linha da página fica a setinha ▼ de "próxima
página", por volta de `x = 282`. Por isso o limite usado pelo `check` é **31**.
Os menus usam a mesma fonte.
