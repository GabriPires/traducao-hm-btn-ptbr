#!/usr/bin/env python3
"""Ferramenta de linha de comando do projeto de tradução.

Uso:
    python3 tools/hm.py info                 # informações do disco e do A_FILE
    python3 tools/hm.py cue                  # gera o .cue para abrir a imagem no emulador
    python3 tools/hm.py extract              # extrai tudo para build/
    python3 tools/hm.py dump                 # exporta os diálogos originais para build/script/
    python3 tools/hm.py check [03 ...]       # confere as traduções contra as regras do jogo
    python3 tools/hm.py font                 # prévia da fonte com os acentos (build/fonte.png)
    python3 tools/hm.py build                # aplica fonte e translation/*.json numa cópia da imagem
    python3 tools/hm.py find "Good morning"  # acha um texto nos subarquivos
    python3 tools/hm.py peek 2 0x1D814       # decodifica texto a partir de uma posição

A imagem original é só lida, nunca alterada.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import sys
from pathlib import Path

from hmbtn import accents, afile, dialog, exetext, font, rules
from hmbtn.disc import Disc, patch_form1
from hmbtn.speakers import Speakers
from hmbtn.table import Table

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / 'build'
AFILE_DIR = BUILD / 'afile'
TABLE = ROOT / 'tables' / 'hmbtn.tbl'
SPEAKERS = ROOT / 'tables' / 'personagens.tsv'
SCRIPT = BUILD / 'script'
TRANSLATION = ROOT / 'translation'
OUTPUT = BUILD / 'HARVESTMOON-PTBR.bin'
FONT_PREVIEW = BUILD / 'fonte.png'
DEFAULT_ISO = Path(os.environ.get('HMBTN_ISO', ROOT / 'HARVESTMOON.iso'))
END = 0xFFFF


def cmd_info(args):
    sha1 = hashlib.sha1()
    with open(args.iso, 'rb') as f:
        while chunk := f.read(1 << 20):
            sha1.update(chunk)
    with Disc(args.iso) as disc:
        print(f'Imagem : {args.iso}')
        print(f'SHA-1  : {sha1.hexdigest()}')
        print(f'Volume : {disc.volume_id} ({disc.system_id}), {disc.sector_count} setores\n')
        print(f'{"tamanho":>10}  {"LBA":>6}  arquivo')
        for entry in disc.files():
            size = 'pasta' if entry.is_dir else str(entry.size)
            print(f'{size:>10}  {entry.lba:6d}  {entry.path}')
        offsets = afile.parse_hdt(disc.read_file(disc.find('/A_FILE.HDT')))
    print(f'\nA_FILE.BIN: {len(offsets) - 1} subarquivos')
    print(f'{"#":>3}  {"offset":>10}  {"tamanho":>10}')
    for i in range(len(offsets) - 1):
        print(f'{i:3d}  0x{offsets[i]:08X}  {offsets[i + 1] - offsets[i]:10d}')


def write_cue(image):
    cue = Path(image).with_suffix('.cue')
    cue.write_text(f'FILE "{Path(image).name}" BINARY\n'
                   '  TRACK 01 MODE2/2352\n'
                   '    INDEX 01 00:00:00\n')
    return cue


def cmd_cue(args):
    print(f'Criado {write_cue(args.iso)}')


def cmd_extract(args):
    disc_dir = BUILD / 'disc'
    with Disc(args.iso) as disc:
        for entry in disc.files():
            target = disc_dir / entry.path.lstrip('/')
            if entry.is_dir:
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if entry.size and disc.is_form2(entry.lba):
                # áudio XA: guarda os setores inteiros, senão perderia dados
                target.write_bytes(disc.read_raw(entry.lba, entry.size))
                print(f'  {entry.path} (Form 2, setores crus)')
            else:
                target.write_bytes(disc.read_file(entry))
                print(f'  {entry.path}')

    hdt = (disc_dir / 'A_FILE.HDT').read_bytes()
    pack = (disc_dir / 'A_FILE.BIN').read_bytes()
    offsets = afile.parse_hdt(hdt)
    subfiles = afile.split(pack, offsets)
    AFILE_DIR.mkdir(parents=True, exist_ok=True)
    for i, data in enumerate(subfiles):
        (AFILE_DIR / f'{i:02d}.bin').write_bytes(data)
    print(f'  A_FILE.BIN -> {len(subfiles)} subarquivos em {AFILE_DIR.relative_to(ROOT)}/')

    # prova de que entendemos o formato: remontar tem que dar exatamente o original
    new_hdt, new_pack = afile.build(subfiles)
    if new_hdt != hdt or new_pack != pack:
        sys.exit('ERRO: remontar o A_FILE não reproduziu o original')
    print('OK: A_FILE remontado é idêntico ao original')


def load_subfiles():
    files = sorted(AFILE_DIR.glob('*.bin'))
    if not files:
        sys.exit('Nada extraído ainda. Rode antes: python3 tools/hm.py extract')
    return [f.read_bytes() for f in files]


def line_around(data, pos):
    """Volta até o {fim} anterior e avança até o próximo: a fala inteira.

    Também para antes de um bloco de zeros (preenchimento). O valor 0 é a letra "A",
    mas dois "A" seguidos quase nunca aparecem num texto de verdade.
    """
    def value(at):
        return struct.unpack_from('<H', data, at)[0]
    start = pos
    while start >= 2 and value(start - 2) != END and pos - start < 400:
        if start >= 4 and value(start - 2) == 0 and value(start - 4) == 0:
            break
        start -= 2
    end = pos
    while end + 2 <= len(data) and value(end) != END and end - pos < 400:
        end += 2
    return start, end


def cmd_find(args):
    table = Table(TABLE)
    needle = table.encode(args.text)
    hits = 0
    for index, data in enumerate(load_subfiles()):
        pos = data.find(needle)
        while pos != -1:
            if pos % 2 == 0:
                hits += 1
                start, end = line_around(data, pos)
                print(f'[{index:02d}] 0x{pos:08X}: {table.decode(data[start:end])!r}')
                if hits >= args.limit:
                    print(f'... parando em {args.limit} resultados (use --limit)')
                    return
            pos = data.find(needle, pos + 1)
    if not hits:
        print('Nada encontrado.')


def cmd_dump(args):
    """Exporta os diálogos originais para build/script/NN.json (fora do git).

    Cada fala leva também `speakers`: quem fala em cada página, na ordem das páginas.
    """
    table = Table(TABLE)
    speakers = Speakers(SPEAKERS)
    subfiles = load_subfiles()
    SCRIPT.mkdir(parents=True, exist_ok=True)
    total = 0
    for sub in dialog.SUBFILES:
        data = subfiles[sub]
        entries = []
        for index in range(dialog.record_count(data)):
            prefix, text = dialog.decode_record(table, data, index)
            # garantia de que nada se perde: codificar de volta tem que dar os mesmos bytes
            if table.encode(prefix + text) != dialog.read_text(data, index):
                sys.exit(f'ERRO: registro {sub:02d}-{index:04d} não sobrevive a decode/encode')
            entries.append({'id': f'{sub:02d}-{index:04d}', 'prefix': prefix,
                            'speakers': speakers.per_page(prefix, text), 'en': text})
        path = SCRIPT / f'{sub:02d}.json'
        path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        total += len(entries)
        print(f'  {path.relative_to(ROOT)}: {len(entries)} falas')
    exe = (BUILD / 'disc' / 'SLUS_011.15').read_bytes()
    entries = []
    for address, raw in exetext.segments(exe):
        text = table.decode_exact(raw)
        if table.encode(text) != raw:
            sys.exit(f'ERRO: {exetext.entry_id(address)} não sobrevive a decode/encode')
        if exetext.is_text(text):
            entries.append({'id': exetext.entry_id(address), 'max': len(raw) // 2, 'en': text})
    path = SCRIPT / 'exe.json'
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'  {path.relative_to(ROOT)}: {len(entries)} textos do executável')
    overlay_entries = []
    for sub in sorted(exetext.OVERLAY_STRINGS):
        for entry_id, _, raw in exetext.overlay_segments(sub, subfiles[sub]):
            text = table.decode_exact(raw)
            if table.encode(text) != raw:
                sys.exit(f'ERRO: {entry_id} não sobrevive a decode/encode')
            overlay_entries.append({'id': entry_id, 'max': len(raw) // 2, 'en': text})
    path = SCRIPT / 'overlays.json'
    path.write_text(json.dumps(overlay_entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'  {path.relative_to(ROOT)}: {len(overlay_entries)} textos dos minigames')
    print(f'OK: {total} falas, {len(entries)} textos do executável e '
          f'{len(overlay_entries)} dos minigames exportados')


def read_translation_file(path):
    """Lê um translation/NN.json. Devolve (falas, erros, avisos) sobre o arquivo em si."""
    errors, warnings = [], []

    def no_duplicates(pairs):
        seen = {}
        for key, value in pairs:
            if key in seen:
                errors.append(f'id repetido: {key}')
            seen[key] = value
        return seen

    try:
        data = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=no_duplicates)
    except json.JSONDecodeError as error:
        return {}, [f'JSON inválido na linha {error.lineno}, coluna {error.colno}: {error.msg}'], []
    if not isinstance(data, dict):
        return {}, ['o arquivo deve ser um objeto no formato {"id": "texto"}'], []
    for key, value in data.items():
        pattern = {'exe': r'exe-[0-9A-F]{8}', 'overlays': r'ov\d\d-[0-9A-F]{5}'}.get(
            path.stem, rf'{re.escape(path.stem)}-\d{{4}}')
        if not re.fullmatch(pattern, key):
            errors.append(f'id inválido ou no arquivo errado: {key}')
        elif not isinstance(value, str):
            errors.append(f'{key}: o valor deve ser um texto')
    if list(data) != sorted(data):
        warnings.append('as falas não estão em ordem crescente de id')
    return data, errors, warnings


def load_translations(folder=TRANSLATION):
    """Todas as falas de translation/*.json com texto. Sai com erro se algum arquivo estiver inválido."""
    translations = {}
    for path in sorted(Path(folder).glob('*.json')):
        data, errors, _ = read_translation_file(path)
        if errors:
            sys.exit(f'ERRO em {path.relative_to(ROOT)}: {errors[0]} (rode: python3 tools/hm.py check)')
        translations.update({key: text for key, text in data.items() if text})
    return translations


def allowed_chars(table):
    """Caracteres que uma tradução pode usar: os que têm desenho na fonte (com os acentos)."""
    return {text for text in table.decode_map.values() if len(text) == 1}


def load_originals():
    if not any(SCRIPT.glob('*.json')):
        sys.exit('Falas originais não encontradas. Rode antes: '
                 'python3 tools/hm.py extract && python3 tools/hm.py dump')
    originals = {}
    for path in sorted(SCRIPT.glob('*.json')):
        originals.update({e['id']: e for e in json.loads(path.read_text(encoding='utf-8'))})
    return originals


def cmd_check(args):
    """Confere translation/*.json contra o original e as regras do jogo (não altera nada)."""
    allowed = allowed_chars(Table(TABLE))
    originals = load_originals()
    if args.files:
        paths = [TRANSLATION / f'{name.removesuffix(".json")}.json' for name in args.files]
        missing = [p.name for p in paths if not p.exists()]
        if missing:
            sys.exit(f'Arquivo(s) não encontrado(s) em translation/: {", ".join(missing)}')
    else:
        paths = sorted(TRANSLATION.glob('*.json'))

    exe_report = ({}, {})
    if any(p.stem == 'exe' for p in paths):
        exe_data, _, _ = read_translation_file(TRANSLATION / 'exe.json')
        subfiles = [bytearray(data) for data in load_subfiles()]
        _, _, exe_errors, exe_warnings = exetext.plan(
            (BUILD / 'disc' / 'SLUS_011.15').read_bytes(), subfiles, Table(TABLE),
            {k: v for k, v in exe_data.items() if isinstance(v, str) and v}, allowed)
        exe_report = (exe_errors, exe_warnings)
    checked = with_errors = with_warnings = 0
    for path in paths:
        data, file_errors, file_warnings = read_translation_file(path)
        for message in file_errors:
            print(f'{path.name}: ERRO: {message}')
        for message in file_warnings:
            print(f'{path.name}: aviso: {message}')
        with_errors += bool(file_errors)
        for entry_id, text in data.items():
            if not isinstance(text, str) or not text or entry_id not in originals:
                if isinstance(text, str) and text and re.fullmatch(r'\d\d-\d{4}|exe-[0-9A-F]{8}|ov\d\d-[0-9A-F]{5}', entry_id):
                    print(f'{entry_id}\n  ERRO: essa fala não existe no jogo')
                    with_errors += 1
                continue
            original = originals[entry_id]
            if entry_id.startswith('exe-'):
                errors, warnings = exe_report[0].get(entry_id, []), exe_report[1].get(entry_id, [])
            elif entry_id.startswith('ov'):
                errors, warnings = exetext.validate(original['en'], text, allowed, original['max']), []
            else:
                errors, warnings = rules.validate(original['prefix'], original['en'], text, allowed)
            checked += 1
            with_errors += bool(errors)
            with_warnings += bool(warnings)
            if errors or warnings:
                print(entry_id)
                for message in errors:
                    print(f'  ERRO: {message}')
                for message in warnings:
                    print(f'  aviso: {message}')
    print(f'\n{checked} fala(s) verificada(s) em {len(paths)} arquivo(s): '
          f'{with_errors} com erro, {with_warnings} com aviso')
    if with_errors:
        sys.exit(1)
    print('OK')


def patched_font(subfile, table):
    """Aplica as letras acentuadas na fonte. Devolve (folha original, folha nova, bytes do pacote)."""
    chunks, end = font.read_package(subfile, font.FONT_PACKAGE_OFFSET)
    if any(subfile[end:font.PACKAGE_LIMIT]):
        sys.exit('ERRO: há dados entre o fim do pacote da fonte e o limite; não é seguro crescer')
    index = font.find_font(chunks)
    w, h = font.FONT_RECT[2:]
    original = font.rle_decode(chunks[index]['payload'], w * h * 2)
    sheet = font.Sheet(original)
    accents.apply(sheet, {text: code for code, text in table.decode_map.items() if len(text) == 1})
    chunks[index]['payload'] = font.rle_encode(bytes(sheet.data))
    package = font.write_package(chunks)
    if len(package) > font.PACKAGE_LIMIT:
        sys.exit(f'ERRO: a fonte nova não cabe ({len(package)} bytes, limite {font.PACKAGE_LIMIT})')
    if font.rle_decode(chunks[index]['payload'], w * h * 2) != bytes(sheet.data):
        sys.exit('ERRO: a fonte comprimida não volta igual')
    return original, bytes(sheet.data), package


def cmd_font(args):
    """Gera build/fonte.png: a folha original e a nova lado a lado, ampliadas."""
    from PIL import Image
    table = Table(TABLE)
    original, new, package = patched_font(bytearray(load_subfiles()[font.FONT_SUBFILE]), table)
    w, h, scale = font.FONT_RECT[2] * 4, font.FONT_RECT[3], 4
    image = Image.new('RGB', ((w * 2 + 8) * scale, h * scale), (240, 208, 160))
    for column, data in enumerate((original, new)):
        sheet = font.Sheet(data)
        for code in range(font.PER_ROW * (h // font.GLYPH_H)):
            for y, row in enumerate(sheet.glyph(code)):
                for x, value in enumerate(row):
                    if value:
                        gray = 40 + value * 12
                        px = (column * (w + 8) + (code % font.PER_ROW) * font.GLYPH_W + x) * scale
                        py = ((code // font.PER_ROW) * font.GLYPH_H + y) * scale
                        image.paste((gray, gray, gray), (px, py, px + scale, py + scale))
    image.save(FONT_PREVIEW)
    print(f'Prévia: {FONT_PREVIEW.relative_to(ROOT)} (original à esquerda, nova à direita)')
    print(f'Pacote da fonte: {len(package)} de {font.PACKAGE_LIMIT} bytes')


def apply_exe(iso, subfiles, table, allowed, translations, errors, warnings):
    """Grava as traduções do executável (no lugar ou em grupos reorganizados).

    Corrige também as referências que ficam nos overlays (subarquivos). Devolve
    ({'original', 'new'}, entrada do executável no disco).
    """
    with Disc(iso) as disc:
        entry = disc.find('/SLUS_011.15')
        original = disc.read_file(entry)
    new = bytearray(original)
    writes, fixes, problems, notes = exetext.plan(original, subfiles, table, translations, allowed)
    for entry_id, messages in sorted(problems.items()):
        errors += [f'{entry_id}: {message}' for message in messages]
    for entry_id, messages in sorted(notes.items()):
        warnings += [f'{entry_id}: {message}' for message in messages]
    for at, data in writes:
        new[at:at + len(data)] = data
    for target, pos, data in fixes:
        buffer = new if target == 'exe' else subfiles[target]
        buffer[pos:pos + len(data)] = data
    try:
        exetext.apply_patches(new, table)
        exetext.apply_overlay_patches(subfiles)
    except ValueError as error:
        errors.append(f'remendo do executável: {error}')
    return {'original': original, 'new': new}, entry


def apply_overlays(subfiles, table, allowed, translations, errors):
    """Grava no lugar as traduções dos textos dos minigames, dentro dos subarquivos."""
    segments = {}
    for sub in exetext.OVERLAY_STRINGS:
        for entry_id, offset, raw in exetext.overlay_segments(sub, subfiles[sub]):
            segments[entry_id] = (sub, offset, raw)
    for entry_id, text in sorted(translations.items()):
        if entry_id not in segments:
            errors.append(f'{entry_id}: esse texto não existe nos minigames')
            continue
        sub, offset, raw = segments[entry_id]
        problems = exetext.validate(table.decode_exact(raw), text, allowed, len(raw) // 2)
        if problems:
            errors += [f'{entry_id}: {message}' for message in problems]
            continue
        exetext.write_at(subfiles[sub], offset, table.encode(text), len(raw))


def cmd_build(args):
    """Aplica translation/*.json numa cópia da imagem: build/HARVESTMOON-PTBR.bin."""
    table = Table(TABLE)
    allowed = allowed_chars(table)
    translations = load_translations(args.translation)
    with Disc(args.iso) as disc:
        pack_entry = disc.find('/A_FILE.BIN')
        pack = disc.read_file(pack_entry)
        hdt = disc.read_file(disc.find('/A_FILE.HDT'))
    subfiles = [bytearray(data) for data in afile.split(pack, afile.parse_hdt(hdt))]
    _, _, package = patched_font(subfiles[font.FONT_SUBFILE], table)
    subfiles[font.FONT_SUBFILE][:font.PACKAGE_LIMIT] = package + bytes(font.PACKAGE_LIMIT - len(package))

    errors, warnings = [], []
    exe_translations = {k: v for k, v in translations.items() if k.startswith('exe-')}
    overlay_translations = {k: v for k, v in translations.items() if k.startswith('ov')}
    for entry_id in list(exe_translations) + list(overlay_translations):
        del translations[entry_id]
    exe, exe_entry = apply_exe(args.iso, subfiles, table, allowed, exe_translations, errors, warnings)
    apply_overlays(subfiles, table, allowed, overlay_translations, errors)
    for entry_id, text in sorted(translations.items()):
        sub, index = (int(part) for part in entry_id.split('-'))
        if sub not in dialog.SUBFILES or index >= dialog.record_count(subfiles[sub]):
            errors.append(f'{entry_id}: essa fala não existe no jogo')
            continue
        prefix, original = dialog.decode_record(table, subfiles[sub], index)
        rule_errors, rule_warnings = rules.validate(prefix, original, text, allowed)
        errors += [f'{entry_id}: {message}' for message in rule_errors]
        warnings += [f'{entry_id}: {message}' for message in rule_warnings]
        if rule_errors:
            continue
        try:
            dialog.write_text(subfiles[sub], index, table.encode(prefix + text))
        except ValueError as error:
            errors.append(f'{entry_id}: {error}')
    for warning in warnings:
        print(f'  aviso: {warning}')
    if errors:
        for error in errors:
            print(f'  ERRO: {error}')
        sys.exit(f'{len(errors)} erro(s), imagem não gerada')

    new_hdt, new_pack = afile.build(subfiles)
    if new_hdt != hdt:
        sys.exit('ERRO: o tamanho dos subarquivos mudou')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.iso, OUTPUT)
    changed = patch_form1(OUTPUT, pack_entry.lba, pack, new_pack)
    changed += patch_form1(OUTPUT, exe_entry.lba, exe['original'], bytes(exe['new']))
    write_cue(OUTPUT)
    print(f'OK: {len(translations)} falas, {len(exe_translations)} textos do executável e '
          f'{len(overlay_translations)} dos minigames traduzidos, {changed} setores alterados')
    print(f'Imagem: {OUTPUT.relative_to(ROOT)} (+ .cue)')


def cmd_peek(args):
    table = Table(TABLE)
    data = load_subfiles()[args.subfile]
    offset = int(args.offset, 0)
    chunk = data[offset:offset + args.chars * 2]
    print(f'[{args.subfile:02d}] 0x{offset:08X}, {len(chunk) // 2} caracteres:\n')
    print(table.decode(chunk))


def main():
    parser = argparse.ArgumentParser(description='Ferramentas da tradução de HM: Back to Nature')
    parser.add_argument('--iso', default=DEFAULT_ISO, help='imagem do jogo (padrão: %(default)s)')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('info', help='mostra arquivos do disco e subarquivos do A_FILE')
    sub.add_parser('cue', help='gera o .cue ao lado da imagem')
    sub.add_parser('extract', help='extrai arquivos e subarquivos para build/')
    p = sub.add_parser('find', help='procura um texto (em inglês) nos subarquivos')
    p.add_argument('text')
    p.add_argument('--limit', type=int, default=20)
    sub.add_parser('dump', help='exporta os diálogos originais para build/script/*.json')
    p = sub.add_parser('check', help='confere as traduções contra o original e as regras do jogo')
    p.add_argument('files', nargs='*', help='arquivos de translation/ (ex.: 03); padrão: todos')
    sub.add_parser('font', help='gera build/fonte.png com a fonte original e a nova')
    p = sub.add_parser('build', help='gera build/HARVESTMOON-PTBR.bin com a tradução e a fonte nova')
    p.add_argument('--translation', default=TRANSLATION,
                   help='pasta com as traduções (padrão: translation/)')
    p = sub.add_parser('peek', help='decodifica texto a partir de uma posição')
    p.add_argument('subfile', type=int)
    p.add_argument('offset', help='posição em bytes (aceita 0x...)')
    p.add_argument('--chars', type=int, default=200)
    args = parser.parse_args()
    {'info': cmd_info, 'cue': cmd_cue, 'extract': cmd_extract,
     'find': cmd_find, 'dump': cmd_dump, 'check': cmd_check, 'font': cmd_font, 'build': cmd_build, 'peek': cmd_peek}[args.command](args)


if __name__ == '__main__':
    main()
