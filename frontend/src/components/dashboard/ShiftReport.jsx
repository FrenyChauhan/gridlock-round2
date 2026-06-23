import React, { useEffect, useState } from 'react';
import api from '../../lib/api';
import { X, Printer } from 'lucide-react';

export default function ShiftReport({ onClose }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetchReport = async () => {
      // For demo, shift is last 8 hours
      const end = new Date();
      const start = new Date(end.getTime() - 8 * 3600000);
      try {
        const res = await api.get('/dashboard/shift-report', {
          params: { shift_start: start.toISOString(), shift_end: end.toISOString() }
        });
        setData(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchReport();
  }, []);

  if (!data) {
    return (
      <div style={{ position: 'fixed', inset: 0, background: 'var(--void)', zIndex: 10000, display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'var(--scan-blue-bright)', fontFamily: 'var(--font-mono)' }}>
        GENERATING SHIFT INTELLIGENCE REPORT...
      </div>
    );
  }

  const { operations, unresolved_zones, recommended_next_shift, top_performing_teams, region } = data;

  const dateStr = new Date(data.shift_start).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  const startStr = new Date(data.shift_start).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });
  const endStr = new Date(data.shift_end).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--void)', zIndex: 10000, overflowY: 'auto' }}>
      <style>
        {`
          @media print {
            body * { visibility: hidden; }
            .print-area, .print-area * { visibility: visible; }
            .print-area { position: absolute; left: 0; top: 0; width: 100%; color: #000; background: #fff !important; }
            .no-print { display: none !important; }
            * { color: #000 !important; background: transparent !important; box-shadow: none !important; }
          }
          .sr-stat { display: flex; flex-direction: column; padding: 20px; background: rgba(0,102,255,0.05); border: 1px solid var(--panel-border); border-radius: 8px; }
          .sr-val { font-family: var(--font-display); font-size: 32px; font-weight: 700; color: var(--text-bright); margin-bottom: 4px; }
          .sr-lbl { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; }
          table { width: 100%; border-collapse: collapse; margin-top: 12px; }
          th { text-align: left; padding: 12px; border-bottom: 1px solid var(--panel-border); font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); }
          td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 12px; color: var(--text-mid); }
        `}
      </style>

      {/* Controls */}
      <div className="no-print" style={{ display: 'flex', justifyContent: 'flex-end', gap: '16px', padding: '24px', position: 'sticky', top: 0, background: 'linear-gradient(to bottom, var(--void) 50%, transparent)' }}>
        <button onClick={() => window.print()} style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--scan-blue)', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 'bold' }}>
          <Printer size={16} /> PRINT REPORT
        </button>
        <button onClick={onClose} style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'transparent', color: 'var(--text-bright)', border: '1px solid var(--panel-border)', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
          <X size={16} /> CLOSE
        </button>
      </div>

      <div className="print-area" style={{ maxWidth: '900px', margin: '0 auto', padding: '0 40px 80px 40px' }}>
        
        {/* Header */}
        <div style={{ marginBottom: '40px' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-dim)', marginBottom: '8px' }}>BENGALURU TRAFFIC POLICE</div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '28px', fontWeight: 700, color: 'var(--text-bright)', marginBottom: '8px' }}>SHIFT INTELLIGENCE REPORT</div>
          <div style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--scan-blue-bright)' }}>{region} Region · {dateStr} · {startStr} – {endStr}</div>
          <div style={{ height: '1px', background: 'var(--scan-blue)', opacity: 0.3, marginTop: '24px' }}></div>
        </div>

        {/* Operations Summary */}
        <div style={{ marginBottom: '40px' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: 'var(--text-bright)', marginBottom: '16px' }}>OPERATIONS SUMMARY</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            <div className="sr-stat"><div className="sr-val">{operations.zones_patrolled}</div><div className="sr-lbl">Zones Patrolled</div></div>
            <div className="sr-stat"><div className="sr-val" style={{color: 'var(--safe-green)'}}>{operations.violations_confirmed}</div><div className="sr-lbl">Violations Confirmed</div></div>
            <div className="sr-stat"><div className="sr-val" style={{color: 'var(--heat-amber)'}}>{operations.false_positive_rate}%</div><div className="sr-lbl">False Positive Rate</div></div>
            <div className="sr-stat"><div className="sr-val" style={{color: 'var(--intel-cyan)'}}>{operations.avg_response_time_minutes}</div><div className="sr-lbl">Avg Response Time (min)</div></div>
            <div className="sr-stat"><div className="sr-val">{operations.teams_deployed}</div><div className="sr-lbl">Teams Deployed</div></div>
            <div className="sr-stat"><div className="sr-val">{operations.backup_requests}</div><div className="sr-lbl">Backup Requests</div></div>
          </div>
        </div>

        {/* Unresolved Zones */}
        <div style={{ marginBottom: '40px' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: 'var(--text-bright)', marginBottom: '8px' }}>UNRESOLVED CRITICAL HOTSPOTS</div>
          <table>
            <thead><tr><th>ZONE ID</th><th>STATION</th><th>PRIORITY SCORE</th><th>PREDICTED</th><th>RECOMMENDED TEAM</th></tr></thead>
            <tbody>
              {unresolved_zones.length === 0 ? <tr><td colSpan="5">No unresolved critical hotspots.</td></tr> : unresolved_zones.map(z => (
                <tr key={z.zone_id} style={{ background: 'rgba(255,45,85,0.05)' }}>
                  <td style={{ color: 'var(--heat-red)', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>{z.zone_id}</td>
                  <td>{z.station}</td>
                  <td>{z.priority_score.toFixed(1)}</td>
                  <td>{Math.round(z.predicted)}</td>
                  <td style={{ color: 'var(--text-dim)' }}>{z.recommended_team}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Recommended for Next Shift */}
        <div style={{ marginBottom: '40px' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: 'var(--text-bright)', marginBottom: '16px' }}>RECOMMENDED FOR NEXT SHIFT (HANDOVER)</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {recommended_next_shift.map((z, idx) => (
              <div key={idx} style={{ padding: '12px', background: 'var(--panel)', border: '1px solid var(--panel-border)', borderRadius: '4px', display: 'flex', gap: '16px', alignItems: 'center' }}>
                <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--scan-blue)', color: '#fff', display: 'flex', justifyContent: 'center', alignItems: 'center', fontSize: '12px', fontWeight: 'bold' }}>{idx + 1}</div>
                <div style={{ flex: 1, fontSize: '14px', color: 'var(--text-bright)' }}>{z.station}</div>
                <div style={{ color: 'var(--text-mid)', fontFamily: 'var(--font-mono)', fontSize: '12px', textTransform: 'uppercase' }}>{z.time_band.replace('_', ' ')}</div>
                <div style={{ color: 'var(--heat-amber)', fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 'bold' }}>PRED: {Math.round(z.predicted)}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Teams */}
        <div style={{ marginBottom: '60px' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: 'var(--text-bright)', marginBottom: '8px' }}>TOP PERFORMING TEAMS</div>
          <table>
            <thead><tr><th>TEAM ID</th><th>OUTCOMES RECORDED</th><th>CONFIRMED RATE</th><th>AVG RESPONSE</th></tr></thead>
            <tbody>
              {top_performing_teams.map(t => (
                <tr key={t.team_id}>
                  <td style={{ color: 'var(--gold)', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>{t.team_id}</td>
                  <td>{t.outcomes}</td>
                  <td style={{ color: 'var(--safe-green)' }}>{t.confirmed_rate}%</td>
                  <td style={{ color: 'var(--intel-cyan)' }}>{t.avg_response_time} min</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div style={{ textAlign: 'center', borderTop: '1px solid var(--panel-border)', paddingTop: '24px', fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-dim)' }}>
          Generated by Gridlock 2.0 · ASTRaM Enforcement Intelligence
        </div>

      </div>
    </div>
  );
}
