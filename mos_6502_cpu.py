#----------Miscellaneous----------
from pathlib import Path
from array import array
import time



#----------Roms----------

#Custom 6502 ASM
import raw_6502asm_rom_loader


#Apple I
import apple_i_roms_loader


#Atari 2600
import atari_2600_roms_loader




#----------Graphics----------
from PIL import Image

import glfw
import numpy as np
from OpenGL.GL import *

base_path = Path(__file__).parent


option = 1

if option == 0:
    custom6502 = True
    apple_i = False
    atari_2600 = False
    

elif option == 1:
    apple_i = True
    custom6502 = False
    atari_2600 = False


elif option == 2:
    atari_2600 = True
    custom6502 = False
    apple_i = False




if custom6502 == True:
    ram_64KB = raw_6502asm_rom_loader.ram_64KB

    pc = raw_6502asm_rom_loader.pc

if apple_i == True:
    ram_64KB = apple_i_roms_loader.program

    pc = apple_i_roms_loader.pc

if atari_2600 == True:
    ram_64KB = atari_2600_roms_loader.program

    pc = atari_2600_roms_loader.pc




#----------Registers----------

#Accumulator
ac = 0

#X Register
x = 0 

#Y Register
y = 0 

#Status Register [NV-BDIZC]	
sr = 0x00 

#Stack Pointer
sp = 0xFF 

halt = False #For break (BRK)

# SR FLAGS : N V - B D I Z C



def negative_flag(ac, sr):
    #Negative Flag (N)
    if ac & 0x80:
        sr |= 0x80
    else:
        sr &= ~0x80
    return sr

def zero_flag(ac, sr):
    #Zero Flag (Z)
    if ac == 0:
        sr |= 0x02
    else:
        sr &= ~0x02
    return sr

def interrupt_test_chip(a):
    a += 1
    if a == 10:
        set_nmi(False)
    elif a == 12:
        set_nmi(False)
    return a

def push_byte(value):
    global sp
    ram_64KB[0x0100 + sp] = value & 0xFF
    sp = (sp - 1) & 0xFF 

def pull_byte():
    global sp
    sp = (sp + 1) & 0xFF
    return ram_64KB[0x0100 + sp]

def take_interrupt(pc, sr, vector, break_flag=False, pc_offset=0):
    
    addr_to_push = (pc + pc_offset) & 0xFFFF
    push_byte((addr_to_push >> 8) & 0xFF)
    push_byte(addr_to_push & 0xFF)

    status_to_push = sr | 0x20
    if break_flag:
        status_to_push |= 0x10
    else:
        status_to_push &= ~0x10

    push_byte(status_to_push)

    # Set Interrupt Disable flag
    sr |= 0x04

    # Load vector
    pc = ram_64KB[vector] | (ram_64KB[vector + 1] << 8)

    return pc, sr

def set_nmi(level):
    global nmi_line, nmi_latched
    if level and not nmi_line:  #rising edge
        nmi_latched = True
    nmi_line = level

def check_interrupts(pc, sr):
    global nmi_latched, irq
    if nmi_latched:
        
        nmi_latched = False
        pc, sr = take_interrupt(pc, sr, 0xFFFA)
    elif irq and not (sr & 0x04):
        
        pc, sr, = take_interrupt(pc, sr, 0xFFFE)
    return pc, sr

#Initialize CPU

a = 0
irq = False

nmi_line = False
nmi_latched = False


opcode = 0
operand_lower = 0
operand_higher = 0

cycle_count = 0

def perform_opcode(pc, opcode, operand_lower, operand_higher, ac, x, y, sr, sp, cycle_count):
    halt = False


#Legal Opcodes

    if opcode == 0x69: #ADC Immediate

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        
        result = ac + operand_lower + cin

        #Carry Flag (C)
        if result > 0xFF:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ operand_lower) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 2
        cycle_count += 2

    elif opcode == 0x65: #ADC Zero Page

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        value = ram_64KB[operand_lower]
        result = ac + value + cin

        #Carry Flag (C)
        if result > 0xFF:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 2
        cycle_count += 3
    
    elif opcode == 0x75: #ADC Zero Page, X

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        addr = (operand_lower + x) & 0xFF
        value = ram_64KB[addr]
        result = ac + value + cin

        #Carry Flag (C)
        if result > 0xFF:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 2
        cycle_count += 4

    elif opcode == 0x6D: #ADC Absolute

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]
        result = ac + value + cin

        #Carry Flag (C)
        if result > 0xFF:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 3
        cycle_count += 4

    elif opcode == 0x7D: #ADC Absolute, X

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        base = (operand_higher << 8) | operand_lower
        addr = (base + x) & 0xFFFF
        value = ram_64KB[addr]

        result = ac + value + cin

        #Carry Flag (C)
        if result > 0xFF:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 3
        cycle_count += 4

    elif opcode == 0x79: #ADC Absolute, Y

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        base = (operand_higher << 8) | operand_lower
        addr = (base + y) & 0xFFFF
        value = ram_64KB[addr]
        
        result = ac + value + cin

        #Carry Flag (C)
        if result > 0xFF:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 3
        cycle_count += 4

    elif opcode == 0x61: #ADC Indirect, X

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        zp = (operand_lower + x) & 0xFF

        low = ram_64KB[zp]
        high = ram_64KB[(zp + 1) & 0xFF]

        addr = (high << 8) | low
        value = ram_64KB[addr]
        
        result = ac + value + cin

        #Carry Flag (C)
        if result > 0xFF:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 2
        cycle_count += 6

    elif opcode == 0x71: #ADC Indirect, Y

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        zp = operand_lower

        low = ram_64KB[zp]
        high = ram_64KB[(zp + 1) & 0xFF]

        base = (high << 8) | low
        addr = (base + y) & 0xFFFF
        value = ram_64KB[addr]
        
        result = ac + value + cin

        #Carry Flag (C)
        if result > 0xFF:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 2
        cycle_count += 5



    elif opcode == 0x29: #AND Immediate
        
        result = ac & operand_lower

        sr = zero_flag(result, sr)
        sr = negative_flag(result, sr)

        ac = result

        pc += 2
        cycle_count += 2

    elif opcode == 0x25: #AND Zero Page
        
        value = ram_64KB[operand_lower]
        result = ac & value

        sr = zero_flag(result, sr)
        sr = negative_flag(result, sr)

        ac = result

        pc += 2
        cycle_count += 3

    elif opcode == 0x35: #AND Zero Page, X
        
        addr = (operand_lower + x) & 0xFF
        value = ram_64KB[addr]
        result = ac & value

        sr = zero_flag(result, sr)
        sr = negative_flag(result, sr)

        ac = result

        pc += 2
        cycle_count += 4

    elif opcode == 0x2D: #AND Absolute
        
        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]
        result = ac & value

        sr = zero_flag(result, sr)
        sr = negative_flag(result, sr)

        ac = result

        pc += 3
        cycle_count += 4

    elif opcode == 0x3D: #AND Absolute, X
        
        base = (operand_higher << 8) | operand_lower
        addr = (base + x) & 0xFFFF
        value = ram_64KB[addr]
        result = ac & value

        sr = zero_flag(result, sr)
        sr = negative_flag(result, sr)

        ac = result

        pc += 3
        cycle_count += 4

    elif opcode == 0x39: #AND Absolute, Y
        
        base = (operand_higher << 8) | operand_lower
        addr = (base + y) & 0xFFFF
        value = ram_64KB[addr]
        result = ac & value

        sr = zero_flag(result, sr)
        sr = negative_flag(result, sr)

        ac = result

        pc += 3
        cycle_count += 4

    elif opcode == 0x21: #AND Indirect, X
        
        zp = (operand_lower + x) & 0xFF

        low = ram_64KB[zp]
        high = ram_64KB[(zp + 1) & 0xFF]

        addr = (high << 8) | low
        value = ram_64KB[addr]

        result = ac & value

        sr = zero_flag(result, sr)
        sr = negative_flag(result, sr)

        ac = result

        pc += 2
        cycle_count += 6

    elif opcode == 0x31: #AND Indirect, Y
        
        zp = operand_lower

        low = ram_64KB[zp]
        high = ram_64KB[(zp + 1) & 0xFF]

        base = (high << 8) | low
        addr = (base + y) & 0xFFFF
        value = ram_64KB[addr]
        
        result = ac & value

        sr = zero_flag(result, sr)
        sr = negative_flag(result, sr)

        ac = result

        pc += 2
        cycle_count += 5



    elif opcode == 0x0A: #ASL Accumulator
        
        #Carry Flag
        if ac & 0x80:
            sr |= 0x01
        else:
            sr &= ~0x01

        ac = (ac << 1) & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        pc += 1
        cycle_count += 2

    elif opcode == 0x06: #ASL Zero Page
        
        value = ram_64KB[operand_lower]

        #Carry Flag
        if value & 0x80:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = (value << 1) & 0xFF
        ram_64KB[operand_lower] = value

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 5

    elif opcode == 0x16: #ASL Zero Page, X
        
        addr = (operand_lower + x) & 0xFF
        value = ram_64KB[addr]

        #Carry Flag
        if value & 0x80:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = (value << 1) & 0xFF
        ram_64KB[addr] = value

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 6

    elif opcode == 0x0E: #ASL Absolute
        
        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]

        #Carry Flag
        if value & 0x80:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = (value << 1) & 0xFF
        ram_64KB[addr] = value

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 3
        cycle_count += 6

    elif opcode == 0x1E: #ASL Absolute, X
        
        base = (operand_higher << 8) | operand_lower
        addr = (base + x) & 0xFFFF
        value = ram_64KB[addr]

        #Carry Flag
        if value & 0x80:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = (value << 1) & 0xFF

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 3
        cycle_count += 7



    elif opcode == 0x24: #BIT Zero Page
        addr = operand_lower
        value = ram_64KB[addr]

        sr = zero_flag(ac & value, sr)

        sr = (sr & ~0xC0) | (value & 0xC0)


        
        pc += 2
        cycle_count += 3

    elif opcode == 0x2C: #BIT Absolute
        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]

        sr = zero_flag(ac & value, sr)

        sr = (sr & ~0xC0) | (value & 0xC0)

        

        pc += 3
        cycle_count += 4



