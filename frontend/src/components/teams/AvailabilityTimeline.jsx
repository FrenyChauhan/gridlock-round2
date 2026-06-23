import React from 'react';
import { BarChart, Bar, XAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function AvailabilityTimeline() {
  // Generate next 4 hours in 30m slots
  const data = Array.from({ length: 8 }).map((_, i) => {
    const time = new Date();
    time.setMinutes(time.getMinutes() + i * 30);
    const label = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    return {
      time: label,
      deployed: Math.floor(Math.random() * 10) + 2,
      returning: Math.floor(Math.random() * 5) + 1,
      available: Math.floor(Math.random() * 20) + 10,
    };
  });

  return (
    <div className="av-timeline">
      <div className="av-title">TEAM AVAILABILITY · NEXT 4 HOURS</div>
      
      <div className="av-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} stackOffset="none" barSize={24} margin={{top: 0, right: 0, left: 0, bottom: -10}}>
            <XAxis dataKey="time" stroke="var(--text-dim)" fontSize={9} fontFamily="var(--font-mono)" tickLine={false} axisLine={false} />
            <Tooltip 
              cursor={{ fill: 'var(--panel-hover)' }}
              contentStyle={{ background: 'var(--panel-raised)', border: '1px solid var(--panel-border)', fontSize: '10px', fontFamily: 'var(--font-mono)' }}
            />
            <Bar dataKey="deployed" stackId="a" fill="var(--heat-red)" />
            <Bar dataKey="returning" stackId="a" fill="var(--heat-amber)" />
            <Bar dataKey="available" stackId="a" fill="var(--safe-green)" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="av-summary">
        <div className="av-pill" style={{ color: 'var(--safe-green)', border: '1px solid var(--safe-green)' }}>
          18 available now
        </div>
        <div className="av-pill" style={{ color: 'var(--heat-amber)', border: '1px solid var(--heat-amber)' }}>
          5 return &lt;1hr
        </div>
      </div>
    </div>
  );
}
