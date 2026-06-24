import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ShotlistPanel, type ShotSyncItem } from './ShotlistPanel';

vi.mock('~/services/api', () => ({
  getStaticUrl: (path: string | null) => path,
}));

vi.mock('~/components/ui/Button', () => ({
  Button: ({
    children,
    onClick,
    disabled,
    loading,
    'data-testid': testId,
    className,
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    loading?: boolean;
    'data-testid'?: string;
    className?: string;
  }) => (
    <button
      data-testid={testId}
      onClick={onClick}
      disabled={disabled || loading}
      className={className}
    >
      {loading ? '同步中...' : children}
    </button>
  ),
}));

const makeShots = (overrides?: Partial<ShotSyncItem>): ShotSyncItem[] => [
  {
    shot_id: 1,
    paragraph_index: 0,
    shot_order: 1,
    shot_description: 'A dark corridor with flickering lights',
    shot_image_url: 'https://example.com/shot1.png',
    is_synced: true,
    ...overrides,
  },
  {
    shot_id: 2,
    paragraph_index: 0,
    shot_order: 2,
    shot_description: 'Close-up of protagonist eyes',
    shot_image_url: null,
    is_synced: false,
  },
];

describe('ShotlistPanel', () => {
  it('renders shot cards for paragraph', () => {
    const shots = makeShots();
    render(<ShotlistPanel shots={shots} />);

    expect(screen.getByTestId('shotlist-panel')).toBeInTheDocument();
    expect(screen.getByTestId('shot-card-1')).toBeInTheDocument();
    expect(screen.getByTestId('shot-card-2')).toBeInTheDocument();
    expect(screen.getByText('分镜预览')).toBeInTheDocument();
  });

  it('highlights selected shot with amber ring', () => {
    const shots = makeShots();
    render(<ShotlistPanel shots={shots} selectedShotId={1} />);

    const selectedCard = screen.getByTestId('shot-card-1');
    expect(selectedCard.className).toContain('ring-2');
    expect(selectedCard.className).toContain('ring-primary');

    const unselectedCard = screen.getByTestId('shot-card-2');
    expect(unselectedCard.className).not.toContain('ring-primary');
  });

  it('shows empty state when shots are empty', () => {
    render(<ShotlistPanel shots={[]} />);

    expect(screen.getByTestId('shotlist-empty')).toBeInTheDocument();
    expect(screen.getByText('该段落无对应分镜')).toBeInTheDocument();
    expect(screen.queryByTestId('shotlist-sync-btn')).not.toBeInTheDocument();
  });

  it('calls onSelectShot when a card is clicked', () => {
    const onSelectShot = vi.fn();
    const shots = makeShots();
    render(<ShotlistPanel shots={shots} onSelectShot={onSelectShot} />);

    fireEvent.click(screen.getByTestId('shot-card-1'));
    expect(onSelectShot).toHaveBeenCalledWith(1);
  });

  it('shows sync button when shots exist and hides it when empty', () => {
    const shots = makeShots();
    const { rerender } = render(<ShotlistPanel shots={shots} />);
    expect(screen.getByTestId('shotlist-sync-btn')).toBeInTheDocument();

    rerender(<ShotlistPanel shots={[]} />);
    expect(screen.queryByTestId('shotlist-sync-btn')).not.toBeInTheDocument();
  });

  it('disables sync button and shows spinner when syncing', () => {
    const shots = makeShots();
    render(<ShotlistPanel shots={shots} isSyncing />);

    const syncBtn = screen.getByTestId('shotlist-sync-btn');
    expect(syncBtn).toBeDisabled();
    expect(syncBtn.textContent).toContain('同步中...');
  });
});
