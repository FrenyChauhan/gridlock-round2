import React from 'react';
import AppShell from '../components/shell/AppShell';
import AvailabilityTimeline from '../components/teams/AvailabilityTimeline';
import TeamGrid from '../components/teams/TeamGrid';
import { useQuery } from '@tanstack/react-query';
import { teams } from '../lib/api';
import '../styles/teams.css';

export default function TeamsPage() {
  const { data: teamsRes, refetch } = useQuery({
    queryKey: ['teams'],
    queryFn: () => teams.getTeams(),
    refetchInterval: 15000,
  });

  const allTeams = teamsRes?.data || [];

  return (
    <AppShell>
      <div className="teams-page">
        <AvailabilityTimeline />
        <TeamGrid teamData={allTeams} refetch={refetch} />
      </div>
    </AppShell>
  );
}
