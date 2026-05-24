"use client";

import { LeftNav } from "./LeftNav";
import { RightDrawer } from "./RightDrawer";
import { useUIStore } from "@/store/ui";
import { cn } from "@/lib/utils";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const { drawerOpen } = useUIStore();

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#FBFCFF] text-[#111827]">
      <LeftNav />
      <main
        className={cn(
          "flex min-w-0 flex-1 flex-col transition-all duration-300",
          drawerOpen && "lg:mr-0"
        )}
      >
        {children}
      </main>
      <RightDrawer />
    </div>
  );
}
