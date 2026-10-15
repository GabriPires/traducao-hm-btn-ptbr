"""Regras que uma fala traduzida precisa seguir para caber e funcionar no jogo.

Usadas pelo `hm.py check` (para revisar traduções) e pelo `hm.py build` (que se recusa
a gravar uma fala que quebre alguma delas). As mesmas regras estão explicadas, em
linguagem de tradutor, no prompt de tradução.

Tipos de código entre chaves:
    controle  {0Exx} e {0Fxx}: páginas, retratos, menus. Mesma ordem e posição do original
    nome      {jogador} e {40xx}: trocados por nomes pelo jogo. Podem mudar de lugar
    símbolo   os demais ({006D}, {0087}...): ícones e enfeites. Mantidos, posição livre
"""

import re
from collections import Counter

MAX_LINE = 31           # caracteres por linha: letras de 8 px, caixa de x=30 a 290, setinha ▼ no fim
MAX_LINES_DIALOG = 4    # linhas por página nos diálogos com retrato
MAX_UNITS = 1000        # o limite físico é 1023 valores; 1000 deixa margem para o prefixo
NAME_WIDTH = 8          # espaço reservado na linha para cada nome variável
APOSTROPHE = '008D'     # apóstrofo cru: pode sumir na tradução
SHORT_RATIO = 0.7       # abaixo disso (em textos longos), a tradução provavelmente cortou conteúdo
TV_PREFIX = '{0FF1}'    # programas de TV: texto corrido, longo
SENTENCE_END = tuple('.!?…:;)"\'♥')

CODE = re.compile(r'\{([^{}]*)\}')
PAGE_BREAK = re.compile(r'(\{0FFC\}\{0FF[AB]\})')
LEADING_CONTROLS = re.compile(r'(?:\{0[EF][0-9A-F]{2}\})*')
DIALOG_PREFIX = '{0FF4}{0FF5}{0E2'
MENU_BREAK = '{0FFC}{0FFA}'
HINTS = {'—': 'use --', '–': 'use --', '“': 'use "', '”': 'use "', '‘': "use '", '’': "use '",
         'º': 'escreva por extenso', 'ª': 'escreva por extenso', '°': 'escreva por extenso'}


def kind(code):
    if code == 'jogador' or re.fullmatch(r'40[0-9A-F]{2}', code):
        return 'name'
    if re.fullmatch(r'0[EF][0-9A-F]{2}', code):
        return 'control'
    return 'symbol'


def codes(text, wanted):
    return [code for code in CODE.findall(text) if kind(code) == wanted]


def units(text):
    """Quantos valores de 16 bits o texto ocupa: cada caractere e cada código vale 1."""
    return len(CODE.sub('#', text))


def width(line):
    """Largura visível: controles não ocupam espaço, nomes ocupam NAME_WIDTH, símbolos 1."""
    def replace(match):
        k = kind(match.group(1))
        return '' if k == 'control' else 'X' * NAME_WIDTH if k == 'name' else '#'
    return len(CODE.sub(replace, line))


def pages(text):
    """Divide em páginas. Devolve [(separador que abriu a página, linhas)]."""
    parts = PAGE_BREAK.split(text)
    result = [('', parts[0])]
    for i in range(1, len(parts), 2):
        result.append((parts[i], parts[i + 1]))
    out = []
    for opener, body in result:
        # a quebra de linha logo depois do separador só abre a página nova
        if opener and body.startswith('\n'):
            body = body[1:]
        out.append((opener, body.split('\n')))
    return out


