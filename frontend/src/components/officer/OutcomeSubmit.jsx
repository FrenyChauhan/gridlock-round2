import React, { useState } from 'react';
import { motion } from 'framer-motion';

export default function OutcomeSubmit({ onSubmit }) {
  const [selectedOpt, setSelectedOpt] = useState(null);
  const [count, setCount] = useState('');

  const handleOptClick = (opt) => {
    setSelectedOpt(opt);
  };

  const handleSubmit = () => {
    onSubmit({ outcome: selectedOpt, violationsFound: parseInt(count, 10) || 0 });
  };

  const getOptClass = (opt) => {
    if (selectedOpt === opt) {
      if (opt === 'confirmed') return 'sel-true';
      if (opt === 'false_pos') return 'sel-false';
      if (opt === 'backup') return 'sel-amber';
      if (opt === 'quick') return 'sel-blue';
    }
    return '';
  };

  return (
    <div className="outcome-sheet-overlay">
      <motion.div 
        className="outcome-sheet"
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      >
        <div className="os-title">SUBMIT OUTCOME</div>

        <div className="os-btns">
          <button className={`os-opt ${getOptClass('confirmed')}`} onClick={() => handleOptClick('confirmed')}>
            ✓ Violation confirmed
          </button>
          <button className={`os-opt ${getOptClass('false_pos')}`} onClick={() => handleOptClick('false_pos')}>
            ✗ False positive
          </button>
          <button className={`os-opt ${getOptClass('backup')}`} onClick={() => handleOptClick('backup')}>
            ⚠ Needed backup
          </button>
          <button className={`os-opt ${getOptClass('quick')}`} onClick={() => handleOptClick('quick')}>
            ⚡ Resolved quickly
          </button>
        </div>

        {selectedOpt && (
          <motion.div 
            className="os-input-grp"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
          >
            <div className="os-lbl">VIOLATIONS FOUND</div>
            <input 
              type="number" 
              className="os-num" 
              value={count} 
              onChange={e => setCount(e.target.value)} 
              placeholder="0"
            />
          </motion.div>
        )}

        <button className="os-submit" onClick={handleSubmit} disabled={!selectedOpt}>
          SUBMIT REPORT
        </button>
      </motion.div>
    </div>
  );
}
