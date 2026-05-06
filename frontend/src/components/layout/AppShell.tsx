"use client";

import { LeftNav } from "./LeftNav";
import { RightDrawer } from "./RightDrawer";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen w-full overflow-hidden">
      <LeftNav />
      <main className="flex-1 flex flex-col min-w-0 bg-white">
        {children}
      </main>
      <RightDrawer />
    </div>
  );
}
