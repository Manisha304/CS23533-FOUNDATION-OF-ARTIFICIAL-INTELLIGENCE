import os

filepath = r'c:\Users\manis\OneDrive\Desktop\new foai\stadium_twin\app\geo\osm_fetch.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_content = content.replace(
    'response = requests.post(url, data={"data": query})',
    'headers = {"User-Agent": "StadiumTwin_v2_Academic_Project/1.0 (manis@example.com)"}\n    response = requests.post(url, data={"data": query}, headers=headers)'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)
