const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("aisb_token");
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  const url = `${API_BASE}${path}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `Request failed: ${res.status}`);
  }

  const data = await res.json();
  return data as T;
}

export function apiEventSource(
  path: string,
  options: { body?: unknown; onMessage?: (data: unknown) => void; onError?: (err: Error) => void; onDone?: () => void } = {}
): { close: () => void } {
  const token = getAuthToken();
  const url = `${API_BASE}${path}`;

  const abortController = new AbortController();

  fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: abortController.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) {
        throw new Error(`SSE request failed: ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;
          const jsonStr = trimmed.slice(5).trim();
          if (jsonStr === "[DONE]") {
            options.onDone?.();
            return;
          }
          try {
            const parsed = JSON.parse(jsonStr);
            options.onMessage?.(parsed);
          } catch {
            // ignore parse errors
          }
        }
      }
      options.onDone?.();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        options.onError?.(err);
      }
    });

  return {
    close: () => abortController.abort(),
  };
}
