import React, { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Check } from 'lucide-react';

export default function NotificationPanel({ notifications, unreadCount, markAllRead, markRead, onClose, onActionClick }) {
  const panelRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      // Don't close if clicking the bell button (which we assume has class ts-bell)
      if (event.target.closest('.ts-bell')) return;
      
      if (panelRef.current && !panelRef.current.contains(event.target)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  const getTimeAgo = (timestamp) => {
    const mins = Math.floor((Date.now() - timestamp) / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    return `${Math.floor(mins / 60)}h ago`;
  };

  const getDotColor = (type) => {
    switch(type) {
      case 'critical': return 'var(--heat-red)';
      case 'warning': return 'var(--heat-amber)';
      case 'info': return 'var(--scan-blue)';
      case 'success': return 'var(--safe-green)';
      default: return 'var(--text-mid)';
    }
  };

  return (
    <AnimatePresence>
      <motion.div 
        ref={panelRef}
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.15 }}
        style={{
          position: 'fixed',
          top: '56px',
          right: '16px',
          width: '360px',
          maxHeight: '480px',
          overflowY: 'auto',
          background: 'rgba(8,13,26,0.97)',
          backdropFilter: 'blur(20px)',
          border: '1px solid var(--panel-border-bright)',
          borderRadius: 'var(--r-lg)',
          boxShadow: 'var(--shadow-panel)',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--panel-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-bright)', letterSpacing: '0.5px' }}>ALERTS & NOTIFICATIONS</span>
            {unreadCount > 0 && (
              <span style={{ background: 'var(--heat-red)', color: '#fff', fontSize: '10px', padding: '2px 6px', borderRadius: '10px', fontWeight: 'bold' }}>{unreadCount}</span>
            )}
          </div>
          {unreadCount > 0 && (
            <button 
              onClick={markAllRead}
              style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', fontSize: '11px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
            >
              <Check size={12}/> Mark all read
            </button>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {notifications.length === 0 ? (
            <div style={{ padding: '40px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px' }}>
              <ShieldCheck size={32} color="var(--safe-green)" />
              <span style={{ color: 'var(--text-dim)', fontSize: '13px' }}>All clear · No active alerts</span>
            </div>
          ) : (
            notifications.map(n => (
              <div 
                key={n.id} 
                onClick={() => markRead(n.id)}
                style={{ 
                  padding: '16px', 
                  borderBottom: '1px solid var(--panel-border)',
                  background: n.read ? 'transparent' : 'rgba(255,255,255,0.03)',
                  display: 'flex',
                  gap: '12px',
                  cursor: 'pointer',
                  transition: 'background 0.2s'
                }}
                onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                onMouseOut={(e) => e.currentTarget.style.background = n.read ? 'transparent' : 'rgba(255,255,255,0.03)'}
              >
                <div style={{ paddingTop: '4px' }}>
                  <div style={{ 
                    width: '8px', height: '8px', borderRadius: '50%', 
                    background: getDotColor(n.type),
                    boxShadow: n.type === 'critical' ? `0 0 8px ${getDotColor(n.type)}` : 'none',
                    animation: n.type === 'critical' ? 'pulse 2s infinite' : 'none'
                  }} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: '13px', fontWeight: 500, color: n.read ? 'var(--text-dim)' : 'var(--text-bright)' }}>{n.title}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-dim)' }}>{getTimeAgo(n.timestamp)}</div>
                  </div>
                  <div style={{ fontFamily: 'var(--font-body)', fontSize: '12px', color: 'var(--text-mid)', marginBottom: n.action ? '12px' : '0' }}>{n.message}</div>
                  {n.action && (
                    <button 
                      onClick={(e) => { e.stopPropagation(); markRead(n.id); if(onActionClick) onActionClick(n); onClose(); }}
                      style={{ 
                        background: 'rgba(0,102,255,0.1)', border: '1px solid var(--scan-blue)', 
                        color: 'var(--scan-blue-bright)', padding: '4px 12px', borderRadius: '12px',
                        fontSize: '10px', fontWeight: 'bold', cursor: 'pointer'
                      }}
                    >
                      {n.action}
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
