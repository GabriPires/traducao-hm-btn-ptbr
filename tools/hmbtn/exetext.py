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
from collections import defaultdict

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


TXT_BASE = BLOCKS[0][0]         # a tabela de receitas guarda deslocamentos a partir daqui
RECIPE_NAMES = (0x40B5C, 0x4173C, 0x20)   # campo de nome de cada receita (posição no corpo do EXE)
FOODS = (0x80053DD6, 0x80054396)          # nomes de comidas, todos citados pela tabela de receitas

# Grupos reorganizados: textos vizinhos regravados um depois do outro. O primeiro nunca
# sai do lugar; cada um que anda tem as referências corrigidas; o grupo termina onde
# terminava (quem conta terminadores continua achando o texto certo). Assim um texto
# pode crescer usando o espaço que sobra nos vizinhos. Referências:
#   ('ovNN', pos)  instrução addiu no subarquivo NN que monta o endereço do texto
#   'receitas'     entradas da tabela de receitas que apontam para o texto
# Um texto em `sem_referencia` pode andar sem correção: deve ficar vazio, e quem
# apontar para o começo antigo cai no FFFF do texto anterior (texto vazio).
GROUPS = (
    {'nome': 'Sim/Não da caixa de confirmação (usa o espaço do ordinal "st")',
     'ids': ('exe-8005175C', 'exe-8005176E'), 'refs': {}, 'sem_referencia': {'exe-8005176E'}},
    {'nome': 'menu da fazenda: Lista, Ajuda, Faltam',
     'ids': ('exe-80053604', 'exe-8005360E', 'exe-80053618'),
     'refs': {'exe-8005360E': [('ov11', 0x45544)], 'exe-80053618': [('ov11', 0x4570C)]},
     'sem_referencia': set()},
    {'nome': 'Sim/Não dos diários + "Diary"',
     'ids': ('exe-80051D80', 'exe-80051D8E'), 'refs': {'exe-80051D8E': [('ov15', 0x08F40)]},
     'sem_referencia': set()},
    {'nome': 'Não da configuração + nomes de comidas',
     'ids': ('exe-80053DD0', 'comidas'), 'refs': 'receitas', 'sem_referencia': set()},
)


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


def _s16(value):
    return value - 0x10000 if value & 0x8000 else value


def recipe_refs(exe):
    """{endereço do texto: [posições no arquivo]} das entradas da tabela de receitas."""
    refs = defaultdict(list)
    first, last, step = RECIPE_NAMES
    for pos in range(first, last + 1, step):
        at = HEADER + pos
        refs[TXT_BASE + struct.unpack_from('<H', exe, at)[0]].append(at)
    return refs


