"""Patches no formato VCDIFF (RFC 3284), o formato dos arquivos .xdelta.

Pense num diff do git, só que de bytes: o patch descreve o arquivo novo janela por
janela, com instruções como "copie N bytes do original a partir daqui" (COPY) e
"escreva estes bytes novos" (ADD). Quem aplica (xdelta3, Rom Patcher JS, Delta
Patcher) precisa do arquivo original e reconstrói o traduzido. O patch só carrega o que
mudou, nunca o jogo.

O codificador é o mínimo para imagens do MESMO tamanho, o caso da tradução (tudo é
gravado no lugar): cada janela do resultado usa como origem o mesmo trecho do original.
Ele usa a tabela de códigos padrão da RFC, sem compressão secundária e sem soma de
verificação, o que qualquer decodificador aceita. O decodificador entende a tabela
padrão inteira (inclusive o cache de endereços), para conferir o patch gerado e também
patches feitos pelo xdelta3 sem compressão secundária.
"""

import zlib

MAGIC = b'\xd6\xc3\xc4\x00'      # "VCD" com o bit alto ligado + versão 0
VCD_DECOMPRESS, VCD_CODETABLE, VCD_APPHEADER = 0x01, 0x02, 0x04    # Hdr_Indicator
VCD_SOURCE, VCD_TARGET, VCD_ADLER32 = 0x01, 0x02, 0x04              # Win_Indicator
NOOP, ADD, RUN, COPY = 0, 1, 2, 3

WINDOW = 1 << 20        # 1 MiB por janela do resultado (o xdelta3 aceita até 16 MiB)
BLOCK = 2352            # compara por setor; só os setores diferentes são vistos byte a byte
MERGE_GAP = 8           # trecho igual menor que isso entra no ADD: um COPY custaria mais
ADD_EXPLICIT = 1        # índices da tabela padrão com o tamanho escrito à parte
COPY_EXPLICIT = 19      # (COPY no modo 0: endereço absoluto)
NEAR, SAME = 4, 3       # tamanhos do cache de endereços padrão


def default_code_table():
    """As 256 entradas da tabela padrão: (tipo1, tamanho1, modo1, tipo2, tamanho2, modo2)."""
    table = [(RUN, 0, 0, NOOP, 0, 0)]
    table += [(ADD, size, 0, NOOP, 0, 0) for size in [0] + list(range(1, 18))]
    for mode in range(9):
        table += [(COPY, size, mode, NOOP, 0, 0) for size in [0] + list(range(4, 19))]
    for mode in range(6):
        table += [(ADD, add, 0, COPY, copy, mode) for add in range(1, 5) for copy in range(4, 7)]
    for mode in range(6, 9):
        table += [(ADD, add, 0, COPY, 4, mode) for add in range(1, 5)]
    table += [(COPY, 4, mode, ADD, 1, 0) for mode in range(9)]
    assert len(table) == 256
    return table


CODE_TABLE = default_code_table()


def varint(value):
    """Inteiro em base 128, do dígito mais significativo para o menos (bit 7 = continua)."""
    digits = [value & 0x7F]
    value >>= 7
    while value:
        digits.append(0x80 | (value & 0x7F))
        value >>= 7
    return bytes(reversed(digits))


class Reader:
    def __init__(self, data, pos=0):
        self.data, self.pos = data, pos

    def byte(self):
        if self.pos >= len(self.data):
            raise ValueError('patch VCDIFF truncado')
        self.pos += 1
        return self.data[self.pos - 1]

    def int(self):
        value = 0
        while True:
            digit = self.byte()
            value = (value << 7) | (digit & 0x7F)
            if not digit & 0x80:
                return value

    def bytes(self, size):
        if self.pos + size > len(self.data):
            raise ValueError('patch VCDIFF truncado')
        self.pos += size
        return self.data[self.pos - size:self.pos]


def diff_runs(old, new):
    """Trechos (início, fim) em que `new` difere de `old`, juntando os separados por
    menos de MERGE_GAP bytes iguais."""
    runs = []
    for block in range(0, len(new), BLOCK):
        if old[block:block + BLOCK] == new[block:block + BLOCK]:
            continue
        for pos in range(block, min(block + BLOCK, len(new))):
            if old[pos] != new[pos]:
                if runs and pos - runs[-1][1] < MERGE_GAP:
                    runs[-1][1] = pos + 1
                else:
                    runs.append([pos, pos + 1])
    return runs


