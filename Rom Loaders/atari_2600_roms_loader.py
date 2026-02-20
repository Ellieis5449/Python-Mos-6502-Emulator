from array import array
from pathlib import Path

base_path = Path(__file__).parent

program = array('B', [0] * 65536)

#Load Game ROM
game_path = Path(__file__).parent / "Roms" / "Atari-2600-VCS-ROM-Collection" / "ROMS" / "Baseball (AKA Super Challenge Baseball) (1988) (Telegames) (5665 A016) (PAL).bin"
with open(game_path, "rb") as f:
    game_data = f.read()

game_start = 0xF000
for i, byte in enumerate(game_data):
    program[game_start + i] = byte



pc = 0xFF00
print(f"Atari 2600 ROM loaded at {hex(game_start)}, PC = {hex(pc)} in Atari 2600 ram\n")
f.close()