#Branch Instructions

    elif opcode == 0x10: #BPL (Branch on Plus)
        offset = operand_lower
        if offset & 0x80:
            offset -= 0x100

        if not (sr & 0x80):
            pc = (pc + 2 + offset) & 0xFFFF
            cycle_count += 3
        else:
            pc += 2
            cycle_count += 2

    elif opcode == 0x30: #BMI (Branch on Minus)
        offset = operand_lower
        if offset & 0x80:
            offset -= 0x100

        if sr & 0x80:
            pc = (pc + 2 + offset) & 0xFFFF
            cycle_count += 3
        else:
            pc += 2
            cycle_count += 2
        
    elif opcode == 0x50: #BVC (Branch on Overflow Clear)
        offset = operand_lower
        if offset & 0x80:
            offset -= 0x100

        if not (sr & 0x40):
            pc = (pc + 2 + offset) & 0xFFFF
            cycle_count += 3
        else:
            pc += 2
            cycle_count += 2

    elif opcode == 0x70: #BVS (Branch on Overflow Set)
        offset = operand_lower
        if offset & 0x80:
            offset -= 0x100

        if sr & 0x40:
            pc = (pc + 2 + offset) & 0xFFFF
            cycle_count += 3
        else:
            pc += 2
            cycle_count += 2

    elif opcode == 0x90: #BCC (Branch on Carry Clear)
        offset = operand_lower
        if offset & 0x80:
            offset -= 0x100

        if not (sr & 0x01):
            pc = (pc + 2 + offset) & 0xFFFF
            cycle_count += 3
        else:
            pc += 2
            cycle_count += 2

    elif opcode == 0xB0: #BCS (Branch on Carry Set)
        offset = operand_lower
        if offset & 0x80:
            offset -= 0x100

        if sr & 0x01:
            pc = (pc + 2 + offset) & 0xFFFF
            cycle_count += 3
        else:
            pc += 2
            cycle_count += 2

    elif opcode == 0xD0:  #BNE (Branch Not Equal)
        offset = ram_64KB[(pc + 1) & 0xFFFF]  # next byte after opcode
        if offset & 0x80:
            offset -= 0x100  # signed
        if not (sr & 0x02):  # Zero flag clear
            pc = (pc + 2 + offset) & 0xFFFF
            cycle_count += 3
        else:
            pc += 2
            cycle_count += 2
        
    elif opcode == 0xF0: #BEQ (Branch on Equal)
        offset = operand_lower
        if offset & 0x80:
            offset -= 0x100

        if sr & 0x02:
            pc = (pc + 2 + offset) & 0xFFFF
            cycle_count += 3
        else:
            pc += 2
            cycle_count += 2



    elif opcode == 0x00: #BRK Implied
        # Increment PC first
        
        # Then push PC & flags, then vector
        pc, sr = take_interrupt(pc, sr, vector=0xFFFE, break_flag=True, pc_offset=2)

        cycle_count += 7

        halt = True
        print("BREAK OCCURED")



    elif opcode == 0xC9: #CMP Immediate

        value = operand_lower & 0xFF
        ac8 = ac & 0xFF        # ensure 8-bit value

        temp = (ac8 - value) & 0xFF

        # Carry flag (set if A >= M)
        if ac8 >= value:
            sr |= 0x01
        else:
            sr &= ~0x01

        # Zero
        if temp == 0:
            sr |= 0x02     # Zero flag is bit 1
        else:
            sr &= ~0x02

        # Negative
        if temp & 0x80:
            sr |= 0x80     # Negative flag is bit 7
        else:
            sr &= ~0x80

        pc += 2
        cycle_count += 2

    elif opcode == 0xC5: #CMP Zero Page

        value = ram_64KB[operand_lower]
        temp = (ac - value) & 0xFF

        # Carry
        if ac >= value:
            sr |= 0x01
        else:
            sr &= ~0x01

        # Zero
        if temp == 0:
            sr |= 0x02     # Zero flag is bit 1
        else:
            sr &= ~0x02

        # Negative
        if temp & 0x80:
            sr |= 0x80     # Negative flag is bit 7
        else:
            sr &= ~0x80

        pc += 2
        cycle_count += 3

    elif opcode == 0xD5: #CMP Zero Page, X

        addr = (operand_lower + x) & 0xFF
        value = ram_64KB[addr]
        temp = (ac - value) & 0xFF

        # Carry
        if ac >= value:
            sr |= 0x01
        else:
            sr &= ~0x01

        # Zero
        if temp == 0:
            sr |= 0x02     # Zero flag is bit 1
        else:
            sr &= ~0x02

        # Negative
        if temp & 0x80:
            sr |= 0x80     # Negative flag is bit 7
        else:
            sr &= ~0x80

        pc += 2
        cycle_count += 4

    elif opcode == 0xCD: #CMP Absolute

        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]
        temp = (ac - value) & 0xFF

                # Carry
        if ac >= value:
            sr |= 0x01
        else:
            sr &= ~0x01

        # Zero
        if temp == 0:
            sr |= 0x02     # Zero flag is bit 1
        else:
            sr &= ~0x02

        # Negative
        if temp & 0x80:
            sr |= 0x80     # Negative flag is bit 7
        else:
            sr &= ~0x80
        pc += 3
        cycle_count += 4

    elif opcode == 0xDD: #CMP Absolute, X

        base = (operand_higher << 8) | operand_lower
        addr = (base + x) & 0xFFFF
        value = ram_64KB[addr]
        temp = (ac - value) & 0xFF

        # Carry
        if ac >= value:
            sr |= 0x01
        else:
            sr &= ~0x01

        # Zero
        if temp == 0:
            sr |= 0x02     # Zero flag is bit 1
        else:
            sr &= ~0x02

        # Negative
        if temp & 0x80:
            sr |= 0x80     # Negative flag is bit 7
        else:
            sr &= ~0x80

        pc += 3
        cycle_count += 4

    elif opcode == 0xD9: #CMP Absolute, Y

        base = (operand_higher << 8) | operand_lower
        addr = (base + y) & 0xFFFF
        value = ram_64KB[addr]
        temp = (ac - value) & 0xFF

        # Carry
        if ac >= value:
            sr |= 0x01
        else:
            sr &= ~0x01

        # Zero
        if temp == 0:
            sr |= 0x02     # Zero flag is bit 1
        else:
            sr &= ~0x02

        # Negative
        if temp & 0x80:
            sr |= 0x80     # Negative flag is bit 7
        else:
            sr &= ~0x80

        pc += 3
        cycle_count += 4

    elif opcode == 0xC1: #CMP Indriect, X

        zp = (operand_lower + x) & 0xFF

        low = ram_64KB[zp]
        high = ram_64KB[(zp + 1) & 0xFF]

        addr = (high << 8) | low
        value = ram_64KB[addr]
        temp = (ac - value) & 0xFF

        # Carry
        if ac >= value:
            sr |= 0x01
        else:
            sr &= ~0x01

        # Zero
        if temp == 0:
            sr |= 0x02     # Zero flag is bit 1
        else:
            sr &= ~0x02

        # Negative
        if temp & 0x80:
            sr |= 0x80     # Negative flag is bit 7
        else:
            sr &= ~0x80

        pc += 2
        cycle_count += 6

    elif opcode == 0xD1: #CMP Indriect, Y

        zp = operand_lower

        low = ram_64KB[zp]
        high = ram_64KB[(zp + 1) & 0xFF]

        base = (high << 8) | low
        addr = (base + y) & 0xFFFF
        value = ram_64KB[addr]
        temp = (ac - value) & 0xFF

        # Carry
        if ac >= value:
            sr |= 0x01
        else:
            sr &= ~0x01

        # Zero
        if temp == 0:
            sr |= 0x02     # Zero flag is bit 1
        else:
            sr &= ~0x02

        # Negative
        if temp & 0x80:
            sr |= 0x80     # Negative flag is bit 7
        else:
            sr &= ~0x80

        pc += 2
        cycle_count += 5



    elif opcode == 0xE0: #CPX Immediate

        # Carry: set if X >= value
        if x >= operand_lower:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = (x - operand_lower) & 0xFF

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 2

    elif opcode == 0xE4: #CPX Zero Page

        # Carry: set if X >= value

        addr = ram_64KB[operand_lower]

        if x >= addr:
            sr |= 0x01
        else:
            sr &= ~0x01
        
        value = (x - addr) & 0xFF

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 3

    elif opcode == 0xEC: #CPX Absolite

        # Carry: set if X >= value

        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]

        if x >= value:
            sr |= 0x01
        else:
            sr &= ~0x01
        
        result = (x - addr) & 0xFF

        sr = zero_flag(result, sr)

        sr = negative_flag(result, sr)

        pc += 3
        cycle_count += 4



    elif opcode == 0xC0: #CPY Immediate

        # Carry: set if Y >= value
        if y >= operand_lower:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = (y - operand_lower) & 0xFF

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 2

    elif opcode == 0xC4: #CPY Zero Page

        # Carry: set if Y >= value

        addr = ram_64KB[operand_lower]

        if y >= addr:
            sr |= 0x01
        else:
            sr &= ~0x01
        
        value = (y - addr) & 0xFF

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 3

    elif opcode == 0xCC: #CPY Absolite

        # Carry: set if Y >= value

        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]

        if y >= value:
            sr |= 0x01
        else:
            sr &= ~0x01
        
        result = (y - addr) & 0xFF

        sr = zero_flag(result, sr)

        sr = negative_flag(result, sr)

        pc += 3
        cycle_count += 4



    elif opcode == 0xC6: #DEC Zero Page
        addr = operand_lower
        value = (ram_64KB[addr] - 1) & 0xFF
        ram_64KB[addr] = value

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 5

    elif opcode == 0xD6: #DEC Zero Page, X
        addr = (operand_lower + x) & 0xFF
        value = (ram_64KB[addr] - 1) & 0xFF
        ram_64KB[addr] = value
        
        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 6

    elif opcode == 0xCE: #DEC Absolute
        addr = (operand_higher << 8) | operand_lower
        value = (ram_64KB[addr] - 1) & 0xFF
        ram_64KB[addr] = value

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 3
        cycle_count += 6

    elif opcode == 0xDE: #DEC Absolute, X
        addr = ((operand_higher << 8) | operand_lower) + x
        addr &= 0xFFFF

        value = (ram_64KB[addr] - 1) & 0xFF
        ram_64KB[addr] = value

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 3
        cycle_count += 7



    elif opcode == 0x49: #EOR Immediate

        ac = (ac ^ operand_lower) & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 2

    elif opcode == 0x45: #EOR Zero Page

        addr = operand_lower
        value = ram_64KB[addr]
        ac = (ac ^ value) & 0xFF

        sr = zero_flag(ac, sr)
        
        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 3

    elif opcode == 0x55: #EOR Zero Page, X

        addr = (operand_lower + x) & 0xFF
        value = ram_64KB[addr]
        ac = (ac ^ value) & 0xFF

        sr = zero_flag(ac, sr)
        
        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 4

    elif opcode == 0x4D: #EOR Absolute

        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]
        ac = (ac ^ value) & 0xFF

        sr = zero_flag(ac, sr)
        
        sr = negative_flag(ac, sr)

        pc += 3
        cycle_count += 4

    elif opcode == 0x5D: #EOR Absolute, X

        addr = ((operand_higher << 8) | operand_lower) + x
        addr &= 0xFFFF

        value = ram_64KB[addr]
        ac = (ac ^ value) & 0xFF

        sr = zero_flag(ac, sr)
        
        sr = negative_flag(ac, sr)

        pc += 3
        cycle_count += 4

    elif opcode == 0x59: #EOR Absolute, Y

        addr = ((operand_higher << 8) | operand_lower) + y
        addr &= 0xFFFF

        value = ram_64KB[addr]
        ac = (ac ^ value) & 0xFF

        sr = zero_flag(ac, sr)
        
        sr = negative_flag(ac, sr)

        pc += 3
        cycle_count += 4

    elif opcode == 0x41: #EOR Indirect, X

        zp = (operand_lower + x) & 0xFF

        low = ram_64KB[zp]
        high = ram_64KB[(zp + 1) & 0xFF]

        addr = (high << 8) | low
        value = ram_64KB[addr]
        ac = (ac ^ value) & 0xFF

        sr = zero_flag(ac, sr)
        
        sr = negative_flag(ac, sr)

        pc += 3
        cycle_count += 6

    elif opcode == 0x51: #EOR Indirect, Y

        zp = (operand_lower + y) & 0xFF

        low = ram_64KB[zp]
        high = ram_64KB[(zp + 1) & 0xFF]

        addr = (high << 8) | low
        value = ram_64KB[addr]
        ac = (ac ^ value) & 0xFF

        sr = zero_flag(ac, sr)
        
        sr = negative_flag(ac, sr)

        pc += 3
        cycle_count += 5



