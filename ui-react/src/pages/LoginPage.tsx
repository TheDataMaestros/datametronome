import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { motion } from 'framer-motion';
import { Music, Database, Shield, TrendingUp } from 'lucide-react';

const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    const success = await login(username, password);
    
    if (!success) {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50 flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-600 to-secondary-600 p-12 flex-col justify-center relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-10 w-20 h-20 border-2 border-white rounded-full"></div>
          <div className="absolute top-32 right-20 w-16 h-16 border-2 border-white rounded-full"></div>
          <div className="absolute bottom-20 left-32 w-12 h-12 border-2 border-white rounded-full"></div>
          <div className="absolute bottom-40 right-10 w-24 h-24 border-2 border-white rounded-full"></div>
        </div>
        
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="relative z-10"
        >
          <div className="flex items-center mb-8">
            <Music className="w-12 h-12 text-white mr-4" />
            <h1 className="text-4xl font-bold text-white">DataMetronome</h1>
          </div>
          
          <h2 className="text-3xl font-semibold text-white mb-4">
            Your Data Quality Command Center
          </h2>
          
          <p className="text-xl text-primary-100 mb-8 leading-relaxed">
            Monitor, analyze, and ensure the quality of your data with beautiful visualizations 
            and intelligent anomaly detection.
          </p>
          
          <div className="space-y-4">
            <div className="flex items-center text-white">
              <Database className="w-6 h-6 mr-3 text-primary-200" />
              <span className="text-lg">Connect to any data source</span>
            </div>
            <div className="flex items-center text-white">
              <Shield className="w-6 h-6 mr-3 text-primary-200" />
              <span className="text-lg">Real-time quality monitoring</span>
            </div>
            <div className="flex items-center text-white">
              <TrendingUp className="w-6 h-6 mr-3 text-primary-200" />
              <span className="text-lg">Advanced analytics & insights</span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Right side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="w-full max-w-md"
        >
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center mb-8">
            <Music className="w-8 h-8 text-primary-600 mr-3" />
            <h1 className="text-2xl font-bold text-gray-900">DataMetronome</h1>
          </div>

          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-2">
              Welcome Back
            </h2>
            <p className="text-gray-600">
              Sign in to access your data quality dashboard
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input-field"
                placeholder="Enter your username"
                required
                disabled={isLoading}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field"
                placeholder="Enter your password"
                required
                disabled={isLoading}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-primary flex items-center justify-center py-3 text-lg font-semibold"
            >
              {isLoading ? (
                <>
                  <div className="loading-spinner mr-2"></div>
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div className="mt-8 text-center">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                <strong>Demo Credentials:</strong><br />
                Username: <code className="bg-blue-100 px-1 rounded">admin</code><br />
                Password: <code className="bg-blue-100 px-1 rounded">admin</code>
              </p>
            </div>
          </div>

          <div className="mt-8 text-center text-sm text-gray-500">
            <p>Make sure the Podium API is running on port 8001</p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default LoginPage;
