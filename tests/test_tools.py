"""Testes das ferramentas. Rodar com: python3 -m unittest discover tests"""

import json
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

from hmbtn import accents, afile, dialog, ecc, font, rules  # noqa: E402
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
            self.table.encode('pingüim')

    def test_accents_encode(self):
        self.assertEqual(self.table.decode(self.table.encode('Ação, é você?')), 'Ação, é você?')


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


class RulesTest(unittest.TestCase):
    DIALOG = '{0FE4}{0FF7}{0FF4}{0FF5}{0E2E}'
    EN = "Hello, {jogador}!\nNice day.{0FFC}{0FFB}\n{0F65}{0FF7}{0F68}Let's go to the {006D}."

    def setUp(self):
        table = Table(TABLE)
        self.allowed = {t for t in table.decode_map.values() if len(t) == 1}

    def errors(self, pt, en=EN, prefix=DIALOG):
        return rules.validate(prefix, en, pt, self.allowed)[0]

    def test_good_translation(self):
        pt = 'Olá, {jogador}!\nQue dia bonito.{0FFC}{0FFB}\n{0F65}{0FF7}{0F68}Vamos ao {006D}.'
        self.assertEqual(self.errors(pt), [])

    def test_name_may_move(self):
        pt = '{jogador}, olá!\nQue dia bonito.{0FFC}{0FFB}\n{0F65}{0FF7}{0F68}Vamos ao {006D}.'
        self.assertEqual(self.errors(pt), [])

    def test_missing_page_and_codes(self):
        errors = self.errors('Olá, {jogador}! Que dia bonito. Vamos ao {006D}.')
        self.assertTrue(any('códigos de controle' in e for e in errors))
        self.assertTrue(any('página(s)' in e for e in errors))

    def test_page_must_start_with_portrait_codes(self):
        pt = 'Olá, {jogador}!{0FFC}{0FFB}\nVamos{0F65}{0FF7}{0F68} ao {006D}.'
        self.assertTrue(any('deve começar com' in e for e in self.errors(pt)))

    def test_missing_name_and_symbol(self):
        errors = self.errors('Olá!{0FFC}{0FFB}\n{0F65}{0FF7}{0F68}Vamos.')
        self.assertTrue(any('nomes variáveis' in e for e in errors))
        self.assertTrue(any('símbolos' in e for e in errors))

    def test_forbidden_characters(self):
        pt = 'Olá… {jogador}...\n“Bom” — dia.{0FFC}{0FFB}\n{0F65}{0FF7}{0F68}Vamos ao {006D}.'
        errors = self.errors(pt)
        self.assertTrue(any('—' in e and '“' in e for e in errors))
        self.assertTrue(any('...' in e for e in errors))

    def test_line_width_counts_names_as_eight(self):
        pt = 'Olá, {jogador}! Bom dia, tudo bem?{0FFC}{0FFB}\n{0F65}{0FF7}{0F68}Vamos ao {006D}.'
        self.assertTrue(any('linha com 33' in e for e in self.errors(pt)))

    def test_dialog_pages_allow_four_lines(self):
        four = 'a\nb\nc\nd'
        self.assertEqual(self.errors(four, en='a'), [])
        self.assertTrue(any('5 linhas' in e for e in self.errors(four + '\ne', en='a')))
        # fora de diálogos o limite é o número de linhas do original
        self.assertTrue(any('2 linhas' in e for e in self.errors('a\nb', en='a', prefix='{0FF3}')))

    def test_menu_options_keep_leading_space(self):
        en = 'Come?{0FFC}{0FFA}\n{0FF6}{0FF4}{0FF5}{0E2F} Yes\n No'
        good = 'Vem?{0FFC}{0FFA}\n{0FF6}{0FF4}{0FF5}{0E2F} Sim\n Não'
        bad = 'Vem?{0FFC}{0FFA}\n{0FF6}{0FF4}{0FF5}{0E2F} Sim\nNão'
        self.assertEqual(self.errors(good, en=en), [])
        self.assertTrue(any('espaço no início' in e for e in self.errors(bad, en=en)))


class FontTest(unittest.TestCase):
    def test_rle_roundtrip(self):
        data = bytes([0] * 300 + [1, 2, 3] + [9] * 5 + list(range(200)) + [7, 7])
        packed = font.rle_encode(data)
        self.assertEqual(font.rle_decode(packed, len(data)), data)
        self.assertLess(len(packed), len(data))

    def test_rle_decode_known_commands(self):
        # 0xFE = copiar 2 bytes literais; 0x03 = repetir o próximo byte 3 vezes
        self.assertEqual(font.rle_decode(bytes([0xFE, 0x49, 0x09, 0x03, 0x00]), 5), bytes([0x49, 0x09, 0, 0, 0]))

    def test_package_roundtrip(self):
        chunks = [{'kind': 6, 'x': 896, 'y': 251, 'w': 16, 'h': 1, 'payload': bytes(32)},
                  {'kind': 0, 'x': 896, 'y': 0, 'w': 32, 'h': 120, 'payload': b'\x7f\x00\x2d'}]
        data = font.write_package(chunks)
        self.assertEqual(len(data) % 4, 0)
        self.assertEqual(font.read_package(data, 0), (chunks, len(data)))

    def test_sheet_glyph_roundtrip(self):
        sheet = font.Sheet(bytes(32 * 120 * 2))
        rows = [[(x + y) % 16 for x in range(8)] for y in range(12)]
        sheet.set_glyph(0x3A, rows)
        self.assertEqual(sheet.glyph(0x3A), rows)
        self.assertTrue(sheet.is_blank(0x3B))

    def test_accents_match_table(self):
        table = Table(TABLE)
        for char, (code, base, _, _) in accents.GLYPHS.items():
            self.assertEqual(table.encode(char), struct.pack('<H', code), char)
            self.assertIn(base, table.encode_map)
        codes = [spec[0] for spec in accents.GLYPHS.values()]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertNotIn(0x1B, codes)
        self.assertNotIn(0x1E, codes)

    def test_uppercase_accent_keeps_twelve_rows(self):
        base = [[1] * 8 for _ in range(11)] + [[0] * 8]
        glyph = accents.build(base, 'acute', {'drop': (2, 6)})
        self.assertEqual(len(glyph), 12)
        self.assertEqual(glyph[11], [0] * 8)


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
