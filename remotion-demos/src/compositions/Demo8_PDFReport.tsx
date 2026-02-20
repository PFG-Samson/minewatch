import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const Demo8_PDFReport: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const titleOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });

    // PDF "building" animation — sections animate in
    const sections = [
        { title: 'Site Identity', icon: '🏭', desc: 'Name · Geodesic Area (ha) · Perimeter (km) · Centroid · Buffer', frame: 40 },
        { title: 'Scene Details', icon: '🛰️', desc: 'Platform (S2A/S2B) · Level L2A · Tile ID · Acquisition date', frame: 70 },
        { title: 'Coverage Quality', icon: '📐', desc: 'Exact % from scene footprints · Mosaic tile count', frame: 100 },
        { title: 'Index Statistics', icon: '📊', desc: 'NDVI / BSI / NDWI: baseline mean · latest mean · delta', frame: 130 },
        { title: 'Change Zones Table', icon: '🗺️', desc: 'Class · Count · Total Area (ha) per zone type', frame: 160 },
        { title: 'Alerts Table', icon: '⚠️', desc: 'Severity · Title · Created At — all active alerts', frame: 190 },
    ];

    const exportBannerOpacity = interpolate(frame, [230, 260], [0, 1], { extrapolateRight: 'clamp' });

    return (
        <AbsoluteFill
            style={{
                background: 'linear-gradient(135deg, #07080f 0%, #0d0f1f 100%)',
                fontFamily: 'Inter, system-ui, sans-serif',
                overflow: 'hidden',
            }}
        >
            {/* Faint document lines background */}
            {Array.from({ length: 15 }).map((_, i) => (
                <div key={i} style={{ position: 'absolute', left: 100, right: 100, top: 140 + i * 60, height: 1, background: 'rgba(255,255,255,0.03)' }} />
            ))}

            {/* Header */}
            <div style={{ position: 'absolute', top: 60, left: 100, opacity: titleOpacity }}>
                <div style={{ fontSize: 14, color: '#8b5cf6', textTransform: 'uppercase', letterSpacing: 4, marginBottom: 8 }}>Compliance Documentation</div>
                <div style={{ fontSize: 48, fontWeight: 900, color: '#f1f5f9', lineHeight: 1 }}>Automated PDF Report</div>
                <div style={{ fontSize: 19, color: '#64748b', marginTop: 10 }}>Audit-ready · Deterministic · Built with ReportLab</div>
            </div>

            {/* Document preview — left panel */}
            <div style={{ position: 'absolute', top: 190, left: 100, width: 520, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: 20, padding: '24px', overflow: 'hidden' }}>
                {/* PDF header bar */}
                <div style={{ background: 'linear-gradient(90deg, #7c3aed, #4f46e5)', borderRadius: 10, padding: '16px 20px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 16 }}>
                    <span style={{ fontSize: 30 }}>⛏️</span>
                    <div>
                        <div style={{ fontSize: 18, fontWeight: 800, color: '#fff' }}>MineWatch Analysis Report</div>
                        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', marginTop: 2 }}>Run ID: #42 · Generated: 2024-11-03 09:14 UTC</div>
                    </div>
                </div>

                {/* PDF sections rendering */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {sections.map((s, i) => {
                        const sOpacity = interpolate(frame, [s.frame, s.frame + 20], [0, 1], { extrapolateRight: 'clamp' });
                        const sY = interpolate(frame, [s.frame, s.frame + 20], [8, 0], { extrapolateRight: 'clamp' });
                        return (
                            <div key={i} style={{ opacity: sOpacity, transform: `translateY(${sY}px)`, display: 'flex', gap: 14, alignItems: 'flex-start', padding: '12px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: 10, borderLeft: '3px solid rgba(139,92,246,0.5)' }}>
                                <span style={{ fontSize: 20 }}>{s.icon}</span>
                                <div>
                                    <div style={{ fontSize: 14, fontWeight: 700, color: '#e2e8f0' }}>{s.title}</div>
                                    <div style={{ fontSize: 12, color: '#475569', marginTop: 3 }}>{s.desc}</div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Right panel — report features */}
            <div style={{ position: 'absolute', top: 190, right: 100, width: 520, display: 'flex', flexDirection: 'column', gap: 16 }}>
                {[
                    { frame: 50, icon: '🗺️', title: 'Labeled Imagery', desc: 'Baseline / Latest RGB composites embedded with per-band captions' },
                    { frame: 90, icon: '📈', title: 'Index Visual Evidence', desc: 'NDVI · BSI · NDWI before/after/change maps with color legends (−1 to +1)' },
                    { frame: 130, icon: '📦', title: 'Real AOI Metrics', desc: 'Geodesic area, perimeter, centroid, bounding box, buffer distance computed live' },
                    { frame: 170, icon: '✅', title: 'Content-Length Headers', desc: 'Accurate download size reported · Downsampled previews prevent large-image warnings' },
                    { frame: 210, icon: '📋', title: 'Strict Section Order', desc: 'Header → Identity → Metadata → Scenes → Coverage → Imagery → Indices → Zones → Alerts' },
                ].map((item, i) => {
                    const itemOpacity = interpolate(frame, [item.frame, item.frame + 25], [0, 1], { extrapolateRight: 'clamp' });
                    const itemX = interpolate(frame, [item.frame, item.frame + 25], [30, 0], { extrapolateRight: 'clamp' });
                    return (
                        <div key={i} style={{ opacity: itemOpacity, transform: `translateX(${itemX}px)`, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 14, padding: '16px 20px', display: 'flex', gap: 16, alignItems: 'flex-start', backdropFilter: 'blur(10px)' }}>
                            <span style={{ fontSize: 26 }}>{item.icon}</span>
                            <div>
                                <div style={{ fontSize: 15, fontWeight: 700, color: '#e2e8f0' }}>{item.title}</div>
                                <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>{item.desc}</div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Export banner */}
            <div style={{ position: 'absolute', bottom: 40, left: 100, right: 100, opacity: exportBannerOpacity }}>
                <div style={{ background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.35)', borderRadius: 14, padding: '18px 32px', display: 'flex', alignItems: 'center', gap: 24 }}>
                    <span style={{ fontSize: 36 }}>🚀</span>
                    <div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: '#8b5cf6' }}>One-Click PDF Download</div>
                        <div style={{ fontSize: 14, color: '#64748b', marginTop: 4 }}>GET /analysis-runs/{'{run_id}'}/report · No frontend rendering · Backend-generated</div>
                    </div>
                    <div style={{ marginLeft: 'auto', background: 'rgba(139,92,246,0.2)', borderRadius: 10, padding: '10px 24px', fontSize: 14, fontWeight: 700, color: '#c4b5fd' }}>Generate Report →</div>
                </div>
            </div>
        </AbsoluteFill>
    );
};
