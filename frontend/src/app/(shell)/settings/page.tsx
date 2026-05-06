"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-[#E5E7EB]">
        <h2 className="text-lg font-semibold text-[#111827]">设置</h2>
      </div>

      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-2xl space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>账户信息</CardTitle>
              <CardDescription>管理您的账户基本信息</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">用户名</Label>
                <Input id="name" placeholder="您的用户名" defaultValue="用户" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">邮箱</Label>
                <Input id="email" type="email" placeholder="user@example.com" />
              </div>
              <Button className="bg-[#4F46E5] hover:bg-[#4338CA] text-white">保存更改</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>API 配置</CardTitle>
              <CardDescription>配置 LLM API 密钥与模型参数</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="api-key">API Key</Label>
                <Input id="api-key" type="password" placeholder="sk-..." />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model">模型</Label>
                <Input id="model" placeholder="gpt-4" defaultValue="gpt-4" />
              </div>
              <Button className="bg-[#4F46E5] hover:bg-[#4338CA] text-white">保存配置</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>本地部署</CardTitle>
              <CardDescription>本地模式配置（离线优先）</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between py-2">
                <div>
                  <div className="font-medium text-[#111827]">离线模式</div>
                  <div className="text-sm text-[#6B7280]">禁用外部网络请求，数据不外传</div>
                </div>
                <Button variant="outline">配置</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
