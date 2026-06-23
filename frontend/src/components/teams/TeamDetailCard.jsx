import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function TeamDetailCard({ team, onUpdate }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [newStatus, setNewStatus] = useState(team.status || 'available');

  const handleUpdate = (e) => {
    e.stopPropagation();
    if (onUpdate) onUpdate(team.team_id, newStatus);
  };

  const getStatusDisplay = (s) => {
    const map = {
      'available': { label: 'AVAILABLE', cls: 'tc-stat-available' },
      'assigned': { label: 'ASSIGNED', cls: 'tc-stat-assigned' },
      'enroute': { label: 'EN ROUTE', cls: 'tc-stat-assigned' },
      'on_site': { label: 'ON SITE', cls: 'tc-stat-onsite' },
      'standby': { label: 'STANDBY', cls: 'tc-stat-standby' },
      'off_duty': { label: 'OFF DUTY', cls: 'tc-stat-offduty' },
    };
    return map[s] || { label: s?.toUpperCase(), cls: 'tc-stat-offduty' };
  };

  const stat = getStatusDisplay(team.status);
  const isBusy = team.status === 'assigned' || team.status === 'enroute' || team.status === 'on_site';

  // Mock assignment history
  const history = [
    { zone: 'BTM-04', time: '08:14' },
    { zone: 'KRM-12', time: '11:32' },
  ];

  return (
    <motion.div 
      className="t-card"
      layout
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => setIsExpanded(!isExpanded)}
    >
      <div className="tc-top">
        <span className="tc-id">{team.team_id}</span>
        <span className={`tc-status ${stat.cls}`}>{stat.label}</span>
      </div>

      <div className="tc-mid">
        <span className="tc-station">{team.station || 'Central HQ'}</span>
        <span className="tc-cat">{team.category || 'PRIMARY'}</span>
      </div>

      {isBusy && (
        <div className="tc-assign">
          <span className="tc-zone">● {team.current_zone_id || 'Z-1234'}</span>
          <span className="tc-eta">
            ~{team.expected_free_at ? new Date(team.expected_free_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : '22 min remaining'}
          </span>
        </div>
      )}

      <AnimatePresence>
        {isHovered && !isExpanded && (
          <motion.div 
            className="tc-hover-actions"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            onClick={(e) => e.stopPropagation()}
          >
            <select className="tc-select" value={newStatus} onChange={e => setNewStatus(e.target.value)}>
              <option value="available">AVAILABLE</option>
              <option value="standby">STANDBY</option>
              <option value="off_duty">OFF DUTY</option>
            </select>
            <button className="tc-update-btn" onClick={handleUpdate}>UPDATE</button>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isExpanded && (
          <motion.div 
            className="tc-expanded"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <div style={{fontFamily:'var(--font-mono)', fontSize:'10px', color:'var(--text-dim)', marginBottom:'8px'}}>RECENT HISTORY</div>
            {history.map((h, i) => (
              <div key={i} className="tc-hist-item">
                <span>{h.zone}</span>
                <span>{h.time}</span>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
