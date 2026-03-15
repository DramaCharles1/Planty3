import React, { useEffect, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import 'chartjs-adapter-date-fns';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

function TelemetryChart({ telemetryData, metricType = 'moisture' }) {
  const chartData = {
    labels: telemetryData.map((t) => new Date(t.timestamp)),
    datasets: [
      {
        label: `${metricType.charAt(0).toUpperCase() + metricType.slice(1)} (%)`,
        data: telemetryData.map((t) => t.value),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.1,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: `${metricType.charAt(0).toUpperCase() + metricType.slice(1)} Over Time`,
      },
    },
    scales: {
      x: {
        type: 'time',
        time: {
          unit: 'minute',
          displayFormats: {
            minute: 'HH:mm',
            hour: 'MMM d, HH:mm',
          },
        },
        title: {
          display: true,
          text: 'Time',
        },
      },
      y: {
        title: {
          display: true,
          text: 'Value (%)',
        },
        beginAtZero: true,
      },
    },
  };

  return (
    <div className="telemetry-chart">
      <Line data={chartData} options={options} />
    </div>
  );
}

export default TelemetryChart;
