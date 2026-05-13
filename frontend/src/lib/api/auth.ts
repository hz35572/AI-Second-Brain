import { User } from "@/store/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  name?: string;
  verification_code: string;
}

export interface EmailVerificationCodePayload {
  email: string;
  purpose: "register";
}

export interface AuthResponse {
  code: number;
  data: {
    token: string;
    expires_in: number;
    user: {
      id: string;
      email: string;
      name: string | null;
    };
  };
}

export async function login(credentials: LoginCredentials): Promise<{ token: string; user: User }> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || "登录失败");
  }

  const result: AuthResponse = await response.json();
  return {
    token: result.data.token,
    user: {
      id: result.data.user.id,
      email: result.data.user.email,
      name: result.data.user.name ?? undefined,
      provider: "local",
    },
  };
}

export async function register(credentials: RegisterCredentials): Promise<{ token: string; user: User }> {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || "注册失败");
  }

  const result: AuthResponse = await response.json();
  return {
    token: result.data.token,
    user: {
      id: result.data.user.id,
      email: result.data.user.email,
      name: result.data.user.name ?? undefined,
      provider: "local",
    },
  };
}

export async function sendEmailVerificationCode(payload: EmailVerificationCodePayload): Promise<{ expires_in: number }> {
  const response = await fetch(`${API_BASE}/auth/email-verification-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || "验证码发送失败");
  }

  const result: { data: { expires_in: number } } = await response.json();
  return { expires_in: result.data.expires_in };
}

export function getGithubAuthUrl(): string {
  // GitHub OAuth 登录 URL
  // 实际实现时需要配置 client_id 和 redirect_uri
  const clientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID;
  const redirectUri = `${window.location.origin}/api/v1/auth/github/callback`;
  const scope = "read:user user:email";

  if (!clientId) {
    console.warn("GitHub client ID not configured");
    return "#";
  }

  return `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=${encodeURIComponent(scope)}`;
}

export async function handleGithubCallback(code: string): Promise<{ token: string; user: User }> {
  const response = await fetch(`${API_BASE}/auth/github/callback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || "GitHub 登录失败");
  }

  const result: AuthResponse = await response.json();
  return {
    token: result.data.token,
    user: {
      id: result.data.user.id,
      email: result.data.user.email,
      name: result.data.user.name ?? undefined,
      provider: "github",
    },
  };
}
