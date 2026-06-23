import React from 'react';

export default function ZoneFilters({ filters, setFilters, count }) {
  const updateFilter = (key, val) => {
    setFilters(prev => ({ ...prev, [key]: val }));
  };

  const PillGroup = ({ label, options, filterKey }) => (
    <div className="zf-group">
      {label && <span className="zf-label">{label}</span>}
      {options.map(opt => (
        <button 
          key={opt}
          className={`zf-pill ${filters[filterKey] === opt ? 'active' : ''}`}
          onClick={() => updateFilter(filterKey, opt)}
        >
          {opt}
        </button>
      ))}
    </div>
  );

  return (
    <div className="zones-filter-bar">
      <div className="zf-groups">
        <PillGroup 
          label="Tier" 
          options={['ALL', 'RED', 'AMBER', 'GREEN']} 
          filterKey="tier" 
        />
        <PillGroup 
          label="Time Band" 
          options={['ALL', 'EARLY MORNING', 'MORNING', 'EVENING']} 
          filterKey="timeBand" 
        />
        <PillGroup 
          label="Volatility" 
          options={['ALL', 'VOLATILE GROWING', 'VOLATILE STABLE', 'STABLE GROWING', 'STABLE FLAT']} 
          filterKey="volatility" 
        />
        <PillGroup 
          label="Confidence" 
          options={['ALL', 'HIGH', 'MEDIUM', 'LOW']} 
          filterKey="confidence" 
        />
        
        <input 
          type="text" 
          className="zf-search" 
          placeholder="Search station or zone..."
          value={filters.search}
          onChange={(e) => updateFilter('search', e.target.value)}
        />
      </div>

      <div className="zf-right">
        <span className="zf-count">Showing {count} zones</span>
        <button className="zf-export">Export CSV</button>
      </div>
    </div>
  );
}