#Flag (Processor Status) Instructions

    elif opcode == 0x18: #CLC (Clear Carry)
        sr &= ~0x01
        pc += 1
        cycle_count += 2

    elif opcode == 0x38: #SEC (Set Carry)
        sr |= 0x01
        pc += 1
        cycle_count += 2

    elif opcode == 0x58: #CLI (Clear Interrupt)
        sr &= ~0x04
        pc += 1
        cycle_count += 2

    elif opcode == 0x78: #SEI (Set Interrupt)
        sr |= 0x04
        pc += 1
        cycle_count += 2

    elif opcode == 0xB8: #CLV (Clear Overflow)
        sr &= ~0x40
        pc += 1
        cycle_count += 2

    elif opcode == 0xD8: #CLD (Clear Decimal)
        sr &= ~0x08
        pc += 1
        cycle_count += 2

    elif opcode == 0xF8: #SED (Set Decimal)
        sr |= 0x08
        pc += 1
        cycle_count += 2
    


    elif opcode == 0xE6: #INC Zero Page
        addr = operand_lower
        value = (ram_64KB[addr] + 1) & 0xFF
        ram_64KB[addr] = value

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 5

    elif opcode == 0xF6: #INC Zero Page, X
        addr = (operand_lower + x) & 0xFF
        value = (ram_64KB[addr] + 1) & 0xFF
        ram_64KB[addr] = value
        
        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 6

    elif opcode == 0xEE: #INC Absolute
        addr = (operand_higher << 8) | operand_lower
        value = (ram_64KB[addr] + 1) & 0xFF
        ram_64KB[addr] = value

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 3
        cycle_count += 6

    elif opcode == 0xFE: #INC Absolute, X
        addr = ((operand_higher << 8) | operand_lower) + x
        addr &= 0xFFFF

        value = (ram_64KB[addr] + 1) & 0xFF
        ram_64KB[addr] = value

        sr = zero_flag(value, sr)

        sr = negative_flag(value, sr)

        pc += 3
        cycle_count += 7



    elif opcode == 0x4C: #JMP Absolute
        pc = (operand_higher << 8) | operand_lower
        cycle_count += 3
    
    elif opcode == 0x6C: #JMP Indirect
        ptr = (operand_higher << 8) | operand_lower

        low = ram_64KB[ptr]

        # 6502 hardware bug emulation
        if (ptr & 0x00FF) == 0x00FF:
            high = ram_64KB[ptr & 0xFF00]
        else:
            high = ram_64KB[ptr + 1]

        pc = (high << 8) | low
        cycle_count += 5



    elif opcode == 0x20: #JSR Absolute
        target = (operand_higher << 8) | operand_lower
        return_addr = pc + 2

        ram_64KB[0x0100 + sp] = (return_addr >> 8) & 0xFF
        sp = (sp - 1) & 0xFF

        ram_64KB[0x0100 + sp] = return_addr & 0xFF
        sp = (sp - 1) & 0xFF

        pc = target
        cycle_count += 6



    elif opcode == 0xA9: #LDA Immediate
        ac = operand_lower

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 2

    elif opcode == 0xA5: #LDA Zero Page
        ac = ram_64KB[operand_lower]

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 3

    elif opcode == 0xB5: #LDA Zero Page, X

        addr = (operand_lower + x) & 0xFF
        ac = ram_64KB[addr]

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 4

    elif opcode == 0xAD: #LDA Absolute

        addr = (operand_higher << 8) | operand_lower
        ac = ram_64KB[addr]

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        pc += 3
        cycle_count += 4
    
    elif opcode == 0xBD: #LDA Absolute, X

        base = (operand_higher << 8) | operand_lower
        addr = (base + x) & 0xFFFF

        ac = ram_64KB[addr]

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        pc += 3
        cycle_count += 4

    elif opcode == 0xB9: #LDA Absolute, Y

        base = (operand_higher << 8) | operand_lower
        addr = (base + y) & 0xFFFF

        ac = ram_64KB[addr]

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        pc += 3
        cycle_count += 4

    elif opcode == 0xA1: #LDA Indirect, X

        zp_addr = (operand_lower + x) & 0xFF

        low_byte = ram_64KB[zp_addr]
        high_byte = ram_64KB[(zp_addr + 1) & 0xFF]

        base_addr = (high_byte << 8) | low_byte

        ac = ram_64KB[base_addr]


        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 6

    elif opcode == 0xB1: #LDA Indirect, Y

        zp_addr = operand_lower

        low_byte = ram_64KB[zp_addr]
        high_byte = ram_64KB[(zp_addr + 1) & 0xFF]

        base_addr = (high_byte << 8) | low_byte
        addr = (base_addr + y) & 0xFFFF

        ac = ram_64KB[addr]

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 5



    elif opcode == 0xA2: #LDX Immediate
        x = operand_lower

        sr = zero_flag(x, sr)

        sr = negative_flag(x, sr)

        pc += 2
        cycle_count += 2

    elif opcode == 0xA6: #LDX Zero Page
        x = ram_64KB[operand_lower]

        sr = zero_flag(x, sr)

        sr = negative_flag(x, sr)

        pc += 2
        cycle_count += 3

    elif opcode == 0xB6: #LDX Zero Page, Y
        addr = (operand_lower + y) & 0xFF
        x = ram_64KB[addr]

        sr = zero_flag(x, sr)

        sr = negative_flag(x, sr)

        pc += 2
        cycle_count += 4

    elif opcode == 0xAE: #LDX Absolute
        addr = (operand_higher << 8) | operand_lower
        x = ram_64KB[addr]

        sr = zero_flag(x, sr)

        sr = negative_flag(x, sr)

        pc += 3
        cycle_count += 4

    elif opcode == 0xBE: #LDX Absolute, Y
        base = (operand_higher << 8) | operand_lower
        addr = (base + y) & 0xFFFF
        x = ram_64KB[addr]

        sr = zero_flag(x, sr)

        sr = negative_flag(x, sr)

        pc += 3
        cycle_count += 4



    elif opcode == 0xA0: #LDY Immediate
        y = operand_lower

        sr = zero_flag(y, sr)

        sr = negative_flag(y, sr)

        pc += 2
        cycle_count += 2

    elif opcode == 0xA4: #LDY Zero Page
        y = ram_64KB[operand_lower]

        sr = zero_flag(y, sr)

        sr = negative_flag(y, sr)

        pc += 2
        cycle_count += 3

    elif opcode == 0xB4: #LDY Zero Page, X
        addr = (operand_lower + x) & 0xFF
        y = ram_64KB[addr]

        sr = zero_flag(y, sr)

        sr = negative_flag(y, sr)

        pc += 2
        cycle_count += 4

    elif opcode == 0xAC: #LDY Absolute
        addr = (operand_higher << 8) | operand_lower
        y = ram_64KB[addr]

        sr = zero_flag(y, sr)

        sr = negative_flag(y, sr)

        pc += 3
        cycle_count += 4

    elif opcode == 0xBC: #LDY Absolute, X
        base = (operand_higher << 8) | operand_lower
        addr = (base + x) & 0xFFFF
        y = ram_64KB[addr]

        sr = zero_flag(y, sr)

        sr = negative_flag(y, sr)

        pc += 3
        cycle_count += 4



    elif opcode == 0x4A: #LSR Accumulator
        #Carry Flag (C)
        if ac & 0x01:
            sr |= 0x01
        else:
            sr &= ~0x01

        ac = (ac >> 1) & 0xFF

        sr = zero_flag(ac, sr)
        sr &= ~0x80
        
        pc += 1
        cycle_count += 2

    elif opcode == 0x46: #LSR Zero Page

        value = ram_64KB[operand_lower]

        #Carry Flag (C)
        if value & 0x01:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = (value >> 1) & 0xFF
        ram_64KB[value] = value

        sr = zero_flag(ac, sr)
        sr &= ~0x80
        
        pc += 2
        cycle_count += 5

    elif opcode == 0x56: #LSR Zero Page, X

        value = (operand_lower + x) & 0xFF

        #Carry Flag (C)
        if value & 0x01:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = (value >> 1) & 0xFF
        ram_64KB[addr] = value

        sr = zero_flag(ac, sr)
        sr &= ~0x80
        
        pc += 2
        cycle_count += 6

    elif opcode == 0x4E: #LSR Absolute

        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]

        # Carry Flag (C)
        if value & 0x01:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = (value >> 1) & 0xFF
        ram_64KB[addr] = value

        sr = zero_flag(value, sr)
        sr = negative_flag(value, sr)  # LSR always clears N flag, optional to keep
        sr &= ~0x80

        pc += 3
        cycle_count += 6

    elif opcode == 0x5E: #LSR Absolute, X

        base = (operand_higher << 8) | operand_lower
        value = (base + x) & 0xFFFF

        #Carry Flag (C)
        if value & 0x01:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = (value >> 1) & 0xFF
        ram_64KB[value]

        sr = zero_flag(ac, sr)
        sr &= ~0x80
        
        pc += 3
        cycle_count += 7



    elif opcode == 0xEA: #NOP Implied
        pc += 1
        cycle_count += 2



    elif opcode == 0x09: #ORA Immediate

        ac = (ac | operand_lower) & 0xFF

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 2

    elif opcode == 0x05: #ORA Zero Page
        
        value = ram_64KB[operand_lower]
        ac = (ac | value) & 0xFF

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 3

    elif opcode == 0x15: #ORA Zero Page, X
        
        addr = (operand_lower + x) & 0xFF
        value = ram_64KB[addr]
        ac = (ac | value) & 0xFF

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 4

    elif opcode == 0x0D: #ORA Absolute
        
        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]
        ac = (ac | value) & 0xFF

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 3
        cycle_count += 4

    elif opcode == 0x1D: #ORA Absolute, X
        
        base = (operand_higher << 8) | operand_lower
        addr = (base + x) & 0xFFFF
        value = ram_64KB[addr]
        ac = (ac | value) & 0xFF

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 3
        cycle_count += 4

    elif opcode == 0x19: #ORA Absolute, Y
        
        base = (operand_higher << 8) | operand_lower
        addr = (base + y) & 0xFFFF
        value = ram_64KB[addr]
        ac = (ac | value) & 0xFF

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 3
        cycle_count += 4

    elif opcode == 0x01: #ORA Indirect, X
        
        zp = (operand_lower + x) & 0xFF

        low = ram_64KB[zp]
        high = ram_64KB[(zp + 1) & 0xFF]

        addr = (high << 8) | low
        value = ram_64KB[addr]
        ac = (ac | value) & 0xFF

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 6

    elif opcode == 0x11: #ORA Indirect, Y
        
        zp = operand_lower

        low = ram_64KB[zp]
        high = ram_64KB[(zp + 1) & 0xFF]

        base = (high << 8) | low
        addr = (base + y) & 0xFFFF
        value = ram_64KB[addr]
        ac = (ac | value) & 0xFF

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 2
        cycle_count += 5



