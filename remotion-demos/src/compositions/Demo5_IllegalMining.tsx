import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const Demo5_IllegalMining: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });

    // Radar sweep animation
    const sweepAngle = interpolate(frame, [0, 270], [0, 360], { extrapolateRight: 'clamp' });

    // Detected hotspots appearing over time
    const hotspots = [
        { cx: 420, cy: 340, r: 18, frame: 60, label: 'Site A', ha: '2.3 ha' },
        { cx: 550, cy: 280, r: 22, frame: 90, label: 'Site B', ha: '4.1 ha' },
        { cx: 480, cy: 420, r: 14, frame: 120, label: 'Site C', ha: '1.8 ha' },
        { cx: 620, cy: 360, r: 26, frame: 150, label: 'Site D', ha: '5.7 ha' },
    ];

    const boundaryOpacity = interpolate(frame, [30, 60], [0, 1], { extrapolateRight: 'clamp' });
    const statsOpacity = interpolate(frame, [180, 210], [0, 1], { extrapolateRight: 'clamp' });
    const alertPulse = Math.sin(frame * 0.18) * 0.3 + 0.7;

    return (
        <AbsoluteFill
            style={{
                background: 'linear-gradient(135deg, #100a00 0%, #1a0f00 50%, #0f0a00 100%)',
                fontFamily: 'Inter, system-ui, sans-serif',
                overflow: 'hidden',
            }}
        >
            {/* Header */}
            <div style={{ position: 'absolute', top: 60, left: 100, opacity: titleOpacity }}>
                <div style={{ fontSize: 14, color: '#ef4444', textTransform: 'uppercase', letterSpacing: 4, marginBottom: 8 }}>Compliance Monitoring</div>
                <div style={{ fontSize: 48, fontWeight: 900, color: '#f1f5f9', lineHeight: 1 }}>Illegal Mining Detection</div>
                <div style={{ fontSize: 19, color: '#64748b', marginTop: 10 }}>Activity flagged outside approved lease boundary</div>
            </div>

            {/* Radar/Map panel */}
            <div style={{ position: 'absolute', top: 190, left: 100, width: 740, height: 490, borderRadius: 20, overflow: 'hidden', border: '1px solid rgba(239,68,68,0.2)', background: '#0a0f08' }}>
                <svg width="740" height="490" style={{ position: 'absolute', inset: 0 }}>
                    {/* Grid */}
                    {Array.from({ length: 8 }).map((_, i) => (
                        <line key={`v${i}`} x1={i * 105} y1={0} x2={i * 105} y2={490} stroke="rgba(255,255,255,0.05)" strokeWidth={1} />
                    ))}
                    {Array.from({ length: 6 }).map((_, i) => (
                        <line key={`h${i}`} x1={0} y1={i * 82} x2={740} y2={i * 82} stroke="rgba(255,255,255,0.05)" strokeWidth={1} />
                    ))}

                    {/* Approved mining zone boundary */}
                    <ellipse cx="500" cy="350" rx="180" ry="130" fill="none" stroke="#22c55e" strokeWidth="2" strokeDasharray="8,4" opacity={boundaryOpacity} />
                    <text x="700" y="240" fill="#22c55e" fontSize="12" opacity={boundaryOpacity}>Approved Lease</text>

                    {/* Buffer zone */}
                    <ellipse cx="500" cy="350" rx="230" ry="175" fill="none" stroke="#fbbf24" strokeWidth="1" strokeDasharray="4,6" opacity={boundaryOpacity * 0.5} />

                    {/* Radar sweep */}
                    <defs>
                        <radialGradient id="sweep" cx="0%" cy="50%">
                            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.4" />
                            <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
                        </radialGradient>
                    </defs>
                    <path
                        d={`M 500 350 L ${500 + 300 * Math.cos((sweepAngle - 30) * Math.PI / 180)} ${350 + 300 * Math.sin((sweepAngle - 30) * Math.PI / 180)} A 300 300 0 0 1 ${500 + 300 * Math.cos(sweepAngle * Math.PI / 180)} ${350 + 300 * Math.sin(sweepAngle * Math.PI / 180)} Z`}
                        fill="url(#sweep)"
                        opacity={0.5}
                    />

                    {/* Detected illegal hotspots */}
                    {hotspots.map((hs) => {
                        if (frame < hs.frame) return null;
                        const pop = spring({ frame: frame - hs.frame, fps, config: { damping: 10, stiffness: 200 } });
                        const scale = interpolate(pop, [0, 1], [0, 1]);
                        const alpha = alertPulse;
                        return (
                            <g key={hs.label} transform={`scale(${scale}) translate(${hs.cx * (1 - scale)}, ${hs.cy * (1 - scale)})`}>
                                <circle cx={hs.cx} cy={hs.cy} r={hs.r * 2.5} fill="rgba(239,68,68,0.12)" />
                                <circle cx={hs.cx} cy={hs.cy} r={hs.r} fill={`rgba(239,68,68,${alpha})`} stroke="#ef4444" strokeWidth="2" />
                                <text x={hs.cx + hs.r + 6} y={hs.cy - 6} fill="#ef4444" fontSize="12" fontWeight="700">{hs.label}</text>
                                <text x={hs.cx + hs.r + 6} y={hs.cy + 10} fill="#94a3b8" fontSize="11">{hs.ha}</text>
                            </g>
                        );
                    })}
                </svg>
                <div style={{ position: 'absolute', top: 16, left: 20, background: 'rgba(0,0,0,0.7)', padding: '6px 14px', borderRadius: 8, fontSize: 13, color: '#ef4444', fontWeight: 600 }}>LIVE — Change Detection Overlay</div>
            </div>

            {/* Stats / verdict */}
            <div style={{ position: 'absolute', top: 190, right: 100, width: 520, display: 'flex', flexDirection: 'column', gap: 16, opacity: statsOpacity }}>
                <div style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 16, padding: '20px 24px' }}>
                    <div style={{ fontSize: 42, fontWeight: 900, color: '#ef4444' }}>4 Sites</div>
                    <div style={{ fontSize: 15, color: '#94a3b8', marginTop: 4 }}>Illegal activity detected outside permit boundary</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 16, padding: '20px 24px' }}>
                    <div style={{ fontSize: 36, fontWeight: 900, color: '#fbbf24' }}>13.9 ha</div>
                    <div style={{ fontSize: 15, color: '#94a3b8', marginTop: 4 }}>Total unauthorized expansion area</div>
                </div>
                {[
                    { label: 'Detection Method', value: 'BSI + NDVI multi-date fusion' },
                    { label: 'Baseline Date', value: 'January 15, 2024' },
                    { label: 'Detection Date', value: 'November 3, 2024' },
                    { label: 'Evidence Export', value: 'PDF Report + GeoJSON Zones' },
                ].map((item) => (
                    <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        <span style={{ fontSize: 14, color: '#64748b' }}>{item.label}</span>
                        <span style={{ fontSize: 14, color: '#e2e8f0', fontWeight: 600 }}>{item.value}</span>
                    </div>
                ))}
            </div>
        </AbsoluteFill>
    );
};
