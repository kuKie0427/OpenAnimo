import { useRef, useEffect, useCallback } from 'react';
import { EditorView, keymap, lineNumbers, drawSelection, highlightActiveLine, Decoration, type DecorationSet } from '@codemirror/view';
import { EditorState, StateEffect, StateField, type Extension } from '@codemirror/state';
import { markdown } from '@codemirror/lang-markdown';
import { oneDark } from '@codemirror/theme-one-dark';
import { indentUnit } from '@codemirror/language';
import { clsx } from 'clsx';
import { Button } from '~/components/ui/Button';

export interface ScriptEditorProps {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
  selectedLine?: number | null;
  onCursorActivity?: (lineNumber: number) => void;
}

const INDENT = '  ';

function wrapSelection(view: EditorView, before: string, after: string) {
  const { from, to } = view.state.selection.main;
  const selected = view.state.sliceDoc(from, to) || 'text';
  view.dispatch({
    changes: { from, to, insert: `${before}${selected}${after}` },
    selection: { anchor: from + before.length, head: from + before.length + selected.length },
  });
  view.focus();
}

function insertAtLineStart(view: EditorView, prefix: string) {
  const { from } = view.state.selection.main;
  const line = view.state.doc.lineAt(from);
  if (line.text.startsWith(prefix)) return;
  view.dispatch({
    changes: { from: line.from, to: line.from, insert: prefix },
    selection: { anchor: from + prefix.length },
  });
  view.focus();
}

function insertAtCursor(view: EditorView, text: string) {
  const { from } = view.state.selection.main;
  view.dispatch({
    changes: { from, to: from, insert: text },
    selection: { anchor: from + text.length },
  });
  view.focus();
}

const tabKeymap = keymap.of([
  {
    key: 'Tab',
    preventDefault: true,
    run: (view) => {
      const { from, to } = view.state.selection.main;
      if (from === to) {
        view.dispatch({
          changes: { from, insert: INDENT },
          selection: { anchor: from + INDENT.length },
        });
      } else {
        const lineFrom = view.state.doc.lineAt(from);
        const lineTo = view.state.doc.lineAt(to);
        const changes: { from: number; to: number; insert: string }[] = [];
        for (let i = lineFrom.number; i <= lineTo.number; i++) {
          const line = view.state.doc.line(i);
          changes.push({ from: line.from, to: line.from, insert: INDENT });
        }
        view.dispatch({ changes });
      }
      return true;
    },
  },
  {
    key: 'Shift-Tab',
    preventDefault: true,
    run: (view) => {
      const { from, to } = view.state.selection.main;
      const lineFrom = view.state.doc.lineAt(from);
      const lineTo = view.state.doc.lineAt(to);
      const changes: { from: number; to: number; insert: string }[] = [];
      for (let i = lineFrom.number; i <= lineTo.number; i++) {
        const line = view.state.doc.line(i);
        if (line.text.startsWith(INDENT)) {
          changes.push({ from: line.from, to: line.from + INDENT.length, insert: '' });
        }
      }
      if (changes.length > 0) {
        view.dispatch({ changes });
      }
      return true;
    },
  },
]);

const highlightLineEffect = StateEffect.define<number | null>();

const highlightLineField = StateField.define<DecorationSet>({
	create() { return Decoration.none; },
	update(decorations, tr) {
		for (const e of tr.effects) {
			if (e.is(highlightLineEffect)) {
				if (e.value === null) return Decoration.none;
				try {
					const line = tr.state.doc.line(e.value);
					return Decoration.set([
						Decoration.line({ class: 'cm-highlighted-paragraph' }).range(line.from),
					]);
				} catch {
					return decorations;
				}
			}
		}
		return decorations.map(tr.changes);
	},
	provide: (f) => EditorView.decorations.from(f),
});

