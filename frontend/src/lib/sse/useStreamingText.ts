import { useEffect, useRef, useState, useCallback } from "react";

export function useStreamingText() {
  const [text, setText] = useState("");
  const bufferRef = useRef("");
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const loop = () => {
      setText(bufferRef.current);
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  const append = useCallback((chunk: string) => {
    bufferRef.current += chunk;
  }, []);

  const reset = useCallback(() => {
    bufferRef.current = "";
    setText("");
  }, []);

  return {
    text,
    append,
    reset,
  };
}
