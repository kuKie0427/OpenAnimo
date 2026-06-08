import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ArtifactVersion } from '~/types';
import { VersionCompareInline } from './VersionCompareInline';
import { versionsApi } from '~/services/api';

vi.mock('~/services/api', () => ({
	versionsApi: {
		list: vi.fn(),
		compare: vi.fn(),
	},
	getStaticUrl: (url: string | null | undefined) => url || '',
}));

vi.mock('~/stores/editorStore', () => ({
	useEditorStore: Object.assign(
		(selector?: (state: any) => unknown) => (selector ? selector({}) : {}),
		{ getState: () => ({}) },
	),
	useShallow: (selector: (state: any) => unknown) => () => selector({}),
}));

vi.mock('~/components/panels/VersionCompareDrawer', () => ({
	VersionColumn: ({ title }: any) => <div data-testid="version-column">{title}</div>,
	DiffRow: ({ diff }: any) => (
		<div data-testid="diff-row">
			{diff.field_name}: {String(diff.old_value)} → {String(diff.new_value)}
		</div>
	),
}));

function createWrapper() {
	const queryClient = new QueryClient({
		defaultOptions: {
			queries: { retry: false, gcTime: 0 },
		},
	});
	return function Wrapper({ children }: { children: React.ReactNode }) {
		return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
	};
}

describe('VersionCompareInline', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('renders version comparison when versions are available', async () => {
		const v2: ArtifactVersion = {
			id: 2,
			entity_type: 'character',
			entity_id: 5,
			version: 2,
			snapshot: { name: 'Hero', image_url: '/img.png', description: 'desc v2' },
			trigger: 'render',
			created_at: '2026-01-02T00:00:00Z',
		};
		const v1: ArtifactVersion = {
			id: 1,
			entity_type: 'character',
			entity_id: 5,
			version: 1,
			snapshot: { name: 'Hero', image_url: '/img.png', description: 'desc v1' },
			trigger: 'render',
			created_at: '2026-01-01T00:00:00Z',
		};
		vi.mocked(versionsApi.list).mockResolvedValue({
			entity_type: 'character',
			entity_id: 5,
			versions: [v2, v1],
		});
		vi.mocked(versionsApi.compare).mockResolvedValue({
			entity_type: 'character',
			entity_id: 5,
			from_version: v1,
			to_version: v2,
			diffs: [{ field_name: 'description', old_value: 'desc v1', new_value: 'desc v2' }],
		});

		render(<VersionCompareInline projectId={1} entityType="character" entityId={5} />, {
			wrapper: createWrapper(),
		});

		await waitFor(() => {
			expect(screen.getByText('版本对比: Hero (v1 → v2)')).toBeInTheDocument();
		});

		expect(screen.getAllByTestId('version-column')).toHaveLength(2);
		expect(await screen.findAllByTestId('diff-row')).toHaveLength(1);
		expect(vi.mocked(versionsApi.list)).toHaveBeenCalledWith(1, 'character', 5);
	});

	it('shows empty state when only 1 version exists', async () => {
		vi.mocked(versionsApi.list).mockResolvedValue({
			entity_type: 'character',
			entity_id: 5,
			versions: [
				{
					id: 1,
					entity_type: 'character',
					entity_id: 5,
					version: 1,
					snapshot: {} as Record<string, unknown>,
					trigger: 'render',
					created_at: '2026-01-01T00:00:00Z',
				},
			],
		});

		render(<VersionCompareInline projectId={1} entityType="character" entityId={5} />, {
			wrapper: createWrapper(),
		});

		await waitFor(() => {
			expect(screen.getByText('暂无历史版本')).toBeInTheDocument();
		});
	});

	it('shows error state when API fails', async () => {
		vi.mocked(versionsApi.list).mockRejectedValue(new Error('Network error'));

		render(<VersionCompareInline projectId={1} entityType="character" entityId={5} />, {
			wrapper: createWrapper(),
		});

		await waitFor(() => {
			expect(screen.getByText('加载失败: Network error')).toBeInTheDocument();
		});
	});
});