export function ScriptEditor({ value, onChange, readOnly = false, selectedLine, onCursorActivity }: ScriptEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  const stableOnChange = useCallback(
    (doc: string) => {
      onChangeRef.current(doc);
    },
    [],
  );

  useEffect(() => {
    if (!editorRef.current) return;

		const updateListener = EditorView.updateListener.of((update) => {
			if (update.docChanged) {
				stableOnChange(update.state.doc.toString());
			}
			if (update.selectionSet || update.docChanged) {
				const pos = update.state.selection.main.head;
				const line = update.state.doc.lineAt(pos);
				onCursorActivity?.(line.number);
			}
		});

		const extensions: Extension[] = [
			markdown(),
			oneDark,
			lineNumbers(),
			drawSelection(),
			highlightActiveLine(),
			EditorView.lineWrapping,
			indentUnit.of(INDENT),
			tabKeymap,
			updateListener,
			highlightLineField,
		];

    if (readOnly) {
      extensions.push(EditorView.editable.of(false));
    }

    const startState = EditorState.create({
      doc: value,
      extensions,
    });

    const view = new EditorView({
      state: startState,
      parent: editorRef.current,
    });
    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
    // eslint-disable-next-line exhaustive-deps -- mount once only
  }, []);

	useEffect(() => {
		const view = viewRef.current;
		if (view && value !== view.state.doc.toString()) {
			view.dispatch({
				changes: { from: 0, to: view.state.doc.length, insert: value },
			});
		}
	}, [value]);

	useEffect(() => {
		const view = viewRef.current;
		if (view) {
			view.dispatch({
				effects: highlightLineEffect.of(selectedLine ?? null),
			});
		}
	}, [selectedLine]);

  const handleBold = useCallback(() => {
    const view = viewRef.current;
    if (view) wrapSelection(view, '**', '**');
  }, []);

  const handleItalic = useCallback(() => {
    const view = viewRef.current;
    if (view) wrapSelection(view, '*', '*');
  }, []);

  const handleH1 = useCallback(() => {
    const view = viewRef.current;
    if (view) insertAtLineStart(view, '# ');
  }, []);

  const handleH2 = useCallback(() => {
    const view = viewRef.current;
    if (view) insertAtLineStart(view, '## ');
  }, []);

  const handleAnchor = useCallback(() => {
    const view = viewRef.current;
    if (view) insertAtCursor(view, '<!-- shot: -->');
  }, []);

  return (
    <div className="flex flex-col rounded-lg border border-base-content/10 overflow-hidden bg-base-300">
      <div className="flex items-center gap-1 px-2 py-1.5 bg-base-200 border-b border-base-content/10">
        <ToolbarButton onClick={handleBold} disabled={readOnly} label="Bold">
          <span className="font-bold font-sans text-sm">B</span>
        </ToolbarButton>
        <ToolbarButton onClick={handleItalic} disabled={readOnly} label="Italic">
          <span className="italic font-sans text-sm">I</span>
        </ToolbarButton>

        <div className="w-px h-5 bg-base-content/10 mx-1" />

        <ToolbarButton onClick={handleH1} disabled={readOnly} label="Heading 1">
          <span className="font-heading font-bold text-sm leading-none">H1</span>
        </ToolbarButton>
        <ToolbarButton onClick={handleH2} disabled={readOnly} label="Heading 2">
          <span className="font-heading font-bold text-xs leading-none">H2</span>
        </ToolbarButton>

        <div className="w-px h-5 bg-base-content/10 mx-1" />

        <ToolbarButton onClick={handleAnchor} disabled={readOnly} label="Insert shot anchor">
          <span className="text-sm">🔗</span>
        </ToolbarButton>
      </div>

      <div
        ref={editorRef}
        className={clsx(
          'min-h-[400px] w-full',
          '[&_.cm-editor]:min-h-[400px]',
          '[&_.cm-editor]:h-full',
          '[&_.cm-scroller]:font-mono',
          '[&_.cm-content]:font-mono',
          readOnly && 'opacity-80',
        )}
      />
    </div>
  );
}

function ToolbarButton({
  onClick,
  disabled,
  label,
  children,
}: {
  onClick: () => void;
  disabled: boolean;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      disabled={disabled}
      onClick={onClick}
      aria-label={label}
      className="!px-2 !py-1 !min-h-0 h-7 w-7 !text-base-content/70 hover:!text-primary"
    >
      {children}
    </Button>
  );
}
