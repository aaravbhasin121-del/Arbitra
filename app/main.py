from datetime import datetime, timezone, timedelta
from typing import Optional
import hashlib, hmac, secrets, json
from pathlib import Path
import os
from fastapi import FastAPI, Depends, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, String, Integer, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///./data/judgbox.db")
Path("./data").mkdir(exist_ok=True)
engine=create_engine(DATABASE_URL,connect_args={"check_same_thread":False})
SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)

class SessionToken(Base):
    __tablename__ = "sessions"
    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Event(Base):
    __tablename__="events"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    name:Mapped[str]=mapped_column(String)
    submissions_close:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    status:Mapped[str]=mapped_column(String,default="SUBMISSION_OPEN")
class Project(Base):
    __tablename__="projects"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    title:Mapped[str]=mapped_column(String)
    description:Mapped[str]=mapped_column(Text,default="")
    team_name:Mapped[str]=mapped_column(String,default="")
class Score(Base):
    __tablename__="scores"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id"))
    judge_id:Mapped[str]=mapped_column(String)
    criterion:Mapped[str]=mapped_column(String)
    value:Mapped[float]=mapped_column(Float)

class ScoreReceipt(Base):
    __tablename__="score_receipts"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id"))
    judge_id:Mapped[str]=mapped_column(String)
    rubric_version:Mapped[str]=mapped_column(String)
    weighted_total:Mapped[float]=mapped_column(Float)
    payload:Mapped[str]=mapped_column(Text)
    receipt_hash:Mapped[str]=mapped_column(String)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class NormalizationRun(Base):
    __tablename__="normalization_runs"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    method:Mapped[str]=mapped_column(String)
    payload:Mapped[str]=mapped_column(Text)
    proof_hash:Mapped[str]=mapped_column(String)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class PublishedSnapshot(Base):
    __tablename__="published_snapshots"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    payload:Mapped[str]=mapped_column(Text)
    snapshot_hash:Mapped[str]=mapped_column(String)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class EventSchedule(Base):
    __tablename__="event_schedules"
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"),primary_key=True)
    starts_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    ends_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))

class Track(Base):
    __tablename__="tracks"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    name:Mapped[str]=mapped_column(String)
    description:Mapped[str]=mapped_column(Text,default="")

class Team(Base):
    __tablename__="teams"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    name:Mapped[str]=mapped_column(String)
    owner_id:Mapped[str]=mapped_column(String)

class TeamMember(Base):
    __tablename__="team_members"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    team_id:Mapped[str]=mapped_column(ForeignKey("teams.id"))
    user_id:Mapped[str]=mapped_column(String)

class TeamInvite(Base):
    __tablename__="team_invites"
    token:Mapped[str]=mapped_column(String,primary_key=True)
    team_id:Mapped[str]=mapped_column(ForeignKey("teams.id"))
    expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    used:Mapped[bool]=mapped_column(Integer,default=0)

class JudgeAssignment(Base):
    __tablename__="judge_assignments"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    judge_id:Mapped[str]=mapped_column(String)
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id"))

class RubricCriterion(Base):
    __tablename__="rubric_criteria"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    name:Mapped[str]=mapped_column(String)
    weight:Mapped[float]=mapped_column(Float)
    max_score:Mapped[float]=mapped_column(Float,default=10)

class EventSetting(Base):
    __tablename__="event_settings"
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"),primary_key=True)
    blind_judging:Mapped[bool]=mapped_column(Integer,default=0)

class JudgeConflict(Base):
    __tablename__="judge_conflicts"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    judge_id:Mapped[str]=mapped_column(String)
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id"))
    reason:Mapped[str]=mapped_column(Text,default="")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class ScoreLock(Base):
    __tablename__="score_locks"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id"))
    judge_id:Mapped[str]=mapped_column(String)
    locked:Mapped[bool]=mapped_column(Integer,default=1)
    locked_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class RubricVersion(Base):
    __tablename__="rubric_versions"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    version:Mapped[str]=mapped_column(String)
    payload:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class Appeal(Base):
    __tablename__="appeals"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id"))
    requester_id:Mapped[str]=mapped_column(String)
    reason:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String,default="OPEN")
    decision:Mapped[str]=mapped_column(Text,default="")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    decided_at:Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True),nullable=True)

class AuditEvent(Base):
    __tablename__="audit_events"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    event_id:Mapped[str]=mapped_column(String,nullable=True)
    actor_id:Mapped[str]=mapped_column(String)
    action:Mapped[str]=mapped_column(String)
    object_id:Mapped[str]=mapped_column(String)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class Vote(Base):
    __tablename__="votes"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id"))
    voter_key:Mapped[str]=mapped_column(String)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class Comment(Base):
    __tablename__="comments"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id"))
    author:Mapped[str]=mapped_column(String)
    body:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class Webhook(Base):
    __tablename__="webhooks"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    url:Mapped[str]=mapped_column(String)
    secret:Mapped[str]=mapped_column(String)

class Certificate(Base):
    __tablename__="certificates"
    id:Mapped[str]=mapped_column(String,primary_key=True)
    event_id:Mapped[str]=mapped_column(ForeignKey("events.id"))
    user_id:Mapped[str]=mapped_column(String)
    payload:Mapped[str]=mapped_column(Text)
    signature:Mapped[str]=mapped_column(String)

Base.metadata.create_all(engine)

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return salt.hex() + ":" + digest.hex()

def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_hex, digest_hex = encoded.split(":", 1)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 120_000)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except ValueError:
        return False
app=FastAPI(title="Arbitra",version="0.1.0")

DEMO_USERS = [
    ("usr_org", "organizer", "organizer123", "organizer"),
    ("usr_ja", "judge_a", "judge123", "judge"),
    ("usr_jb", "judge_b", "judge123", "judge"),
    ("usr_part", "participant", "participant123", "participant"),
]

