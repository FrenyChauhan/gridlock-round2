import './styles/tokens.css';
import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import CommandPage from './pages/CommandPage';
import ZonesPage from './pages/ZonesPage';
import TeamsPage from './pages/TeamsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import OfficerPage from './pages/OfficerPage';
import { Toaster } from 'react-hot-toast';

const ProtectedRoute = ({ children, allowedRole }) => {
  const token = localStorage.getItem('gridlock_token');
  const role = localStorage.getItem('gridlock_role');
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRole === 'control_room' && role !== 'control_room' && role !== 'superadmin') {
    return <Navigate to="/officer" replace />;
  }
  
  if (allowedRole === 'officer' && role !== 'officer' && role !== 'control_room' && role !== 'superadmin') {
    return <Navigate to="/command" replace />;
  }

  return children;
};

export default function App() {
  const token = localStorage.getItem('gridlock_token');
  const role = localStorage.getItem('gridlock_role');

  return (
    <>
    <Routes>
      <Route path="/" element={
        token ? (role === 'officer' ? <Navigate to="/officer" replace /> : <Navigate to="/command" replace />) : <Navigate to="/login" replace />
      } />
      
      <Route path="/login" element={<LoginPage />} />

      {/* Control Room Routes */}
      <Route path="/command" element={
        <ProtectedRoute allowedRole="control_room">
          <CommandPage />
        </ProtectedRoute>
      } />
      
      <Route path="/zones" element={
        <ProtectedRoute allowedRole="control_room">
          <ZonesPage />
        </ProtectedRoute>
      } />
      
      <Route path="/teams" element={
        <ProtectedRoute allowedRole="control_room">
          <TeamsPage />
        </ProtectedRoute>
      } />

      <Route path="/analytics" element={
        <ProtectedRoute allowedRole="control_room">
          <AnalyticsPage />
        </ProtectedRoute>
      } />

      {/* Officer Routes */}
      <Route path="/officer" element={
        <ProtectedRoute allowedRole="officer">
          <OfficerPage />
        </ProtectedRoute>
      } />

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
    </>
  );
}
