r"""Tabela de caracteres do jogo (valor de 16 bits <-> texto).

O jogo não usa ASCII: cada caractere é um número de 16 bits (little-endian) que
aponta para um desenho na fonte. A tabela fica em tables/hmbtn.tbl, uma entrada por
linha no formato `HEX=texto` (ex.: `0000=A`). Linhas começando com # são comentários.
No texto, `\s` vira espaço e `\n` quebra de linha (para não depender de espaço no fim
da linha, que editores costumam apagar).

Códigos de controle (fim de fala, nome do jogador...) são escritos entre chaves,
ex.: `FFFF={fim}`. Valores que não estão na tabela aparecem como `{XXXX}`, então
decode -> encode sempre devolve os bytes originais.
"""

import re
import struct

_RAW = re.compile(r'\{([0-9A-Fa-f]{4})\}')
_ESCAPES = {r'\s': ' ', r'\n': '\n'}


class Table:
    def __init__(self, path):
        self.decode_map = {}
        self.encode_map = {}
        with open(path, encoding='utf-8') as f:
            for lineno, line in enumerate(f, 1):
                line = line.rstrip('\n')
                if not line or line.startswith('#'):
                    continue
                code, sep, text = line.partition('=')
                if not sep or not text:
                    raise ValueError(f'{path}:{lineno}: linha inválida: {line!r}')
                text = _ESCAPES.get(text, text)
                value = int(code, 16)
                if value in self.decode_map:
                    raise ValueError(f'{path}:{lineno}: código {code} repetido')
                self.decode_map[value] = text
                self.encode_map.setdefault(text, value)
        # na codificação, o texto mais longo tem prioridade ("'s" antes de "'")
        self._longest = max(len(t) for t in self.encode_map)

    def decode(self, data):
        values = struct.unpack(f'<{len(data) // 2}H', data[:len(data) // 2 * 2])
        return ''.join(self.decode_map.get(v, f'{{{v:04X}}}') for v in values)

    def decode_exact(self, data):
        """Como decode, mas garante que encode(resultado) devolve exatamente `data`.

        Ex.: o jogo às vezes escreve "'" + "s" (dois caracteres) em vez do caractere
        único "'s". Os dois viram o mesmo texto, então o encode escolheria o errado.
        Nesses pontos o valor sai cru ({008D}) para não perder a diferença.
        """
        values = list(struct.unpack(f'<{len(data) // 2}H', data[:len(data) // 2 * 2]))
        raw = set()
        while True:
            text = ''.join(f'{{{v:04X}}}' if i in raw or v not in self.decode_map
                           else self.decode_map[v] for i, v in enumerate(values))
            encoded = self.encode(text)
            if encoded == data:
                return text
            back = struct.unpack(f'<{len(encoded) // 2}H', encoded)
            first = next(i for i, (a, b) in enumerate(zip(values, back)) if a != b)
            raw.add(first)

    def encode(self, text):
        out = []
        i = 0
        while i < len(text):
            raw = _RAW.match(text, i)
            if raw:
                out.append(int(raw.group(1), 16))
                i = raw.end()
                continue
            for size in range(min(self._longest, len(text) - i), 0, -1):
                value = self.encode_map.get(text[i:i + size])
                if value is not None:
                    out.append(value)
                    i += size
                    break
            else:
                raise ValueError(f'caractere sem entrada na tabela: {text[i]!r} (posição {i})')
        return struct.pack(f'<{len(out)}H', *out)
