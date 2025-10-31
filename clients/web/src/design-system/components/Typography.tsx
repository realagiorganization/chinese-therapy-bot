import { ElementType, ReactNode } from "react";

type TypographyVariant = "display" | "title" | "subtitle" | "body" | "caption" | "overline";

export type TypographyProps<T extends ElementType> = {
  as?: T;
  variant?: TypographyVariant;
  children: ReactNode;
  align?: "left" | "center" | "right";
} & Omit<React.ComponentPropsWithoutRef<T>, "as" | "children">;

const defaults: Record<TypographyVariant, { fontSize: string; fontWeight: string; letterSpacing?: string }> = {
  display: { fontSize: "2.4rem", fontWeight: "var(--mw-font-weight-bold)" },
  title: { fontSize: "1.75rem", fontWeight: "var(--mw-font-weight-semibold)" },
  subtitle: { fontSize: "1.25rem", fontWeight: "var(--mw-font-weight-medium)" },
  body: { fontSize: "1rem", fontWeight: "var(--mw-font-weight-regular)" },
  caption: { fontSize: "0.85rem", fontWeight: "var(--mw-font-weight-medium)" },
  overline: { fontSize: "0.7rem", fontWeight: "var(--mw-font-weight-medium)", letterSpacing: "0.08em" }
};

export function Typography<T extends ElementType = "p">({
  as,
  variant = "body",
  align = "left",
  children,
  style,
  ...props
}: TypographyProps<T>) {
  const Component = (as || "p") as ElementType;
  const variantStyle = defaults[variant] ?? defaults.body;
  return (
    <Component
      style={{
        margin: "0",
        fontFamily:
          variant === "display" || variant === "title"
            ? "var(--mw-font-heading)"
            : "var(--mw-font-base)",
        color: "var(--text-primary)",
        textAlign: align,
        ...variantStyle,
        ...style
      }}
      {...props}
    >
      {children}
    </Component>
  );
}
