import os, re

# Pattern for emojis
p = re.compile(r'[\U0001F300-\U0001F5FF\U0001F900-\U0001F9FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]')

with open('emojis_found.txt', 'w', encoding='utf-8') as out:
    for root, dirs, files in os.walk('.'):
        if any(x in root for x in ['.git', '__pycache__', 'venv', 'node_modules']):
            continue
        for file in files:
            if file.endswith(('.html', '.js', '.py', '.css')):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f):
                            if p.search(line) or any(e in line for e in ['✅', '⚠️', '🏟', '🌊', '🚪', '🚨', '🔴', '🟢', '🟡', '🗺', '👥', '🚗', '🍔', '🎯', '🤖', '⚡', '❌', '🏥', '🚑', '📊', '📐', '🎬', '📋', '🔵', '🔗', '✏️', '🗑', '🏗', '➕']):
                                out.write(f"{path}:{i+1}: {line.strip()}\n")
                except Exception as e:
                    pass
