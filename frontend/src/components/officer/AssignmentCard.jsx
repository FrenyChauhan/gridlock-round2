import React from 'react';
import { ExternalLink } from 'lucide-react';

export default function AssignmentCard({ assignment }) {
  if (!assignment) return null;

  const { tier, station, zone_id, predicted_violations, time_band, is_volatile } = assignment;
  const tColor = tier?.toLowerCase() || 'amber';

  return (
    <div className={`assign-card tier-${tColor}`}>
      <div className={`ac-badge ${tColor}`}>
        {tColor === 'red' ? '● CRITICAL ZONE' : '● PRIORITY ZONE'}
      </div>

      <div className="ac-station">{station}</div>
      <div className="ac-zone">ZONE ID: {zone_id}</div>

      <div className="ac-data">
        Predicted {Math.round(predicted_violations)} violations · {time_band?.replace('_', ' ')}
      </div>

      {is_volatile && (
        <div className="ac-volatility">
          Volatile zone · Stay alert · Extra backup may be needed
        </div>
      )}

      {/* Lat/Lon mapping could be dynamic */}
      <a 
        href={`https://maps.google.com?q=12.9716,77.5946`} 
        target="_blank" 
        rel="noopener noreferrer" 
        className="ac-nav-btn"
      >
        <ExternalLink size={18} />
        OPEN IN MAPS
      </a>
    </div>
  );
}
