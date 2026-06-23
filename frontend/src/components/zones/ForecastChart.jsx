import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, ComposedChart } from 'recharts';

export default function ForecastChart({ clusterId, timeBand }) {
  // Mock history + forecast data
  const data = [
    { day: 'Mon', actual: 320 },
    { day: 'Tue', actual: 410 },
    { day: 'Wed', actual: 390 },
    { day: 'Thu', actual: 520 },
    { day: 'Fri', actual: 480 },
    { day: 'Sat', actual: 210 },
    { day: 'Sun', actual: 190 },
    { day: 'Today', forecast: 450, confRange: [400, 500] }
  ];

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'var(--panel-raised)',
          border: '1px solid var(--panel-border)',
          padding: '12px',
          borderRadius: 'var(--r-md)',
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          zIndex: 1000
        }}>
          <div style={{ color: 'var(--text-dim)', marginBottom: '8px' }}>{label}</div>
          {payload.map((entry, idx) => {
            if (entry.dataKey === 'confRange') return null; // hide range bounds from tooltip directly
            return (
              <div key={idx} style={{ color: entry.color, marginBottom: '4px' }}>
                {entry.name}: {entry.value}
              </div>
            );
          })}
        </div>
      );
    }
    return null;
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--panel-border)" vertical={false} />
        <XAxis 
          dataKey="day" 
          stroke="var(--text-dim)" 
          fontSize={10} 
          fontFamily="var(--font-mono)" 
          tickLine={false}
          axisLine={false}
        />
        <YAxis 
          stroke="var(--text-dim)" 
          fontSize={10} 
          fontFamily="var(--font-mono)" 
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        
        {/* Historical Line */}
        <Line 
          type="monotone" 
          dataKey="actual" 
          name="Actual"
          stroke="var(--scan-blue)" 
          strokeWidth={2}
          dot={{ fill: 'var(--void)', stroke: 'var(--scan-blue)', strokeWidth: 2, r: 4 }}
          activeDot={{ r: 6, fill: 'var(--scan-blue)' }}
        />

        {/* Confidence Band */}
        <Area 
          type="monotone" 
          dataKey="confRange" 
          stroke="none" 
          fill="rgba(255,149,0,0.15)" 
        />

        {/* Forecast Point */}
        <Line 
          type="monotone" 
          dataKey="forecast" 
          name="Predicted"
          stroke="var(--heat-amber)" 
          strokeWidth={2}
          strokeDasharray="5 5"
          dot={{ fill: 'var(--heat-amber)', stroke: 'var(--void)', strokeWidth: 2, r: 6 }}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
