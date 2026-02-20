import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const Demo2_STACIngestion: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });

    const steps = [
        { icon: '📡', title: 'STAC Catalog Query', desc: 'Microsoft Planetary Computer', detail: 'Search Sentinel-2 L2A scenes within AOI bounding box', time: 30 },
        { icon: '☁️', title: 'Cloud Filter', desc: '≤20% cloud cover threshold', detail: 'Filters scenes — prioritises clearest, most recent acquisition', time: 70 },
        { icon: '🗺️', title: 'Coverage Validation', desc: 'Pre-download footprint check', detail: 'Scene footprint must cover ≥95% of mine boundary', time: 110 },
        { icon: '⬇️', title: 'Band Download', desc: 'B02 B03 B04 B08 B11', detail: 'Blue · Green · Red · NIR · SWIR bands cached locally as .tif', time: 150 },
        { icon: '🧩', title: 'Multi-Scene Mosaic', desc: 'If single scene < 92% coverage', detail: 'Automatically tiles additional scenes to reach 95%+ coverage', time: 190 },
    ];

    const dataFlow = interpolate(frame, [220, 260], [0, 1], { extrapolateRight: 'clamp' });

    return (
        <AbsoluteFill
            style={{
                background: 'linear-gradient(135deg, #0c0e1a 0%, #0f1729 100%)',
                fontFamily: 'Inter, system-ui, sans-serif',
                overflow: 'hidden',
            }}
        >
            {/* Header */}
            <div style={{ position: 'absolute', top: 70, left: 100, opacity: titleOpacity }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12 }}>
                    <div style={{ width: 48, height: 48, borderRadius: 12, background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26 }}>📡</div>
                    <div>
                        <div style={{ fontSize: 36, fontWeight: 800, color: '#f1f5f9' }}>STAC Imagery Ingestion</div>
                        <div style={{ fontSize: 18, color: '#64748b', marginTop: 2 }}>Automated satellite data acquisition pipeline</div>
                    </div>
                </div>
            </div>

            {/* Pipeline steps */}
            <div style={{ position: 'absolute', top: 200, left: 100, right: 100, display: 'flex', flexDirection: 'column', gap: 20 }}>
                {steps.map((step, i) => {
                    const stepSpring = spring({ frame: frame - step.time, fps, config: { damping: 16, stiffness: 100 } });
                    const stepOpacity = interpolate(frame, [step.time, step.time + 25], [0, 1], { extrapolateRight: 'clamp' });
                    const stepX = interpolate(stepSpring, [0, 1], [-60, 0]);
                    const isActive = frame > step.time + 10;

                    return (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 24, opacity: stepOpacity, transform: `translateX(${stepX}px)` }}>
                            {/* Step number */}
                            <div style={{ width: 40, height: 40, borderRadius: '50%', background: isActive ? 'linear-gradient(135deg, #3b82f6, #1d4ed8)' : 'rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, fontWeight: 700, color: isActive ? '#fff' : '#475569', flexShrink: 0, boxShadow: isActive ? '0 0 20px rgba(59,130,246,0.4)' : 'none', transition: 'all 0.3s' }}>
                                {i + 1}
                            </div>
                            {/* Connector */}
                            {i < steps.length - 1 && (
                                <div style={{ position: 'absolute', left: 119, top: 200 + i * 64 + 40, width: 2, height: 20, background: 'rgba(59,130,246,0.3)' }} />
                            )}
                            {/* Icon */}
                            <div style={{ fontSize: 32, width: 48, textAlign: 'center' }}>{step.icon}</div>
                            {/* Content */}
                            <div style={{ flex: 1, background: 'rgba(255,255,255,0.04)', border: `1px solid ${isActive ? 'rgba(59,130,246,0.3)' : 'rgba(255,255,255,0.06)'}`, borderRadius: 14, padding: '14px 24px', backdropFilter: 'blur(10px)' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                                    <span style={{ fontSize: 18, fontWeight: 700, color: '#f1f5f9' }}>{step.title}</span>
                                    <span style={{ fontSize: 13, color: '#3b82f6', background: 'rgba(59,130,246,0.1)', padding: '2px 10px', borderRadius: 20, fontFamily: 'monospace' }}>{step.desc}</span>
                                </div>
                                <div style={{ fontSize: 14, color: '#64748b', marginTop: 4 }}>{step.detail}</div>
                            </div>
                            {/* Status indicator */}
                            {isActive && (
                                <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#22c55e', boxShadow: '0 0 12px rgba(34,197,94,0.6)', flexShrink: 0 }} />
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Result banner */}
            <div style={{ position: 'absolute', bottom: 80, left: 100, right: 100, opacity: dataFlow }}>
                <div style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 16, padding: '20px 32px', display: 'flex', alignItems: 'center', gap: 24 }}>
                    <span style={{ fontSize: 36 }}>✅</span>
                    <div>
                        <div style={{ fontSize: 22, fontWeight: 700, color: '#22c55e' }}>Ingestion Complete</div>
                        <div style={{ fontSize: 16, color: '#64748b', marginTop: 4 }}>Up to 20 Sentinel-2 scenes registered · Metadata stored · Ready for analysis</div>
                    </div>
                    <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
                        <div style={{ fontSize: 32, fontWeight: 900, color: '#22c55e' }}>≥95%</div>
                        <div style={{ fontSize: 13, color: '#64748b' }}>Coverage guaranteed</div>
                    </div>
                </div>
            </div>
        </AbsoluteFill>
    );
};
