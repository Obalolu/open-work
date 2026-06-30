"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

export interface EmptyProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  variant?: "default" | "bordered";
}

export function Empty({
  icon,
  title,
  description,
  action,
  variant = "default",
  className,
  children,
  ...props
}: EmptyProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg p-8 text-center md:p-12",
        variant === "bordered" && "border border-dashed border-border bg-surface",
        className
      )}
      {...props}
    >
      {icon && (
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </div>
      )}
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          {description}
        </p>
      )}
      {action && <div className="mt-6">{action}</div>}
      {children}
    </div>
  );
}
