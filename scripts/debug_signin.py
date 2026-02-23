import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app
from dotenv import load_dotenv

load_dotenv()

app.config['TESTING'] = True
client = app.test_client()

try:
    response = client.post('/api/users/signin', json={
        "email": "aelharouchi@myanalytiq.org",
        "password": "invalidpassword"
    })
    print(f"Status Code: {response.status_code}")
    print(f"Data: {response.data.decode('utf-8')}")
except Exception as e:
    import traceback
    traceback.print_exc()
