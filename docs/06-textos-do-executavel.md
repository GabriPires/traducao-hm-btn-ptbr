# 06 · Textos do executável e dos minigames

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

## Grupos reorganizados: quando o texto precisa crescer

Não existe espaço livre comprovado no executável: as áreas zeradas são buffers que o
código usa, e a memória logo depois do fim do executável também é usada. Por isso, quando
um texto não cabe, ele cresce **pegando espaço dos vizinhos**, num grupo reorganizado
(`exetext.GROUPS`, aplicado por `exetext.plan`, que o `check` e o `build` usam):

- os textos do grupo são regravados um depois do outro; o primeiro nunca sai do lugar;
- cada texto que anda tem as referências conhecidas corrigidas (instrução `addiu` nos
  overlays ou entradas da tabela de receitas);
- o grupo termina exatamente onde terminava e mantém o mesmo número de textos, então
  quem conta terminadores continua achando o texto certo;
- **rede de segurança:** quando possível, o começo antigo de um texto que andou cai no
  `FFFF` do anterior, e uma referência desconhecida mostra texto vazio em vez de lixo.

| Grupo | Para quê |
|---|---|
| `" Yes\n No"` + ordinal `st` | `" Sim\n Não"` na caixa de confirmação, usando o espaço do `st` (que fica vazio). Uma referência aponta para o meio do texto, direto no "No": ela passa a ler "Não" |
| List, Help, Days left | "Lista", "Ajuda", "Faltam" no menu da fazenda (overlay 11) |
| `"Yes\nNo"` + Diary | "Sim/Não" nos diários; "Diary {4001}" vira "Jogo {4001}" (overlay 15) |
| No + 65 comidas | "Não" na configuração e nomes completos das comidas. A **tabela de receitas** do executável (entradas de 32 bytes em `0x40B40`–`0x4175F`, nome no fim de cada entrada) é a única referência aos nomes de comida |

Detalhe curioso: o código sempre soma ao endereço do texto um valor guardado em
`0x80054BBC`, que vale zero na versão americana. Deve ser o "deslocamento do idioma" da
versão europeia (que tinha vários idiomas; daí as letras alemãs na fonte).

## Pendências

Estes textos não cabem traduzidos e ficam em inglês até as referências deles serem
mapeadas (as lojas usam alguma estrutura que a análise estática não encontrou; o caminho
é um ponto de parada de leitura no emulador, com a loja aberta):

`Wine`, `Brush`, `Milker`, `Milk`, `Snowcone`, `Salad` (cardápio da Pousada), `Buy cow`,
`Buy sheep`, `Sell cow`, `Sell sheep`.

Também ficam em inglês, de propósito: termos técnicos (`ON`, `OFF`, `Stereo`, `Mono`,
`Analog`, `Odds`), nomes próprios (Duendes, galinhas, competidores, animais) e a grade de
letras da tela de nomes. Abreviações usadas por falta de espaço: "Açúc.", "Gelad.",
"Ferram.", "Ingred.", "Utensíl.", "Medal.", "Sem." (sementes), "Máq." (máquinas).

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

## Textos dos minigames (overlays)

Alguns minigames carregam código próprio, em subarquivos do `A_FILE` (os overlays), com
uns poucos textos soltos. São **16 textos** traduzíveis, listados em
`exetext.OVERLAY_STRINGS` e tratados com a mesma regra (no lugar, sem crescer):

| Subarquivo | Conteúdo |
|---|---|
| 11 | pergunta se quer subir a escada e sair da mina |
| 17 | apostas da corrida de cavalos ("Odds", "Tickets", "You can win … medals") |
| 21 | aviso do minigame de arremesso |
| 23 | competidores da corrida no formato "Fazenda X's nome" |
| 25 | aviso de que todos estão esperando |

Ficam de fora os nomes próprios de competidores do subarquivo 19 e os nomes das moças
no 11. Original em `build/script/overlays.json`, tradução em `translation/overlays.json`,
com ids `ovNN-DESLOCAMENTO` (ex.: `ov17-0367A`).
