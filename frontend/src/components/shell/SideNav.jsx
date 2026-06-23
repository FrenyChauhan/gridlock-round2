import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Radio, Map, Users, BarChart2, LogOut } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

export default function SideNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname.startsWith(path);

  return (
    <aside className="side-nav">
      <div className="sn-logo" onClick={() => navigate('/command')}>G2</div>

      <button 
        className={`sn-item ${isActive('/command') ? 'active' : ''}`}
        onClick={() => navigate('/command')}
        data-tooltip="Live Command"
      >
        <Radio size={24} />
      </button>

      <button 
        className={`sn-item ${isActive('/zones') ? 'active' : ''}`}
        onClick={() => navigate('/zones')}
        data-tooltip="Zone Intelligence"
      >
        <Map size={24} />
      </button>

      <button 
        className={`sn-item ${isActive('/teams') ? 'active' : ''}`}
        onClick={() => navigate('/teams')}
        data-tooltip="Team Management"
      >
        <Users size={24} />
      </button>

      <button 
        className={`sn-item ${isActive('/analytics') ? 'active' : ''}`}
        onClick={() => navigate('/analytics')}
        data-tooltip="Analytics"
      >
        <BarChart2 size={24} />
      </button>

      <div className="sn-separator"></div>

      <div className="sn-bottom">
        <button className="sn-item" onClick={handleLogout} data-tooltip="Logout">
          <LogOut size={22} />
        </button>
      </div>
    </aside>
  );
}
