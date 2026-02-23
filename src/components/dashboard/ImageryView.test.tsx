import { render, screen, fireEvent } from '@/test/utils';
import { ImageryView } from './ImageryView';
import { describe, it, expect } from 'vitest';

describe('ImageryView Component', () => {
    it('renders the imagery catalog header', () => {
        render(<ImageryView />);
        expect(screen.getByText(/Satellite Imagery Catalog/i)).toBeInTheDocument();
    });

    it('renders progress labels', () => {
        render(<ImageryView />);
        // Just verify the placeholder or static text is there
        expect(screen.getByText(/Select two scenes/i)).toBeInTheDocument();
    });

    it('renders the STAC sync button', () => {
        render(<ImageryView />);
        const syncBtn = screen.getByRole('button', { name: /Sync STAC/i });
        expect(syncBtn).toBeInTheDocument();
    });
});
