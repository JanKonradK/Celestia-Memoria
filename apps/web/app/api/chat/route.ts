import { auth } from "@/lib/auth";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

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

  const accessToken = (session as any).accessToken || "";

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
          intent: "",
          requires_rag: false,
          query_rewrite: "",
          retrieved_chunks: [],
          reranked_chunks: [],
          final_response: "",
          sources: [],
          node_trace: [],
          model_slug,
          aerodrome_icao,
        },
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: `Backend error: ${errorText}` },
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
              if (line.startsWith("data: ")) {
                const data = line.slice(6).trim();
                if (data === "[DONE]") continue;

                try {
                  const parsed = JSON.parse(data);
                  // Extract the text content from LangServe stream events
                  if (parsed.ops) {
                    for (const op of parsed.ops) {
                      if (
                        op.path === "/final_response" &&
                        op.op === "replace"
                      ) {
                        const text = op.value || "";
                        controller.enqueue(
                          encoder.encode(`0:${JSON.stringify(text)}\n`)
                        );
                      }
                    }
                  }
                } catch {
                  // Skip unparseable lines
                }
              }
            }
          }
        } catch (err) {
          console.error("Stream error:", err);
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
