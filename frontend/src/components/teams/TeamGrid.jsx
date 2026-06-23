import React, { useState } from 'react';
import { Plus } from 'lucide-react';
import TeamDetailCard from './TeamDetailCard';
import AddTeamModal from './AddTeamModal';
import { teams } from '../../lib/api';

export default function TeamGrid({ teamData, refetch }) {
  const [showModal, setShowModal] = useState(false);
  const [filterStat, setFilterStat] = useState('ALL');
  const [filterCat, setFilterCat] = useState('ALL');
  const [filterStation, setFilterStation] = useState('ALL');

  const handleUpdateStatus = async (id, status) => {
    try {
      await teams.updateTeamStatus(id, { current_status: status });
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  const filtered = teamData.filter(t => {
    if (filterStat !== 'ALL') {
      let match = filterStat.toLowerCase();
      if (filterStat === 'ON SITE') match = 'on_site';
      if (filterStat === 'DEPLOYED') match = 'assigned';
      if (t.status !== match) return false;
    }
    if (filterCat !== 'ALL' && t.category?.toUpperCase() !== filterCat) return false;
    if (filterStation !== 'ALL' && t.station !== filterStation) return false;
    return true;
  });

  const stations = [...new Set(teamData.map(t => t.station).filter(Boolean))];

  return (
    <div className="tg-container">
      <div className="tg-filter-bar">
        <div className="tg-filters-left">
          <div className="zf-group">
            <span className="zf-label">Status</span>
            {['ALL', 'AVAILABLE', 'DEPLOYED', 'ON SITE', 'STANDBY'].map(opt => (
              <button 
                key={opt}
                className={`zf-pill ${filterStat === opt ? 'active' : ''}`}
                onClick={() => setFilterStat(opt)}
              >{opt}</button>
            ))}
          </div>
          <div className="zf-group">
            <span className="zf-label">Category</span>
            {['ALL', 'PRIMARY', 'SUBSTITUTION', 'RESERVE'].map(opt => (
              <button 
                key={opt}
                className={`zf-pill ${filterCat === opt ? 'active' : ''}`}
                onClick={() => setFilterCat(opt)}
              >{opt}</button>
            ))}
          </div>
          <div className="zf-group">
            <select 
              className="tc-select" 
              style={{ padding: '6px 12px', fontSize: '11px' }}
              value={filterStation}
              onChange={e => setFilterStation(e.target.value)}
            >
              <option value="ALL">ALL STATIONS</option>
              {stations.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
        
        <button className="btn-add" onClick={() => setShowModal(true)}>
          <Plus size={14} /> ADD TEAM
        </button>
      </div>

      <div className="tg-grid">
        {filtered.map(t => (
          <TeamDetailCard key={t.team_id} team={t} onUpdate={handleUpdateStatus} />
        ))}
      </div>

      {showModal && (
        <AddTeamModal 
          onClose={() => setShowModal(false)} 
          onSuccess={() => {
            setShowModal(false);
            refetch();
          }} 
        />
      )}
    </div>
  );
}
