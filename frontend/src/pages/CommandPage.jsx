import React, { useState, useEffect } from 'react';
import AppShell from '../components/shell/AppShell';
import LiveMap from '../components/command/LiveMap';
import CommandStrip from '../components/command/CommandStrip';
import DispatchModal from '../components/command/DispatchModal';
import ZonePopup from '../components/command/ZonePopup';
import { useQuery } from '@tanstack/react-query';
import { zones, dashboard } from '../lib/api';

export default function CommandPage() {
  const [selectedZone, setSelectedZone] = useState(null);
  const [isDispatchModalOpen, setIsDispatchModalOpen] = useState(false);
  const [dispatchZoneId, setDispatchZoneId] = useState(null);

  const { data: zonesRes } = useQuery({
    queryKey: ['allZones'],
    queryFn: () => zones.getZones(),
    refetchInterval: 30000,
  });

  const { data: statsRes } = useQuery({
    queryKey: ['stats'],
    queryFn: dashboard.getStats,
    refetchInterval: 30000,
  });

  const allZones = zonesRes?.data || [];

  useEffect(() => {
    const handleOpenDispatch = (e) => {
      setDispatchZoneId(e.detail?.zoneId || null);
      setIsDispatchModalOpen(true);
    };
    
    const handleSelectZone = (e) => {
      const z = allZones.find(x => x.zone_id === e.detail?.zoneId);
      if (z) setSelectedZone(z);
    };

    window.addEventListener('openDispatchModal', handleOpenDispatch);
    window.addEventListener('selectZone', handleSelectZone);
    
    return () => {
      window.removeEventListener('openDispatchModal', handleOpenDispatch);
      window.removeEventListener('selectZone', handleSelectZone);
    };
  }, [allZones]);

  const stats = statsRes?.data || {
    unassigned_red_zones: 0,
    active_teams: 0,
    available_teams: 0,
    total_red_zones: 0,
    total_amber_zones: 0
  };

  return (
    <AppShell>
      <div style={{ position: 'relative', width: '100%', height: '100%' }}>
        <LiveMap 
          zones={allZones} 
          selectedZone={selectedZone} 
          onZoneSelect={setSelectedZone} 
        />
        {selectedZone && (
          <>
            <div 
              style={{ position: 'absolute', inset: 0, zIndex: 1999, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(2px)' }} 
              onClick={() => setSelectedZone(null)}
            />
            <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', zIndex: 2000 }}>
            <ZonePopup 
              zone={selectedZone} 
              onClose={() => setSelectedZone(null)} 
              onDispatch={() => {
                setDispatchZoneId(selectedZone.zone_id);
                setIsDispatchModalOpen(true);
                setSelectedZone(null);
              }}
            />
          </div>
          </>
        )}

        {isDispatchModalOpen && (
          <DispatchModal 
            initialZoneId={dispatchZoneId}
            onClose={() => {
              setIsDispatchModalOpen(false);
              setDispatchZoneId(null);
            }}
          />
        )}

        {stats && <CommandStrip stats={stats} onOpenDispatch={() => {
          setDispatchZoneId(null);
          setIsDispatchModalOpen(true);
        }} />}
      </div>
    </AppShell>
  );
}
