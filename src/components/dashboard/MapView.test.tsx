import { render, screen, waitFor } from '@/test/utils';
import { MapView } from './MapView';
import { describe, it, expect, vi } from 'vitest';
import L from 'leaflet';

describe('MapView Component', () => {
    it('renders the map container', () => {
        const { container } = render(<MapView />);
        // The MapView returns a div with ref={mapRef} and rounded-xl class
        expect(container.querySelector('div')).toBeInTheDocument();
    });

    it('initializes the leaflet map', async () => {
        render(<MapView />);
        expect(L.map).toHaveBeenCalled();
    });

    it('fetches latest preview when no runId is provided', async () => {
        render(<MapView />);
        await waitFor(() => {
            // getLatestImageryPreview is called in MapView's useEffect when no runId
            expect(L.imageOverlay).toHaveBeenCalledWith(
                expect.stringContaining('/mock-preview.png'),
                expect.any(Array),
                expect.any(Object)
            );
        });
    });

    it('renders boundary geometry if provided', async () => {
        const mockBoundary = {
            type: 'Polygon',
            coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]]
        };
        render(<MapView showBoundary={true} mineAreaBoundary={mockBoundary} />);

        await waitFor(() => {
            // Leaflet geoJSON should be called with the boundary
            const calls = (L.geoJSON as any).mock.calls;
            const boundaryCall = calls.find((call: any) =>
                call[0] && call[0].type === 'Polygon'
            );
            expect(boundaryCall).toBeDefined();
        });
    });
});
