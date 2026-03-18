import React from 'react';

const MetricsPanel = ({ metrics, sessionTime, showFFT = false }) => {
  const formatValue = (value, decimals = 1) => {
    return Number(value).toFixed(decimals);
  };

  const MetricCard = ({ label, value, unit, color = '#E8F1FF' }) => (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color }}>
        {formatValue(value)}
        <span className="metric-unit">{unit}</span>
      </div>
    </div>
  );

  return (
    <>
      {showFFT ? (
        <>
          <MetricCard
            label="PEAK FREQUENCY"
            value={metrics.peak_frequency ?? 0}
            unit="Hz"
            color={(metrics.peak_frequency ?? 0) > 0 ? '#6EC1FF' : '#666666'}
          />

          <MetricCard
            label="SPECTRAL CENTROID"
            value={metrics.spectral_centroid ?? 0}
            unit="Hz"
            color={(metrics.spectral_centroid ?? 0) > 0 ? '#6EC1FF' : '#666666'}
          />

          <MetricCard
            label="SPECTRAL ROLLOFF"
            value={metrics.spectral_rolloff ?? 0}
            unit="Hz"
            color={(metrics.spectral_rolloff ?? 0) > 0 ? '#6EC1FF' : '#666666'}
          />

          <MetricCard
            label="SPECTRAL FLATNESS"
            value={metrics.spectral_flatness ?? 0}
            unit=""
            color={(metrics.spectral_flatness ?? 0) > 0 ? '#6EC1FF' : '#666666'}
          />
        </>
      ) : (
        <>
          <MetricCard
            label="BPM"
            value={metrics.bpm}
            unit=""
            color={metrics.bpm > 0 ? '#4DA3FF' : '#666666'}
          />

          <MetricCard
            label="RMS"
            value={metrics.rms}
            unit="V"
            color={metrics.rms > 0 ? '#6EC1FF' : '#666666'}
          />

          <MetricCard
            label="PEAK"
            value={metrics.peak}
            unit="V"
            color={metrics.peak > 0 ? '#6EC1FF' : '#666666'}
          />

          <MetricCard
            label="FREQUENCY"
            value={metrics.frequency}
            unit="Hz"
            color={metrics.frequency > 0 ? '#6EC1FF' : '#666666'}
          />
        </>
      )}
      
      <div className="session-time">
        <div className="metric-label">SESSION TIME</div>
        <div className="metric-value">{sessionTime}</div>
      </div>
    </>
  );
};

export default MetricsPanel;
