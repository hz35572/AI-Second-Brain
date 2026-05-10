"use client";

import { Suspense } from "react";
import { useRouter } from "next/navigation";
import { GithubCallbackContent } from "./GithubCallbackContent";

export default function GithubCallbackPage() {
  return (
    <Suspense fallback={<GithubCallbackFallback />}>
      <GithubCallbackContent />
    </Suspense>
  );
}

function GithubCallbackFallback() {
  const router = useRouter();
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F9FAFB]">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#4F46E5] mx-auto mb-4" />
        <p className="text-[#6B7280]">正在处理 GitHub 登录...</p>
        <button
          onClick={() => router.push("/login")}
          className="mt-4 text-[#4F46E5] hover:underline"
        >
          返回登录页面
        </button>
      </div>
    </div>
  );
}
