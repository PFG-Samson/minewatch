import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

const STEPS = [
    {
        step: 1,
        title: 'Configure Site',
        icon: '⚙️',
        color: '#3b82f6',
        detail: 'Upload GeoJSON boundary · Set buffer zone · Enter project name',
        frameIn: 30,
    },
    {
        step: 2,
        title: 'Sync Satellite Scenes',
        icon: '📡',
        color: '#8b5cf6',
        detail: 'STAC ingestion from Microsoft Planetary Computer · Cloud filter ≤20%',
        frameIn: 90,
    },
    {
        step: 3,
        title: 'Run Analysis',
        icon: '⚡',
        color: '#f59e0b',
        detail: 'Download bands → Clip to AOI → Calculate NDVI/BSI/NDWI → Vectorize zones',
        frameIn: 150,
    },
    {
        step: 4,
        title: 'Review Alerts',
        icon: '🚨',
        color: '#ef4444',
        detail: 'Rule-based alerts with severity · Click to zoom on map · View on Map',
        frameIn: 210,
    },
    {
        step: 5,
        title: 'Export Report',
        icon: '📄',
        color: '#22c55e',
        detail: 'One-click PDF · Audit-ready · Timestamped · Includes imagery evidence',
        frameIn: 270,
    },
];

export const Demo10_FullWorkflow: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });

    // Overall progress bar
    const progressWidth = interpolate(frame, [30, 310], [0, 100], { extrapolateRight: 'clamp' });

    // Final CTA
    const ctaOpacity = interpolate(frame, [320, 355], [0, 1], { extrapolateRight: 'clamp' });
    const ctaScale = spring({ frame: frame - 320, fps, config: { damping: 12, stiffness: 150 } });

    const summaryStats = [
        { value: '< 2 min', label: 'Analysis Time' },
        { value: '95%+', label: 'Coverage Guaranteed' },
        { value: '3', label: 'Index Types' },
        { value: '100%', label: 'Automated' },
    ];

    return (
        <AbsoluteFill
            style={{
                background: 'linear-gradient(135deg, #060b0f 0%, #091221 50%, #060f0b 100%)',
                fontFamily: 'Inter, system-ui, sans-serif',
                overflow: 'hidden',
            }}
        >
            {/* Subtle animated particles */}
            {Array.from({ length: 12 }).map((_, i) => {
                const x = (i * 167 + frame * 0.3) % 1920;
                const y = (i * 89 + frame * 0.15) % 1080;
                return <div key={i} style={{ position: 'absolute', left: x, top: y, width: 2, height: 2, borderRadius: '50%', background: '#22c55e', opacity: 0.15 }} />;
            })}

            {/* Header */}
            <div style={{ position: 'absolute', top: 55, left: 100, right: 100, opacity: titleOpacity, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <div style={{ fontSize: 14, color: '#22c55e', textTransform: 'uppercase', letterSpacing: 4, marginBottom: 8 }}>End-to-End</div>
                    <div style={{ fontSize: 48, fontWeight: 900, color: '#f1f5f9', lineHeight: 1 }}>Full MineWatch Workflow</div>
                    <div style={{ fontSize: 19, color: '#64748b', marginTop: 10 }}>From boundary upload to compliance report — fully automated</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 8 }}>
                    <div style={{ width: 52, height: 52, borderRadius: 14, background: 'linear-gradient(135deg, #22c55e, #16a34a)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 30, boxShadow: '0 0 30px rgba(34,197,94,0.4)' }}>⛏️</div>
                    <span style={{ fontSize: 28, fontWeight: 900, background: 'linear-gradient(90deg, #22c55e, #86efac)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>MineWatch</span>
                </div>
            </div>

            {/* Global progress bar */}
            <div style={{ position: 'absolute', top: 190, left: 100, right: 100, height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 3 }}>
                <div style={{ height: '100%', width: `${progressWidth}%`, borderRadius: 3, background: 'linear-gradient(90deg, #3b82f6, #8b5cf6, #f59e0b, #ef4444, #22c55e)', boxShadow: '0 0 12px rgba(34,197,94,0.4)', transition: 'width 0.1s' }} />
            </div>

            {/* Workflow steps */}
            <div style={{ position: 'absolute', top: 220, left: 100, right: 100, display: 'flex', gap: 20 }}>
                {STEPS.map((step, i) => {
                    const stepSpring = spring({ frame: frame - step.frameIn, fps, config: { damping: 16, stiffness: 100 } });
                    const stepOpacity = interpolate(frame, [step.frameIn, step.frameIn + 30], [0, 1], { extrapolateRight: 'clamp' });
                    const stepY = interpolate(stepSpring, [0, 1], [40, 0]);
                    const isActive = frame >= step.frameIn + 10;

                    return (
                        <div key={i} style={{ flex: 1, opacity: stepOpacity, transform: `translateY(${stepY}px)` }}>
                            {/* Step card */}
                            <div style={{ background: isActive ? `${step.color}0f` : 'rgba(255,255,255,0.02)', border: `1px solid ${isActive ? step.color + '44' : 'rgba(255,255,255,0.07)'}`, borderRadius: 20, padding: '28px 20px', height: 320, display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 14, backdropFilter: 'blur(10px)', boxShadow: isActive ? `0 0 30px ${step.color}10` : 'none', transition: 'all 0.4s' }}>
                                {/* Step number */}
                                <div style={{ width: 44, height: 44, borderRadius: '50%', background: isActive ? `linear-gradient(135deg, ${step.color}, ${step.color}aa)` : 'rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, fontWeight: 800, color: isActive ? '#fff' : '#334155', boxShadow: isActive ? `0 0 20px ${step.color}50` : 'none' }}>
                                    {step.step}
                                </div>
                                {/* Icon */}
                                <div style={{ fontSize: 42 }}>{step.icon}</div>
                                {/* Title */}
                                <div style={{ fontSize: 17, fontWeight: 800, color: isActive ? '#f1f5f9' : '#64748b' }}>{step.title}</div>
                                {/* Detail */}
                                <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.5 }}>{step.detail}</div>
                                {/* Active indicator */}
                                {isActive && (
                                    <div style={{ width: '60%', height: 3, borderRadius: 2, background: `linear-gradient(90deg, ${step.color}, transparent)`, marginTop: 'auto' }} />
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Summary stats */}
            <div style={{ position: 'absolute', bottom: 100, left: 100, right: 100, display: 'flex', justifyContent: 'space-around', opacity: ctaOpacity, transform: `scale(${interpolate(ctaScale, [0, 1], [0.9, 1])})` }}>
                {summaryStats.map((s, i) => (
                    <div key={i} style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 40, fontWeight: 900, color: '#22c55e', lineHeight: 1 }}>{s.value}</div>
                        <div style={{ fontSize: 14, color: '#475569', marginTop: 6 }}>{s.label}</div>
                    </div>
                ))}
            </div>

            {/* CTA footer */}
            <div style={{ position: 'absolute', bottom: 36, left: 0, right: 0, textAlign: 'center', opacity: ctaOpacity }}>
                <div style={{ fontSize: 14, color: '#334155', letterSpacing: 3, textTransform: 'uppercase' }}>
                    Continuous satellite monitoring · No field visits required · Government-grade evidence
                </div>
            </div>
        </AbsoluteFill>
    );
};
