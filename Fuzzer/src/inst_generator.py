import os
import random

from riscv_definitions import *
from word import *

""" rvInstGenerator
Generates syntactically, semantically desirable unit of instructions

Properties
 2. Compilable
 1. Guarantee forward progress and end (No loop)
"""
class rvInstGenerator():
    def __init__(self, isa='RV64G'):
        # RISC-V 32-bit Integer Base ISA: 这是最基本的 RISC-V 指令集，支持 32 位的整数运算。所有 RISC-V 处理器都至少支持这个指令集。
        '''
        标准扩展
        M (Multiplication and Division):
        整数乘法和除法扩展: 提供对整数乘法和除法的支持，增强了基本整数操作的能力。
        A (Atomic):
        原子操作扩展: 提供对原子性内存操作的支持，主要用于多核处理器中的并发控制。
        F (Single-Precision Floating-Point):
        单精度浮点数扩展: 提供对单精度(32 位)浮点数运算的支持。
        D (Double-Precision Floating-Point):
        双精度浮点数扩展: 提供对双精度(64 位)浮点数运算的支持。需要 F 扩展。
        Q (Quad-Precision Floating-Point):
        四精度浮点数扩展: 提供对四精度(128 位)浮点数运算的支持。需要 D 扩展。
        C (Compressed):
        压缩指令集扩展: 提供一组压缩指令，可以减少程序的代码大小，提高代码密度。
        Zifencei (Instruction-Fetch Fence):
        指令获取屏障扩展: 提供用于确保指令获取顺序正确的屏障指令，主要用于自修改代码或代码和数据分离的场景。
        Zicsr (Control and Status Register):
        控制和状态寄存器扩展: 提供对控制和状态寄存器(CSR)的访问和操作。
        工业扩展
        G (General):
        通用扩展：通常被定义为包含 RV32I、M、A、F、D、Zifencei 和 Zicsr 扩展的组合。这是一个通用的、适用于大多数应用的扩展集合。
        特定扩展
        trap_ret:
        陷阱和返回扩展：通常用于处理异常和中断，提供陷阱处理和返回指令。
        RV32 和 RV64 的区别
            RV32 系列支持 32 位地址和数据操作，适用于低功耗和嵌入式系统。
            RV64 系列支持 64 位地址和数据操作，适用于高性能和服务器级系统。
        '''
        isas = ['trap_ret']
        if 'I' in isa:
            isas += [ 'rv32i' ]
        if 'M' in isa:
            isas += [ 'rv32m' ]
        if 'A' in isa:
            isas += [ 'rv32a' ]
        if 'F' in isa:
            isas += [ 'rv32f' ]
        if 'zifencei' in isa:
            isas += [ 'rv_zifencei' ]
        if 'zicsr' in isa:
            isas += [ 'rv_zicsr' ]
        if 'D' in isa:
            isas += [ 'rv32d' ]
        if 'Q' in isa:
            isas += [ 'rv32q' ]
        if 'G' in isa:
            isas += [ 'rv32i', 'rv32a', 'rv32f', 'rv_zifencei', 'rv_zicsr', 'rv32m' ]

        if 'RV64' in isa:
            isas = self.extend(isas)
        self.rv_isas = isas

        self.opcodes_map = {}
        for isa in self.rv_isas:
            self.opcodes_map.update(rv_opcodes[isa])

        self.opcodes = list(self.opcodes_map.keys())

        self.prefix_num = 0
        self.main_num = 0
        self.suffix_num = 0

        self.xNums = [ i for i in range(32) ]
        self.fNums = [ i for i in range(32) ]

        self.used_xNums = set([])
        self.used_fNums = set([])
        self.used_imms = set([])


    def extend(self, isas):
        extended_isas = []
        for isa in isas:
            extended_isas.append(isa)
            if '32' in isa:
                extended_isas.append(isa.replace('32', '64'))

        return extended_isas

    def reset(self):
        self.prefix_num = 0
        self.main_num = 0
        self.suffix_num = 0

        self.used_xNums = set([])
        self.used_fNums = set([])
        self.used_imms = set([])

    def _get_xregs(self, region=(0, 31), no_zero=False, thres=0.2):
        if region == (0, 31) and len(self.used_xNums) > 0 and random.random() < thres:
            xNum = random.choice(list(self.used_xNums))
        else:
            xNum = random.choice(self.xNums[region[0]:region[1]])
            used_xNums = list(self.used_xNums) + [ xNum ]
            self.used_xNums = set(used_xNums)

        if no_zero and xNum == 0:
            xNum = random.choice(list(self.xNums)[1:])

        return 'x' + str(xNum)

    def _get_fregs(self, thres=0.2):
        if len(self.used_fNums) > 0 and random.random() < thres:
            fNum = random.choice(list(self.used_fNums))
        else:
            fNum = random.choice(self.fNums)
            used_fNums = list(self.used_fNums) + [ fNum ]
            self.used_fNums = set(used_fNums)
        return 'f' + str(fNum)

    def _get_imm(self, iName, align, thres=0.2, zfthres=0.2, alignthres=1):
        assert align & (align - 1) == 0, 'align must be power of 2'
        if 'uimm' in iName:
            sign = ''
            width = int(iName[4:])
        else:
            sign = random.choice(['', '-'])
            width = int(iName[3:]) - 1

        mask = (1 << width) - 1

        rand = random.random()
        if rand < alignthres:
            align_mask = ~(align - 1)
        else:
            align_mask = 0

        mask = mask & align_mask

        rand = random.random()
        if len(self.used_imms) > 0 and rand < thres:
            imm = random.choice(list(self.used_imms))
            return sign + str(mask & imm)
        elif rand < thres + zfthres:
            imm = random.choice([ 0x0, 0xffffffff ])
            return sign + str(mask & imm)
        else:
            imm = random.randint(0, mask)
            used_imms = list(self.used_imms) + [ imm ]
            self.used_imms = set(used_imms)
            return sign + str(mask & imm)

    def _get_symbol(self, tpe, my_label, max_label, part):
        if tpe == MEM_W:
            n = random.randint(0, 5) # TODO, num_mem_sections = 6
            k = random.randint(0, 27)
            symbol = 'd_' + str(n) + '_' + str(k)
        elif tpe == MEM_R:
            rand = random.random()
            if rand < 0.2:
                n = random.randint(0, max_label)
                symbol = part + str(n)
            else:
                n = random.randint(0, 5)
                k = random.randint(0, 27)
                symbol = 'd_' + str(n) + '_' + str(k)
        else:
            if tpe in [ CF_J, CF_RET ]:
                num = random.randint(my_label + 1, max_label)
                symbol = part + str(num)
            else:
                num = random.randint(my_label + 1, max_label)
                symbol = part + str(num)

        return symbol

    """ Word
    Set of instructions which forms compilable, forward-guaranteeing sequence.
    """
    def get_word(self, part):
        if part == PREFIX:
            opcode = random.choice(list(rv_zicsr.keys()))
            label_num = self.prefix_num
            self.prefix_num += 1
        elif part == MAIN:
            opcode = random.choice(self.opcodes)
            label_num = self.main_num
            self.main_num += 1
        else: # SUFFIX
            opcode = random.choice(self.opcodes)
            label_num = self.suffix_num
            self.suffix_num += 1
        #print("OPCODE: ",opcode)
        (syntax, xregs, fregs, imms, symbols) = self.opcodes_map.get(opcode)
        xregs = list(xregs)
        fregs = list(fregs)
        imms = list(imms)
        symbols = list(symbols)
        #print(xregs, fregs, imms, symbols)
        tpe = NONE # 
        insts = [ syntax ]

        for (key, tup) in opcodes_words.items():
            key_opcodes = tup[0]
            key_word = tup[1]
            if opcode in key_opcodes:
                (tpe, insts) = key_word(opcode, syntax, xregs, fregs, imms, symbols)
                break

        word = Word(label_num, insts, tpe, xregs, fregs, imms, symbols)

        return word

    def populate_word(self, word: Word, max_label: int, part: str):
        if word.populated:
            return

        region = (0, 31)
        if part == PREFIX:
            region = (10, 15)
        opvals = {}

        for xreg in word.xregs:
            if word.tpe == NONE:
                opvals[xreg] = self._get_xregs()
            else:
                opvals[xreg] = self._get_xregs(region, True)

        for freg in word.fregs:
            opvals[freg] = self._get_fregs()

        for (imm, align) in word.imms:
            opvals[imm] = self._get_imm(imm, align)

        for symbol in word.symbols:
            opvals[symbol] = self._get_symbol(word.tpe, word.label, max_label, part)

        word.populate(opvals, part)
