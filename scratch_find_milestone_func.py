import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'function updateMilestoneWidget' in line:
        print(f"Line {idx+1}: {line}")
        for j in range(idx, min(idx+60, len(lines))):
            print(f"{j+1}: {lines[j]}", end='')
        break
