import React, { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';

export default function ViolationHeatmap({ zones = [] }) {
  const map = useMap();

  useEffect(() => {
    let heatLayer = null;

    const initHeatmap = async () => {
      if (zones.length === 0) return;

      // Generate synthetic heatmap density perfectly aligned with current active zones
      const data = [];
      zones.forEach(z => {
        // More predicted violations = more density points
        const numPoints = Math.max(8, Math.floor((z.buffered_forecast || 500) / 40));
        const baseIntensity = z.tier?.toLowerCase() === 'red' ? 0.9 : 0.4;
        
        for (let i = 0; i < numPoints; i++) {
          // Jitter points within ~700m radius of the centroid
          const jLat = z.centroid_lat + (Math.random() - 0.5) * 0.012;
          const jLon = z.centroid_lon + (Math.random() - 0.5) * 0.012;
          // Add a central core point
          if (i === 0) {
            data.push([z.centroid_lat, z.centroid_lon, baseIntensity]);
          } else {
            // Fade intensity slightly towards edges
            data.push([jLat, jLon, baseIntensity * 0.7]);
          }
        }
      });

      if (!window.L) window.L = L;
      await import('leaflet.heat');
      
      heatLayer = L.heatLayer(data, {
        radius: 35,
        blur: 25,
        maxZoom: 13,
        max: 0.8, // Raised slightly because we generate overlapping jitter points
        gradient: {
          0.3: '#0066ff',
          0.6: '#ffb300',
          0.8: '#ff2a2a',
          1.0: '#ffffff'
        }
      });
      
      heatLayer.addTo(map);
    };

    initHeatmap();

    return () => {
      if (heatLayer) {
        heatLayer.remove();
      }
    };
  }, [map, zones]);

  return null;
}
