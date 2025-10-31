import { CSSProperties, HTMLAttributes } from "react";

export type CardProps = HTMLAttributes<HTMLDivElement> & {
  elevated?: boolean;
  padding?: "none" | "sm" | "md" | "lg";
};

const paddingMap: Record<NonNullable<CardProps["padding"]>, string> = {
  none: "0",
  sm: "var(--mw-spacing-sm)",
  md: "var(--mw-spacing-md)",
  lg: "var(--mw-spacing-lg)"
};

export function Card({
  elevated = true,
  padding = "md",
  style,
  children,
  ...props
}: CardProps) {
  const mergedStyle: CSSProperties = {
    background: "var(--mw-surface-card)",
    borderRadius: "var(--mw-radius-lg)",
    border: elevated ? "1px solid transparent" : "1px solid var(--mw-border-subtle)",
    boxShadow: elevated ? "var(--mw-shadow-md)" : "none",
    padding: paddingMap[padding],
    transition: "transform 160ms ease, box-shadow 200ms ease",
    ...style
  };

  return (
    <div
      style={mergedStyle}
      {...props}
      onMouseEnter={(event) => {
        if (elevated) {
          event.currentTarget.style.transform = "translateY(-1px)";
          event.currentTarget.style.boxShadow = "var(--mw-shadow-lg)";
        }
        props.onMouseEnter?.(event);
      }}
      onMouseLeave={(event) => {
        if (elevated) {
          event.currentTarget.style.transform = "translateY(0)";
          event.currentTarget.style.boxShadow = "var(--mw-shadow-md)";
        }
        props.onMouseLeave?.(event);
      }}
    >
      {children}
    </div>
  );
}
