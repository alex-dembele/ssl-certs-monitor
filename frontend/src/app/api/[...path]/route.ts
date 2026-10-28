import { NextRequest } from "next/server";

// Lu à chaque requête : l'URL du backend se configure au déploiement, pas au build.
export const dynamic = "force-dynamic";

const STRIPPED_REQUEST_HEADERS = ["connection", "content-length", "host", "keep-alive", "transfer-encoding"];
const STRIPPED_RESPONSE_HEADERS = ["content-encoding", "content-length", "transfer-encoding"];

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, { params }: Context) {
  const backendUrl = (process.env.BACKEND_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
  const { path } = await params;
  const target = new URL(`${backendUrl}/api/${path.map(encodeURIComponent).join("/")}`);
  target.search = request.nextUrl.search;

  const headers = new Headers(request.headers);
  STRIPPED_REQUEST_HEADERS.forEach((name) => headers.delete(name));
  const token = process.env.BACKEND_API_TOKEN;
  if (token) {
    headers.set("authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return Response.json({ detail: "Le backend est injoignable." }, { status: 502 });
  }

  const responseHeaders = new Headers(response.headers);
  STRIPPED_RESPONSE_HEADERS.forEach((name) => responseHeaders.delete(name));
  return new Response(response.body, { status: response.status, headers: responseHeaders });
}

export { forward as DELETE, forward as GET, forward as POST, forward as PUT };
