# MineWatch Remotion Demos

10 animated demo videos showcasing the MineWatch geospatial mining intelligence platform.

## Quick Start

```sh
cd remotion-demos
npm install
npm start
```

Opens the Remotion preview at `http://localhost:3000`

## Demos

| # | ID | Focus | Duration |
|---|-----|-------|----------|
| 1 | `Demo1_Overview` | Platform hero — features, stats, branding | 10s |
| 2 | `Demo2_STACIngestion` | Satellite ingestion pipeline (STAC → download → mosaic) | 9s |
| 3 | `Demo3_NDVI` | NDVI vegetation loss — before/after split panel | 9s |
| 4 | `Demo4_BSIMiningExpansion` | BSI bare soil / mining expansion — animated pit growth | 9s |
| 5 | `Demo5_IllegalMining` | Illegal mining detection — radar sweep + hotspots | 9s |
| 6 | `Demo6_WaterAccumulation` | NDWI water accumulation & turbidity risk | 9s |
| 7 | `Demo7_AlertSystem` | Rule-based alert engine — animated feed | 9s |
| 8 | `Demo8_PDFReport` | Automated PDF compliance report generation | 9s |
| 9 | `Demo9_ChangeAnalysis` | Time-series change dashboard — animated trend lines | 10s |
| 10 | `Demo10_FullWorkflow` | End-to-end workflow — all 5 steps animated | 12s |

## Render a Single Demo

```sh
npx remotion render src/index.ts Demo1_Overview out/demo1.mp4
```

## Render All Demos

```sh
for i in 1 2 3 4 5 6 7 8 9 10; do
  npx remotion render src/index.ts Demo${i}_* out/demo${i}.mp4
done
```

## Technical Specs

- **Resolution**: 1920×1080 (Full HD)
- **Frame Rate**: 30 FPS
- **Codec**: H.264
- **Libraries**: Remotion 4, React 18, TypeScript 5

## Project Structure

```
remotion-demos/
├── src/
│   ├── index.ts                        # Remotion entry point
│   ├── Root.tsx                        # All 10 compositions registered
│   └── compositions/
│       ├── Demo1_Overview.tsx
│       ├── Demo2_STACIngestion.tsx
│       ├── Demo3_NDVI.tsx
│       ├── Demo4_BSIMiningExpansion.tsx
│       ├── Demo5_IllegalMining.tsx
│       ├── Demo6_WaterAccumulation.tsx
│       ├── Demo7_AlertSystem.tsx
│       ├── Demo8_PDFReport.tsx
│       ├── Demo9_ChangeAnalysis.tsx
│       └── Demo10_FullWorkflow.tsx
├── package.json
└── tsconfig.json
```
