"""Textos do executável SLUS_011.15 (menus, comidas, lojas, sementes, memory card) e dos
overlays dos minigames.

Ficam colados em dois blocos, cada um terminado por FFFF. O jogo chega a eles por
caminhos variados (endereço absoluto em overlays, deslocamento a partir do início do
bloco guardado em tabelas ou variáveis), e nem todas as referências foram mapeadas
(docs/06-textos-do-executavel.md). Por isso a tradução é gravada NO LUGAR: cada texto
continua começando e terminando no mesmo endereço. Se a tradução for mais curta, o
fim é completado com espaços antes do FFFF; nunca pode ser mais longa.
"""

import hashlib
import re
import struct
from collections import defaultdict

from . import mips

EXE_BASE = 0x80010000           # endereço da RAM onde o corpo do executável é carregado
HEADER = 0x800                  # cabeçalho PS-X EXE antes do corpo
BLOCKS = ((0x8005175C, 0x80054BBA),   # menus, mensagens, comidas, lojas, sementes
          (0x800556B6, 0x800558A2))   # nomes de animais e competidores
# Textos soltos nos overlays (subarquivos do A_FILE carregados sob demanda pelos
# minigames). Nomes próprios de competidores ficam de fora. Mesma regra: no lugar.
# O primeiro texto de cada lista vem logo depois de código, sem um FFFF antes: é fácil
# de perder numa busca por textos (o comando `scan` procura os que faltam).
OVERLAY_STRINGS = {
    11: (0x70328, 0x7035C),                            # buraco na mina, sair da mina
    17: (0x03662, 0x0367A, 0x03684, 0x03694),          # apostas da corrida de cavalos
    21: (0x04C58, 0x04CB8),                            # minigame de arremesso
    23: (0x03A40, 0x03A66, 0x03A8A, 0x03AAC, 0x03ACE,  # competidores "Fazenda X: nome"
         0x03AF8, 0x03B28, 0x03B54, 0x03B76, 0x03BA2),
    25: (0x04D14, 0x04D6E),                            # incentivo e aviso de espera
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
     'sem_referencia': set(),
     # o overlay 15 guarda o endereço de "Diary" num registrador e acha outras mensagens
     # somando um deslocamento a ele: elas precisam continuar no mesmo lugar
     'derivados': {'exe-80051D8E': [('ov15', 0x08FCC, 0x80051C54), ('ov15', 0x08FE8, 0x80051C54),
                                    ('ov15', 0x0901C, 0x80051C54), ('ov15', 0x09000, 0x80051C66),
                                    ('ov15', 0x09030, 0x80051C92)]}},
    {'nome': 'teclado da tela de nomes: Máximo + as duas grades de letras',
     'ids': ('exe-800537A2', 'exe-800537B2', 'exe-80053888'),
     'refs': {'exe-800537B2': [('exe', 0x80023D60)], 'exe-80053888': [('exe', 0x80023D6C)]},
     'sem_referencia': set()},
    # Lojas: o overlay 11 monta a lista de itens com endereços SOMADOS (BASE_WORD): cada
    # instrução de `somados` é um addiu cuja base é o "lui 0x8005" (número) ou o endereço
    # de outro nome que já está no registrador (id). Varredura feita em todos os
    # subarquivos e no executável: só o overlay 11 acha estes textos.
    {'nome': 'Ferraria: Comprar, Escova, Ordenhadeira, Tesoura',
     'ids': ('exe-80054772', 'exe-80054784', 'exe-80054790', 'exe-8005479E'),
     'refs': {}, 'sem_referencia': set(),
     'somados': {'exe-80054772': [('ov11', 0x63688, 0x80050000)],
                 'exe-80054784': [('ov11', 0x636DC, 'exe-80054772')],
                 'exe-80054790': [('ov11', 0x63750, 0x80050000)],
                 'exe-8005479E': [('ov11', 0x6379C, 0x80050000)]}},
    {'nome': 'Pousada e bar: cardápio do dia, bebidas, Leite, Raspadinha',
     'ids': ('exe-800547CA', 'exe-800547DC', 'exe-800547E8', 'exe-800547FC', 'exe-80054812',
             'exe-80054820', 'exe-8005482C', 'exe-80054846', 'exe-80054866', 'exe-80054870'),
     'refs': {}, 'sem_referencia': set(),
     'somados': {'exe-800547CA': [('ov11', 0x5FA54, 0x80050000)],
                 'exe-800547DC': [('ov11', 0x5FA84, 'exe-800547CA')],
                 'exe-800547E8': [('ov11', 0x5FAB4, 'exe-800547CA')],
                 'exe-800547FC': [('ov11', 0x5FAE4, 'exe-800547CA')],
                 'exe-80054812': [('ov11', 0x5FB14, 'exe-800547CA')],
                 'exe-80054820': [('ov11', 0x5FB8C, 0x80050000), ('ov11', 0x5FD3C, 'exe-80054870')],
                 'exe-8005482C': [('ov11', 0x5F9A4, 0x80050000)],
                 'exe-80054846': [('ov11', 0x5F9D4, 'exe-8005482C')],
                 'exe-80054866': [('ov11', 0x5FA04, 'exe-8005482C')],
                 'exe-80054870': [('ov11', 0x5FD08, 0x80050000)]}},
    {'nome': 'Vinícola: Sem. capim, Vinho, Suco de uva',
     'ids': ('exe-800546CA', 'exe-800546E2', 'exe-800546EC'),
     'refs': {}, 'sem_referencia': set(),
     'somados': {'exe-800546CA': [('ov11', 0x62CF8, 0x80050000), ('ov11', 0x62EC0, 0x80050000),
                                  ('ov11', 0x63068, 'exe-80054454')],
                 'exe-800546E2': [('ov11', 0x63460, 0x80050000)],
                 'exe-800546EC': [('ov11', 0x6346C, 'exe-800546E2')]}},
    {'nome': 'Rancho: comprar e vender vaca e ovelha',
     'ids': ('exe-80054B0A', 'exe-80054B1A', 'exe-80054B2E', 'exe-80054B40'),
     'refs': {}, 'sem_referencia': set(),
     'somados': {'exe-80054B0A': [('ov11', 0x5C03C, 0x80050000)],
                 'exe-80054B1A': [('ov11', 0x5C074, 'exe-80054B0A')],
                 'exe-80054B2E': [('ov11', 0x5C0A4, 'exe-80054B0A')],
                 'exe-80054B40': [('ov11', 0x5C0D0, 'exe-80054B0A')]}},
    {'nome': 'Não da configuração + nomes de comidas',
     'ids': ('exe-80053DD0', 'comidas'), 'refs': 'receitas', 'sem_referencia': set()},
)