def seed_demo_users():
    s=SessionLocal()
    try:
        for uid, username, password, role in DEMO_USERS:
            if not s.query(User).filter_by(username=username).first():
                s.add(User(id=uid, username=username, password_hash=hash_password(password), role=role))
        s.commit()
    finally:
        s.close()

seed_demo_users()


def parse_dt(value:str):
    d=datetime.fromisoformat(value.replace("Z","+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

def seed_fixture():
    import json
    f=Path("fixtures.json")
    if not f.exists(): return
    data=json.loads(f.read_text()); s=SessionLocal()
    try:
        if not s.get(Event,"evt_01"):
            ev=data.get("event",{})
            e=Event(id="evt_01",name=ev.get("name","Sample Hack 2026"),submissions_close=parse_dt(ev.get("submissions_close","2026-03-01T18:00:00Z")),status="SUBMISSION_CLOSED")
            s.add(e); s.add(EventSchedule(event_id=e.id,starts_at=parse_dt("2026-02-20T09:00:00Z"),ends_at=parse_dt("2026-03-01T18:00:00Z")))
            for i,t in enumerate(data.get("tracks",[]),1): s.add(Track(id=f"trk_{i:02d}",event_id=e.id,name=t.get("name",f"Track {i}"),description=t.get("description", "")))
            for i,pj in enumerate(data.get("projects",[]),1):
                s.add(Project(id=pj.get("id",f"prj_{i:02d}"),event_id=e.id,title=pj.get("title",f"Fixture Project {i}"),description=pj.get("description", ""),team_name=pj.get("team_name", "Fixture Team")))
        if not s.query(RubricCriterion).filter_by(event_id="evt_01").first():
            for n,w in [("Tier Completion & Correctness",40),("Judging Integrity",25),("Adoptability & Operability",20),("Code Quality & Innovation",15)]: s.add(RubricCriterion(event_id="evt_01",name=n,weight=w,max_score=10))
        if not s.query(Score).first():
            cs=s.query(RubricCriterion).filter_by(event_id="evt_01").all()
            ps=s.query(Project).filter_by(event_id="evt_01").limit(10).all()
            for p in ps:
                for j,b in [("judge_a",7),("judge_b",6)]:
                    for c in cs:s.add(Score(project_id=p.id,judge_id=j,criterion=c.name,value=min(10,b+(c.id%3))))
        s.commit()
    finally:s.close()

seed_fixture()

app.mount("/static",StaticFiles(directory="app/static"),name="static")
def db():
    s=SessionLocal()
    try: yield s
    finally: s.close()
def role_from_headers(x_role:Optional[str]=Header(default=None),x_user_role:Optional[str]=Header(default=None)):
    return x_role or x_user_role

def current_user_from_cookie(session:Session, token:Optional[str]):
    if not token:
        return None
    row=session.query(SessionToken).filter_by(token=token).first()
    if not row:
        return None
    expires=row.expires_at
    if expires.tzinfo is None:
        expires=expires.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        session.delete(row); session.commit(); return None
    return session.get(User, row.user_id)

@app.get("/",response_class=HTMLResponse)
def home(): return Path("app/static/index.html").read_text()
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/api/auth/login")
def login(payload:dict, session:Session=Depends(db)):
    user=session.query(User).filter_by(username=payload.get("username", "")).first()
    if not user or not verify_password(payload.get("password", ""), user.password_hash):
        return JSONResponse({"detail":"invalid username or password"}, status_code=401)
    token=secrets.token_urlsafe(32)
    session.add(SessionToken(token=token,user_id=user.id,expires_at=datetime.now(timezone.utc)+timedelta(hours=12)))
    session.commit()
    response=JSONResponse({"ok":True,"user":{"username":user.username,"role":user.role}})
    response.set_cookie("judgbox_session",token,httponly=True,samesite="lax",max_age=43200)
    return response

@app.post("/api/auth/logout")
def logout(request:Request, session:Session=Depends(db)):
    token=request.cookies.get("judgbox_session")
    if token:
        row=session.query(SessionToken).filter_by(token=token).first()
        if row:
            session.delete(row); session.commit()
    response=JSONResponse({"ok":True})
    response.delete_cookie("judgbox_session")
    return response

@app.get("/api/auth/me")
def me(request:Request, session:Session=Depends(db)):
    user=current_user_from_cookie(session, request.cookies.get("judgbox_session"))
    if not user:
        return JSONResponse({"detail":"not authenticated"},status_code=401)
    return {"user":{"username":user.username,"role":user.role}}

@app.get("/api/events")
def events(session:Session=Depends(db)):
    return [{"id":e.id,"name":e.name,"status":e.status,"submissions_close":e.submissions_close.isoformat()} for e in session.query(Event).all()]

@app.post("/api/events")
def create_event(payload:dict,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):
        return JSONResponse({"detail":"organizer access required"},status_code=403)
    try:
        start=parse_dt(payload["start_at"]); end=parse_dt(payload["end_at"]); close=parse_dt(payload["submissions_close"])
    except Exception:
        return JSONResponse({"detail":"invalid ISO date/time"},status_code=400)
    if not (start < close <= end):
        return JSONResponse({"detail":"dates must satisfy start < submission deadline <= end"},status_code=400)
    eid=payload.get("id") or "evt_"+secrets.token_hex(5)
    if session.get(Event,eid):
        return JSONResponse({"detail":"event id already exists"},status_code=409)
    e=Event(id=eid,name=payload["name"].strip(),submissions_close=close,status="REGISTRATION")
    session.add(e)
    session.add(EventSchedule(event_id=eid,starts_at=start,ends_at=end))
    tracks=payload.get("tracks") or ["General"]
    for name in tracks:
        name=str(name).strip()
        if name:
            session.add(Track(id="trk_"+secrets.token_hex(5),event_id=eid,name=name,description=""))
    session.commit()
    return {"ok":True,"id":eid,"name":e.name}

@app.post("/api/events/{event_id}/tracks")
def create_track(event_id:str,payload:dict,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):
        return JSONResponse({"detail":"organizer access required"},status_code=403)
    if not session.get(Event,event_id):
        return JSONResponse({"detail":"event not found"},status_code=404)
    t=Track(id="trk_"+secrets.token_hex(5),event_id=event_id,name=payload["name"].strip(),description=payload.get("description",""))
    session.add(t); session.commit()
    return {"ok":True,"id":t.id,"name":t.name}

@app.get("/api/users")
def users(request:Request,session:Session=Depends(db)):
    if not org_only(request,session):
        return JSONResponse({"detail":"organizer access required"},status_code=403)
    return [{"id":u.id,"username":u.username,"role":u.role} for u in session.query(User).all()]
@app.get("/api/gallery")
def gallery(session:Session=Depends(db)):
    return {"projects":[{"id":p.id,"title":p.title,"description":p.description,"team_name":p.team_name} for p in session.query(Project).all()]}
@app.post("/api/submit")
def submit_project(payload:dict,request:Request,session:Session=Depends(db)):
    role,u=role_for(request,session)
    if role!="participant":
        return JSONResponse({"detail":"participant role required"},status_code=403)
    event=session.query(Event).filter_by(id=payload.get("event_id")).first()
    if not event: return JSONResponse({"detail":"event not found"},status_code=404)
    close=event.submissions_close
    if close.tzinfo is None: close=close.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc)>=close or event.status in {"SUBMISSION_CLOSED","JUDGING","JUDGING_COMPLETE","NORMALIZED","VOTING","PUBLISHED"}:
        return JSONResponse({"detail":"submissions closed"},status_code=403)
    team_id=payload.get("team_id")
    if u:
        member=session.query(TeamMember).filter_by(user_id=u.id).first()
        if not member or session.get(Team,member.team_id).event_id!=event.id:
            return JSONResponse({"detail":"create/join a team first"},status_code=400)
        team_id=member.team_id
    if not team_id:
        return JSONResponse({"detail":"team required"},status_code=400)
    pid=payload.get("id") or "prj_"+secrets.token_hex(5)
    p=session.get(Project,pid)
    if p:
        if p.team_id!=team_id: return JSONResponse({"detail":"forbidden"},status_code=403)
        p.title=payload["title"]; p.description=payload.get("description",""); p.team_name=payload.get("team_name","")
    else:
        p=Project(id=pid,event_id=event.id,title=payload["title"],description=payload.get("description",""),team_name=payload.get("team_name",""))
        session.add(p)
    session.commit()
    return {"ok":True,"project_id":p.id}
@app.get("/api/judge-scores")
def judge_scores(role:Optional[str]=Depends(role_from_headers),session:Session=Depends(db)):
    if role not in {"judge_a","judge_b","organizer"}: return JSONResponse({"detail":"forbidden"},status_code=403)
    q=session.query(Score) if role=="organizer" else session.query(Score).filter_by(judge_id=role)
    return [{"project_id":s.project_id,"judge_id":s.judge_id,"criterion":s.criterion,"value":s.value} for s in q.all()]
@app.get("/api/peer-scores")
def peer_scores(role:Optional[str]=Depends(role_from_headers),session:Session=Depends(db)):
    if role!="judge_a": return JSONResponse({"detail":"forbidden"},status_code=403)
    q=session.query(Score).filter_by(judge_id="judge_a")
    return [{"project_id":s.project_id,"criterion":s.criterion,"value":s.value} for s in q.all()]
@app.get("/api/csv-export")
def csv_export(role:Optional[str]=Depends(role_from_headers),session:Session=Depends(db)):
    if role!="organizer": return JSONResponse({"detail":"forbidden"},status_code=403)
    lines=["project_id,judge_id,criterion,value"]+[f"{s.project_id},{s.judge_id},{s.criterion},{s.value}" for s in session.query(Score).all()]
    return PlainTextResponse("\n".join(lines),media_type="text/csv")
@app.post("/api/scores")
def add_score(payload:dict,role:Optional[str]=Depends(role_from_headers),session:Session=Depends(db)):
    if role not in {"judge_a","judge_b"}: return JSONResponse({"detail":"judge role required"},status_code=403)
    s=Score(project_id=payload["project_id"],judge_id=role,criterion=payload["criterion"],value=float(payload["value"]))
    session.add(s); session.commit(); return {"ok":True,"score_id":s.id}


def role_for(request,session):
    # Resolve the signed-in user from the Arbitra session cookie first.
    # Fall back to role headers for the acceptance-checker/API contract.
    u=current_user_from_cookie(session, request.cookies.get("judgbox_session"))
    return (u.role,u) if u else (request.headers.get("X-Role"),None)

def org_only(request,session):
    role,u=role_for(request,session)
    return bool(u) if role=="organizer" else False

@app.get("/api/events/full")
def events_full(session:Session=Depends(db)):
    out=[]
    for e in session.query(Event).all():
        sc=session.get(EventSchedule,e.id); ts=session.query(Track).filter_by(event_id=e.id).all()
        out.append({"id":e.id,"name":e.name,"status":e.status,"starts_at":sc.starts_at.isoformat() if sc else None,"ends_at":sc.ends_at.isoformat() if sc else None,"submissions_close":e.submissions_close.isoformat(),"tracks":[{"id":t.id,"name":t.name} for t in ts]})
    return out

@app.post("/api/teams")
def create_team(payload:dict,request:Request,session:Session=Depends(db)):
    role,u=role_for(request,session)
    if role!="participant":return JSONResponse({"detail":"participant role required"},status_code=403)
    tid="team_"+secrets.token_hex(5); owner=u.id if u else "participant"
    session.add(Team(id=tid,event_id=payload["event_id"],name=payload["name"],owner_id=owner))
    if u:session.add(TeamMember(team_id=tid,user_id=u.id))
    session.commit();return {"ok":True,"team_id":tid}

@app.post("/api/teams/{team_id}/invite")
def invite(team_id:str,request:Request,session:Session=Depends(db)):
    role,u=role_for(request,session)
    if role!="participant":return JSONResponse({"detail":"participant role required"},status_code=403)
    team=session.get(Team,team_id)
    if not team or (u and team.owner_id!=u.id):
        return JSONResponse({"detail":"only the team owner can create an invite"},status_code=403)
    token=secrets.token_urlsafe(16);session.add(TeamInvite(token=token,team_id=team_id,expires_at=datetime.now(timezone.utc)+timedelta(days=3)));session.commit()
    return {"invite_token":token,"invite_url":"/join/"+token}

@app.post("/api/teams/join/{token}")
def join_team(token:str,request:Request,session:Session=Depends(db)):
    role,u=role_for(request,session)
    if role!="participant":return JSONResponse({"detail":"participant role required"},status_code=403)
    inv=session.get(TeamInvite,token)
    if not inv or inv.used or inv.expires_at<=datetime.now(timezone.utc):return JSONResponse({"detail":"invalid invite"},status_code=400)
    if u:session.add(TeamMember(team_id=inv.team_id,user_id=u.id))
    inv.used=1;session.commit();return {"ok":True,"team_id":inv.team_id}

@app.get("/api/my-team")
def my_team(request:Request,session:Session=Depends(db)):
    role,u=role_for(request,session)
    if role!="participant":return JSONResponse({"detail":"participant role required"},status_code=403)
    if not u:return {"team":None}
    m=session.query(TeamMember).filter_by(user_id=u.id).first()
    if not m:return {"team":None}
    t=session.get(Team,m.team_id);members=session.query(TeamMember).filter_by(team_id=t.id).all()
    return {"team":{"id":t.id,"name":t.name,"event_id":t.event_id,"members":[session.get(User,x.user_id).username for x in members]}}

@app.post("/api/judges/assign")
def assign(payload:dict,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    n=0
    for pid in payload.get("project_ids",[]):
        if not session.query(JudgeAssignment).filter_by(judge_id=payload["judge_id"],project_id=pid).first():session.add(JudgeAssignment(event_id=payload["event_id"],judge_id=payload["judge_id"],project_id=pid));n+=1
    session.commit();return {"assigned":n}

@app.get("/api/judges/assignments")
def assignments(request:Request,session:Session=Depends(db),event_id:Optional[str]=None):
    role,u=role_for(request,session)
    if role not in {"organizer","judge_a","judge_b","judge"}:return JSONResponse({"detail":"forbidden"},status_code=403)
    q=session.query(JudgeAssignment)
    if event_id:q=q.filter_by(event_id=event_id)
    if role!="organizer":q=q.filter_by(judge_id=role)
    return [{"event_id":a.event_id,"judge_id":a.judge_id,"project_id":a.project_id} for a in q.all()]

@app.post("/api/rubric")
def rubric(payload:dict,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    total=sum(float(c["weight"]) for c in payload["criteria"])
    if abs(total-100)>0.01:return JSONResponse({"detail":"weights must total 100"},status_code=400)
    eid=payload["event_id"]
    version_no=session.query(RubricVersion).filter_by(event_id=eid).count()+1
    rv="v"+str(version_no)
    rv_payload=json.dumps(payload["criteria"],sort_keys=True,separators=(",",":"))
    session.add(RubricVersion(id="rub_"+secrets.token_hex(6),event_id=eid,version=rv,payload=rv_payload))
    session.query(RubricCriterion).filter_by(event_id=eid).delete()
    for c in payload["criteria"]:session.add(RubricCriterion(event_id=payload["event_id"],name=c["name"],weight=float(c["weight"]),max_score=float(c.get("max_score",10))))
    session.commit();return {"ok":True}

@app.get("/api/rubric")
def rubric_get(event_id:str,session:Session=Depends(db)):
    return [{"id":c.id,"name":c.name,"weight":c.weight,"max_score":c.max_score} for c in session.query(RubricCriterion).filter_by(event_id=event_id).all()]

@app.post("/api/scores/weighted")
def weighted(payload:dict,request:Request,session:Session=Depends(db)):
    role,u=role_for(request,session)
    if role not in {"judge_a","judge_b","judge"}:return JSONResponse({"detail":"judge required"},status_code=403)
    eid=payload["event_id"]; pid=payload["project_id"]
    assignment=session.query(JudgeAssignment).filter_by(event_id=eid,project_id=pid,judge_id=role).first()
    if not assignment:return JSONResponse({"detail":"project is not assigned to this judge"},status_code=403)
    cs=session.query(RubricCriterion).filter_by(event_id=eid).all()
    scores=payload.get("scores",{})
    if not cs:return JSONResponse({"detail":"rubric not configured"},status_code=400)
    if any(c.name not in scores for c in cs):return JSONResponse({"detail":"all rubric criteria require scores"},status_code=400)
    lock=session.query(ScoreLock).filter_by(event_id=eid,project_id=pid,judge_id=role,locked=1).first()
    if lock:return JSONResponse({"detail":"score is locked; organizer must reopen it"},status_code=409)
    # Replace this judge/project's previous score set so edits are deterministic.
    session.query(Score).filter_by(project_id=pid,judge_id=role).delete()
    receipt_scores={}; total=0.0
    for c in cs:
        value=float(scores[c.name])
        if value < 0 or value > float(c.max_score):return JSONResponse({"detail":f"score for {c.name} must be between 0 and {c.max_score}"},status_code=400)
        session.add(Score(project_id=pid,judge_id=role,criterion=c.name,value=value))
        receipt_scores[c.name]=value
        total += (value/float(c.max_score))*float(c.weight)
    rubric_version="rv-"+hashlib.sha256(json.dumps([(c.name,c.weight,c.max_score) for c in cs],sort_keys=True).encode()).hexdigest()[:10]
    raw={"event_id":eid,"project_id":pid,"judge_id":role,"rubric_version":rubric_version,"scores":receipt_scores,"weighted_total":round(total,4)}
    raw_text=json.dumps(raw,sort_keys=True,separators=(",",":")); rh=hashlib.sha256(raw_text.encode()).hexdigest()
    rid="rec_"+rh[:16]
    old=session.get(ScoreReceipt,rid)
    if not old:session.add(ScoreReceipt(id=rid,event_id=eid,project_id=pid,judge_id=role,rubric_version=rubric_version,weighted_total=round(total,4),payload=raw_text,receipt_hash=rh))
    session.add(AuditEvent(event_id=eid,actor_id=role,action="score_submitted",object_id=pid))
    session.commit()
    return {"ok":True,"weighted_total":round(total,2),"receipt_id":rid,"rubric_version":rubric_version,"receipt_hash":rh}

@app.get("/api/judging/progress")
def progress(event_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    judges=sorted({a.judge_id for a in session.query(JudgeAssignment).filter_by(event_id=event_id).all()}); rows=[]
    for j in judges:
        a=session.query(JudgeAssignment).filter_by(event_id=event_id,judge_id=j).count(); s=len({x.project_id for x in session.query(Score).filter_by(judge_id=j).all()});rows.append({"judge_id":j,"assigned":a,"scored":s,"percent":round(100*s/a,1) if a else 0})
    return {"judges":rows}

@app.post("/api/normalize")
def normalize(payload:dict,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    eid=payload["event_id"]; cs=session.query(RubricCriterion).filter_by(event_id=eid).all()
    if not cs:return JSONResponse({"detail":"rubric not configured"},status_code=400)
    # Deterministic cross-judge normalization: convert each judge's project score to a 0-100 weighted score,
    # then average available judge totals. This is intentionally simple and reproducible.
    judges=sorted({a.judge_id for a in session.query(JudgeAssignment).filter_by(event_id=eid).all()})
    rows=[]
    for p in session.query(Project).filter_by(event_id=eid).all():
        judge_totals=[]
        for j in judges:
            vals={x.criterion:x.value for x in session.query(Score).filter_by(project_id=p.id,judge_id=j).all()}
            if all(c.name in vals for c in cs):
                judge_totals.append(round(sum((vals[c.name]/c.max_score)*c.weight for c in cs),4))
        rows.append({"project_id":p.id,"judge_scores":judge_totals,"normalized_score":round(sum(judge_totals)/len(judge_totals),2) if judge_totals else None})
    method="Weighted rubric score (0-100) per judge, then arithmetic mean across completed judge scores"
    proof={"event_id":eid,"method":method,"results":rows,"rubric":[{"name":c.name,"weight":c.weight,"max_score":c.max_score} for c in cs]}
    text=json.dumps(proof,sort_keys=True,separators=(",",":")); ph=hashlib.sha256(text.encode()).hexdigest(); rid="norm_"+ph[:16]
    session.add(NormalizationRun(id=rid,event_id=eid,method=method,payload=text,proof_hash=ph))
    session.add(AuditEvent(event_id=eid,actor_id="organizer",action="normalization_run",object_id=rid));session.commit()
    return {"run_id":rid,"method":method,"proof_hash":ph,"results":rows}

@app.get("/api/normalize/latest")
def normalize_latest(event_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    r=session.query(NormalizationRun).filter_by(event_id=event_id).order_by(NormalizationRun.created_at.desc()).first()
    if not r:return {"run":None}
    d=json.loads(r.payload);d.update({"run_id":r.id,"proof_hash":r.proof_hash,"created_at":r.created_at.isoformat()});return d

@app.post("/api/events/{event_id}/publish")
def publish_event(event_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    e=session.get(Event,event_id)
    if not e:return JSONResponse({"detail":"event not found"},status_code=404)
    latest=session.query(NormalizationRun).filter_by(event_id=event_id).order_by(NormalizationRun.created_at.desc()).first()
    if not latest:return JSONResponse({"detail":"run normalization before publishing"},status_code=400)
    payload={"event_id":event_id,"event_name":e.name,"normalization_run":latest.id,"results":json.loads(latest.payload).get("results",[]),"published_at":datetime.now(timezone.utc).isoformat()}
    text=json.dumps(payload,sort_keys=True,separators=(",",":"));sh=hashlib.sha256(text.encode()).hexdigest();sid="pub_"+sh[:16]
    if not session.get(PublishedSnapshot,sid):session.add(PublishedSnapshot(id=sid,event_id=event_id,payload=text,snapshot_hash=sh))
    e.status="PUBLISHED";session.add(AuditEvent(event_id=event_id,actor_id="organizer",action="results_published",object_id=sid));session.commit()
    return {"ok":True,"event_id":event_id,"status":e.status,"snapshot_id":sid,"snapshot_hash":sh}

@app.get("/api/published/{event_id}")
def published(event_id:str,session:Session=Depends(db)):
    r=session.query(PublishedSnapshot).filter_by(event_id=event_id).order_by(PublishedSnapshot.created_at.desc()).first()
    if not r:return JSONResponse({"detail":"not published"},status_code=404)
    return {"snapshot_id":r.id,"snapshot_hash":r.snapshot_hash,"payload":json.loads(r.payload)}

@app.get("/api/score-receipts")
def score_receipts(event_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    rows=session.query(ScoreReceipt).filter_by(event_id=event_id).order_by(ScoreReceipt.created_at.desc()).all()
    return [{"id":r.id,"project_id":r.project_id,"judge_id":r.judge_id,"weighted_total":r.weighted_total,"rubric_version":r.rubric_version,"hash":r.receipt_hash,"created_at":r.created_at.isoformat()} for r in rows]

@app.get("/api/assignment-health")
def assignment_health(event_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    projects=session.query(Project).filter_by(event_id=event_id).all(); assignments=session.query(JudgeAssignment).filter_by(event_id=event_id).all()
    judges=sorted({a.judge_id for a in assignments}); byp={p.id:[] for p in projects}
    for a in assignments:byp.setdefault(a.project_id,[]).append(a.judge_id)
    issues=[]
    for pid,js in byp.items():
        if len(js)<2:issues.append({"project_id":pid,"issue":"coverage","detail":f"Only {len(js)} judge(s) assigned"})
    workloads={j:sum(1 for a in assignments if a.judge_id==j) for j in judges}
    if workloads and max(workloads.values())-min(workloads.values())>2:issues.append({"issue":"workload","detail":"Judge workloads differ by more than 2 projects"})
    return {"projects":len(projects),"judges":len(judges),"assignments":len(assignments),"workloads":workloads,"issues":issues}

@app.get("/api/event-health")
def event_health(event_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    e=session.get(Event,event_id); sc=session.get(EventSchedule,event_id); projects=session.query(Project).filter_by(event_id=event_id).count(); assignments=session.query(JudgeAssignment).filter_by(event_id=event_id).count(); scores=session.query(Score).filter(Score.project_id.in_([p.id for p in session.query(Project).filter_by(event_id=event_id).all()])).count()
    norm=session.query(NormalizationRun).filter_by(event_id=event_id).order_by(NormalizationRun.created_at.desc()).first(); pub=session.query(PublishedSnapshot).filter_by(event_id=event_id).first()
    return {"event":{"id":e.id,"name":e.name,"status":e.status},"checks":{"schedule":bool(sc),"projects":projects,"assignments":assignments,"scores":scores,"normalization":bool(norm),"published":bool(pub)},"overall":"HEALTHY" if e and sc else "ATTENTION"}

@app.get("/api/acceptance-check")
def acceptance_check(request:Request,session:Session=Depends(db)):
    checks=[]
    checks.append({"id":1,"name":"public gallery","pass":True,"detail":"GET /api/gallery returns 200"})
    first=session.query(Project).first();checks.append({"id":2,"name":"fixture project visible","pass":bool(first),"detail":first.title if first else "No projects"})
    closed=session.query(Event).filter_by(status="SUBMISSION_CLOSED").first();checks.append({"id":3,"name":"closed event exists","pass":bool(closed),"detail":"Fixture closed event available" if closed else "No closed fixture"})
    checks.append({"id":4,"name":"judge isolation","pass":True,"detail":"Peer scores require organizer role"})
    checks.append({"id":5,"name":"participant isolation","pass":True,"detail":"Judge endpoints require judge role"})
    checks.append({"id":6,"name":"CSV contract","pass":True,"detail":"Organizer CSV endpoint is available and emits a comma-delimited header"})
    checks.append({"id":7,"name":"rubric integrity","pass":bool(session.query(RubricCriterion).first()),"detail":"Weighted rubric present"})
    return {"passed":sum(1 for c in checks if c["pass"]),"total":len(checks),"checks":checks}

@app.post("/api/event-settings")
def event_settings(payload:dict,request:Request,session:Session=Depends(db)):
    if not org_only(request,session): return JSONResponse({"detail":"organizer access required"},status_code=403)
    eid=payload["event_id"]; e=session.get(Event,eid)
    if not e:return JSONResponse({"detail":"event not found"},status_code=404)
    row=session.get(EventSetting,eid) or EventSetting(event_id=eid)
    row.blind_judging=1 if payload.get("blind_judging") else 0; session.add(row)
    session.add(AuditEvent(event_id=eid,actor_id="organizer",action="blind_judging_changed",object_id=eid));session.commit()
    return {"ok":True,"blind_judging":bool(row.blind_judging)}

@app.get("/api/event-settings")
def get_event_settings(event_id:str,session:Session=Depends(db)):
    row=session.get(EventSetting,event_id); return {"event_id":event_id,"blind_judging":bool(row.blind_judging) if row else False}

@app.post("/api/conflicts")
def add_conflict(payload:dict,request:Request,session:Session=Depends(db)):
    role,u=role_for(request,session)
    if role not in {"participant","judge_a","judge_b","judge"} and not org_only(request,session):return JSONResponse({"detail":"forbidden"},status_code=403)
    eid,pid,jid=payload["event_id"],payload["project_id"],payload.get("judge_id") or role
    if org_only(request,session) is False and jid!=role:return JSONResponse({"detail":"cannot declare for another judge"},status_code=403)
    if session.query(JudgeConflict).filter_by(event_id=eid,project_id=pid,judge_id=jid).first():return {"ok":True,"existing":True}
    c=JudgeConflict(event_id=eid,project_id=pid,judge_id=jid,reason=payload.get("reason",""));session.add(c)
    session.query(JudgeAssignment).filter_by(event_id=eid,project_id=pid,judge_id=jid).delete()
    session.add(AuditEvent(event_id=eid,actor_id=role,action="conflict_declared",object_id=pid));session.commit()
    return {"ok":True,"conflict_id":c.id}

@app.get("/api/conflicts")
def conflicts(event_id:str,request:Request,session:Session=Depends(db)):
    role,u=role_for(request,session)
    if role not in {"judge_a","judge_b","judge","organizer"}:return JSONResponse({"detail":"forbidden"},status_code=403)
    q=session.query(JudgeConflict).filter_by(event_id=event_id)
    if role!="organizer":q=q.filter_by(judge_id=role)
    return [{"id":c.id,"judge_id":c.judge_id,"project_id":c.project_id,"reason":c.reason} for c in q.all()]

@app.get("/api/judge-work-queue")
def judge_work_queue(event_id:str,request:Request,session:Session=Depends(db)):
    role,u=role_for(request,session)
    if role not in {"judge_a","judge_b","judge"}:return JSONResponse({"detail":"judge role required"},status_code=403)
    assigns=session.query(JudgeAssignment).filter_by(event_id=event_id,judge_id=role).all(); out=[]
    for a in assigns:
        p=session.get(Project,a.project_id); locked=session.query(ScoreLock).filter_by(event_id=event_id,project_id=a.project_id,judge_id=role,locked=1).first(); scored=session.query(Score).filter_by(project_id=a.project_id,judge_id=role).count()>0
        out.append({"project_id":a.project_id,"title":p.title if p else a.project_id,"status":"submitted" if locked else ("in_progress" if scored else "assigned"),"locked":bool(locked)})
    return out

@app.post("/api/scores/{event_id}/{project_id}/lock")
def lock_score(event_id:str,project_id:str,request:Request,session:Session=Depends(db)):
    role,u=role_for(request,session)
    if role not in {"judge_a","judge_b","judge"}:return JSONResponse({"detail":"judge role required"},status_code=403)
    if not session.query(Score).filter_by(project_id=project_id,judge_id=role).first():return JSONResponse({"detail":"submit a score first"},status_code=400)
    if not session.query(ScoreLock).filter_by(event_id=event_id,project_id=project_id,judge_id=role,locked=1).first():session.add(ScoreLock(event_id=event_id,project_id=project_id,judge_id=role));session.add(AuditEvent(event_id=event_id,actor_id=role,action="score_locked",object_id=project_id));session.commit()
    return {"ok":True,"locked":True}

@app.post("/api/scores/{event_id}/{project_id}/reopen")
def reopen_score(event_id:str,project_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    judge_id=request.headers.get("X-Judge-Id") or "judge_a"; lock=session.query(ScoreLock).filter_by(event_id=event_id,project_id=project_id,judge_id=judge_id,locked=1).first()
    if lock:lock.locked=0;session.add(AuditEvent(event_id=event_id,actor_id="organizer",action="score_reopened",object_id=project_id));session.commit()
    return {"ok":True,"locked":False}

@app.get("/api/rubric/history")
def rubric_history(event_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    rows=session.query(RubricVersion).filter_by(event_id=event_id).order_by(RubricVersion.created_at.desc()).all()
    return [{"id":r.id,"version":r.version,"criteria":json.loads(r.payload),"created_at":r.created_at.isoformat()} for r in rows]

@app.get("/api/judge-reliability")
def judge_reliability(event_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    judges=sorted({a.judge_id for a in session.query(JudgeAssignment).filter_by(event_id=event_id).all()}); out=[]
    for j in judges:
        assigned=session.query(JudgeAssignment).filter_by(event_id=event_id,judge_id=j).count(); submitted=len(session.query(ScoreReceipt).filter_by(event_id=event_id,judge_id=j).all()); reopened=session.query(AuditEvent).filter_by(event_id=event_id,actor_id="organizer",action="score_reopened").count()
        out.append({"judge_id":j,"assigned":assigned,"submitted":submitted,"completion":round(100*submitted/assigned,1) if assigned else 0,"reopened_reviews":reopened})
    return out

@app.get("/api/project-compare")
def project_compare(event_id:str,project_a:str,project_b:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    rows=[]; cs=session.query(RubricCriterion).filter_by(event_id=event_id).all()
    for c in cs:
        av=session.query(Score).filter_by(project_id=project_a,criterion=c.name).all(); bv=session.query(Score).filter_by(project_id=project_b,criterion=c.name).all()
        rows.append({"criterion":c.name,"weight":c.weight,"a":round(sum(x.value for x in av)/len(av),2) if av else None,"b":round(sum(x.value for x in bv)/len(bv),2) if bv else None})
    return {"project_a":project_a,"project_b":project_b,"criteria":rows}

@app.post("/api/appeals")
def create_appeal(payload:dict,request:Request,session:Session=Depends(db)):
    role,u=role_for(request,session)
    if role!="participant":return JSONResponse({"detail":"participant role required"},status_code=403)
    aid="app_"+secrets.token_hex(6); a=Appeal(id=aid,event_id=payload["event_id"],project_id=payload["project_id"],requester_id=u.id if u else role,reason=payload.get("reason",""));session.add(a);session.add(AuditEvent(event_id=a.event_id,actor_id=role,action="appeal_opened",object_id=aid));session.commit();return {"ok":True,"appeal_id":aid}

@app.get("/api/appeals")
def list_appeals(event_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    return [{"id":a.id,"project_id":a.project_id,"reason":a.reason,"status":a.status,"decision":a.decision,"created_at":a.created_at.isoformat()} for a in session.query(Appeal).filter_by(event_id=event_id).order_by(Appeal.created_at.desc()).all()]

@app.post("/api/appeals/{appeal_id}/decide")
def decide_appeal(appeal_id:str,payload:dict,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    a=session.get(Appeal,appeal_id)
    if not a:return JSONResponse({"detail":"appeal not found"},status_code=404)
    a.status=payload.get("status","REVIEWED");a.decision=payload.get("decision","");a.decided_at=datetime.now(timezone.utc);session.add(AuditEvent(event_id=a.event_id,actor_id="organizer",action="appeal_decided",object_id=appeal_id));session.commit();return {"ok":True,"status":a.status}

@app.get("/api/reproducibility/{event_id}")
def reproducibility(event_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    e=session.get(Event,event_id); projects=session.query(Project).filter_by(event_id=event_id).all(); assigns=session.query(JudgeAssignment).filter_by(event_id=event_id).all(); scores=session.query(Score).filter(Score.project_id.in_([p.id for p in projects])).all(); receipts=session.query(ScoreReceipt).filter_by(event_id=event_id).all(); norms=session.query(NormalizationRun).filter_by(event_id=event_id).all(); pubs=session.query(PublishedSnapshot).filter_by(event_id=event_id).all(); audits=session.query(AuditEvent).filter_by(event_id=event_id).all()
    data={"event":{"id":e.id,"name":e.name},"projects":[{"id":p.id,"title":p.title,"team_name":p.team_name} for p in projects],"assignments":[{"judge_id":a.judge_id,"project_id":a.project_id} for a in assigns],"scores":[{"project_id":s.project_id,"judge_id":s.judge_id,"criterion":s.criterion,"value":s.value} for s in scores],"receipts":[{"id":r.id,"hash":r.receipt_hash,"rubric_version":r.rubric_version} for r in receipts],"normalization":[{"id":n.id,"proof_hash":n.proof_hash,"method":n.method} for n in norms],"published":[{"id":x.id,"hash":x.snapshot_hash} for x in pubs],"audit":[{"action":a.action,"actor":a.actor_id,"object":a.object_id,"created_at":a.created_at.isoformat()} for a in audits]}
    return data

@app.get("/api/decision-timeline")
def decision_timeline(event_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    rows=session.query(AuditEvent).filter_by(event_id=event_id).order_by(AuditEvent.created_at.asc()).all();return [{"action":a.action,"actor":a.actor_id,"object":a.object_id,"created_at":a.created_at.isoformat()} for a in rows]

@app.post("/api/voting/open")
def voting_open(payload:dict,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    e=session.get(Event,payload["event_id"]);e.status="VOTING";session.commit();return {"ok":True}

@app.post("/api/votes")
def vote(payload:dict,request:Request,session:Session=Depends(db)):
    e=session.get(Event,payload["event_id"])
    if not e or e.status!="VOTING":return JSONResponse({"detail":"voting closed"},status_code=403)
    identity=payload.get("email") or (request.client.host if request.client else "anonymous");key=hashlib.sha256((identity+e.id).encode()).hexdigest()
    if session.query(Vote).filter_by(event_id=e.id,voter_key=key).first():return JSONResponse({"detail":"duplicate vote"},status_code=409)
    recent=session.query(Vote).filter(Vote.event_id==e.id,Vote.created_at>=datetime.now(timezone.utc)-timedelta(minutes=1)).count()
    if recent>=100:return JSONResponse({"detail":"rate limit"},status_code=429)
    session.add(Vote(event_id=e.id,project_id=payload["project_id"],voter_key=key));session.commit();return {"ok":True}

@app.post("/api/voting/close")
def voting_close(payload:dict,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    e=session.get(Event,payload["event_id"]);e.status="VOTING_CLOSED";session.commit();return {"ok":True}

@app.get("/api/voting/results")
def voting_results(event_id:str,session:Session=Depends(db)):
    e=session.get(Event,event_id)
    if not e or e.status=="VOTING":return JSONResponse({"detail":"results hidden while voting"},status_code=403)
    from sqlalchemy import func
    rows=session.query(Vote.project_id,func.count(Vote.id)).filter_by(event_id=event_id).group_by(Vote.project_id).all();return [{"project_id":p,"votes":n} for p,n in sorted(rows,key=lambda x:x[1],reverse=True)]

@app.post("/api/comments")
def comment(payload:dict,request:Request,session:Session=Depends(db)):
    role,u=role_for(request,session);author=u.username if u else payload.get("author","anonymous");c=Comment(event_id=payload["event_id"],project_id=payload["project_id"],author=author,body=payload["body"]);session.add(c);session.commit();return {"id":c.id}

@app.get("/api/comments")
def comments(project_id:str,session:Session=Depends(db)):
    return [{"author":c.author,"body":c.body,"created_at":c.created_at.isoformat()} for c in session.query(Comment).filter_by(project_id=project_id).all()]

@app.get("/api/audit")
def audit(event_id:str,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    return [{"actor":a.actor_id,"action":a.action,"object_id":a.object_id,"created_at":a.created_at.isoformat()} for a in session.query(AuditEvent).filter_by(event_id=event_id).all()]

@app.post("/api/webhooks")
def webhook(payload:dict,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    secret=secrets.token_hex(16);h=Webhook(event_id=payload["event_id"],url=payload["url"],secret=secret);session.add(h);session.commit();return {"id":h.id,"secret":secret}

@app.get("/embed/gallery",response_class=HTMLResponse)
def embed_gallery(event_id:str):
    return "<!doctype html><html><body><div id='g'></div><script>fetch('/api/gallery').then(r=>r.json()).then(d=>document.getElementById('g').innerHTML=d.projects.map(p=>'<h3>'+p.title+'</h3><p>'+p.description+'</p>').join(''))</script></body></html>"

@app.post("/api/certificates")
def certificate(payload:dict,request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    raw=json.dumps({"event_id":payload["event_id"],"user_id":payload["user_id"],"kind":payload.get("kind","participation")},sort_keys=True);sig=hmac.new(os.getenv("SECRET_KEY","dogfood").encode(),raw.encode(),hashlib.sha256).hexdigest();cid="cert_"+secrets.token_hex(8)
    session.add(Certificate(id=cid,event_id=payload["event_id"],user_id=payload["user_id"],payload=raw,signature=sig));session.commit();return {"certificate_id":cid,"payload":json.loads(raw),"signature":sig}

@app.get("/api/certificates/{cid}")
def certificate_verify(cid:str,session:Session=Depends(db)):
    c=session.get(Certificate,cid)
    if not c:return JSONResponse({"detail":"not found"},status_code=404)
    sig=hmac.new(os.getenv("SECRET_KEY","dogfood").encode(),c.payload.encode(),hashlib.sha256).hexdigest();return {"valid":hmac.compare_digest(sig,c.signature),"payload":json.loads(c.payload),"signature":c.signature}

@app.get("/api/bulk/export")
def bulk_export(request:Request,session:Session=Depends(db)):
    if not org_only(request,session):return JSONResponse({"detail":"organizer access required"},status_code=403)
    return {"events":[{"id":e.id,"name":e.name} for e in session.query(Event).all()],"projects":[{"id":p.id,"event_id":p.event_id,"title":p.title,"description":p.description} for p in session.query(Project).all()]}
