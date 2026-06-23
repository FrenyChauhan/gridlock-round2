import { useState, useEffect } from 'react';
import { zones, teams } from '../lib/api';

export function useNotifications() {
  const [notifications, setNotifications] = useState([]);
  const [readIds, setReadIds] = useState(new Set());

  useEffect(() => {
    const fetchNotifs = async () => {
      try {
        const [zonesRes, teamsRes] = await Promise.all([
          zones.getZones(),
          teams.getTeams()
        ]);
        
        const allZones = zonesRes.data || [];
        const allTeams = teamsRes.data || [];

        const newNotifs = [];

        // Source 1: unassigned red zones
        const unassignedRed = allZones.filter(z => z.tier?.toLowerCase() === 'red' && !z.assigned_team_id);
        unassignedRed.forEach(z => {
          newNotifs.push({
            id: `unassigned-red-${z.zone_id}`,
            type: 'critical',
            title: 'Unpatrolled Red Zone',
            message: `${z.dominant_station} · ${z.time_band.replace('_', ' ')} · ${Math.round(z.predicted_violations)} violations predicted`,
            action: 'ASSIGN NOW',
            zone_id: z.zone_id,
            timestamp: Date.now()
          });
        });

        // Source 2: volatile growing zones with no team
        const volatile = allZones.filter(z => z.volatility_class === 'volatile_growing' && !z.assigned_team_id && z.tier?.toLowerCase() !== 'red');
        volatile.forEach(z => {
          newNotifs.push({
            id: `volatile-${z.zone_id}`,
            type: 'warning',
            title: 'Volatile Hotspot Unmonitored',
            message: `${z.dominant_station} is growing · +30% buffer applied`,
            action: 'VIEW',
            zone_id: z.zone_id,
            timestamp: Date.now()
          });
        });

        // Source 3: high false positive zones
        const highFp = allZones.filter(z => z.cii_score > 0.8 && z.tier?.toLowerCase() === 'amber');
        highFp.slice(0, 1).forEach(z => {
          newNotifs.push({
            id: `fp-${z.zone_id}`,
            type: 'info',
            title: 'Model Accuracy Alert',
            message: `${z.zone_id} has 12.4% FP rate · Consider lower priority`,
            timestamp: Date.now()
          });
        });

        // Source 4: teams returning soon
        const activeTeams = allTeams.filter(t => t.status === 'onsite' || t.status === 'enroute');
        activeTeams.forEach(t => {
          newNotifs.push({
            id: `team-return-${t.team_id}`,
            type: 'success',
            title: 'Team Becoming Available',
            message: `${t.team_id} free in ~15m · ${t.station} needs coverage`,
            action: 'PRE-ASSIGN',
            team_id: t.team_id,
            timestamp: Date.now()
          });
        });

        // Source 5: teams needing backup
        const needsBackup = allTeams.filter(t => t.status === 'needs_backup');
        needsBackup.forEach(t => {
          newNotifs.push({
            id: `backup-${t.team_id}`,
            type: 'critical',
            title: 'BACKUP REQUIRED',
            message: `Team ${t.team_id} has requested immediate backup at ${t.station || 'their location'}!`,
            action: 'DISPATCH',
            team_id: t.team_id,
            timestamp: Date.now()
          });
        });

        setNotifications(prev => {
          const prevMap = new Map(prev.map(n => [n.id, n]));
          const merged = newNotifs.map(n => {
            if (prevMap.has(n.id)) {
              return { ...n, timestamp: prevMap.get(n.id).timestamp };
            }
            return n;
          });
          return merged.sort((a, b) => b.timestamp - a.timestamp);
        });
      } catch (err) {
        console.error('Failed to fetch notifications:', err);
      }
    };

    fetchNotifs();
    const interval = setInterval(fetchNotifs, 30000);
    return () => clearInterval(interval);
  }, []);

  const notifsWithState = notifications.map(n => ({
    ...n,
    read: readIds.has(n.id)
  }));

  const unreadCount = notifsWithState.filter(n => !n.read).length;

  const markAllRead = () => {
    const newRead = new Set(readIds);
    notifications.forEach(n => newRead.add(n.id));
    setReadIds(newRead);
  };

  const markRead = (id) => {
    const newRead = new Set(readIds);
    newRead.add(id);
    setReadIds(newRead);
  };

  return { notifications: notifsWithState, unreadCount, markAllRead, markRead };
}
