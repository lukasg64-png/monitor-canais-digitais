import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f):
        if any(term in line.lower() for term in ['canvas', 'chart', 'rendercharts', 'renderdashboard']):
            print(f"Line {idx+1}: {line.strip()[:120]}")
