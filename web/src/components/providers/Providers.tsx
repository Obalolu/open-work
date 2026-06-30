"use client";

import { useState } from "react";
import { ThemeProvider as NextThemesProvider, type ThemeProviderProps } from "next-themes";
import { MotionConfig } from "framer-motion";
import { Toaster } from "@/components/ui/Toaster";
import { TooltipProvider } from "@/components/ui/Tooltip";
import { CommandPalette } from "@/components/command/CommandPalette";
import { ShortcutHelp } from "@/components/command/ShortcutHelp";
import { useGlobalShortcuts } from "@/hooks/useGlobalShortcuts";

function ShortcutsRoot({ children }: { children: React.ReactNode }) {
  const [helpOpen, setHelpOpen] = useState(false);
  useGlobalShortcuts({ onShowHelp: () => setHelpOpen(true) });
  return (
    <>
      {children}
      <ShortcutHelp open={helpOpen} onOpenChange={setHelpOpen} />
    </>
  );
}

export function Providers({ children, ...props }: ThemeProviderProps) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
      {...props}
    >
      <MotionConfig
        reducedMotion="user"
        transition={{ type: "spring", stiffness: 380, damping: 32, mass: 0.8 }}
      >
        <TooltipProvider delayDuration={250}>
          <ShortcutsRoot>
            {children}
            <CommandPalette />
            <Toaster />
          </ShortcutsRoot>
        </TooltipProvider>
      </MotionConfig>
    </NextThemesProvider>
  );
}
