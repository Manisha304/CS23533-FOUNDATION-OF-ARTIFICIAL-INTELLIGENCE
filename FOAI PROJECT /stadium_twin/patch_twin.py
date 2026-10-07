import os

twin_path = r'c:\Users\manis\OneDrive\Desktop\new foai\stadium_twin\static\twin.html'
with open(twin_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add credentials to fetch calls
content = content.replace('fetch("/api/twin/search?q="', 'fetch("/api/twin/search?q="') # just find it
content = content.replace('method: "POST"', 'method: "POST", credentials: "same-origin"')

# Add an auth check on load
auth_check = """
                // Check auth on load
                fetch('/api/me').then(res => {
                    if(!res.ok) {
                        alert("You are not logged in! Redirecting to login...");
                        window.location.href = '/static/login.html';
                    }
                });
"""
content = content.replace('window.marker = marker;', 'window.marker = marker;' + auth_check)

with open(twin_path, 'w', encoding='utf-8') as f:
    f.write(content)
