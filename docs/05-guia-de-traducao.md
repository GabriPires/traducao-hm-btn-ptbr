# 05 · Guia de tradução

Regras, estilo e glossário da tradução. Vale para quem traduz, para quem revisa e para
agentes de IA (o prompt do agente tradutor, em [`prompts/agente-tradutor.md`](../prompts/agente-tradutor.md),
manda seguir este guia).

As regras técnicas são conferidas automaticamente por `python3 tools/hm.py check`; o
estilo e o glossário dependem de quem traduz e revisa.

## Arquivos

**Original (local, fora do git):** `build/script/NN.json`, gerado da sua cópia do jogo
por `python3 tools/hm.py dump`. Uma entrada por fala:

```json
{
  "id": "03-0013",
  "prefix": "{0F90}{0FF7}{0FF4}{0FF5}{0E2F}",
  "speakers": ["Barley (M)"],
  "en": "(texto original da fala, com \n nas quebras de linha)"
}
```

- `id`: identificador da fala; liga original e tradução.
- `prefix`: códigos do início da fala. Não se traduz e não vai para a tradução; serve
  para saber o tipo de texto (ver "Tipos de texto").
- `speakers`: quem fala em cada página, na ordem das páginas (ver "Quem fala").
- `en`: o texto a traduzir.

**Tradução (versionada):** `translation/NN.json`, só `id → texto em português`:

```json
{
  "03-1899": "E então, o que achou?\nEsta era a fazenda do seu avô…"
}
```

- Chaves em ordem crescente de `id`, indentação de 2 espaços, UTF-8 com os caracteres
  reais (`ç`, não `ç`), sem comentários.
- Quebras de linha como `\n`. Nada do texto em inglês, nem o `prefix`.
- Falas com `en` vazio ou só `Dummy` não aparecem no jogo e não são traduzidas.
- Fala ausente continua em inglês no jogo.

## Regras técnicas

Quebrar estas regras faz a fala sair cortada, embaralhada ou travar o jogo. O `check`
acusa todas, e o `build` se recusa a gravar uma fala que as quebre.

### Caracteres

Só os que têm desenho na fonte do jogo ([04-fonte.md](04-fonte.md)):

- letras `A–Z`, `a–z` e `á à â ã é ê í ó ô õ ú ç Á À Â Ã É Ê Í Ó Ô Õ Ú Ç`;
- dígitos `0–9`, espaço e quebra de linha;
- pontuação `. , ; ! ? : - ( ) ' " / + % & ~`, as reticências como **um caractere só**
  (`…`) e o `♥`.

Proibidos: aspas curvas (`“ ” ‘ ’`), travessão (`—`, `–`), `ü`, `ª`, `º`, `°`, `*`,
`$`, `#`, `=`, `_`, colchetes, emojis. No lugar:

| Em vez de | Use |
|---|---|
| `...` | `…` |
| `—` (travessão) | `--`, como o original |
| `“ ”` | `"` |
| `1º`, `2ª` | "primeiro", "dia 1", "segunda" |

### Códigos entre chaves

- **Controle** (`{0Exx}`, `{0Fxx}`): páginas, retratos, menus. Todos presentes, **na
  mesma ordem e na mesma posição** (começo de página, fim de página, antes de opções).
  Copie letra por letra.
- **Nomes variáveis**: o jogo troca pelo nome. Todos devem continuar presentes, mas
  podem mudar de lugar na frase: `{jogador}'s farm` → `a fazenda de {jogador}`.

  | Código | O que vira | Gênero |
  |---|---|---|
  | `{jogador}` | nome do jogador | M |
  | `{400B}` | nome do cavalo | M ("o {400B}") |
  | `{400C}` | nome do cão | M ("o {400C}") |
  | `{400D}` | nome da fazenda | "a fazenda {400D}" |
  | `{400E}` | nome do filho | M ("o {400E}") |
  | `{400F}` | apelido carinhoso que a esposa usa com o jogador ("Honey", "Darling") | vocativo |
  | `{4000}`, `{4001}` | valores ou nomes de competidores, conforme a cena | — |
  | `{401B}`–`{4020}` | nome de um animal da fazenda (cerimônias de despedida) | use "de {401C}", sem artigo |

  Nas cerimônias o original escreve `{401E}soul`, sem espaço: é possível que o jogo
  troque o código por "Nome's " em inglês. **(?)** Está registrado para conferir no jogo.
- **Símbolos** que continuam como código: botões `{006D}` `{006E}` `{006F}` `{0070}`
  (○ × △ □), setas `{0087}`–`{008A}`, notas musicais `{0082}`–`{0085}` e enfeites
  `{0065}` `{0075}` `{0077}` `{0086}`. Mantenha, reposicionando conforme a frase:
  `{006D} button: Select` → `Botão {006D}: Selecionar`.
