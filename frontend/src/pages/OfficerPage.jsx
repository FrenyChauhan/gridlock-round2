import React, { useState } from 'react';
import { LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import AssignmentCard from '../components/officer/AssignmentCard';
import StatusStepper from '../components/officer/StatusStepper';
import OutcomeSubmit from '../components/officer/OutcomeSubmit';
import '../styles/officer.css';

import { teams } from '../lib/api';
import toast from 'react-hot-toast';

export default function OfficerPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  // Use a real database team ID for the demo
  const [officerId] = useState('T-001');
  
  // States: standby -> assigned -> enroute -> on_site -> resolved -> standby
  const [assignmentStatus, setAssignmentStatus] = useState('standby'); 
  const [showOutcome, setShowOutcome] = useState(false);
  const [showFlash, setShowFlash] = useState(false);

  // Mock assignment
  const assignment = {
    tier: 'red',
    station: 'Koramangala',
    zone_id: 'KRM-12',
    predicted_violations: 450,
    time_band: 'MORNING',
    is_volatile: true
  };

  const handleCompleteTask = () => {
    setShowOutcome(true);
  };

  const handleBackup = async () => {
    try {
      await teams.updateTeamStatus(officerId, { current_status: 'needs_backup' });
      toast.error('Backup requested! Control room notified.', {
        style: { background: 'var(--panel-raised)', border: '1px solid var(--heat-red)', color: 'var(--text-bright)' },
        icon: '🚨'
      });
      setAssignmentStatus('needs_backup');
    } catch (err) {
      console.error("Failed to request backup", err);
    }
  };

  const handleSubmitOutcome = (data) => {
    setShowOutcome(false);
    setShowFlash(true);
    setTimeout(() => {
      setShowFlash(false);
      setAssignmentStatus('standby');
    }, 600);
  };

  // For testing UI flow easily:
  const triggerAssignment = () => {
    if (assignmentStatus === 'standby') setAssignmentStatus('assigned');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="officer-page-wrapper grid-bg">
      <div className="officer-mobile-container">
        
        {/* Header */}
        <div className="off-header">
          <div className="off-logo" onClick={triggerAssignment}>G2</div>
          <div className="off-id">{officerId}</div>
          <button className="off-logout" onClick={handleLogout}>
            <LogOut size={20} />
          </button>
        </div>

        {/* Content Area */}
        <div className="off-content">
          
          {assignmentStatus === 'standby' ? (
            <div className="off-standby">
              <div className="standby-radar"></div>
              <div className="off-st-title">STANDING BY</div>
              <div className="off-st-sub">Awaiting dispatch from command</div>
            </div>
          ) : (
            <>
              <AssignmentCard assignment={assignment} />
              
              <StatusStepper 
                status={assignmentStatus} 
                onUpdateStatus={setAssignmentStatus} 
                onCompleteTask={handleCompleteTask} 
                onBackup={handleBackup}
              />
            </>
          )}

        </div>

        {/* Overlays */}
        <AnimatePresence>
          {showOutcome && (
            <OutcomeSubmit onSubmit={handleSubmitOutcome} />
          )}
        </AnimatePresence>

        <AnimatePresence>
          {showFlash && (
            <motion.div 
              className="flash-overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            />
          )}
        </AnimatePresence>

      </div>
    </div>
  );
}