# Textos que o jogo insere no meio das falas: o apelido {400F} ("Honey", "Darling").
# Precisam ocupar o espaço inteiro, senão o espaço de enchimento aparece na frase
# ("Amor !"). O código os acha somando BASE_DELTA a uma constante, então não andam.
EXACT_LENGTH = {'exe-80054396', 'exe-800543A2'}

# Vários menus acham o texto somando uma constante à palavra guardada em BASE_WORD
# (vale BASE_DELTA no disco americano): endereço = constante + 0x2C3A. A constante sozinha
# não aponta para o texto, por isso não aparece numa busca direta pelo endereço.
BASE_WORD = 0x80054BC0
BASE_DELTA = 0x2C3A

# Remendos fixos fora dos blocos de texto: (endereço, bytes originais, bytes novos).
# Os bytes originais são conferidos antes de gravar; quando eles são texto em inglês, a
# conferência é pelo SHA-1 (o repositório não guarda o texto original).
#
# 1) Dias da semana e estações (calendário, relógio, diário e a variável de data).
#    No original, duas funções copiam o nome de uma tabela de largura fixa: estações com
#    6 letras ("Fall" + 2 espaços) em 0x8004908C e dias com 3 letras em 0x800490BC, cada
#    letra um valor de 16 bits. "Primavera" não cabe em 6. As funções são reescritas
#    (mesmo tamanho, 15 instruções) para ler uma letra por BYTE, o que dobra o espaço:
#    estações com até 9 letras (tamanho livre, terminadas em 0xFF) e dias com 3.
# 2) Animais nas cerimônias ({401B}-{4020}): o jogo cola o texto de 0x80049084 depois
#    do nome de cada animal: "'s" + quebra. Em português fica só a quebra. Ele fica no
#    mesmo trecho, logo antes das estações, e é gravado junto.
SEASON_NAMES = ('Primavera', 'Verão', 'Outono', 'Inverno')
WEEKDAY_NAMES = ('Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb')
SEASON_FN, WEEKDAY_FN = 0x8001AA7C, 0x8001AAB8
NAMES_AREA = (0x80049084, 0x800490E8)
NAMES_AREA_SHA1 = '615bf07e510f8424744b1cdd56d72eee4fffbf2a'
SEASONS_AT = 0x80049088          # logo depois de "quebra + FFFF"
SEASON_STRIDE = 10               # 9 letras + o fim (0xFF)
WEEKDAYS_AT = SEASONS_AT + 4 * SEASON_STRIDE
NAMES_END = 0xFF
SEASON_FN_ORIGINAL = (0x00041840, 0x00641821, 0x00031880, 0x3C028005, 0x2442908C, 0x00621821,
                      0x24040005, 0x94620000, 0x24630002, 0x2484FFFF, 0xA4A20000, 0x0481FFFB,
                      0x24A50002, 0x03E00008, 0x00A01021)
