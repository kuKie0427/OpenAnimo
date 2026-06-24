import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ChatPanel } from './ChatPanel';
import type { WorkflowStage, CritiqueReviewEventData, RunAwaitingConfirmEventData } from '~/types';
import type { RunMode, GateName } from '~/stores/editorStore';

type ChatPanelStoreState = {
  messages: never[];
  currentAgent: string | null;
  awaitingConfirm: boolean;
  awaitingAgent: string | null;
  currentStage: WorkflowStage;
  currentRunId: number | null;
  runMode: RunMode;
  setRunMode: (mode: RunMode) => void;
  gateModes: Set<GateName>;
  setGateMode: (gate: GateName, enabled: boolean) => void;
  setGateModes: (gates: GateName[]) => void;
  resetGateModes: () => void;
  critiqueReviewCard: CritiqueReviewEventData | null;
  recoveryGate: RunAwaitingConfirmEventData | null;
};

const onSendFeedback = vi.fn();
const onConfirm = vi.fn();
const onGenerate = vi.fn();
const onCancel = vi.fn();
const setRunMode = vi.fn();

const storeState: ChatPanelStoreState = {
  messages: [] as never[],
  currentAgent: null,
  awaitingConfirm: false,
  awaitingAgent: null,
  currentStage: 'plan',
  currentRunId: null as number | null,
  runMode: 'manual',
  setRunMode,
  gateModes: new Set<GateName>(),
  setGateMode: vi.fn(),
  setGateModes: vi.fn(),
  resetGateModes: vi.fn(),
  critiqueReviewCard: null,
  recoveryGate: null,
};

vi.mock('~/stores/editorStore', () => ({
  useEditorStore: Object.assign(
    (selector?: (state: typeof storeState) => unknown) =>
      selector ? selector(storeState) : storeState,
    {
      getState: () => storeState,
    }
  ),
  useShallow: (selector: (state: typeof storeState) => unknown) => {
    const result = selector(storeState);
    return () => result;
  },
  ALL_GATES: ["outline", "characters", "shots", "character_images", "shot_images", "compose", "critique_characters", "critique_shots"],
  GATE_LABELS: {
    outline: "大纲审批",
    characters: "角色规划审批",
    shots: "分镜规划审批",
    character_images: "角色图片审批",
    shot_images: "分镜图片审批",
    compose: "视频合成审批",
    critique_characters: "Critic 角色审查",
    critique_shots: "Critic 分镜审查",
  },
}));

vi.mock('./MessageList', () => ({
  MessageList: () => <div data-testid="message-list" />,
}));

vi.mock('./CritiqueResultCard', () => ({
  CritiqueResultCard: ({ data }: any) => (
    <div data-testid="critique-result-card">
      {data.entity_type} review - {data.total} items
    </div>
  ),
}));

vi.mock('./VersionCompareInline', () => ({
  VersionCompareInline: ({ entityId, entityType, onClose }: any) => (
    <div data-testid="version-compare-inline">
      版本对比: {entityType} #{entityId}
      {onClose && <button onClick={onClose} data-testid="close-vc">关闭</button>}
    </div>
  ),
}));

vi.mock('./EntityApprovalCard', () => ({
  EntityApprovalCard: ({ entityType, entityLabel, entities }: any) => (
    <div data-testid="entity-approval-card">
      {entityLabel}审批 ({entities.length} 个实体)
      <span data-testid="entity-type">{entityType}</span>
    </div>
  ),
}));

