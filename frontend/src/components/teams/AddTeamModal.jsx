import React, { useState } from 'react';
import { X } from 'lucide-react';
import { motion } from 'framer-motion';
import { teams } from '../../lib/api';

export default function AddTeamModal({ onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    team_id: '',
    station: '',
    category: 'primary',
    vehicle_type: 'interceptor',
    officers: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await teams.addTeam({
        team_id: formData.team_id,
        station: formData.station,
        category: formData.category,
        capacity: formData.officers.split(',').length
      });
      onSuccess();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <motion.div 
        className="modal-content"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-header">
          <div className="modal-title">ADD TO ROSTER</div>
          <button className="modal-close" onClick={onClose}><X size={24} /></button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Team ID</label>
            <div className="input-wrapper">
              <input 
                type="text" 
                className="form-input" 
                required 
                value={formData.team_id}
                onChange={e => setFormData({...formData, team_id: e.target.value})}
              />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Station</label>
            <div className="input-wrapper">
              <select 
                className="form-input" 
                required
                value={formData.station}
                onChange={e => setFormData({...formData, station: e.target.value})}
              >
                <option value="">Select Station</option>
                <option value="Koramangala">Koramangala</option>
                <option value="HSR Layout">HSR Layout</option>
                <option value="Indiranagar">Indiranagar</option>
                <option value="Madiwala">Madiwala</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Category</label>
            <div className="input-wrapper">
              <select 
                className="form-input"
                value={formData.category}
                onChange={e => setFormData({...formData, category: e.target.value})}
              >
                <option value="primary">PRIMARY</option>
                <option value="substitution">SUBSTITUTION</option>
                <option value="reserve">RESERVE</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Vehicle Type</label>
            <div className="input-wrapper">
              <select 
                className="form-input"
                value={formData.vehicle_type}
                onChange={e => setFormData({...formData, vehicle_type: e.target.value})}
              >
                <option value="interceptor">Interceptor</option>
                <option value="bike">Patrol Bike</option>
                <option value="van">Transport Van</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Officer Names (comma-separated)</label>
            <div className="input-wrapper">
              <input 
                type="text" 
                className="form-input" 
                required 
                value={formData.officers}
                onChange={e => setFormData({...formData, officers: e.target.value})}
              />
            </div>
          </div>

          <button type="submit" className="login-btn">ADD TO ROSTER</button>
        </form>
      </motion.div>
    </div>
  );
}
