"""Mapa de referências dos textos do executável: onde o jogo guarda o endereço de cada um.

Um texto só pode mudar de lugar se todas as referências a ele forem conhecidas: é como
mover uma página de um site, que obriga a atualizar todos os links que apontam para ela.
A varredura procura, no executável e nos subarquivos com código (overlays):

- `addiu`: instrução que monta o endereço do texto a partir de um `lui 0x8005` ou do
  endereço de outro texto que já está no registrador. O valor montado é o endereço menos
  `delta`: 0 ou `exetext.BASE_DELTA`, quando o código soma depois a palavra de
  `exetext.BASE_WORD` (docs/06, "Endereços somados");
- `leitura`: instrução que lê bytes direto do começo do texto. Ou o "texto" é na verdade
  um dado, ou o código depende do conteúdo: esse texto nunca anda;
- `tabela`: valor de 16 bits igual a endereço - `exetext.TXT_BASE`, numa tabela de pelo
  menos 4 entradas com passo fixo de até 8 bytes e valores crescentes, ou na tabela de
  receitas. Sequências mais curtas, com passo maior ou fora de ordem apareceram no meio
  de código (pedaços de instruções que coincidem com deslocamentos) e são descartadas.

Os valores dos registradores são acompanhados em linha reta a partir de cada `lui`
(propagação de constantes), sem seguir desvios. É uma heurística: uma referência montada
longe do `lui`, ou por um caminho diferente, escapa. Por isso todo texto que anda precisa
ser conferido no jogo.

O mapa depende só do disco original. O comando `refs` o grava em `build/refs.json`
(fora do git), e o `check` e o `build` o reaproveitam.
"""

import json
import re
import struct
from collections import defaultdict

from . import exetext

VERSION = 2                     # mude quando a varredura mudar: o cache é refeito
WINDOW = 120                    # instruções acompanhadas depois de cada lui
TABLE_STEPS = (2, 4, 6, 8)
TABLE_MIN = 4                   # entradas seguidas, em ordem crescente, para valer como tabela
TABLE_MIN_VALUE = 0x20          # deslocamentos menores são comuns demais em dados
LUI = re.compile(rb'[\x05\x06]\x80[\x00-\x1f]\x3c')    # lui rX, 0x8005 ou 0x8006
JR_RA = b'\x08\x00\xe0\x03'


def _s16(value):
    return value - 0x10000 if value & 0x8000 else value


def code_subfiles(subfiles):
    """Números dos subarquivos que têm código (pelo menos um `jr ra` alinhado)."""
    found = []
    for number, data in enumerate(subfiles):
        pos = data.find(JR_RA)
        while pos >= 0 and pos % 4:
            pos = data.find(JR_RA, pos + 1)
        if pos >= 0:
            found.append(number)
    return found


class _Collector:
    def __init__(self, starts):
        self.starts = starts                    # endereço -> id
        self.refs = defaultdict(dict)           # id -> {(onde, pos): ref}
        self.seen = {}                          # (onde, pos) -> id
        self.conflicts = set()

    def texts_at(self, value):
        """[(id, delta)] dos textos que começam em `value` + delta."""
        return [(self.starts[(value + delta) & 0xFFFFFFFF], delta) for delta in (0, exetext.BASE_DELTA)
                if (value + delta) & 0xFFFFFFFF in self.starts]

    def text_at(self, value, prefer=None):
        """(id, delta) do texto em `value` + delta. Se os dois deltas acharem texto, vale o
        `prefer` (o delta da base); sem ele, a leitura é ambígua e os dois ficam presos."""
        hits = self.texts_at(value)
        if len(hits) == 2:
            chosen = [hit for hit in hits if hit[1] == prefer]
            if chosen:
                return chosen[0]
            self.conflicts.update(sid for sid, _ in hits)
            return None
        return hits[0] if hits else None

    def add(self, sid, ref):
        key = (ref['where'], ref['pos'])
        other = self.seen.get(key)
        if other is not None and (other != sid or self.refs[sid][key] != ref):
            self.conflicts.update({sid, other})
            return
        self.seen[key] = sid
        self.refs[sid][key] = ref


