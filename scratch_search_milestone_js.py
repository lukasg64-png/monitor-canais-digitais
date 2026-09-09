import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'milestone-widget-container' in line or 'toggleMilestoneCalc' in line or 'metaMilestoneLine' in line:
        print(f"{idx+1}: {line.strip()}")
