import { NextRequest, NextResponse } from "next/server";
const BACKEND = process.env.HEAAP_API_URL || "http://127.0.0.1:8000";
function permitted(path: string, method: string) {
  if (method === "GET") return path === "api/dynamic-metadata/latest" || path === "api/business-metadata/catalog" || path === "health" || path === "registry/agents" || /^governance\/(status|history)\/[^/]+$/.test(path) || /^api\/assurance\/live\/(summary|trend|reports)$/.test(path) || /^api\/assurance\/live\/reports\/[0-9]+$/.test(path);
  if (method === "POST") return path === "api/supervisor-metadata/select" || path === "api/supervisor-metadata/validate" || path === "api/business-metadata/ask" || path === "api/business-metadata/bulk" || path === "api/dynamic-metadata/run" || /^assurance\/test\/[^/]+$/.test(path);
  return false;
}
async function proxy(request: NextRequest, context: {params: Promise<{path: string[]}>}) {
  const {path} = await context.params;
  const route = path.join("/");
  if (!permitted(route, request.method)) return NextResponse.json({error: "Route not allowed"}, {status: 403});
  try {
    const response = await fetch(`${BACKEND}/${route}`, {
    method: request.method,
    headers: request.method === "POST"
      ? { "Content-Type": "application/json" }
      : undefined,
    body: request.method === "POST"
      ? await request.text()
      : undefined,
    cache: "no-store",
    signal: AbortSignal.timeout(120000)
  });
    return new NextResponse(await response.text(), {status: response.status, headers: {"content-type": response.headers.get("content-type") || "application/json", "cache-control": "no-store"}});
  } catch(e) {return NextResponse.json({error: "Backend unavailable", detail: e instanceof Error ? e.message : "Unknown error"}, {status: 502});}
}
export const GET = proxy;
export const POST = proxy;