def encode_window(old, new, position):
    """Uma janela: o resultado `new` a partir do trecho `old` do original em `position`."""
    data, instructions, addresses = bytearray(), bytearray(), bytearray()
    here = 0

    def copy(start, end):
        instructions.extend(bytes([COPY_EXPLICIT]) + varint(end - start))
        addresses.extend(varint(start))         # modo 0: posição dentro do trecho do original

    for start, end in diff_runs(old, new):
        if start > here:
            copy(here, start)
        instructions.extend(bytes([ADD_EXPLICIT]) + varint(end - start))
        data.extend(new[start:end])
        here = end
    if here < len(new):
        copy(here, len(new))
    delta = (varint(len(new)) + b'\x00' + varint(len(data)) + varint(len(instructions))
             + varint(len(addresses)) + data + instructions + addresses)
    return bytes([VCD_SOURCE]) + varint(len(old)) + varint(position) + varint(len(delta)) + delta


def encode(source, target, out, window=WINDOW):
    """Grava em `out` o patch que transforma `source` em `target` (arquivos abertos em
    modo binário, do mesmo tamanho)."""
    out.write(MAGIC + b'\x00')                  # Hdr_Indicator: nada de extra
    position = 0
    while True:
        new = target.read(window)
        old = source.read(window)
        if len(new) != len(old):
            raise ValueError('o original e o resultado precisam ter o mesmo tamanho')
        if not new:
            return
        out.write(encode_window(old, new, position))
        position += len(new)


def apply(source, patch, out):
    """Aplica o patch VCDIFF (bytes) sobre `source` (arquivo aberto, com seek) e grava
    o resultado em `out`."""
    reader = Reader(patch)
    if reader.bytes(4) != MAGIC:
        raise ValueError('não é um patch VCDIFF (.xdelta)')
    header = reader.byte()
    if header & VCD_DECOMPRESS:
        raise ValueError('patch com compressão secundária: não suportado (use o xdelta3)')
    if header & VCD_CODETABLE:
        raise ValueError('patch com tabela de códigos própria: não suportado')
    if header & VCD_APPHEADER:
        reader.bytes(reader.int())
    while reader.pos < len(patch):
        indicator = reader.byte()
        if indicator & VCD_TARGET:
            raise ValueError('janela que copia do próprio resultado: não suportado')
        old = b''
        if indicator & VCD_SOURCE:
            size, position = reader.int(), reader.int()
            source.seek(position)
            old = source.read(size)
            if len(old) != size:
                raise ValueError('o original é menor do que o patch espera')
        delta = Reader(reader.bytes(reader.int()))
        new_size = delta.int()
        if delta.byte():
            raise ValueError('janela com seções comprimidas: não suportado')
        sizes = delta.int(), delta.int(), delta.int()
        checksum = delta.bytes(4) if indicator & VCD_ADLER32 else None
        data = Reader(delta.bytes(sizes[0]))
        instructions = Reader(delta.bytes(sizes[1]))
        addresses = Reader(delta.bytes(sizes[2]))
        new = _decode_window(old, new_size, data, instructions, addresses)
        if checksum is not None and zlib.adler32(new) != int.from_bytes(checksum, 'big'):
            raise ValueError('soma de verificação de uma janela não confere')
        out.write(new)


def _decode_window(old, new_size, data, instructions, addresses):
    new = bytearray()
    near, near_slot, same = [0] * NEAR, 0, [0] * (SAME * 256)
    while instructions.pos < len(instructions.data):
        entry = CODE_TABLE[instructions.byte()]
        for kind, size, mode in (entry[:3], entry[3:]):
            if kind == NOOP:
                continue
            if size == 0:
                size = instructions.int()
            if kind == ADD:
                new += data.bytes(size)
            elif kind == RUN:
                new += data.bytes(1) * size
            else:
                here = len(old) + len(new)
                if mode == 0:
                    address = addresses.int()
                elif mode == 1:
                    address = here - addresses.int()
                elif mode < 2 + NEAR:
                    address = near[mode - 2] + addresses.int()
                else:
                    address = same[(mode - 2 - NEAR) * 256 + addresses.byte()]
                near[near_slot] = address
                near_slot = (near_slot + 1) % NEAR
                same[address % (SAME * 256)] = address
                if address + size <= len(old):
                    new += old[address:address + size]
                    continue
                for offset in range(size):      # byte a byte: a cópia pode se sobrepor
                    at = address + offset
                    new.append(old[at] if at < len(old) else new[at - len(old)])
    if len(new) != new_size:
        raise ValueError('janela do patch com tamanho errado')
    return bytes(new)
