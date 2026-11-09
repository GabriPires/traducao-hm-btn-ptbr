# 08 · Gráficos com texto

Alguns textos do jogo não são texto: são imagens. A primeira tela traduzida é a de
título.

## Como a tela de título foi encontrada

1. Um save state na tela de título e outro no menu inicial.
2. A memória de vídeo (VRAM, 1024×512 pontos de 16 bits) foi localizada no save state
   pela folha da fonte, que o nosso build grava em `(896, 0)` (`docs/04-fonte.md`).
3. Desenhada como cores diretas, a VRAM mostra as duas telas do quadro à esquerda e as
   texturas à direita. As texturas com paleta aparecem como ruído colorido, mas dá para
   ver os retângulos: o logotipo em `(576, 256)` e, ao lado e abaixo, os textos do menu.
4. Os pacotes de imagem (formato em `tools/hmbtn/font.py`) dizem para onde cada bloco vai
   na VRAM. Procurando blocos com as dimensões do logotipo, achou-se o pacote da tela de
   título: **subarquivo 00, posição `0x2D1C`, 73 blocos**, logo depois do pacote da fonte.

Tipos de bloco vistos nos pacotes:

| Tipo | Conteúdo |
|---|---|
| 0 | imagem comprimida com RLE (o mesmo da fonte) |
| 1 | imagem comprimida de outro jeito **(?)**; o logotipo usa esse tipo |
| 4 e 5 | imagem crua: o tamanho é largura × altura × 2 |
| 6 | paleta crua |

## Os textos da tela de título

| Bloco | Tamanho | Original | Tradução |
|---|---|---|---|
| 65 | 160×24 pontos | convite para apertar START | PRESSIONE START |
| 66 | 80×24 | opção de jogo novo | INICIAR |
| 67 | 80×24 | opção de continuar | CONTINUAR |

São imagens de 4 bits por pixel com uma paleta comum de 16 cores (bloco 64): o índice 12
é transparente e o 0 é o contorno preto. O logotipo, o da Natsume e as linhas de © ficam
como estão.

O código desenha cada texto num retângulo de tamanho fixo, então a imagem traduzida tem
de ter a mesma largura. As letras têm 14 pontos de altura e cerca de 9,5 de largura, com
traço de 3 pontos (miolo branco e borda cinza) e contorno preto, e se encostam umas nas
outras. "NOVO JOGO" ocupa 82 pontos mesmo apertado: não cabe nos 80, e por isso o menu
diz "INICIAR".

## Como as imagens são montadas (`tools/hmbtn/titlegfx.py`)

Nada das imagens originais vai para o git. Como os acentos da fonte, as palavras são
montadas no `build` a partir das letras das próprias imagens do jogo:

1. **Letras.** Cada imagem original é dividida pelo "miolo" (os 3 tons mais claros, no
   centro dos traços). As letras se encostam pela borda, mas o miolo de uma nunca toca o
   da vizinha. Onde dois miolos se tocam por um ponto (o E e o S de uma palavra), corta-se
   no ponto mais fino.
2. **Dono de cada ponto.** Uma busca em largura parte de todos os pixels de miolo ao mesmo
   tempo, e cada ponto fica com a letra que chega primeiro. Assim a barra de um T que
   avança por cima da letra seguinte continua sendo do T.
3. **Só o corpo.** De cada letra ficam só os cinzas ligados ao próprio miolo, até uma
   linha acima e abaixo dele (a borda do traço). O contorno preto e o halo verde, que no
   original faz a transição para a grama, são descartados. Na primeira versão eles vinham
   junto e, fora do lugar, viraram pontinhos verdes e restos das letras vizinhas na tela.
4. **Palavra e contorno.** As letras são coladas com o espaçamento original (2 pontos entre
   miolos, 8 entre palavras) ou, se a palavra não couber, 1 ponto mais juntas. O miolo usa
   o tom da imagem original (as três variam um pouco no branco). O contorno preto é
   refeito em volta do corpo, sem halo: comparado na tela real, o halo uniforme deixava
   um aro grosso e o contorno simples ficou mais próximo do original.
5. **Letras que não existem.** O J é o U sem a parte de cima da perna esquerda; o V é o U
   com as pernas se aproximando embaixo.

A palavra é centralizada na largura original e comprimida com o RLE. O pacote novo não
pode passar do tamanho do original (fica menor, porque o nosso RLE é mais eficiente).

As palavras ficam em `translation/graficos.json` (ids `gfx-titulo-start`,
`gfx-titulo-novo` e `gfx-titulo-continuar`). O `check` confere se todas as letras
existem e se a palavra cabe; `python3 tools/hm.py titulo` gera `build/titulo.png` com o
original e a tradução lado a lado. A fala da TV que cita a opção do menu (05-0808 e
05-0863) usa a mesma palavra da imagem.

## Pendências

- Inventário das outras telas com texto desenhado (minigames, festivais, créditos).
  Para cada uma: save state, VRAM, bloco e paleta.
- A compressão do tipo 1 não foi decifrada. Não foi preciso, porque o logotipo fica
  como está.