- `{001B}` e `{001E}` aparecem em volta de opções; mantenha-os no mesmo lugar.
- `{008D}` é só um apóstrofo e pode sair se a frase em português não precisar.
- Nunca invente códigos nem altere os dígitos de um.

### Linhas e páginas

- **Página**: trecho separado por `{0FFC}{0FFB}` (espera o botão, limpa a caixa) ou
  `{0FFC}{0FFA}` (espera o botão e abre opções). Mesmo número de páginas do original.
- **Linha**: trecho separado por `\n`. Redistribua as quebras para o português ficar
  bom; não precisa seguir as do inglês.
- **No máximo 31 caracteres por linha.** Códigos não contam; cada nome variável conta
  como 8; espaços contam. (A caixa tem espaço para 32 letras de 8 pixels, mas a
  setinha ▼ ocupa o fim da última linha.)
- **Linhas por página:** diálogos com retrato mostram **4**; nos outros tipos, no
  máximo as linhas da página original.
- Não coube? Reescreva mais curto. Nunca crie páginas.
- Linhas que começam com espaço (opções de menu, títulos centralizados) mantêm o espaço.
- **Tamanho total:** até 1000 unidades por fala (cada caractere e cada código vale 1).
  Só pesa nos programas de TV, que precisam ser condensados.

### Tipos de texto

| `prefix` contém | Tipo | Cuidados |
|---|---|---|
| `{0FF4}{0FF5}{0E2` | Diálogo com retrato | O caso comum; 4 linhas por página |
| `{0FF6}` | Pensamento, flashback ou voz fora de cena | Linhas por página iguais às do original |
| `{0FF3}` | Descrição de item ou aviso do sistema | Informativo e direto |
| `{0FF1}` | Programa de TV ou texto de tela cheia | Respeite linhas e tamanho total |
| `{0FFA}` | Menu de escolha | Uma opção por linha, começando com espaço, curta |

Menus também aparecem no meio de um diálogo, depois de `{0FFC}{0FFA}`:

```
en: Will you come with me?{0FFC}{0FFA}\n{0FF6} Yes\n No
pt: Você vem comigo?{0FFC}{0FFA}\n{0FF6} Sim\n Não
```

## Textos do executável (`exe.json`)

Menus, comidas, itens de loja, sementes e mensagens de memory card ficam no executável
([06-textos-do-executavel.md](06-textos-do-executavel.md)). O original fica em
`build/script/exe.json` (`{id, max, en}`) e a tradução em `translation/exe.json`
(`{"exe-800535E6": "Total\nenviado"}`).

- **Nunca mais longo que `max`**, contando cada caractere, espaço, `\n` e código como 1.
  Mais curto pode: o jogo completa com espaços.
- Prefira um sinônimo que caiba ("Free" → "Vago"). Se for preciso abreviar, use ponto
  ("Sem. de nabo") e abrevie **sempre do mesmo jeito**.
- Opções de menu e títulos alinhados (linhas que começam com espaço) mantêm o mesmo
  número de linhas e o espaço do começo: `" Yes\n No"` → `" Sim\n ..."`.
- Nomes de itens e comidas seguem o glossário e devem bater com como aparecem nos
  diálogos.
- Mensagens de memory card e sistema: tom neutro e direto ("Salvando no MEMORY CARD").
- Se um texto não couber de jeito nenhum, deixe-o sem tradução e informe o `id` na
  resposta final: ele será tratado à parte.

- Espaços **no meio** de um texto marcam onde o jogo desenha um número
  (`"You can win      medals"`): mantenha o vão do mesmo tamanho e na mesma posição.

Os textos dos minigames (`build/script/overlays.json` → `translation/overlays.json`,
ids `ovNN-...`) seguem exatamente as mesmas regras.

**Não traduzir:**

- a grade de letras da tela de nomes (`exe-800537B2` e `exe-80053888`);
- os nomes de animais e competidores (todos os `id`s a partir de `exe-800556B6`) e os
  nomes dos Duendes (Chef, Nappy, Timid, Hoggy, Staid, Bold, Aqua);
- os sufixos de ordinal `st`, `nd`, `rd`, `th`: traduza cada um como um único espaço
  (`" "`), porque o português não tem `º` na fonte.

## Quem fala

O campo `speakers` diz quem fala em cada página. Use para acertar o gênero das
palavras (`obrigado`/`obrigada`, `cansado`/`cansada`) e o tom de cada personagem.

- `Nome (F)` / `Nome (M)`: personagem e gênero gramatical.
- `sem retrato`: pensamentos do protagonista, vozes de flashback, descrições, TV.
  Descubra pelo contexto.
- `opções do jogador`: respostas que o jogador escolhe; quem fala é o protagonista.

O **protagonista é homem**: quando falam com ele ou sobre ele, use o masculino
(`Você está cansado?`, `o dono da fazenda`).

