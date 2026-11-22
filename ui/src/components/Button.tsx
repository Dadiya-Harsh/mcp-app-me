import type { MouseEvent, ReactNode } from "react";

type Props = {
  children: ReactNode;
  variant?: "primary" | "secondary" | "link";
  /** Makes it a real link. `onOpen` gets the URL so the host can open it. */
  href?: string;
  onOpen?: (url: string) => void;
  onClick?: () => void;
};

const CLASS = { primary: "btn btn-primary", secondary: "btn", link: "btn btn-link" } as const;

export function Button({ children, variant = "secondary", href, onOpen, onClick }: Props) {
  if (href) {
    // A sandboxed iframe can't navigate, so the click goes to the host instead.
    const handle = (e: MouseEvent) => {
      e.preventDefault();
      onOpen?.(href);
    };
    return (
      <a className={CLASS[variant]} href={href} onClick={handle} target="_blank" rel="noreferrer noopener">
        {children}
      </a>
    );
  }
  return (
    <button type="button" className={CLASS[variant]} onClick={onClick}>
      {children}
    </button>
  );
}
