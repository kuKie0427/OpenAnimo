import { describe, expect, it, vi } from 'vitest';

import { canvasEvents } from './canvasEvents';

describe('canvasEvents', () => {
  it('delivers preview-image events to subscribers', () => {
    const handler = vi.fn();
    const unsubscribe = canvasEvents.on('preview-image', handler);

    canvasEvents.emit('preview-image', { src: '/img.png', alt: 'test' });
    expect(handler).toHaveBeenCalledWith({ src: '/img.png', alt: 'test' });

    unsubscribe();
  });

  it('delivers preview-video events to subscribers', () => {
    const handler = vi.fn();
    const unsubscribe = canvasEvents.on('preview-video', handler);

    canvasEvents.emit('preview-video', { src: '/vid.mp4', title: 'test video' });
    expect(handler).toHaveBeenCalledWith({ src: '/vid.mp4', title: 'test video' });

    unsubscribe();
  });

  it('stops delivering events after unsubscribe', () => {
    const handler = vi.fn();
    const unsubscribe = canvasEvents.on('preview-image', handler);
    unsubscribe();

    canvasEvents.emit('preview-image', { src: '/img.png', alt: 'test' });
    expect(handler).not.toHaveBeenCalled();
  });
});
