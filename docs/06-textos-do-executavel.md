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
| Maximum + grades do teclado | "Símbolos", "Espaço" e "ABC" na tela de nomes. As duas grades são achadas por `addiu` no próprio executável (`0x80023D60` e `0x80023D6C`), e o código só as desenha: a letra digitada vem de outro lugar |
| Lojas | Ferraria, Pousada/bar, Vinícola e Rancho: nomes achados por endereços somados no overlay 11 (ver abaixo) |

**Referências derivadas.** O diário (overlay 15) guarda o endereço de "Diary" num
registrador e acha as mensagens de diário vazio e de falta de espaço somando um
deslocamento a ele (`addiu v1,s6,-0x13A` etc.). Quando "Diary" anda, essas instruções
precisam compensar, senão as mensagens começam uma letra depois ("Vazio" aparecia como
"azio"). O grupo lista essas instruções em `derivados`, e o `build` as corrige.

**Endereços somados (lojas).** O código soma ao endereço do texto um valor guardado na
memória. Em geral é a palavra de `0x80054BBC`, que vale zero na versão americana (deve
ser o "deslocamento do idioma" da versão europeia, que tinha vários idiomas; daí as
letras alemãs na fonte). Alguns menus usam a palavra seguinte, `0x80054BC0`, que vale
`0x2C3A` (`exetext.BASE_WORD` e `BASE_DELTA`): o `addiu` monta `endereço - 0x2C3A`, e por
isso uma busca pelo endereço do texto não acha nada.

As lojas funcionam assim. No overlay 11, a função de cada loja faz `lui 0x8005` +
`addiu` para o primeiro nome, soma a palavra de `0x80054BC0` e guarda o ponteiro numa
lista. Os nomes seguintes saem de `addiu` sobre o registrador que já tem o primeiro
(`addiu v0,a1,0x12` = 9 letras depois). Uma primeira hipótese, de que o jogo contava
terminadores, foi derrubada no jogo: os nomes apareciam cortados ("scova") ou vazios.
Cada grupo de loja lista essas instruções em `somados` (base: o `lui` ou o id do texto
que já está no registrador). O `build` recalcula cada uma, inclusive quando a base também
anda. A varredura foi feita em todos os subarquivos e no executável, e só o overlay 11
acha esses textos. O teste refaz a conta de cada instrução sobre o resultado.

## Textos que entram no meio das falas

- **Apelido da esposa** (`{400F}`): `exe-80054396` e `exe-800543A2` ("Honey" e
  "Darling") são colados dentro das falas. O espaço de enchimento apareceria na frase
  ("Amor !"), então o `check` exige que a tradução ocupe o tamanho exato
  (`exetext.EXACT_LENGTH`): ficaram "Lindo" e "Querido". As opções do menu de apelido
  nas falas (`Meu bem / Lindo / Querido`) precisam usar as mesmas palavras.
- **Animais nas cerimônias** (`{401B}`–`{4020}`): o jogo cola o texto de `0x80049084`
  depois de cada nome. Ele fica fora dos blocos de texto, e o `build` o troca por um
  remendo fixo (`exetext.patches`, que confere os bytes originais antes de gravar):
  `"'s" + quebra` vira só `quebra`. Só uma instrução do executável lê esse endereço.

## Dias da semana e estações (remendo de código)

Calendário, relógio, diário e a variável de data (`{4003}`) pegam os nomes de duas
funções do executável, logo depois do texto das cerimônias:

| Função | Original | Tabela original |
|---|---|---|
| `0x8001AA7C` (estação 0–3) | copia 6 letras de 16 bits | `0x8004908C`, 6 letras por nome ("Fall" + 2 espaços) |
| `0x8001AAB8` (dia 0–6) | copia 3 letras de 16 bits | `0x800490BC`, 3 letras por nome |

"Primavera" não cabe em 6, e não há espaço livre comprovado para uma tabela maior. Mas
todas as letras usadas têm código menor que `0x100`: as duas funções foram reescritas
com o mesmo tamanho (15 instruções) para ler **uma letra por byte** (`lbu` em vez de
`lhu`), o que dobra o espaço da mesma área:

- estações: 4 × 10 bytes a partir de `0x80049088`, até 9 letras terminadas em `0xFF`
  (sem os espaços de enchimento; "4 de Verão, Ano 1" sai sem buraco);
- dias: 7 × 3 bytes logo depois.

Os nomes ficam em `exetext.SEASON_NAMES` e `WEEKDAY_NAMES`. O montador e o interpretador
mínimos de MIPS (`tools/hmbtn/mips.py`) geram o código e, nos testes, rodam as funções
antiga e nova sobre o executável de verdade. A área antiga é conferida por SHA-1 antes
de gravar (o repositório não guarda o texto original).

## Calendário: "Ano 1"

O cabeçalho do calendário (overlay 11, função em `0x428AC`) desenha o número do ano em
`x=0x1F` e "Year" em `x=0x39` ("1st Year"; os ordinais ficaram vazios). O remendo
`exetext.OVERLAY_PATCHES` troca as posições: "Ano" em `0x1F` e o número (2 casas,
alinhado à direita) em `0x3B`, o que dá "Ano 1" e "Ano 10".

## Diário: data de cada jogo

A tela de carregar e salvar (overlay 15, a partir de `0x9100`) monta a data num buffer
de `0x28` bytes, preenchido antes com `0xFF`: ano em `+0x00`, estação em `+0x0A` e dia
em `+0x1A`, ligados às variáveis `{4002}`, `{4003}` e `{4004}` da frase
`exe-80051D9E`. Havia dois problemas, corrigidos em `exetext.OVERLAY_PATCHES`:

- a estação tinha 8 letras de espaço, e o dia, escrito depois, apagava o fim de
  "Primavera" ("Primaver 4"). O dia passou para `+0x1E`: estação com até 9 letras +
  `FFFF`, dia com 2 casas + `FFFF` até `+0x24`;
- o dia era escrito com o ordinal ("4th"), por uma função do próprio overlay
  (`0x8013703C`) que chama a do número (`0x8001A970`) e depois copia o ordinal. Como os
  ordinais viraram espaços, sobrava "4   de". A chamada vai direto para a função do
  número, que recebe os mesmos argumentos.

## Notas e pendências

- **Lojas:** os 10 itens que faltavam (`Wine`, `Brush`, `Milker`, `Milk`, `Snowcone`,
  `Salad`, `Buy/Sell cow/sheep`) foram traduzidos com os grupos `somados`, conferidos
  no jogo. Abreviação de cardápio: "Ordenh." (Ordenhadeira; a coluna do nome na
  Ferraria tem 8 letras). Comprar e vender animais viraram "Vaca", "Ovelha", "Vender
  vaca", "Vender ovelha".
- **Relógio:** "AM"/"PM" continuam (não estão nos blocos de texto; provavelmente são
  desenhos). Em português o uso é entendido.

Também ficam em inglês, de propósito: termos técnicos (`ON`, `OFF`, `Stereo`, `Mono`,
`Analog`, `Odds`) e nomes próprios (Duendes, galinhas, competidores, animais).
Abreviações usadas por falta de espaço: "Açúc.", "Gelad.", "Ferram.", "Ingred.",
"Utensíl.", "Medal.", "Sem." (sementes), "Máq." (máquinas), "Ordenh.".

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
