#!/usr/bin/env python3
"""Ferramenta de linha de comando do projeto de tradução.

Uso:
    python3 tools/hm.py info                 # informações do disco e do A_FILE
    python3 tools/hm.py cue                  # gera o .cue para abrir a imagem no emulador
    python3 tools/hm.py extract              # extrai tudo para build/
    python3 tools/hm.py find "Good morning"  # acha um texto nos subarquivos
    python3 tools/hm.py peek 2 0x1D814       # decodifica texto a partir de uma posição

A imagem original é só lida, nunca alterada.
"""

import argparse
import hashlib
import os
import struct
import sys
from pathlib import Path

from hmbtn import afile
from hmbtn.disc import Disc
from hmbtn.table import Table

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / 'build'
AFILE_DIR = BUILD / 'afile'
TABLE = ROOT / 'tables' / 'hmbtn.tbl'
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


def cmd_cue(args):
    iso = Path(args.iso)
    cue = iso.with_suffix('.cue')
    cue.write_text(f'FILE "{iso.name}" BINARY\n'
                   '  TRACK 01 MODE2/2352\n'
                   '    INDEX 01 00:00:00\n')
    print(f'Criado {cue}')


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
    p = sub.add_parser('peek', help='decodifica texto a partir de uma posição')
    p.add_argument('subfile', type=int)
    p.add_argument('offset', help='posição em bytes (aceita 0x...)')
    p.add_argument('--chars', type=int, default=200)
    args = parser.parse_args()
    {'info': cmd_info, 'cue': cmd_cue, 'extract': cmd_extract,
     'find': cmd_find, 'peek': cmd_peek}[args.command](args)


if __name__ == '__main__':
    main()
