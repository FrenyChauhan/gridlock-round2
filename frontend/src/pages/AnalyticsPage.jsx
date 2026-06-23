import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboard } from '../lib/api';
import AppShell from '../components/shell/AppShell';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell, Legend, LineChart, Line, CartesianGrid } from 'recharts';
import { Activity, MapPin, Users, AlertTriangle, TrendingUp, Zap } from 'lucide-react';
import '../styles/analytics.css';

const PIE_COLORS = {
  Red: '#ff2a2a',    // var(--heat-red)
  Amber: '#ffb300',  // var(--heat-amber)
  Green: '#00c853'   // var(--safe-green)
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="ap-tooltip">
        <div className="ap-tooltip-label">{label}</div>
        {payload.map((entry, index) => (
          <div key={index} className="ap-tooltip-item">
            <span style={{ color: entry.color }}>{entry.name}:</span>
            <span style={{ color: '#fff' }}>{entry.value}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['analyticsData'],
    queryFn: () => dashboard.getAnalytics(),
    refetchInterval: 60000,
  });

  const { data: forecastData } = useQuery({
    queryKey: ['teamForecast'],
    queryFn: () => dashboard.getTeamForecast(),
    refetchInterval: 60000,
  });

  const analytics = data?.data;
  const forecasts = forecastData?.data || [];

  if (isLoading || !analytics) {
    return (
      <AppShell>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-dim)' }}>
          Loading Intelligence Data...
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="analytics-page grid-bg">
        <div className="ap-header">
          <h1 className="ap-title">Intelligence Dashboard</h1>
          <div className="ap-subtitle">7-Day Historical Analysis & Team Deployment Metrics</div>
        </div>

        <div className="ap-grid">
          
          {/* Violations by Time Band */}
          <div className="ap-card col-span-8">
            <div className="ap-card-title"><Activity size={16} /> Violations by Time Band (7 Days)</div>
            <div className="ap-chart-wrapper">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={analytics.violations_by_time} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorMorn" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0066ff" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#0066ff" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorEve" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ffb300" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#ffb300" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="day" stroke="var(--panel-border-bright)" tick={{ fill: 'var(--text-dim)', fontSize: 11 }} />
                  <YAxis stroke="var(--panel-border-bright)" tick={{ fill: 'var(--text-dim)', fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="morning" name="Morning" stroke="#0066ff" fillOpacity={1} fill="url(#colorMorn)" />
                  <Area type="monotone" dataKey="evening" name="Evening" stroke="#ffb300" fillOpacity={1} fill="url(#colorEve)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Tier Distribution */}
          <div className="ap-card col-span-4">
            <div className="ap-card-title"><AlertTriangle size={16} /> Zone Priority Distribution</div>
            <div className="ap-chart-wrapper" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={analytics.tier_distribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                    stroke="none"
                  >
                    {analytics.tier_distribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[entry.name] || '#ccc'} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top Stations */}
          <div className="ap-card col-span-8">
            <div className="ap-card-title"><MapPin size={16} /> Top Stations by Violation Volume</div>
            <div className="ap-chart-wrapper">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.top_stations} layout="vertical" margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                  <XAxis type="number" stroke="var(--panel-border-bright)" tick={{ fill: 'var(--text-dim)', fontSize: 11 }} />
                  <YAxis dataKey="name" type="category" width={100} stroke="none" tick={{ fill: 'var(--text-bright)', fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--panel-raised)' }} />
                  <Bar dataKey="violations" name="Total Violations" fill="var(--scan-blue)" radius={[0, 4, 4, 0]} barSize={20} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Team Metrics */}
          <div className="ap-card col-span-4">
            <div className="ap-card-title"><Users size={16} /> Active Team Deployments</div>
            
            <div className="ap-metrics-grid">
              <div className="ap-metric-box">
                <div className="ap-mb-val">{analytics.team_metrics.active_teams}</div>
                <div className="ap-mb-lbl">Active Teams</div>
              </div>
              <div className="ap-metric-box">
                <div className="ap-mb-val" style={{ color: 'var(--safe-green)' }}>{analytics.team_metrics.avg_response_time}</div>
                <div className="ap-mb-lbl">Avg Response (m)</div>
              </div>
            </div>

            <div className="ap-squad-list">
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-dim)', marginTop: '8px', marginBottom: '4px' }}>
                SQUAD SIZE BREAKDOWN
              </div>
              {analytics.team_metrics.squad_sizes.map((s, idx) => (
                <div key={idx} className="ap-squad-row">
                  <div className="ap-squad-size">{s.size}</div>
                  <div className="ap-squad-count">{s.count} Teams</div>
                </div>
              ))}
            </div>

          </div>

          {/* Smart Dispatch Recommendations */}
          <div className="ap-card col-span-12" style={{ marginTop: '24px' }}>
            <div className="ap-card-title"><Zap size={16} color="var(--heat-amber)" /> Smart Dispatch Priorities (Team Availability Forecast)</div>
            <div className="ap-table-wrapper" style={{ overflowX: 'auto', marginTop: '16px' }}>
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--panel-border-bright)', color: 'var(--text-dim)' }}>
                    <th style={{ padding: '8px 12px' }}>TEAM ID</th>
                    <th style={{ padding: '8px 12px' }}>STATUS</th>
                    <th style={{ padding: '8px 12px' }}>FREE IN (MINS)</th>
                    <th style={{ padding: '8px 12px' }}>RECOMMENDED NEXT ZONE</th>
                    <th style={{ padding: '8px 12px' }}>PRIORITY SCORE</th>
                    <th style={{ padding: '8px 12px' }}>DISTANCE</th>
                  </tr>
                </thead>
                <tbody>
                  {forecasts.map((f, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--panel-border)', color: 'var(--text-bright)' }}>
                      <td style={{ padding: '12px', color: 'var(--intel-cyan)' }}>{f.team_id}</td>
                      <td style={{ padding: '12px', textTransform: 'uppercase' }}>{f.current_status.replace('_', ' ')}</td>
                      <td style={{ padding: '12px', color: f.minutes_until_free < 15 ? 'var(--safe-green)' : 'var(--heat-amber)' }}>{f.minutes_until_free}m</td>
                      <td style={{ padding: '12px', color: f.recommended_next_zone ? 'var(--heat-red)' : 'var(--text-dim)' }}>
                        {f.recommended_next_zone ? f.recommended_next_zone.zone_id : 'NO PENDING RED ZONES'}
                      </td>
                      <td style={{ padding: '12px' }}>{f.recommended_next_zone ? f.recommended_next_zone.priority_score.toFixed(1) : '-'}</td>
                      <td style={{ padding: '12px' }}>{f.recommended_next_zone ? `${f.recommended_next_zone.distance_km} km` : '-'}</td>
                    </tr>
                  ))}
                  {forecasts.length === 0 && (
                    <tr>
                      <td colSpan="6" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-dim)' }}>No active deployments to forecast.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* 30-Day Overall Trend (Full Width) */}
          <div className="ap-card col-span-12" style={{ marginTop: '24px' }}>
            <div className="ap-card-title"><TrendingUp size={16} /> 30-Day Total Violations Trend</div>
            <div className="ap-chart-wrapper" style={{ height: '300px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={analytics.monthly_trend} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--panel-border)" vertical={false} />
                  <XAxis dataKey="day" stroke="var(--panel-border-bright)" tick={{ fill: 'var(--text-dim)', fontSize: 11 }} />
                  <YAxis stroke="var(--panel-border-bright)" tick={{ fill: 'var(--text-dim)', fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="violations" name="Total Violations" stroke="var(--intel-cyan)" strokeWidth={3} dot={{ fill: 'var(--void)', stroke: 'var(--intel-cyan)', strokeWidth: 2, r: 4 }} activeDot={{ r: 6, fill: 'var(--intel-cyan)' }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      </div>
    </AppShell>
  );
}
