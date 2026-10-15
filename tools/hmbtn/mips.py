"""Montador e interpretador mínimos de MIPS R3000, só com as instruções que os remendos
de código usam (docs/06-textos-do-executavel.md, "Dias da semana e estações").

O interpretador existe para os testes: roda o código remendado sobre uma RAM de
mentira e confere o que ele escreve, sem precisar do emulador.
"""

import struct

REGS = {name: number for number, name in enumerate(
    'zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 '
    's0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split())}


def _r(op, rs, rt, rd, shamt, funct):
    return (op << 26) | (REGS[rs] << 21) | (REGS[rt] << 16) | (REGS[rd] << 11) | (shamt << 6) | funct


def _i(op, rs, rt, imm):
    return (op << 26) | (REGS[rs] << 21) | (REGS[rt] << 16) | (imm & 0xFFFF)


def nop():
    return 0


def sll(rd, rt, shamt):
    return _r(0, 'zero', rt, rd, shamt, 0x00)


def addu(rd, rs, rt):
    return _r(0, rs, rt, rd, 0, 0x21)


def jr(rs):
    return _r(0, rs, 'zero', 'zero', 0, 0x08)


def addiu(rt, rs, imm):
    return _i(0x09, rs, rt, imm)


def lui(rt, imm):
    return _i(0x0F, 'zero', rt, imm)


def lbu(rt, offset, base):
    return _i(0x24, base, rt, offset)


def sh(rt, offset, base):
    return _i(0x29, base, rt, offset)


def beq(rs, rt, offset):
    """offset em instruções, contado a partir da instrução seguinte (a do atraso)."""
    return _i(0x04, rs, rt, offset)


def bgez(rs, offset):
    return _i(0x01, rs, 'at', offset)          # REGIMM com rt = 1


def assemble(words):
    return b''.join(struct.pack('<I', word) for word in words)


def _s16(value):
    return value - 0x10000 if value & 0x8000 else value


def run(memory, pc, regs, limit=10_000):
    """Executa a partir de `pc` até o `jr ra` (incluindo o atraso). `memory` é um dict
    endereço -> bytearray de blocos {base: dados}; `regs` é um dict nome -> valor."""
    reg = [0] * 32
    for name, value in regs.items():
        reg[REGS[name]] = value & 0xFFFFFFFF

    def locate(address):
        for base, data in memory.items():
            if base <= address < base + len(data):
                return data, address - base
        raise IndexError(f'endereço fora da memória: {address:#x}')

    def fetch(address):
        data, pos = locate(address)
        return struct.unpack_from('<I', data, pos)[0]

    delay_target = None             # desvio pendente: vale depois da instrução do atraso
    return_after_delay = False
    for _ in range(limit):
        word = fetch(pc)
        op, rs, rt = word >> 26, (word >> 21) & 31, (word >> 16) & 31
        rd, shamt, funct, imm = (word >> 11) & 31, (word >> 6) & 31, word & 63, word & 0xFFFF
        branch, is_return, target, value = None, False, 0, 0
        if op == 0 and funct == 0x00:
            target, value = rd, (reg[rt] << shamt) & 0xFFFFFFFF
        elif op == 0 and funct == 0x21:
            target, value = rd, (reg[rs] + reg[rt]) & 0xFFFFFFFF
        elif op == 0 and funct == 0x08:
            branch, is_return = reg[rs], True
        elif op == 0x09:
            target, value = rt, (reg[rs] + _s16(imm)) & 0xFFFFFFFF
        elif op == 0x0F:
            target, value = rt, imm << 16
        elif op == 0x24:
            data, pos = locate((reg[rs] + _s16(imm)) & 0xFFFFFFFF)
            target, value = rt, data[pos]
        elif op == 0x25:
            data, pos = locate((reg[rs] + _s16(imm)) & 0xFFFFFFFF)
            target, value = rt, struct.unpack_from('<H', data, pos)[0]
        elif op == 0x29:
            data, pos = locate((reg[rs] + _s16(imm)) & 0xFFFFFFFF)
            struct.pack_into('<H', data, pos, reg[rt] & 0xFFFF)
        elif op == 0x04:
            if reg[rs] == reg[rt]:
                branch = pc + 4 + _s16(imm) * 4
        elif op == 0x01 and rt == 1:
            if not reg[rs] & 0x80000000:
                branch = pc + 4 + _s16(imm) * 4
        else:
            raise ValueError(f'{pc:#x}: instrução não suportada {word:08x}')
        if target:
            reg[target] = value
        if delay_target is not None:
            if return_after_delay:
                return {name: reg[number] for name, number in REGS.items()}
            pc, delay_target = delay_target, None
        else:
            pc += 4
        if branch is not None:
            delay_target, return_after_delay = branch, is_return
    raise RuntimeError('o código não terminou')