WEEKDAY_FN_ORIGINAL = (0x00041840, 0x00641821, 0x00031840, 0x3C028005, 0x244290BC, 0x00621821,
                       0x24040002, 0x94620000, 0x24630002, 0x2484FFFF, 0xA4A20000, 0x0481FFFB,
                       0x24A50002, 0x03E00008, 0x00A01021)


def _low(address):
    """Parte baixa de um endereço montado com lui 0x8005 + deslocamento com sinal."""
    return address - 0x80050000


def season_function():
    """a0 = estação (0-3), a1 = destino. Copia até o 0xFF; devolve o fim em v0."""
    return mips.assemble([
        mips.sll('v1', 'a0', 3),
        mips.sll('v0', 'a0', 1),
        mips.addu('v1', 'v1', 'v0'),                    # v1 = estação * 10
        mips.lui('v0', 0x8005),
        mips.addu('v1', 'v1', 'v0'),
        mips.addiu('a0', 'zero', NAMES_END),
        mips.lbu('v0', _low(SEASONS_AT), 'v1'),         # laço:
        mips.addiu('v1', 'v1', 1),
        mips.beq('v0', 'a0', 4),                        # fim do nome -> retorna
        mips.nop(),
        mips.sh('v0', 0, 'a1'),
        mips.beq('zero', 'zero', -6),                   # volta ao laço
        mips.addiu('a1', 'a1', 2),
        mips.jr('ra'),
        mips.addu('v0', 'a1', 'zero'),
    ])


def weekday_function():
    """a0 = dia (0-6), a1 = destino. Copia 3 letras; devolve o fim em v0."""
    return mips.assemble([
        mips.sll('v1', 'a0', 1),
        mips.addu('v1', 'v1', 'a0'),                    # v1 = dia * 3
        mips.lui('v0', 0x8005),
        mips.addu('v1', 'v1', 'v0'),
        mips.addiu('a0', 'zero', 2),
        mips.lbu('v0', _low(WEEKDAYS_AT), 'v1'),        # laço:
        mips.addiu('v1', 'v1', 1),
        mips.addiu('a0', 'a0', -1),
        mips.sh('v0', 0, 'a1'),
        mips.bgez('a0', -5),
        mips.addiu('a1', 'a1', 2),
        mips.jr('ra'),
        mips.addu('v0', 'a1', 'zero'),
        mips.nop(),
        mips.nop(),
    ])


