import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EditModal } from './EditModal';
import { describe, it, expect, vi } from 'vitest';

describe('EditModal', () => {
  const fields = [
    { name: 'title', label: 'Title', type: 'text' as const },
    { name: 'description', label: 'Description', type: 'textarea' as const },
  ];

  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSave: vi.fn().mockResolvedValue(undefined),
    fields: fields,
    initialData: { title: 'Initial Title', description: 'Initial Description' },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when isOpen is false', () => {
    render(<EditModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
  
  const getModal = () => screen.getByText('Edit Content').closest('.modal-open');

  it('renders correctly when isOpen is true with initial data', () => {
    render(<EditModal {...defaultProps} />);
    
    expect(getModal()).toBeInTheDocument();
    expect(screen.getByText('Edit Content')).toBeInTheDocument(); // default title
    expect(screen.getByLabelText('Title')).toHaveValue('Initial Title');
    expect(screen.getByLabelText('Description')).toHaveValue('Initial Description');
  });

  it('updates form data on user input', async () => {
    const user = userEvent.setup();
    render(<EditModal {...defaultProps} />);
    
    const titleInput = screen.getByLabelText('Title');
    await user.clear(titleInput);
    await user.type(titleInput, 'New Title');
    expect(titleInput).toHaveValue('New Title');

    const descriptionInput = screen.getByLabelText('Description');
    await user.clear(descriptionInput);
    await user.type(descriptionInput, 'New Description');
    expect(descriptionInput).toHaveValue('New Description');
  });

  it('calls onSave with updated data when save button is clicked', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<EditModal {...defaultProps} onSave={onSave} />);

    const titleInput = screen.getByLabelText('Title');
    await user.clear(titleInput);
    await user.type(titleInput, 'Updated Title');

    const saveButton = screen.getByRole('button', { name: 'Save', hidden: true });
    await user.click(saveButton);

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith({
        title: 'Updated Title',
        description: 'Initial Description',
      });
    });
  });

  it('calls onClose when cancel button is clicked', async () => {
    const user = userEvent.setup();
    render(<EditModal {...defaultProps} />);

    await user.click(screen.getByRole('button', { name: 'Cancel', hidden: true }));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });
  
  it('calls onClose when close icon is clicked', async () => {
    const user = userEvent.setup();
    render(<EditModal {...defaultProps} />);
    
    const closeBtn = document.querySelector('.btn-circle') as HTMLElement;
    await user.click(closeBtn);
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });
  
  it('calls onClose when backdrop is clicked', async () => {
    const user = userEvent.setup();
    render(<EditModal {...defaultProps} />);
    
    // The backdrop is the div with class .modal-backdrop
    await user.click(document.querySelector('.modal-backdrop')!);
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it('shows loading state and disables buttons', () => {
    render(<EditModal {...defaultProps} isLoading={true} />);

    const saveButton = screen.getByRole('button', { name: 'Saving...', hidden: true });
    expect(saveButton).toBeDisabled();
    expect(saveButton).toHaveClass('loading');
  });

  it('resets form to initialData when re-opened', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<EditModal {...defaultProps} />);
    
    const titleInput = screen.getByLabelText('Title');
    await user.clear(titleInput);
    await user.type(titleInput, 'Temporary Change');
    expect(titleInput).toHaveValue('Temporary Change');

    // "Close" the modal
    rerender(<EditModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    // "Re-open" the modal
    rerender(<EditModal {...defaultProps} isOpen={true} />);
    expect(screen.getByLabelText('Title')).toHaveValue('Initial Title');
  });
});
