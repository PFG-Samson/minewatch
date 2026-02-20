import { Composition } from 'remotion';
import { Demo1_Overview } from './compositions/Demo1_Overview';
import { Demo2_STACIngestion } from './compositions/Demo2_STACIngestion';
import { Demo3_NDVI } from './compositions/Demo3_NDVI';
import { Demo4_BSIMiningExpansion } from './compositions/Demo4_BSIMiningExpansion';
import { Demo5_IllegalMining } from './compositions/Demo5_IllegalMining';
import { Demo6_WaterAccumulation } from './compositions/Demo6_WaterAccumulation';
import { Demo7_AlertSystem } from './compositions/Demo7_AlertSystem';
import { Demo8_PDFReport } from './compositions/Demo8_PDFReport';
import { Demo9_ChangeAnalysis } from './compositions/Demo9_ChangeAnalysis';
import { Demo10_FullWorkflow } from './compositions/Demo10_FullWorkflow';

export const RemotionRoot: React.FC = () => {
    return (
        <>
            <Composition
                id="Demo1-Overview"
                component={Demo1_Overview}
                durationInFrames={300}
                fps={30}
                width={1920}
                height={1080}
            />
            <Composition
                id="Demo2-STACIngestion"
                component={Demo2_STACIngestion}
                durationInFrames={270}
                fps={30}
                width={1920}
                height={1080}
            />
            <Composition
                id="Demo3-NDVI"
                component={Demo3_NDVI}
                durationInFrames={270}
                fps={30}
                width={1920}
                height={1080}
            />
            <Composition
                id="Demo4-BSIMiningExpansion"
                component={Demo4_BSIMiningExpansion}
                durationInFrames={270}
                fps={30}
                width={1920}
                height={1080}
            />
            <Composition
                id="Demo5-IllegalMining"
                component={Demo5_IllegalMining}
                durationInFrames={270}
                fps={30}
                width={1920}
                height={1080}
            />
            <Composition
                id="Demo6-WaterAccumulation"
                component={Demo6_WaterAccumulation}
                durationInFrames={270}
                fps={30}
                width={1920}
                height={1080}
            />
            <Composition
                id="Demo7-AlertSystem"
                component={Demo7_AlertSystem}
                durationInFrames={270}
                fps={30}
                width={1920}
                height={1080}
            />
            <Composition
                id="Demo8-PDFReport"
                component={Demo8_PDFReport}
                durationInFrames={270}
                fps={30}
                width={1920}
                height={1080}
            />
            <Composition
                id="Demo9-ChangeAnalysis"
                component={Demo9_ChangeAnalysis}
                durationInFrames={300}
                fps={30}
                width={1920}
                height={1080}
            />
            <Composition
                id="Demo10-FullWorkflow"
                component={Demo10_FullWorkflow}
                durationInFrames={360}
                fps={30}
                width={1920}
                height={1080}
            />
        </>
    );
};
