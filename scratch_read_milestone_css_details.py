import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(1743, 1990):
    if i < len(lines):
        print(lines[i], end='')
