const configuredApiBase = process.env.NEXT_PUBLIC_API_BASE?.trim();

export const API_BASE = configuredApiBase || "/api/v1";
