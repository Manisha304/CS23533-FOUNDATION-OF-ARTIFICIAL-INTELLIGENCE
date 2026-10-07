import requests

# We need the auth cookie to test properly, or we expect 401, not 404
res = requests.post("http://127.0.0.1:8000/api/twin/3/gates", json={"lat":13.06, "lon":80.27, "name":"test"})
print("Status:", res.status_code)
print("Response:", res.text)
