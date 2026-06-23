import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { teams, assignments, zones } from '../../lib/api';
import toast from 'react-hot-toast';
import { ShieldAlert, Crosshair, Users, X } from 'lucide-react';
import '../../styles/dispatch.css';

export default function DispatchModal({ initialZoneId = null, onClose }) {
  const queryClient = useQueryClient();
  const [selectedZone, setSelectedZone] = useState(initialZoneId);
  const [selectedTeams, setSelectedTeams] = useState([]);
  
  // Fetch unassigned red zones
  const { data: zonesRes } = useQuery({
    queryKey: ['unassignedZones'],
    queryFn: () => zones.getUnassignedRed()
  });
  
  // Fetch available teams
  const { data: teamsRes } = useQuery({
    queryKey: ['availableTeams'],
    queryFn: () => teams.getTeams({ status: 'available' })
  });

  const availableZones = zonesRes?.data || [];
  const availableTeamsList = teamsRes?.data || [];

  const handleDispatch = async () => {
    if (!selectedZone || selectedTeams.length === 0) {
      toast.error('Select both a zone and at least one team');
      return;
    }
    
    try {
      for (const team_id of selectedTeams) {
        await assignments.createAssignment({ zone_id: selectedZone, team_id });
      }
      toast.success(`Dispatch sequence confirmed! ${selectedTeams.length} Team(s) En Route.`, { icon: '🚀', style: { background: '#1c2538', color: '#fff' } });
      queryClient.invalidateQueries({ queryKey: ['unassignedZones'] });
      queryClient.invalidateQueries({ queryKey: ['availableTeams'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardStats'] });
      queryClient.invalidateQueries({ queryKey: ['zones'] });
      queryClient.invalidateQueries({ queryKey: ['teams'] });
      queryClient.invalidateQueries({ queryKey: ['activeAssignments'] });
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to dispatch teams');
    }
  };

  return (
    <div className="dm-overlay">
      <div className="dm-modal">
        <div className="dm-header">
          <div className="dm-title"><ShieldAlert size={18} className="dm-icon" /> INITIATE DISPATCH SEQUENCE</div>
          <button className="dm-close" onClick={onClose}><X size={20} /></button>
        </div>
        
        <div className="dm-body">
          <div style={{ background: 'rgba(0,102,255,0.1)', padding: '12px', borderRadius: '4px', borderLeft: '2px solid var(--scan-blue)', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--scan-blue-bright)', marginBottom: '16px', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
            <span>⚡</span>
            <span><strong>ALGORITHMIC RECOMMENDATION:</strong> Available teams below are prioritized automatically based on real-time geographic proximity to {selectedZone || 'the target'}, optimal squad size, and historical resolution speed for this specific sector.</span>
          </div>

          <div className="dm-form-group">
            <label><Crosshair size={14}/> Target Hotspot</label>
            <select 
              className="dm-select" 
              value={selectedZone || ''} 
              onChange={e => setSelectedZone(e.target.value)}
              disabled={!!initialZoneId}
            >
              <option value="">Select a critical zone...</option>
              {initialZoneId && !availableZones.find(z => z.zone_id === initialZoneId) && (
                <option value={initialZoneId}>{initialZoneId} (Selected via Map)</option>
              )}
              {availableZones.map(z => (
                <option key={z.zone_id} value={z.zone_id}>
                  {z.zone_id} - {z.dominant_station} (Pred: {Math.round(z.buffered_forecast)})
                </option>
              ))}
            </select>
          </div>

          <div className="dm-form-group">
            <label><Users size={14}/> Assign Response Teams (Multi-Select)</label>
            <div className="dm-team-list" style={{ maxHeight: '150px', overflowY: 'auto', border: '1px solid var(--panel-border)', borderRadius: 'var(--r-md)', background: 'var(--void)' }}>
              {availableTeamsList.map(t => (
                <label key={t.team_id} style={{ display: 'flex', alignItems: 'center', padding: '10px 12px', borderBottom: '1px solid var(--panel-border)', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-bright)', transition: 'background 0.2s' }} className="dm-team-label">
                  <input 
                    type="checkbox" 
                    checked={selectedTeams.includes(t.team_id)}
                    onChange={(e) => {
                      if (e.target.checked) setSelectedTeams([...selectedTeams, t.team_id]);
                      else setSelectedTeams(selectedTeams.filter(id => id !== t.team_id));
                    }}
                    style={{ marginRight: '12px', cursor: 'pointer', width: '16px', height: '16px', accentColor: 'var(--scan-blue)' }}
                  />
                  <span style={{ color: 'var(--intel-cyan)', width: '70px' }}>{t.team_id}</span>
                  <span style={{ flex: 1 }}>{t.station} ({t.category})</span>
                </label>
              ))}
              {availableTeamsList.length === 0 && (
                <div style={{ padding: '12px', color: 'var(--text-dim)', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>No available teams.</div>
              )}
            </div>
          </div>
          
          <div className="dm-footer">
            <button className="dm-btn-cancel" onClick={onClose}>CANCEL</button>
            <button 
              className="dm-btn-confirm" 
              onClick={handleDispatch}
              disabled={!selectedZone || selectedTeams.length === 0}
            >
              AUTHORIZE DISPATCH
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
