import React, { useState, useEffect } from 'react';
import { Bell } from 'lucide-react';
import { jwtDecode } from 'jwt-decode';
import toast from 'react-hot-toast';
import NotificationPanel from './NotificationPanel';
import { useNotifications } from '../../hooks/useNotifications';
import ShiftReport from '../dashboard/ShiftReport';
import { useNavigate } from 'react-router-dom';

export default function TopStrip({ title }) {
  const [time, setTime] = useState(new Date());
  const navigate = useNavigate();

  // Get user info from token
  const token = localStorage.getItem('token');
  let user = { region: 'CENTRAL', email: 'U' };
  if (token) {
    try {
      const decoded = jwtDecode(token);
      if (decoded.region) user.region = decoded.region;
      if (decoded.email) user.email = decoded.email;
    } catch(e) {}
  }

  // Live clock
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const timeString = time.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false });
  const dateString = time.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric' });

  const initials = user.email ? user.email.substring(0, 2).toUpperCase() : 'CR';

  const { notifications, unreadCount, markAllRead, markRead } = useNotifications();
  const [showPanel, setShowPanel] = useState(false);
  const [showReport, setShowReport] = useState(false);

  const handleActionClick = (n) => {
    if (n.action === 'ASSIGN NOW' || n.action === 'DISPATCH' || n.action === 'PRE-ASSIGN') {
      navigate('/command');
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('openDispatchModal', { detail: { zoneId: n.zone_id, teamId: n.team_id } }));
      }, 100);
    } else if (n.action === 'VIEW') {
      navigate('/command');
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('selectZone', { detail: { zoneId: n.zone_id } }));
      }, 100);
    }
  };

  return (
    <header className="top-strip">
      <div className="ts-left">
        <span className="ts-title">{title}</span>
        <span className="ts-breadcrumb">/</span>
        <span className="ts-region">{user.region} REGION</span>
      </div>

      <div className="ts-center">
        <div className="ts-clock">{timeString}</div>
        <div className="ts-date">{dateString}</div>
      </div>

      <div className="ts-right">
        <div className="ts-shift">
          <div className="ts-dot"></div>
          SHIFT ACTIVE
        </div>

        <button onClick={() => setShowReport(true)} style={{ background: 'var(--panel-raised)', border: '1px solid var(--panel-border-bright)', color: 'var(--scan-blue-bright)', fontFamily: 'var(--font-mono)', fontSize: '10px', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', marginLeft: '12px', fontWeight: 'bold' }}>
          SHIFT REPORT
        </button>
        
        <button className="ts-bell" onClick={(e) => { e.stopPropagation(); setShowPanel(!showPanel); }}>
          <Bell size={20} />
          {unreadCount > 0 && <span className="ts-badge">{unreadCount}</span>}
        </button>
        {showPanel && (
          <NotificationPanel 
            notifications={notifications}
            unreadCount={unreadCount}
            markAllRead={markAllRead}
            markRead={markRead}
            onClose={() => setShowPanel(false)}
            onActionClick={handleActionClick}
          />
        )}

        <div className="ts-avatar">{initials}</div>
      </div>
      
      {showReport && <ShiftReport onClose={() => setShowReport(false)} />}
    </header>
  );
}