#Register Instructions

    elif opcode == 0xAA: #TAX (Transfer A to X)
        x = ac

        sr = zero_flag(x, sr)
        sr = negative_flag(x, sr)

        pc += 1
        cycle_count += 2

    elif opcode == 0x8A: #TXA (Transfer X to A)
        ac = x

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 1
        cycle_count += 2
    
    elif opcode == 0xCA: #DEX (Decrement X)
        x = (x - 1) & 0xFF

        sr = zero_flag(x, sr)
        sr = negative_flag(x, sr)

        pc += 1
        cycle_count += 2

    elif opcode == 0xE8: #INX (Increment X)
        x = (x + 1) & 0xFF

        sr = zero_flag(x, sr)
        sr = negative_flag(x, sr)

        pc += 1
        cycle_count += 2

    elif opcode == 0xA8: #TAY (Transfer A to Y)
        y = ac

        sr = zero_flag(y, sr)
        sr = negative_flag(y, sr)

        pc += 1
        cycle_count += 2

    elif opcode == 0x98: #TYA (Transfer Y to A)
        ac = y

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 1
        cycle_count += 2

    elif opcode == 0x88: #DEY (Decrement Y)
        y = (y - 1) & 0xFF

        sr = zero_flag(y, sr)
        sr = negative_flag(y, sr)

        pc += 1
        cycle_count += 2

    elif opcode == 0xC8: #INY (Increment Y)
        y = (y + 1) & 0xFF

        sr = zero_flag(y, sr)
        sr = negative_flag(y, sr)

        pc += 1
        cycle_count += 2



    elif opcode == 0x2A: #ROL Accumulator
        old_c = sr & 0x01

        # New carry from bit 7
        if ac & 0x80:
            sr |= 0x01
        else:
            sr &= ~0x01

        ac = ((ac << 1) | old_c) & 0xFF

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 1
        cycle_count += 2

    elif opcode == 0x26: #ROL Zero Page

        addr = operand_lower
        value = ram_64KB[addr]


        old_c = sr & 0x01

        # New carry from bit 7
        if value & 0x80:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = ((value << 1) | old_c) & 0xFF

        ram_64KB[addr] = value

        sr = zero_flag(value, sr)
        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 5

    elif opcode == 0x36: #ROL Zero Page, X

        addr = (operand_lower + x) & 0xFF
        value = ram_64KB[addr]


        old_c = sr & 0x01

        # New carry from bit 7
        if value & 0x80:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = ((value << 1) | old_c) & 0xFF

        ram_64KB[addr] = value

        sr = zero_flag(value, sr)
        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 6

    elif opcode == 0x2E: #ROL Absolute

        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]


        old_c = sr & 0x01

        # New carry from bit 7
        if value & 0x80:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = ((value << 1) | old_c) & 0xFF

        ram_64KB[addr] = value

        sr = zero_flag(value, sr)
        sr = negative_flag(value, sr)

        pc += 3
        cycle_count += 6

    elif opcode == 0x3E: #ROL Absolute, X

        base = (operand_higher << 8) | operand_lower
        addr = (base + x) & 0xFFFF
        value = ram_64KB[addr]


        old_c = sr & 0x01

        # New carry from bit 7
        if value & 0x80:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = ((value << 1) | old_c) & 0xFF

        ram_64KB[addr] = value

        sr = zero_flag(value, sr)
        sr = negative_flag(value, sr)

        pc += 3
        cycle_count += 7



    elif opcode == 0x6A: #ROR Accumulator
        old_c = sr & 0x01

        # New carry from bit 0
        if ac & 0x01:
            sr |= 0x01
        else:
            sr &= ~0x01

        ac = ((ac >> 1) | (old_c << 7)) & 0xFF

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 1
        cycle_count += 2

    elif opcode == 0x66: #ROR Zero Page

        addr = operand_lower
        value = ram_64KB[addr]


        old_c = sr & 0x01

        # New carry from bit 0
        if value & 0x01:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = ((value >> 1) | (old_c << 7)) & 0xFF

        ram_64KB[addr] = value

        sr = zero_flag(value, sr)
        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 5

    elif opcode == 0x76: #ROR Zero Page, X

        addr = (operand_lower + x) & 0xFF
        value = ram_64KB[addr]


        old_c = sr & 0x01

        # New carry from bit 0
        if value & 0x01:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = ((value >> 1) | (old_c << 7)) & 0xFF

        ram_64KB[addr] = value

        sr = zero_flag(value, sr)
        sr = negative_flag(value, sr)

        pc += 2
        cycle_count += 6

    elif opcode == 0x6E: #ROR Absolute

        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]


        old_c = sr & 0x01

        # New carry from bit 0
        if value & 0x01:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = ((value >> 1) | (old_c << 7)) & 0xFF

        ram_64KB[addr] = value

        sr = zero_flag(value, sr)
        sr = negative_flag(value, sr)

        pc += 3
        cycle_count += 6

    elif opcode == 0x7E: #ROR Absolute, X

        base = (operand_higher << 8) | operand_lower
        addr = (base + x) & 0xFFFF
        value = ram_64KB[addr]


        old_c = sr & 0x01

        # New carry from bit 0
        if value & 0x01:
            sr |= 0x01
        else:
            sr &= ~0x01

        value = ((value >> 1) | (old_c << 7)) & 0xFF

        ram_64KB[addr] = value

        sr = zero_flag(value, sr)
        sr = negative_flag(value, sr)

        pc += 3
        cycle_count += 7



    elif opcode == 0x40:  #RTI Implied
                # pull SR
        sp = (sp + 1) & 0xFF
        sr = ram_64KB[0x0100 + sp]
        sr &= ~0b00010000
        sr |=  0b00100000

        # pull PC low
        sp = (sp + 1) & 0xFF
        pcl = ram_64KB[0x0100 + sp]

        # pull PC high
        sp = (sp + 1) & 0xFF
        pch = ram_64KB[0x0100 + sp]

        pc = (pch << 8) | pcl
        cycle_count += 6



    elif opcode == 0x60: #RTS Implied
        sp = (sp + 1) & 0xFF
        low = ram_64KB[0x0100 + sp]

        sp = (sp + 1) & 0xFF
        high = ram_64KB[0x0100 + sp]

        pc = ((high << 8) | low) + 1
        cycle_count += 6



    elif opcode == 0xE9: #SBC Immediate

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        
        result = ac - operand_lower - (1 - cin)

        

        #Carry Flag (C)
        if result >= 0:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ operand_lower) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 2
        cycle_count += 2

    elif opcode == 0xE5: #SBC Zero Page

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        value = ram_64KB[operand_lower]
        result = ac - value - (1 - cin)

        #Carry Flag (C)
        if result >= 0:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 2
        cycle_count += 3
    
    elif opcode == 0xF5: #SBC Zero Page, X

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        addr = (operand_lower + x) & 0xFF
        value = ram_64KB[addr]
        result = ac - value - (1 - cin)

        #Carry Flag (C)
        if result >= 0:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 2
        cycle_count += 4

    elif opcode == 0xED: #SBC Absolute

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        addr = (operand_higher << 8) | operand_lower
        value = ram_64KB[addr]
        result = ac - value - (1 - cin)

        #Carry Flag (C)
        if result >= 0:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 3
        cycle_count += 4

    elif opcode == 0xFD: #SBC Absolute, X

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        base = (operand_higher << 8) | operand_lower
        addr = (base + x) & 0xFFFF
        value = ram_64KB[addr]

        result = ac - value - (1 - cin)

        #Carry Flag (C)
        if result >= 0:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 3
        cycle_count += 4

    elif opcode == 0xF9: #SBC Absolute, Y

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        base = (operand_higher << 8) | operand_lower
        addr = (base + y) & 0xFFFF
        value = ram_64KB[addr]
        
        result = ac - value - (1 - cin)

        #Carry Flag (C)
        if result >= 0:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 3
        cycle_count += 4

    elif opcode == 0xE1: #SBC Indirect, X

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        zp = (operand_lower + x) & 0xFF

        low = ram_64KB[zp]
        high = ram_64KB[(zp + 1) & 0xFF]

        addr = (high << 8) | low
        value = ram_64KB[addr]
        
        result = ac - value - (1 - cin)

        #Carry Flag (C)
        if result >= 0:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 2
        cycle_count += 6

    elif opcode == 0xF1: #SBC Indirect, Y

        old_ac = ac

        if sr & 0x01:
            cin = 1
        else:
            cin = 0

        zp = operand_lower

        low = ram_64KB[zp]
        high = ram_64KB[(zp + 1) & 0xFF]

        base = (high << 8) | low
        addr = (base + y) & 0xFFFF
        value = ram_64KB[addr]
        
        result = ac - value - (1 - cin)

        #Carry Flag (C)
        if result >= 0:
            sr |= 0x01
        else:
            sr &= ~0x01
        ac = result & 0xFF

        sr = zero_flag(ac, sr)

        sr = negative_flag(ac, sr)

        #Overflow Flag (V)
        if (~(old_ac ^ value) & (old_ac ^ ac) & 0x80) != 0:
            sr |= 0x40
        else:
            sr &= ~0x40

        pc += 2
        cycle_count += 5



    elif opcode == 0x85: #STA Zero Page
        ram_64KB[operand_lower] = ac

        pc += 2
        cycle_count += 3

    elif opcode == 0x95: #STA Zero Page, X
        ram_64KB[(operand_lower + x) & 0xFF] = ac

        pc += 2
        cycle_count += 4

    elif opcode == 0x8D: #STA Absolute
        ram_64KB[(operand_higher << 8) | operand_lower] = ac

        pc += 3
        cycle_count += 4
    
    elif opcode == 0x9D: #STA Absolute, X
        addr = ((operand_higher << 8) | operand_lower) + x
        ram_64KB[addr & 0xFFFF] = ac

        pc += 3
        cycle_count += 5

    elif opcode == 0x99: #STA Absolute, Y
        addr = ((operand_higher << 8) | operand_lower) + y
        ram_64KB[addr & 0xFFFF] = ac

        pc += 3
        cycle_count += 5
    
    elif opcode == 0x81: #STA Indirect, X

        zp_addr = (operand_lower + x) & 0xFF

        low_byte = ram_64KB[zp_addr]
        high_byte = ram_64KB[(zp_addr + 1) & 0xFF]

        base_addr = (high_byte << 8) | low_byte

        target_addr = base_addr

        ram_64KB[target_addr] = ac


        pc += 2
        cycle_count += 6

    elif opcode == 0x91: #STA Indirect, Y
        zp_addr = operand_lower

        low_byte = ram_64KB[zp_addr]
        high_byte = ram_64KB[(zp_addr + 1) & 0xFF]

        base_addr = (high_byte << 8) | low_byte

        target_addr = (base_addr + y) & 0xFFFF

        ram_64KB[target_addr] = ac


        pc += 2
        cycle_count += 6



