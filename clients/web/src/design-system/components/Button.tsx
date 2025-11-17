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
    border: "1px solid rgba(44, 45, 41, 0.32)",
    cursor: props.disabled ? "not-allowed" : "pointer",
    fontFamily: "var(--mw-font-base)",
    fontWeight: "var(--mw-font-weight-semibold)",
    fontSize: "0.95rem",
    lineHeight: 1.1,
    minHeight: "42px",
    padding: sizeStyles[size],
    width: block ? "100%" : undefined,
    transition: "box-shadow 180ms ease, background 180ms ease, color 150ms ease",
    boxShadow: "none",
    background: "var(--mw-color-primary)",
    color: "#FDFBF7"
  };

  if (variant === "secondary") {
    baseStyle.background = "transparent";
    baseStyle.color = "var(--text-primary)";
    baseStyle.border = "1px solid rgba(44, 45, 41, 0.4)";
  }

  if (variant === "ghost") {
    baseStyle.background = "transparent";
    baseStyle.color = "var(--mw-color-primary)";
    baseStyle.border = "1px solid rgba(44, 45, 41, 0.25)";
  }

  return (
    <button
      ref={ref}
      style={{
        ...baseStyle,
        ...style
      }}
      {...props}
    >
      {children}
    </button>
  );
});
