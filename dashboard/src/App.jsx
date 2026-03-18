import React, { useState, useEffect, useCallback, useRef } from 'react'
import WaveformVisualization from './components/WaveformVisualization'
import MetricsPanel from './components/MetricsPanel'
import ConnectionStatus from './components/ConnectionStatus'
import AverageMetricsPanel from './components/AverageMetricsPanel'
import SessionSidebar, { HistoryIcon } from './components/SessionSidebar'
import './styles.css'
import { useWebSocket } from './hooks/useWebSocket'

function App() {

    const [currentMetrics, setCurrentMetrics] = useState({
        bpm: 0,
        rms: 0,
        peak: 0,
        frequency: 0,
        peak_frequency: 0,
        spectral_centroid: 0,
        spectral_rolloff: 0,
        spectral_flatness: 0
    })

    const [sessionTime, setSessionTime] = useState(0)
    const [waveformData, setWaveformData] = useState([])
    const [sessionStartTime, setSessionStartTime] = useState(null)

    const [sessionActive, setSessionActive] = useState(false)
    const [activeSessionId, setActiveSessionId] = useState(null)
    const [archivedSessionId, setArchivedSessionId] = useState(null)

    const [averages, setAverages] = useState(null)
    const [currentSessionId, setCurrentSessionId] = useState(null)

    const [sidebarOpen, setSidebarOpen] = useState(false)
    const [showFFT, setShowFFT] = useState(false)
    const [waveformResetKey, setWaveformResetKey] = useState(0)

    const timerRef = useRef(null)

    const { isConnected, lastMessage, connectionStatus } = useWebSocket('ws://localhost:8000/ws/audio')



    /* ---------------- WEBSOCKET STREAM ---------------- */

    useEffect(() => {

        if (!lastMessage) return

        let data

        try {
            data = JSON.parse(lastMessage)
        } catch {
            return
        }

        if (data.session_id) {
            setActiveSessionId(data.session_id)
            setSessionActive(true)
            setArchivedSessionId(null)
            setCurrentSessionId(null)
            setAverages(null)
        }

        const samples = data.samples || data.data?.samples

        if (samples && Array.isArray(samples)) {

            setWaveformData(prev => {
                const next = prev.length + samples.length > 40000 ? prev.slice(samples.length) : prev
                return [...next, ...samples]
            })

            if (!sessionStartTime) {

                const ts = Number(data.timestamp)

                const start = Number.isFinite(ts)
                    ? (ts < 1e12 ? ts * 1000 : ts)
                    : Date.now()

                setSessionStartTime(start)
                setSessionActive(true)
                setSessionTime(0)
            }
        }

        const metrics = data.metrics || data.data?.metrics || {}

        setCurrentMetrics(prev => {

            const next = {
                bpm: metrics.bpm ?? prev.bpm,
                rms: metrics.rms ?? prev.rms,
                peak: metrics.peak ?? prev.peak,
                frequency: metrics.frequency ?? prev.frequency,
                peak_frequency: metrics.peak_frequency ?? prev.peak_frequency,
                spectral_centroid: metrics.spectral_centroid ?? prev.spectral_centroid,
                spectral_rolloff: metrics.spectral_rolloff ?? prev.spectral_rolloff,
                spectral_flatness: metrics.spectral_flatness ?? prev.spectral_flatness
            }

            if (
                next.bpm === prev.bpm &&
                next.rms === prev.rms &&
                next.peak === prev.peak &&
                next.frequency === prev.frequency &&
                next.peak_frequency === prev.peak_frequency &&
                next.spectral_centroid === prev.spectral_centroid &&
                next.spectral_rolloff === prev.spectral_rolloff &&
                next.spectral_flatness === prev.spectral_flatness
            ) {
                return prev
            }

            return next
        })

    }, [lastMessage, sessionStartTime])



    /* ---------------- DASHBOARD GLOW ---------------- */

    useEffect(() => {

        const rms = currentMetrics.rms || 0
        const normalized = Math.min(rms * 3, 1)

        document.documentElement.style.setProperty('--wave-glow', normalized)

    }, [currentMetrics.rms])



    /* ---------------- SESSION TIMER ---------------- */

    useEffect(() => {

        if (!sessionActive || !sessionStartTime) return

        timerRef.current = setInterval(() => {

            const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000)

            setSessionTime(elapsed)

        }, 1000)

        return () => {

            if (timerRef.current) {
                clearInterval(timerRef.current)
                timerRef.current = null
            }

        }

    }, [sessionActive, sessionStartTime])



    /* ---------------- WAVEFORM RESET ---------------- */

    const handleRefreshWaveform = useCallback(() => {

        setWaveformData([])
        setWaveformResetKey(prev => prev + 1)

    }, [])



    /* ---------------- STOP SESSION ---------------- */

    const handleStopSession = useCallback(() => {

        if (!activeSessionId) return

        fetch(`/api/sessions/${activeSessionId}/stop`, { method: 'POST' })
            .then(res => res.json())
            .then(() => {

                if (timerRef.current) {
                    clearInterval(timerRef.current)
                    timerRef.current = null
                }

                setSessionActive(false)
                setArchivedSessionId(activeSessionId)
                setActiveSessionId(null)
                setSessionStartTime(null)

            })
            .catch(err => console.error('Stop failed', err))

    }, [activeSessionId])



    /* ---------------- EXPORT FULL SESSION ---------------- */

    const handleExportSession = useCallback(() => {

        const id = activeSessionId || archivedSessionId || currentSessionId
        if (!id) return

        const mode = showFFT ? 'fft' : 'wave'
        fetch(`/api/session/${id}/metrics?mode=${mode}`)
            .then(res => res.json())
            .then(data => {

                setAverages(data.averages || {})
                setCurrentSessionId(data.session_id)

                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
                const url = URL.createObjectURL(blob)

                const a = document.createElement('a')
                a.href = url
                a.download = `session_${id}.json`

                document.body.appendChild(a)
                a.click()

                a.remove()
                URL.revokeObjectURL(url)

            })
            .catch(err => console.error('Export failed', err))

    }, [activeSessionId, archivedSessionId, currentSessionId, showFFT])



    /* ---------------- EXPORT AVERAGES ---------------- */

    const handleExportAverages = useCallback(() => {

        const id = activeSessionId || archivedSessionId || currentSessionId
        if (!id) return

        const mode = showFFT ? 'fft' : 'wave'
        fetch(`/api/session/${id}/averages?mode=${mode}`)
            .then(res => res.json())
            .then(data => {

                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
                const url = URL.createObjectURL(blob)

                const a = document.createElement('a')
                a.href = url
                a.download = `session_averages_${id}.json`

                document.body.appendChild(a)
                a.click()

                a.remove()
                URL.revokeObjectURL(url)

            })
            .catch(err => console.error('Export averages failed', err))

    }, [activeSessionId, archivedSessionId, currentSessionId, showFFT])



    /* ---------------- LOAD HISTORY SESSION ---------------- */

    const handleLoadSession = useCallback((sessionId) => {

        fetch(`/api/session/${sessionId}`)
            .then(res => res.json())
            .then(data => {

                setAverages(data.averages || {})
                setCurrentSessionId(data.session_id)

                setSessionActive(false)
                setActiveSessionId(null)
                setArchivedSessionId(sessionId)

            })
            .catch(err => console.error('Load session failed', err))

    }, [])



    const canExport = activeSessionId || archivedSessionId || currentSessionId



    const formatSessionTime = useCallback(seconds => {

        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60

        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`

    }, [])



    return (

        <div className="dashboard">

            <header className="header">

                <h1>Audio Waveform Analyzer</h1>

                <div className="header__right">

                    <ConnectionStatus
                        isConnected={isConnected}
                        status={connectionStatus}
                    />

                    <HistoryIcon
                        onClick={() => setSidebarOpen(open => !open)}
                        isOpen={sidebarOpen}
                    />

                </div>

                <SessionSidebar
                    isOpen={sidebarOpen}
                    onClose={() => setSidebarOpen(false)}
                    onSelectSession={handleLoadSession}
                    showFFT={showFFT}
                    onToggleFFT={() => setShowFFT(v => !v)}
                />

            </header>



            <div className="main-content">

                <div className="waveform-panel">

                    <h2 className="panel-title">Real-Time Waveform</h2>

                    <div className="waveform-container">

                        <WaveformVisualization
                            key={waveformResetKey}
                            data={waveformData}
                            isConnected={isConnected}
                            showFFT={showFFT}
                        />

                    </div>

                </div>

                <div className="metrics-panel">

                    <MetricsPanel
                        metrics={currentMetrics}
                        sessionTime={formatSessionTime(sessionTime)}
                        showFFT={showFFT}
                    />

                </div>

                {averages && (

                    <AverageMetricsPanel
                        averages={averages}
                        sessionId={currentSessionId}
                        animate={true}
                        showFFT={showFFT}
                    />

                )}

            </div>



            <div className="controls-row" style={{ justifyContent: "space-between" }}>

                <button className="btn" onClick={handleRefreshWaveform}>
                    Refresh Waveform
                </button>

                <div style={{ display: "flex", gap: "12px" }}>

                    <button
                        className="btn btn-export-averages"
                        onClick={handleExportAverages}
                        disabled={!canExport}
                    >
                        Export Averages
                    </button>

                    <button
                        className="btn btn-export"
                        onClick={handleExportSession}
                        disabled={!canExport}
                    >
                        Export Metrics
                    </button>

                    <button
                        className="btn btn-stop"
                        onClick={handleStopSession}
                        disabled={!activeSessionId}
                    >
                        Stop Session
                    </button>

                </div>

            </div>

        </div>

    )

}

export default App