def validate(prefix, en, pt, allowed):
    """Compara a tradução com o original. Devolve (erros, avisos), listas de mensagens."""
    errors, warnings = [], []

    # caracteres
    plain = CODE.sub('', pt)
    bad = sorted({ch for ch in plain if ch not in allowed and ch != '\n'})
    if bad:
        detail = ', '.join(f'{ch!r}' + (f' ({HINTS[ch]})' if ch in HINTS else '') for ch in bad)
        errors.append(f'caracteres não permitidos: {detail}')
    if '...' in plain:
        errors.append('use o caractere único … em vez de ...')
    for code in CODE.findall(pt):
        if code != 'jogador' and not re.fullmatch(r'[0-9A-F]{4}', code):
            errors.append(f'código inválido: {{{code}}}')

    # códigos
    if codes(en, 'control') != codes(pt, 'control'):
        errors.append('códigos de controle diferentes do original (devem ser os mesmos, na mesma ordem): '
                      f'esperado {_fmt(codes(en, "control"))}, encontrado {_fmt(codes(pt, "control"))}')
    if Counter(codes(en, 'name')) != Counter(codes(pt, 'name')):
        errors.append(f'nomes variáveis diferentes do original: esperado {_fmt(codes(en, "name"))}, '
                      f'encontrado {_fmt(codes(pt, "name"))}')
    symbols_en = Counter(c for c in codes(en, 'symbol') if c != APOSTROPHE)
    symbols_pt = Counter(c for c in codes(pt, 'symbol') if c != APOSTROPHE)
    if symbols_en != symbols_pt:
        errors.append(f'símbolos diferentes do original: esperado {_fmt(sorted(symbols_en.elements()))}, '
                      f'encontrado {_fmt(sorted(symbols_pt.elements()))}')

    # páginas e linhas
    pages_en, pages_pt = pages(en), pages(pt)
    if len(pages_en) != len(pages_pt):
        errors.append(f'{len(pages_pt)} página(s), o original tem {len(pages_en)}')
    else:
        dialog = DIALOG_PREFIX in prefix
        for number, ((opener, lines_en), (_, lines_pt)) in enumerate(zip(pages_en, pages_pt), 1):
            where = f'página {number}' if len(pages_en) > 1 else 'texto'
            start_en = LEADING_CONTROLS.match(lines_en[0]).group()
            start_pt = LEADING_CONTROLS.match(lines_pt[0]).group()
            if start_en != start_pt:
                errors.append(f'{where}: deve começar com {start_en or "texto (sem códigos)"}')
            menu = opener == MENU_BREAK or (number == 1 and '{0FFA}' in prefix)
            if menu:
                if len(lines_pt) != len(lines_en):
                    errors.append(f'{where} (menu de escolha): {len(lines_pt)} linha(s), '
                                  f'o original tem {len(lines_en)}; mantenha uma opção por linha')
                elif [_indented(l) for l in lines_en] != [_indented(l) for l in lines_pt]:
                    errors.append(f'{where} (menu de escolha): as opções devem manter o espaço no início')
            else:
                limit = max(MAX_LINES_DIALOG, len(lines_en)) if dialog else len(lines_en)
                if len(lines_pt) > limit:
                    errors.append(f'{where}: {len(lines_pt)} linhas, o máximo é {limit}')

    for line in re.split(r'\n|' + PAGE_BREAK.pattern, pt):
        if line and not PAGE_BREAK.fullmatch(line) and width(line) > MAX_LINE:
            errors.append(f'linha com {width(line)} caracteres (máximo {MAX_LINE}): {line!r}')

    if units(pt) > MAX_UNITS:
        errors.append(f'texto longo demais: {units(pt)} unidades, o máximo é {MAX_UNITS}')

    if CODE.sub('', en).strip() in ('', 'Dummy'):
        warnings.append('esta fala não aparece no jogo (Dummy ou vazia), não precisa de tradução')
    elif pt == en:
        warnings.append('tradução idêntica ao original')

    if units(en) > 200 and units(pt) < SHORT_RATIO * units(en):
        warnings.append(f'a tradução tem {units(pt)} unidades, {units(pt) * 100 // units(en)}% do original '
                        f'({units(en)}): confira se nada foi cortado (o limite é {MAX_UNITS})')
    if TV_PREFIX in prefix:
        for before, after in loose_breaks(pt):
            warnings.append(f'quebra de linha solta: {before!r} + {after!r} cabem numa linha só')
    return errors, warnings


def loose_breaks(text):
    """Pares de linhas em que a 2ª é um pedaço curto da mesma frase que caberia na 1ª."""
    pairs = []
    for page in PAGE_BREAK.split(text):
        if PAGE_BREAK.fullmatch(page):
            continue
        lines = page.split('\n')
        for a, b in zip(lines, lines[1:]):
            plain_a, plain_b = CODE.sub('', a), CODE.sub('', b)
            if (not plain_a.strip() or not plain_b.strip() or plain_a.startswith(' ')
                    or plain_b.startswith(' ') or plain_a.rstrip().endswith(SENTENCE_END)):
                continue
            if width(b) <= 10 and width(a) + 1 + width(b) <= MAX_LINE:
                pairs.append((plain_a.strip(), plain_b.strip()))
    return pairs


def _indented(line):
    return line[len(LEADING_CONTROLS.match(line).group()):].startswith(' ')


def _fmt(items):
    return ''.join(f'{{{c}}}' for c in items) or '(nenhum)'
