import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const Demo4_BSIMiningExpansion: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });

    // Expanding mine pit animation
    const pitScale = interpolate(frame, [40, 180], [0.4, 1.0], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
    const expansionRing = interpolate(frame, [80, 200], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

    const statsOpacity = interpolate(frame, [160, 200], [0, 1], { extrapolateRight: 'clamp' });
    const alertOpacity = Math.sin(frame * 0.15) * 0.4 + 0.6;

    // BSI grid cells - simulating bare soil detection
    const gridRows = 10;
    const gridCols = 14;

    return (
        <AbsoluteFill
            style={{
                background: 'linear-gradient(135deg, #12090a 0%, #1e1008 100%)',
                fontFamily: 'Inter, system-ui, sans-serif',
                overflow: 'hidden',
            }}
        >
            {/* Header */}
            <div style={{ position: 'absolute', top: 60, left: 100, opacity: titleOpacity }}>
                <div style={{ fontSize: 14, color: '#f97316', textTransform: 'uppercase', letterSpacing: 4, marginBottom: 8 }}>Bare Soil Index · BSI</div>
                <div style={{ fontSize: 48, fontWeight: 900, color: '#f1f5f9', lineHeight: 1 }}>Mining Expansion Detection</div>
                <div style={{ fontSize: 19, color: '#64748b', marginTop: 10 }}>BSI = (Red + SWIR − NIR − Blue) / (Red + SWIR + NIR + Blue)</div>
            </div>

            {/* Map visualization panel */}
            <div style={{ position: 'absolute', top: 200, left: 100, width: 760, height: 480, borderRadius: 20, overflow: 'hidden', border: '1px solid rgba(249,115,22,0.25)', background: 'rgba(255,255,255,0.02)', boxShadow: '0 0 60px rgba(249,115,22,0.08)' }}>
                {/* Grid base — green vegetation */}
                <div style={{ position: 'absolute', inset: 0, display: 'grid', gridTemplateColumns: `repeat(${gridCols}, 1fr)`, gridTemplateRows: `repeat(${gridRows}, 1fr)`, gap: 2, padding: 16 }}>
                    {Array.from({ length: gridRows * gridCols }).map((_, i) => {
                        const row = Math.floor(i / gridCols);
                        const col = i % gridCols;
                        const cx = col / gridCols;
                        const cy = row / gridRows;
                        const dist = Math.sqrt((cx - 0.45) ** 2 + (cy - 0.45) ** 2);
                        const isMine = dist < 0.18 * pitScale;
                        const isExpansion = dist < 0.25 * expansionRing && dist > 0.18 * pitScale;
                        return (
                            <div key={i} style={{
                                borderRadius: 2,
                                background: isMine
                                    ? `rgba(249,115,22,${0.6 + Math.random() * 0.3})`
                                    : isExpansion
                                        ? `rgba(251,191,36,${0.4 + Math.random() * 0.4})`
                                        : `rgba(34,197,94,${0.15 + Math.random() * 0.2})`,
                                boxShadow: isMine ? '0 0 4px rgba(249,115,22,0.6)' : 'none',
                            }} />
                        );
                    })}
                </div>

                {/* Mine boundary circle */}
                <div style={{ position: 'absolute', top: '50%', left: '48%', transform: 'translate(-50%, -50%)', width: 160 * pitScale, height: 130 * pitScale, borderRadius: '50%', border: '2px solid rgba(249,115,22,0.8)', boxShadow: '0 0 30px rgba(249,115,22,0.3)' }} />

                {/* Expansion ring */}
                <div style={{ position: 'absolute', top: '50%', left: '48%', transform: 'translate(-50%, -50%)', width: 220 * expansionRing, height: 180 * expansionRing, borderRadius: '50%', border: '2px dashed rgba(251,191,36,0.6)', boxShadow: '0 0 20px rgba(251,191,36,0.2)' }} />

                {/* Labels */}
                <div style={{ position: 'absolute', top: 20, left: 20, background: 'rgba(0,0,0,0.7)', padding: '6px 14px', borderRadius: 8, fontSize: 13, color: '#f97316', fontWeight: 600 }}>BSI Change Map</div>

                {/* Legend */}
                <div style={{ position: 'absolute', bottom: 16, left: 20, display: 'flex', gap: 16 }}>
                    {[['#f97316', 'Active Pit'], ['#fbbf24', 'Expansion Zone'], ['#22c55e', 'Vegetation']].map(([c, l]) => (
                        <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div style={{ width: 12, height: 12, borderRadius: 2, background: c as string }} />
                            <span style={{ fontSize: 11, color: '#94a3b8' }}>{l as string}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Alert badge */}
            {frame > 100 && (
                <div style={{ position: 'absolute', top: 240, right: 100, width: 400, opacity: alertOpacity }}>
                    <div style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.4)', borderRadius: 14, padding: '18px 22px', boxShadow: '0 0 30px rgba(239,68,68,0.15)' }}>
                        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                            <span style={{ fontSize: 28 }}>🚨</span>
                            <div>
                                <div style={{ fontSize: 16, fontWeight: 700, color: '#ef4444' }}>HIGH — Boundary Breach</div>
                                <div style={{ fontSize: 13, color: '#94a3b8', marginTop: 4 }}>Mining activity detected outside approved permit boundary. BSI increase +0.22 over 3.4 ha.</div>
                                <div style={{ fontSize: 11, color: '#475569', marginTop: 8 }}>Threshold: BSI Δ &gt; 0.10 · Area &gt; 0.1 ha</div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Stats */}
            <div style={{ position: 'absolute', bottom: 50, left: 100, right: 100, display: 'flex', gap: 20, opacity: statsOpacity }}>
                {[
                    { value: '3.4 ha', label: 'Bare Soil Expansion', color: '#f97316' },
                    { value: '+0.22', label: 'BSI Delta (baseline → latest)', color: '#fbbf24' },
                    { value: '1.2 km', label: 'Beyond Permit Boundary', color: '#ef4444' },
                    { value: '>0.10', label: 'Alert Trigger Threshold', color: '#64748b' },
                ].map((s, i) => (
                    <div key={i} style={{ flex: 1, background: 'rgba(255,255,255,0.04)', border: `1px solid ${s.color}44`, borderRadius: 14, padding: '18px 22px', backdropFilter: 'blur(10px)' }}>
                        <div style={{ fontSize: 32, fontWeight: 900, color: s.color }}>{s.value}</div>
                        <div style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>{s.label}</div>
                    </div>
                ))}
            </div>
        </AbsoluteFill>
    );
};
