import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const Demo9_ChangeAnalysis: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });

    // Timeline scrubber animation
    const timelineProgress = interpolate(frame, [40, 220], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

    // Animated area counters
    const vegLoss = interpolate(frame, [150, 230], [0, 18.4], { extrapolateRight: 'clamp' });
    const soilGain = interpolate(frame, [155, 235], [0, 5.7], { extrapolateRight: 'clamp' });
    const waterGain = interpolate(frame, [160, 240], [0, 8.2], { extrapolateRight: 'clamp' });
    const alertCount = Math.floor(interpolate(frame, [165, 240], [0, 5], { extrapolateRight: 'clamp' }));

    const statsOpacity = interpolate(frame, [145, 175], [0, 1], { extrapolateRight: 'clamp' });

    const timePoints = ['Jan 2024', 'Mar 2024', 'May 2024', 'Jul 2024', 'Sep 2024', 'Nov 2024'];

    // Simulated trend lines (vegetation decline)
    const chartOpacity = interpolate(frame, [60, 100], [0, 1], { extrapolateRight: 'clamp' });

    return (
        <AbsoluteFill
            style={{
                background: 'linear-gradient(135deg, #0a0c14 0%, #0e1022 100%)',
                fontFamily: 'Inter, system-ui, sans-serif',
                overflow: 'hidden',
            }}
        >
            {/* Header */}
            <div style={{ position: 'absolute', top: 60, left: 100, opacity: titleOpacity }}>
                <div style={{ fontSize: 14, color: '#a78bfa', textTransform: 'uppercase', letterSpacing: 4, marginBottom: 8 }}>Temporal Intelligence</div>
                <div style={{ fontSize: 48, fontWeight: 900, color: '#f1f5f9', lineHeight: 1 }}>Change Analysis Dashboard</div>
                <div style={{ fontSize: 19, color: '#64748b', marginTop: 10 }}>Multi-date comparison · NDVI / BSI / NDWI index deltas over time</div>
            </div>

            {/* Timeline */}
            <div style={{ position: 'absolute', top: 195, left: 100, right: 100 }}>
                <div style={{ position: 'relative', height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 3 }}>
                    <div style={{ position: 'absolute', left: 0, width: `${timelineProgress * 100}%`, height: '100%', borderRadius: 3, background: 'linear-gradient(90deg, #7c3aed, #a78bfa)', boxShadow: '0 0 12px rgba(139,92,246,0.6)' }} />
                    {/* Scrubber head */}
                    <div style={{ position: 'absolute', top: -8, left: `${timelineProgress * 100}%`, transform: 'translateX(-50%)', width: 22, height: 22, borderRadius: '50%', background: '#a78bfa', boxShadow: '0 0 20px rgba(167,139,250,0.8)' }} />
                </div>
                {/* Labels */}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10 }}>
                    {timePoints.map((label, i) => {
                        const labelProgress = i / (timePoints.length - 1);
                        const isPast = timelineProgress > labelProgress;
                        return (
                            <div key={label} style={{ fontSize: 13, color: isPast ? '#a78bfa' : '#334155', fontWeight: isPast ? 600 : 400, transition: 'color 0.3s' }}>{label}</div>
                        );
                    })}
                </div>
            </div>

            {/* Chart — time series simulation */}
            <div style={{ position: 'absolute', top: 270, left: 100, width: 860, height: 360, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(139,92,246,0.18)', borderRadius: 20, overflow: 'hidden', opacity: chartOpacity }}>
                <svg width="860" height="360" style={{ position: 'absolute', inset: 0 }}>
                    {/* Y-axis grid */}
                    {[0, 0.25, 0.5, 0.75, 1].map((v) => (
                        <line key={v} x1={60} y1={30 + v * 280} x2={840} y2={30 + v * 280} stroke="rgba(255,255,255,0.05)" strokeWidth={1} />
                    ))}
                    {/* NDVI decline line */}
                    <polyline
                        points={`60,60 220,80 380,110 540,155 700,190 ${60 + timelineProgress * 780},${60 + timelineProgress * 150}`}
                        fill="none"
                        stroke="#22c55e"
                        strokeWidth={2.5}
                        strokeDasharray={`${timelineProgress * 1000} 1000`}
                    />
                    {/* BSI rise line */}
                    <polyline
                        points={`60,290 220,275 380,255 540,225 700,200 ${60 + timelineProgress * 780},${290 - timelineProgress * 95}`}
                        fill="none"
                        stroke="#f97316"
                        strokeWidth={2.5}
                        strokeDasharray={`${timelineProgress * 1000} 1000`}
                    />
                    {/* NDWI line */}
                    <polyline
                        points={`60,230 220,235 380,228 540,210 700,185 ${60 + timelineProgress * 780},${230 - timelineProgress * 70}`}
                        fill="none"
                        stroke="#06b6d4"
                        strokeWidth={2.5}
                        strokeDasharray={`${timelineProgress * 1000} 1000`}
                    />
                    {/* Legend */}
                    <text x={70} y={340} fill="#22c55e" fontSize="12" fontWeight="600">— NDVI (Vegetation)</text>
                    <text x={270} y={340} fill="#f97316" fontSize="12" fontWeight="600">— BSI (Bare Soil)</text>
                    <text x={470} y={340} fill="#06b6d4" fontSize="12" fontWeight="600">— NDWI (Water)</text>
                </svg>
                <div style={{ position: 'absolute', top: 14, left: 20, fontSize: 13, color: '#64748b', fontWeight: 600 }}>Index Trend — Jan–Nov 2024</div>
            </div>

            {/* Stats panel — right */}
            <div style={{ position: 'absolute', top: 270, right: 100, width: 450, display: 'flex', flexDirection: 'column', gap: 14, opacity: statsOpacity }}>
                {[
                    { label: 'Vegetation Loss', value: `${vegLoss.toFixed(1)} ha`, sub: 'NDVI Δ > −0.15', color: '#22c55e' },
                    { label: 'Bare Soil Expansion', value: `${soilGain.toFixed(1)} ha`, sub: 'BSI Δ > +0.10', color: '#f97316' },
                    { label: 'Water Accumulation', value: `${waterGain.toFixed(1)} ha`, sub: 'NDWI Δ > +0.20', color: '#06b6d4' },
                    { label: 'Active Alerts', value: `${alertCount}`, sub: 'High + Medium severity', color: '#ef4444' },
                ].map((s, i) => {
                    const sp = spring({ frame: frame - 155 - i * 12, fps, config: { damping: 14 } });
                    return (
                        <div key={i} style={{ background: 'rgba(255,255,255,0.03)', border: `1px solid ${s.color}44`, borderRadius: 16, padding: '18px 22px', transform: `translateY(${interpolate(sp, [0, 1], [20, 0])}px)`, backdropFilter: 'blur(10px)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <div style={{ fontSize: 13, color: '#64748b' }}>{s.label}</div>
                                    <div style={{ fontSize: 36, fontWeight: 900, color: s.color, lineHeight: 1.1, marginTop: 4 }}>{s.value}</div>
                                    <div style={{ fontSize: 12, color: '#475569', marginTop: 4 }}>{s.sub}</div>
                                </div>
                                <div style={{ width: 48, height: 48, borderRadius: '50%', background: `${s.color}15`, border: `2px solid ${s.color}44`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22 }}>
                                    {s.color === '#22c55e' ? '🌿' : s.color === '#f97316' ? '🏜️' : s.color === '#06b6d4' ? '💧' : '🚨'}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </AbsoluteFill>
    );
};
