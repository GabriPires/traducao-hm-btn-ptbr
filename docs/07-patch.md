# O patch (.xdelta) e o pacote de lançamento

Não podemos distribuir o jogo, nem a imagem traduzida. O que se distribui é um
**patch**: a descrição de como transformar a imagem original na traduzida. É como um
`git diff`, só que de bytes. Quem baixa aplica o patch sobre a própria cópia do jogo e
obtém a imagem traduzida. O patch só leva o que mudou: textos, fonte e os códigos de
correção de erro dos setores alterados (`docs/03-montagem.md`).

## O formato VCDIFF

Os arquivos `.xdelta` usam o formato **VCDIFF**, um padrão aberto (RFC 3284) criado
pelo autor do xdelta3. Por isso o mesmo arquivo funciona no xdelta3, no Rom Patcher JS
(navegador), no Delta Patcher e no xdelta UI (Windows).

Um patch VCDIFF é um cabeçalho seguido de **janelas**:

```
D6 C3 C4 00   número mágico ("VCD" com o bit alto ligado) + versão 0
00            indicador do cabeçalho: sem compressão extra, tabela de códigos padrão
janela 1, janela 2, ...
```

Cada janela produz um pedaço do arquivo final e diz de onde vem a sua **origem**, um
trecho do original (tamanho e posição). Depois vêm três seções, um pouco como uma
página HTML que separa estrutura, estilo e script:

- **dados:** os bytes novos;
- **instruções:** o que fazer, em ordem: `ADD` (escreva N bytes dos dados), `COPY`
  (copie N bytes de um endereço) e `RUN` (repita 1 byte N vezes);
- **endereços:** de onde cada `COPY` copia.

O endereço de um `COPY` aponta para "origem + o que já foi escrito nesta janela",
como se os dois estivessem colados. Uma cópia pode até ler bytes que ela mesma acabou
de escrever, o que repete um padrão.

Para economizar espaço, cada instrução é **1 byte** que indexa uma tabela de 256
combinações de tipo, tamanho e modo de endereço. Algumas entradas juntam duas
instruções (`ADD` de 1 a 4 bytes + `COPY` de 4 a 6, por exemplo). Quando o tamanho não
cabe na tabela, a entrada tem tamanho 0 e o tamanho vem escrito logo depois. Os
endereços também têm modos: absoluto, relativo à posição atual ("here") e dois caches
dos endereços recentes ("near" e "same").

Os números usam **base 128**, do dígito mais significativo para o menos, com o bit 7
ligado em todos os bytes menos o último. O exemplo da RFC: 123456789 vira
`BA EF 9A 15`.

## Como o nosso patch é gerado

`tools/hmbtn/vcdiff.py` tem um codificador mínimo, em Python puro, para o nosso caso:
a imagem traduzida tem o **mesmo tamanho** da original, porque tudo é gravado no lugar.

- Cada janela tem 1 MiB e usa como origem o mesmo trecho do original.
- A comparação é feita por setor (2.352 bytes). Setores iguais viram um `COPY` só. Nos
  setores diferentes, a comparação é byte a byte.
- Um trecho igual com menos de 8 bytes entre duas diferenças entra no `ADD`, porque um
  `COPY` (código, tamanho e endereço) custaria mais.
- Só são usadas as entradas da tabela com tamanho escrito à parte: `ADD` (código 1) e
  `COPY` com endereço absoluto (código 19).
- Não há compressão secundária, nem a soma de verificação Adler-32 (uma extensão do
  xdelta3). Isso deixa o patch maior, mas aceito por qualquer aplicador. O `.zip` do
  lançamento compensa: o patch de 2,9 MB vira 1,6 MB.

O decodificador do mesmo módulo entende a tabela padrão inteira, inclusive os caches
de endereço. Ele serve para conferir o patch gerado e também aplica patches do xdelta3
feitos sem compressão secundária.

## Conferência

O comando `python3 tools/hm.py patch VERSÃO`:

1. confere o tamanho e os checksums da imagem original (`release.ORIGINAL`);
2. roda o `build` com `translation/`;
3. gera o patch e o aplica de volta sobre o original, com o decodificador próprio,
   conferindo que o resultado é idêntico à imagem traduzida;
4. monta o pacote.

O patch da versão 0.1.0 também foi aplicado com o núcleo do **Rom Patcher JS** (em
Node), e o resultado tem o mesmo SHA-1 da imagem traduzida. A tabela de códigos dele é
idêntica à nossa nas 256 entradas. Com o xdelta3 o patch ainda não foi testado aqui
**(?)**, mas ele usa só o formato padrão, sem extensões.

## O pacote de lançamento

O comando grava em `build/release/` (fora do git):

| Arquivo | Conteúdo |
|---|---|
| `HarvestMoon-BTN-PTBR-vX.Y.Z.xdelta` | o patch |
| `HarvestMoon-BTN-PTBR-vX.Y.Z.zip` | o patch, o `.cue` e o LEIA-ME, para publicar |

Dentro do `.zip`:

- o `.cue` aponta para `HarvestMoon-BTN-PTBR.bin`, o nome que o LEIA-ME pede para dar
  à imagem gerada;
- o `LEIA-ME.txt` traz como aplicar, os checksums da imagem original e os da
  traduzida, para quem quiser conferir.

O LEIA-ME sai do modelo `release.README`. A seção "Situação desta versão" precisa ser
revista a cada lançamento. As versões seguem o formato `MAIOR.MENOR.CORREÇÃO`; enquanto
for `0.x`, são prévias para testes.
