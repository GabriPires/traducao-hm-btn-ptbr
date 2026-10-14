"""Quem fala em cada página de uma fala, a partir de tables/personagens.tsv.

No começo de uma página, o primeiro código, se for um retrato (0E30–0FEF), é quem
fala (ex.: `{0F8D}{0FF7}{0F8B}Who's that, May?` é o Barley falando). Página sem
retrato continua com quem falava antes. Falas sem nenhum retrato (prefixo {0FF6},
{0FF3}, {0FF1}) são pensamentos, vozes fora de cena, descrições ou TV. Uma página
aberta por {0FFC}{0FFA}, ou que começa com {0FF6} depois da primeira, é um menu de
respostas do jogador.
"""

import re

PAGE_BREAK = re.compile(r'(\{0FFC\}\{0FF[AB]\})')
LEADING = re.compile(r'\n?((?:\{0[EF][0-9A-F]{2}\})*)')
NO_PORTRAIT = 'sem retrato'
OPTIONS = 'opções do jogador'


class Speakers:
    def __init__(self, path):
        self.ranges = []
        with open(path, encoding='utf-8') as f:
            for line in f:
                if not line.strip() or line.startswith('#'):
                    continue
                start, end, name, gender, *_ = line.rstrip('\n').split('\t')
                self.ranges.append((int(start, 16), int(end, 16), name, gender))

    def lookup(self, code):
        """(nome, gênero) do retrato, ou None se o código não está na tabela."""
        for start, end, name, gender in self.ranges:
            if start <= code <= end:
                return name, gender
        return None

    def label(self, code):
        found = self.lookup(code)
        return f'{found[0]} ({found[1]})' if found else f'retrato {code:04X} (desconhecido)'

    def per_page(self, prefix, text):
        """Uma etiqueta por página da fala, na mesma ordem das páginas de `text`."""
        parts = PAGE_BREAK.split(prefix + text)
        pages = [('', parts[0])] + [(parts[i], parts[i + 1]) for i in range(1, len(parts), 2)]
        labels, current = [], NO_PORTRAIT
        for number, (opener, body) in enumerate(pages):
            codes = [int(c, 16) for c in re.findall(r'\{(0[EF][0-9A-F]{2})\}', LEADING.match(body).group(1))]
            if codes and is_portrait(codes[0]):
                current = self.label(codes[0])
            elif opener == '{0FFC}{0FFA}' or (number and codes and codes[0] == 0x0FF6):
                labels.append(OPTIONS)
                continue
            labels.append(current)
        return labels


def is_portrait(code):
    return 0x0E30 <= code < 0x0FF0
