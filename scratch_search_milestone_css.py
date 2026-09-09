import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines[:2400]):
    if 'milestone' in line.lower():
        print(f"{idx+1}: {line.strip()}")