def _scan_code(collector, where, data):
    for match in LUI.finditer(data):
        start = match.start()
        if start % 4:
            continue
        word = struct.unpack_from('<I', data, start)[0]
        known = {(word >> 16) & 31: (word & 0xFFFF) << 16}
        for step in range(1, WINDOW):
            pc = start + 4 * step
            if pc + 4 > len(data):
                break
            word = struct.unpack_from('<I', data, pc)[0]
            op, rs, rt, rd = word >> 26, (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
            funct = word & 63
            target, value = None, None
            if op == 0x09:                                      # addiu
                target = rt
                if rs in known:
                    value = (known[rs] + _s16(word & 0xFFFF)) & 0xFFFFFFFF
                    base = collector.text_at(known[rs])
                    hit = collector.text_at(value, prefer=base[1] if base else None)
                    if hit:
                        collector.add(hit[0], {
                            'kind': 'addiu', 'where': where, 'pos': pc, 'delta': hit[1],
                            'base': base[0] if base else known[rs],
                            'base_delta': base[1] if base else 0})
            elif op in (0x20, 0x21, 0x23, 0x24, 0x25):            # lb lh lw lbu lhu
                target = rt
                if rs in known:
                    hit = collector.text_at((known[rs] + _s16(word & 0xFFFF)) & 0xFFFFFFFF)
                    if hit:
                        collector.add(hit[0], {'kind': 'leitura', 'where': where, 'pos': pc})
            elif op == 0x0F:                                    # lui
                target, value = rt, (word & 0xFFFF) << 16
            elif op == 0 and funct in (0x20, 0x21, 0x25) and rt == 0 and rs in known:
                target, value = rd, known[rs]                   # move
            elif op == 0 and funct == 0x08:                     # jr: fim da função
                break
            elif op == 0:
                target = rd
            elif op in (0x08, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E):
                target = rt
            if target:
                if value is None:
                    known.pop(target, None)
                else:
                    known[target] = value
            if not known:
                break


def _scan_tables(collector, where, data, skip=()):
    values = struct.unpack_from(f'<{len(data) // 2}H', data)
    hits, values_at = {}, {}
    for index, value in enumerate(values):
        if value >= TABLE_MIN_VALUE and exetext.TXT_BASE + value in collector.starts:
            pos = index * 2
            if not any(a <= pos < b for a, b in skip):
                hits[pos] = collector.starts[exetext.TXT_BASE + value]
                values_at[pos] = value
    for step in TABLE_STEPS:
        for pos in sorted(hits):
            if pos - step in hits:
                continue                                        # não é o começo da tabela
            run = [pos]
            while run[-1] + step in hits:
                run.append(run[-1] + step)
            values = [values_at[p] for p in run]
            if len(run) >= TABLE_MIN and all(a < b for a, b in zip(values, values[1:])):
                for p in run:
                    collector.add(hits[p], {'kind': 'tabela', 'where': where, 'pos': p})


def find(exe, subfiles):
    """{id: [ref, ...]} para os textos do executável; textos em conflito ganham uma
    referência do tipo 'conflito' (duas leituras diferentes da mesma instrução)."""
    starts = {address: exetext.entry_id(address) for address, _ in exetext.segments(exe)}
    collector = _Collector(starts)
    blocks = [(exetext.file_offset(a), exetext.file_offset(b) + 2) for a, b in exetext.BLOCKS]
    _scan_code(collector, 'exe', exe)
    _scan_tables(collector, 'exe', exe, skip=blocks)
    for number in code_subfiles(subfiles):
        _scan_code(collector, number, subfiles[number])
        _scan_tables(collector, number, subfiles[number])
    for address, positions in exetext.recipe_refs(exe).items():
        for pos in positions:
            collector.add(starts[address], {'kind': 'tabela', 'where': 'exe', 'pos': pos})
    result = {sid: sorted(refs.values(), key=lambda r: (str(r['where']), r['pos']))
              for sid, refs in collector.refs.items()}
    for sid in collector.conflicts:
        result.setdefault(sid, []).append({'kind': 'conflito', 'where': None, 'pos': None})
    return result


movable = exetext.movable


def save(path, refs):
    path.write_text(json.dumps({'version': VERSION, 'refs': refs}, ensure_ascii=False, indent=1))


def load(path):
    """O mapa salvo, ou None se não existir ou for de outra versão da varredura."""
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if data.get('version') != VERSION:
        return None
    return data['refs']
