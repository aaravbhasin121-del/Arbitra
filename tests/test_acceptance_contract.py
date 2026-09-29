from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_gallery_public(): assert client.get('/api/gallery').status_code==200
def test_participant_blocked(): assert client.get('/api/judge-scores',headers={'X-Role':'participant'}).status_code in (401,403)
def test_judge_own_scores(): assert client.get('/api/judge-scores',headers={'X-Role':'judge_a'}).status_code==200
def test_peer_blocked(): assert client.get('/api/peer-scores',headers={'X-Role':'judge_b'}).status_code in (401,403)
def test_csv(): r=client.get('/api/csv-export',headers={'X-Role':'organizer'}); assert r.status_code==200 and ',' in r.text
