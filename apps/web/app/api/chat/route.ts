import { auth } from "@/lib/auth";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const MAX_MESSAGE_LENGTH = 10_000;

export async function POST(request: NextRequest) {
  const session = await auth();

  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { messages, aerodrome_icao = "GLOBAL", model_slug = "default" } = body;

  const lastMessage = messages?.[messages.length - 1];
  if (!lastMessage?.content) {
    return NextResponse.json({ error: "No message content" }, { status: 400 });
  }

  if (
    typeof lastMessage.content !== "string" ||
    lastMessage.content.length > MAX_MESSAGE_LENGTH
  ) {
    return NextResponse.json(
      { error: `Message must be a string of at most ${MAX_MESSAGE_LENGTH} characters` },
      { status: 400 }
    );
  }

  const accessToken = session.accessToken ?? "";

  try {
    const response = await fetch(`${BACKEND_URL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        input: {
          messages: [
            {
              type: "human",
              content: lastMessage.content,
            },
          ],
          // Router node computes these — provide empty defaults for LangServe schema
          intent: "",
          requires_rag: false,
          query_rewrite: "",
          retrieved_chunks: [],
          reranked_chunks: [],
          final_response: "",
          sources: [],
          node_trace: [],
          // Client-controlled fields
          model_slug,
          aerodrome_icao,
        },
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Backend error:", response.status, errorText);
      return NextResponse.json(
        { error: "Failed to get response from AI backend" },
        { status: response.status }
      );
    }

    // Stream the response back to the client
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        const reader = response.body?.getReader();
        if (!reader) {
          controller.close();
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (!line.startsWith("data: ")) continue;

              const data = line.slice(6).trim();
              if (data === "[DONE]") continue;

              try {
                const parsed = JSON.parse(data);
                if (!parsed.ops || !Array.isArray(parsed.ops)) continue;

                for (const op of parsed.ops) {
                  if (
                    op.path === "/final_response" &&
                    op.op === "replace" &&
                    typeof op.value === "string"
                  ) {
                    controller.enqueue(
                      encoder.encode(`0:${JSON.stringify(op.value)}\n`)
                    );
                  }
                  if (
                    op.path === "/sources" &&
                    op.op === "replace" &&
                    Array.isArray(op.value)
                  ) {
                    controller.enqueue(
                      encoder.encode(
                        `8:${JSON.stringify([{ sources: op.value }])}\n`
                      )
                    );
                  }
                }
              } catch {
                // Skip unparseable SSE lines — non-JSON keep-alive or malformed events
                console.warn("Skipping unparseable SSE line:", data.slice(0, 100));
              }
            }
          }
        } catch (err) {
          console.error("Stream processing error:", err);
        } finally {
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    console.error("Chat proxy error:", error);
    return NextResponse.json(
      { error: "Failed to connect to backend" },
      { status: 502 }
    );
  }
}