#Stack Instructions

    elif opcode == 0x9A: #TXS (Transfer X to Stack ptr)
        sp = x
        pc += 1
        cycle_count += 2

    elif opcode == 0xBA: #TSX (Transfer Stack ptr to X)
        x = sp

        sr = zero_flag(x, sr)
        sr = negative_flag(x, sr)

        pc += 1
        cycle_count += 2

    elif opcode == 0x48: #PHA (Push Accumulator)
        ram_64KB[0x100 + sp] = ac
        sp = (sp - 1) & 0xFF
        pc += 1
        cycle_count += 3

    elif opcode == 0x68: #PLA (Pull Accumulator)
        sp = (sp + 1) & 0xFF
        ac = ram_64KB[0x100 + sp]

        sr = zero_flag(ac, sr)
        sr = negative_flag(ac, sr)

        pc += 1
        cycle_count += 4

    elif opcode == 0x08: #PHP (Push Processor Status)
        ram_64KB[0x100 + sp] = sr
        sp = (sp - 1) & 0xFF
        pc += 1
        cycle_count += 3

    elif opcode == 0x28: #PLP (Pull Processor Status)
        sp = (sp + 1) & 0xFF
        sr = ram_64KB[0x100 + sp]
        pc += 1
        cycle_count += 4




    elif opcode == 0x86: #STX Zero Page
        ram_64KB[operand_lower] = x

        pc += 2
        cycle_count += 3

    elif opcode == 0x96: #STX Zero Page, Y
        ram_64KB[(operand_lower + y) & 0xFF] = x

        pc += 2
        cycle_count += 4
        
    elif opcode == 0x8E: #STX Absolute
        addr = (operand_higher << 8) | operand_lower
        ram_64KB[addr] = x

        pc += 3
        cycle_count += 4



    elif opcode == 0x84: #STY Zero Page
        ram_64KB[operand_lower] = y

        pc += 2
        cycle_count += 3

    elif opcode == 0x94: #STY Zero Page, X
        ram_64KB[(operand_lower + x) & 0xFF] = y

        pc += 2
        cycle_count += 4
        
    elif opcode == 0x8C: #STY Absolute
        addr = (operand_higher << 8) | operand_lower
        ram_64KB[addr] = y

        pc += 3
        cycle_count += 4




