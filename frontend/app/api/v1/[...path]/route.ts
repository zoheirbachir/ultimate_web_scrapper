import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

const BACKEND_URL = (process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

async function proxyRequest(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  const path = (resolvedParams.path || []).join("/");
  const url = new URL(request.url);
  const targetUrl = `${BACKEND_URL}/v1/${path}${url.search}`;

  // Get user session token from Supabase server client
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  const headers = new Headers(request.headers);
  headers.delete("host");
  if (token && !headers.get("authorization")) {
    headers.set("authorization", `Bearer ${token}`);
  }

  try {
    const init: RequestInit = {
      method: request.method,
      headers,
    };

    if (["POST", "PUT", "PATCH"].includes(request.method.toUpperCase())) {
      const bodyText = await request.text();
      if (bodyText) {
        init.body = bodyText;
      }
    }

    const backendRes = await fetch(targetUrl, init);
    const data = await backendRes.arrayBuffer();

    const resHeaders = new Headers(backendRes.headers);
    resHeaders.delete("content-encoding");
    resHeaders.delete("content-length");

    return new NextResponse(data, {
      status: backendRes.status,
      statusText: backendRes.statusText,
      headers: resHeaders,
    });
  } catch (err: any) {
    console.error("API Proxy Error:", err);
    return NextResponse.json(
      { detail: `Could not connect to backend server. Make sure START_PLATFORM.bat is running. (${err.message})` },
      { status: 502 }
    );
  }
}

export { proxyRequest as GET, proxyRequest as POST, proxyRequest as PUT, proxyRequest as PATCH, proxyRequest as DELETE };
