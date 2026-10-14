# 03 · Montando a imagem traduzida

Fase 2. Comando: `python3 tools/hm.py build`.

## O que o build faz

1. Lê o `A_FILE.BIN` e o `A_FILE.HDT` da imagem original, que só é lida.
2. Para cada fala em `translation/*.json`:
   - pega o **prefixo** de códigos da fala original (retrato, caixa...);
   - codifica `prefixo + texto em português` com a tabela;
   - grava no setor de texto do registro (0x1800), completando com zeros.
3. Confere que nenhum subarquivo mudou de tamanho. Tudo é gravado no lugar, então o
   índice do pacote e o sistema de arquivos do CD continuam valendo.
4. Copia a imagem original para `build/HARVESTMOON-PTBR.bin` e reescreve **só os
   setores que mudaram**, recalculando o EDC/ECC de cada um (`tools/hmbtn/ecc.py`).
5. Gera o `.cue` ao lado.

Erros que impedem a geração: caractere sem entrada na tabela (por enquanto qualquer
acento), fala com mais de 1023 valores, `id` inexistente. Linhas com mais de
`MAX_LINE` caracteres (30, provisório) geram só aviso.

## Por que recalcular EDC/ECC

Cada setor de dados termina com um CRC (EDC) e com paridade Reed-Solomon (ECC), que
servem para detectar e corrigir riscos no CD. Se os dados mudam e esses códigos não,
o setor parece corrompido. Emuladores costumam ignorar isso, mas um leitor de verdade
(ou um emulador mais rigoroso) não. O cálculo foi validado regerando setores do disco
original: todos ficaram idênticos byte a byte (`tests/test_tools.py`, `EccTest`).

## Garantias verificadas

- Sem traduções, a imagem gerada é **idêntica** à original (mesmo SHA-1).
- Com 5 falas traduzidas, mudam **exatamente 5 setores**, um por fala, espaçados de 4
  em 4 (registros de 8 KB). Retratos e todo o resto ficam iguais.

## Prova de conceito no emulador

Traduzimos, sem acentos, as 5 primeiras falas de um jogo novo: o prefeito mostrando a
fazenda (`03-1899`, `03-1900`) e o começo do flashback (`03-1901` a `03-1903`).

Resultado no DuckStation: as falas apareceram em português, a conversa seguiu
normalmente em inglês nas falas seguintes e nada travou.

Isso confirma a hipótese do [02-dialogos.md](02-dialogos.md): **o jogo acha cada fala
pela posição do registro e não guarda o tamanho do texto em outro lugar**. Dá para
traduzir todos os diálogos gravando no lugar, sem tabela de ponteiros.
