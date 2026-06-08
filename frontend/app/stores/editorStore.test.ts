import { beforeEach, describe, expect, it } from 'vitest';

import { useEditorStore } from '~/stores/editorStore';
import type { Character, Shot, CritiqueReviewEventData } from '~/types';

describe('useEditorStore review contract', () => {
  beforeEach(() => {
    useEditorStore.getState().reset();
  });

  it('stores server-authored character approval state', () => {
    const draftCharacter: Character = {
      id: 1,
      project_id: 9,
      name: 'Mika',
      description: 'A cautious creator',
      image_url: '/static/characters/mika-draft.png',
      approval_state: 'draft',
      approval_version: 0,
      approved_at: null,
      approved_name: null,
      approved_description: null,
      approved_image_url: null,
    };

    const approvedCharacter: Character = {
      ...draftCharacter,
      name: 'Mika Prime',
      image_url: '/static/characters/mika-approved.png',
      approval_state: 'approved',
      approval_version: 2,
      approved_at: '2026-04-11T10:00:00.000Z',
      approved_name: 'Mika Prime',
      approved_description: 'A confident creator',
      approved_image_url: '/static/characters/mika-approved.png',
    };

    useEditorStore.getState().setCharacters([draftCharacter]);
    useEditorStore.getState().updateCharacter(approvedCharacter);

    expect(useEditorStore.getState().characters[0]).toEqual(approvedCharacter);
  });

  it('stores server-authored shot approval state', () => {
    const draftShot: Shot = {
      id: 11,
      project_id: 9,
      order: 1,
      description: 'Opening shot',
      prompt: 'A quiet opening at dawn',
      image_prompt: 'dawn over a city roof',
      image_url: '/static/shots/11-draft.png',
      video_url: '/static/shots/11-draft.mp4',
      duration: 8.5,
      camera: 'wide',
      motion_note: 'slow pan in',
      scene: null, action: null, expression: null, lighting: null, dialogue: null, sfx: null,
      character_ids: [1],
      approval_state: 'draft',
      approval_version: 0,
      approved_at: null,
      approved_description: null,
      approved_prompt: null,
      approved_image_prompt: null,
      approved_duration: null,
      approved_camera: null,
      approved_motion_note: null,
      approved_scene: null, approved_action: null, approved_expression: null,
      approved_lighting: null, approved_dialogue: null, approved_sfx: null,
      approved_character_ids: [],
      seed: null,
    };

    const supersededShot: Shot = {
      ...draftShot,
      description: 'Opening shot, tightened',
      prompt: 'A tighter opening at dawn',
      approval_state: 'superseded',
      approval_version: 3,
      approved_at: '2026-04-11T10:15:00.000Z',
      approved_description: 'Opening shot',
      approved_prompt: 'A quiet opening at dawn',
      approved_image_prompt: 'dawn over a city roof',
      approved_duration: 8.5,
      approved_camera: 'wide',
      approved_motion_note: 'slow pan in',
      approved_scene: null, approved_action: null, approved_expression: null,
      approved_lighting: null, approved_dialogue: null, approved_sfx: null,
      approved_character_ids: [1],
    };

    useEditorStore.getState().setShots([draftShot]);
    useEditorStore.getState().updateShot(supersededShot);

    expect(useEditorStore.getState().shots[0]).toEqual(supersededShot);
  });

  it('toggles runMode between manual and yolo', () => {
    expect(useEditorStore.getState().runMode).toBe('manual');
    useEditorStore.getState().setRunMode('yolo');
    expect(useEditorStore.getState().runMode).toBe('yolo');
    useEditorStore.getState().setRunMode('manual');
    expect(useEditorStore.getState().runMode).toBe('manual');
  });

  it('resetRunState clears run fields without touching data', () => {
    const store = useEditorStore.getState();
    store.setGenerating(true);
    store.setCurrentAgent('plan');
    store.setProgress(0.5);
    store.setCurrentRunId(42);
    store.setAwaitingConfirm(true, 'plan', 42);
    store.setCharacters([{ id: 1, project_id: 9, name: 'A', description: '', image_url: '', approval_state: 'draft', approval_version: 0, approved_at: null, approved_name: null, approved_description: null, approved_image_url: null }]);

    store.resetRunState();

    const s = useEditorStore.getState();
    expect(s.isGenerating).toBe(false);
    expect(s.currentAgent).toBeNull();
    expect(s.progress).toBe(0);
    expect(s.currentRunId).toBeNull();
    expect(s.awaitingConfirm).toBe(false);
    expect(s.awaitingAgent).toBeNull();
    expect(s.characters).toHaveLength(1);
    expect(s.currentStage).toBe('plan');
  });

  it("setCritiqueReviewCard sets card and awaiting states", () => {
    const data: CritiqueReviewEventData = {
      entity_type: "character",
      total: 2,
      results: [
        {
          entity_id: 1,
          entity_name: "Alice",
          score: 8.5,
          dimensions: {},
          issues: [],
          suggestions: [],
          will_regenerate: false,
          failed_checks: [],
          image_url: null,
        },
        {
          entity_id: 2,
          entity_name: "Bob",
          score: 4.0,
          dimensions: {},
          issues: [],
          suggestions: [],
          will_regenerate: true,
          failed_checks: [],
          image_url: null,
        },
      ],
    };
    useEditorStore.getState().setCritiqueReviewCard(data);
    const s = useEditorStore.getState();
    expect(s.critiqueReviewCard).toEqual(data);
    expect(s.awaitingConfirm).toBe(true);
    expect(s.awaitingAgent).toBe("critic");
  });

  it("setCritiqueOverride adds to overrides map", () => {
    useEditorStore.getState().setCritiqueOverride(3, true);
    expect(useEditorStore.getState().critiqueOverrides[3]).toBe(true);

    useEditorStore.getState().setCritiqueOverride(5, false);
    expect(useEditorStore.getState().critiqueOverrides[5]).toBe(false);
    // Previous override preserved
    expect(useEditorStore.getState().critiqueOverrides[3]).toBe(true);
  });

  it("clearCritiqueReview resets all critic state", () => {
    useEditorStore.getState().setCritiqueOverride(1, true);
    useEditorStore.getState().setCritiqueReviewCard({
      entity_type: "character",
      total: 1,
      results: [],
    });
    useEditorStore.getState().clearCritiqueReview();
    const s = useEditorStore.getState();
    expect(s.critiqueReviewCard).toBeNull();
    expect(s.critiqueOverrides).toEqual({});
    expect(s.awaitingConfirm).toBe(false);
    expect(s.awaitingAgent).toBeNull();
  });

  it('setGateMode adds gate to set', () => {
    useEditorStore.getState().reset();
    useEditorStore.getState().setGateMode('outline', true);
    expect(useEditorStore.getState().gateModes.has('outline')).toBe(true);
    expect(useEditorStore.getState().gateModes.size).toBe(1);
  });

  it('setGateMode removes gate from set', () => {
    useEditorStore.getState().reset();
    useEditorStore.getState().setGateMode('outline', true);
    useEditorStore.getState().setGateMode('outline', false);
    expect(useEditorStore.getState().gateModes.has('outline')).toBe(false);
    expect(useEditorStore.getState().gateModes.size).toBe(0);
  });

  it('setGateModes bulk sets multiple gates', () => {
    useEditorStore.getState().reset();
    useEditorStore.getState().setGateModes(['outline', 'shots']);
    expect(useEditorStore.getState().gateModes.size).toBe(2);
    expect(useEditorStore.getState().gateModes.has('outline')).toBe(true);
    expect(useEditorStore.getState().gateModes.has('shots')).toBe(true);
    expect(useEditorStore.getState().gateModes.has('compose')).toBe(false);
  });

  it('resetGateModes clears all gates', () => {
    useEditorStore.getState().reset();
    useEditorStore.getState().setGateModes(['outline', 'shots', 'compose']);
    expect(useEditorStore.getState().gateModes.size).toBe(3);
    useEditorStore.getState().resetGateModes();
    expect(useEditorStore.getState().gateModes.size).toBe(0);
  });
});
