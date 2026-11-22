import type { KeyboardEvent } from "react";

type Tab<T extends string> = { id: T; label: string };

type Props<T extends string> = {
  tabs: readonly Tab<T>[];
  value: T;
  onChange: (id: T) => void;
  /** Used to link each tab to the panel it controls. */
  idPrefix: string;
  label: string;
};

/** Tab strip with arrow-key support. The panel itself is the caller's: give it
 * `id={`${idPrefix}-panel`}`, `role="tabpanel"` and `aria-labelledby={`${idPrefix}-${value}`}`. */
export function Tabs<T extends string>({ tabs, value, onChange, idPrefix, label }: Props<T>) {
  const move = (e: KeyboardEvent, index: number) => {
    let next = index;
    if (e.key === "ArrowRight") next = (index + 1) % tabs.length;
    else if (e.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    else return;
    e.preventDefault();
    onChange(tabs[next].id);
    document.getElementById(`${idPrefix}-${tabs[next].id}`)?.focus();
  };

  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {tabs.map((t, i) => {
        const selected = t.id === value;
        return (
          <button
            key={t.id}
            id={`${idPrefix}-${t.id}`}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={`${idPrefix}-panel`}
            tabIndex={selected ? 0 : -1}
            className={selected ? "tab tab-active" : "tab"}
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => move(e, i)}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
