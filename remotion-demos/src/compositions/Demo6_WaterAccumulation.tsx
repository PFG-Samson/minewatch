import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const Demo6_WaterAccumulation: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });

    // Water rising animation
    const waterLevel = interpolate(frame, [40, 200], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
    const turbidityPulse = Math.sin(frame * 0.12) * 0.15 + 0.85;
    const statsOpacity = interpolate(frame, [180, 210], [0, 1], { extrapolateRight: 'clamp' });

    const gridCols = 16;
    const gridRows = 10;

    const riskZones = [
        { label: 'Low Turbidity', color: '#06b6d4', threshold: 0.3 },
        { label: 'Medium Risk', color: '#f59e0b', threshold: 0.6 },
        { label: 'High Risk — Sedimentation', color: '#ef4444', threshold: 0.85 },
    ];

    return (
        <AbsoluteFill
            style={{
                background: 'linear-gradient(135deg, #040d14 0%, #061525 100%)',
                fontFamily: 'Inter, system-ui, sans-serif',
                overflow: 'hidden',
            }}
        >
            {/* Header */}
            <div style={{ position: 'absolute', top: 60, left: 100, opacity: titleOpacity }}>
                <div style={{ fontSize: 14, color: '#06b6d4', textTransform: 'uppercase', letterSpacing: 4, marginBottom: 8 }}>Environmental Monitoring</div>
                <div style={{ fontSize: 48, fontWeight: 900, color: '#f1f5f9', lineHeight: 1 }}>Water Accumulation &amp; Turbidity</div>
                <div style={{ fontSize: 19, color: '#64748b', marginTop: 10 }}>NDWI = (Green − NIR) / (Green + NIR) · Sedimentation risk mapping</div>
            </div>

            {/* Main panel */}
            <div style={{ position: 'absolute', top: 190, left: 100, width: 740, height: 500, borderRadius: 20, overflow: 'hidden', border: '1px solid rgba(6,182,212,0.25)', background: '#020d14' }}>
                {/* NDWI heatmap grid */}
                <div style={{ position: 'absolute', inset: 0, display: 'grid', gridTemplateColumns: `repeat(${gridCols}, 1fr)`, gridTemplateRows: `repeat(${gridRows}, 1fr)`, gap: 2, padding: 12 }}>
                    {Array.from({ length: gridRows * gridCols }).map((_, i) => {
                        const row = Math.floor(i / gridCols);
                        const col = i % gridCols;
                        const cx = col / gridCols;
                        const cy = row / gridRows;
                        // Simulate water body + drainage channels
                        const isLake = Math.sqrt((cx - 0.3) ** 2 * 4 + (cy - 0.5) ** 2 * 6) < 0.15 * waterLevel;
                        const isRiver = Math.abs(cx * 2 - cy * 1.5 - 0.8) < 0.06 * waterLevel;
                        const isSediment = Math.sqrt((cx - 0.65) ** 2 * 3 + (cy - 0.35) ** 2 * 5) < 0.12 * waterLevel;
                        const intensity = Math.random() * 0.3;
                        return (
                            <div key={i} style={{
                                borderRadius: 2,
                                background: isSediment
                                    ? `rgba(239,68,68,${0.5 + intensity})`
                                    : isLake || isRiver
                                        ? `rgba(6,182,212,${(0.4 + intensity) * turbidityPulse})`
                                        : `rgba(34,197,94,${0.08 + intensity * 0.2})`,
                                boxShadow: (isLake || isRiver) ? `0 0 6px rgba(6,182,212,0.5)` : isSediment ? '0 0 6px rgba(239,68,68,0.4)' : 'none',
                            }} />
                        );
                    })}
                </div>

                {/* Labels */}
                <div style={{ position: 'absolute', top: 16, left: 20, background: 'rgba(0,0,0,0.7)', padding: '6px 14px', borderRadius: 8, fontSize: 13, color: '#06b6d4', fontWeight: 600 }}>NDWI Change Map</div>

                {/* Legend */}
                <div style={{ position: 'absolute', bottom: 14, left: 20, display: 'flex', gap: 18 }}>
                    {riskZones.map((z) => (
                        <div key={z.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div style={{ width: 12, height: 12, borderRadius: 2, background: z.color }} />
                            <span style={{ fontSize: 11, color: '#94a3b8' }}>{z.label}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Risk indicators */}
            <div style={{ position: 'absolute', top: 190, right: 100, width: 520, display: 'flex', flexDirection: 'column', gap: 16, opacity: statsOpacity }}>
                <div style={{ background: 'rgba(239,68,68,0.09)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 16, padding: '20px 24px' }}>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                        <span style={{ fontSize: 36 }}>⚠️</span>
                        <div>
                            <div style={{ fontSize: 18, fontWeight: 700, color: '#ef4444' }}>Sedimentation Risk Detected</div>
                            <div style={{ fontSize: 13, color: '#94a3b8', marginTop: 4 }}>Downstream runoff accumulation from pit drainage</div>
                        </div>
                    </div>
                </div>
                {[
                    { value: '+0.31', label: 'NDWI Delta', color: '#06b6d4' },
                    { value: '8.2 ha', label: 'New Water Accumulation', color: '#06b6d4' },
                    { value: '2.1 ha', label: 'High-Turbidity Zone', color: '#ef4444' },
                    { value: '>0.20', label: 'NDWI Alert Threshold', color: '#64748b' },
                ].map((s, i) => {
                    const sp = spring({ frame: frame - 195 - i * 12, fps, config: { damping: 14 } });
                    return (
                        <div key={i} style={{ background: 'rgba(255,255,255,0.04)', border: `1px solid ${s.color}33`, borderRadius: 14, padding: '16px 22px', transform: `translateY(${interpolate(sp, [0, 1], [20, 0])}px)`, backdropFilter: 'blur(10px)' }}>
                            <div style={{ fontSize: 32, fontWeight: 900, color: s.color }}>{s.value}</div>
                            <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>{s.label}</div>
                        </div>
                    );
                })}
            </div>
        </AbsoluteFill>
    );
};