#Illegal Opcodes

    elif opcode == 0x04: #DOP Zero Page
        pc += 1

    elif opcode == 0x14: #DOP Zero Page, X
        pc += 1

    elif opcode == 0x34: #DOP Zero Page, X
        pc += 1

    elif opcode == 0x44: #DOP Zero Page
        pc += 1

    elif opcode == 0x54: #DOP Zero Page, X
        pc += 1

    elif opcode == 0x64: #DOP Zero Page
        pc += 1

    elif opcode == 0x74: #DOP Zero Page, X
        pc += 1

    elif opcode == 0x80: #DOP Immediate
        pc += 1

    elif opcode == 0x82: #DOP Immediate
        pc += 1

    elif opcode == 0x89: #DOP Immediate
        pc += 1

    elif opcode == 0xC2: #DOP Immediate
        pc += 1

    elif opcode == 0xD4: #DOP Zero Page, X
        pc += 1

    elif opcode == 0xE2: #DOP Immediate
        pc += 1

    elif opcode == 0xF4: #DOP Zero Page, X
        pc += 1



    else:

        printerror = False

        if printerror == True:
            print(f"\nUnknown opcode {opcode:02X} at PC {pc:04X}\n")
        halt = False
        pc += 1

    return pc, ac, x, y, sr, sp, halt, cycle_count





if custom6502 == True:
    while (pc + 3) != 65536:
        pc, ac, x, y, sr, sp, halt, cycle_count = perform_opcode(pc, ram_64KB[pc], ram_64KB[pc+1], ram_64KB[pc+2], ac, x, y, sr, sp, cycle_count)
        if halt == True:
            break

