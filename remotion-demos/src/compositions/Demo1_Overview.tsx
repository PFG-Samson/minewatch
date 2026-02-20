import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

const BRAND = '#22c55e';
const BRAND2 = '#16a34a';

export const Demo1_Overview: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
    const titleY = interpolate(frame, [0, 30], [40, 0], { extrapolateRight: 'clamp' });

    const subtitleOpacity = interpolate(frame, [20, 50], [0, 1], { extrapolateRight: 'clamp' });

    const cards = [
        { icon: '🛰️', label: 'Satellite Imagery', sub: 'Sentinel-2 Multispectral', color: '#3b82f6', delay: 0 },
        { icon: '🌿', label: 'NDVI Analysis', sub: 'Vegetation Loss Detection', color: '#22c55e', delay: 8 },
        { icon: '⚠️', label: 'Smart Alerts', sub: 'Rule-Based, Real-Time', color: '#f59e0b', delay: 16 },
        { icon: '📄', label: 'PDF Reports', sub: 'Audit-Ready Compliance', color: '#8b5cf6', delay: 24 },
    ];

    const statsOpacity = interpolate(frame, [130, 160], [0, 1], { extrapolateRight: 'clamp' });

    const stats = [
        { value: '10m', label: 'Spatial Resolution' },
        { value: '3', label: 'Index Types (NDVI/BSI/NDWI)' },
        { value: '95%', label: 'Min Coverage Required' },
        { value: '<2min', label: 'Analysis Time' },
    ];

    return (
        <AbsoluteFill
            style={{
                background: 'linear-gradient(135deg, #0a0f1e 0%, #0d1a2e 50%, #0a1a10 100%)',
                fontFamily: 'Inter, system-ui, sans-serif',
                overflow: 'hidden',
            }}
        >
            {/* Animated grid background */}
            <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.06 }}>
                {Array.from({ length: 20 }).map((_, i) => (
                    <line key={`v${i}`} x1={i * 100} y1={0} x2={i * 100} y2={1080} stroke='#22c55e' strokeWidth={1} />
                ))}
                {Array.from({ length: 12 }).map((_, i) => (
                    <line key={`h${i}`} x1={0} y1={i * 90} x2={1920} y2={i * 90} stroke='#22c55e' strokeWidth={1} />
                ))}
            </svg>

            {/* Glowing orbs */}
            <div style={{ position: 'absolute', top: -200, right: 200, width: 600, height: 600, borderRadius: '50%', background: 'radial-gradient(circle, rgba(34,197,94,0.12) 0%, transparent 70%)' }} />
            <div style={{ position: 'absolute', bottom: -100, left: 100, width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(59,130,246,0.10) 0%, transparent 70%)' }} />

            {/* Logo + Title */}
            <div style={{ position: 'absolute', top: 120, left: 0, right: 0, textAlign: 'center', opacity: titleOpacity, transform: `translateY(${titleY}px)` }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20, marginBottom: 20 }}>
                    <div style={{ width: 72, height: 72, borderRadius: 18, background: 'linear-gradient(135deg, #22c55e, #16a34a)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 40, boxShadow: '0 0 40px rgba(34,197,94,0.4)' }}>
                        ⛏️
                    </div>
                    <span style={{ fontSize: 72, fontWeight: 900, background: 'linear-gradient(90deg, #22c55e, #86efac)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: -2 }}>
                        MineWatch
                    </span>
                </div>
                <p style={{ fontSize: 28, color: '#94a3b8', fontWeight: 300, letterSpacing: 6, textTransform: 'uppercase', opacity: subtitleOpacity }}>
                    Satellite-Powered Mining Intelligence
                </p>
            </div>

            {/* Feature Cards */}
            <div style={{ position: 'absolute', top: 340, left: 160, right: 160, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 24 }}>
                {cards.map((card, i) => {
                    const cardProgress = spring({ frame: frame - 60 - card.delay, fps, config: { damping: 14, stiffness: 120 } });
                    const cardOpacity = interpolate(frame, [60 + card.delay, 90 + card.delay], [0, 1], { extrapolateRight: 'clamp' });
                    const cardY = interpolate(cardProgress, [0, 1], [50, 0]);
                    return (
                        <div key={i} style={{ opacity: cardOpacity, transform: `translateY(${cardY}px)`, background: 'rgba(255,255,255,0.04)', border: `1px solid ${card.color}33`, borderRadius: 20, padding: 32, backdropFilter: 'blur(20px)', boxShadow: `0 0 30px ${card.color}15` }}>
                            <div style={{ fontSize: 48, marginBottom: 16 }}>{card.icon}</div>
                            <div style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9', marginBottom: 8 }}>{card.label}</div>
                            <div style={{ fontSize: 15, color: '#64748b' }}>{card.sub}</div>
                            <div style={{ marginTop: 20, height: 3, borderRadius: 2, background: `linear-gradient(90deg, ${card.color}, transparent)` }} />
                        </div>
                    );
                })}
            </div>

            {/* Stats bar */}
            <div style={{ position: 'absolute', bottom: 100, left: 160, right: 160, display: 'flex', justifyContent: 'space-around', opacity: statsOpacity }}>
                {stats.map((s, i) => (
                    <div key={i} style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 42, fontWeight: 900, color: BRAND, lineHeight: 1 }}>{s.value}</div>
                        <div style={{ fontSize: 16, color: '#64748b', marginTop: 8 }}>{s.label}</div>
                    </div>
                ))}
            </div>

            {/* Tagline */}
            <div style={{ position: 'absolute', bottom: 40, left: 0, right: 0, textAlign: 'center', fontSize: 16, color: '#334155', letterSpacing: 3, textTransform: 'uppercase', opacity: statsOpacity }}>
                Continuous monitoring · No field visits required
            </div>
        </AbsoluteFill>
    );
};
