import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

type Severity = 'high' | 'medium' | 'low';

const SEVERITY_COLORS: Record<Severity, string> = {
    high: '#ef4444',
    medium: '#f59e0b',
    low: '#22c55e',
};

const alerts = [
    { id: 1, severity: 'high' as Severity, title: 'Boundary Breach Detected', desc: 'Mining activity 1.2 km outside approved lease', type: 'BOUNDARY_BREACH', time: '09:14 UTC', area: '3.4 ha', frame: 45 },
    { id: 2, severity: 'high' as Severity, title: 'Vegetation Loss — Critical', desc: 'NDVI drop > 0.15 across 18.4 ha', type: 'VEGETATION_LOSS', time: '09:14 UTC', area: '18.4 ha', frame: 70 },
    { id: 3, severity: 'medium' as Severity, title: 'Bare Soil Expansion', desc: 'BSI increase 0.22 — active excavation zone', type: 'MINING_EXPANSION', time: '09:14 UTC', area: '5.7 ha', frame: 95 },
    { id: 4, severity: 'medium' as Severity, title: 'Water Accumulation', desc: 'NDWI delta +0.31 — downstream sedimentation risk', type: 'WATER_ACCUMULATION', time: '09:14 UTC', area: '8.2 ha', frame: 120 },
    { id: 5, severity: 'low' as Severity, title: 'Buffer Zone Activity', desc: 'Minor soil disturbance 0.3 ha within buffer', type: 'MINING_EXPANSION', time: '09:14 UTC', area: '0.3 ha', frame: 145 },
];

export const Demo7_AlertSystem: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });
    const rulesPanelOpacity = interpolate(frame, [200, 230], [0, 1], { extrapolateRight: 'clamp' });

    return (
        <AbsoluteFill
            style={{
                background: 'linear-gradient(135deg, #0f0a0a 0%, #1a0e0e 100%)',
                fontFamily: 'Inter, system-ui, sans-serif',
                overflow: 'hidden',
            }}
        >
            {/* Header */}
            <div style={{ position: 'absolute', top: 60, left: 100, opacity: titleOpacity }}>
                <div style={{ fontSize: 14, color: '#ef4444', textTransform: 'uppercase', letterSpacing: 4, marginBottom: 8 }}>Rule-Based Engine</div>
                <div style={{ fontSize: 48, fontWeight: 900, color: '#f1f5f9', lineHeight: 1 }}>Intelligent Alert System</div>
                <div style={{ fontSize: 19, color: '#64748b', marginTop: 10 }}>Configurable thresholds · Severity classification · GeoJSON geometry</div>
            </div>

            {/* Alert feed */}
            <div style={{ position: 'absolute', top: 200, left: 100, width: 860, display: 'flex', flexDirection: 'column', gap: 14 }}>
                {alerts.map((alert, i) => {
                    const sp = spring({ frame: frame - alert.frame, fps, config: { damping: 16, stiffness: 120 } });
                    const alertOpacity = interpolate(frame, [alert.frame, alert.frame + 20], [0, 1], { extrapolateRight: 'clamp' });
                    const alertX = interpolate(sp, [0, 1], [-40, 0]);
                    const color = SEVERITY_COLORS[alert.severity];
                    return (
                        <div key={alert.id} style={{ opacity: alertOpacity, transform: `translateX(${alertX}px)`, background: `rgba(255,255,255,0.03)`, border: `1px solid ${color}44`, borderRadius: 14, padding: '18px 24px', backdropFilter: 'blur(10px)', display: 'flex', alignItems: 'center', gap: 20 }}>
                            {/* Severity badge */}
                            <div style={{ width: 80, height: 28, borderRadius: 20, background: `${color}22`, border: `1px solid ${color}66`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color, textTransform: 'uppercase', letterSpacing: 1, flexShrink: 0 }}>
                                {alert.severity}
                            </div>
                            {/* Indicator dot */}
                            <div style={{ width: 10, height: 10, borderRadius: '50%', background: color, boxShadow: `0 0 10px ${color}`, flexShrink: 0 }} />
                            {/* Content */}
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9' }}>{alert.title}</div>
                                <div style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>{alert.desc}</div>
                            </div>
                            {/* Meta */}
                            <div style={{ textAlign: 'right', flexShrink: 0 }}>
                                <div style={{ fontSize: 14, fontWeight: 600, color }}>Area: {alert.area}</div>
                                <div style={{ fontSize: 11, color: '#475569', marginTop: 2 }}>{alert.time}</div>
                            </div>
                            {/* Map link indicator */}
                            <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}>📍</div>
                        </div>
                    );
                })}
            </div>

            {/* Alert rules config panel */}
            <div style={{ position: 'absolute', top: 200, right: 100, width: 460, display: 'flex', flexDirection: 'column', gap: 14, opacity: rulesPanelOpacity }}>
                <div style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 16, padding: '20px 24px' }}>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9', marginBottom: 16 }}>⚙️ Alert Rule Configuration</div>
                    {[
                        { rule: 'Vegetation Loss', high: '> 1.0 ha', med: '> 0.5 ha', low: '> 0.2 ha' },
                        { rule: 'Mining Expansion', high: '—', med: '> 0.1 ha', low: '> 0.05 ha' },
                        { rule: 'Water Accumulation', high: '—', med: '—', low: '> 0.05 ha' },
                        { rule: 'Boundary Breach', high: 'Any', med: '—', low: '—' },
                    ].map((r) => (
                        <div key={r.rule} style={{ display: 'flex', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                            <span style={{ flex: 1, fontSize: 13, color: '#94a3b8' }}>{r.rule}</span>
                            <span style={{ width: 70, textAlign: 'center', fontSize: 12, color: SEVERITY_COLORS.high }}>{r.high}</span>
                            <span style={{ width: 70, textAlign: 'center', fontSize: 12, color: SEVERITY_COLORS.medium }}>{r.med}</span>
                            <span style={{ width: 70, textAlign: 'center', fontSize: 12, color: SEVERITY_COLORS.low }}>{r.low}</span>
                        </div>
                    ))}
                    <div style={{ display: 'flex', gap: 12, marginTop: 8, paddingTop: 8 }}>
                        {[['HIGH', '#ef4444'], ['MEDIUM', '#f59e0b'], ['LOW', '#22c55e']].map(([label, color]) => (
                            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <div style={{ width: 10, height: 10, borderRadius: '50%', background: color as string }} />
                                <span style={{ fontSize: 11, color: '#64748b' }}>{label as string}</span>
                            </div>
                        ))}
                    </div>
                </div>
                <div style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.25)', borderRadius: 14, padding: '16px 22px' }}>
                    <div style={{ fontSize: 14, color: '#22c55e', fontWeight: 600 }}>📍 Click-to-Map Integration</div>
                    <div style={{ fontSize: 13, color: '#64748b', marginTop: 6 }}>Each alert carries a GeoJSON geometry. Clicking "View on Map" zooms the dashboard to the exact flagged zone.</div>
                </div>
            </div>
        </AbsoluteFill>
    );
};