if apple_i == True:

    shiftspace = array('B', [0] * 1024)
    def writeshiftreg1024B(byte, shiftspace, writep):
        if writep < 1024:
            shiftspace[writep] = byte
            writep += 1
        else:
            writep = 0

        return writep, shiftspace

    def readshiftreg1024B(shiftspace, readp):
        if readp < 1024:
            value111 = shiftspace[readp]
            readp += 1
        else:
            readp = 0
            value111 = shiftspace[readp]
    

        return readp, value111

    def shiftdisplay():
        clear = array('B', [0] * 40)

        shiftspace[0:40] = shiftspace[40:80]                              # Row1  <- Row2
        shiftspace[40:80] = shiftspace[80:120]                            # Row2  <- Row3
        shiftspace[80:120] = shiftspace[120:160]                          # Row3  <- Row4
        shiftspace[120:160] = shiftspace[160:200]                         # Row4  <- Row5
        shiftspace[160:200] = shiftspace[200:240]                         # Row5  <- Row6
        shiftspace[200:240] = shiftspace[240:280]                         # Row6  <- Row7
        shiftspace[240:280] = shiftspace[280:320]                         # Row7  <- Row8
        shiftspace[280:320] = shiftspace[320:360]                         # Row8  <- Row9
        shiftspace[320:360] = shiftspace[360:400]                         # Row9  <- Row10
        shiftspace[360:400] = shiftspace[400:440]                         # Row10 <- Row11
        shiftspace[400:440] = shiftspace[440:480]                         # Row11 <- Row12
        shiftspace[440:480] = shiftspace[480:520]                         # Row12 <- Row13
        shiftspace[480:520] = shiftspace[520:560]                         # Row13 <- Row14
        shiftspace[520:560] = shiftspace[560:600]                         # Row14 <- Row15
        shiftspace[560:600] = shiftspace[600:640]                         # Row15 <- Row16
        shiftspace[600:640] = shiftspace[640:680]                         # Row16 <- Row17
        shiftspace[640:680] = shiftspace[680:720]                         # Row17 <- Row18
        shiftspace[680:720] = shiftspace[720:760]                         # Row18 <- Row19
        shiftspace[720:760] = shiftspace[760:800]                         # Row19 <- Row20
        shiftspace[760:800] = shiftspace[800:840]                         # Row20 <- Row21
        shiftspace[800:840] = shiftspace[840:880]                         # Row21 <- Row22
        shiftspace[840:880] = shiftspace[880:920]                         # Row22 <- Row23
        shiftspace[880:920] = shiftspace[920:960]                         # Row23 <- Row24
        shiftspace[920:960] = clear[0:40]    # Row24 <- Clear



    #Apple I Shift REG Pointers
    readpointer = 0
    writepointer = 0


    #Keyboard
    key_repeat_counter = 0
    key_repeat = 6

    wait1 = 0
    wait2 = 0


    #Display
    cursor_xpos = 0
    cursor_ypos = 0

    xpos = 0x00
    ypos = 0x00

    #Window Scale Value
    scalevar = 5


    apple1_width = 280
    apple1_height = 192

    if not glfw.init():
        raise Exception("GLFW can't be initialized")

    # Request legacy context
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_ANY_PROFILE)

    glfw.window_hint(glfw.RESIZABLE, glfw.FALSE)

    window = glfw.create_window((apple1_width * scalevar), (apple1_height * scalevar), "Apple I  -  Ellie's Ems", None, None)
    if not window:
        glfw.terminate()
        raise Exception("GLFW window can't be created")
    




    #Set Icon
    img_path = Path(__file__).parent / "Assets" / "Apple_1_Icon-64x64.png"
    img = Image.open(img_path).convert("RGBA")
    width, height = img.size
    pixels = np.array(img, dtype=np.uint8)

    glfw.set_window_icon(window, 1, [(width, height, pixels)])





    glfw.make_context_current(window)
    glfw.swap_interval(1)  # vsync

    glClearColor(0.0, 0.0, 0.0, 1.0)

    # Create texture
    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, apple1_width, apple1_height, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glEnable(GL_TEXTURE_2D)

    framebuffer = np.zeros((apple1_height, apple1_width, 3), dtype=np.uint8)
    framebuffer = np.ascontiguousarray(framebuffer)


    def update_texture():
        i1 = 0

        while i1 != 960:
            character = shiftspace[i1]

            x1 = i1 % 40

            y1 = i1 // 40

            if character == 0x40: # '@'
                rasterize_char(x1, y1, framebuffer, 0)
            
            elif character == 0x41: # 'A'
                rasterize_char(x1, y1, framebuffer, 1)

            elif character == 0x42: # 'B'
                rasterize_char(x1, y1, framebuffer, 2)
            
            elif character == 0x43: # 'C'
                rasterize_char(x1, y1, framebuffer, 3)

            elif character == 0x44: # 'D'
                rasterize_char(x1, y1, framebuffer, 4)

            elif character == 0x45: # 'E'
                rasterize_char(x1, y1, framebuffer, 5)

            elif character == 0x46: # 'F'
                rasterize_char(x1, y1, framebuffer, 6)

            elif character == 0x47: # 'G'
                rasterize_char(x1, y1, framebuffer, 7)

            elif character == 0x48: # 'H'
                rasterize_char(x1, y1, framebuffer, 8)

            elif character == 0x49: # 'I'
                rasterize_char(x1, y1, framebuffer, 9)

            elif character == 0x4A: # 'J'
                rasterize_char(x1, y1, framebuffer, 10)

            elif character == 0x4B: # 'K'
                rasterize_char(x1, y1, framebuffer, 11)

            elif character == 0x4C: # 'L'
                rasterize_char(x1, y1, framebuffer, 12)

            elif character == 0x4D: # 'M'
                rasterize_char(x1, y1, framebuffer, 13)

            elif character == 0x4E: # 'N'
                rasterize_char(x1, y1, framebuffer, 14)

            elif character == 0x4F: # 'O'
                rasterize_char(x1, y1, framebuffer, 15)

            elif character == 0x50: # 'P'
                rasterize_char(x1, y1, framebuffer, 16)

            elif character == 0x51: # 'Q'
                rasterize_char(x1, y1, framebuffer, 17)

            elif character == 0x52: # 'R'
                rasterize_char(x1, y1, framebuffer, 18)

            elif character == 0x53: # 'S'
                rasterize_char(x1, y1, framebuffer, 19)

            elif character == 0x54: # 'T'
                rasterize_char(x1, y1, framebuffer, 20)

            elif character == 0x55: # 'U'
                rasterize_char(x1, y1, framebuffer, 21)

            elif character == 0x56: # 'V'
                rasterize_char(x1, y1, framebuffer, 22)

            elif character == 0x57: # 'W'
                rasterize_char(x1, y1, framebuffer, 23)

            elif character == 0x58: # 'X'
                rasterize_char(x1, y1, framebuffer, 24)

            elif character == 0x59: # 'Y'
                rasterize_char(x1, y1, framebuffer, 25)

            elif character == 0x5A: # 'Z'
                rasterize_char(x1, y1, framebuffer, 26)

            elif character == 0x5B: # '['
                rasterize_char(x1, y1, framebuffer, 27)

            elif character == 0x5C: # '\'
                rasterize_char(x1, y1, framebuffer, 28)

            elif character == 0x5D: # ']'
                rasterize_char(x1, y1, framebuffer, 29)

            elif character == 0x5E: # '^'
                rasterize_char(x1, y1, framebuffer, 30)

            elif character == 0x5F: # '_'
                rasterize_char(x1, y1, framebuffer, 31)

            elif character == 0x00: # ' '
                rasterize_char(x1, y1, framebuffer, 32)
            elif character == 0x20: # ' '
                rasterize_char(x1, y1, framebuffer, 32)

            elif character == 0x21: # '!'
                rasterize_char(x1, y1, framebuffer, 33)

            elif character == 0x22: # '"'
                rasterize_char(x1, y1, framebuffer, 34)

            elif character == 0x23: # '#'
                rasterize_char(x1, y1, framebuffer, 35)

            elif character == 0x24: # '$'
                rasterize_char(x1, y1, framebuffer, 36)

            elif character == 0x25: # '%'
                rasterize_char(x1, y1, framebuffer, 37)

            elif character == 0x26: # '&'
                rasterize_char(x1, y1, framebuffer, 38)
            
            elif character == 0x27: # '''
                rasterize_char(x1, y1, framebuffer, 39)

            elif character == 0x28: # '('
                rasterize_char(x1, y1, framebuffer, 40)

            elif character == 0x29: # ')'
                rasterize_char(x1, y1, framebuffer, 41)

            elif character == 0x2A: # '*'
                rasterize_char(x1, y1, framebuffer, 42)

            elif character == 0x2B: # '+'
                rasterize_char(x1, y1, framebuffer, 43)

            elif character == 0x2C: # ','
                rasterize_char(x1, y1, framebuffer, 44)

            elif character == 0x2D: # '-'
                rasterize_char(x1, y1, framebuffer, 45)

            elif character == 0x2E: # '.'
                rasterize_char(x1, y1, framebuffer, 46)

            elif character == 0x2F: # '/'
                rasterize_char(x1, y1, framebuffer, 47)

            elif character == 0x30: # '0'
                rasterize_char(x1, y1, framebuffer, 48)
            
            elif character == 0x31: # '1'
                rasterize_char(x1, y1, framebuffer, 49)

            elif character == 0x32: # '2'
                rasterize_char(x1, y1, framebuffer, 50)

            elif character == 0x33: # '3'
                rasterize_char(x1, y1, framebuffer, 51)

            elif character == 0x34: # '4'
                rasterize_char(x1, y1, framebuffer, 52)

            elif character == 0x35: # '5'
                rasterize_char(x1, y1, framebuffer, 53)

            elif character == 0x36: # '6'
                rasterize_char(x1, y1, framebuffer, 54)

            elif character == 0x37: # '7'
                rasterize_char(x1, y1, framebuffer, 55)

            elif character == 0x38: # '8'
                rasterize_char(x1, y1, framebuffer, 56)

            elif character == 0x39: # '9'
                rasterize_char(x1, y1, framebuffer, 57)

            elif character == 0x3A: # ':'
                rasterize_char(x1, y1, framebuffer, 58)

            elif character == 0x3B: # ';'
                rasterize_char(x1, y1, framebuffer, 59)

            elif character == 0x3C: # '<'
                rasterize_char(x1, y1, framebuffer, 60)

            elif character == 0x3D: # '='
                rasterize_char(x1, y1, framebuffer, 61)

            elif character == 0x3E: # '>'
                rasterize_char(x1, y1, framebuffer, 62)

            elif character == 0x3F: # '?'
                rasterize_char(x1, y1, framebuffer, 63)

            else:
                rasterize_char(x1, y1, framebuffer, 32)

            i1 += 1
        
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0,
                        apple1_width, apple1_height,
                        GL_RGB, GL_UNSIGNED_BYTE,
                        np.ascontiguousarray(framebuffer))


    def rasterize_char(xposition, yposition, framebuffer, character):
        xpos = (xposition * 7)
        ypos = apple1_height - ((yposition * 8) + 1)

        if character == 0: #Character : '@' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 1: #Character : 'A' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]
        
        elif character == 2: #Character : 'B' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 3: #Character : 'C' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 4: #Character : 'D' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 5: #Character : 'E' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 6: #Character : 'F' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 7: #Character : 'G' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 8: #Character : 'H' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 9: #Character : 'I' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 10: #Character : 'J' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 11: #Character : 'K' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 12: #Character : 'L' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 13: #Character : 'M' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 14: #Character : 'N' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 15: #Character : 'O' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 16: #Character : 'P' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 17: #Character : 'Q' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 18: #Character : 'R' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 19: #Character : 'S' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 20: #Character : 'T' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 21: #Character : 'U' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 22: #Character : 'V' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 23: #Character : 'W' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 24: #Character : 'X' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 25: #Character : 'Y' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 26: #Character : 'Z' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 27: #Character : '[' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 28: #Character : '\' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 29: #Character : ']' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 30: #Character : '^' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 31: #Character : '_' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 32: #Character : ' ' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 33: #Character : '!' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 34: #Character : '"' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 35: #Character : '#' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 36: #Character : '$' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 37: #Character : '%' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 38: #Character : '&' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 39: #Character : ''' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 40: #Character : '(' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 41: #Character : ')' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 42: #Character : '*' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 43: #Character : '+' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 44: #Character : ',' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 45: #Character : '-' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 46: #Character : '.' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 47: #Character : '/' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 48: #Character : '0' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 49: #Character : '1' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 50: #Character : '2' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 51: #Character : '3' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 52: #Character : '4' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 53: #Character : '5' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 54: #Character : '6' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 55: #Character : '7' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 56: #Character : '8' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 57: #Character : '9' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 58: #Character : ':' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 59: #Character : ';' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 60: #Character : '<' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 61: #Character : '=' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 62: #Character : '>' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

        elif character == 63: #Character : '?' DONE
            framebuffer[ypos - 0, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 0, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 1, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 2] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 1, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 1, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 2, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 1] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 2, xpos + 5] = [255 ,255 ,255]
            framebuffer[ypos - 2, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 3, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 4] = [255 ,255 ,255]
            framebuffer[ypos - 3, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 3, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 4, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 4, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 4, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 5, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 5, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 5, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 6, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 3] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 6, xpos + 6] = [0 ,0 ,0]

            framebuffer[ypos - 7, xpos + 0] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 1] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 2] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 3] = [255 ,255 ,255]
            framebuffer[ypos - 7, xpos + 4] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 5] = [0 ,0 ,0]
            framebuffer[ypos - 7, xpos + 6] = [0 ,0 ,0]

    def key_input():
        if (ram_64KB[0xD011] & 0x80) == 0:
                if glfw.get_key(window, glfw.KEY_ENTER) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0x8D
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xA0
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_1) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xA1
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_APOSTROPHE) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xA2
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_3) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xA3
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_4) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xA4
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_5) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xA5
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_7) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xA6
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_APOSTROPHE) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xA7
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_9) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xA8
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_0) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xA9
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_8) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xAA
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_EQUAL) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xAB
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_COMMA) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xAC
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_MINUS) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xAD
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_PERIOD) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xAE
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_SLASH) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xAF
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_0) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xB0
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_1) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xB1
                    ram_64KB[0xD011] = 0x80
                    
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_2) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xB2
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_3) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xB3
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_4) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xB4
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_5) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xB5
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_6) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xB6
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_7) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xB7
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_8) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xB8
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_9) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xB9
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_SEMICOLON) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xBA
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_SEMICOLON) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xBB
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_COMMA) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xBC
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_EQUAL) == glfw.PRESS and not (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xBD
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_PERIOD) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xBE
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_SLASH) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xBF
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_2) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xC0
                    ram_64KB[0xD011] = 0x80

                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xC1
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_B) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xC2
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_C) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xC3
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xC4
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_E) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xC5
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_F) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xC6
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_G) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xC7
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_H) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xC8
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_I) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xC9
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_J) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xCA
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_K) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xCB
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_L) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xCC
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_M) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xCD
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_N) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xCE
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_O) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xCF
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_P) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xD0
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_Q) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xD1
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_R) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xD2
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xD3
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_T) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xD4
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_U) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xD5
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_V) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xD6
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xD7
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_X) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xD8
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_Y) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xD9
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_Z) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xDA
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_LEFT_BRACKET) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xDB
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_BACKSLASH) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xDC
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_RIGHT_BRACKET) == glfw.PRESS:
                    ram_64KB[0xD010] = 0xDD
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_6) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xDE
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                if glfw.get_key(window, glfw.KEY_MINUS) == glfw.PRESS and (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS):
                    ram_64KB[0xD010] = 0xDF
                    ram_64KB[0xD011] = 0x80

                if glfw.get_key(window, glfw.KEY_BACKSPACE) == glfw.PRESS:
                    ram_64KB[0xD010] = 0x7F
                    ram_64KB[0xD011] = 0x80
                        
                    key_repeat_counter = key_repeat  # reset counter
                
                
        
        



    start = time.perf_counter()
    while not glfw.window_should_close(window):
        glfw.poll_events()
        glClear(GL_COLOR_BUFFER_BIT)

        

        # Draw quad
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(-1, -1)
        glTexCoord2f(1, 0); glVertex2f(1, -1)
        glTexCoord2f(1, 1); glVertex2f(1, 1)
        glTexCoord2f(0, 1); glVertex2f(-1, 1)
        glEnd()


        glfw.swap_buffers(window)

        
        if key_repeat_counter <= 0:
            key_input()
            key_repeat_counter = key_repeat
        key_repeat_counter -= 1

        if ram_64KB[pc - 1] == 0xD0 and ram_64KB[pc - 2] == 0x12:
            ram_64KB[0xD012] |= 0x80

        while wait2 != 500:
            
            pc, ac, x, y, sr, sp, halt, cycle_count = perform_opcode(pc, ram_64KB[pc], ram_64KB[pc+1], ram_64KB[pc+2], ac, x, y, sr, sp, cycle_count)
     
            if ram_64KB[0xD012] & 0x80:    
                
                writepointer, shiftspace = writeshiftreg1024B((ram_64KB[0xD012] & 0x7F), shiftspace, writepointer) #Write to shift reg
                
                    
                        
                        
                ram_64KB[0xD012] &= 0x7F

                if ram_64KB[0xD012] == 0x0D:
                            if cursor_ypos == 0:
                                writepointer = 40
                            elif cursor_ypos == 1:
                                writepointer = 80
                            elif cursor_ypos == 2:
                                writepointer = 120
                            elif cursor_ypos == 3:
                                writepointer = 160
                            elif cursor_ypos == 4:
                                writepointer = 200
                            elif cursor_ypos == 5:
                                writepointer = 240
                            elif cursor_ypos == 6:
                                writepointer = 280
                            elif cursor_ypos == 7:
                                writepointer = 320
                            elif cursor_ypos == 8:
                                writepointer = 360
                            elif cursor_ypos == 9:
                                writepointer = 400
                            elif cursor_ypos == 10:
                                writepointer = 440
                            elif cursor_ypos == 11:
                                writepointer = 480
                            elif cursor_ypos == 12:
                                writepointer = 520
                            elif cursor_ypos == 13:
                                writepointer = 560
                            elif cursor_ypos == 14:
                                writepointer = 600
                            elif cursor_ypos == 15:
                                writepointer = 640
                            elif cursor_ypos == 16:
                                writepointer = 680
                            elif cursor_ypos == 17:
                                writepointer = 720
                            elif cursor_ypos == 18:
                                writepointer = 760
                            elif cursor_ypos == 19:
                                writepointer = 800
                            elif cursor_ypos == 20:
                                writepointer = 840
                            elif cursor_ypos == 21:
                                writepointer = 880
                            elif cursor_ypos == 22:
                                writepointer = 920
                            elif cursor_ypos == 23:
                                writepointer = 920
                                shiftdisplay()

                cursor_xpos += 1
                if cursor_xpos >= 40:
                        cursor_xpos = 0

                if writepointer == 40:
                        cursor_ypos = 1
                elif writepointer == 80:
                        cursor_ypos = 2
                elif writepointer == 120:
                        cursor_ypos = 3
                elif writepointer == 160:
                        cursor_ypos = 4
                elif writepointer == 200:
                        cursor_ypos = 5
                elif writepointer == 240:
                        cursor_ypos = 6
                elif writepointer == 280:
                        cursor_ypos = 7
                elif writepointer == 320:
                        cursor_ypos = 8
                elif writepointer == 360:
                        cursor_ypos = 9
                elif writepointer == 400:
                        cursor_ypos = 10
                elif writepointer == 440:
                        cursor_ypos = 11
                elif writepointer == 480:
                        cursor_ypos = 12
                elif writepointer == 520:
                        cursor_ypos = 13
                elif writepointer == 560:
                        cursor_ypos = 14
                elif writepointer == 600:
                        cursor_ypos = 15
                elif writepointer == 640:
                        cursor_ypos = 16
                elif writepointer == 680:
                        cursor_ypos = 17
                elif writepointer == 720:
                        cursor_ypos = 18
                elif writepointer == 760:
                        cursor_ypos = 19
                elif writepointer == 800:
                        cursor_ypos = 20
                elif writepointer == 840:
                        cursor_ypos = 21
                elif writepointer == 880:
                        cursor_ypos = 22
                elif writepointer == 920:
                        cursor_ypos = 23
                elif writepointer > 960:
                        writepointer = 920
                        shiftdisplay()
                        
                
            
            

            if ram_64KB[pc - 1] == 0xD0 and ram_64KB[pc - 2] == 0x10:
                ram_64KB[0xD011] = 0x7F

            wait2 += 1
        update_texture()
        wait2 = 0
            



            
        elapsed = time.perf_counter() - start

