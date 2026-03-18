import React, { useEffect, useState } from 'react';

/**
 * Visual summary of session averages: RMS bar, Peak gauge, BPM line, overall loudness.
 * Appears below MetricsPanel after export or when a previous session is loaded.
 */
const AverageMetricsPanel = ({ averages, sessionId, animate = true, showFFT = false }) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (!animate) {
      setMounted(true);
      return;
    }
    const t = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(t);
  }, [animate]);

  if (!averages || typeof averages !== 'object') return null;

  const avgRms = Number(averages.avg_rms ?? 0);
  const avgPeak = Number(averages.avg_peak ?? 0);
  const avgBpm = Number(averages.avg_bpm ?? 0);
  const loudness = avgRms > 0 ? Math.min(100, Math.round(avgRms * 120)) : 0;

  const rmsPercent = Math.min(100, avgRms * 100);
  const peakPercent = Math.min(100, avgPeak * 100);
  const bpmPercent = Math.min(100, avgBpm / 2); // Scale BPM (0-200) to percentage

  const avgPeakFrequency = Number(averages.avg_peak_frequency ?? 0);
  const avgSpectralCentroid = Number(averages.avg_spectral_centroid ?? 0);
  const avgSpectralRolloff = Number(averages.avg_spectral_rolloff ?? 0);
  const avgSpectralFlatness = Number(averages.avg_spectral_flatness ?? 0);

  return (
    <section
      className={`average-metrics-panel ${mounted ? 'average-metrics-panel--visible' : ''}`}
      aria-label="Session average metrics"
    >
      <h2 className="panel-title average-metrics-panel__title">Session Averages</h2>
      {sessionId && (
        <p className="average-metrics-panel__session-id">Session: {sessionId}</p>
      )}
      <div className="average-metrics-panel__grid">
        {showFFT ? (
          <>
            <div className="average-metrics-card">
              <div className="average-metrics-card__label">Avg Peak Frequency</div>
              <div className="average-metrics-card__value">
                {avgPeakFrequency.toFixed(1)}
                <span className="average-metrics-card__unit">Hz</span>
              </div>
            </div>

            <div className="average-metrics-card">
              <div className="average-metrics-card__label">Avg Spectral Centroid</div>
              <div className="average-metrics-card__value">
                {avgSpectralCentroid.toFixed(1)}
                <span className="average-metrics-card__unit">Hz</span>
              </div>
            </div>

            <div className="average-metrics-card">
              <div className="average-metrics-card__label">Avg Spectral Rolloff</div>
              <div className="average-metrics-card__value">
                {avgSpectralRolloff.toFixed(1)}
                <span className="average-metrics-card__unit">Hz</span>
              </div>
            </div>

            <div className="average-metrics-card">
              <div className="average-metrics-card__label">Avg Spectral Flatness</div>
              <div className="average-metrics-card__value">{avgSpectralFlatness.toFixed(4)}</div>
            </div>
          </>
        ) : (
          <>
            {/* Overall loudness — large numeric */}
            <div className="average-metrics-card average-metrics-card--loudness">
              <div className="average-metrics-card__label">Overall Loudness</div>
              <div className="average-metrics-card__value average-metrics-card__value--loudness">
                {loudness}
                <span className="average-metrics-card__unit">%</span>
              </div>
            </div>

            {/* RMS — horizontal bar */}
            <div className="average-metrics-card">
              <div className="average-metrics-card__label">Avg RMS</div>
              <div className="average-metrics-bar">
                <div
                  className="average-metrics-bar__fill"
                  style={{ width: `${rmsPercent}%` }}
                />
              </div>
              <div className="average-metrics-card__small-value">{avgRms.toFixed(3)}</div>
            </div>

            {/* Peak — radial gauge */}
            <div className="average-metrics-card">
              <div className="average-metrics-card__label">Avg Peak</div>
              <div className="average-metrics-gauge">
                <svg viewBox="0 0 100 100" className="average-metrics-gauge__svg">
                  <circle
                    className="average-metrics-gauge__bg"
                    cx="50"
                    cy="50"
                    r="42"
                    fill="none"
                    strokeWidth="8"
                  />
                  <circle
                    className="average-metrics-gauge__arc"
                    cx="50"
                    cy="50"
                    r="42"
                    fill="none"
                    strokeWidth="8"
                    strokeDasharray={`${(peakPercent / 100) * 264} 264`}
                    transform="rotate(-90 50 50)"
                  />
                </svg>
                <span className="average-metrics-gauge__value">{avgPeak.toFixed(3)}</span>
              </div>
            </div>

            {/* BPM — line indicator */}
            <div className="average-metrics-card">
              <div className="average-metrics-card__label">Avg BPM</div>
              <div className="average-metrics-line">
                <div
                  className="average-metrics-line__fill"
                  style={{ width: `${bpmPercent}%` }}
                />
              </div>
              <div className="average-metrics-card__small-value">{avgBpm.toFixed(1)}</div>
            </div>
          </>
        )}
      </div>
    </section>
  );
};

export default AverageMetricsPanel;
