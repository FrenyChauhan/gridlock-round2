import api from './api';

export async function fetchHeatmapPoints() {
  try {
    const res = await api.get('/zones/heatmap-points');
    return res.data.map(p => [p.lat, p.lng, p.intensity]);
  } catch (error) {
    console.error('Error fetching heatmap points:', error);
    return [];
  }
}
