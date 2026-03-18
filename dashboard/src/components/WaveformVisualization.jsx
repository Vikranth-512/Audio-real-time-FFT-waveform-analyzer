import React, { useRef, useEffect, useState, useCallback } from 'react'

const WaveformVisualization = ({ data, isConnected, showFFT = false }) => {

    const canvasRef = useRef(null)
    const glRef = useRef(null)
    const bufferRef = useRef(null)
    const programRef = useRef(null)
    const animationFrameRef = useRef(null)

    const audioCtxRef = useRef(null)
    const analyserRef = useRef(null)
    const fftDataRef = useRef(null)

    const fftMapRef = useRef(null)
    const fftPeaksRef = useRef(null)
    const fftSmoothRef = useRef(null)
    const fftCanvasRef = useRef(null)

    const [isChartReady, setIsChartReady] = useState(false)

    const SAMPLE_RATE = 8000
    const TARGET_SAMPLES_PER_PIXEL = 2
    const MAX_WINDOW_SECONDS = 1.5
    const MAX_SAMPLES = SAMPLE_RATE * MAX_WINDOW_SECONDS

    const FFT_SIZE = 1024
    const FFT_BARS = 96
    const PEAK_DECAY = 0.95
    const FFT_SMOOTH = 0.25

    /* -------------------------------------------------- */
    /* FFT MAP (LOG SCALE) */
    /* -------------------------------------------------- */

    const ensureFftMap = useCallback(() => {

        if (fftMapRef.current) return

        const nyquist = SAMPLE_RATE / 2
        const minF = 20
        const maxF = Math.min(2000, nyquist)
        const binHz = SAMPLE_RATE / FFT_SIZE

        const edges = []

        for (let i = 0; i <= FFT_BARS; i++) {

            const t = i / FFT_BARS
            edges.push(minF * Math.pow(maxF / minF, t))

        }

        const ranges = []

        for (let i = 0; i < FFT_BARS; i++) {

            const a = Math.max(1, Math.floor(edges[i] / binHz))
            const b = Math.max(a + 1, Math.floor(edges[i + 1] / binHz))
            ranges.push([a, Math.min(b, FFT_SIZE / 2)])

        }

        fftMapRef.current = ranges

    }, [])

    /* -------------------------------------------------- */
    /* WEB AUDIO FFT INITIALIZATION */
    /* -------------------------------------------------- */

    const initWebAudioFFT = useCallback(() => {

        if (audioCtxRef.current) return

        const audioCtx = new (window.AudioContext || window.webkitAudioContext)()

        const analyser = audioCtx.createAnalyser()

        analyser.fftSize = FFT_SIZE
        analyser.smoothingTimeConstant = 0.8

        audioCtxRef.current = audioCtx
        analyserRef.current = analyser

        fftDataRef.current = new Float32Array(analyser.frequencyBinCount)

        fftPeaksRef.current = new Float32Array(FFT_BARS)
        fftSmoothRef.current = new Float32Array(FFT_BARS)

    }, [])

    /* -------------------------------------------------- */
    /* FFT BAR COMPUTATION */
    /* -------------------------------------------------- */

    const computeFftBars = useCallback(() => {

        ensureFftMap()

        if (!analyserRef.current) return null

        const analyser = analyserRef.current

        analyser.getFloatFrequencyData(fftDataRef.current)

        const bins = fftDataRef.current
        const ranges = fftMapRef.current

        const peaks = fftPeaksRef.current
        const smooth = fftSmoothRef.current

        const bars = new Float32Array(FFT_BARS)

        let totalEnergy = 0

        for (let b = 0; b < FFT_BARS; b++) {

            const [a, z] = ranges[b]

            let v = -120

            for (let i = a; i < z; i++) {

                if (bins[i] > v) v = bins[i]

            }

            let normalized = Math.max(0, (v + 120) / 120)

            /* -------------------------------------------------- */
            /* PROFESSIONAL VISUALIZER UPGRADE (~20 lines) */
            /* -------------------------------------------------- */

            /* psychoacoustic frequency weighting */

            const freq = (b / FFT_BARS) * 2000
            const weight = 1 + Math.exp(-freq / 120)

            /* sub bass emphasis */

            const bassBoost = 1 + (1 / (1 + freq * 0.01))

            normalized *= weight * bassBoost

            /* exponential smoothing */

            smooth[b] = FFT_SMOOTH * normalized + (1 - FFT_SMOOTH) * smooth[b]

            /* animated interpolation */

            bars[b] = 0.4 * smooth[b] + 0.6 * bars[b]

            /* peak hold */

            peaks[b] = Math.max(bars[b], peaks[b] * PEAK_DECAY)

            totalEnergy += bars[b]

        }

        return { bars, peak: peaks, energy: totalEnergy / FFT_BARS }

    }, [ensureFftMap])

    /* -------------------------------------------------- */
    /* FFT RENDER */
    /* -------------------------------------------------- */

    const renderFft = useCallback(() => {

        if (!canvasRef.current) return

        const canvas = fftCanvasRef.current
        const ctx = canvas.getContext('2d')

        if (!ctx) return

        const dpr = window.devicePixelRatio || 1
        const w = Math.floor(canvas.clientWidth * dpr)
        const h = Math.floor(canvas.clientHeight * dpr)

        if (canvas.width !== w || canvas.height !== h) {

            canvas.width = w
            canvas.height = h

        }

        ctx.clearRect(0, 0, w, h)

        const res = computeFftBars()

        if (!res) return

        const padX = 20 * dpr
        const padY = 20 * dpr

        const innerW = w - padX * 2
        const innerH = h - padY * 2

        const barW = innerW / FFT_BARS

        /* dynamic glow based on energy */

        ctx.globalAlpha = 0.25 + res.energy * 0.6

        const glow = ctx.createRadialGradient(w / 2, h * 0.55, 0, w / 2, h * 0.55, Math.max(w, h) * 0.6)

        glow.addColorStop(0, 'rgba(110,193,255,0.45)')
        glow.addColorStop(1, 'rgba(110,193,255,0)')

        ctx.fillStyle = glow
        ctx.fillRect(0, 0, w, h)

        ctx.globalAlpha = 1

        const grad = ctx.createLinearGradient(0, padY, 0, padY + innerH)

        grad.addColorStop(0, 'rgba(207,239,255,0.95)')
        grad.addColorStop(0.5, 'rgba(110,193,255,0.9)')
        grad.addColorStop(1, 'rgba(77,163,255,0.7)')

        for (let i = 0; i < FFT_BARS; i++) {

            const v = Math.min(1, res.bars[i])
            const p = Math.min(1, res.peak[i])

            const x = padX + i * barW
            const barH = v * innerH
            const y = padY + (innerH - barH)

            ctx.fillStyle = grad
            ctx.fillRect(x, y, barW * 0.8, barH)

            const py = padY + (innerH - p * innerH)

            ctx.fillStyle = 'rgba(255,255,255,0.8)'
            ctx.fillRect(x, py, barW * 0.8, 2 * dpr)

        }

    }, [computeFftBars])

    /* -------------------------------------------------- */
    /* WEBGL WAVEFORM INIT */
    /* -------------------------------------------------- */

    useEffect(() => {

        if (!canvasRef.current) return

        const canvas = canvasRef.current
        const gl = canvas.getContext('webgl', { antialias: true, alpha: true })

        if (!gl) return

        const dpr = window.devicePixelRatio || 1

        canvas.width = canvas.clientWidth * dpr
        canvas.height = canvas.clientHeight * dpr

        gl.viewport(0, 0, canvas.width, canvas.height)

        glRef.current = gl

        /* ---------- SHADERS ---------- */

        const vertexShader = gl.createShader(gl.VERTEX_SHADER)

        gl.shaderSource(vertexShader, `
attribute vec2 position;
void main(){
    gl_Position = vec4(position, 0.0, 1.0);
}`)

        gl.compileShader(vertexShader)

        const fragmentShader = gl.createShader(gl.FRAGMENT_SHADER)

        gl.shaderSource(fragmentShader, `
precision mediump float;
void main(){
    gl_FragColor = vec4(0.43, 0.76, 1.0, 1.0);
}`)

        gl.compileShader(fragmentShader)

        const program = gl.createProgram()

        gl.attachShader(program, vertexShader)
        gl.attachShader(program, fragmentShader)
        gl.linkProgram(program)

        gl.useProgram(program)

        programRef.current = program

        /* ---------- BUFFER ---------- */

        const buffer = gl.createBuffer()
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer)

        bufferRef.current = buffer

        /* ---------- ATTRIBUTE ---------- */

        const positionLocation = gl.getAttribLocation(program, "position")

        gl.enableVertexAttribArray(positionLocation)

        gl.vertexAttribPointer(
            positionLocation,
            2,
            gl.FLOAT,
            false,
            0,
            0
        )

        /* ---------- RENDER SETTINGS ---------- */

        gl.lineWidth(2)

        gl.enable(gl.BLEND)
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)

        gl.clearColor(0, 0, 0, 0)
        gl.clear(gl.COLOR_BUFFER_BIT)

        /* ---------- FFT INIT ---------- */

        if (showFFT) {

            initWebAudioFFT()

        }

        setIsChartReady(true)

    }, [showFFT, initWebAudioFFT])

    /* -------------------------------------------------- */
    /* UPDATE CHART */
    /* -------------------------------------------------- */

    const updateChart = useCallback(() => {

        if (!isChartReady || data.length === 0) return

        if (showFFT) {

            if (analyserRef.current && data.length >= FFT_SIZE) {

                const audioCtx = audioCtxRef.current
                const analyser = analyserRef.current

                const buffer = audioCtx.createBuffer(1, FFT_SIZE, SAMPLE_RATE)

                const channel = buffer.getChannelData(0)

                const start = data.length - FFT_SIZE

                for (let i = 0; i < FFT_SIZE; i++) {

                    channel[i] = (data[start + i] - 2048) / 2048

                }

                const source = audioCtx.createBufferSource()

                source.buffer = buffer
                source.connect(analyser)
                source.start()

            }

            renderFft()

            return

        }

        const canvas = canvasRef.current

        const dpr = window.devicePixelRatio || 1

        if (canvas.width !== canvas.clientWidth * dpr) {

            canvas.width = canvas.clientWidth * dpr
            canvas.height = canvas.clientHeight * dpr

            if (glRef.current) {

                glRef.current.viewport(0, 0, canvas.width, canvas.height)

            }

        }

        if (glRef.current) {
            glRef.current.viewport(0, 0, canvas.width, canvas.height)
        }

        const canvasWidth = canvas.clientWidth

        const visibleSamples = canvasWidth * TARGET_SAMPLES_PER_PIXEL

        const samples = data.slice(-Math.min(visibleSamples, MAX_SAMPLES))

        const bucketSize = Math.max(1, Math.floor(samples.length / canvasWidth))

        const vertices = []

        let prevY = null

        for (let i = 0; i < samples.length; i += bucketSize) {

            let min = Infinity
            let max = -Infinity

            const end = Math.min(i + bucketSize, samples.length)

            for (let j = i; j < end; j++) {

                const v = (samples[j] - 2048) / 2048

                if (v < min) min = v
                if (v > max) max = v

            }

            const x = (i / samples.length) * 2 - 1

            /* midpoint waveform */
            const mid = (min + max) * 0.5

            /* temporal smoothing for oscilloscope look */
            let smooth

            if (prevY === null) {

                smooth = mid

            } else {

                smooth = prevY * 0.7 + mid * 0.3

            }

            prevY = smooth

            vertices.push(x, smooth)

        }

        if (glRef.current) {

            const gl = glRef.current

            const vertexArray = new Float32Array(vertices)

            gl.bindBuffer(gl.ARRAY_BUFFER, bufferRef.current)
            gl.bufferData(gl.ARRAY_BUFFER, vertexArray, gl.DYNAMIC_DRAW)

            const position = gl.getAttribLocation(programRef.current, "position")

            gl.enableVertexAttribArray(position)

            gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0)

            gl.clearColor(0, 0, 0, 0)
            gl.clear(gl.COLOR_BUFFER_BIT)



            const vertexCount = vertexArray.length / 2

            if (vertexCount === 0) return

            if (showFFT) {

                gl.drawArrays(gl.LINES, 0, vertexCount)

            } else {

                gl.drawArrays(gl.LINE_STRIP, 0, vertexCount)

            }

            }

        

    }, [data, isChartReady, showFFT, renderFft])

    /* -------------------------------------------------- */
    /* ANIMATION LOOP */
    /* -------------------------------------------------- */

    useEffect(() => {

        if (!isConnected) return

        const animate = () => {

            updateChart()

            animationFrameRef.current = requestAnimationFrame(animate)

        }

        animate()

        return () => {

            if (animationFrameRef.current) {

                cancelAnimationFrame(animationFrameRef.current)

            }

        }

    }, [isConnected, data, updateChart])

    /* -------------------------------------------------- */

    return (

        <div style={{
            width: '100%',
            height: 'clamp(320px,38vh,420px)',
            position: 'relative'
        }}>

            <canvas
                ref={canvasRef}
                style={{
                    width: '100%',
                    height: '100%',
                    position: 'absolute',
                    inset: 0,
                    display: showFFT ? 'none' : 'block'
                }}
            />

            <canvas
                ref={fftCanvasRef}
                style={{
                    width: '100%',
                    height: '100%',
                    position: 'absolute',
                    inset: 0,
                    display: showFFT ? 'block' : 'none'
                }}
            />

            {!isConnected && (

                <div style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#7A8CA8',
                    fontSize: '1.1rem'
                }}>
                    Waiting for audio data...
                </div>

            )}

        </div>

    )

}

export default WaveformVisualization