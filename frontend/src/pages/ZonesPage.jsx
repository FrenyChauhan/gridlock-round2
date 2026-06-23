import React, { useState } from 'react';
import AppShell from '../components/shell/AppShell';
import ZoneFilters from '../components/zones/ZoneFilters';
import ZoneTable from '../components/zones/ZoneTable';
import ZoneDetailPanel from '../components/zones/ZoneDetailPanel';
import DispatchModal from '../components/command/DispatchModal';
import { useQuery } from '@tanstack/react-query';
import { zones } from '../lib/api';
import '../styles/zones.css';

export default function ZonesPage() {
  const [selectedZone, setSelectedZone] = useState(null);
  const [isDispatchModalOpen, setIsDispatchModalOpen] = useState(false);
  
  // Filter states
  const [filters, setFilters] = useState({
    tier: 'ALL',
    timeBand: 'ALL',
    volatility: 'ALL',
    confidence: 'ALL',
    search: ''
  });

  const { data: zonesRes, isLoading } = useQuery({
    queryKey: ['allZones'],
    queryFn: () => zones.getZones(),
    refetchInterval: 30000,
  });

  const allZones = zonesRes?.data || [];

  // Apply filters
  const filteredZones = allZones.filter(z => {
    if (filters.tier !== 'ALL' && z.tier?.toUpperCase() !== filters.tier) return false;
    
    if (filters.timeBand !== 'ALL') {
      const tb = z.time_band?.replace('_', ' ').toUpperCase();
      if (tb !== filters.timeBand) return false;
    }

    if (filters.volatility !== 'ALL') {
      const vol = z.volatility_class?.replace('_', ' ').toUpperCase();
      if (vol !== filters.volatility) return false;
    }

    if (filters.confidence !== 'ALL' && z.confidence_level?.toUpperCase() !== filters.confidence) return false;

    if (filters.search) {
      const term = filters.search.toLowerCase();
      if (!z.dominant_station?.toLowerCase().includes(term) && !z.zone_id?.toLowerCase().includes(term)) {
        return false;
      }
    }

    return true;
  });

  return (
    <AppShell>
      <div className="zones-page">
        <ZoneFilters 
          filters={filters} 
          setFilters={setFilters} 
          count={filteredZones.length} 
        />
        
        <div className="zones-content">
          <ZoneTable 
            zones={filteredZones} 
            selectedZone={selectedZone} 
            onSelect={setSelectedZone} 
            isLoading={isLoading}
          />
          
          {selectedZone && (
            <ZoneDetailPanel 
              zone={selectedZone} 
              onClose={() => setSelectedZone(null)} 
              onDispatch={() => setIsDispatchModalOpen(true)}
            />
          )}
        </div>
        
        {isDispatchModalOpen && selectedZone && (
          <DispatchModal 
            initialZoneId={selectedZone.zone_id}
            onClose={() => setIsDispatchModalOpen(false)}
          />
        )}
      </div>
    </AppShell>
  );
}
