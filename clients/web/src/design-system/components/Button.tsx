import { forwardRef } from "react";
import type { ButtonHTMLAttributes, CSSProperties } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "var(--mw-spacing-xs) var(--mw-spacing-sm)",
  md: "calc(var(--mw-spacing-sm) + 2px) var(--mw-spacing-md)",
  lg: "calc(var(--mw-spacing-md)) var(--mw-spacing-lg)"
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", block = false, style, children, ...props },
  ref
) {
  const baseStyle: CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    borderRadius: "var(--mw-radius-md)",
    border: "1px solid transparent",
    cursor: props.disabled ? "not-allowed" : "pointer",
    fontFamily: "var(--mw-font-base)",
    fontWeight: "var(--mw-font-weight-semibold)",
    fontSize: "0.95rem",
    lineHeight: 1.1,
    minHeight: "42px",
    padding: sizeStyles[size],
    width: block ? "100%" : undefined,
    transition: "transform 120ms ease, box-shadow 180ms ease, background 180ms ease",
    boxShadow: "var(--mw-shadow-sm)",
    background: "var(--mw-color-primary)",
    color: "#FFFFFF"
  };

  if (variant === "secondary") {
    baseStyle.background = "var(--mw-surface-card)";
    baseStyle.color = "var(--mw-color-primary)";
    baseStyle.border = "1px solid var(--mw-border-subtle)";
    baseStyle.boxShadow = "none";
  }

  if (variant === "ghost") {
    baseStyle.background = "transparent";
    baseStyle.color = "var(--mw-color-primary)";
    baseStyle.border = "1px solid transparent";
    baseStyle.boxShadow = "none";
  }

  return (
    <button
      ref={ref}
      style={{
        ...baseStyle,
        ...style
      }}
      {...props}
      onMouseDown={(event) => {
        event.currentTarget.style.transform = "scale(0.985)";
        props.onMouseDown?.(event);
      }}
      onMouseUp={(event) => {
        event.currentTarget.style.transform = "scale(1)";
        props.onMouseUp?.(event);
      }}
      onMouseLeave={(event) => {
        event.currentTarget.style.transform = "scale(1)";
        props.onMouseLeave?.(event);
      }}
    >
      {children}
    </button>
  );
});
