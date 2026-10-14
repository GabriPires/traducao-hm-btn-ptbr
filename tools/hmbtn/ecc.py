"""Códigos de detecção e correção de erro (EDC/ECC) dos setores de CD.

Cada setor Form 1 termina com:
    EDC  (4 bytes em 0x818): um CRC-32 dos dados, para *detectar* erros
    ECC  (276 bytes em 0x81C): paridade Reed-Solomon "P" e "Q", para *corrigir* erros

Quando mudamos os 2048 bytes de dados de um setor, esses códigos precisam ser
recalculados, senão um leitor de CD (ou um emulador mais rigoroso) acha que o setor
está corrompido. Algoritmo igual ao do ECM, de Neill Corlett.
"""

import struct

_EDC = []
_ECC_F = [0] * 256
_ECC_B = [0] * 256
for _i in range(256):
    _j = (_i << 1) ^ (0x11D if _i & 0x80 else 0)
    _ECC_F[_i] = _j
    _ECC_B[_i ^ _j] = _i
    _edc = _i
    for _ in range(8):
        _edc = (_edc >> 1) ^ (0xD8018001 if _edc & 1 else 0)
    _EDC.append(_edc)


def edc(data):
    value = 0
    for byte in data:
        value = (value >> 8) ^ _EDC[(value ^ byte) & 0xFF]
    return value


def _block_indexes(major_count, minor_count, major_mult, minor_inc):
    """Para cada linha da paridade, quais bytes (a partir de 0x0C) ela cobre."""
    size = major_count * minor_count
    table = []
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        row = []
        for _ in range(minor_count):
            row.append(index)
            index += minor_inc
            if index >= size:
                index -= size
        table.append(row)
    return table


_P = _block_indexes(86, 24, 2, 86)
_Q = _block_indexes(52, 43, 86, 88)


def _parity(buf, rows, out_offset):
    count = len(rows)
    for major, row in enumerate(rows):
        a = b = 0
        for index in row:
            value = buf[index]
            a = _ECC_F[a ^ value]
            b ^= value
        a = _ECC_B[_ECC_F[a] ^ b]
        buf[out_offset + major] = a
        buf[out_offset + major + count] = a ^ b


def encode_mode2_form1(sector):
    """Recalcula EDC e ECC de um setor Mode 2 Form 1 (bytearray de 2352 bytes), no lugar."""
    struct.pack_into('<I', sector, 0x818, edc(sector[0x10:0x818]))
    # no modo 2 o ECC é calculado como se os 4 bytes de endereço (0x0C) fossem zero
    buf = bytearray(4) + sector[0x10:]
    _parity(buf, _P, 0x81C - 0x0C)
    _parity(buf, _Q, 0x8C8 - 0x0C)
    sector[0x81C:] = buf[0x81C - 0x0C:]
