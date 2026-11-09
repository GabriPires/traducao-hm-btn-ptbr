---
name: remanejar-texto
description: Roteiro para fazer um texto do executável de Harvest Moon BTN (ids exe-XXXXXXXX em translation/exe.json) ficar mais longo que o original, usando o remanejamento automático. Use ao traduzir ou revisar menus, itens, lojas e rótulos quando a tradução ideal passa do `max`, ao trocar uma abreviação ("Sem.", "Gelad.", "Utensíl.") pela palavra inteira, ou quando o `check` disser "passou N caractere(s)" ou "longo demais". Não serve para falas (02–06), textos dos minigames (ovNN-...) nem para os apelidos de tamanho exato.
---

# Remanejar um texto do executável

Os textos do executável moram em endereços fixos, e o código guarda esses endereços,
como links apontando para URLs. Por padrão cada tradução cabe no espaço do original.
Um texto pode crescer quando os vizinhos ficaram mais curtos e todos os "links" para os
textos que precisam andar são conhecidos: o `check` e o `build` mudam os textos de
lugar e corrigem as referências sozinhos. Detalhes: `docs/06-textos-do-executavel.md`,
seção "Mapa de referências e remanejamento automático".

Há **dois limites diferentes**:

1. **Memória:** quantos caracteres cabem no bloco de textos. É o que o remanejamento
   resolve, e o comando `refs` mostra.
2. **Tela:** a largura da janela ou da coluna onde o texto aparece. Nenhuma ferramenta
   mede isso: só o teste no jogo.

## Quando NÃO usar

- Falas (`02-…` a `06-…`): têm espaço de sobra na memória; o limite é a caixa de
  diálogo (regras do `check`).
- Textos dos minigames (`ovNN-…`): não há mapa de referências; ficam sempre no lugar.
- Apelidos `exe-80054396` e `exe-800543A2`: têm tamanho exato.

## Passo a passo

1. **Contexto.** Leia o original e o `max` em `build/script/exe.json` e os textos
   vizinhos (eles costumam ser da mesma tela). Descubra onde o texto aparece.
2. **Limite de memória.** Rode `python3 tools/hm.py refs ID`:
   - `limite: N no lugar, até M com remanejamento`: a tradução pode ter até M
     caracteres (`\n` e cada código `{…}` contam 1);
   - `M == N`: não dá para crescer. Use um sinônimo que caiba ou a abreviação padrão do
     guia (`docs/05-guia-de-traducao.md`);
   - `está num grupo feito à mão`: não use este roteiro; avise quem mantém as
     ferramentas;
   - o limite vale para **um texto de cada vez**: dois vizinhos que crescem juntos
     disputam a mesma sobra (o `check` decide com todos).
3. **Limite de tela.** Consulte a tabela "Larguras conhecidas" abaixo. Se a tela não
   estiver lá, não passe do texto mais longo que já aparece na mesma lista ou janela, e
   marque o texto para teste no jogo.
4. **Grave** a tradução em `translation/exe.json` (só esse id).
5. **Confira** com `python3 tools/hm.py check exe`:
   - o esperado é o aviso `cresceu com remanejamento: K texto(s) mudaram de lugar
     (ids…); confira no jogo`. Guarde essa lista;
   - se vier erro (`o remanejamento não resolveu: …`), ele diz o motivo: falta de sobra
     ou vizinho sem referência conhecida. Não force: escolha outra palavra.
6. **Testes** (quem tem acesso às ferramentas): `python3 -m unittest discover tests`.
   O teste `test_current_translations_keep_every_reference` refaz a conta de cada
   referência conhecida depois de gravar as traduções.
7. **Roteiro de teste no jogo.** Liste o texto que cresceu e **todos** os textos da
   lista do aviso, com a tela onde aparecem. Todos precisam aparecer inteiros, nem
   cortados, nem vazios, nem com pedaço de outro texto.
8. **Depois do teste no jogo:** anote o resultado na tabela "Larguras conhecidas" e
   atualize o glossário e a lista de abreviações (`docs/05` e `docs/06`).

## Regras

- Nunca edite `exetext.GROUPS`, `tools/hmbtn/refs.py` ou `build/refs.json` para "fazer
  caber".
- Se no jogo um texto aparecer cortado, vazio ou trocado, existe uma referência que o
  mapa não achou: volte a tradução ao tamanho original e relate com uma captura de tela.
  A investigação é feita com um save state (memória do jogo); veja `docs/06`.
- Textos que cresceram só entram num lançamento depois do teste no jogo.
- O mesmo item deve ter o mesmo nome em todas as telas. Se uma tela não deixa crescer
  (por exemplo, a outra "Gelad.", no menu de guardar itens), registre a diferença no
  guia.

## Larguras conhecidas

| Tela | Largura | Fonte |
|---|---|---|
| Ferraria, lista de ferramentas | 8 letras ("Ordenh.") | teste no jogo |
| Rancho (comprar animais e itens) | pelo menos 14 letras + preço ("Remédio animal 1000G") | teste no jogo |
| Vinícola e Pousada | 10 a 11 letras encostam no preço ("Suco de uva200G", "Cheesecake250G"; igual no original) | teste no jogo |
| Cozinha (Utensílios, Ingrediente, temperos, Geladeira) | a confirmar: piloto de 2026-11 | piloto |
| Loja de sementes | a confirmar: piloto "Sementes de nabo" (16 letras) | piloto |

## Para o agente tradutor

O agente que traduz lotes (`prompts/agente-tradutor.md`) pode rodar só
`python3 tools/hm.py refs ID` e `python3 tools/hm.py check`. Ele não roda testes nem
`build`. No resumo final, ele lista cada texto que cresceu e os vizinhos que mudaram de
lugar, para o teste no jogo.
