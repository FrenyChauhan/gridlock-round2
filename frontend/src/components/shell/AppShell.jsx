import React from 'react';
import { useLocation } from 'react-router-dom';
import SideNav from './SideNav';
import TopStrip from './TopStrip';
import CommandAssistant from '../command/CommandAssistant';
import './AppShell.css';

export default function AppShell({ children }) {
  const location = useLocation();

  // Determine current page title
  let pageTitle = 'Dashboard';
  if (location.pathname.startsWith('/command')) pageTitle = 'Live Command';
  else if (location.pathname.startsWith('/zones')) pageTitle = 'Zone Intelligence';
  else if (location.pathname.startsWith('/teams')) pageTitle = 'Team Management';

  return (
    <div className="app-shell grid-bg">
      <TopStrip title={pageTitle} />
      <SideNav />
      <main className="main-content">
        <div style={{ width: '100%', height: '100%', position: 'relative', overflow: 'hidden' }}>
          {children}
        </div>
      </main>
      <CommandAssistant />
    </div>
  );
}
