"""Leitura da imagem de disco do PS1 (formato "cru", 2352 bytes por setor).

Um CD é dividido em setores. Na imagem crua cada setor tem 2352 bytes:

    12 bytes  sync        (marcador fixo 00 FF FF ... FF 00)
     4 bytes  header      (endereço do setor + modo)
     8 bytes  subheader   (só no modo 2; diz se é dado "Form 1" ou áudio/vídeo "Form 2")
  2048 bytes  dados       (Form 1)  -- ou 2324 bytes (Form 2)
   280 bytes  EDC/ECC     (códigos de correção de erro; Form 2 usa só 4)

Arquivos "normais" (executável, A_FILE.BIN...) são Form 1: só os 2048 bytes do meio
importam. Os .XA (áudio) são Form 2 e, por isso, são extraídos com o setor inteiro.

Sobre os setores existe um sistema de arquivos ISO9660, igual ao de um CD de PC.
"""

import struct
from dataclasses import dataclass

SECTOR_SIZE = 2352
DATA_OFFSET = 24          # sync(12) + header(4) + subheader(8)
FORM1_SIZE = 2048
SUBMODE_FORM2 = 0x20      # bit do byte "submode" que indica Form 2


@dataclass
class DiscFile:
    path: str      # ex.: "/STR/01.XA"
    lba: int       # setor inicial (Logical Block Address)
    size: int      # tamanho em bytes, contado em blocos de 2048
    is_dir: bool


class Disc:
    def __init__(self, path):
        self.path = path
        self._f = open(path, 'rb')
        self._f.seek(0, 2)
        size = self._f.tell()
        if size % SECTOR_SIZE:
            raise ValueError(f'{path}: tamanho não é múltiplo de {SECTOR_SIZE}; '
                             'esperado uma imagem crua MODE2/2352')
        self.sector_count = size // SECTOR_SIZE
        if self.raw_sector(16)[15] != 2:
            raise ValueError(f'{path}: setor 16 não é modo 2')
        pvd = self.read_sector(16)
        if pvd[1:6] != b'CD001':
            raise ValueError(f'{path}: descritor de volume ISO9660 não encontrado')
        self.system_id = pvd[8:40].decode('ascii').strip()
        self.volume_id = pvd[40:72].decode('ascii').strip()
        self._root = pvd[156:156 + 34]

    def close(self):
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def raw_sector(self, lba):
        self._f.seek(lba * SECTOR_SIZE)
        return self._f.read(SECTOR_SIZE)

    def read_sector(self, lba):
        """Os 2048 bytes de dados de um setor Form 1."""
        return self.raw_sector(lba)[DATA_OFFSET:DATA_OFFSET + FORM1_SIZE]

    def is_form2(self, lba):
        return bool(self.raw_sector(lba)[18] & SUBMODE_FORM2)

    def read_data(self, lba, size):
        sectors = (size + FORM1_SIZE - 1) // FORM1_SIZE
        out = bytearray()
        for i in range(sectors):
            out += self.read_sector(lba + i)
        return bytes(out[:size])

    def read_raw(self, lba, size):
        """Setores inteiros (2352 bytes cada); usado para arquivos Form 2."""
        sectors = (size + FORM1_SIZE - 1) // FORM1_SIZE
        self._f.seek(lba * SECTOR_SIZE)
        return self._f.read(sectors * SECTOR_SIZE)

    def files(self):
        """Lista todos os arquivos e pastas do disco (percorrendo o ISO9660)."""
        lba, size = _extent(self._root)
        return list(self._walk(lba, size, '/'))

    def find(self, path):
        for entry in self.files():
            if entry.path == path:
                return entry
        raise FileNotFoundError(path)

    def read_file(self, entry):
        return self.read_data(entry.lba, entry.size)

    def _walk(self, lba, size, prefix):
        data = self.read_data(lba, size)
        i = 0
        while i < len(data):
            length = data[i]
            if length == 0:
                # registros não cruzam setores: o resto do setor é preenchimento
                i = (i // FORM1_SIZE + 1) * FORM1_SIZE
                continue
            record = data[i:i + length]
            i += length
            name_len = record[32]
            name = record[33:33 + name_len]
            if name in (b'\x00', b'\x01'):   # "." e ".."
                continue
            name = name.decode('ascii').split(';')[0]
            elba, esize = _extent(record)
            is_dir = bool(record[25] & 2)
            path = prefix + name
            yield DiscFile(path, elba, esize, is_dir)
            if is_dir:
                yield from self._walk(elba, esize, path + '/')


def _extent(record):
    lba = struct.unpack_from('<I', record, 2)[0]
    size = struct.unpack_from('<I', record, 10)[0]
    return lba, size