A tabela completa (códigos de retrato → personagem) está em
[`tables/personagens.tsv`](../tables/personagens.tsv). Foi montada olhando o retrato de
cada código e conferida pelas falas em que os personagens se apresentam.

| Feminino | Masculino |
|---|---|
| Ann, Anna, Deusa da Colheita, Elli, Ellen, Karen, Lillia, Manna, Mary, May, Popuri, Sasha | Barley, Basil, Carter (padre), Cliff, Doug, Doutor, Duke, Gotz, Gourmet, Gray, Greg, Harris, Jeff, Kai, Kano, Kappa, Louis, Rick, Saibara, Stu, Thomas (prefeito), Won, Zack, os Duendes da Colheita, o filho do jogador |

## Estilo

- Português do Brasil natural, como num jogo bem localizado; nada de tradução literal.
  Crianças falam como crianças, idosos como idosos.
- Trate o interlocutor por **você**; use "o senhor"/"a senhora" quando o original
  deixa clara uma relação de respeito (ex.: a Karen falando com a Lillia).
- **Artigo antes de nomes de pessoas**, como na fala brasileira: "a Popuri", "o Rick",
  "da Elli e do Doutor", "Sou a Mary".
- Mantenha tiques de fala e onomatopeias inventadas (o "budum" de um personagem).
  Interjeições: Wow → Uau, Ouch → Ai, Hmm → Hum, Ahem (pigarro) → Hum, hum (não use
  "Aham" para pigarro: em português ele significa "sim", e é a tradução certa de
  "Uh huh"), Waaa (choro) → Buááá, sob → snif, munch → nhac.
- Falas iguais em inglês recebem traduções iguais, salvo quando o contexto pede outra.
- Horários no padrão brasileiro: `6PM` → `18h`; `8:00` pode ficar. Moeda: `500G`.
  Datas: `the 22nd of Spring` → `dia 22 da Primavera`.
- Adapte expressões em vez de traduzir palavra por palavra ("Lunch Special" →
  "prato do dia"; "Rick…brother…" dito pelo futuro cunhado → "Rick… cunhado…").

## Glossário

**Não se traduzem:** nomes de personagens (os da tabela acima, mais Aja, Joanna, Pon,
Begak, Chibi...), nomes dos Duendes da Colheita (Chef, Nappy, Timid, Hoggy, Staid,
Bold, Aqua) e nomes inventados de produtos e programas (Ultror, Bodigizer, Turbojolt,
Farmer Fran, Jimmy).

| Inglês | Português |
|---|---|
| Spring / Summer / Fall / Winter | Primavera / Verão / Outono / Inverno |
| Monday … Sunday / on Mondays | segunda-feira … domingo / às segundas |
| Mineral Town | Mineral Town |
| Mayor | Prefeito |
| Doctor (personagem) | Doutor |
| Pastor | padre |
| Policeman | policial |
| woodcutter | lenhador |
| Grandpa / Grandma | vovô / vovó (avô / avó em tom formal) |
| Mom / Dad | mãe / pai (mamãe / papai na fala de crianças) |
| Harvest Goddess / Goddess | Deusa da Colheita / Deusa |
| Harvest Sprites | Duendes da Colheita |
| Poultry Farm | Granja |
| Yodel Ranch | Rancho Yodel |
| Rose Square / Square | Praça das Rosas / Praça |
| Supermarket | Supermercado |
| Blacksmith (loja / pessoa) | Ferraria / ferreiro |
| "Improve" (opção da Ferraria) | "Melhorar" (com aspas: é o nome da opção no menu) |
| Clinic / Library / Church | Clínica / Biblioteca / Igreja |
| Inn | Pousada |
| Seaside Lodge | Cabana da Praia |
| Aja Winery | Vinícola Aja |
| Orchard | Pomar |
| Mother's Hill | Colina da Mãe |
| Goddess Spring | Fonte da Deusa |
| Fish Pond | Lago dos Peixes |
| Hen House / Barn / stable | Galinheiro / Estábulo / Estábulo |
| water mill | moinho d'água |
| Shipping Bin / Bin | Caixa de Envio / Caixa |
| Fodder / Chicken Feed / Fish Food | Feno / Ração de galinha / Ração de peixe |
| Ax / Hoe / Sickle / Hammer / Watering Can | Machado / Enxada / Foice / Martelo / Regador |
| Fishing Rod / Milker / Brush / Clippers | Vara de Pesca / Ordenhadeira / Escova / Tesoura |
| Rucksack / Basket | Mochila / Cesta |
| Mayonnaise / Cheese / Yarn Maker | Máquina de Maionese / de Queijo / de Lã |
| Blue Feather | Pena Azul |
| Power Berry | Fruta do Poder |
| Miracle Potion | Poção Milagrosa |
| Moon Drop / Moondrop (flor) | Gota da Lua |
| Pink Cat / Magic Red / Toy Flower / Orangecup (flores) | Gato Rosa / Rubra Mágica / Flor-Brinquedo / Taça Laranja |
| Hothouse / Lumber | Estufa / madeira (no menu: "tábuas") |
| Honey / Darling (como a esposa chama o jogador) | Amor / Querido |
| Orichalcum / Adamantite / Mystrile | Oricalco / Adamantita / Mistrilo |
| Lunch Special | prato do dia |
| Love Potion | Poção do Amor |
| Relaxation tea / tea party (dos Duendes) | Chá relaxante / chá da tarde |
| Hot Spring | Fonte Termal |
| King (peixe) / Fisher King (título) | Peixe Rei / Rei da Pesca |
| Top Breeder (título) | Criador de Elite |
| Flower Festival | Festival das Flores |
| Goddess Festival | Festival da Deusa |
| Cooking Festival | Festival de Culinária |
| Tomato Festival | Festival do Tomate |
| Chicken / Cow / Sheep Festival | Festival das Galinhas / das Vacas / das Ovelhas |
| Horse Race / Local Horse Race / Dog Race | Corrida de Cavalos / Corrida de Cavalos da vila / Corrida de Cães |
| Music Festival | Festival de Música |
| Harvest Festival | Festival da Colheita |
| Star Night (Festival) | Noite Estrelada (Festival da Noite Estrelada) |
| Thanksgiving / Winter Thanksgiving | Ação de Graças / Ação de Graças de Inverno |
| Fireworks Display | Queima de Fogos |
| New Year's (Party) | Ano-Novo (Festa de Ano-Novo) |

