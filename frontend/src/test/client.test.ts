import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, request, setToken, setUnauthorizedHandler } from "../api/client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  setUnauthorizedHandler(null);
  setToken(null);
});

describe("api client", () => {
  it("attaches the Bearer token when authenticated", async () => {
    setToken("tok-123");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await request("/api/auth/me");

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>)["Authorization"]).toBe("Bearer tok-123");
  });

  it("omits the Authorization header when auth is false", async () => {
    setToken("tok-123");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ access_token: "x" }));
    vi.stubGlobal("fetch", fetchMock);

    await request("/api/auth/login", { method: "POST", body: {}, auth: false });

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>)["Authorization"]).toBeUndefined();
  });

  it("invokes the unauthorized handler and throws on 401", async () => {
    setToken("expired");
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "nope" }, 401)));

    await expect(request("/api/insights/today")).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("surfaces the FastAPI detail string on errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Email already registered" }, 409)),
    );

    await expect(request("/api/auth/register", { method: "POST", body: {} })).rejects.toThrow(
      "Email already registered",
    );
  });
});
