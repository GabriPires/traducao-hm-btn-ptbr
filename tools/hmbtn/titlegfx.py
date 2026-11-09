"""Textos desenhados da tela de título, montados com as letras do próprio jogo.

A tela de título vem num pacote de imagens do subarquivo 00 (formato em font.py). Três
blocos são texto: o convite para apertar START e as duas opções do menu. São imagens de
4 bits por pixel com uma paleta comum de 16 cores, comprimidas com RLE.

Nada dessas imagens vai para o git. Como os acentos da fonte, as palavras em português
são montadas no build a partir das letras das imagens originais:

1. cada imagem original é dividida em letras pelo "miolo" (os pixels mais claros, no
   centro dos traços): as letras se encostam pela borda, mas o miolo de uma nunca toca
   o da vizinha;
2. cada pixel pertence à letra cujo miolo está mais perto (em 2D: a barra de um T que
   avança por cima da letra seguinte continua sendo do T), e de cada letra fica só o
   corpo: os cinzas ligados ao próprio miolo. O contorno preto e o halo verde (que no
   original faz a transição para a grama) ficam de fora, junto com pedaços da vizinha;
3. as letras são coladas com o mesmo espaçamento do original (ou 1 pixel mais juntas,
   se a palavra não couber), e o contorno preto é refeito em volta do corpo, sem halo;
4. o resultado é centralizado na largura da imagem original, que não pode mudar (o
   código desenha um retângulo de tamanho fixo).

O V e o J não existem nessas imagens e são derivados do U (funções _letter_v e
_letter_j).
"""

import struct

from . import font

SUBFILE = 0
PACKAGE = 0x2D1C                 # pacote da tela de título no subarquivo 00
PALETTE_BLOCK = 64               # paleta de 16 cores das três imagens
TRANSPARENT = 12                 # índice transparente dessa paleta
OUTLINE = 0                      # contorno preto
HEIGHT = 24

# Imagens com texto: bloco -> (id da tradução, número de letras da imagem original)
TARGETS = {65: ('gfx-titulo-start', 16), 66: ('gfx-titulo-novo', 7),
           67: ('gfx-titulo-continuar', 8)}

# Onde está cada letra disponível: (bloco, posição da letra na imagem original). Quando a
# letra aparece mais de uma vez, vale a que não perde pixels para a vizinha (o T antes de
# um A tem a barra cortada, porque ela avança sobre o topo do A).
LETTERS = {'P': (65, 0), 'R': (65, 1), 'E': (65, 2), 'S': (65, 3), 'T': (65, 9), 'A': (65, 7),
           'B': (65, 10), 'U': (65, 11), 'O': (65, 14), 'N': (65, 15), 'W': (66, 2),
           'G': (66, 3), 'M': (66, 5), 'C': (67, 0), 'I': (67, 4)}
DERIVED = {'V': 'U', 'J': 'U'}

GAP = 2                          # pixels entre o miolo de uma letra e o da seguinte
WORD_GAP = 8                     # o mesmo, entre palavras
MIN_GAP, MIN_WORD_GAP = 1, 3     # o mais apertado que ainda se lê


class TitleError(ValueError):
    pass


def _luminance(palette):
    return [(v & 31) + ((v >> 5) & 31) + ((v >> 10) & 31) for v in palette]


class Sheet:
    """O pacote da tela de título, com as imagens decodificadas."""

    def __init__(self, subfile):
        self.chunks, self.end = font.read_package(subfile, PACKAGE)
        self.palette = [v for (v,) in struct.iter_unpack('<H', self.chunks[PALETTE_BLOCK]['payload'])]
        lum = _luminance(self.palette)
        order = sorted(range(16), key=lambda i: lum[i])
        self.rank = {index: position for position, index in enumerate(order)}
        self.core_rank = 13          # miolo: os 3 tons mais claros da paleta

    def image(self, block):
        """Pixels (índices da paleta) da imagem: lista de linhas."""
        c = self.chunks[block]
        raw = font.rle_decode(c['payload'], c['w'] * 2 * c['h'])
        pixels = []
        for byte in raw:
            pixels += [byte & 15, byte >> 4]
        width = c['w'] * 4
        return [pixels[y * width:(y + 1) * width] for y in range(c['h'])]

    def width(self, block):
        return self.chunks[block]['w'] * 4

    def is_core(self, index):
        return self.rank[index] >= self.core_rank

    def is_body(self, index):
        """Corpo da letra: os cinzas da paleta (sem o preto do contorno e sem o halo verde,
        que no original faz a transição para a grama)."""
        v = self.palette[index]
        r, g, b = v & 31, (v >> 5) & 31, (v >> 10) & 31
        return index not in (TRANSPARENT, OUTLINE) and max(r, g, b) - min(r, g, b) <= 1

    def core_index(self, block):
        """O tom do miolo mais claro usado na imagem (as imagens variam um pouco)."""
        return max((i for row in self.image(block) for i in row), key=lambda i: self.rank[i])


