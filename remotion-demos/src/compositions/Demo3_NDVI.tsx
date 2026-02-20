import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const Demo3_NDVI: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });
    const comparisonProgress = spring({ frame: frame - 40, fps, config: { damping: 18, stiffness: 80 } });
    const splitX = interpolate(comparisonProgress, [0, 1], [0, 50]);

    const statsVisible = frame > 150;
    const statsOpacity = interpolate(frame, [150, 185], [0, 1], { extrapolateRight: 'clamp' });

    const ndviCells = [
        '#1a472a', '#22c55e', '#86efac', '#d1fae5', '#fef08a',
        '#fdba74', '#f97316', '#dc2626', '#7f1d1d', '#22c55e',
        '#86efac', '#22c55e', '#1a472a', '#fef08a', '#dc2626',
        '#f97316', '#22c55e', '#86efac', '#d1fae5', '#fef08a',
    ];

    const alertPulse = Math.sin(frame * 0.2) * 0.3 + 0.7;

    return (
        <AbsoluteFill
            style={{
                background: 'linear-gradient(135deg, #080f0a 0%, #0d1f10 50%, #091408 100%)',
                fontFamily: 'Inter, system-ui, sans-serif',
                overflow: 'hidden',
            }}
        >
            {/* Header */}
            <div style={{ position: 'absolute', top: 60, left: 100, opacity: titleOpacity }}>
                <div style={{ fontSize: 14, color: '#22c55e', textTransform: 'uppercase', letterSpacing: 4, marginBottom: 8 }}>Spectral Index Analysis</div>
                <div style={{ fontSize: 48, fontWeight: 900, color: '#f1f5f9', lineHeight: 1 }}>NDVI Vegetation Loss</div>
                <div style={{ fontSize: 20, color: '#64748b', marginTop: 10 }}>Normalized Difference Vegetation Index — (NIR − Red) / (NIR + Red)</div>
            </div>

            {/* Split comparison panel */}
            <div style={{ position: 'absolute', top: 200, left: 100, right: 100, height: 460, borderRadius: 20, overflow: 'hidden', border: '1px solid rgba(34,197,94,0.2)', boxShadow: '0 0 60px rgba(34,197,94,0.08)' }}>
                {/* Baseline (before) */}
                <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(135deg, #1a2e1a 0%, #243524 100%)' }}>
                    <div style={{ position: 'absolute', top: 20, left: 24, background: 'rgba(0,0,0,0.6)', padding: '8px 16px', borderRadius: 8, fontSize: 14, color: '#86efac', fontWeight: 600, letterSpacing: 2 }}>BASELINE — Jan 2024</div>
                    {/* Simulated healthy vegetation heatmap */}
                    <div style={{ position: 'absolute', top: 60, left: 40, right: '50%', bottom: 40, display: 'grid', gridTemplateColumns: 'repeat(10, 1fr)', gridTemplateRows: 'repeat(5, 1fr)', gap: 3, padding: 20 }}>
                        {Array.from({ length: 50 }).map((_, i) => (
                            <div key={i} style={{ borderRadius: 4, background: i % 7 === 0 ? '#fef08a' : i % 11 === 0 ? '#86efac66' : '#22c55e', opacity: 0.7 }} />
                        ))}
                    </div>
                    {/* NDVI legend labels */}
                    <div style={{ position: 'absolute', bottom: 20, left: 60, display: 'flex', gap: 12, alignItems: 'center' }}>
                        {[['#1a472a', '-1.0'], ['#22c55e', '0.0'], ['#fef08a', '0.5'], ['#dc2626', '+1.0']].map(([c, l]) => (
                            <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <div style={{ width: 16, height: 16, borderRadius: 3, background: c as string }} />
                                <span style={{ fontSize: 12, color: '#94a3b8' }}>{l}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Latest (after) with change overlay */}
                <div style={{ position: 'absolute', inset: 0, left: `${splitX}%`, background: 'linear-gradient(135deg, #1a0f0a 0%, #2d1a0f 100%)', overflow: 'hidden' }}>
                    <div style={{ position: 'absolute', top: 20, right: 24, background: 'rgba(0,0,0,0.6)', padding: '8px 16px', borderRadius: 8, fontSize: 14, color: '#f97316', fontWeight: 600, letterSpacing: 2 }}>LATEST — Nov 2024</div>
                    <div style={{ position: 'absolute', top: 60, left: 0, right: 0, bottom: 40, display: 'grid', gridTemplateColumns: 'repeat(10, 1fr)', gridTemplateRows: 'repeat(5, 1fr)', gap: 3, padding: 20 }}>
                        {ndviCells.concat(ndviCells).slice(0, 50).map((color, i) => (
                            <div key={i} style={{ borderRadius: 4, background: color, opacity: color === '#dc2626' || color === '#f97316' ? alertPulse : 0.7 }} />
                        ))}
                    </div>
                </div>

                {/* Split handle */}
                <div style={{ position: 'absolute', top: 0, bottom: 0, left: `${splitX}%`, width: 3, background: '#22c55e', boxShadow: '0 0 20px rgba(34,197,94,0.8)', transform: 'translateX(-50%)', zIndex: 10 }}>
                    <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: 32, height: 32, borderRadius: '50%', background: '#22c55e', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, boxShadow: '0 0 20px rgba(34,197,94,0.8)' }}>⟺</div>
                </div>
            </div>

            {/* Stats */}
            <div style={{ position: 'absolute', bottom: 50, left: 100, right: 100, display: 'flex', gap: 20, opacity: statsOpacity }}>
                {[
                    { value: '−0.31', label: 'Avg NDVI Delta', color: '#dc2626' },
                    { value: '18.4 ha', label: 'Vegetation Lost', color: '#f97316' },
                    { value: '72%', label: 'Healthy Remaining', color: '#22c55e' },
                    { value: '>0.15', label: 'Alert Threshold (drop)', color: '#f59e0b' },
                ].map((s, i) => {
                    const sp = spring({ frame: frame - 160 - i * 15, fps, config: { damping: 14 } });
                    return (
                        <div key={i} style={{ flex: 1, background: 'rgba(255,255,255,0.04)', border: `1px solid ${s.color}33`, borderRadius: 14, padding: '20px 24px', transform: `translateY(${interpolate(sp, [0, 1], [20, 0])}px)`, backdropFilter: 'blur(10px)' }}>
                            <div style={{ fontSize: 34, fontWeight: 900, color: s.color }}>{s.value}</div>
                            <div style={{ fontSize: 13, color: '#64748b', marginTop: 6 }}>{s.label}</div>
                        </div>
                    );
                })}
            </div>
        </AbsoluteFill>
    );
};
