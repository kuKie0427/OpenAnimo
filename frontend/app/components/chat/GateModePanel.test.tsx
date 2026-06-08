import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { GateModePanel } from './GateModePanel';
import { ALL_GATES, type GateName, GATE_LABELS } from '~/stores/editorStore';

describe('GateModePanel', () => {
	it('renders "全部手动" when no gates selected', () => {
		render(
			<GateModePanel
				gateModes={new Set()}
				onToggle={vi.fn()}
				onSetAll={vi.fn()}
			/>,
		);
		// Appears both in summary text and as a preset button
		expect(screen.getAllByText('全部手动').length).toBeGreaterThanOrEqual(1);
	});

	it('renders "全部自动" when all gates selected', () => {
		render(
			<GateModePanel
				gateModes={new Set(ALL_GATES)}
				onToggle={vi.fn()}
				onSetAll={vi.fn()}
			/>,
		);
		expect(screen.getByText('全部自动')).toBeTruthy();
	});

	it('renders custom count when partial gates selected', () => {
		render(
			<GateModePanel
				gateModes={new Set(['outline', 'shots'] as GateName[])}
				onToggle={vi.fn()}
				onSetAll={vi.fn()}
			/>,
		);
		expect(screen.getByText(/自定义/)).toBeTruthy();
	});

	it('calls onSetAll with ALL_GATES when "全部 YOLO" clicked', () => {
		const onSetAll = vi.fn();
		render(
			<GateModePanel
				gateModes={new Set()}
				onToggle={vi.fn()}
				onSetAll={onSetAll}
			/>,
		);
		// Click to expand the collapse
		const collapseInput = screen.getByLabelText('展开/收起 YOLO 模式配置');
		fireEvent.click(collapseInput);
		// Click "全部 YOLO" button
		const yoloBtn = screen.getByText('全部 YOLO');
		fireEvent.click(yoloBtn);
		expect(onSetAll).toHaveBeenCalledWith(ALL_GATES);
	});

	it('renders all 8 gate labels', () => {
		render(
			<GateModePanel
				gateModes={new Set()}
				onToggle={vi.fn()}
				onSetAll={vi.fn()}
			/>,
		);
		for (const label of Object.values(GATE_LABELS)) {
			expect(screen.getAllByText(label).length).toBeGreaterThanOrEqual(1);
		}
	});
});
