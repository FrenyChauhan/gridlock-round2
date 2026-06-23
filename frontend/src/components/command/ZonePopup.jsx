import React from 'react';
import '../../styles/radar.css';
import { AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';

export default function ZonePopup({ zone, onClose, onDispatch }) {
  if (!zone) return null;

  const {
    zone_id, dominant_station, tier, buffered_forecast,
    cii_score, volatility_class, confidence_level, assigned_team_id
  } = zone;

  const tierLower = tier?.toLowerCase() || 'amber';
  const isVolatile = volatility_class === 'volatile_growing';

  return (
    <div className={`zone-popup-container tier-${tierLower}`}>
      <div className="zp-header">
        <span className="zp-id">{zone_id}</span>
        <span className={`zp-tier ${tierLower}`}>{tier?.toUpperCase()}</span>
      </div>
      
      <div className="zp-station">{dominant_station}</div>

      <div className="zp-grid">
        <div className="zp-data-point">
          <span className="zp-value">{Math.round(buffered_forecast || 0)}</span>
          <span className="zp-label">Predicted</span>
        </div>
        <div className="zp-data-point">
          <span className="zp-value">{cii_score ? parseFloat(cii_score).toFixed(2) : '0.00'}</span>
          <span className="zp-label">CII Score</span>
        </div>
        <div className="zp-data-point">
          <span className="zp-value" style={{ textTransform: 'capitalize' }}>{volatility_class?.replace('_', ' ')}</span>
          <span className="zp-label">Volatility</span>
        </div>
        <div className="zp-data-point">
          <span className="zp-value">{confidence_level || '--'}</span>
          <span className="zp-label">Confidence</span>
        </div>
      </div>

      {isVolatile && (
        <div className="zp-volatility-box">
          <AlertTriangle size={14} />
          <span>⚠ Growing hotspot · Buffer: +30%</span>
        </div>
      )}

      <div className="zp-bottom">
        {assigned_team_id ? (
          <div className="zp-status assigned">● {assigned_team_id} EN ROUTE</div>
        ) : (
          <div className="zp-status unassigned">UNPATROLLED</div>
        )}
        <button className="zp-btn" onClick={() => {
          if(onDispatch) onDispatch();
        }}>{assigned_team_id ? 'DISPATCH BACKUP →' : 'DISPATCH TEAM →'}</button>
      </div>
    </div>
  );
}
