"""O pacote A_FILE.BIN e seu índice A_FILE.HDT.

O HDT é uma lista de inteiros de 32 bits (little-endian). Cada um é a posição, em
bytes, onde um subarquivo começa dentro do A_FILE.BIN. O último valor é o tamanho
total do pacote, então N+1 valores descrevem N subarquivos. Todas as posições são
múltiplas de 2048 (alinhadas a setor), o que permite ao jogo ler direto do CD.
"""

import struct

ALIGN = 2048


def parse_hdt(hdt):
    count = len(hdt) // 4
    return list(struct.unpack(f'<{count}I', hdt[:count * 4]))


def split(afile, offsets):
    if offsets[-1] != len(afile):
        raise ValueError(f'último offset do HDT ({offsets[-1]}) != tamanho do A_FILE ({len(afile)})')
    return [afile[offsets[i]:offsets[i + 1]] for i in range(len(offsets) - 1)]


def build(subfiles):
    """Monta (hdt, afile) a partir da lista de subarquivos, alinhando cada um a 2048."""
    offsets = [0]
    body = bytearray()
    for data in subfiles:
        body += data
        body += bytes(-len(body) % ALIGN)
        offsets.append(len(body))
    hdt = struct.pack(f'<{len(offsets)}I', *offsets)
    return hdt, bytes(body)
