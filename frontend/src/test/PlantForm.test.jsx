import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PlantForm from '../components/PlantForm';

describe('PlantForm', () => {
  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders create mode form', () => {
    render(<PlantForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
    
    expect(screen.getByLabelText(/plant id/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/location/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create plant/i })).toBeInTheDocument();
  });

  it('renders edit mode form with plant data', () => {
    const plant = {
      plant_id: 'test_plant',
      name: 'Test Plant',
      location: 'Test Location',
    };

    render(<PlantForm plant={plant} onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
    
    expect(screen.getByDisplayValue('test_plant')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Test Plant')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Test Location')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /update plant/i })).toBeInTheDocument();
  });

  it('disables plant_id field in edit mode', () => {
    const plant = { plant_id: 'test_plant', name: 'Test' };
    render(<PlantForm plant={plant} onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
    
    const plantIdInput = screen.getByLabelText(/plant id/i);
    expect(plantIdInput).toBeDisabled();
  });

  it('validates required plant_id field', async () => {
    render(<PlantForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
    
    const submitButton = screen.getByRole('button', { name: /create plant/i });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/plant id is required/i)).toBeInTheDocument();
    });
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('validates plant_id max length', async () => {
    render(<PlantForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
    
    const plantIdInput = screen.getByLabelText(/plant id/i);
    fireEvent.change(plantIdInput, { target: { value: 'a'.repeat(65) } });
    
    const submitButton = screen.getByRole('button', { name: /create plant/i });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/cannot exceed 64 characters/i)).toBeInTheDocument();
    });
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('submits valid form data', async () => {
    render(<PlantForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
    
    fireEvent.change(screen.getByLabelText(/plant id/i), { target: { value: 'new_plant' } });
    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'New Plant' } });
    fireEvent.change(screen.getByLabelText(/location/i), { target: { value: 'Kitchen' } });
    
    const submitButton = screen.getByRole('button', { name: /create plant/i });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        plant_id: 'new_plant',
        name: 'New Plant',
        location: 'Kitchen',
      });
    });
  });

  it('calls onCancel when cancel button clicked', () => {
    render(<PlantForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
    
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);
    
    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('clears error when field value changes', async () => {
    render(<PlantForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);
    
    // Trigger validation error
    const submitButton = screen.getByRole('button', { name: /create plant/i });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/plant id is required/i)).toBeInTheDocument();
    });
    
    // Change field value
    const plantIdInput = screen.getByLabelText(/plant id/i);
    fireEvent.change(plantIdInput, { target: { value: 'test' } });
    
    // Error should be cleared
    expect(screen.queryByText(/plant id is required/i)).not.toBeInTheDocument();
  });
});
