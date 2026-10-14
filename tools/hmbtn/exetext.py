"""Textos do executável SLUS_011.15 (menus, comidas, lojas, sementes, memory card) e dos
overlays dos minigames.

Ficam colados em dois blocos, cada um terminado por FFFF. O jogo chega a eles por
caminhos variados (endereço absoluto em overlays, deslocamento a partir do início do
bloco guardado em tabelas ou variáveis), e nem todas as referências foram mapeadas
(docs/06-textos-do-executavel.md). Por isso a tradução é gravada NO LUGAR: cada texto
continua começando e terminando no mesmo endereço. Se a tradução for mais curta, o
fim é completado com espaços antes do FFFF; nunca pode ser mais longa.
"""

import re
import struct

EXE_BASE = 0x80010000           # endereço da RAM onde o corpo do executável é carregado
HEADER = 0x800                  # cabeçalho PS-X EXE antes do corpo
BLOCKS = ((0x8005175C, 0x80054BBA),   # menus, mensagens, comidas, lojas, sementes
          (0x800556B6, 0x800558A2))   # nomes de animais e competidores
# Textos soltos nos overlays (subarquivos do A_FILE carregados sob demanda pelos
# minigames). Nomes próprios de competidores ficam de fora. Mesma regra: no lugar.
OVERLAY_STRINGS = {
    11: (0x7035C,),                                    # sair da mina
    17: (0x03662, 0x0367A, 0x03684, 0x03694),          # apostas da corrida de cavalos
    21: (0x04CB8,),                                    # minigame de arremesso
    23: (0x03A66, 0x03A8A, 0x03AAC, 0x03ACE, 0x03AF8,  # competidores "Fazenda X: nome"
         0x03B28, 0x03B54, 0x03B76, 0x03BA2),
    25: (0x04D6E,),
}
END = 0xFFFF
SPACE = 0x0FFD
CODE = re.compile(r'\{([^{}]*)\}')


def file_offset(address):
    return address - EXE_BASE + HEADER


def segments(exe):
    """(endereço, bytes sem o FFFF) de cada texto dos blocos, em ordem."""
    for start, end in BLOCKS:
        pos = file_offset(start)
        limit = file_offset(end)
        begin = pos
        while pos < limit:
            if struct.unpack_from('<H', exe, pos)[0] == END:
                yield EXE_BASE + begin - HEADER, bytes(exe[begin:pos])
                begin = pos + 2
            pos += 2


def overlay_segments(subfile_index, data):
    """(id, deslocamento, bytes sem o FFFF) dos textos de um overlay."""
    for start in OVERLAY_STRINGS.get(subfile_index, ()):
        pos = start
        while struct.unpack_from('<H', data, pos)[0] != END:
            pos += 2
        yield overlay_id(subfile_index, start), start, bytes(data[start:pos])


def overlay_id(subfile_index, offset):
    return f'ov{subfile_index:02d}-{offset:05X}'


def write_at(data, offset, encoded, original_len):
    """Como write(), mas por deslocamento dentro de um arquivo qualquer."""
    if len(encoded) > original_len:
        raise ValueError(f'{offset:#x}: maior que o original')
    padding = struct.pack('<H', SPACE) * ((original_len - len(encoded)) // 2)
    data[offset:offset + original_len] = encoded + padding
    if struct.unpack_from('<H', data, offset + original_len)[0] != END:
        raise ValueError(f'{offset:#x}: o terminador original não está onde deveria')


def is_text(decoded):
    """Separa texto de verdade de dados que só parecem texto."""
    letters = len(re.findall(r'[A-Za-z]', CODE.sub('', decoded)))
    return letters >= 2


def entry_id(address):
    return f'exe-{address:08X}'


def validate(en, pt, allowed, max_units):
    """Erros de uma tradução de texto do executável."""
    errors = []
    plain = CODE.sub('', pt)
    bad = sorted({ch for ch in plain if ch not in allowed and ch != '\n'})
    if bad:
        errors.append('caracteres não permitidos: ' + ', '.join(repr(ch) for ch in bad))
    if '...' in plain:
        errors.append('use o caractere único … em vez de ...')
    if sorted(CODE.findall(en)) != sorted(CODE.findall(pt)):
        errors.append(f'códigos diferentes do original: esperado {sorted(CODE.findall(en))}, '
                      f'encontrado {sorted(CODE.findall(pt))}')
    lines_en, lines_pt = en.split('\n'), pt.split('\n')
    leading_en = [line.startswith(' ') for line in lines_en]
    if any(leading_en):
        # opções de menu e títulos alinhados com espaços: mesma estrutura de linhas
        if len(lines_pt) != len(lines_en):
            errors.append(f'{len(lines_pt)} linhas, o original tem {len(lines_en)} (uma opção por linha)')
        elif leading_en != [line.startswith(' ') for line in lines_pt]:
            errors.append('as linhas que começam com espaço no original devem continuar com espaço')
    elif len(lines_pt) > len(lines_en):
        errors.append(f'{len(lines_pt)} linhas, o original tem {len(lines_en)}')
    units = len(CODE.sub('#', pt))
    if units > max_units:
        errors.append(f'longo demais: {units} caracteres, o espaço do original é {max_units} '
                      f'(textos do executável não podem crescer)')
    return errors


def write(exe, address, encoded, original_len):
    """Grava no lugar: texto + espaços até o tamanho original + o FFFF de sempre."""
    try:
        write_at(exe, file_offset(address), encoded, original_len)
    except ValueError as error:
        raise ValueError(f'{entry_id(address)}: {error}') from None
