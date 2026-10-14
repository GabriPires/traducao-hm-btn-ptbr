"""Letras acentuadas do português, montadas a partir das letras originais da fonte.

Nenhum desenho original do jogo fica no repositório: na hora do build pegamos a letra
base da própria fonte do disco e acrescentamos a marca (acento ou cedilha), que é
desenho nosso. Segue o estilo que o próprio jogo usou nas letras alemãs da folha:

- minúscula: corpo da letra intacto (linhas 3 a 10), acento nas linhas 1 e 2;
- maiúscula: a letra perde duas linhas iguais do meio (as listadas em `drop`), desce
  para as linhas 2 a 10 e o acento ocupa as linhas 0 e 1;
- cedilha: por baixo da letra, na linha 11, sem mexer no corpo.

Os desenhos usam a mesma escala de intensidade da fonte: 1 = tinta mais forte,
2, 4..8 = intermediários, 9 = mais fraca, '.' = fundo.
"""

# Marcas de duas linhas, 8 pixels de largura cada.
MARKS = {
    'acute':      ('....18..',
                   '...18...'),
    'grave':      ('..81....',
                   '...81...'),
    'circumflex': ('...11...',
                   '..1..1..'),
    'tilde':      ('..11..1.',
                   '.1..11..'),
}
CEDILLA = '..81....'

# caractere: (código na fonte, letra base, marca, opções)
# Os códigos são espaços vazios da folha (0x1A, 0x1C, 0x1D, 0x3A–0x3F, 0x4A–0x4F,
# 0x5E, 0x5F) ou letras alemãs que o jogo não usa (0x57–0x5D). 0x1B e 0x1E ficam
# de fora: estão vazios, mas aparecem no texto original com alguma função.
GLYPHS = {
    'á': (0x3A, 'a', 'acute', {}),
    'à': (0x3B, 'a', 'grave', {}),
    'â': (0x3C, 'a', 'circumflex', {}),
    'ã': (0x3D, 'a', 'tilde', {}),
    'é': (0x3E, 'e', 'acute', {}),
    'ê': (0x3F, 'e', 'circumflex', {}),
    'í': (0x4A, 'i', 'acute', {'dotless': True, 'shift': 1}),
    'ó': (0x4B, 'o', 'acute', {}),
    'ô': (0x4C, 'o', 'circumflex', {}),
    'õ': (0x4D, 'o', 'tilde', {}),
    'ú': (0x4E, 'u', 'acute', {}),
    'ç': (0x4F, 'c', 'cedilla', {}),
    'É': (0x57, 'E', 'acute', {'drop': (2, 6)}),
    'À': (0x58, 'A', 'grave', {'drop': (1, 9)}),
    'Á': (0x59, 'A', 'acute', {'drop': (1, 9)}),
    'Ó': (0x5A, 'O', 'acute', {'drop': (3, 5)}),
    'Ç': (0x5B, 'C', 'cedilla', {}),
    'Ê': (0x5C, 'E', 'circumflex', {'drop': (2, 6)}),
    'Í': (0x5D, 'I', 'acute', {'drop': (3, 6)}),
    'Ú': (0x5E, 'U', 'acute', {'drop': (1, 4)}),
    'Ô': (0x5F, 'O', 'circumflex', {'drop': (3, 5)}),
    'Â': (0x1A, 'A', 'circumflex', {'drop': (1, 9)}),
    'Ã': (0x1C, 'A', 'tilde', {'drop': (1, 9)}),
    'Õ': (0x1D, 'O', 'tilde', {'drop': (3, 5)}),
}


def _pattern(text):
    return [0 if ch == '.' else int(ch, 16) for ch in text]


def build(base, mark, options):
    """Monta o novo caractere a partir das linhas (12x8) da letra base."""
    rows = [list(row) for row in base]
    if mark == 'cedilla':
        # a perna da cedilha encosta na curva de baixo da letra
        rows[11] = _pattern(CEDILLA)
        rows[10][3] = max(rows[10][3], 2) if rows[10][3] else 2
        return rows
    top, bottom = (_pattern(line) for line in MARKS[mark])
    if 'drop' in options:
        body = [row for y, row in enumerate(rows[:11]) if y not in options['drop']]
        return [top, bottom] + body + [rows[11]]
    if options.get('dotless'):
        for y in range(0, 5):
            rows[y] = [0] * 8
    start = 1 + options.get('shift', 0)
    rows[start], rows[start + 1] = top, bottom
    return rows


def apply(sheet, table):
    """Desenha todas as letras acentuadas na folha. `table` traduz letra base -> código."""
    for char, (code, base, mark, options) in GLYPHS.items():
        if not sheet.is_blank(code) and not 0x57 <= code <= 0x5D:
            raise ValueError(f'{char}: o espaço {code:#04x} da fonte não está vazio')
        sheet.set_glyph(code, build(sheet.glyph(table[base]), mark, options))
