"""A fonte do jogo e o formato de pacotes de imagem em que ela vem.

Pacote de imagem (assinatura 0x100D): uma lista de cópias para a memória de vídeo.

    u16 0x100D, u16 quantidade de blocos
    cada bloco:  u32 (tipo << 24 | tamanho), u16 x, u16 y, u16 largura, u16 altura, dados
                 e o próximo bloco começa alinhado a 4 bytes

Tipo 0 = dados comprimidos com RLE; tipo 6 = dados crus (paletas). Largura em unidades
de 16 bits da VRAM, como o PS1 conta.

RLE: um byte de comando n seguido de dados.
    n = 0x80..0xFF  copia os próximos 256 - n bytes como estão (1 a 128)
    n = 0x01..0x7F  repete o próximo byte n vezes

A fonte é o último bloco do primeiro pacote do subarquivo 00: uma folha de 128x120
pixels, 4 bits por pixel, com 16 caracteres de 8x12 por linha. O código do caractere
é a posição na folha (0x00 = A no canto superior esquerdo, 0x10 = Q na linha seguinte).
Cada pixel guarda a intensidade da tinta: 0 = fundo, 1 = mais forte, 9 = mais fraca.
"""

import struct

PACKAGE_MAGIC = 0x100D
FONT_SUBFILE = 0
FONT_PACKAGE_OFFSET = 0
PACKAGE_LIMIT = 0x2000          # o pacote ocupa os 4 primeiros setores; depois vêm outros dados
FONT_RECT = (896, 0, 32, 120)   # x, y, largura (unidades de 16 bits), altura
GLYPH_W, GLYPH_H, PER_ROW = 8, 12, 16
ROW_BYTES = FONT_RECT[2] * 2    # 64 bytes por linha de pixels da folha
KIND_RLE = 0


def rle_decode(data, size):
    out = bytearray()
    i = 0
    while len(out) < size:
        n = data[i]
        i += 1
        if n >= 0x80:
            count = 256 - n
            out += data[i:i + count]
            i += count
        elif n:
            out += bytes([data[i]]) * n
            i += 1
        else:
            raise ValueError(f'RLE: comando 0 na posição {i - 1}')
    if len(out) != size:
        raise ValueError(f'RLE: gerou {len(out)} bytes, esperado {size}')
    return bytes(out)


def rle_encode(data):
    out = bytearray()
    literal = bytearray()

    def flush():
        while literal:
            part = literal[:128]
            out.append(256 - len(part))
            out.extend(part)
            del literal[:128]

    i = 0
    while i < len(data):
        run = 1
        while i + run < len(data) and data[i + run] == data[i] and run < 127:
            run += 1
        if run >= 3:
            flush()
            out += bytes([run, data[i]])
        else:
            literal += data[i:i + run]
        i += run
    flush()
    return bytes(out)


def read_package(buf, offset):
    """Devolve (blocos, fim). Cada bloco: dict com kind, x, y, w, h e payload (como no disco)."""
    magic, count = struct.unpack_from('<HH', buf, offset)
    if magic != PACKAGE_MAGIC:
        raise ValueError(f'pacote de imagem não encontrado em {offset:#x}')
    pos = offset + 4
    chunks = []
    for _ in range(count):
        word, x, y, w, h = struct.unpack_from('<IHHHH', buf, pos)
        size = word & 0xFFFFFF
        chunks.append({'kind': word >> 24, 'x': x, 'y': y, 'w': w, 'h': h,
                       'payload': bytes(buf[pos + 12:pos + 12 + size])})
        pos = (pos + 12 + size + 3) & ~3
    return chunks, pos


def write_package(chunks):
    out = bytearray(struct.pack('<HH', PACKAGE_MAGIC, len(chunks)))
    for c in chunks:
        out += struct.pack('<IHHHH', c['kind'] << 24 | len(c['payload']), c['x'], c['y'], c['w'], c['h'])
        out += c['payload']
        out += bytes(-len(out) % 4)
    return bytes(out)


def find_font(chunks):
    for index, c in enumerate(chunks):
        if (c['x'], c['y'], c['w'], c['h']) == FONT_RECT and c['kind'] == KIND_RLE:
            return index
    raise ValueError('bloco da fonte não encontrado no pacote')


class Sheet:
    """A folha da fonte descomprimida, com acesso caractere a caractere."""

    def __init__(self, data):
        self.data = bytearray(data)

    def glyph(self, code):
        """Pixels do caractere: 12 linhas de 8 intensidades."""
        rows = []
        for y in range(GLYPH_H):
            row = []
            for x in range(GLYPH_W):
                px = (code % PER_ROW) * GLYPH_W + x
                byte = self.data[((code // PER_ROW) * GLYPH_H + y) * ROW_BYTES + px // 2]
                row.append(byte >> 4 if px & 1 else byte & 15)
            rows.append(row)
        return rows

    def set_glyph(self, code, rows):
        for y, row in enumerate(rows):
            for x, value in enumerate(row):
                px = (code % PER_ROW) * GLYPH_W + x
                at = ((code // PER_ROW) * GLYPH_H + y) * ROW_BYTES + px // 2
                if px & 1:
                    self.data[at] = (self.data[at] & 0x0F) | value << 4
                else:
                    self.data[at] = (self.data[at] & 0xF0) | value

    def is_blank(self, code):
        return all(v == 0 for row in self.glyph(code) for v in row)