### Comidas (como aparecem nos menus)

As descrições de itens (subarquivo 05) começam com o nome do item na primeira linha:
use **exatamente** o nome do menu. Comidas que não estão na tabela ficam iguais
(Curry, Ketchup, Cheesecake, Sushi, Sashimi, Chirashi sushi, Pizza, Cookie).

| Inglês | Português |
|---|---|
| Mayonnaise S | Maionese P |
| Mayonnaise M | Maionese M |
| Mayonnaise L | Maionese G |
| Mayonnaise XL | Maionese GG |
| Salad | Salada |
| Stew | Ensopado |
| Miso soup | Missoshiru |
| Stir fry | Refogado |
| Fried rice | Arroz frito |
| Veggie pancake | Panqueca |
| Sandwich | Sanduíche |
| Fruit juice | Suco de fruta |
| Fruit latte | Vitamina |
| Vegetable juice | Suco verde |
| Veggie latte | Vitamina verde |
| Mixed juice | Suco misto |
| Mixed latte | Vitamina mista |
| Pickled turnips | Nabo em conserva |
| Fries | Fritas |
| Pickles | Picles |
| Strawberry jam | Doce de morango |
| Strawberry milk | Leite de morango |
| Tomato juice | Suco de tomate |
| Popcorn | Pipoca |
| Pumpkin pudding | Pudim de abóbora |
| Happy eggplant | Berinjela feliz |
| Sweet potato | Batata-doce |
| Roasted potatoes | Batata assada |
| Greens | Verduras |
| Scrambled eggs | Ovos mexidos |
| Omelet | Omelete |
| Rice omelet | Omelete de arroz |
| Boiled egg | Ovo cozido |
| Hot milk | Leite quente |
| Butter | Manteiga |
| Cheese fondue | Fondue |
| Apple pie | Torta de maçã |
| Apple jam | Doce de maçã |
| Bamboo rice | Arroz de bambu |
| Grape jam | Doce de uva |
| Mushroom rice | Arroz de shitake |
| Truffle rice | Arroz trufado |
| Jam bun | Sonho |
| Dinner roll | Pãozinho |
| Raisin bread | Pão de passas |
| Grilled fish | Peixe assado |
| Noodles | Lámen |
| Curry noodles | Lámen de curry |
| Tempura noodles | Lámen tempurá |
| Fried noodles | Yakisoba |
| Chocolate cookie | Cookie de cacau |
| Tempura | Tempurá |
| Ice cream | Sorvete |
| Cake | Bolo |
| Chocolate cake | Bolo de cacau |
| Relaxation tea | Chá relaxante |
| Food fiasco | Gororoba |

Termo novo que não está aqui: traduza pelo sentido, use **sempre a mesma tradução** e
peça para incluí-lo no glossário na revisão do lote.

## Verificação

```sh
python3 tools/hm.py check 03     # um arquivo
python3 tools/hm.py check        # todos
```

Corrija todo `ERRO` até terminar em `OK`. Os `aviso`s não bloqueiam, mas leia cada um.
O `check` só lê arquivos; nunca altera nada.
