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
    reading_time: Optional[int] = None  # additional minutes read
    current_page: Optional[int] = None

class BookmarkToggle(BaseModel):
    book_id: str
    page_number: int

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

class CategoryCreate(BaseModel):
    name: str
    color: str = "#3B82F6"

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
    category: str = Form(None),
    tags: str = Form(""),  # comma-separated tags
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
    
    # Process tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    
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
        "reading_progress": 0.0,
        "category": category,
        "tags": tag_list,
        "reading_time": 0,
        "bookmarks": [],
        "cover_image": None
    }
    
    await db.books.insert_one(book_data)
    
    # Update category book count
    if category:
        # Check if category exists, if not create it with proper fields
        existing_category = await db.categories.find_one({
            "name": category, 
            "user_id": current_user["id"]
        })
        
        if existing_category:
            # Category exists, just increment count
            await db.categories.update_one(
                {"name": category, "user_id": current_user["id"]},
                {"$inc": {"book_count": 1}}
            )
        else:
            # Category doesn't exist, create it with all required fields
            new_category = {
                "id": str(uuid.uuid4()),
                "name": category,
                "color": "#3B82F6",  # Default blue color
                "user_id": current_user["id"],
                "book_count": 1
            }
            await db.categories.insert_one(new_category)
    
    return BookResponse(**book_data)

@api_router.get("/books", response_model=List[BookResponse])
async def get_books(
    search: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    # Build query
    query = {"user_id": current_user["id"]}
    
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"author": {"$regex": search, "$options": "i"}},
            {"filename": {"$regex": search, "$options": "i"}}
        ]
    
    if category:
        query["category"] = category
    
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        query["tags"] = {"$in": tag_list}
    
    books = await db.books.find(query).sort("upload_date", -1).to_list(1000)
    return [BookResponse(**book) for book in books]

@api_router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: str, current_user: dict = Depends(get_current_user)):
    book = await db.books.find_one({"id": book_id, "user_id": current_user["id"]})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return BookResponse(**book)

@api_router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: str,
    book_update: BookUpdate,
    current_user: dict = Depends(get_current_user)
):
    book = await db.books.find_one({"id": book_id, "user_id": current_user["id"]})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Prepare update data
    update_data = {}
    if book_update.title:
        update_data["title"] = book_update.title
    if book_update.author:
        update_data["author"] = book_update.author
    if book_update.category:
        update_data["category"] = book_update.category
    if book_update.tags is not None:
        update_data["tags"] = book_update.tags
    
    if update_data:
        await db.books.update_one(
            {"id": book_id, "user_id": current_user["id"]},
            {"$set": update_data}
        )
    
    # Get updated book
    updated_book = await db.books.find_one({"id": book_id, "user_id": current_user["id"]})
    return BookResponse(**updated_book)

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
    
    update_data = {"reading_progress": progress_data.progress}
    
    if progress_data.reading_time:
        current_time = book.get("reading_time", 0)
        update_data["reading_time"] = current_time + progress_data.reading_time
    
    await db.books.update_one(
        {"id": book_id, "user_id": current_user["id"]},
        {"$set": update_data}
    )
    
    return {"message": "Reading progress updated successfully"}

@api_router.post("/books/{book_id}/bookmark")
async def toggle_bookmark(
    book_id: str,
    bookmark_data: BookmarkToggle,
    current_user: dict = Depends(get_current_user)
):
    book = await db.books.find_one({"id": book_id, "user_id": current_user["id"]})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    bookmarks = book.get("bookmarks", [])
    page_number = bookmark_data.page_number
    
    if page_number in bookmarks:
        bookmarks.remove(page_number)
        action = "removed"
    else:
        bookmarks.append(page_number)
        action = "added"
    
    await db.books.update_one(
        {"id": book_id, "user_id": current_user["id"]},
        {"$set": {"bookmarks": bookmarks}}
    )
    
    return {"message": f"Bookmark {action} successfully", "bookmarks": bookmarks}

@api_router.delete("/books/{book_id}")
async def delete_book(book_id: str, current_user: dict = Depends(get_current_user)):
    book = await db.books.find_one({"id": book_id, "user_id": current_user["id"]})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Delete file from filesystem
    file_path = Path(book["file_path"])
    if file_path.exists():
        file_path.unlink()
    
    # Update category book count
    if book.get("category"):
        await db.categories.update_one(
            {"name": book["category"], "user_id": current_user["id"]},
            {"$inc": {"book_count": -1}}
        )
    
    # Delete book record
    await db.books.delete_one({"id": book_id, "user_id": current_user["id"]})
    
    return {"message": "Book deleted successfully"}

# Category management endpoints
@api_router.post("/categories", response_model=Category)
async def create_category(
    category_data: CategoryCreate,
    current_user: dict = Depends(get_current_user)
):
    # Check if category already exists
    existing = await db.categories.find_one({
        "name": category_data.name,
        "user_id": current_user["id"]
    })
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    category = {
        "id": str(uuid.uuid4()),
        "name": category_data.name,
        "color": category_data.color,
        "user_id": current_user["id"],
        "book_count": 0
    }
    
    await db.categories.insert_one(category)
    return Category(**category)

@api_router.get("/categories", response_model=List[Category])
async def get_categories(current_user: dict = Depends(get_current_user)):
    categories = await db.categories.find({"user_id": current_user["id"]}).to_list(1000)
    return [Category(**category) for category in categories]

@api_router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    current_user: dict = Depends(get_current_user)
):
    category = await db.categories.find_one({"id": category_id, "user_id": current_user["id"]})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Remove category from books
    await db.books.update_many(
        {"category": category["name"], "user_id": current_user["id"]},
        {"$unset": {"category": ""}}
    )
    
    # Delete category
    await db.categories.delete_one({"id": category_id, "user_id": current_user["id"]})
    
    return {"message": "Category deleted successfully"}

# Statistics endpoint
@api_router.get("/stats", response_model=ReadingStats)
async def get_reading_stats(current_user: dict = Depends(get_current_user)):
    books = await db.books.find({"user_id": current_user["id"]}).to_list(1000)
    
    total_books = len(books)
    books_completed = len([book for book in books if book.get("reading_progress", 0) >= 0.95])
    total_reading_time = sum(book.get("reading_time", 0) for book in books)
    
    # Calculate current month books
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    books_this_month = len([
        book for book in books 
        if book["upload_date"].month == current_month and book["upload_date"].year == current_year
    ])
    
    # Find favorite category
    categories = {}
    for book in books:
        if book.get("category"):
            categories[book["category"]] = categories.get(book["category"], 0) + 1
    
    favorite_category = max(categories, key=categories.get) if categories else None
    
    return ReadingStats(
        total_books=total_books,
        books_completed=books_completed,
        total_reading_time=total_reading_time,
        current_streak=0,  # Simple implementation
        books_this_month=books_this_month,
        favorite_category=favorite_category
    )

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