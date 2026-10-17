"""Pacote de lançamento: o patch .xdelta, o .cue e o LEIA-ME, juntos num .zip.

O pacote nunca leva o jogo: só o patch (o que mudou) e arquivos de texto nossos.
"""

import datetime
import hashlib
import re
import zipfile
import zlib
from pathlib import Path

from . import vcdiff

NAME = 'HarvestMoon-BTN-PTBR'
VERSION = re.compile(r'\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?')

# A única imagem compatível: versão americana, BIN de faixa única (igual ao README).
ORIGINAL = {'size': 213954384, 'crc32': 'b0e8f078', 'md5': '424f9fbda58e95f597e39b4bdde239b1',
            'sha1': 'cb26381fa1336bdd15f07469e59f1143ccf37b03'}


class Hasher:
    """Recebe bytes como um arquivo e calcula tamanho, CRC32, MD5 e SHA-1."""

    def __init__(self):
        self.size, self.crc, self.md5, self.sha1 = 0, 0, hashlib.md5(), hashlib.sha1()

    def write(self, data):
        self.size += len(data)
        self.crc = zlib.crc32(data, self.crc)
        self.md5.update(data)
        self.sha1.update(data)

    def result(self):
        return {'size': self.size, 'crc32': f'{self.crc:08x}', 'md5': self.md5.hexdigest(),
                'sha1': self.sha1.hexdigest()}


def checksums(path):
    hasher = Hasher()
    with open(path, 'rb') as f:
        while chunk := f.read(1 << 20):
            hasher.write(chunk)
    return hasher.result()


def cue_text(bin_name):
    return (f'FILE "{bin_name}" BINARY\n'
            '  TRACK 01 MODE2/2352\n'
            '    INDEX 01 00:00:00\n')


def _size(value):
    return f'{value:,}'.replace(',', '.') + ' bytes'


def _sums(sums, indent='  '):
    return '\n'.join(f'{indent}{label:<8}: {value}' for label, value in (
        ('Tamanho', _size(sums['size'])), ('CRC32', sums['crc32']), ('MD5', sums['md5']),
        ('SHA-1', sums['sha1'])))


README = """\
Harvest Moon: Back to Nature - Tradução PT-BR
Versão {version} ({date})

Tradução de fã para português do Brasil de Harvest Moon: Back to Nature (PlayStation,
versão americana). Este pacote contém só o patch: o jogo NÃO está incluído.

SITUAÇÃO DESTA VERSÃO
- Prévia para testes: todos os textos estão traduzidos (falas, cartas, TV, menus,
  itens, lojas, calendário, memory card e minigames).
- Os gráficos com texto (tela de título e alguns menus desenhados) ainda estão em
  inglês.

ARQUIVOS
- {patch}  o patch
- {cue}  abre a imagem traduzida no emulador
- LEIA-ME.txt  este arquivo

IMAGEM NECESSÁRIA
Versão americana (NTSC-U, SLUS-01115), em imagem BIN/CUE de faixa única:
{original}
Confira o checksum antes de aplicar. Outras versões (europeia, japonesa) ou imagens
com outro tamanho não funcionam.

COMO APLICAR
No navegador, com o Rom Patcher JS (https://www.marcrobledo.com/RomPatcher.js/):
  1. Em "ROM file", escolha o .bin original.
  2. Em "Patch file", escolha {patch}.
  3. Clique em "Apply patch" e salve o resultado.
No Windows, também funcionam o Delta Patcher e o xdelta UI.
Na linha de comando, com o xdelta3:
  xdelta3 -d -s "jogo original.bin" {patch} {bin}

DEPOIS DE APLICAR
Dê à imagem gerada o nome {bin} e deixe-a na mesma pasta de {cue}.
Abra o .cue no emulador (os testes são feitos no DuckStation).
A imagem traduzida correta tem:
{patched}

SAVES
Os saves do memory card continuam valendo: o jogo traduzido usa os mesmos saves do
original. Já um save state (estado salvo do emulador) feito no jogo original guarda a
memória com o texto em inglês: para continuar um jogo na tradução, carregue o diário
pelo memory card.

AVISO LEGAL
Projeto de fã, gratuito e sem fins lucrativos, sem afiliação com Natsume Inc., Victor
Interactive Software Inc. ou seus sucessores. Harvest Moon é marca registrada da
Natsume Inc.; Harvest Moon: Back to Nature (c) 2000 Natsume Inc. / Victor Interactive
Software Inc. Para usar o patch é necessário possuir uma cópia original do jogo.
"""


def make(original, translated, out_dir, version, date=None):
    """Gera em `out_dir` o patch, o .cue, o LEIA-ME e o .zip com os três.

    Antes de empacotar, aplica o patch gerado sobre o original e confere se o resultado
    é idêntico à imagem traduzida. Devolve {'zip', 'patch', 'patched', 'size'}.
    """
    if not VERSION.fullmatch(version):
        raise ValueError(f'versão inválida: {version} (use algo como 0.1.0 ou 0.1.0-beta)')
    date = date or datetime.date.today()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f'{NAME}-v{version}'
    patch_path, cue_name, bin_name = out_dir / f'{stem}.xdelta', f'{NAME}.cue', f'{NAME}.bin'

    with open(original, 'rb') as source, open(translated, 'rb') as target, \
            open(patch_path, 'wb') as out:
        vcdiff.encode(source, target, out)
    patched = checksums(translated)
    check = Hasher()
    with open(original, 'rb') as source:
        vcdiff.apply(source, patch_path.read_bytes(), check)
    if check.result() != patched:
        raise RuntimeError('o patch aplicado não reproduz a imagem traduzida')

    readme = README.format(version=version, date=date.strftime('%d/%m/%Y'), patch=patch_path.name,
                           cue=cue_name, bin=bin_name, original=_sums(checksums(original)),
                           patched=_sums(patched))
    zip_path = out_dir / f'{stem}.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        package.write(patch_path, patch_path.name)
        package.writestr(cue_name, cue_text(bin_name).replace('\n', '\r\n'))
        package.writestr('LEIA-ME.txt', readme.replace('\n', '\r\n'))
    return {'zip': zip_path, 'patch': patch_path, 'patched': patched,
            'size': patch_path.stat().st_size}
