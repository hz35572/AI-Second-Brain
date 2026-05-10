"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { handleGithubCallback } from "@/lib/api/auth";

export function GithubCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuthStore();
  const [error, setError] = useState("");
  const processedRef = useRef(false);
  const [, startTransition] = useTransition();

  useEffect(() => {
    if (processedRef.current) return;

    const code = searchParams.get("code");

    if (!code) {
      startTransition(() => {
        setError("授权失败：未获取到授权码");
      });
      return;
    }

    processedRef.current = true;

    handleGithubCallback(code)
      .then(({ token, user }) => {
        login(user);
        localStorage.setItem("token", token);
        router.push("/chat");
      })
      .catch((err) => {
        startTransition(() => {
          setError(err instanceof Error ? err.message : "GitHub 登录失败");
        });
      });
  }, [searchParams, login, router, startTransition]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F9FAFB]">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={() => router.push("/login")}
            className="text-[#4F46E5] hover:underline"
          >
            返回登录页面
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F9FAFB]">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#4F46E5] mx-auto mb-4" />
        <p className="text-[#6B7280]">正在处理 GitHub 登录...</p>
      </div>
    </div>
  );
}
