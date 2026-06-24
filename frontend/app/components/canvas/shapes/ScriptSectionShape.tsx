import {
  HTMLContainer,
  Rectangle2d,
  ShapeUtil,
  T,
  type Geometry2d,
  type RecordProps,
} from "tldraw";
import { type ScriptSectionShape } from "./types";
import { SectionShell } from "./SectionShell";
import { useDomSize, getShapeSize } from "~/hooks/useDomSize";

export class ScriptSectionShapeUtil extends ShapeUtil<ScriptSectionShape> {
  static override type = "script-section" as const;

  static override props: RecordProps<ScriptSectionShape> = {
    w: T.number,
    h: T.number,
    story: T.string,
    summary: T.string,
    characters: T.any,
    shots: T.any,
    sectionState: T.string,
    placeholder: T.boolean,
    statusLabel: T.string,
    placeholderText: T.string,
  };

  getDefaultProps(): ScriptSectionShape["props"] {
    return {
      w: 800,
      h: 200,
      story: "",
      summary: "",
      characters: [],
      shots: [],
      sectionState: "draft",
      placeholder: true,
      statusLabel: "待生成",
      placeholderText: "等待剧本生成...",
    };
  }

  override canEdit() { return true; }
  override canResize() { return false; }
  override canCull() { return false; }

  getGeometry(shape: ScriptSectionShape): Geometry2d {
    const size = this.editor ? getShapeSize(this.editor, shape.id) : undefined;
    return new Rectangle2d({
      width: shape.props.w,
      height: size?.height ?? shape.props.h,
      isFilled: true,
    });
  }

  component(shape: ScriptSectionShape) {
    const { story, summary, shots, characters, placeholder, placeholderText, statusLabel, w } = shape.props;
    const ref = useDomSize(shape, this.editor ?? null);

    return (
      <HTMLContainer style={{ width: w, pointerEvents: "all", overflow: "visible" }}>
        <div ref={ref} style={{ width: w }}>
        <SectionShell
          sectionKey="plan"
          sectionTitle="编剧"
          statusLabel={statusLabel}
          placeholder={placeholder}
          placeholderText={placeholderText}
        >
          <div className="space-y-3">
            {story ? (
              <div className="rounded-lg p-3 bg-secondary/10">
                <p className="text-sm text-base-content/80 whitespace-pre-wrap leading-relaxed">{story}</p>
                {summary && (
                  <p className="text-xs text-base-content/50 mt-2 pt-2 border-t border-base-content/10">{summary}</p>
                )}
              </div>
            ) : summary ? (
              <div className="rounded-lg p-3 bg-secondary/10">
                <p className="text-sm text-base-content/80 whitespace-pre-wrap leading-relaxed">{summary}</p>
              </div>
            ) : null}
            {shots.length > 0 && (
              <div className="overflow-hidden rounded-lg border border-base-content/10">
                <table className="w-full text-xs">
                  <thead className="bg-base-200/80">
                    <tr>
                      <th className="px-2 py-1.5 text-left font-semibold w-8">#</th>
                      <th className="px-2 py-1.5 text-left font-semibold">描述</th>
                      <th className="px-2 py-1.5 text-left font-semibold w-16">运镜</th>
                      <th className="px-2 py-1.5 text-left font-semibold w-12">时长</th>
                      <th className="px-2 py-1.5 text-left font-semibold w-20">角色</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shots.map((shot, i) => {
                      const charNames = shot.character_ids
                        ?.map((cid) => characters.find((character) => character.id === cid)?.name)
                        .filter(Boolean);
                      return (
                        <tr key={shot.id} className={i % 2 === 0 ? "bg-base-100" : "bg-base-200/30"}>
                          <td className="px-2 py-1.5 text-base-content/60 font-mono truncate max-w-0">{shot.order}</td>
                          <td className="px-2 py-1.5 text-base-content/80 truncate max-w-0">{shot.description}</td>
                          <td className="px-2 py-1.5 text-base-content/60 truncate max-w-0">{shot.camera || "—"}</td>
                          <td className="px-2 py-1.5 text-base-content/60 truncate max-w-0">{shot.duration ? `${shot.duration}s` : "—"}</td>
                          <td className="px-2 py-1.5 text-base-content/60 truncate max-w-0">{charNames?.length ? charNames.join("、") : "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            {!story && !summary && shots.length === 0 && characters.length > 0 && (
              <div className="text-xs text-base-content/60">
                <span className="font-medium text-base-content/80">角色：</span>
                {characters.map((character) => character.name).join("、")}
              </div>
            )}
          </div>
        </SectionShell>
        </div>
      </HTMLContainer>
    );
  }

  indicator() {
    return null;
  }
}
