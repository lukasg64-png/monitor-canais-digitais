import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'milestone-widget' in line or 'milestone-container' in line:
        print(f"{idx+1}: {line.strip()}")
