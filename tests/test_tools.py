"""Testes das ferramentas. Rodar com: python3 -m unittest discover tests"""

import json
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

from hmbtn import afile, dialog, ecc  # noqa: E402
from hmbtn.disc import Disc  # noqa: E402
from hmbtn.table import Table  # noqa: E402

TABLE = ROOT / 'tables' / 'hmbtn.tbl'
ISO = ROOT / 'HARVESTMOON.iso'


class TableTest(unittest.TestCase):
    def setUp(self):
        self.table = Table(TABLE)

    def test_encode_known_line(self):
        # "Oh, it's you." como aparece no jogo: 's é um caractere só
        expected = struct.pack('<9H', 0x0E, 0x27, 0x8C, 0x0FFD, 0x28, 0x33, 0x51, 0x0FFD, 0x38) \
            + struct.pack('<3H', 0x2E, 0x34, 0x6C)
        self.assertEqual(self.table.encode("Oh, it's you."), expected)

    def test_roundtrip_with_controls_and_unknown(self):
        text = 'Hi {jogador}!\nI can\'t {0FF4}wait…{fim}'
        self.assertEqual(self.table.decode(self.table.encode(text)), text)

    def test_decode_exact_keeps_split_contraction(self):
        # "he's" escrito com apóstrofo (008D) + s, e não com o caractere único 's (0051)
        data = struct.pack('<4H', 0x27, 0x24, 0x8D, 0x32)
        text = self.table.decode_exact(data)
        self.assertEqual(text, "he{008D}s")
        self.assertEqual(self.table.encode(text), data)

    def test_unknown_char_raises(self):
        with self.assertRaises(ValueError):
            self.table.encode('ação')


class AfileTest(unittest.TestCase):
    def test_build_aligns_and_roundtrips(self):
        subfiles = [b'a' * 10, b'b' * 2048, b'']
        hdt, pack = afile.build(subfiles)
        self.assertEqual(afile.parse_hdt(hdt), [0, 2048, 4096, 4096])
        self.assertEqual(afile.split(pack, afile.parse_hdt(hdt))[1], b'b' * 2048)


class DialogTest(unittest.TestCase):
    def test_write_then_read(self):
        subfile = bytearray(b'\xAA' * dialog.RECORD_SIZE * 2)
        dialog.write_text(subfile, 1, struct.pack('<2H', 0x07, 0x28))
        self.assertEqual(dialog.read_text(subfile, 1), struct.pack('<2H', 0x07, 0x28))
        # o retrato do registro e o registro vizinho não podem ser tocados
        self.assertEqual(subfile[:dialog.RECORD_SIZE + dialog.TEXT_OFFSET],
                         b'\xAA' * (dialog.RECORD_SIZE + dialog.TEXT_OFFSET))
        self.assertEqual(subfile[-2:], b'\0\0')

    def test_text_too_long_raises(self):
        subfile = bytearray(dialog.RECORD_SIZE)
        with self.assertRaises(ValueError):
            dialog.write_text(subfile, 0, bytes(2 * (dialog.MAX_VALUES + 1)))

    def test_split_prefix(self):
        values = [0x0FE4, 0x0FF7, 0x0FF4, 0x0FF5, 0x0E2E, 0x06, 0x0FFD]
        self.assertEqual(dialog.split_prefix(values), 5)


@unittest.skipUnless(ISO.exists(), 'imagem do jogo ausente')
class EccTest(unittest.TestCase):
    def test_recomputes_original_sectors(self):
        with Disc(ISO) as disc:
            for lba in (16, 24, 182, 65580):
                original = disc.raw_sector(lba)
                sector = bytearray(original)
                sector[0x818:] = bytes(len(sector) - 0x818)
                ecc.encode_mode2_form1(sector)
                self.assertEqual(bytes(sector), original, f'setor {lba}')


class TranslationFilesTest(unittest.TestCase):
    """translation/ vai para um repositório público: só {id: texto em português}."""

    def test_format(self):
        for path in (ROOT / 'translation').glob('*.json'):
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertIsInstance(data, dict, path.name)
            for entry_id, text in data.items():
                self.assertRegex(entry_id, rf'^{re.escape(path.stem)}-\d{{4}}$')
                self.assertIsInstance(text, str, entry_id)


if __name__ == '__main__':
    unittest.main()