def segments(sheet, block, count):
    """Colunas (início, fim) do miolo de cada letra da imagem original."""
    img = sheet.image(block)
    width = len(img[0])
    core = [[sheet.is_core(img[y][x]) for x in range(width)] for y in range(HEIGHT)]
    present = [any(core[y][x] for y in range(HEIGHT)) for x in range(width)]

    def link(x):        # pixels de miolo que passam da coluna x para x + 1 (inclusive na diagonal)
        return sum(1 for y in range(HEIGHT) for dy in (-1, 0, 1)
                   if 0 <= y + dy < HEIGHT and core[y][x] and core[y + dy][x + 1])

    found, start = [], None
    for x in range(width):
        if present[x] and start is None:
            start = x
        if start is not None and (x == width - 1 or link(x) == 0):
            found.append((start, x))
            start = None
    while len(found) < count:            # duas letras grudadas: corta onde o miolo é mais fino
        widest = max(range(len(found)), key=lambda k: found[k][1] - found[k][0])
        a, b = found[widest]
        cut = min(range(a + 2, b - 2), key=link)
        found[widest:widest + 1] = [(a, cut), (cut + 1, b)]
    if len(found) != count:
        raise TitleError(f'bloco {block}: {len(found)} letras achadas, esperado {count}')
    return found


class Glyph:
    """Uma letra: colunas de pixels (24 linhas cada) e onde começa e termina o miolo."""

    def __init__(self, columns, core_start, core_end):
        self.columns, self.core_start, self.core_end = columns, core_start, core_end


def labels(sheet, block):
    """Para cada pixel, a letra (posição) dona dele: a do miolo mais próximo, em 2D.

    Uma busca em largura que parte de todos os pixels de miolo ao mesmo tempo, como uma
    mancha que se espalha de cada letra. Assim a barra de um T que avança por cima da
    letra seguinte continua sendo do T."""
    img = sheet.image(block)
    width = len(img[0])
    segs = segments(sheet, block, TARGETS[block][1])
    owner = {}
    frontier = []
    for k, (a, b) in enumerate(segs):
        for x in range(a, b + 1):
            for y in range(HEIGHT):
                if sheet.is_core(img[y][x]):
                    owner[(x, y)] = k
                    frontier.append((x, y))
    while frontier:
        following = []
        for x, y in frontier:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q not in owner and 0 <= q[0] < width and 0 <= q[1] < HEIGHT:
                        owner[q] = owner[(x, y)]
                        following.append(q)
        frontier = following
    return img, segs, owner


def _cut_glyph(sheet, block, position):
    """Só o corpo da letra: os cinzas ligados ao próprio miolo. O contorno é refeito na
    montagem; o halo verde e pedaços da vizinha ficam de fora."""
    img, segs, owner = labels(sheet, block)
    seeds = [(x, y) for (x, y), k in owner.items() if k == position and sheet.is_core(img[y][x])]
    top = min(y for _, y in seeds) - 1          # o corpo vai até a borda do traço; mais longe
    bottom = max(y for _, y in seeds) + 1       # é a linha do contorno (com cinzas de suavização)
    mine, frontier = set(seeds), list(seeds)
    while frontier:
        following = []
        for x, y in frontier:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q not in mine and owner.get(q) == position and top <= q[1] <= bottom \
                            and sheet.is_body(img[q[1]][q[0]]):
                        mine.add(q)
                        following.append(q)
        frontier = following
    left = min(x for x, _ in mine)
    right = max(x for x, _ in mine)
    columns = [[TRANSPARENT] * HEIGHT for _ in range(left, right + 1)]
    for x, y in mine:
        columns[x - left][y] = img[y][x]
    a, b = segs[position]
    return Glyph(columns, a - left, b - left)


def _clear(sheet, glyph, x0, x1, y0, y1):
    for x in range(x0, x1):
        for y in range(y0, y1):
            glyph.columns[x][y] = TRANSPARENT


def _letter_j(sheet, u):
    """J: o U sem a parte de cima da perna esquerda (sobra o gancho embaixo)."""
    j = Glyph([list(c) for c in u.columns], u.core_start, u.core_end)
    middle = (u.core_start + u.core_end) // 2
    _clear(sheet, j, 0, middle, 0, 13)
    return j