describe('ChatPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(HTMLElement.prototype, 'scrollTo', {
      configurable: true,
      value: vi.fn(),
    });
    storeState.messages = [];
    storeState.currentAgent = null;
    storeState.awaitingConfirm = false;
    storeState.awaitingAgent = null;
    storeState.currentStage = 'plan';
    storeState.currentRunId = null;
    storeState.runMode = 'manual';
    storeState.gateModes = new Set<GateName>();
    storeState.critiqueReviewCard = null;
    storeState.recoveryGate = null;
  });

  it('shows the start button when there are no messages and generation has not started', () => {
    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating={false}
      />
    );

    expect(screen.getByRole('button', { name: '开始生成漫剧' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '开始生成漫剧' })).toHaveTextContent('开始生成');
  });

  it('disables generate and exposes the reason through aria-describedby', () => {
    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating={false}
        generateDisabled
        generateDisabledReason="还缺少角色设定"
      />
    );

    const button = screen.getByRole('button', { name: '开始生成漫剧' });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-describedby', 'generate-disabled-reason');
    expect(screen.getByText('还缺少角色设定')).toHaveAttribute('id', 'generate-disabled-reason');
  });

  it('shows processing state and stop button while generating', () => {
    storeState.currentAgent = 'plan';

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating
      />
    );

    expect(screen.getByText('规划...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '停止生成' })).toBeInTheDocument();
  });

  it('shows awaiting confirm area and sends trimmed feedback to confirm', async () => {
    const user = userEvent.setup();
    storeState.awaitingConfirm = true;
    storeState.awaitingAgent = 'plan';
    storeState.messages = [
      {
        id: '1',
        agent: 'plan',
        role: 'assistant',
        content: '完整内容',
        summary: '规划摘要',
      },
    ] as never[];

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating
      />
    );

    expect(screen.getByText(/规划 已完成/)).toBeInTheDocument();

    await user.type(screen.getByRole('textbox'), '  修改剧情节奏  ');
    await user.click(screen.getByRole('button', { name: /通过/ }));

    expect(onConfirm).toHaveBeenLastCalledWith('修改剧情节奏');
  });

  it('toggles between manual and YOLO mode', async () => {
    const user = userEvent.setup();
    storeState.runMode = 'manual';

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating={false}
      />
    );

    const toggleButton = screen.getByRole('button', { name: '切换YOLO模式' });
    await user.click(toggleButton);
    expect(setRunMode).toHaveBeenCalledWith('yolo');
  });

  it('hides manual confirm bar in YOLO mode', () => {
    storeState.awaitingConfirm = true;
    storeState.awaitingAgent = 'plan';
    storeState.runMode = 'yolo';

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating
      />
    );

    expect(screen.queryByText(/已完成/)).not.toBeInTheDocument();
  });

  it('sends feedback through onSendFeedback outside generating and confirm states', async () => {
    const user = userEvent.setup();

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating={false}
      />
    );

    await user.type(screen.getByRole('textbox'), '  这里有建议  ');
    await user.click(screen.getByRole('button', { name: '发送' }));

    expect(onSendFeedback).toHaveBeenLastCalledWith('  这里有建议  ');
  });

  it('shows render stage icon when currentStage is render', () => {
    storeState.currentStage = 'render';

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating={false}
      />
    );

    expect(screen.getByText('渲染阶段')).toBeInTheDocument();
  });

  it('shows render_approval stage icon when currentStage is render_approval', () => {
    storeState.currentStage = 'render_approval';

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating={false}
      />
    );

    expect(screen.getByText('渲染阶段')).toBeInTheDocument();
  });

  it('shows merge stage icon when currentStage is merge', () => {
    storeState.currentStage = 'compose';

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating={false}
      />
    );

    expect(screen.getByText('合成阶段')).toBeInTheDocument();
  });

  it('shows clip stage icon when currentStage is clip', () => {
    storeState.currentStage = 'compose';

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating={false}
      />
    );

    expect(screen.getByText('合成阶段')).toBeInTheDocument();
  });

  it('renders CritiqueResultCard when critiqueReviewCard is set', () => {
    storeState.critiqueReviewCard = {
      entity_type: 'character',
      total: 2,
      results: [],
    };
    storeState.currentRunId = 42;

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating
      />
    );

    expect(screen.getByTestId('critique-result-card')).toBeInTheDocument();
    expect(screen.getByText('character review - 2 items')).toBeInTheDocument();
  });

  it('does not render CritiqueResultCard when critiqueReviewCard is null', () => {
    storeState.critiqueReviewCard = null;
    storeState.currentRunId = 42;

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating
      />
    );

    expect(screen.queryByTestId('critique-result-card')).not.toBeInTheDocument();
  });

  it('shows version compare button when entity_ids exist in recoveryGate', () => {
    storeState.awaitingConfirm = true;
    storeState.awaitingAgent = 'character';
    storeState.recoveryGate = {
      entity_ids: [5],
      entity_type: 'character',
      agent: 'character',
      run_id: 1,
      recovery_summary: {},
    } as RunAwaitingConfirmEventData;

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating
      />
    );

    expect(screen.getByRole('button', { name: /查看版本对比/ })).toBeVisible();
  });

  it('hides version compare button when entity_ids is empty', () => {
    storeState.awaitingConfirm = true;
    storeState.awaitingAgent = 'character';
    storeState.recoveryGate = {
      run_id: 1,
      agent: 'character',
      recovery_summary: {} as any,
      entity_ids: [],
      entity_type: 'character',
    } as RunAwaitingConfirmEventData;

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating
      />
    );

    expect(screen.queryByRole('button', { name: /查看版本对比/ })).not.toBeInTheDocument();
  });

  it('toggles VersionCompareInline when clicking the version compare button', async () => {
    const user = userEvent.setup();
    storeState.awaitingConfirm = true;
    storeState.awaitingAgent = 'character';
    storeState.recoveryGate = {
      entity_ids: [5],
      entity_type: 'character',
      agent: 'character',
      run_id: 1,
      recovery_summary: {},
    } as RunAwaitingConfirmEventData;

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating
      />
    );

    expect(screen.queryByTestId('version-compare-inline')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /查看版本对比/ }));

    expect(screen.getByTestId('version-compare-inline')).toBeInTheDocument();
    expect(screen.getByText(/版本对比: character #5/)).toBeInTheDocument();
  });

  it('renders EntityApprovalCard when recoveryGate.entity_summaries has items', () => {
    storeState.awaitingConfirm = true;
    storeState.awaitingAgent = 'character';
    storeState.recoveryGate = {
      run_id: 1,
      agent: 'character',
      recovery_summary: {} as any,
      entity_type: 'character',
      entity_ids: [1, 2],
      entity_summaries: [
        { entity_id: 1, entity_name: '亚瑟', description: '战士', image_url: null, approval_state: 'draft' },
        { entity_id: 2, entity_name: '梅林', description: '法师', image_url: null, approval_state: 'draft' },
      ],
    } as RunAwaitingConfirmEventData;

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating
      />
    );

    expect(screen.getByTestId('entity-approval-card')).toBeInTheDocument();
    expect(screen.getByText('角色审批 (2 个实体)')).toBeInTheDocument();
    expect(screen.getByTestId('entity-type')).toHaveTextContent('character');
  });

  it('renders generic confirm bar when recoveryGate.entity_summaries is empty', () => {
    storeState.awaitingConfirm = true;
    storeState.awaitingAgent = 'character';
    storeState.recoveryGate = {
      run_id: 1,
      agent: 'character',
      recovery_summary: {} as any,
      entity_type: 'character',
      entity_ids: [5],
      entity_summaries: [],
    } as RunAwaitingConfirmEventData;

    render(
      <ChatPanel
        onSendFeedback={onSendFeedback}
        onConfirm={onConfirm}
        onGenerate={onGenerate}
        onCancel={onCancel}
        isGenerating
      />
    );

    expect(screen.queryByTestId('entity-approval-card')).not.toBeInTheDocument();
    expect(screen.getByText(/角色 已完成.*确认继续/)).toBeInTheDocument();
  });
});
