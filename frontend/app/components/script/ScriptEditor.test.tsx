import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ScriptEditor } from './ScriptEditor';

// Mock CodeMirror modules to avoid browser API requirements (jsdom does not
// provide the full DOM environment CodeMirror needs).
vi.mock('@codemirror/view', () => {
	class MockEditorView {
		destroy = vi.fn();
		dispatch = vi.fn();
		focus = vi.fn();
		state = {
			doc: { toString: () => '' },
			selection: { main: { from: 0, to: 0 } },
			lineAt: vi.fn(() => ({ from: 0, text: '' })),
		};
		static updateListener = { of: vi.fn(() => ({})) };
		static lineWrapping = Symbol('lineWrapping');
		static editable = { of: vi.fn(() => ({})) };
		static decorations = { from: vi.fn(() => ({})) };
	}
	return {
		EditorView: MockEditorView,
		keymap: { of: vi.fn(() => ({})) },
		lineNumbers: vi.fn(() => ({})),
		drawSelection: vi.fn(() => ({})),
		highlightActiveLine: vi.fn(() => ({})),
		Decoration: {
			none: Symbol('none'),
			set: vi.fn(() => ({})),
			line: vi.fn(() => ({ range: () => ({}) })),
		},
	};
});

vi.mock('@codemirror/state', () => ({
	EditorState: {
		create: vi.fn(() => ({
			doc: { toString: () => '', lineAt: vi.fn() },
			selection: { main: { from: 0, to: 0 } },
		})),
	},
	StateEffect: {
		define: vi.fn(() => ({
			is: () => false,
			of: (val: unknown) => ({ type: 'effect', value: val }),
		})),
	},
	StateField: {
		define: vi.fn(() => ({})),
	},
}));

vi.mock('@codemirror/lang-markdown', () => ({ markdown: vi.fn(() => ({})) }));
vi.mock('@codemirror/theme-one-dark', () => ({ oneDark: {} }));
vi.mock('@codemirror/language', () => ({ indentUnit: { of: vi.fn(() => ({})) } }));

describe('ScriptEditor', () => {
  it('renders editor container', () => {
    const { container } = render(<ScriptEditor value="" onChange={() => {}} />);

    // The editor container div has the `w-full` class — the toolbar above it
    // does not, so this reliably identifies the CodeMirror mount point.
    const editorDiv = container.querySelector('.w-full');
    expect(editorDiv).toBeTruthy();
  });

  it('applies read-only mode with disabled toolbar and opacity class', () => {
    const { container } = render(
      <ScriptEditor value="some text" onChange={() => {}} readOnly />,
    );

    // Editor container should have reduced opacity
    const editorDiv = container.querySelector('.opacity-80');
    expect(editorDiv).toBeTruthy();

    // All toolbar buttons should be disabled when readOnly is true
    expect(screen.getByRole('button', { name: 'Bold' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Italic' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Heading 1' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Heading 2' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Insert shot anchor' })).toBeDisabled();
  });

  it('renders toolbar buttons with correct aria-labels', () => {
    render(<ScriptEditor value="" onChange={() => {}} />);

    // Each ToolbarButton passes its label prop as aria-label to <Button>
    expect(screen.getByRole('button', { name: 'Bold' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Italic' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Heading 1' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Heading 2' })).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Insert shot anchor' }),
    ).toBeInTheDocument();
  });
});
