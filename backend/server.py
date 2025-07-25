from fastapi import FastAPI, APIRouter, Depends, HTTPException, File, UploadFile, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timedelta
import hashlib
import aiofiles
import mimetypes
from passlib.context import CryptContext
from jose import JWTError, jwt
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create upload directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Create the main app
app = FastAPI(title="Books Management System")

# Create API router
api_router = APIRouter(prefix="/api")

# Pydantic Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class Book(BaseModel):
    id: str
    user_id: str
    title: str
    author: Optional[str] = None
    filename: str
    file_path: str
    file_type: str
    file_size: int
    upload_date: datetime
    reading_progress: float = 0.0
    category: Optional[str] = None
    tags: List[str] = []
    reading_time: int = 0  # in minutes
    bookmarks: List[int] = []  # page numbers
    cover_image: Optional[str] = None  # base64 encoded image

class BookResponse(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    filename: str
    file_type: str
    file_size: int
    upload_date: datetime
    reading_progress: float = 0.0
    category: Optional[str] = None
    tags: List[str] = []
    reading_time: int = 0
    bookmarks: List[int] = []
    cover_image: Optional[str] = None

class Category(BaseModel):
    id: str
    name: str
    color: str
    user_id: str
    book_count: int = 0

class ReadingStats(BaseModel):
    total_books: int
    books_completed: int
    total_reading_time: int
    current_streak: int
    books_this_month: int
    favorite_category: Optional[str] = None

class ReadingProgressUpdate(BaseModel):
    book_id: str
    progress: float

# Authentication helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"email": email})
    if user is None:
        raise credentials_exception
    return user

# Authentication endpoints
@api_router.post("/auth/register", response_model=Token)
async def register(user: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    user_data = {
        "id": str(uuid.uuid4()),
        "email": user.email,
        "name": user.name,
        "password_hash": hashed_password,
        "created_at": datetime.utcnow()
    }
    
    await db.users.insert_one(user_data)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.post("/auth/login", response_model=Token)
async def login(user: UserLogin):
    # Find user
    db_user = await db.users.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return User(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        created_at=current_user["created_at"]
    )

# Book management endpoints
@api_router.post("/books/upload", response_model=BookResponse)
async def upload_book(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    # Validate file type
    allowed_types = ["application/pdf", "application/epub+zip"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and EPUB files are allowed"
        )
    
    # Create unique filename
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{file_id}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Create book record
    book_data = {
        "id": file_id,
        "user_id": current_user["id"],
        "title": title,
        "author": author,
        "filename": file.filename,
        "file_path": str(file_path),
        "file_type": file.content_type,
        "file_size": len(content),
        "upload_date": datetime.utcnow(),
        "reading_progress": 0.0
    }
    
    await db.books.insert_one(book_data)
    
    return BookResponse(**book_data)

@api_router.get("/books", response_model=List[BookResponse])
async def get_books(current_user: dict = Depends(get_current_user)):
    books = await db.books.find({"user_id": current_user["id"]}).to_list(1000)
    return [BookResponse(**book) for book in books]

@api_router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: str, current_user: dict = Depends(get_current_user)):
    book = await db.books.find_one({"id": book_id, "user_id": current_user["id"]})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return BookResponse(**book)

@api_router.get("/books/{book_id}/download")
async def download_book(book_id: str, current_user: dict = Depends(get_current_user)):
    book = await db.books.find_one({"id": book_id, "user_id": current_user["id"]})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    file_path = Path(book["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=book["filename"],
        media_type=book["file_type"]
    )

@api_router.put("/books/{book_id}/progress")
async def update_reading_progress(
    book_id: str,
    progress_data: ReadingProgressUpdate,
    current_user: dict = Depends(get_current_user)
):
    book = await db.books.find_one({"id": book_id, "user_id": current_user["id"]})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    await db.books.update_one(
        {"id": book_id, "user_id": current_user["id"]},
        {"$set": {"reading_progress": progress_data.progress}}
    )
    
    return {"message": "Reading progress updated successfully"}

@api_router.delete("/books/{book_id}")
async def delete_book(book_id: str, current_user: dict = Depends(get_current_user)):
    book = await db.books.find_one({"id": book_id, "user_id": current_user["id"]})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Delete file from filesystem
    file_path = Path(book["file_path"])
    if file_path.exists():
        file_path.unlink()
    
    # Delete book record
    await db.books.delete_one({"id": book_id, "user_id": current_user["id"]})
    
    return {"message": "Book deleted successfully"}

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()