def names_area(table):
    """Bytes novos de NAMES_AREA: quebra das cerimônias, estações e dias da semana."""
    def letters(name, size):
        codes = [table.encode(ch) for ch in name]
        if any(len(code) != 2 or code[1] for code in codes):
            raise ValueError(f'"{name}": só letras de código menor que 0x100')
        if len(codes) > size:
            raise ValueError(f'"{name}": mais de {size} letras')
        return bytes(code[0] for code in codes)
    data = struct.pack('<2H', 0xFFFE, END)                                      # cerimônias
    for name in SEASON_NAMES:
        data += letters(name, SEASON_STRIDE - 1).ljust(SEASON_STRIDE, bytes([NAMES_END]))
    for name in WEEKDAY_NAMES:
        if len(name) != 3:
            raise ValueError(f'"{name}": o dia da semana precisa ter 3 letras')
        data += letters(name, 3)
    size = NAMES_AREA[1] - NAMES_AREA[0]
    if len(data) > size:
        raise ValueError('nomes de estações e dias não cabem')
    return data.ljust(size, b'\0')


def patches(table):
    """Lista de (endereço, conferência, bytes novos); conferência = bytes ou SHA-1."""
    return [
        (NAMES_AREA[0], NAMES_AREA_SHA1, names_area(table)),
        (SEASON_FN, mips.assemble(SEASON_FN_ORIGINAL), season_function()),
        (WEEKDAY_FN, mips.assemble(WEEKDAY_FN_ORIGINAL), weekday_function()),
    ]


# Remendos de código nos overlays: (subarquivo, posição, palavra original, palavra nova).
#   Overlay 11, cabeçalho do calendário: o original desenha o número do ano em x=0x1F e
#   "Year" em x=0x39 ("1st Year"). Em português a ordem é "Ano 1": "Ano" vai para 0x1F e
#   o número (2 casas, alinhado à direita) para 0x3B.
#   Overlay 15, data de cada diário: um buffer de 0x28 bytes (preenchido com 0xFF) guarda
#   o ano em +0x00, a estação em +0x0A e o dia em +0x1A. O espaço da estação (8 letras)
#   cortava "Primavera" e o dia apagava o fim dela; o dia vai para +0x1E (estação com
#   até 9 letras + FFFF; dia com 2 casas + FFFF termina em +0x24).
#   O dia era escrito por uma função do overlay (0x8013703C) que põe o número e depois o
#   ordinal ("4th"); como os ordinais viraram espaços, sobrava "4   de". A chamada passa a
#   ir direto para a função do número (0x8001A970, mesmos argumentos), sem o ordinal.
OVERLAY_PATCHES = (
    (11, 0x428F8, 0x2406001F, 0x2406003B),      # addiu a2,zero,x do número
    (11, 0x42910, 0x24060039, 0x2406001F),      # addiu a2,zero,x de "Year"
    (15, 0x09174, 0x2610001A, 0x2610001E),      # addiu s0,s0,+0x1A → +0x1E (campo do dia)
    (15, 0x0918C, 0x0C04DC0F, 0x0C006A5C),      # jal número+ordinal → jal só o número
)


def apply_overlay_patches(subfiles):
    """Grava OVERLAY_PATCHES nos subarquivos, conferindo as palavras originais."""
    for sub, pos, old, new in OVERLAY_PATCHES:
        if struct.unpack_from('<I', subfiles[sub], pos)[0] != old:
            raise ValueError(f'subarquivo {sub}, {pos:#x}: instrução original diferente da esperada')
        struct.pack_into('<I', subfiles[sub], pos, new)


def apply_patches(exe, table):
    """Grava os remendos no executável (bytearray), conferindo os bytes originais."""
    for address, check, new in patches(table):
        pos = file_offset(address)
        old = bytes(exe[pos:pos + len(new)])
        ok = (hashlib.sha1(old).hexdigest() == check) if isinstance(check, str) else old == check
        if not ok:
            raise ValueError(f'{address:#010x}: bytes originais diferentes do esperado')
        exe[pos:pos + len(new)] = new


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
        errors.append(f'longo demais: {units} caracteres, o espaço do original é {max_units}')
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


