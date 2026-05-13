"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { BrainCircuit, Loader2, MailCheck } from "lucide-react";
import { GithubIcon } from "@/components/icons/GithubIcon";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { register, sendEmailVerificationCode } from "@/lib/api/auth";
import { useAuthStore } from "@/store/auth";

export default function RegisterPage() {
  const router = useRouter();
  const { login, setLoading, isLoading } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isSendingCode, setIsSendingCode] = useState(false);
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = window.setTimeout(() => setCountdown((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [countdown]);

  const validatePassword = (pwd: string): string | null => {
    if (pwd.length < 8) {
      return "密码长度不能小于8位";
    }
    return null;
  };

  const handleSendCode = async () => {
    setError("");
    setNotice("");

    if (!email) {
      setError("请先输入邮箱");
      return;
    }

    setIsSendingCode(true);
    try {
      const result = await sendEmailVerificationCode({ email, purpose: "register" });
      setCountdown(60);
      setNotice(`验证码已发送，请在 ${Math.floor(result.expires_in / 60)} 分钟内完成注册`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "验证码发送失败");
    } finally {
      setIsSendingCode(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email || !password || !confirmPassword || !verificationCode) {
      setError("请填写所有字段");
      return;
    }

    const passwordError = validatePassword(password);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    if (password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }

    setLoading(true);

    try {
      const result = await register({
        email,
        password,
        name: email.split("@")[0],
        verification_code: verificationCode,
      });
      localStorage.setItem("aisb_token", result.token);
      login(result.user);

      router.push("/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "注册失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const handleGithubRegister = () => {
    const clientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID;
    if (!clientId) {
      setError("GitHub 注册未配置");
      return;
    }
    const redirectUri = `${window.location.origin}/auth/github/callback`;
    const scope = "read:user user:email";
    const githubAuthUrl = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=${encodeURIComponent(scope)}`;
    window.location.href = githubAuthUrl;
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F9FAFB] px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-2 mb-8">
          <BrainCircuit className="h-8 w-8 text-[#4F46E5]" />
          <h1 className="text-2xl font-bold text-[#111827]">AI Second Brain</h1>
        </div>

        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-xl text-center">注册</CardTitle>
            <CardDescription className="text-center">
              创建您的新账户
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">邮箱</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="verificationCode">邮箱验证码</Label>
                <div className="flex gap-2">
                  <Input
                    id="verificationCode"
                    inputMode="numeric"
                    pattern="[0-9]{6}"
                    maxLength={6}
                    placeholder="6位数字验证码"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    disabled={isLoading}
                    required
                  />
                  <Button
                    type="button"
                    variant="outline"
                    className="shrink-0"
                    onClick={handleSendCode}
                    disabled={isLoading || isSendingCode || countdown > 0}
                  >
                    {isSendingCode ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : countdown > 0 ? (
                      `${countdown}s`
                    ) : (
                      <>
                        <MailCheck className="h-4 w-4 mr-2" />
                        发送
                      </>
                    )}
                  </Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">密码</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="至少8位字符"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  required
                />
                <p className="text-xs text-[#6B7280]">
                  密码长度不能小于8位
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">确认密码</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="再次输入密码"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isLoading}
                  required
                />
              </div>

              {error && (
                <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
                  {error}
                </p>
              )}
              {notice && (
                <p className="text-sm text-emerald-700 bg-emerald-50 px-3 py-2 rounded">
                  {notice}
                </p>
              )}

              <Button
                type="submit"
                className="w-full bg-[#4F46E5] hover:bg-[#4338CA] text-white"
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "注册"
                )}
              </Button>
            </form>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <Separator className="w-full" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-[#6B7280]">
                  或使用以下方式
                </span>
              </div>
            </div>

            <Button
              variant="outline"
              className="w-full"
              onClick={handleGithubRegister}
              disabled={isLoading}
            >
              <GithubIcon className="h-4 w-4 mr-2" />
              使用 GitHub 注册
            </Button>

            <p className="text-center text-sm text-[#6B7280]">
              已有账户？{" "}
              <Link
                href="/login"
                className="text-[#4F46E5] hover:underline font-medium"
              >
                立即登录
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
