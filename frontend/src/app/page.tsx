"use client";

import { useState, useRef, useEffect } from "react";

type Message = { role: "user" | "assistant"; content: string };

const THREAD_ID =
  typeof crypto !== "undefined"
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

function CooperAvatar({ size = 36 }: { size?: number }) {
  return (
    <div className="flex-shrink-0">
      <svg viewBox="0 0 20 20" width={size} height={size} xmlns="http://www.w3.org/2000/svg">
        {/* Circle background */}
        <circle cx="10" cy="10" r="10" fill="#606060" />
        {/* Antenna */}
        <rect x="9" y="1" width="2" height="2" fill="#FF8C00" />
        <rect x="9.5" y="3" width="1" height="2" fill="#2a5a5b" />
        {/* Face plate */}
        <rect x="3.5" y="5" width="13" height="11" rx="1.5" fill="#4dbec2" />
        {/* Ear accents */}
        <rect x="1.5" y="8.5" width="2" height="3" fill="#FF8C00" />
        <rect x="16.5" y="8.5" width="2" height="3" fill="#FF8C00" />
        {/* Eyes */}
        <rect x="5.5" y="7.5" width="3" height="2.5" fill="#111111" />
        <rect x="11.5" y="7.5" width="3" height="2.5" fill="#111111" />
        {/* Mouth */}
        <rect x="7" y="13" width="6" height="1" fill="#111111" />
      </svg>
    </div>
  );
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, thread_id: THREAD_ID }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply ?? data.error ?? "No response." },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Is the backend running?" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-[#121212]">
      <header className="bg-[#2a2a2a] px-6 py-4">
        <div className="flex items-center gap-3">
          <svg viewBox="0 0 36 36" width="36" height="36" xmlns="http://www.w3.org/2000/svg">
            <path d="M18 2 L36 16 L31 16 L31 34 L5 34 L5 16 L0 16 Z" fill="#E8981A" />
            <text x="18" y="29" textAnchor="middle" fill="white" fontWeight="bold" fontSize="15" fontFamily="Arial, sans-serif">P</text>
          </svg>
          <div>
            <div className="text-white text-xl font-bold leading-none">PartSelect</div>
            <div className="bg-[#265A5B] text-white text-[10px] font-medium px-1.5 py-0.5 mt-1 inline-block">
              Here to help since 1999
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5">
        {messages.length === 0 && (
          <div className="flex flex-col items-center mt-20 gap-4">
            <CooperAvatar size={96} />
            <p className="text-[#E8981A] font-bold text-2xl">Cooper</p>
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="bg-[#2a2a2a] text-[#f0f0f0] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap max-w-xl">
                {m.content}
              </div>
            </div>
          ) : (
            <div key={i} className="flex flex-col gap-2 max-w-2xl">
              <div className="flex items-center gap-2.5 pl-4">
                <CooperAvatar />
                <span className="text-[#E8981A] font-bold text-sm">Cooper</span>
              </div>
              <p className="text-[#cccccc] text-sm whitespace-pre-wrap leading-relaxed">
                {m.content}
              </p>
            </div>
          )
        )}
        {loading && (
          <div className="flex flex-col gap-2 max-w-2xl">
            <div className="flex items-center gap-2.5">
              <CooperAvatar />
              <span className="text-[#E8981A] font-bold text-sm">Cooper</span>
            </div>
            <span className="inline-flex gap-1 pl-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#E8981A] animate-bounce [animation-delay:0ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-[#E8981A] animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-[#E8981A] animate-bounce [animation-delay:300ms]" />
            </span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="px-4 py-4">
        <div className="max-w-3xl mx-auto">
          <input
            className="w-full rounded-full border border-[#333333] bg-[#1e1e1e] px-4 py-2.5 text-sm text-[#f0f0f0] placeholder:text-[#555555] focus:outline-none focus:ring-2 focus:ring-[#265A5B]"
            placeholder="Reply to Cooper..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={loading}
          />
        </div>
      </div>
    </div>
  );
}
