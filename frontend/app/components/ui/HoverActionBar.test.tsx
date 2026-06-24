import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HoverActionBar } from './HoverActionBar';
import { describe, it, expect, vi } from 'vitest';
import { PencilIcon, TrashIcon } from '@heroicons/react/24/outline';

describe('HoverActionBar', () => {
  const mockActions = [
    {
      icon: PencilIcon,
      label: 'Edit',
      onClick: vi.fn(),
    },
    {
      icon: TrashIcon,
      label: 'Delete',
      onClick: vi.fn(),
      variant: 'error' as const,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children', () => {
    render(
      <HoverActionBar actions={mockActions}>
        <div>My Content</div>
      </HoverActionBar>
    );
    expect(screen.getByText('My Content')).toBeInTheDocument();
  });

  it('action bar is hidden by default', () => {
    render(
      <HoverActionBar actions={mockActions}>
        <div>My Content</div>
      </HoverActionBar>
    );
    // The bar is hidden with opacity-0, we can check for that
    const actionBar = screen.getByRole('button', { name: 'Edit' }).closest('div.absolute');
    expect(actionBar).toHaveClass('opacity-0');
  });

  it('shows action bar on mouse enter', async () => {
    render(
      <HoverActionBar actions={mockActions}>
        <div data-testid="container">My Content</div>
      </HoverActionBar>
    );
    const container = screen.getByTestId('container').parentElement!;
    const actionBar = screen.getByRole('button', { name: 'Edit' }).closest('div.absolute');

    expect(actionBar).toHaveClass('opacity-0');
    
    await userEvent.hover(container);

    expect(actionBar).toHaveClass('opacity-100');
    expect(screen.getByRole('button', { name: 'Edit' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeVisible();
  });
  
  it('hides action bar on mouse leave', async () => {
    render(
      <HoverActionBar actions={mockActions}>
        <div data-testid="container">My Content</div>
      </HoverActionBar>
    );
    const container = screen.getByTestId('container').parentElement!;
    const actionBar = screen.getByRole('button', { name: 'Edit' }).closest('div.absolute');

    await userEvent.hover(container);
    expect(actionBar).toHaveClass('opacity-100');
    
    await userEvent.unhover(container);
    expect(actionBar).toHaveClass('opacity-0');
  });

  it('calls correct onClick when an action button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <HoverActionBar actions={mockActions}>
        <div data-testid="container">My Content</div>
      </HoverActionBar>
    );
    
    await userEvent.hover(screen.getByTestId('container').parentElement!);

    const editButton = screen.getByRole('button', { name: 'Edit' });
    await user.click(editButton);
    expect(mockActions[0].onClick).toHaveBeenCalledTimes(1);
    expect(mockActions[1].onClick).not.toHaveBeenCalled();

    const deleteButton = screen.getByRole('button', { name: 'Delete' });
    await user.click(deleteButton);
    expect(mockActions[1].onClick).toHaveBeenCalledTimes(1);
  });

  it('disables button and shows loading state', async () => {
    const loadingActions = [
      { ...mockActions[0], loading: true },
      mockActions[1],
    ];
    render(
      <HoverActionBar actions={loadingActions}>
        <div data-testid="container">My Content</div>
      </HoverActionBar>
    );
    
    await userEvent.hover(screen.getByTestId('container').parentElement!);

    const editButton = screen.getByRole('button', { name: 'Edit' });
    expect(editButton).toBeDisabled();
    expect(editButton).toHaveClass('loading');
    
    const deleteButton = screen.getByRole('button', { name: 'Delete' });
    expect(deleteButton).not.toBeDisabled();
  });
});
