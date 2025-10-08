import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';

interface User {
  username: string;
  email?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  isLoading: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001';

// Configure axios defaults
axios.defaults.baseURL = `${API_BASE_URL}/api/v1`;
axios.defaults.timeout = 10000;

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for stored token on app load
    const storedToken = localStorage.getItem('datametronome_token');
    const storedUser = localStorage.getItem('datametronome_user');
    
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      // Set axios default header
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
    }
    
    setIsLoading(false);
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      
      const response = await axios.post('/auth/login', {
        username,
        password,
      });

      const { access_token } = response.data;
      
      if (access_token) {
        setToken(access_token);
        setUser({ username });
        
        // Store in localStorage
        localStorage.setItem('datametronome_token', access_token);
        localStorage.setItem('datametronome_user', JSON.stringify({ username }));
        
        // Set axios default header
        axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        
        toast.success(`Welcome back, ${username}!`);
        return true;
      }
      
      return false;
    } catch (error: any) {
      console.error('Login error:', error);
      
      if (error.response?.status === 401) {
        toast.error('Invalid username or password');
      } else if (error.response?.status === 404) {
        toast.error('API server not found. Please check if the Podium API is running.');
      } else if (error.code === 'ECONNREFUSED') {
        toast.error('Cannot connect to API server. Please ensure the Podium API is running on port 8001.');
      } else {
        toast.error('Login failed. Please try again.');
      }
      
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    
    // Clear localStorage
    localStorage.removeItem('datametronome_token');
    localStorage.removeItem('datametronome_user');
    
    // Remove axios default header
    delete axios.defaults.headers.common['Authorization'];
    
    toast.success('Logged out successfully');
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    logout,
    isLoading,
    isAuthenticated: !!token && !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
