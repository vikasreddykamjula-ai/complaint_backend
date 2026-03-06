import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.exc import IntegrityError

# Load environment variables from .env file
load_dotenv()

# 1. Database Configuration
# Get DATABASE_URL from environment variables (.env file or Render config)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please add it to your .env file.")

# Fix for Render: sqlalchemy requires 'mysql+pymysql' instead of just 'mysql'
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

# SSL Configuration for Aiven
connect_args = {}
if "aivencloud.com" in DATABASE_URL:
    connect_args = {"ssl": {"ssl_mode": "REQUIRED"}}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Database Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True)
    fullname = Column(String(100))
    age = Column(Integer)
    address = Column(String(255))
    email = Column(String(100))
    mobile = Column(String(15))
    password = Column(String(50))
    role = Column(String(10), default="user")

class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(100))
    description = Column(Text)
    status = Column(String(20), default="Pending")
    reply = Column(Text, nullable=True)

# Create tables in the cloud DB
Base.metadata.create_all(bind=engine)

# 3. FastAPI Setup
app = FastAPI(title="Online Complaint System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. Pydantic Schemas
class UserSignup(BaseModel):
    username: str
    fullname: str
    age: int
    address: str
    email: str
    mobile: str
    password: str

class UserUpdate(BaseModel):
    fullname: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    role: Optional[str] = None

class ComplaintCreate(BaseModel):
    user_id: int
    title: str
    description: str

class StatusUpdate(BaseModel):
    status: str

class ReplyRequest(BaseModel):
    reply: str

# 5. API Endpoints

@app.get("/")
def read_root():
    return {"status": "API is running successfully"}

@app.post("/signup")
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    try:
        new_user = User(**user_data.model_dump())
        db.add(new_user)
        db.commit()
        return {"message": "Signup successful"}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or Email already registered")

@app.post("/login")
def login(credentials: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == credentials.get('username')) | 
        (User.email == credentials.get('username'))
    ).first()
    if not user or user.password != credentials.get('password'):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "id": user.id, "username": user.username, "fullname": user.fullname, 
        "role": user.role, "email": user.email, "mobile": user.mobile
    }

@app.get("/admin/users")
def get_all_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.put("/admin/users/{u_id}")
def update_user(u_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == u_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    db.commit()
    return {"message": "User updated"}

@app.delete("/admin/users/{u_id}")
def delete_user(u_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == u_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.query(Complaint).filter(Complaint.user_id == u_id).delete()
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted"}

@app.post("/complaints")
def create_complaint(complaint: ComplaintCreate, db: Session = Depends(get_db)):
    db_complaint = Complaint(**complaint.model_dump())
    db.add(db_complaint)
    db.commit()
    return {"message": "Complaint submitted"}

@app.get("/admin/complaints")
def get_all_complaints(db: Session = Depends(get_db)):
    return db.query(Complaint).all()

@app.get("/user/complaints/{u_id}")
def get_user_complaints(u_id: int, db: Session = Depends(get_db)):
    return db.query(Complaint).filter(Complaint.user_id == u_id).all()

@app.put("/admin/complaints/{id}")
def update_complaint(id: int, update: StatusUpdate, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    complaint.status = update.status
    db.commit()
    return {"message": "Status updated"}

@app.post("/complaints/{id}/reply")
def reply_complaint(id: int, req: ReplyRequest, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    complaint.reply = req.reply
    db.commit()
    return {"message": "Reply saved"}

@app.delete("/complaints/{id}")
def delete_complaint(id: int, db: Session = Depends(get_db)):
    db.query(Complaint).filter(Complaint.id == id).delete()
    db.commit()
    return {"message": "Complaint deleted"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
