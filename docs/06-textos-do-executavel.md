# 06 · Textos do executável

Menus, comidas, itens de loja, sementes, mensagens de memory card e PocketStation, a
tela de criação do personagem e nomes de animais não estão nos registros de diálogo:
ficam dentro do próprio executável `SLUS_011.15`. Ferramentas: `tools/hmbtn/exetext.py`
e os comandos `dump`, `check` e `build`.

## Onde ficam

O corpo do executável é carregado na RAM em `0x80010000` (depois de um cabeçalho de
`0x800` bytes). Os textos ficam colados um no outro, cada um terminado por `FFFF`, em
dois blocos:

| Bloco | Endereços | Conteúdo |
|---|---|---|
| Principal | `0x8005175C`–`0x80054BBA` | menus, avisos, memory card, comidas, lojas, sementes |
| Nomes | `0x800556B6`–`0x800558A2` | nomes de animais e de competidores |

São **387 textos** (o `dump` grava em `build/script/exe.json`, com o tamanho máximo
de cada um no campo `max`). Logo depois do bloco principal vêm variáveis do jogo, então
o bloco não pode crescer.

## Como o jogo acha cada texto (investigação parcial)

Diferente dos diálogos, aqui não há posição fixa por registro, e não existe uma tabela
única de ponteiros. Encontramos vários caminhos ao mesmo tempo:

- **Deslocamento a partir do início do bloco.** O código soma `0x8005175C` com um número
  guardado numa variável ou numa tabela (ex.: a caixa "Yes / No" lê o deslocamento em
  `0x80054BBC`). O overlay 11 tem tabelas desses deslocamentos.
- **Endereço absoluto no código dos overlays** (subarquivos 11, 15 e 27), montado com o
  par de instruções `lui`/`addiu`.
- **Endereço absoluto no próprio executável**, para poucos textos (a grade de letras da
  tela de nomes, "Name", "Birthday").
- **Tabelas de estruturas**: o deslocamento do nome aparece a cada N bytes, junto com
  outros campos (preço, ícone...). Achadas procurando o deslocamento de textos
  consecutivos em intervalos constantes: várias no executável com passo de 32 bytes
  (comidas, itens) e outras nos overlays 11, 18 e 27.

Somando tudo, **189 dos 354 textos do bloco principal** têm referência identificada.
Os demais formam grupos (itens das lojas, sementes, avisos de memory card, opções de
configuração) que devem usar estruturas de outro formato, ainda não mapeadas. **(?)**

Para isso foi escrito um desmontador mínimo de MIPS R3000 (usado só na análise).

## Estratégia: traduzir no lugar

Como nem todas as referências são conhecidas, a tradução é gravada sem mudar nada de
posição, o que funciona qualquer que seja o caminho que o jogo usa:

- cada texto continua **começando** no mesmo endereço (ponteiros e deslocamentos
  continuam valendo);
- e continua **terminando** no mesmo lugar: se a tradução for mais curta, o `build`
  completa com espaços antes do `FFFF` (assim até um código que contasse terminadores
  chegaria ao texto certo).

A consequência é a regra principal: **a tradução de um texto do executável não pode
ser mais longa que o original** (`max`, em caracteres; `\n` conta como 1).

Exemplos do menu de pausa:

| Original | `max` | Tradução |
|---|---|---|
| `Amount\nshipped` | 14 | `Total\nenviado` |
| `Earnings &\nexpenses` | 19 | `Receitas e\ndespesas` |
| `Satisfactory` | 12 | `Satisfatório` |
| `Free` | 4 | `Vago` (não cabe "Livre") |

Se um texto importante não couber de jeito nenhum, a saída é mapear as referências
dele e movê-lo para outro lugar. Fica para quando aparecer o caso.

## Regras conferidas pelo `check`

- no máximo `max` caracteres;
- só caracteres com desenho na fonte, os mesmos códigos `{...}` do original;
- não mais linhas que o original;
- textos com linhas começando por espaço (opções de menu como `" Yes\n No"`, títulos
  alinhados) mantêm o mesmo número de linhas e os espaços do começo.

## Arquivos

- original: `build/script/exe.json` (local), entradas `{id, max, en}`, com `id` no
  formato `exe-ENDEREÇO` (ex.: `exe-800535E6`);
- tradução: `translation/exe.json`, `{"exe-800535E6": "Total\nenviado"}`.
