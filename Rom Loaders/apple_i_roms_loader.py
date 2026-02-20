from array import array
from pathlib import Path

base_path = Path(__file__).parent

program = array('B', [0] * 65536)

#Load Woz Monitor ROM
monitor_path = Path(__file__).parent / "Roms" / "Apple I" / "Apple-1 ROM.bin"
with open(monitor_path, "rb") as f:
    monitor_data = f.read()

monitor_start = 0xFF00
for i, byte in enumerate(monitor_data):
    program[monitor_start + i] = byte



pc = 0xFF00
print(f"Monitor ROM loaded at {hex(monitor_start)}, PC = {hex(pc)} in Apple I ram")
f.close()

#Load Woz BASIC ROM
basic_path = Path(__file__).parent / "Roms" / "Apple I" / "Apple-1 BASIC ROM.bin"
with open(basic_path, "rb") as f:
    basic_data = f.read()

basic_start = 0xE000
for i, byte in enumerate(basic_data):
    program[basic_start + i] = byte

print(f"BASIC ROM loaded at {hex(basic_start)} in Apple I ram\n")
f.close()