#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Books Management System
Tests all authentication, book management, and progress tracking endpoints
"""

import requests
import json
import os
import tempfile
from pathlib import Path
import time

# Get backend URL from frontend .env file
def get_backend_url():
    frontend_env_path = Path("/app/frontend/.env")
    if frontend_env_path.exists():
        with open(frontend_env_path, 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    return "http://localhost:8001"

BASE_URL = get_backend_url() + "/api"
print(f"Testing backend at: {BASE_URL}")

class BookManagementTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.test_user_token = None
        self.test_user2_token = None
        self.test_book_id = None
        self.test_book_id2 = None  # For additional testing
        self.test_category_id = None
        self.timestamp = str(int(time.time()))  # Add timestamp as instance variable
        self.results = {
            "auth_tests": [],
            "book_upload_tests": [],
            "book_management_tests": [],
            "progress_tracking_tests": [],
            "user_isolation_tests": [],
            "search_tests": [],
            "category_tests": [],
            "bookmark_tests": [],
            "stats_tests": []
        }
    
    def log_test(self, category, test_name, success, message, details=None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.results[category].append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def create_test_pdf(self):
        """Create a simple test PDF file"""
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test Book Content) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
297
%%EOF"""
        return pdf_content
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        print("\n=== Testing User Registration ===")
        
        # Test valid registration
        import time
        timestamp = str(int(time.time()))
        user_data = {
            "email": f"alice.reader.{timestamp}@bookstore.com",
            "password": "SecurePass123!",
            "name": "Alice Reader"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/auth/register", json=user_data)
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "token_type" in data:
                    self.test_user_token = data["access_token"]
                    self.log_test("auth_tests", "Valid Registration", True, 
                                "User registered successfully with token")
                else:
                    self.log_test("auth_tests", "Valid Registration", False, 
                                "Missing token in response", {"response": data})
            else:
                self.log_test("auth_tests", "Valid Registration", False, 
                            f"Registration failed with status {response.status_code}", 
                            {"response": response.text})
        except Exception as e:
            self.log_test("auth_tests", "Valid Registration", False, 
                        f"Request failed: {str(e)}")
        
        # Test duplicate email registration
        try:
            response = self.session.post(f"{self.base_url}/auth/register", json=user_data)
            if response.status_code == 400:
                self.log_test("auth_tests", "Duplicate Email Validation", True, 
                            "Correctly rejected duplicate email")
            else:
                self.log_test("auth_tests", "Duplicate Email Validation", False, 
                            f"Should reject duplicate email, got status {response.status_code}")
        except Exception as e:
            self.log_test("auth_tests", "Duplicate Email Validation", False, 
                        f"Request failed: {str(e)}")
        
        # Register second user for isolation testing
        user2_data = {
            "email": f"bob.writer.{self.timestamp}@bookstore.com",
            "password": "AnotherPass456!",
            "name": "Bob Writer"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/auth/register", json=user2_data)
            if response.status_code == 200:
                data = response.json()
                self.test_user2_token = data["access_token"]
                self.log_test("auth_tests", "Second User Registration", True, 
                            "Second user registered for isolation testing")
            else:
                self.log_test("auth_tests", "Second User Registration", False, 
                            f"Failed to register second user: {response.status_code}")
        except Exception as e:
            self.log_test("auth_tests", "Second User Registration", False, 
                        f"Request failed: {str(e)}")
    
    def test_user_login(self):
        """Test user login endpoint"""
        print("\n=== Testing User Login ===")
        
        # Test valid login
        login_data = {
            "email": f"alice.reader.{self.timestamp}@bookstore.com",
            "password": "SecurePass123!"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.log_test("auth_tests", "Valid Login", True, 
                                "Login successful with token")
                else:
                    self.log_test("auth_tests", "Valid Login", False, 
                                "Missing token in login response")
            else:
                self.log_test("auth_tests", "Valid Login", False, 
                            f"Login failed with status {response.status_code}")
        except Exception as e:
            self.log_test("auth_tests", "Valid Login", False, 
                        f"Login request failed: {str(e)}")
        
        # Test invalid credentials
        invalid_login = {
            "email": "alice.reader@bookstore.com",
            "password": "WrongPassword"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/auth/login", json=invalid_login)
            if response.status_code == 401:
                self.log_test("auth_tests", "Invalid Credentials", True, 
                            "Correctly rejected invalid credentials")
            else:
                self.log_test("auth_tests", "Invalid Credentials", False, 
                            f"Should reject invalid credentials, got status {response.status_code}")
        except Exception as e:
            self.log_test("auth_tests", "Invalid Credentials", False, 
                        f"Request failed: {str(e)}")
    
    def test_protected_endpoint_access(self):
        """Test JWT token validation on protected endpoints"""
        print("\n=== Testing JWT Token Validation ===")
        
        # Test access without token
        try:
            response = self.session.get(f"{self.base_url}/auth/me")
            if response.status_code == 401:
                self.log_test("auth_tests", "No Token Access", True, 
                            "Correctly rejected request without token")
            else:
                self.log_test("auth_tests", "No Token Access", False, 
                            f"Should reject no token, got status {response.status_code}")
        except Exception as e:
            self.log_test("auth_tests", "No Token Access", False, 
                        f"Request failed: {str(e)}")
        
        # Test access with valid token
        if self.test_user_token:
            headers = {"Authorization": f"Bearer {self.test_user_token}"}
            try:
                response = self.session.get(f"{self.base_url}/auth/me", headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if "email" in data and data["email"] == "alice.reader@bookstore.com":
                        self.log_test("auth_tests", "Valid Token Access", True, 
                                    "Successfully accessed protected endpoint with valid token")
                    else:
                        self.log_test("auth_tests", "Valid Token Access", False, 
                                    "Token valid but wrong user data returned")
                else:
                    self.log_test("auth_tests", "Valid Token Access", False, 
                                f"Valid token rejected, status {response.status_code}")
            except Exception as e:
                self.log_test("auth_tests", "Valid Token Access", False, 
                            f"Request failed: {str(e)}")
        
        # Test access with invalid token
        headers = {"Authorization": "Bearer invalid_token_here"}
        try:
            response = self.session.get(f"{self.base_url}/auth/me", headers=headers)
            if response.status_code == 401:
                self.log_test("auth_tests", "Invalid Token Access", True, 
                            "Correctly rejected invalid token")
            else:
                self.log_test("auth_tests", "Invalid Token Access", False, 
                            f"Should reject invalid token, got status {response.status_code}")
        except Exception as e:
            self.log_test("auth_tests", "Invalid Token Access", False, 
                        f"Request failed: {str(e)}")
    
    def test_book_upload(self):
        """Test book upload functionality"""
        print("\n=== Testing Book Upload ===")
        
        if not self.test_user_token:
            self.log_test("book_upload_tests", "Book Upload", False, 
                        "No valid user token available for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Test valid PDF upload with categories and tags
        pdf_content = self.create_test_pdf()
        
        try:
            files = {
                'file': ('test_book.pdf', pdf_content, 'application/pdf')
            }
            data = {
                'title': 'The Art of Programming',
                'author': 'Jane Developer',
                'category': 'Programming',
                'tags': 'python,coding,tutorial'
            }
            
            response = self.session.post(f"{self.base_url}/books/upload", 
                                       files=files, data=data, headers=headers)
            
            if response.status_code == 200:
                book_data = response.json()
                if ("id" in book_data and "title" in book_data and 
                    book_data.get("category") == "Programming" and
                    "python" in book_data.get("tags", [])):
                    self.test_book_id = book_data["id"]
                    self.log_test("book_upload_tests", "Enhanced PDF Upload", True, 
                                "PDF uploaded successfully with category and tags")
                else:
                    self.log_test("book_upload_tests", "Enhanced PDF Upload", False, 
                                "Upload response missing category/tags data")
            else:
                self.log_test("book_upload_tests", "Enhanced PDF Upload", False, 
                            f"PDF upload failed with status {response.status_code}", 
                            {"response": response.text})
        except Exception as e:
            self.log_test("book_upload_tests", "Enhanced PDF Upload", False, 
                        f"Upload request failed: {str(e)}")
        
        # Upload second book for search testing
        try:
            files = {
                'file': ('advanced_algorithms.pdf', pdf_content, 'application/pdf')
            }
            data = {
                'title': 'Advanced Algorithms',
                'author': 'Dr. Computer Science',
                'category': 'Computer Science',
                'tags': 'algorithms,data-structures'
            }
            
            response = self.session.post(f"{self.base_url}/books/upload", 
                                       files=files, data=data, headers=headers)
            
            if response.status_code == 200:
                book_data = response.json()
                self.test_book_id2 = book_data["id"]
                self.log_test("book_upload_tests", "Second Book Upload", True, 
                            "Second book uploaded for search testing")
            else:
                self.log_test("book_upload_tests", "Second Book Upload", False, 
                            f"Second book upload failed with status {response.status_code}")
        except Exception as e:
            self.log_test("book_upload_tests", "Second Book Upload", False, 
                        f"Second upload request failed: {str(e)}")
        
        # Test invalid file type upload
        try:
            files = {
                'file': ('test.txt', b'This is a text file', 'text/plain')
            }
            data = {
                'title': 'Text File',
                'author': 'Test Author'
            }
            
            response = self.session.post(f"{self.base_url}/books/upload", 
                                       files=files, data=data, headers=headers)
            
            if response.status_code == 400:
                self.log_test("book_upload_tests", "Invalid File Type", True, 
                            "Correctly rejected non-PDF/EPUB file")
            else:
                self.log_test("book_upload_tests", "Invalid File Type", False, 
                            f"Should reject invalid file type, got status {response.status_code}")
        except Exception as e:
            self.log_test("book_upload_tests", "Invalid File Type", False, 
                        f"Request failed: {str(e)}")
        
        # Test upload without authentication
        try:
            files = {
                'file': ('test2.pdf', pdf_content, 'application/pdf')
            }
            data = {
                'title': 'Unauthorized Book',
                'author': 'No Auth'
            }
            
            response = self.session.post(f"{self.base_url}/books/upload", 
                                       files=files, data=data)
            
            if response.status_code == 401:
                self.log_test("book_upload_tests", "Unauthorized Upload", True, 
                            "Correctly rejected upload without authentication")
            else:
                self.log_test("book_upload_tests", "Unauthorized Upload", False, 
                            f"Should reject unauthorized upload, got status {response.status_code}")
        except Exception as e:
            self.log_test("book_upload_tests", "Unauthorized Upload", False, 
                        f"Request failed: {str(e)}")
    
    def test_book_management(self):
        """Test book CRUD operations"""
        print("\n=== Testing Book Management ===")
        
        if not self.test_user_token:
            self.log_test("book_management_tests", "Book Management", False, 
                        "No valid user token available for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Test get all books
        try:
            response = self.session.get(f"{self.base_url}/books", headers=headers)
            if response.status_code == 200:
                books = response.json()
                if isinstance(books, list):
                    self.log_test("book_management_tests", "Get All Books", True, 
                                f"Retrieved {len(books)} books")
                else:
                    self.log_test("book_management_tests", "Get All Books", False, 
                                "Response is not a list")
            else:
                self.log_test("book_management_tests", "Get All Books", False, 
                            f"Failed to get books, status {response.status_code}")
        except Exception as e:
            self.log_test("book_management_tests", "Get All Books", False, 
                        f"Request failed: {str(e)}")
        
        # Test get specific book
        if self.test_book_id:
            try:
                response = self.session.get(f"{self.base_url}/books/{self.test_book_id}", 
                                          headers=headers)
                if response.status_code == 200:
                    book = response.json()
                    if "id" in book and book["id"] == self.test_book_id:
                        self.log_test("book_management_tests", "Get Specific Book", True, 
                                    "Retrieved specific book successfully")
                    else:
                        self.log_test("book_management_tests", "Get Specific Book", False, 
                                    "Book ID mismatch in response")
                else:
                    self.log_test("book_management_tests", "Get Specific Book", False, 
                                f"Failed to get specific book, status {response.status_code}")
            except Exception as e:
                self.log_test("book_management_tests", "Get Specific Book", False, 
                            f"Request failed: {str(e)}")
        
        # Test get non-existent book
        try:
            fake_id = "non-existent-book-id"
            response = self.session.get(f"{self.base_url}/books/{fake_id}", headers=headers)
            if response.status_code == 404:
                self.log_test("book_management_tests", "Get Non-existent Book", True, 
                            "Correctly returned 404 for non-existent book")
            else:
                self.log_test("book_management_tests", "Get Non-existent Book", False, 
                            f"Should return 404, got status {response.status_code}")
        except Exception as e:
            self.log_test("book_management_tests", "Get Non-existent Book", False, 
                        f"Request failed: {str(e)}")
        
        # Test file download
        if self.test_book_id:
            try:
                response = self.session.get(f"{self.base_url}/books/{self.test_book_id}/download", 
                                          headers=headers)
                if response.status_code == 200:
                    if len(response.content) > 0:
                        self.log_test("book_management_tests", "File Download", True, 
                                    f"Downloaded file successfully ({len(response.content)} bytes)")
                    else:
                        self.log_test("book_management_tests", "File Download", False, 
                                    "Downloaded file is empty")
                else:
                    self.log_test("book_management_tests", "File Download", False, 
                                f"Download failed with status {response.status_code}")
            except Exception as e:
                self.log_test("book_management_tests", "File Download", False, 
                            f"Download request failed: {str(e)}")
    
    def test_reading_progress(self):
        """Test reading progress tracking"""
        print("\n=== Testing Reading Progress Tracking ===")
        
        if not self.test_user_token or not self.test_book_id:
            self.log_test("progress_tracking_tests", "Progress Tracking", False, 
                        "No valid user token or book ID available for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Test update reading progress
        progress_data = {
            "book_id": self.test_book_id,
            "progress": 0.35
        }
        
        try:
            response = self.session.put(f"{self.base_url}/books/{self.test_book_id}/progress", 
                                      json=progress_data, headers=headers)
            if response.status_code == 200:
                self.log_test("progress_tracking_tests", "Update Progress", True, 
                            "Reading progress updated successfully")
            else:
                self.log_test("progress_tracking_tests", "Update Progress", False, 
                            f"Progress update failed with status {response.status_code}")
        except Exception as e:
            self.log_test("progress_tracking_tests", "Update Progress", False, 
                        f"Progress update request failed: {str(e)}")
        
        # Test retrieve updated progress
        try:
            response = self.session.get(f"{self.base_url}/books/{self.test_book_id}", 
                                      headers=headers)
            if response.status_code == 200:
                book = response.json()
                if "reading_progress" in book and abs(book["reading_progress"] - 0.35) < 0.01:
                    self.log_test("progress_tracking_tests", "Retrieve Progress", True, 
                                "Reading progress persisted correctly")
                else:
                    self.log_test("progress_tracking_tests", "Retrieve Progress", False, 
                                f"Progress not persisted correctly, got {book.get('reading_progress', 'missing')}")
            else:
                self.log_test("progress_tracking_tests", "Retrieve Progress", False, 
                            f"Failed to retrieve book for progress check, status {response.status_code}")
        except Exception as e:
            self.log_test("progress_tracking_tests", "Retrieve Progress", False, 
                        f"Progress retrieval request failed: {str(e)}")
    
    def test_user_isolation(self):
        """Test that users can only access their own books"""
        print("\n=== Testing User Isolation ===")
        
        if not self.test_user2_token or not self.test_book_id:
            self.log_test("user_isolation_tests", "User Isolation", False, 
                        "Missing second user token or book ID for isolation testing")
            return
        
        headers2 = {"Authorization": f"Bearer {self.test_user2_token}"}
        
        # Test that user2 cannot access user1's book
        try:
            response = self.session.get(f"{self.base_url}/books/{self.test_book_id}", 
                                      headers=headers2)
            if response.status_code == 404:
                self.log_test("user_isolation_tests", "Book Access Isolation", True, 
                            "User correctly cannot access another user's book")
            else:
                self.log_test("user_isolation_tests", "Book Access Isolation", False, 
                            f"User should not access other's book, got status {response.status_code}")
        except Exception as e:
            self.log_test("user_isolation_tests", "Book Access Isolation", False, 
                        f"Request failed: {str(e)}")
        
        # Test that user2 cannot download user1's book
        try:
            response = self.session.get(f"{self.base_url}/books/{self.test_book_id}/download", 
                                      headers=headers2)
            if response.status_code == 404:
                self.log_test("user_isolation_tests", "Download Isolation", True, 
                            "User correctly cannot download another user's book")
            else:
                self.log_test("user_isolation_tests", "Download Isolation", False, 
                            f"User should not download other's book, got status {response.status_code}")
        except Exception as e:
            self.log_test("user_isolation_tests", "Download Isolation", False, 
                        f"Request failed: {str(e)}")
        
        # Test that user2's book list is empty (doesn't include user1's books)
        try:
            response = self.session.get(f"{self.base_url}/books", headers=headers2)
            if response.status_code == 200:
                books = response.json()
                if isinstance(books, list) and len(books) == 0:
                    self.log_test("user_isolation_tests", "Book List Isolation", True, 
                                "User2's book list correctly empty (no access to user1's books)")
                else:
                    self.log_test("user_isolation_tests", "Book List Isolation", False, 
                                f"User2 should have empty book list, got {len(books) if isinstance(books, list) else 'invalid'} books")
            else:
                self.log_test("user_isolation_tests", "Book List Isolation", False, 
                            f"Failed to get user2's book list, status {response.status_code}")
        except Exception as e:
            self.log_test("user_isolation_tests", "Book List Isolation", False, 
                        f"Request failed: {str(e)}")
    
    def test_search_functionality(self):
        """Test search functionality by title, author, filename"""
        print("\n=== Testing Search Functionality ===")
        
        if not self.test_user_token:
            self.log_test("search_tests", "Search Functionality", False, 
                        "No valid user token available for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Test search by title
        try:
            response = self.session.get(f"{self.base_url}/books?search=Programming", headers=headers)
            if response.status_code == 200:
                books = response.json()
                if isinstance(books, list) and len(books) > 0:
                    found_book = any("Programming" in book.get("title", "") for book in books)
                    if found_book:
                        self.log_test("search_tests", "Search by Title", True, 
                                    f"Found {len(books)} books matching title search")
                    else:
                        self.log_test("search_tests", "Search by Title", False, 
                                    "Search returned books but none match title")
                else:
                    self.log_test("search_tests", "Search by Title", False, 
                                "Search returned empty results")
            else:
                self.log_test("search_tests", "Search by Title", False, 
                            f"Search failed with status {response.status_code}")
        except Exception as e:
            self.log_test("search_tests", "Search by Title", False, 
                        f"Search request failed: {str(e)}")
        
        # Test search by author
        try:
            response = self.session.get(f"{self.base_url}/books?search=Jane", headers=headers)
            if response.status_code == 200:
                books = response.json()
                if isinstance(books, list) and len(books) > 0:
                    found_book = any("Jane" in book.get("author", "") for book in books)
                    if found_book:
                        self.log_test("search_tests", "Search by Author", True, 
                                    f"Found {len(books)} books matching author search")
                    else:
                        self.log_test("search_tests", "Search by Author", False, 
                                    "Search returned books but none match author")
                else:
                    self.log_test("search_tests", "Search by Author", False, 
                                "Author search returned empty results")
            else:
                self.log_test("search_tests", "Search by Author", False, 
                            f"Author search failed with status {response.status_code}")
        except Exception as e:
            self.log_test("search_tests", "Search by Author", False, 
                        f"Author search request failed: {str(e)}")
        
        # Test case-insensitive search
        try:
            response = self.session.get(f"{self.base_url}/books?search=programming", headers=headers)
            if response.status_code == 200:
                books = response.json()
                if isinstance(books, list) and len(books) > 0:
                    self.log_test("search_tests", "Case Insensitive Search", True, 
                                f"Case-insensitive search found {len(books)} books")
                else:
                    self.log_test("search_tests", "Case Insensitive Search", False, 
                                "Case-insensitive search returned empty results")
            else:
                self.log_test("search_tests", "Case Insensitive Search", False, 
                            f"Case-insensitive search failed with status {response.status_code}")
        except Exception as e:
            self.log_test("search_tests", "Case Insensitive Search", False, 
                        f"Case-insensitive search request failed: {str(e)}")
        
        # Test filter by category
        try:
            response = self.session.get(f"{self.base_url}/books?category=Programming", headers=headers)
            if response.status_code == 200:
                books = response.json()
                if isinstance(books, list):
                    category_match = all(book.get("category") == "Programming" for book in books)
                    if category_match:
                        self.log_test("search_tests", "Filter by Category", True, 
                                    f"Category filter returned {len(books)} matching books")
                    else:
                        self.log_test("search_tests", "Filter by Category", False, 
                                    "Category filter returned non-matching books")
                else:
                    self.log_test("search_tests", "Filter by Category", False, 
                                "Category filter response is not a list")
            else:
                self.log_test("search_tests", "Filter by Category", False, 
                            f"Category filter failed with status {response.status_code}")
        except Exception as e:
            self.log_test("search_tests", "Filter by Category", False, 
                        f"Category filter request failed: {str(e)}")
        
        # Test filter by tags
        try:
            response = self.session.get(f"{self.base_url}/books?tags=python", headers=headers)
            if response.status_code == 200:
                books = response.json()
                if isinstance(books, list):
                    tag_match = all("python" in book.get("tags", []) for book in books if book.get("tags"))
                    if len(books) > 0 and tag_match:
                        self.log_test("search_tests", "Filter by Tags", True, 
                                    f"Tag filter returned {len(books)} matching books")
                    elif len(books) == 0:
                        self.log_test("search_tests", "Filter by Tags", True, 
                                    "Tag filter returned no books (acceptable if no matches)")
                    else:
                        self.log_test("search_tests", "Filter by Tags", False, 
                                    "Tag filter returned non-matching books")
                else:
                    self.log_test("search_tests", "Filter by Tags", False, 
                                "Tag filter response is not a list")
            else:
                self.log_test("search_tests", "Filter by Tags", False, 
                            f"Tag filter failed with status {response.status_code}")
        except Exception as e:
            self.log_test("search_tests", "Filter by Tags", False, 
                        f"Tag filter request failed: {str(e)}")
    
    def test_categories_system(self):
        """Test categories CRUD operations"""
        print("\n=== Testing Categories System ===")
        
        if not self.test_user_token:
            self.log_test("category_tests", "Categories System", False, 
                        "No valid user token available for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Test create category
        try:
            category_data = {
                "name": "Science Fiction",
                "color": "#FF6B6B"
            }
            response = self.session.post(f"{self.base_url}/categories", 
                                       json=category_data, headers=headers)
            if response.status_code == 200:
                category = response.json()
                if "id" in category and category.get("name") == "Science Fiction":
                    self.test_category_id = category["id"]
                    self.log_test("category_tests", "Create Category", True, 
                                "Category created successfully")
                else:
                    self.log_test("category_tests", "Create Category", False, 
                                "Category response missing required fields")
            else:
                self.log_test("category_tests", "Create Category", False, 
                            f"Category creation failed with status {response.status_code}")
        except Exception as e:
            self.log_test("category_tests", "Create Category", False, 
                        f"Category creation request failed: {str(e)}")
        
        # Test get all categories
        try:
            response = self.session.get(f"{self.base_url}/categories", headers=headers)
            if response.status_code == 200:
                categories = response.json()
                if isinstance(categories, list):
                    self.log_test("category_tests", "Get Categories", True, 
                                f"Retrieved {len(categories)} categories")
                else:
                    self.log_test("category_tests", "Get Categories", False, 
                                "Categories response is not a list")
            else:
                self.log_test("category_tests", "Get Categories", False, 
                            f"Get categories failed with status {response.status_code}")
        except Exception as e:
            self.log_test("category_tests", "Get Categories", False, 
                        f"Get categories request failed: {str(e)}")
        
        # Test duplicate category creation
        try:
            duplicate_data = {
                "name": "Science Fiction",
                "color": "#00FF00"
            }
            response = self.session.post(f"{self.base_url}/categories", 
                                       json=duplicate_data, headers=headers)
            if response.status_code == 400:
                self.log_test("category_tests", "Duplicate Category Prevention", True, 
                            "Correctly prevented duplicate category creation")
            else:
                self.log_test("category_tests", "Duplicate Category Prevention", False, 
                            f"Should prevent duplicate category, got status {response.status_code}")
        except Exception as e:
            self.log_test("category_tests", "Duplicate Category Prevention", False, 
                        f"Duplicate category test failed: {str(e)}")
    
        # Test delete category
        if self.test_category_id:
            try:
                response = self.session.delete(f"{self.base_url}/categories/{self.test_category_id}", 
                                             headers=headers)
                if response.status_code == 200:
                    self.log_test("category_tests", "Delete Category", True, 
                                "Category deleted successfully")
                else:
                    self.log_test("category_tests", "Delete Category", False, 
                                f"Category deletion failed with status {response.status_code}")
            except Exception as e:
                self.log_test("category_tests", "Delete Category", False, 
                            f"Category deletion request failed: {str(e)}")
    
    def test_bookmarks_system(self):
        """Test bookmark toggle functionality"""
        print("\n=== Testing Bookmarks System ===")
        
        if not self.test_user_token or not self.test_book_id:
            self.log_test("bookmark_tests", "Bookmarks System", False, 
                        "No valid user token or book ID available for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Test add bookmark
        try:
            bookmark_data = {
                "book_id": self.test_book_id,
                "page_number": 25
            }
            response = self.session.post(f"{self.base_url}/books/{self.test_book_id}/bookmark", 
                                       json=bookmark_data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if "bookmarks" in result and 25 in result["bookmarks"]:
                    self.log_test("bookmark_tests", "Add Bookmark", True, 
                                "Bookmark added successfully")
                else:
                    self.log_test("bookmark_tests", "Add Bookmark", False, 
                                "Bookmark not found in response")
            else:
                self.log_test("bookmark_tests", "Add Bookmark", False, 
                            f"Add bookmark failed with status {response.status_code}")
        except Exception as e:
            self.log_test("bookmark_tests", "Add Bookmark", False, 
                        f"Add bookmark request failed: {str(e)}")
        
        # Test bookmark persistence
        try:
            response = self.session.get(f"{self.base_url}/books/{self.test_book_id}", headers=headers)
            if response.status_code == 200:
                book = response.json()
                if "bookmarks" in book and 25 in book["bookmarks"]:
                    self.log_test("bookmark_tests", "Bookmark Persistence", True, 
                                "Bookmark persisted correctly")
                else:
                    self.log_test("bookmark_tests", "Bookmark Persistence", False, 
                                "Bookmark not persisted")
            else:
                self.log_test("bookmark_tests", "Bookmark Persistence", False, 
                            f"Failed to retrieve book for bookmark check")
        except Exception as e:
            self.log_test("bookmark_tests", "Bookmark Persistence", False, 
                        f"Bookmark persistence check failed: {str(e)}")
        
        # Test remove bookmark (toggle)
        try:
            bookmark_data = {
                "book_id": self.test_book_id,
                "page_number": 25
            }
            response = self.session.post(f"{self.base_url}/books/{self.test_book_id}/bookmark", 
                                       json=bookmark_data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if "bookmarks" in result and 25 not in result["bookmarks"]:
                    self.log_test("bookmark_tests", "Remove Bookmark", True, 
                                "Bookmark removed successfully (toggle)")
                else:
                    self.log_test("bookmark_tests", "Remove Bookmark", False, 
                                "Bookmark not removed on toggle")
            else:
                self.log_test("bookmark_tests", "Remove Bookmark", False, 
                            f"Remove bookmark failed with status {response.status_code}")
        except Exception as e:
            self.log_test("bookmark_tests", "Remove Bookmark", False, 
                        f"Remove bookmark request failed: {str(e)}")
    
    def test_reading_statistics(self):
        """Test reading statistics endpoint"""
        print("\n=== Testing Reading Statistics ===")
        
        if not self.test_user_token:
            self.log_test("stats_tests", "Reading Statistics", False, 
                        "No valid user token available for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Test get reading statistics
        try:
            response = self.session.get(f"{self.base_url}/stats", headers=headers)
            if response.status_code == 200:
                stats = response.json()
                required_fields = ["total_books", "books_completed", "total_reading_time", 
                                 "current_streak", "books_this_month"]
                
                if all(field in stats for field in required_fields):
                    self.log_test("stats_tests", "Get Reading Stats", True, 
                                f"Statistics retrieved: {stats['total_books']} total books, "
                                f"{stats['books_completed']} completed")
                else:
                    missing_fields = [f for f in required_fields if f not in stats]
                    self.log_test("stats_tests", "Get Reading Stats", False, 
                                f"Missing required fields: {missing_fields}")
            else:
                self.log_test("stats_tests", "Get Reading Stats", False, 
                            f"Get stats failed with status {response.status_code}")
        except Exception as e:
            self.log_test("stats_tests", "Get Reading Stats", False, 
                        f"Get stats request failed: {str(e)}")
        
        # Test stats calculation accuracy
        try:
            # First get current stats
            response = self.session.get(f"{self.base_url}/stats", headers=headers)
            if response.status_code == 200:
                stats = response.json()
                
                # Get books count for verification
                books_response = self.session.get(f"{self.base_url}/books", headers=headers)
                if books_response.status_code == 200:
                    books = books_response.json()
                    actual_book_count = len(books)
                    
                    if stats["total_books"] == actual_book_count:
                        self.log_test("stats_tests", "Stats Calculation Accuracy", True, 
                                    f"Book count matches: {actual_book_count}")
                    else:
                        self.log_test("stats_tests", "Stats Calculation Accuracy", False, 
                                    f"Book count mismatch: stats={stats['total_books']}, actual={actual_book_count}")
                else:
                    self.log_test("stats_tests", "Stats Calculation Accuracy", False, 
                                "Could not retrieve books for verification")
            else:
                self.log_test("stats_tests", "Stats Calculation Accuracy", False, 
                            "Could not retrieve stats for accuracy check")
        except Exception as e:
            self.log_test("stats_tests", "Stats Calculation Accuracy", False, 
                        f"Stats accuracy check failed: {str(e)}")

    def test_enhanced_progress_tracking(self):
        """Test enhanced reading progress with reading time"""
        print("\n=== Testing Enhanced Progress Tracking ===")
        
        if not self.test_user_token or not self.test_book_id:
            self.log_test("progress_tracking_tests", "Enhanced Progress Tracking", False, 
                        "No valid user token or book ID available for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Test update reading progress with reading time
        progress_data = {
            "book_id": self.test_book_id,
            "progress": 0.65,
            "reading_time": 30,  # 30 minutes
            "current_page": 45
        }
        
        try:
            response = self.session.put(f"{self.base_url}/books/{self.test_book_id}/progress", 
                                      json=progress_data, headers=headers)
            if response.status_code == 200:
                self.log_test("progress_tracking_tests", "Enhanced Progress Update", True, 
                            "Reading progress with time updated successfully")
                
                # Verify the reading time was added
                book_response = self.session.get(f"{self.base_url}/books/{self.test_book_id}", 
                                               headers=headers)
                if book_response.status_code == 200:
                    book = book_response.json()
                    if (abs(book.get("reading_progress", 0) - 0.65) < 0.01 and 
                        book.get("reading_time", 0) >= 30):
                        self.log_test("progress_tracking_tests", "Reading Time Tracking", True, 
                                    f"Reading time tracked: {book.get('reading_time', 0)} minutes")
                    else:
                        self.log_test("progress_tracking_tests", "Reading Time Tracking", False, 
                                    f"Reading time not tracked correctly: {book.get('reading_time', 0)}")
                else:
                    self.log_test("progress_tracking_tests", "Reading Time Tracking", False, 
                                "Could not retrieve book to verify reading time")
            else:
                self.log_test("progress_tracking_tests", "Enhanced Progress Update", False, 
                            f"Enhanced progress update failed with status {response.status_code}")
        except Exception as e:
            self.log_test("progress_tracking_tests", "Enhanced Progress Update", False, 
                        f"Enhanced progress update request failed: {str(e)}")

    def test_book_deletion(self):
        """Test book deletion functionality"""
        print("\n=== Testing Book Deletion ===")
        
        if not self.test_user_token or not self.test_book_id:
            self.log_test("book_management_tests", "Book Deletion", False, 
                        "No valid user token or book ID available for deletion testing")
            return
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Test delete book
        try:
            response = self.session.delete(f"{self.base_url}/books/{self.test_book_id}", 
                                         headers=headers)
            if response.status_code == 200:
                self.log_test("book_management_tests", "Delete Book", True, 
                            "Book deleted successfully")
                
                # Verify book is actually deleted
                response = self.session.get(f"{self.base_url}/books/{self.test_book_id}", 
                                          headers=headers)
                if response.status_code == 404:
                    self.log_test("book_management_tests", "Verify Deletion", True, 
                                "Book correctly no longer accessible after deletion")
                else:
                    self.log_test("book_management_tests", "Verify Deletion", False, 
                                "Book still accessible after deletion")
            else:
                self.log_test("book_management_tests", "Delete Book", False, 
                            f"Book deletion failed with status {response.status_code}")
        except Exception as e:
            self.log_test("book_management_tests", "Delete Book", False, 
                        f"Deletion request failed: {str(e)}")
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Comprehensive Backend API Testing")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Run tests in logical order
        self.test_user_registration()
        self.test_user_login()
        self.test_protected_endpoint_access()
        self.test_book_upload()
        self.test_book_management()
        self.test_search_functionality()
        self.test_categories_system()
        self.test_enhanced_progress_tracking()
        self.test_bookmarks_system()
        self.test_reading_statistics()
        self.test_user_isolation()
        self.test_book_deletion()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.results.items():
            if tests:
                print(f"\n{category.replace('_', ' ').title()}:")
                for test in tests:
                    status = "✅" if test["success"] else "❌"
                    print(f"  {status} {test['test']}: {test['message']}")
                    total_tests += 1
                    if test["success"]:
                        passed_tests += 1
        
        print(f"\n📈 Overall Results: {passed_tests}/{total_tests} tests passed")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"📊 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 Excellent! Backend APIs are working well.")
        elif success_rate >= 70:
            print("⚠️  Good, but some issues need attention.")
        else:
            print("🚨 Critical issues found. Backend needs fixes.")

if __name__ == "__main__":
    tester = BookManagementTester()
    tester.run_all_tests()