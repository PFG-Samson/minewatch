import { render, screen, waitFor } from '@/test/utils';
import { AlertsView } from './AlertsView';
import { describe, it, expect } from 'vitest';

describe('AlertsView Component', () => {
    it('renders the alerts view header', () => {
        render(<AlertsView />);
        expect(screen.getByText('Alert History')).toBeInTheDocument();
    });

    it('renders a list of alerts from MSW', async () => {
        render(<AlertsView />);

        await waitFor(() => {
            // Check for the mock alert title from MSW handler
            expect(screen.getByText('Significant Vegetation Loss')).toBeInTheDocument();
            expect(screen.getByText('North sector')).toBeInTheDocument();
        });
    });

    it('displays the alert severity badge', async () => {
        render(<AlertsView />);

        await waitFor(() => {
            // "high" is the severity in MSW handler, should be uppercase in badge usually
            expect(screen.getByText(/high/i)).toBeInTheDocument();
        });
    });
});
