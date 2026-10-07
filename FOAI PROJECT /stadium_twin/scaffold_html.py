import os

base_dir = r'c:\Users\manis\OneDrive\Desktop\new foai\stadium_twin'

login_html = '''<!DOCTYPE html>
<html>
<head>
    <title>StadiumTwin v2 - Login</title>
</head>
<body>
    <h2>Login</h2>
    <form id="loginForm">
        <input type="text" id="username" name="username" placeholder="Username" required><br><br>
        <input type="password" id="password" name="password" placeholder="Password" required><br><br>
        <button type="submit">Login</button>
    </form>
    <p>Don\\'t have an account? <a href="/static/register.html">Register here</a></p>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new URLSearchParams(new FormData(e.target));
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });
            if (response.ok) {
                window.location.href = '/static/dashboard.html';
            } else {
                const data = await response.json();
                alert(data.detail || 'Login failed');
            }
        });
    </script>
</body>
</html>'''

register_html = '''<!DOCTYPE html>
<html>
<head>
    <title>StadiumTwin v2 - Register</title>
</head>
<body>
    <h2>Register</h2>
    <form id="registerForm">
        <input type="text" id="username" name="username" placeholder="Username" required><br><br>
        <input type="password" id="password" name="password" placeholder="Password" required><br><br>
        <button type="submit">Register</button>
    </form>
    <p>Already have an account? <a href="/static/login.html">Login here</a></p>

    <script>
        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new URLSearchParams(new FormData(e.target));
            const response = await fetch('/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });
            if (response.ok) {
                alert('Registration successful! Please login.');
                window.location.href = '/static/login.html';
            } else {
                const data = await response.json();
                alert(data.detail || 'Registration failed');
            }
        });
    </script>
</body>
</html>'''

dashboard_html = '''<!DOCTYPE html>
<html>
<head>
    <title>StadiumTwin v2 - Dashboard</title>
</head>
<body>
    <h2>Dashboard</h2>
    <p>Welcome, <span id="username"></span>!</p>
    <button onclick="logout()">Logout</button>

    <script>
        async function fetchUser() {
            const response = await fetch('/api/me');
            if (response.ok) {
                const data = await response.json();
                document.getElementById('username').innerText = data.username;
            } else {
                window.location.href = '/static/login.html';
            }
        }
        
        async function logout() {
            await fetch('/auth/logout', { method: 'POST' });
            window.location.href = '/static/login.html';
        }

        fetchUser();
    </script>
</body>
</html>'''

files = {
    'static/login.html': login_html,
    'static/register.html': register_html,
    'static/dashboard.html': dashboard_html
}

for path, content in files.items():
    full_path = os.path.join(base_dir, path.replace('/', os.sep))
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("HTML files scaffolded.")
