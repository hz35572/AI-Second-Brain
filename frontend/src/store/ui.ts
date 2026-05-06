import { create } from "zustand";

export type Scope =
  | { type: "global" }
  | { type: "folder"; ids: string[] }
  | { type: "file"; ids: string[] };

export type PreviewTarget =
  | { kind: "pdf"; fileId: string; page: number; start: number; end: number }
  | { kind: "markdown"; fileId: string; anchorText?: string }
  | { kind: "excel"; fileId: string; sheet: string; rowStart: number; rowEnd: number; colStart: number; colEnd: number };

interface UIState {
  scope: Scope;
  setScope: (scope: Scope) => void;
  drawerOpen: boolean;
  previewTarget: PreviewTarget | null;
  openDrawer: (target: PreviewTarget) => void;
  closeDrawer: () => void;
  leftNavCollapsed: boolean;
  toggleLeftNav: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  scope: { type: "global" },
  setScope: (scope) => set({ scope }),
  drawerOpen: false,
  previewTarget: null,
  openDrawer: (target) => set({ drawerOpen: true, previewTarget: target }),
  closeDrawer: () => set({ drawerOpen: false, previewTarget: null }),
  leftNavCollapsed: false,
  toggleLeftNav: () => set((state) => ({ leftNavCollapsed: !state.leftNavCollapsed })),
}));