def _letter_v(sheet, u):
    """V: o U com as pernas se aproximando na parte de baixo."""
    width = len(u.columns)
    middle = (u.core_start + u.core_end + 1) // 2
    shift = {y: (0 if y < 10 else 1 if y < 13 else 2) for y in range(HEIGHT)}
    columns = [[TRANSPARENT] * HEIGHT for _ in range(width)]
    for y in range(HEIGHT):
        for x in range(width):
            index = u.columns[x][y]
            if index == TRANSPARENT:
                continue
            nx = x + shift[y] if x < middle else x - shift[y]
            if 0 <= nx < width and (columns[nx][y] == TRANSPARENT or
                                    sheet.rank[index] > sheet.rank[columns[nx][y]]):
                columns[nx][y] = index
    return Glyph(columns, u.core_start, u.core_end)


def glyph(sheet, letter):
    if letter in DERIVED:
        base = glyph(sheet, DERIVED[letter])
        return _letter_j(sheet, base) if letter == 'J' else _letter_v(sheet, base)
    if letter not in LETTERS:
        raise TitleError(f'a letra "{letter}" não existe nas imagens da tela de título')
    return _cut_glyph(sheet, *LETTERS[letter])


def compose(sheet, text, width, core_index, gap=GAP, word_gap=WORD_GAP):
    """Monta `text` com as letras do jogo numa imagem de `width` x 24 pixels."""
    canvas = {}
    cursor = None                       # coluna onde termina o miolo da letra anterior
    pending_gap = 0
    for char in text:
        if char == ' ':
            pending_gap = word_gap
            continue
        g = glyph(sheet, char)
        start = 0 if cursor is None else cursor + 1 + (pending_gap or gap)
        pending_gap = 0
        origin = start - g.core_start
        for dx, column in enumerate(g.columns):
            for y, index in enumerate(column):
                if index == TRANSPARENT:
                    continue
                if sheet.is_core(index):
                    index = core_index
                key = (origin + dx, y)
                if key not in canvas or sheet.rank[index] > sheet.rank[canvas[key]]:
                    canvas[key] = index
        cursor = start + (g.core_end - g.core_start)
    for x, y in [p for p, i in canvas.items() if sheet.is_body(i)]:   # contorno preto em volta
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y + dy) not in canvas and 0 <= y + dy < HEIGHT:
                canvas[(x + dx, y + dy)] = OUTLINE
    xs = [x for x, _ in canvas]
    left, right = min(xs), max(xs)
    used = right - left + 1
    if used > width:
        raise TitleError(f'"{text}" ocupa {used} pixels; a imagem tem {width}')
    offset = (width - used) // 2 - left
    rows = [[TRANSPARENT] * width for _ in range(HEIGHT)]
    for (x, y), index in canvas.items():
        rows[y][x + offset] = index
    return rows


def compose_fit(sheet, text, width, core_index):
    """Tenta o espaçamento original e, se não couber, aperta letras e depois palavras."""
    last = None
    for gap, word_gap in ((GAP, WORD_GAP), (MIN_GAP, WORD_GAP), (MIN_GAP, 6), (MIN_GAP, 5),
                          (MIN_GAP, 4), (MIN_GAP, MIN_WORD_GAP)):
        try:
            return compose(sheet, text, width, core_index, gap, word_gap), (gap, word_gap)
        except TitleError as error:
            last = error
    raise last


def check(subfile, texts):
    """{id: [erros]} das traduções dos gráficos (letras que não existem, texto largo demais)."""
    sheet = Sheet(subfile)
    known = {text_id: block for block, (text_id, _) in TARGETS.items()}
    problems = {}
    for text_id, text in texts.items():
        if text_id not in known:
            problems[text_id] = ['esse gráfico não existe (ids: ' + ', '.join(sorted(known)) + ')']
            continue
        block = known[text_id]
        try:
            compose_fit(sheet, text.upper(), sheet.width(block), sheet.core_index(block))
        except TitleError as error:
            problems[text_id] = [str(error)]
    return problems


def encode(rows):
    data = bytearray()
    for row in rows:
        for x in range(0, len(row), 2):
            data.append(row[x] | (row[x + 1] << 4))
    return font.rle_encode(bytes(data))


def build(subfile, texts):
    """Grava no subarquivo 00 (bytearray) as imagens com os textos {id: texto}.

    Devolve {id: (gap, word_gap)} com o espaçamento usado. O pacote não pode passar do
    tamanho original."""
    sheet = Sheet(subfile)
    chunks = [dict(c) for c in sheet.chunks]
    used = {}
    for block, (text_id, _) in TARGETS.items():
        text = texts.get(text_id)
        if not text:
            continue
        rows, spacing = compose_fit(sheet, text.upper(), sheet.width(block), sheet.core_index(block))
        chunks[block] = {**chunks[block], 'kind': font.KIND_RLE, 'payload': encode(rows)}
        used[text_id] = spacing
    package = font.write_package(chunks)
    room = sheet.end - PACKAGE
    if len(package) > room:
        raise TitleError(f'o pacote da tela de título passou {len(package) - room} bytes do espaço original')
    subfile[PACKAGE:PACKAGE + room] = package + bytes(room - len(package))
    return used
