import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(3760, 3830):
    if i < len(lines):
        print(f"{i+1}: {lines[i]}", end='')
