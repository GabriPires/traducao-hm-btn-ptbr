# 01 · O disco e o texto

Achados da Fase 0. Tudo aqui foi verificado com as ferramentas em `tools/` sobre a
imagem cujo SHA-1 está no README. O que ainda é palpite está marcado como **(?)**.

## A imagem do disco

O arquivo `HARVESTMOON.iso` não é uma ISO "de verdade" (2048 bytes por setor): é uma
imagem crua com **2352 bytes por setor**, o formato normalmente chamado de `.bin`.
Cada setor carrega, além dos dados, cabeçalhos e códigos de correção de erro do CD
(detalhes no topo de `tools/hmbtn/disc.py`). É uma faixa só de dados, `MODE2/2352`,
por isso o `.cue` gerado por `hm.py cue` tem uma linha de TRACK só.

Por cima dos setores existe um sistema de arquivos ISO9660, igual ao de um CD de PC:

| Arquivo | Tamanho | O que é |
|---|---|---|
| `SYSTEM.CNF` | 69 B | "Manifesto" do boot: manda o console rodar `SLUS_011.15` |
| `SLUS_011.15` | 316 KB | Executável principal (código MIPS) |
| `A_FILE.BIN` | 128 MB | Pacote com quase todos os dados do jogo |
| `A_FILE.HDT` | 132 B | Índice do pacote |
| `STR/01..04.XA` | 18 MB | Áudio XA (música/sons, setores "Form 2") |
| `DUMMY.DAT` | 32 MB | Enchimento: empurra os dados para a borda externa do CD, que é lida mais rápido |
| `*.TXT` | 0 B | Arquivos vazios exigidos pelo padrão |

> Analogia web: o `SYSTEM.CNF` é o `index.html` que só carrega o `main.js`
> (`SLUS_011.15`), e o `A_FILE.BIN` é um bundle com todos os assets.

## O pacote A_FILE

`A_FILE.HDT` é uma lista de 33 inteiros de 32 bits (little-endian). Cada um diz onde um
subarquivo começa dentro do `A_FILE.BIN`; o último é o tamanho total. Todos são
múltiplos de 2048, ou seja, cada subarquivo começa num setor novo do CD.

O `hm.py extract` separa os 32 subarquivos em `build/afile/NN.bin` e confere que
remontá-los reproduz o original byte a byte.

| # | Tamanho | Conteúdo |
|---|---|---|
| 00, 01, 07 | 61 MB, 1,6 MB, 62 KB | (?) gráficos/cenários: cabeçalho parecido entre si, a investigar |
| **02–06** | 15, 16, 5, 11 MB, 448 KB | **Diálogos**, em registros de 8 KB ([02-dialogos.md](02-dialogos.md)) |
| 09 | 5,7 MB | Banco de sons (começa com `pBAV`, formato VAB da Sony) |
| 10, 11, 15, 17, 19, 21, 23, 25, 27, 28 | pequenos | (?) Código extra carregado sob demanda ("overlays"): começam com um ID e endereços `0x800Bxxxx` da RAM do PS1 |
| 14, 18, 20, 22, 24, 26 | pequenos | (?) Dados que acompanham os overlays (todos começam com `0E 00 00 00`) |
| 10, 30, 31 | pequenos | Têm textos ASCII de depuração e de memory card (`<<Ez MemoryCard Util.>>`), provavelmente invisíveis para o jogador |
| demais | | a investigar |

## Codificação do texto

Uma busca por "nomes de personagens" em ASCII não acha nada. Isso acontece porque o jogo
usa uma **tabela própria**. Para descobri-la usamos a *busca relativa*: em vez de procurar
os bytes de "festival", procuramos qualquer sequência cujas **diferenças** entre valores
batam com as diferenças entre as letras (f→e = −1, e→s = +14, ...). Funcionou com
valores de **16 bits**, e daí saiu que `a = 0x0020`.

Cada caractere ocupa 2 bytes (little-endian). A tabela completa está em
`tables/hmbtn.tbl`. Resumo:

| Valores | Significado |
|---|---|
| `0000–0019` | A–Z |
| `0020–0039` | a–z |
| `0040–0049` | 0–9 |
| `0050–0056` | Contrações num caractere só: `'t 's 'l 'd 'm 'r 'v` |
| `0062 0063 0066 0069 006A 006B 006C 007F 008C 008D 008E` | `? ! : - ( ) . … , ' "` (`?` e `…` são deduções fortes) |
| `0076` | `♥` (entre nomes de casais) |
| `0FFD` | espaço |
| `400A` | nome do jogador (o jogo troca pelo nome digitado) |
| `FFFE` | quebra de linha |
| `FFFF` | fim da fala |

Repare que a fonte **não tem acentos**. Os caracteres de contração (`'s` como um único
desenho) mostram que a fonte é desenhada sob medida para o inglês. Na Fase 3 vamos
precisar criar `á à â ã é ê í ó ô õ ú ç` e as maiúsculas, aproveitando por exemplo os
espaços das contrações, que não fazem sentido em português.

### Estrutura de uma fala

Resolvido na Fase 1: veja [02-dialogos.md](02-dialogos.md).

