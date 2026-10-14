"""Registros de diálogo dos subarquivos 02–06 do A_FILE.

Cada subarquivo é uma sequência de registros de 8 KB (0x2000 bytes, 4 setores):

    0x0000  retrato: ID de 4 bytes + imagem   (ou FF FF FF FF quando não há retrato)
    0x1800  texto: valores de 16 bits até um FFFF, o resto do setor é zero

O jogo acha o registro pela posição (número do registro × 0x2000), sem tabela de
ponteiros. Por isso, desde que cada texto continue cabendo no seu setor de 2 KB, dá
para trocar o texto sem mexer em mais nada.
"""

import struct

SUBFILES = (2, 3, 4, 5, 6)
RECORD_SIZE = 0x2000
TEXT_OFFSET = 0x1800
TEXT_SIZE = RECORD_SIZE - TEXT_OFFSET
MAX_VALUES = TEXT_SIZE // 2 - 1      # 1023 valores + o FFFF final
END = 0xFFFF


def record_count(subfile):
    if len(subfile) % RECORD_SIZE:
        raise ValueError(f'tamanho {len(subfile)} não é múltiplo de {RECORD_SIZE:#x}')
    return len(subfile) // RECORD_SIZE


def read_text(subfile, index):
    """Bytes do texto do registro, sem o FFFF final."""
    start = index * RECORD_SIZE + TEXT_OFFSET
    sector = subfile[start:start + TEXT_SIZE]
    for pos in range(0, TEXT_SIZE, 2):
        if struct.unpack_from('<H', sector, pos)[0] == END:
            return sector[:pos]
    raise ValueError(f'registro {index}: texto sem FFFF')


def write_text(subfile, index, text):
    """Grava o texto (sem FFFF) no registro de um bytearray, completando com zeros."""
    if len(text) // 2 > MAX_VALUES:
        raise ValueError(f'registro {index}: {len(text) // 2} valores, máximo {MAX_VALUES}')
    start = index * RECORD_SIZE + TEXT_OFFSET
    sector = text + struct.pack('<H', END)
    subfile[start:start + TEXT_SIZE] = sector + bytes(TEXT_SIZE - len(sector))


def decode_record(table, subfile, index):
    """Devolve (prefixo, texto) de um registro, ambos já decodificados."""
    raw = read_text(subfile, index)
    values = struct.unpack(f'<{len(raw) // 2}H', raw)
    cut = split_prefix(values) * 2
    return table.decode_exact(raw[:cut]), table.decode_exact(raw[cut:])


def split_prefix(values):
    """Separa os códigos de controle do início (quem fala, retrato, tipo de caixa).

    São os valores 0E00–0FFF do começo, exceto 0FFD, que é o espaço.
    """
    n = 0
    while n < len(values) and 0x0E00 <= values[n] <= 0x0FFF and values[n] != 0x0FFD:
        n += 1
    return n
