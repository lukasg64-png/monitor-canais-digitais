import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('<div class="chart-canvas-wrap" style="height: 380px;">')
print(html[idx-300:idx+200])
