import { render, screen, waitFor } from '@/test/utils';
import { Dashboard } from './Dashboard';
import { describe, it, expect } from 'vitest';

describe('Dashboard Component', () => {
    it('renders the dashboard with site name', async () => {
        const { container } = render(<Dashboard />);

        // Check for "Mock Mine" from MSW handler
        try {
            await waitFor(() => {
                expect(screen.getByText(/Mock Mine/i)).toBeInTheDocument();
            }, { timeout: 5000 });
        } catch (e) {
            console.log("DEBUG: Dashboard render failed to show Mock Mine. Current HTML:");
            console.log(container.innerHTML);
            throw e;
        }
    });

    it('displays the stats cards with mock data', async () => {
        render(<Dashboard />);

        await waitFor(() => {
            // 100.00 is for Monitored Area in MSW handler
            expect(screen.getByText('100.00')).toBeInTheDocument();
            // "1" for Active Alerts in MSW handler
            expect(screen.getByText('1')).toBeInTheDocument();
        }, { timeout: 5000 });
    });

    it('renders the map view container', async () => {
        render(<Dashboard />);
        await waitFor(() => {
            expect(document.querySelector('.map-container')).toBeInTheDocument();
        }, { timeout: 5000 });
    });

    it('renders navigation items in the sidebar', async () => {
        render(<Dashboard />);
        await waitFor(() => {
            expect(screen.getByText('Dashboard')).toBeInTheDocument();
            expect(screen.getByText('Map View')).toBeInTheDocument();
            expect(screen.getByText('Alerts')).toBeInTheDocument();
        }, { timeout: 5000 });
    });
});
