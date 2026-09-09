import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(3660, min(len(lines), 3820)):
    print(f"{i+1}: {lines[i]}", end='')
