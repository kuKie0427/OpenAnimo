import React, { useState, useEffect } from "react";
import { SvgIcon } from "~/components/ui/SvgIcon";

interface FieldConfig {
  name: string;
  label: string;
  type: "text" | "textarea";
  defaultValue?: string;
}

interface EditModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: Record<string, string>) => Promise<void>;
  fields: FieldConfig[];
  title?: string;
  initialData: Record<string, string>;
  isLoading?: boolean;
}

export function EditModal({
  isOpen,
  onClose,
  onSave,
  fields,
  title = "Edit Content",
  initialData,
  isLoading = false,
}: EditModalProps) {
  const [formData, setFormData] = useState(initialData);

  useEffect(() => {
    if (isOpen) {
      setFormData(initialData);
    }
  }, [isOpen, initialData]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    await onSave(formData);
  };

  if (!isOpen) return null;

  return (
    <dialog className="modal modal-open" aria-modal="true" aria-labelledby="edit-modal-heading">
      <div className="modal-box card-screen">
        <h3 id="edit-modal-heading" className="font-bold text-lg mb-4">{title}</h3>
        <button
          className="btn btn-sm btn-circle btn-ghost absolute right-2 top-2"
          onClick={onClose}
        >
          <SvgIcon name="x" size={14} />
        </button>

        <div className="space-y-4">
          {fields.map((field) => {
            const id = `edit-modal-${field.name}`;
            return (
              <div key={field.name} className="form-control">
                <label htmlFor={id} className="label">
                  <span className="label-text">{field.label}</span>
                </label>
                {field.type === "textarea" ? (
                  <textarea
                    id={id}
                    name={field.name}
                    value={formData[field.name] || ""}
                    onChange={handleChange}
                    className="textarea textarea-bordered h-24 input-field"
                    rows={4}
                  />
                ) : (
                  <input
                    id={id}
                    type="text"
                    name={field.name}
                    value={formData[field.name] || ""}
                    onChange={handleChange}
                    className="input input-bordered input-field"
                  />
                )}
              </div>
            );
          })}
        </div>

        <div className="modal-action mt-6">
          <button className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            className={`btn btn-primary btn-projection ${isLoading ? "loading" : ""}`}
            onClick={handleSave}
            disabled={isLoading}
          >
            {isLoading ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
      <div className="modal-backdrop" onClick={onClose}></div>
    </dialog>
  );
}