if atari_2600 == True:





    wait1 = 0
    wait2 = 0


        #Window Scale Value
    scalevar = 5


    atari2600_width = 160
    atari2600_height = 192

    if not glfw.init():
        raise Exception("GLFW can't be initialized")

    # Request legacy context
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_ANY_PROFILE)

    glfw.window_hint(glfw.RESIZABLE, glfw.FALSE)


    window = glfw.create_window((256 * scalevar), (atari2600_height * scalevar), "Atari® 2600™  -  Ellie's Ems", None, None)
    if not window:
        glfw.terminate()
        raise Exception("GLFW window can't be created")
    


    #Set Icon
    img_path = Path(__file__).parent / "Assets" / "Atari_2600_Icon-64x64.png"
    img = Image.open(img_path).convert("RGBA")
    width, height = img.size
    pixels = np.array(img, dtype=np.uint8)

    glfw.set_window_icon(window, 1, [(width, height, pixels)])



    glfw.make_context_current(window)
    glfw.swap_interval(1)  # vsync

    glClearColor(0.0, 0.0, 0.0, 1.0)

    # Create texture
    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, atari2600_width, atari2600_height, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glEnable(GL_TEXTURE_2D)

    framebuffer = np.zeros((atari2600_height, atari2600_width, 3), dtype=np.uint8)
    framebuffer = np.ascontiguousarray(framebuffer)

    

    def update_texture():

        framebuffer[1, 1] = [255,255,255]


        glBindTexture(GL_TEXTURE_2D, texture)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0,
                        atari2600_width, atari2600_height,
                        GL_RGB, GL_UNSIGNED_BYTE,
                        np.ascontiguousarray(framebuffer))
        


    def atari_2600_tia():
        print("a")





    
    start = time.perf_counter()
    while not glfw.window_should_close(window):
        glfw.poll_events()
        glClear(GL_COLOR_BUFFER_BIT)

        

        # Draw quad
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(-1, -1)
        glTexCoord2f(1, 0); glVertex2f(1, -1)
        glTexCoord2f(1, 1); glVertex2f(1, 1)
        glTexCoord2f(0, 1); glVertex2f(-1, 1)
        glEnd()

        glfw.swap_buffers(window)






        while wait2 != 500:
                    
                pc, ac, x, y, sr, sp, halt, cycle_count = perform_opcode(pc, ram_64KB[pc], ram_64KB[pc+1], ram_64KB[pc+2], ac, x, y, sr, sp, cycle_count)
            
                    















                wait2 += 1
        update_texture()
        wait2 = 0



        elapsed = time.perf_counter() - start


glfw.terminate()