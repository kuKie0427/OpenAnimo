import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { CollapsibleMessage } from './CollapsibleMessage';

describe('CollapsibleMessage', () => {
  it('renders collapsed by default and expands on click', async () => {
    const user = userEvent.setup();

    render(
      <CollapsibleMessage summary="摘要内容">
        <div>完整内容</div>
      </CollapsibleMessage>
    );

    expect(screen.getByText('摘要内容')).toBeInTheDocument();
    expect(screen.getByText('点击展开')).toBeInTheDocument();
    expect(screen.queryByText('完整内容')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '展开查看详情' }));

    expect(screen.getByText('完整内容')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '收起详情' })).toBeInTheDocument();
  });

  it('starts expanded when defaultExpanded is true', () => {
    render(
      <CollapsibleMessage summary="摘要内容" defaultExpanded>
        <div>完整内容</div>
      </CollapsibleMessage>
    );

    expect(screen.getByText('完整内容')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '收起详情' })).toBeInTheDocument();
  });

  it('toggles on Enter key press', async () => {
    render(
      <CollapsibleMessage summary="摘要内容">
        <div>完整内容</div>
      </CollapsibleMessage>
    );

    const button = screen.getByRole('button', { name: '展开查看详情' });
    fireEvent.keyDown(button, { key: 'Enter' });

    expect(screen.getByText('完整内容')).toBeInTheDocument();
  });

  it('toggles on Space key press', async () => {
    render(
      <CollapsibleMessage summary="摘要内容">
        <div>完整内容</div>
      </CollapsibleMessage>
    );

    const button = screen.getByRole('button', { name: '展开查看详情' });
    fireEvent.keyDown(button, { key: ' ' });

    expect(screen.getByText('完整内容')).toBeInTheDocument();
  });
});
