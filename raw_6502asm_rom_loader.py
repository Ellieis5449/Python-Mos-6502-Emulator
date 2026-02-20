from array import array

ram_64KB = array('B', [0] * 65536)




ram_64KB[0x0000] = 0xA2  # LDX #$0A
ram_64KB[0x0001] = 0x0A

ram_64KB[0x0002] = 0xC8  # INY
ram_64KB[0x0003] = 0xCA  # DEX
ram_64KB[0x0004] = 0xD0  # BNE
ram_64KB[0x0005] = 0xFB

ram_64KB[0x0007] = 0xEA  # NOP
ram_64KB[0x0008] = 0x4C  # JMP $0007
ram_64KB[0x0009] = 0x06
ram_64KB[0x000A] = 0x00

pc = 0x0000
print(f"6502 ASM Program ROM loaded at {hex(0x0000)}, PC = {hex(pc)} in General 6502 ram\n")