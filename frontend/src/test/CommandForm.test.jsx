import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CommandForm from '../components/CommandForm';

describe('CommandForm', () => {
  let mockOnCommandSent;
  let mockOnError;

  beforeEach(() => {
    mockOnCommandSent = vi.fn();
    mockOnError = vi.fn();
    vi.clearAllMocks();
  });

  it('should render command form with default values', () => {
    render(
      <CommandForm
        plantId="test_plant_01"
        onCommandSent={mockOnCommandSent}
        onError={mockOnError}
      />
    );

    expect(screen.getByLabelText('Send Command:')).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toHaveValue('water');
    expect(screen.getByRole('button', { name: /Send Command/i })).toBeInTheDocument();
  });

  it('should have all command options in dropdown', () => {
    render(
      <CommandForm
        plantId="test_plant_01"
        onCommandSent={mockOnCommandSent}
        onError={mockOnError}
      />
    );

    const select = screen.getByRole('combobox');
    const options = select.querySelectorAll('option');

    expect(options).toHaveLength(1);
    expect(options[0]).toHaveValue('water');
  });

  it('should call onCommandSent on successful submission', async () => {
    const user = userEvent.setup();
    const mockResponse = {
      id: 1,
      command: 'water',
      cmd_id: 'test-123',
      status: 'pending',
    };

    // Mock the sendCommand import
    vi.doMock('../api/client', () => ({
      sendCommand: vi.fn().mockResolvedValue(mockResponse),
    }));

    render(
      <CommandForm
        plantId="test_plant_01"
        onCommandSent={mockOnCommandSent}
        onError={mockOnError}
      />
    );

    const button = screen.getByRole('button', { name: /Send Command/i });
    await user.click(button);

    await waitFor(() => {
      expect(mockOnCommandSent).toHaveBeenCalledWith(mockResponse);
    });
  });

  it('should disable form while sending', async () => {
    const user = userEvent.setup();

    vi.doMock('../api/client', () => ({
      sendCommand: vi.fn().mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      ),
    }));

    render(
      <CommandForm
        plantId="test_plant_01"
        onCommandSent={mockOnCommandSent}
        onError={mockOnError}
      />
    );

    const button = screen.getByRole('button', { name: /Send Command/i });
    await user.click(button);

    // Button should show "Sending..." and be disabled
    await waitFor(() => {
      expect(screen.getByText('Sending...')).toBeInTheDocument();
      expect(button).toBeDisabled();
    });
  });

  it('should call onError on failed submission', async () => {
    const user = userEvent.setup();
    const errorMessage = 'Network error';

    vi.doMock('../api/client', () => ({
      sendCommand: vi.fn().mockRejectedValue({
        response: { data: { error: errorMessage } },
      }),
    }));

    render(
      <CommandForm
        plantId="test_plant_01"
        onCommandSent={mockOnCommandSent}
        onError={mockOnError}
      />
    );

    const button = screen.getByRole('button', { name: /Send Command/i });
    await user.click(button);

    await waitFor(() => {
      expect(mockOnError).toHaveBeenCalled();
    });
  });
});
