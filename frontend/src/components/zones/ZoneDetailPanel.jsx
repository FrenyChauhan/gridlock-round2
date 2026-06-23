import React, { useState } from 'react';
import { X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ForecastChart from './ForecastChart';
import ZoneHistoryTab from './ZoneHistoryTab';

export default function ZoneDetailPanel({ zone, onClose, onDispatch }) {
  if (!zone) return null;

  const {
    zone_id, dominant_station, tier, buffered_forecast,
    cii_score, volatility_class, confidence_level, assigned_team_id
  } = zone;

  const tColor = tier?.toLowerCase() || 'amber';
  const [activeTab, setActiveTab] = useState('INTELLIGENCE');

  return (
    <AnimatePresence>
      <motion.div 
        className="z-detail-panel"
        initial={{ x: 40, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 40, opacity: 0 }}
        transition={{ type: 'spring', damping: 20, stiffness: 200 }}
      >
        <div className="zdp-header">
          <button className="zdp-close" onClick={onClose}><X size={24} /></button>
          <div className="zdp-eyebrow">ZONE INTELLIGENCE</div>
          <div className="zdp-id">{zone_id}</div>
          <div className="zdp-station">{dominant_station}</div>
          <div className={`zdp-tier ${tColor}`}>{tier?.toUpperCase()}</div>
        </div>

        {/* TABS */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--panel-border)', margin: '0 16px' }}>
          <button 
            onClick={() => setActiveTab('INTELLIGENCE')}
            style={{ 
              flex: 1, padding: '12px 0', background: 'transparent', border: 'none',
              fontFamily: 'var(--font-mono)', fontSize: '11px', cursor: 'pointer',
              color: activeTab === 'INTELLIGENCE' ? 'var(--text-bright)' : 'var(--text-dim)',
              borderBottom: activeTab === 'INTELLIGENCE' ? '2px solid var(--scan-blue)' : '2px solid transparent',
            }}
          >
            INTELLIGENCE
          </button>
          <button 
            onClick={() => setActiveTab('HISTORY')}
            style={{ 
              flex: 1, padding: '12px 0', background: 'transparent', border: 'none',
              fontFamily: 'var(--font-mono)', fontSize: '11px', cursor: 'pointer',
              color: activeTab === 'HISTORY' ? 'var(--text-bright)' : 'var(--text-dim)',
              borderBottom: activeTab === 'HISTORY' ? '2px solid var(--scan-blue)' : '2px solid transparent',
            }}
          >
            HISTORY
          </button>
        </div>

        <div className="zdp-body">
          {activeTab === 'INTELLIGENCE' ? (
            <>
              <div className="zdp-grid">
            <div className="zdp-metric">
              <span className="zdp-m-val">{Math.round(buffered_forecast || 0)}</span>
              <span className="zdp-m-label">Predicted</span>
            </div>
            <div className="zdp-metric">
              <span className="zdp-m-val">+{Math.round((buffered_forecast || 0) * 0.3)}</span>
              <span className="zdp-m-label">Buffered Forecast</span>
            </div>
            <div className="zdp-metric">
              <span className="zdp-m-val">{cii_score ? parseFloat(cii_score).toFixed(2) : '0.00'}</span>
              <span className="zdp-m-label">CII Score</span>
            </div>
            <div className="zdp-metric">
              <span className="zdp-m-val" style={{ color: 'var(--heat-red)' }}>HIGH</span>
              <span className="zdp-m-label">Priority Score</span>
            </div>
            <div className="zdp-metric">
              <span className="zdp-m-val" style={{ textTransform: 'capitalize' }}>
                {volatility_class?.replace('_', ' ')}
              </span>
              <span className="zdp-m-label">Volatility</span>
            </div>
            <div className="zdp-metric">
              <span className="zdp-m-val">{confidence_level || 'HIGH'}</span>
              <span className="zdp-m-label">Confidence</span>
            </div>
          </div>

          <div>
            <div className="zdp-section-title">Forecast Trend</div>
            <div className="zdp-chart">
              <ForecastChart clusterId={zone_id} timeBand={zone.time_band} />
            </div>
          </div>

          <div>
            <div className="zdp-section-title">Deployment</div>
            {assigned_team_id ? (
              <div className="zdp-assign">
                <div style={{ color: 'var(--safe-green)', fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600, marginBottom: '8px' }}>
                  ● EN ROUTE
                </div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '18px', color: 'var(--text-bright)' }}>
                  {assigned_team_id}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  Expected free: 45m
                </div>
                <button className="zdp-btn" onClick={onDispatch} style={{ marginTop: '16px', background: 'transparent', border: '1px solid var(--panel-border-bright)' }}>DISPATCH BACKUP</button>
              </div>
            ) : (
              <button className="zdp-btn" onClick={onDispatch}>DISPATCH TEAM</button>
            )}
          </div>

          {/* Model Accuracy (Mocked for demo) */}
          <div>
            <div className="zdp-section-title">Model Accuracy for This Zone</div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-bright)'}}>Predicted: 450</span>
              <span style={{fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-mid)'}}>Actual: 420</span>
            </div>
            <div className="zdp-acc-bar">
              <div className="zdp-acc-pred" style={{ flex: 45 }}>PRED</div>
              <div className="zdp-acc-act" style={{ flex: 42 }}>ACTUAL</div>
            </div>
            <div style={{fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--safe-green)', marginTop: '8px'}}>
              FPR: 6.6% (Healthy)
            </div>
          </div>
          </>
          ) : (
            <ZoneHistoryTab clusterId={zone.cluster_id} zoneId={zone.zone_id} />
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
