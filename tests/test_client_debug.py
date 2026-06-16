from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

app = FastAPI()

@app.get('/')
def idx(req: Request):
    print("headers:", req.headers)
    return "ok"

client = TestClient(app)
client.headers["x-forwarded-for"] = "1.2.3.4"
client.get("/")
