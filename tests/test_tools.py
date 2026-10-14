"""Testes das ferramentas. Rodar com: python3 -m unittest discover tests"""

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

from hmbtn import afile  # noqa: E402
from hmbtn.table import Table  # noqa: E402

TABLE = ROOT / 'tables' / 'hmbtn.tbl'


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

    def test_unknown_char_raises(self):
        with self.assertRaises(ValueError):
            self.table.encode('ação')


class AfileTest(unittest.TestCase):
    def test_build_aligns_and_roundtrips(self):
        subfiles = [b'a' * 10, b'b' * 2048, b'']
        hdt, pack = afile.build(subfiles)
        self.assertEqual(afile.parse_hdt(hdt), [0, 2048, 4096, 4096])
        self.assertEqual(afile.split(pack, afile.parse_hdt(hdt))[1], b'b' * 2048)


if __name__ == '__main__':
    unittest.main()
