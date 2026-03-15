import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import TelemetryChart from '../components/TelemetryChart';

describe('TelemetryChart', () => {
  it('should render chart with telemetry data', () => {
    const telemetryData = [
      { id: 1, type: 'moisture', value: 65, timestamp: '2024-03-15T10:00:00Z' },
      { id: 2, type: 'moisture', value: 70, timestamp: '2024-03-15T11:00:00Z' },
      { id: 3, type: 'moisture', value: 68, timestamp: '2024-03-15T12:00:00Z' },
    ];

    const { container } = render(
      <TelemetryChart telemetryData={telemetryData} metricType="moisture" />
    );

    // Chart should be rendered (mocked in setup.js)
    expect(container.querySelector('.telemetry-chart')).toBeInTheDocument();
  });

  it('should render with empty data', () => {
    const { container } = render(<TelemetryChart telemetryData={[]} />);

    expect(container.querySelector('.telemetry-chart')).toBeInTheDocument();
  });

  it('should use default metric type when not provided', () => {
    const telemetryData = [
      { id: 1, type: 'moisture', value: 50, timestamp: '2024-03-15T10:00:00Z' },
    ];

    const { container } = render(<TelemetryChart telemetryData={telemetryData} />);

    expect(container.querySelector('.telemetry-chart')).toBeInTheDocument();
  });

  it('should handle custom metric types', () => {
    const telemetryData = [
      { id: 1, type: 'temperature', value: 22, timestamp: '2024-03-15T10:00:00Z' },
    ];

    const { container } = render(
      <TelemetryChart telemetryData={telemetryData} metricType="temperature" />
    );

    expect(container.querySelector('.telemetry-chart')).toBeInTheDocument();
  });
});
