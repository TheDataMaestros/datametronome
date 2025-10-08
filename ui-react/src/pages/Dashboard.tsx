import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import Overview from './Overview';
import Staves from './Staves';
import Clefs from './Clefs';
import Reports from './Reports';
import { motion } from 'framer-motion';

const Dashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      {/* Main Content */}
      <div className="lg:pl-64">
        {/* Header */}
        <Header 
          user={user} 
          onLogout={logout}
          onMenuClick={() => setSidebarOpen(true)}
        />
        
        {/* Page Content */}
        <main className="py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <Routes>
                <Route path="/" element={<Navigate to="overview" replace />} />
                <Route path="overview" element={<Overview />} />
                <Route path="staves" element={<Staves />} />
                <Route path="clefs" element={<Clefs />} />
                <Route path="reports" element={<Reports />} />
              </Routes>
            </motion.div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default Dashboard;