def plan(exe, subfiles, table, translations, allowed, refmap=None):
    """Decide como gravar as traduções do executável.

    Com `refmap` (o mapa de `refs.find`), um texto que não cabe no seu espaço pode
    crescer por remanejamento automático (classe _Layout). Sem ele, só os GROUPS.

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
    hand_new_of = {}                                  # textos que os GROUPS mudaram de lugar

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
        new_of = {}
        for number, sid in enumerate(ids):
            _, old_address, _ = segs[index[sid]]
            new_address = start + len(data)
            new_of[sid] = new_address
            if new_address != old_address:
                hand_new_of[sid] = new_address
            chunk = encoded[sid]
            if number == len(ids) - 1:
                chunk += struct.pack('<H', SPACE) * ((end - new_address - len(chunk)) // 2)
            data += chunk + struct.pack('<H', END)
            if new_address == old_address or sid in group.get('somados', {}):
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
            for target, pos, other in group.get('derivados', {}).get(sid, []):
                fix = _fix_derived(target, pos, old_address, new_address, other, subfiles)
                if isinstance(fix, str):
                    errors[sid].append(fix)
                else:
                    fixes.append(fix)
            if refs != 'receitas':
                moved.append((sid, old_address))
        for sid, sums in group.get('somados', {}).items():
            for target, pos, base in sums:
                fix = _fix_sum(target, pos, sid, base, segs, index, new_of, subfiles)
                if isinstance(fix, str):
                    errors[sid].append(fix)
                elif fix:
                    fixes.append(fix)
        for sid, old_address in moved:
            if data[old_address - start:old_address - start + 2] != struct.pack('<H', END):
                warnings[sid].append('o começo antigo deste texto ficou no meio de outro: se houver '
                                     'alguma referência desconhecida, ela mostrará um pedaço do vizinho')
        writes.append((file_offset(start), bytes(data)))

    not_moved = set()                                 # não couberam nem com remanejamento
    if refmap is not None:
        layout = _Layout(exe, segs, table, translations, allowed, refmap, grouped)
        for i in layout.overflowing():
            if i in layout.taken:
                continue
            window = layout.find_window(i)
            if window is None:
                errors[segs[i][0]].append(layout.why_not(i))
                not_moved.add(segs[i][0])
                continue
            layout.take(window)
        auto_writes, notes = layout.write_windows()
        writes += auto_writes
        for sid, messages in notes.items():
            warnings[sid] += messages
        grouped |= {segs[i][0] for i in layout.taken}
        # todas as referências conhecidas de textos que andaram (nos GROUPS ou nas janelas),
        # inclusive as que só passam pelo endereço de um texto que andou
        known = {fix[:2]: fix for fix in fixes}
        new_fixes, problems = layout.ref_fixes({**hand_new_of, **layout.new_of}, subfiles)
        for sid, messages in problems.items():
            errors[sid] += messages
        for sid, fix in new_fixes:
            key = fix[:2]
            if key in known and known[key] != fix:
                errors[sid].append(f'{key[0]}:{key[1]:#x} seria corrigido de dois jeitos')
            elif key not in known:
                known[key] = fix
                fixes.append(fix)

    for sid, address, raw in segs:
        if sid in grouped or sid not in translations:
            continue
        en = table.decode_exact(raw)
        limit = 10 ** 6 if sid in not_moved else len(raw) // 2     # o motivo já foi dado
        problems = validate(en, translations[sid], allowed, limit)
        units = len(CODE.sub('#', translations[sid]))
        if sid in EXACT_LENGTH and units != len(raw) // 2:
            problems.append(f'precisa ter exatamente {len(raw) // 2} caracteres (aparece no meio '
                            f'das falas; o que sobrar vira espaço visível)')
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


WINDOW_REACH = 12           # vizinhos procurados de cada lado no remanejamento


def movable(refs):
    """Um texto com estas referências (mapa de `refs.find`) pode mudar de lugar?"""
    return bool(refs) and all(ref['kind'] in ('addiu', 'tabela') for ref in refs)


def hand_grouped(segs):
    """Ids dos textos nos GROUPS feitos à mão (o remanejamento automático não mexe neles)."""
    ids = set()
    for group in GROUPS:
        ids.update(group['ids'])
        if group['ids'][-1] == 'comidas':
            ids.update(sid for sid, address, _ in segs if FOODS[0] <= address < FOODS[1])
    ids.discard('comidas')
    return ids


class _Layout:
    """Remanejamento automático dos textos do executável.

    Um texto que não cabe no seu espaço cresce dentro de uma JANELA de vizinhos: o
    primeiro texto da janela não anda, e cada texto que anda precisa ter todas as
    referências conhecidas (mapa de `refs.find`), que são corrigidas. A ordem e o número
    de terminadores não mudam, e cada texto continua terminando logo antes do seguinte
    (o que sobra vira espaço antes do FFFF), então quem conta textos continua certo.
    Dentro da janela há duas arrumações: empurrar os textos para a frente ou puxá-los
    para trás, usando a sobra dos vizinhos; vale a que move menos textos.
    """

    def __init__(self, exe, segs, table, translations, allowed, refmap, excluded):
        self.exe, self.segs, self.refmap = exe, segs, refmap
        self.index = {sid: i for i, (sid, _, _) in enumerate(segs)}
        self.encoded, self.need, self.slot, self.block = [], [], [], []
        block = 0
        for i, (sid, address, raw) in enumerate(segs):
            if i and address != segs[i - 1][1] + len(segs[i - 1][2]) + 2:
                block += 1
            self.block.append(block)
            encoded, pt = raw, translations.get(sid)
            invalid = bool(pt and validate(table.decode_exact(raw), pt, allowed, 10 ** 6))
            if pt and not invalid:
                encoded = table.encode(pt)
            self.encoded.append(encoded)
            self.need.append(len(encoded) + 2)          # bytes, com o FFFF
            self.slot.append(len(raw) + 2)
            if invalid:                                 # o erro sai na gravação no lugar
                excluded = excluded | {sid}
        self.fixed = {i for i, (sid, _, _) in enumerate(segs) if sid in excluded or sid in EXACT_LENGTH}
        self.movable = [movable(refmap.get(sid, [])) for sid, _, _ in segs]
        self.taken = set()
        self.windows = []                               # (s, e, posições, quem motivou)

    def overflowing(self):
        return [i for i in range(len(self.segs))
                if self.need[i] > self.slot[i] and i not in self.fixed]

    def _free(self, j, i):
        return 0 <= j < len(self.segs) and j not in self.fixed and j not in self.taken \
            and self.block[j] == self.block[i]

    def _pack(self, s, e, need):
        """Posições dos textos s..e, ou None. Devolve a arrumação que move menos textos."""
        addr = [self.segs[j][1] for j in range(s, e + 1)]
        end = addr[-1] + self.slot[e]
        options = []
        positions, cur = [], addr[0]                    # empurrando para a frente
        for k, j in enumerate(range(s, e + 1)):
            positions.append(max(addr[k], cur))
            cur = positions[-1] + need[j]
        if cur <= end:
            options.append(positions)
        positions, cur = [], end                        # puxando para trás
        for k, j in reversed(list(enumerate(range(s, e + 1)))):
            cur = min(addr[k], cur - need[j])
            positions.insert(0, cur)
        if positions[0] == addr[0]:
            options.append(positions)
        best = None
        for positions in options:
            moved = [s + k for k, p in enumerate(positions) if p != addr[k]]
            if all(self.movable[j] for j in moved) and (best is None or len(moved) < best[0]):
                best = (len(moved), positions)
        return best

    def find_window(self, i, need=None):
        """(s, e, posições) da melhor janela para o texto i, ou None."""
        need = need or self.need
        best = None
        s = i
        while self._free(s, i) and i - s <= WINDOW_REACH:
            e = i
            while self._free(e, i) and e - i <= WINDOW_REACH:
                packed = self._pack(s, e, need)
                if packed and (best is None or (packed[0], e - s) < best[0]):
                    best = ((packed[0], e - s), (s, e, packed[1]))
                e += 1
            s -= 1
        return best[1] if best else None

    def why_not(self, i):
        excess = (self.need[i] - self.slot[i]) // 2
        sid = self.segs[i][0]
        if not self.movable[i] and not self.refmap.get(sid):
            reason = 'ele e os vizinhos não têm como abrir espaço'
        else:
            reason = 'não há sobra nos vizinhos que podem mudar de lugar'
        blockers = [self.segs[j][0] for j in range(max(0, i - 2), min(len(self.segs), i + 3))
                    if j != i and self._free(j, i) and not self.movable[j]]
        if blockers:
            reason += f' (sem referência conhecida: {", ".join(blockers)})'
        return f'passou {excess} caractere(s) e o remanejamento não resolveu: {reason}'

    def take(self, window):
        s, e, positions = window
        self.taken.update(range(s, e + 1))
        self.windows.append(window)

    def write_windows(self):
        """(gravações, avisos) das janelas escolhidas; guarda em self.new_of quem andou."""
        writes, notes = [], defaultdict(list)
        new_of = self.new_of = {}
        for s, e, positions in self.windows:
            data = bytearray()
            end = self.segs[e][1] + self.slot[e]
            moved = []
            for k, j in enumerate(range(s, e + 1)):
                sid, address, _ = self.segs[j]
                region = (positions[k + 1] if k + 1 < len(positions) else end) - positions[k]
                chunk = self.encoded[j]
                data += chunk + struct.pack('<H', SPACE) * ((region - 2 - len(chunk)) // 2)
                data += struct.pack('<H', END)
                if positions[k] != address:
                    new_of[sid] = positions[k]
                    moved.append(sid)
            writes.append((file_offset(positions[0]), bytes(data)))
            for j in range(s, e + 1):
                if self.need[j] > self.slot[j]:
                    notes[self.segs[j][0]].append(
                        f'cresceu com remanejamento: {len(moved)} texto(s) mudaram de lugar '
                        f'({", ".join(moved)}); confira no jogo')
        return writes, notes

    def ref_fixes(self, new_of, subfiles):
        """Correções de todas as referências do mapa cujo texto ou cuja base andou.
        Devolve ([(id, correção)], {id: [problemas]})."""
        fixes, problems = [], defaultdict(list)
        for sid, refs in self.refmap.items():
            for ref in refs:
                base = ref.get('base')
                if ref['kind'] not in ('addiu', 'tabela') or sid not in self.index:
                    continue
                if sid not in new_of and not (isinstance(base, str) and base in new_of):
                    continue
                fix = self._fix(sid, ref, new_of, subfiles)
                if isinstance(fix, str):
                    problems[sid].append(fix)
                elif fix:
                    fixes.append((sid, fix))
        return fixes, problems

    def _address(self, sid, new_of=None):
        old = self.segs[self.index[sid]][1]
        return new_of.get(sid, old) if new_of is not None else old

    def _fix(self, sid, ref, new_of, subfiles):
        where, pos = ref['where'], ref['pos']
        data = self.exe if where == 'exe' else subfiles[where]
        old, new = self._address(sid), self._address(sid, new_of)
        if ref['kind'] == 'tabela':
            value = struct.unpack_from('<H', data, pos)[0]
            if TXT_BASE + value != old:
                return f'{where}:{pos:#x}: a tabela não aponta para este texto'
            if not 0 <= new - TXT_BASE < 0x10000:
                return f'{where}:{pos:#x}: deslocamento fora do alcance da tabela'
            return None if new == old else (where, pos, struct.pack('<H', new - TXT_BASE))
        word = struct.unpack_from('<I', data, pos)[0]
        if word >> 26 != 0x09:
            return f'{where}:{pos:#x} não é uma instrução addiu'
        base = ref['base']
        if isinstance(base, str):
            old_base = self._address(base) - ref['base_delta']
            new_base = self._address(base, new_of) - ref['base_delta']
        else:
            old_base = new_base = base
        if (old_base + _s16(word & 0xFFFF)) & 0xFFFFFFFF != old - ref['delta']:
            return f'{where}:{pos:#x} não calcula o endereço deste texto'
        low = new - ref['delta'] - new_base
        if not -0x8000 <= low < 0x8000:
            return f'{where}:{pos:#x}: deslocamento fora do alcance'
        if low == _s16(word & 0xFFFF):
            return None
        return (where, pos, struct.pack('<I', (word & 0xFFFF0000) | (low & 0xFFFF)))


def budget(exe, table, translations, allowed, refmap, sid, limit=200):
    """(espaço no lugar, máximo com remanejamento) em caracteres para o texto `sid`, com
    as outras traduções como estão. Aproximado: não considera outros textos que também
    precisem crescer na mesma região."""
    segs = [(entry_id(address), address, raw) for address, raw in segments(exe)]
    layout = _Layout(exe, segs, table, translations, allowed, refmap, hand_grouped(segs))
    i = layout.index[sid]
    in_place = layout.slot[i] // 2 - 1
    if i in layout.fixed:
        return in_place, in_place
    need = list(layout.need)
    low, high = in_place, in_place + limit
    while low < high:                                   # maior n que ainda cabe
        n = (low + high + 1) // 2
        need[i] = 2 * n + 2
        if need[i] <= layout.slot[i] or layout.find_window(i, need):
            low = n
        else:
            high = n - 1
    return in_place, low


def _fix_sum(target, pos, sid, base, segs, index, new_of, subfiles):
    """addiu que dá (endereço do texto `sid` - BASE_DELTA) a partir de `base`: o valor do
    "lui" (número) ou o endereço de outro texto já num registrador (id, que também pode
    ter andado). Devolve a correção, None se nada mudou, ou uma mensagem de erro."""
    sub = int(target[2:])
    word = struct.unpack_from('<I', subfiles[sub], pos)[0]
    if word >> 26 != 0x09:
        return f'{target}:{pos:#x} não é uma instrução addiu'

    def old(text_id):
        return segs[index[text_id]][1]

    def new(text_id):
        return new_of.get(text_id, old(text_id))

    if isinstance(base, int):
        old_base, new_base = base, base
    else:
        old_base, new_base = old(base) - BASE_DELTA, new(base) - BASE_DELTA
    if (old_base + _s16(word & 0xFFFF)) & 0xFFFFFFFF != old(sid) - BASE_DELTA:
        return f'{target}:{pos:#x} não calcula o endereço deste texto'
    low = (new(sid) - BASE_DELTA) - new_base
    if not -0x8000 <= low < 0x8000:
        return f'{target}:{pos:#x}: deslocamento fora do alcance'
    if low == _s16(word & 0xFFFF):
        return None
    return (sub, pos, struct.pack('<I', (word & 0xFFFF0000) | (low & 0xFFFF)))


def _fix_derived(target, pos, old_address, new_address, other, subfiles):
    """addiu que soma um deslocamento ao endereço de um texto para achar OUTRO texto
    (`other`, que não andou): quando o primeiro anda, o deslocamento compensa."""
    sub = int(target[2:])
    word = struct.unpack_from('<I', subfiles[sub], pos)[0]
    if word >> 26 != 0x09:
        return f'{target}:{pos:#x} não é uma instrução addiu'
    if old_address + _s16(word & 0xFFFF) != other:
        return f'{target}:{pos:#x} não calcula o endereço {other:#x} a partir deste texto'
    low = other - new_address
    if not -0x8000 <= low < 0x8000:
        return f'{target}:{pos:#x}: deslocamento fora do alcance'
    return (sub, pos, struct.pack('<I', (word & 0xFFFF0000) | (low & 0xFFFF)))


def _fix(target, pos, old_address, new_address, exe, subfiles):
    """Correção de uma referência: (alvo, posição, bytes novos), ou uma mensagem de erro."""
    if target == 'exe16':
        old = struct.unpack_from('<H', exe, pos)[0]
        if TXT_BASE + old != old_address:
            return f'tabela de receitas em {pos:#x} não aponta para este texto'
        return ('exe', pos, struct.pack('<H', new_address - TXT_BASE))
    if target == 'exe':                     # instrução addiu no próprio executável
        sub, data, pos = 'exe', exe, file_offset(pos)
    else:
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
