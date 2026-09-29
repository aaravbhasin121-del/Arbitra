from datetime import datetime, timezone
from app.main import SessionLocal, Event, Project, Score, User, hash_password
s=SessionLocal()
if not s.query(Event).filter_by(id="evt_01").first(): s.add(Event(id="evt_01",name="Sample Hack 2026",submissions_close=datetime(2026,3,1,18,0,tzinfo=timezone.utc),status="SUBMISSION_CLOSED"))
for pid,title,desc,team in [("prj_01","Glass Signal","A sample project.","Team Glass"),("prj_02","Small Meadow","A sample project.","Team Meadow"),("prj_03","Deep Compass","A sample project.","Team Compass")]:
    if not s.query(Project).filter_by(id=pid).first(): s.add(Project(id=pid,event_id="evt_01",title=title,description=desc,team_name=team))
if not s.query(Score).first(): s.add_all([Score(project_id="prj_01",judge_id="judge_a",criterion="innovation",value=8),Score(project_id="prj_01",judge_id="judge_a",criterion="technical",value=7),Score(project_id="prj_01",judge_id="judge_b",criterion="innovation",value=6)])
s.commit();s.close();print("Seed complete")