def plan(exe, subfiles, table, translations, allowed):
    """Decide como gravar as traduções do executável.

    Devolve (gravações, correções, erros, avisos): gravações = [(posição no EXE, bytes)],
    correções = [(alvo, posição, bytes)] com alvo 'exe' ou o número do subarquivo,
    erros/avisos = {id: [mensagens]}.
    """
    segs = [(entry_id(address), address, raw) for address, raw in segments(exe)]
    index = {sid: i for i, (sid, _, _) in enumerate(segs)}
    writes, fixes = [], []
    errors, warnings = defaultdict(list), defaultdict(list)
    grouped = set()
    recipes = recipe_refs(exe)

    for group in GROUPS:
        ids = list(group['ids'])
        if ids[-1] == 'comidas':
            ids = ids[:-1] + [sid for sid, address, _ in segs if FOODS[0] <= address < FOODS[1]]
        positions = [index[sid] for sid in ids]
        if positions != list(range(positions[0], positions[0] + len(ids))):
            raise ValueError(f'grupo "{group["nome"]}": textos não são vizinhos')
        grouped.update(ids)
        start = segs[positions[0]][1]
        last_sid, last_address, last_raw = segs[positions[-1]]
        end = last_address + len(last_raw)            # onde fica o FFFF final do grupo
        encoded = {}
        for sid in ids:
            _, address, raw = segs[index[sid]]
            en = table.decode_exact(raw)
            pt = translations.get(sid)
            if pt:
                problems = validate(en, pt, allowed, 10 ** 6)
                if problems:
                    errors[sid] += problems
                    pt = None
            encoded[sid] = table.encode(pt) if pt else raw
        need = sum(len(encoded[sid]) + 2 for sid in ids) - 2
        if start + need > end:
            excess = (start + need - end) // 2
            for sid in ids:
                if sid in translations:
                    errors[sid].append(f'o grupo "{group["nome"]}" passou {excess} caractere(s) do espaço total')
                    break
            continue
        data = bytearray()
        moved = []
        for number, sid in enumerate(ids):
            _, old_address, _ = segs[index[sid]]
            new_address = start + len(data)
            chunk = encoded[sid]
            if number == len(ids) - 1:
                chunk += struct.pack('<H', SPACE) * ((end - new_address - len(chunk)) // 2)
            data += chunk + struct.pack('<H', END)
            if new_address == old_address:
                continue
            if sid in group['sem_referencia']:
                if table.decode(chunk).strip():
                    errors[sid].append('este texto só pode ficar em branco (ele cede o espaço ao anterior)')
                continue
            refs = group['refs']
            targets = ([('exe16', pos) for pos in recipes.get(old_address, [])] if refs == 'receitas'
                       else refs.get(sid, []))
            if not targets:
                errors[sid].append(f'precisa mudar de lugar, mas não tem referência conhecida '
                                   f'(grupo "{group["nome"]}")')
                continue
            for target, pos in targets:
                fix = _fix(target, pos, old_address, new_address, exe, subfiles)
                if isinstance(fix, str):
                    errors[sid].append(fix)
                else:
                    fixes.append(fix)
            if refs != 'receitas':
                moved.append((sid, old_address))
        for sid, old_address in moved:
            if data[old_address - start:old_address - start + 2] != struct.pack('<H', END):
                warnings[sid].append('o começo antigo deste texto ficou no meio de outro: se houver '
                                     'alguma referência desconhecida, ela mostrará um pedaço do vizinho')
        writes.append((file_offset(start), bytes(data)))

    for sid, address, raw in segs:
        if sid in grouped or sid not in translations:
            continue
        en = table.decode_exact(raw)
        problems = validate(en, translations[sid], allowed, len(raw) // 2)
        if problems:
            errors[sid] += problems
            continue
        encoded = table.encode(translations[sid])
        padding = struct.pack('<H', SPACE) * ((len(raw) - len(encoded)) // 2)
        writes.append((file_offset(address), encoded + padding))
    for sid in translations:
        if sid not in index:
            errors[sid].append('esse texto não existe no executável')
    return writes, fixes, errors, warnings


def _fix(target, pos, old_address, new_address, exe, subfiles):
    """Correção de uma referência: (alvo, posição, bytes novos), ou uma mensagem de erro."""
    if target == 'exe16':
        old = struct.unpack_from('<H', exe, pos)[0]
        if TXT_BASE + old != old_address:
            return f'tabela de receitas em {pos:#x} não aponta para este texto'
        return ('exe', pos, struct.pack('<H', new_address - TXT_BASE))
    sub = int(target[2:])
    data = subfiles[sub]
    word = struct.unpack_from('<I', data, pos)[0]
    if word >> 26 != 0x09:
        return f'{target}:{pos:#x} não é uma instrução addiu'
    high = old_address - _s16(word & 0xFFFF)
    low = new_address - high
    if high & 0xFFFF or not -0x8000 <= low < 0x8000:
        return f'{target}:{pos:#x} não monta o endereço deste texto'
    return (sub, pos, struct.pack('<I', (word & 0xFFFF0000) | (low & 0xFFFF)))
