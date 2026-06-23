import React, { useState } from 'react';

export default function ZoneTable({ zones, selectedZone, onSelect, isLoading }) {
  const [sortField, setSortField] = useState('buffered_forecast');
  const [sortAsc, setSortAsc] = useState(false);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const sortedZones = [...zones].sort((a, b) => {
    let valA = a[sortField];
    let valB = b[sortField];
    
    if (valA == null) valA = '';
    if (valB == null) valB = '';

    if (valA < valB) return sortAsc ? -1 : 1;
    if (valA > valB) return sortAsc ? 1 : -1;
    return 0;
  });

  const getTierColor = (tier) => {
    const t = tier?.toLowerCase();
    if (t === 'red') return 'red';
    if (t === 'amber') return 'amber';
    return 'green';
  };

  const getVolClass = (vol) => {
    if (vol === 'volatile_growing') return 'vol-vg';
    if (vol === 'volatile_stable') return 'vol-vs';
    if (vol === 'stable_growing') return 'vol-sg';
    return 'vol-sf';
  };

  return (
    <div className="zt-container">
      <table className="z-table">
        <thead className="zt-head">
          <tr>
            <th className="zt-th" onClick={() => handleSort('zone_id')}>ZONE {sortField === 'zone_id' && (sortAsc ? '↑' : '↓')}</th>
            <th className="zt-th" onClick={() => handleSort('dominant_station')}>STATION {sortField === 'dominant_station' && (sortAsc ? '↑' : '↓')}</th>
            <th className="zt-th" onClick={() => handleSort('time_band')}>TIME BAND {sortField === 'time_band' && (sortAsc ? '↑' : '↓')}</th>
            <th className="zt-th" onClick={() => handleSort('buffered_forecast')}>PREDICTED {sortField === 'buffered_forecast' && (sortAsc ? '↑' : '↓')}</th>
            <th className="zt-th" onClick={() => handleSort('cii_score')}>SCORE {sortField === 'cii_score' && (sortAsc ? '↑' : '↓')}</th>
            <th className="zt-th" onClick={() => handleSort('volatility_class')}>VOLATILITY {sortField === 'volatility_class' && (sortAsc ? '↑' : '↓')}</th>
            <th className="zt-th" onClick={() => handleSort('confidence_level')}>CONFIDENCE {sortField === 'confidence_level' && (sortAsc ? '↑' : '↓')}</th>
            <th className="zt-th" onClick={() => handleSort('assigned_team_id')}>TEAM {sortField === 'assigned_team_id' && (sortAsc ? '↑' : '↓')}</th>
            <th className="zt-th">STATUS</th>
          </tr>
        </thead>
        <tbody>
          {sortedZones.map((z, idx) => {
            const isSelected = selectedZone?.zone_id === z.zone_id;
            const tColor = getTierColor(z.tier);
            const scorePct = Math.min(100, Math.max(0, (z.cii_score || 0) * 100));

            return (
              <tr 
                key={z.zone_id} 
                className={`zt-tr ${isSelected ? 'selected' : ''}`}
                style={{ animationDelay: `${Math.min(idx * 20, 400)}ms` }}
                onClick={() => onSelect(z)}
              >
                <td className="zt-td ztd-zone">{z.zone_id}</td>
                <td className="zt-td ztd-station">{z.dominant_station}</td>
                <td className="zt-td ztd-zone" style={{textTransform:'uppercase'}}>{z.time_band?.replace('_', ' ')}</td>
                <td className="zt-td ztd-predicted">{Math.round(z.buffered_forecast || 0)}</td>
                <td className="zt-td">
                  <div className="ztd-score-wrap">
                    <span className="ztd-score-val">{z.cii_score ? parseFloat(z.cii_score).toFixed(2) : '0.0'}</span>
                    <div className="ztd-score-bar-bg">
                      <div className={`ztd-score-bar-fill ${tColor}`} style={{ width: `${scorePct}%` }}></div>
                    </div>
                  </div>
                </td>
                <td className="zt-td">
                  <span className={`ztd-volatility ${getVolClass(z.volatility_class)}`}>
                    {z.volatility_class?.replace('_', ' ')}
                  </span>
                </td>
                <td className="zt-td ztd-conf">● {z.confidence_level || 'HIGH'}</td>
                <td className="zt-td">
                  {z.assigned_team_id ? (
                    <span className="ztd-team assigned">{z.assigned_team_id}</span>
                  ) : (
                    <span className="ztd-team unassigned">—</span>
                  )}
                </td>
                <td className="zt-td">
                  {z.assigned_team_id ? (
                    <span className="ztd-status stat-as">ASSIGNED</span>
                  ) : (
                    <span className="ztd-status stat-un">UNASSIGNED</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
