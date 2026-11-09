"""Procura textos do jogo que ainda não são extraídos (e, portanto, nem traduzidos).

Um texto do jogo é uma sequência de valores de 16 bits da tabela, terminada em FFFF.
A varredura passa por todos os subarquivos do A_FILE e pelo executável, guarda o que
parece texto em inglês (letras, espaços e pontuação, mais minúsculas que maiúsculas) e
descarta o que já é coberto: a área de texto dos registros de falas, os blocos de texto
do executável, os textos dos minigames (`exetext.OVERLAY_STRINGS`) e a lista IGNORED.

É uma heurística: dados binários às vezes parecem texto. O que sobrar precisa ser
conferido à mão.
"""

import struct

from . import dialog, exetext

UPPER = frozenset(range(0x00, 0x1A))
LOWER = frozenset(range(0x20, 0x3A))
OTHER = frozenset(list(range(0x40, 0x4A)) + list(range(0x50, 0x57)) + [
    0x62, 0x63, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x71, 0x74, 0x76, 0x7F, 0x80,
    0x8C, 0x8D, 0x8E, 0x8F, 0x0FFD, 0xFFFE])
END = 0xFFFF
MIN_LOWER = 2           # letras minúsculas mínimas
MAX_UNITS = 1100        # mais que isso não é texto (uma fala tem no máximo 1023 valores)

# Achados conferidos que ficam de fora de propósito: (onde, início, fim, motivo).
# `onde` é 'exe' (posição no arquivo do executável) ou o número do subarquivo.
IGNORED = (
    ('exe', 0x45EA8, 0x45EB6, 'nome de animal, colado no bloco de nomes'),
    (11, 0x6E33A, 0x6E348, 'dados: pedaço do alfabeto'),
    (11, 0x70178, 0x701B2, 'nomes das moças'),
    (19, 0x04F48, 0x05076, 'nomes das galinhas competidoras'),
)


def _allowed(value):
    return (value in UPPER or value in LOWER or value in OTHER or 0x0F00 <= value <= 0x0FFF
            or 0x4000 <= value <= 0x40FF)


def candidates(data):
    """(posição, bytes sem o FFFF) de cada trecho que parece texto em inglês."""
    values = struct.unpack_from(f'<{len(data) // 2}H', data)
    start = None
    for i, value in enumerate(values):
        if value == END:
            if start is not None:
                while start < i and values[start] not in UPPER and values[start] not in LOWER:
                    start += 1          # pontuação ou dados antes da primeira letra
                run = values[start:i]
                lower = sum(1 for x in run if x in LOWER)
                upper = sum(1 for x in run if x in UPPER)
                common = max((run.count(x) for x in set(run)), default=0)
                if (lower >= MIN_LOWER and len({x for x in run if x in LOWER}) >= 3
                        and lower + upper >= len(run) / 2 and lower >= upper
                        and len(run) <= MAX_UNITS and common <= 0.35 * len(run)):
                    yield start * 2, bytes(data[start * 2:i * 2])
            start = None
        elif _allowed(value):
            if start is None:
                start = i
        else:
            start = None


def _covered(where, offset):
    for place, start, end, _ in IGNORED:
        if place == where and start <= offset < end:
            return True
    if where == 'exe':
        return any(exetext.file_offset(a) <= offset <= exetext.file_offset(b)
                   for a, b in exetext.BLOCKS)
    if where in dialog.SUBFILES and offset % dialog.RECORD_SIZE >= dialog.TEXT_OFFSET:
        return True
    return offset in exetext.OVERLAY_STRINGS.get(where, ())


def untracked(exe, subfiles):
    """[(onde, posição, bytes)] dos textos que parecem do jogo e não são extraídos."""
    found = [('exe', offset, raw) for offset, raw in candidates(exe)
             if not _covered('exe', offset)]
    for number, data in enumerate(subfiles):
        found += [(number, offset, raw) for offset, raw in candidates(data)
                  if not _covered(number, offset)]
    return found
