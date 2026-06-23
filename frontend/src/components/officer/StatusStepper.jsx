import React from 'react';

export default function StatusStepper({ status, onUpdateStatus, onCompleteTask, onBackup }) {
  const steps = [
    { id: 'assigned', label: 'Dispatched' },
    { id: 'enroute', label: 'En Route' },
    { id: 'on_site', label: 'On Site' },
    { id: 'resolved', label: 'Resolved' }
  ];

  const displayStatus = status === 'needs_backup' ? 'on_site' : status;
  const currentIndex = steps.findIndex(s => s.id === displayStatus);
  
  // Calculate line fill
  let fillPct = 0;
  if (currentIndex === 1) fillPct = 33;
  if (currentIndex === 2) fillPct = 66;
  if (currentIndex >= 3) fillPct = 100;

  return (
    <div style={{ marginTop: 'auto' }}>
      <div className="stepper-container">
        <div className="stepper-line">
          <div className="stepper-line-fill" style={{ width: `${fillPct}%` }}></div>
        </div>
        
        {steps.map((step, idx) => {
          let cls = '';
          if (idx < currentIndex) cls = 'completed';
          else if (idx === currentIndex) cls = 'current';
          if (status === 'needs_backup' && step.id === 'on_site') cls += ' critical';

          return (
            <div key={step.id} className={`step-item ${cls}`}>
              <div className="step-circle"></div>
              <div className="step-label">{step.label}</div>
            </div>
          );
        })}
      </div>

      <div className="step-btn-container">
        {status === 'assigned' && (
          <button className="step-btn btn-enroute" onClick={() => onUpdateStatus('enroute')}>
            TAP WHEN EN ROUTE
          </button>
        )}
        {status === 'enroute' && (
          <button className="step-btn btn-arrived" onClick={() => onUpdateStatus('on_site')}>
            TAP WHEN ARRIVED
          </button>
        )}
        {(status === 'on_site' || status === 'needs_backup') && (
          <>
            <button 
              className="step-btn btn-backup" 
              onClick={onBackup}
              disabled={status === 'needs_backup'}
              style={{ opacity: status === 'needs_backup' ? 0.5 : 1, cursor: status === 'needs_backup' ? 'not-allowed' : 'pointer' }}
            >
              {status === 'needs_backup' ? 'BACKUP REQUESTED' : 'NEEDS BACKUP'}
            </button>
            <button className="step-btn btn-complete" onClick={onCompleteTask}>
              TASK COMPLETE
            </button>
          </>
        )}
      </div>
    </div>
  );
}
