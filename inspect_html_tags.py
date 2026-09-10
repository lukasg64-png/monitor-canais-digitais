import re

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines, 1):
    if i == 2821:
        print(f"Line {i}: <EMBEDDED DATA {len(line)} bytes>")
        continue
    # print headers, section tags, main containers, navs
    stripped = line.strip()
    if stripped.startswith('<header') or stripped.startswith('<section') or stripped.startswith('<main') or stripped.startswith('<nav') or stripped.startswith('<footer') or 'class="header' in stripped or 'class="top-' in stripped:
        print(f"Line {i}: {stripped[:120]}")
    elif '<h1' in stripped or '<h2' in stripped or '<h3' in stripped or '<h4' in stripped:
        print(f"Line {i}: {stripped[:120]}")
