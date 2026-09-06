import requests, io, random
from PIL import Image, ImageDraw

buf = io.BytesIO()
img = Image.new("RGB", (100, 120), (10, 10, 40))
d = ImageDraw.Draw(img)
d.rectangle([20, 30, 80, 90], fill=(201, 169, 106))
img.save(buf, "JPEG")
buf.seek(0)

email = "upfinal_%d@example.com" % random.randint(100000, 999999)
r = requests.post(
    "http://localhost:8000/api/v1/auth/register",
    json={"email": email, "password": "TestPass123!", "full_name": "Up", "mobile": "9876543215"},
)
print("register:", r.status_code)
token = r.json()["access_token"]

r = requests.post(
    "http://localhost:8000/api/v1/upload/person",
    headers={"Authorization": "Bearer %s" % token},
    files={"file": ("person.jpg", buf.getvalue(), "image/jpeg")},
    timeout=60,
)
print("upload person:", r.status_code)
print("body:", r.text[:300])

r = requests.post(
    "http://localhost:8000/api/v1/upload/fabric",
    headers={"Authorization": "Bearer %s" % token},
    files={"file": ("fabric.jpg", buf.getvalue(), "image/jpeg")},
    timeout=60,
)
print("upload fabric:", r.status_code)
print("body:", r.text[:300])