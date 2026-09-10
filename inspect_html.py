import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

print("File length:", len(content))
sections = re.findall(r'id=["\'](section[^"\']*)["\']', content)
print("Sections with id=section*:", sections)

all_ids = re.findall(r'id=["\']([^"\']+)["\']', content)
print("Total IDs:", len(all_ids))

# Find buttons or tabs
channel_tabs = re.findall(r'<button[^>]*data-channel[^>]*>[\s\S]*?<\/button>', content)
print("Channel buttons:", [re.sub(r'\s+', ' ', b) for b in channel_tabs])

# Look for headers or titles
h1_h2 = re.findall(r'<(h[123])[^>]*>([\s\S]*?)<\/\1>', content)
print("Headings:")
for tag, text in h1_h2[:15]:
    clean = re.sub(r'<[^>]+>', '', text).strip()
    print(f"  {tag}: {clean}")
