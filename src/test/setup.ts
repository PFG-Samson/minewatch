import "@testing-library/jest-dom";
import { beforeAll, afterEach, afterAll, vi } from "vitest";
import { server } from "./mocks/server";
import React from 'react';

// MSW Lifecycle
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// JSDOM Mocks
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => { },
    removeListener: () => { },
    addEventListener: () => { },
    removeEventListener: () => { },
    dispatchEvent: () => { },
  }),
});

// Framer Motion Mock (Proxy for all motion elements)
vi.mock('framer-motion', () => {
  const dummy = (type: string) => ({ children, ...props }: any) => React.createElement(type, props, children);

  const motion = new Proxy({}, {
    get: (_target, key: string) => {
      return dummy(key);
    }
  });

  return {
    motion,
    AnimatePresence: ({ children }: any) => children,
  };
});

// Leaflet Mock
const mockMap = {
  setView: vi.fn().mockReturnThis(),
  fitBounds: vi.fn().mockReturnThis(),
  remove: vi.fn(),
  addLayer: vi.fn().mockReturnThis(),
  removeLayer: vi.fn().mockReturnThis(),
};

const mockLayer = {
  addTo: vi.fn().mockReturnThis(),
  remove: vi.fn(),
  bindPopup: vi.fn().mockReturnThis(),
  getBounds: vi.fn().mockReturnValue({
    isValid: () => true,
    pad: () => ({ isValid: () => true }),
    getCenter: () => [0, 0],
  }),
};

vi.mock("leaflet", () => ({
  default: {
    map: vi.fn().mockReturnValue(mockMap),
    tileLayer: vi.fn().mockReturnValue(mockLayer),
    marker: vi.fn().mockReturnValue(mockLayer),
    imageOverlay: vi.fn().mockReturnValue(mockLayer),
    geoJSON: vi.fn().mockReturnValue(mockLayer),
    circle: vi.fn().mockReturnValue(mockLayer),
    icon: vi.fn(),
    rectangle: vi.fn().mockReturnValue(mockLayer),
  },
}));

// ResizeObserver Mock
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));
