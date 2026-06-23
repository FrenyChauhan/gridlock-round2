import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, SVGOverlay } from 'react-leaflet';
import L from 'leaflet';
import ViolationHeatmap from './ViolationHeatmap';
import '../../styles/radar.css';
import 'leaflet/dist/leaflet.css';

// SVG bounds for the radar (~8km radius around Bengaluru)
const centerLat = 12.9716;
const centerLon = 77.5946;
const r = 0.15;
const bounds = [
  [centerLat - r, centerLon - r],
  [centerLat + r, centerLon + r],
];

function RadarOverlay() {
  return (
    <SVGOverlay bounds={bounds} className="radar-overlay">
      <svg viewBox="0 0 100 100" width="100%" height="100%">
        <circle cx="50" cy="50" r="48" fill="none" stroke="rgba(0,102,255,0.2)" strokeWidth="0.5" />
        <circle cx="50" cy="50" r="32" fill="none" stroke="rgba(0,102,255,0.1)" strokeWidth="0.5" />
        <circle cx="50" cy="50" r="16" fill="none" stroke="rgba(0,102,255,0.1)" strokeWidth="0.5" />
        <g className="sweep-sector">
          <path d="M50,50 L50,2 A48,48 0 0,1 78,11 Z" fill="url(#radar-grad)" />
        </g>
        <defs>
          <radialGradient id="radar-grad" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
            <stop offset="0%" stopColor="rgba(0,102,255,0.4)" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
        </defs>
      </svg>
    </SVGOverlay>
  );
}

function ZoneMarker({ zone, onSelect }) {
  const { 
    zone_id, centroid_lat, centroid_lon, tier, 
    volatility_class, buffered_forecast 
  } = zone;

  const tierLower = tier?.toLowerCase() || 'amber';
  const isVolatileGrowing = volatility_class === 'volatile_growing';
  const ringColor = tierLower === 'red' ? 'var(--heat-red)' : 'var(--heat-amber)';
  
  // Size maps 0-1000 to 24-52
  const scaledSize = Math.max(24, Math.min(52, 24 + ((buffered_forecast || 0) / 1000) * 28));
  
  // Center dot style
  let centerDotSize = 8;
  let centerDotStyle = `background-color: ${ringColor};`;
  if (tierLower === 'red') {
    centerDotSize = 10;
    centerDotStyle += ` border: 2px solid rgba(255,45,85,0.5);`;
  }
  
  const speed1 = tierLower === 'red' ? '2s' : '3s';
  const speed2 = isVolatileGrowing ? '1.4s' : null;

  const iconHtml = `
    <div class="pulse-dot" style="width: ${scaledSize}px; height: ${scaledSize}px;">
      <div class="center-dot" style="width: ${centerDotSize}px; height: ${centerDotSize}px; ${centerDotStyle}"></div>
      <div class="pulse-ring pulse-ring-1" style="--pulse-speed: ${speed1}; --ring-color: ${ringColor}; width: ${scaledSize}px; height: ${scaledSize}px;"></div>
      ${speed2 ? `<div class="pulse-ring pulse-ring-2" style="--pulse-speed: ${speed2}; --ring-color: ${ringColor}; width: ${scaledSize}px; height: ${scaledSize}px;"></div>` : ''}
    </div>
  `;

  const customIcon = L.divIcon({
    html: iconHtml,
    className: 'custom-pulse-marker',
    iconSize: [scaledSize, scaledSize],
    iconAnchor: [scaledSize/2, scaledSize/2],
  });

  return (
    <Marker 
      position={[centroid_lat, centroid_lon]} 
      icon={customIcon}
      eventHandlers={{
        click: () => onSelect(zone)
      }}
    />
  );
}

export default function LiveMap({ zones = [], selectedZone, onZoneSelect }) {
  const [filterTier, setFilterTier] = useState('ALL');
  const [filterTime, setFilterTime] = useState('ALL');
  const [showHeatmap, setShowHeatmap] = useState(true);

  const filteredZones = zones.filter(z => {
    const tierLower = z.tier?.toLowerCase() || '';
    if (tierLower !== 'red' && tierLower !== 'amber') return false;
    
    if (filterTier === 'RED' && tierLower !== 'red') return false;
    if (filterTier === 'AMBER' && tierLower !== 'amber') return false;
    if (filterTier === 'VOLATILE' && z.volatility_class !== 'volatile_growing') return false;

    if (filterTime !== 'ALL' && z.time_band !== filterTime.toLowerCase().replace(' ', '_')) {
      return false;
    }

    return true;
  });

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <MapContainer 
        center={[12.9716, 77.5946]} 
        zoom={13} 
        minZoom={11}
        maxZoom={16}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
          attribution='&copy; CARTO'
        />
        <RadarOverlay />
        {showHeatmap && <ViolationHeatmap zones={filteredZones} />}
        
        {filteredZones.map(zone => (
          <ZoneMarker 
            key={zone.zone_id} 
            zone={zone} 
            onSelect={onZoneSelect}
          />
        ))}
      </MapContainer>

      {/* Floating Filter Controls */}
      <div className="floating-filters">
        <div className="ff-label">LAYERS & FILTERS</div>
        <div className="ff-row" style={{ marginBottom: '12px' }}>
          <button 
            className={`ff-pill ${showHeatmap ? 'active' : ''}`}
            onClick={() => setShowHeatmap(!showHeatmap)}
            style={{ width: '100%', borderColor: showHeatmap ? 'var(--scan-blue)' : 'var(--panel-border)', boxShadow: showHeatmap ? '0 0 10px rgba(0, 102, 255, 0.2)' : 'none' }}
          >
            🔥 HEATMAP DENSITY
          </button>
        </div>
        <div className="ff-row">
          {['ALL', 'RED', 'AMBER', 'VOLATILE'].map(t => (
            <button 
              key={t} 
              className={`ff-pill ${filterTier === t ? 'active' : ''}`}
              onClick={() => setFilterTier(t)}
            >{t}</button>
          ))}
        </div>
        <div className="ff-row">
          {['ALL', 'EARLY MORNING', 'MORNING', 'EVENING'].map(t => (
            <button 
              key={t} 
              className={`ff-pill ${filterTime === t ? 'active' : ''}`}
              onClick={() => setFilterTime(t)}
            >{t}</button>
          ))}
        </div>
      </div>
    </div>
  );
}
