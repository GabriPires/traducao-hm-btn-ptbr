#!/usr/bin/env python3
"""Ferramenta de linha de comando do projeto de tradução.

Uso:
    python3 tools/hm.py info                 # informações do disco e do A_FILE
    python3 tools/hm.py cue                  # gera o .cue para abrir a imagem no emulador
    python3 tools/hm.py extract              # extrai tudo para build/
    python3 tools/hm.py dump                 # exporta os diálogos originais para build/script/
    python3 tools/hm.py build                # aplica translation/*.json numa cópia da imagem
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

from hmbtn import afile, dialog
from hmbtn.disc import Disc, patch_form1
from hmbtn.table import Table

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / 'build'
AFILE_DIR = BUILD / 'afile'
TABLE = ROOT / 'tables' / 'hmbtn.tbl'
SCRIPT = BUILD / 'script'
TRANSLATION = ROOT / 'translation'
OUTPUT = BUILD / 'HARVESTMOON-PTBR.bin'
MAX_LINE = 30   # provisório, até medirmos a caixa de texto (Fase 3)
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
    """Exporta os diálogos originais para build/script/NN.json (fora do git)."""
    table = Table(TABLE)
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
            entries.append({'id': f'{sub:02d}-{index:04d}', 'prefix': prefix, 'en': text})
        path = SCRIPT / f'{sub:02d}.json'
        path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        total += len(entries)
        print(f'  {path.relative_to(ROOT)}: {len(entries)} falas')
    print(f'OK: {total} falas exportadas')


def load_translations():
    """Lê translation/NN.json, no formato {"02-0117": "texto"}. Textos vazios são ignorados."""
    translations = {}
    for path in sorted(TRANSLATION.glob('*.json')):
        for entry_id, text in json.loads(path.read_text(encoding='utf-8')).items():
            if not entry_id.startswith(path.stem + '-'):
                sys.exit(f'ERRO: {entry_id} está no arquivo errado ({path.name})')
            if text:
                translations[entry_id] = text
    return translations


def visible_lines(text):
    """Linhas como aparecem na tela: sem códigos, nome do jogador contando 8 letras."""
    text = text.replace('{jogador}', 'X' * 8)
    return [re.sub(r'\{[^}]*\}', '', line) for line in re.split(r'\n|\{0FFC\}\{0FFB\}', text)]


def cmd_build(args):
    """Aplica translation/*.json numa cópia da imagem: build/HARVESTMOON-PTBR.bin."""
    table = Table(TABLE)
    translations = load_translations()
    with Disc(args.iso) as disc:
        pack_entry = disc.find('/A_FILE.BIN')
        pack = disc.read_file(pack_entry)
        hdt = disc.read_file(disc.find('/A_FILE.HDT'))
    subfiles = [bytearray(data) for data in afile.split(pack, afile.parse_hdt(hdt))]

    errors, warnings = [], []
    for entry_id, text in sorted(translations.items()):
        sub, index = (int(part) for part in entry_id.split('-'))
        if sub not in dialog.SUBFILES or index >= dialog.record_count(subfiles[sub]):
            errors.append(f'{entry_id}: não existe')
            continue
        try:
            prefix, _ = dialog.decode_record(table, subfiles[sub], index)
            dialog.write_text(subfiles[sub], index, table.encode(prefix + text))
        except ValueError as error:
            errors.append(f'{entry_id}: {error}')
        for line in visible_lines(text):
            if len(line) > MAX_LINE:
                warnings.append(f'{entry_id}: linha com {len(line)} caracteres: {line!r}')
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
    write_cue(OUTPUT)
    print(f'OK: {len(translations)} falas traduzidas, {changed} setores alterados')
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
    sub.add_parser('build', help='gera build/HARVESTMOON-PTBR.bin com a tradução')
    p = sub.add_parser('peek', help='decodifica texto a partir de uma posição')
    p.add_argument('subfile', type=int)
    p.add_argument('offset', help='posição em bytes (aceita 0x...)')
    p.add_argument('--chars', type=int, default=200)
    args = parser.parse_args()
    {'info': cmd_info, 'cue': cmd_cue, 'extract': cmd_extract,
     'find': cmd_find, 'dump': cmd_dump, 'build': cmd_build, 'peek': cmd_peek}[args.command](args)


if __name__ == '__main__':
    main()
