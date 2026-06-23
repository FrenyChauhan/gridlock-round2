import React from 'react';
import '../../styles/radar.css';

export default function CommandStrip({ stats, onOpenDispatch }) {
  const { total_red_zones, active_teams, unassigned_red_zones, available_teams } = stats;

  return (
    <div className="command-strip">
      <div className="cs-stats">
        <div className="cs-stat-block">
          <div className="cs-value red">{total_red_zones || 0}</div>
          <div className="cs-label">Red Zones</div>
        </div>
        <div className="cs-stat-block">
          <div className="cs-value cyan">{active_teams || 0}</div>
          <div className="cs-label">Teams Active</div>
        </div>
        <div className="cs-stat-block">
          <div className={`cs-value amber ${unassigned_red_zones > 0 ? 'blink' : ''}`}>
            {unassigned_red_zones || 0}
          </div>
          <div className="cs-label">Unassigned Critical</div>
        </div>
        <div className="cs-stat-block">
          <div className="cs-value green">{available_teams || 0}</div>
          <div className="cs-label">Available Teams</div>
        </div>
        <div className="cs-stat-block">
          <div className="cs-value gold">12</div>
          <div className="cs-label">Volatile Hotspots</div>
        </div>
      </div>
      
      <div className="cs-actions">
        <button className="cs-btn" onClick={onOpenDispatch}>ASSIGN PATROL</button>
      </div>
    </div>
  );
}
