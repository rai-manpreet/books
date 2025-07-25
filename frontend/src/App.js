import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUserInfo();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUserInfo = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user info:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      await fetchUserInfo();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Login failed' };
    }
  };

  const register = async (email, password, name) => {
    try {
      const response = await axios.post(`${API}/auth/register`, { email, password, name });
      const { access_token } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      await fetchUserInfo();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Registration failed' };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Components
const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <nav className="bg-blue-600 text-white p-4">
      <div className="container mx-auto flex justify-between items-center">
        <h1 className="text-2xl font-bold cursor-pointer" onClick={() => navigate('/')}>
          BookShelf
        </h1>
        <div className="flex items-center space-x-4">
          <span>Welcome, {user?.name}!</span>
          <button
            onClick={logout}
            className="bg-red-500 hover:bg-red-600 px-4 py-2 rounded"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
};

const LoginForm = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [name, setName] = useState('');
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    let result;
    if (isRegister) {
      result = await register(email, password, name);
    } else {
      result = await login(email, password);
    }

    if (!result.success) {
      setError(result.error);
    }
    
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            {isRegister ? 'Create Account' : 'Sign In'}
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm space-y-4">
            {isRegister && (
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Full Name"
                required
                className="appearance-none relative block w-full px-3 py-2 border border-gray-300 rounded-md placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            )}
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email address"
              required
              className="appearance-none relative block w-full px-3 py-2 border border-gray-300 rounded-md placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
              className="appearance-none relative block w-full px-3 py-2 border border-gray-300 rounded-md placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {error && (
            <div className="text-red-600 text-sm text-center">{error}</div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? 'Processing...' : (isRegister ? 'Register' : 'Sign In')}
            </button>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={() => setIsRegister(!isRegister)}
              className="text-blue-600 hover:text-blue-500"
            >
              {isRegister ? 'Already have an account? Sign in' : 'Need an account? Register'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const FileUpload = ({ onUpload }) => {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [category, setCategory] = useState('');
  const [tags, setTags] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Failed to fetch categories:', error);
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      if (!title) {
        setTitle(selectedFile.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !title) {
      setError('Please select a file and enter a title');
      return;
    }

    setUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    if (author) formData.append('author', author);
    if (category) formData.append('category', category);
    if (tags) formData.append('tags', tags);

    try {
      const response = await axios.post(`${API}/books/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      onUpload(response.data);
      setFile(null);
      setTitle('');
      setAuthor('');
      setCategory('');
      setTags('');
      setError('');
    } catch (error) {
      setError(error.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Upload New Book</h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select File (PDF or EPUB)
          </label>
          <input
            type="file"
            accept=".pdf,.epub"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            required
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Author (optional)
          </label>
          <input
            type="text"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Category (optional)
          </label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Select a category</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.name}>{cat.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tags (optional, comma-separated)
          </label>
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="fiction, mystery, thriller"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {error && (
          <div className="text-red-600 text-sm">{error}</div>
        )}

        <button
          type="submit"
          disabled={uploading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {uploading ? 'Uploading...' : 'Upload Book'}
        </button>
      </form>
    </div>
  );
};

const BookCard = ({ book, onRead, onDelete, onBookmark }) => {
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatReadingTime = (minutes) => {
    if (minutes === 0) return '0 min';
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-semibold truncate">{book.title}</h3>
        <div className="flex space-x-2">
          <button
            onClick={() => onBookmark(book.id, 1)}
            className="text-yellow-500 hover:text-yellow-600 text-sm"
            title="Bookmark"
          >
            ★
          </button>
          <button
            onClick={() => onDelete(book.id)}
            className="text-red-600 hover:text-red-800 text-sm"
            title="Delete"
          >
            ×
          </button>
        </div>
      </div>
      
      {book.author && (
        <p className="text-gray-600 text-sm mb-2">by {book.author}</p>
      )}
      
      {book.category && (
        <span className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full mb-2">
          {book.category}
        </span>
      )}
      
      {book.tags && book.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {book.tags.map((tag, index) => (
            <span key={index} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded">
              {tag}
            </span>
          ))}
        </div>
      )}
      
      <div className="text-xs text-gray-500 mb-3">
        <p>Format: {book.file_type === 'application/pdf' ? 'PDF' : 'EPUB'}</p>
        <p>Size: {formatFileSize(book.file_size)}</p>
        <p>Progress: {Math.round(book.reading_progress * 100)}%</p>
        <p>Reading Time: {formatReadingTime(book.reading_time || 0)}</p>
        {book.bookmarks && book.bookmarks.length > 0 && (
          <p>Bookmarks: {book.bookmarks.length}</p>
        )}
      </div>
      
      <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
        <div 
          className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
          style={{ width: `${book.reading_progress * 100}%` }}
        ></div>
      </div>
      
      <button
        onClick={() => onRead(book)}
        className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 transition-colors"
      >
        {book.reading_progress > 0 ? 'Continue Reading' : 'Start Reading'}
      </button>
    </div>
  );
};

const SearchAndFilter = ({ onSearch, onFilter }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedTags, setSelectedTags] = useState('');
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Failed to fetch categories:', error);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    onSearch(searchTerm);
  };

  const handleFilter = () => {
    onFilter({
      category: selectedCategory,
      tags: selectedTags
    });
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow-md mb-6">
      <div className="flex flex-wrap gap-4 items-end">
        <div className="flex-1 min-w-64">
          <form onSubmit={handleSearch} className="flex">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search books by title, author, or filename..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-l-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-r-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Search
            </button>
          </form>
        </div>
        
        <div className="flex gap-2">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">All Categories</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.name}>{cat.name}</option>
            ))}
          </select>
          
          <input
            type="text"
            value={selectedTags}
            onChange={(e) => setSelectedTags(e.target.value)}
            placeholder="Filter by tags..."
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
          
          <button
            onClick={handleFilter}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
          >
            Filter
          </button>
          
          <button
            onClick={() => {
              setSearchTerm('');
              setSelectedCategory('');
              setSelectedTags('');
              onSearch('');
              onFilter({});
            }}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Clear
          </button>
        </div>
      </div>
    </div>
  );
};

const ReadingStats = ({ stats }) => {
  if (!stats) return null;

  const completionRate = stats.total_books > 0 ? (stats.books_completed / stats.total_books * 100).toFixed(1) : 0;
  const avgReadingTime = stats.total_books > 0 ? Math.round(stats.total_reading_time / stats.total_books) : 0;

  return (
    <div className="bg-white p-6 rounded-lg shadow-md mb-6">
      <h3 className="text-lg font-semibold mb-4">Reading Statistics</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">{stats.total_books}</div>
          <div className="text-sm text-gray-600">Total Books</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{stats.books_completed}</div>
          <div className="text-sm text-gray-600">Completed</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-600">{Math.round(stats.total_reading_time / 60)}h</div>
          <div className="text-sm text-gray-600">Reading Time</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-orange-600">{stats.books_this_month}</div>
          <div className="text-sm text-gray-600">This Month</div>
        </div>
      </div>
      <div className="mt-4 flex justify-between text-sm text-gray-600">
        <span>Completion Rate: {completionRate}%</span>
        {stats.favorite_category && (
          <span>Favorite Category: {stats.favorite_category}</span>
        )}
      </div>
    </div>
  );
};

const PDFReader = ({ book, onClose, onProgressUpdate }) => {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadPDF = async () => {
      try {
        const response = await axios.get(`${API}/books/${book.id}/download`, {
          responseType: 'blob',
        });
        
        const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
        setPdfUrl(url);
        setLoading(false);
      } catch (error) {
        setError('Failed to load PDF');
        setLoading(false);
      }
    };

    loadPDF();
    
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [book.id]);

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
    const savedProgress = Math.round(book.reading_progress * numPages) || 1;
    setPageNumber(savedProgress);
  };

  const updateProgress = (currentPage) => {
    const progress = currentPage / numPages;
    onProgressUpdate(book.id, progress);
  };

  const goToPrevPage = () => {
    if (pageNumber > 1) {
      const newPage = pageNumber - 1;
      setPageNumber(newPage);
      updateProgress(newPage);
    }
  };

  const goToNextPage = () => {
    if (pageNumber < numPages) {
      const newPage = pageNumber + 1;
      setPageNumber(newPage);
      updateProgress(newPage);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white p-6 rounded-lg">
          <p>Loading PDF...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white p-6 rounded-lg">
          <p className="text-red-600">{error}</p>
          <button
            onClick={onClose}
            className="mt-4 bg-blue-600 text-white px-4 py-2 rounded"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50">
      <div className="bg-white h-full flex flex-col">
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-xl font-semibold">{book.title}</h2>
          <button
            onClick={onClose}
            className="text-gray-600 hover:text-gray-800 text-2xl"
          >
            ×
          </button>
        </div>
        
        <div className="flex-1 flex flex-col items-center justify-center p-4">
          {pdfUrl && (
            <iframe
              src={`${pdfUrl}#page=${pageNumber}`}
              width="100%"
              height="600"
              className="border rounded-lg"
              title="PDF Viewer"
            />
          )}
        </div>
        
        <div className="flex justify-between items-center p-4 border-t">
          <button
            onClick={goToPrevPage}
            disabled={pageNumber <= 1}
            className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
          >
            Previous
          </button>
          
          <div className="flex items-center space-x-2">
            <span>Page</span>
            <input
              type="number"
              value={pageNumber}
              onChange={(e) => {
                const page = parseInt(e.target.value);
                if (page >= 1 && page <= numPages) {
                  setPageNumber(page);
                  updateProgress(page);
                }
              }}
              className="w-16 px-2 py-1 border rounded text-center"
              min="1"
              max={numPages}
            />
            <span>of {numPages}</span>
          </div>
          
          <button
            onClick={goToNextPage}
            disabled={pageNumber >= numPages}
            className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};

const Dashboard = () => {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedBook, setSelectedBook] = useState(null);
  const [showUpload, setShowUpload] = useState(false);
  const [stats, setStats] = useState(null);
  const [searchParams, setSearchParams] = useState({});

  useEffect(() => {
    fetchBooks();
    fetchStats();
  }, []);

  const fetchBooks = async (search = '', filters = {}) => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (filters.category) params.append('category', filters.category);
      if (filters.tags) params.append('tags', filters.tags);
      
      const response = await axios.get(`${API}/books?${params.toString()}`);
      setBooks(response.data);
    } catch (error) {
      console.error('Failed to fetch books:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleSearch = (searchTerm) => {
    setSearchParams({ ...searchParams, search: searchTerm });
    fetchBooks(searchTerm, searchParams);
  };

  const handleFilter = (filters) => {
    setSearchParams({ ...searchParams, ...filters });
    fetchBooks(searchParams.search || '', { ...searchParams, ...filters });
  };

  const handleUpload = (newBook) => {
    setBooks([newBook, ...books]);
    setShowUpload(false);
    fetchStats(); // Refresh stats
  };

  const handleRead = (book) => {
    setSelectedBook(book);
  };

  const handleDelete = async (bookId) => {
    if (window.confirm('Are you sure you want to delete this book?')) {
      try {
        await axios.delete(`${API}/books/${bookId}`);
        setBooks(books.filter(book => book.id !== bookId));
        fetchStats(); // Refresh stats
      } catch (error) {
        console.error('Failed to delete book:', error);
      }
    }
  };

  const handleBookmark = async (bookId, pageNumber) => {
    try {
      await axios.post(`${API}/books/${bookId}/bookmark`, {
        book_id: bookId,
        page_number: pageNumber
      });
      
      // Refresh books to show updated bookmarks
      fetchBooks(searchParams.search || '', searchParams);
    } catch (error) {
      console.error('Failed to toggle bookmark:', error);
    }
  };

  const handleProgressUpdate = async (bookId, progress) => {
    try {
      await axios.put(`${API}/books/${bookId}/progress`, {
        book_id: bookId,
        progress: progress,
        reading_time: 1 // Add 1 minute of reading time
      });
      
      setBooks(books.map(book => 
        book.id === bookId ? { ...book, reading_progress: progress } : book
      ));
      
      // Refresh stats if book is completed
      if (progress >= 0.95) {
        fetchStats();
      }
    } catch (error) {
      console.error('Failed to update progress:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100">
        <Navbar />
        <div className="container mx-auto px-4 py-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading your library...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <h2 className="text-3xl font-bold">My Library</h2>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            {showUpload ? 'Cancel' : 'Upload Book'}
          </button>
        </div>

        <ReadingStats stats={stats} />

        <SearchAndFilter 
          onSearch={handleSearch}
          onFilter={handleFilter}
        />

        {showUpload && (
          <div className="mb-8">
            <FileUpload onUpload={handleUpload} />
          </div>
        )}

        {books.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-600 text-lg">
              {searchParams.search || searchParams.category || searchParams.tags 
                ? 'No books found matching your criteria' 
                : 'Your library is empty'}
            </p>
            <p className="text-gray-500">
              {searchParams.search || searchParams.category || searchParams.tags 
                ? 'Try adjusting your search or filters' 
                : 'Upload your first book to get started!'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {books.map(book => (
              <BookCard
                key={book.id}
                book={book}
                onRead={handleRead}
                onDelete={handleDelete}
                onBookmark={handleBookmark}
              />
            ))}
          </div>
        )}

        {selectedBook && (
          <PDFReader
            book={selectedBook}
            onClose={() => setSelectedBook(null)}
            onProgressUpdate={handleProgressUpdate}
          />
        )}
      </div>
    </div>
  );
};

const PrivateRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }
  
  return user ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<LoginForm />} />
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <Dashboard />
                </PrivateRoute>
              }
            />
          </Routes>
        </Router>
      </AuthProvider>
    </div>
  );
}

export default App;