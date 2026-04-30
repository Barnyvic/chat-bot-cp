'use client';

import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';

type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
};

export default function HomePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [usedTools, setUsedTools] = useState<string[]>([]);
  const [streamState, setStreamState] = useState<'idle' | 'streaming'>('idle');
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const sessionId = useMemo(() => crypto.randomUUID(), []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, streamState]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = input.trim();
    if (!message || isLoading) return;

    const userMessage: ChatMessage = { role: 'user', content: message };
    const history = [...messages, userMessage].map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, userMessage, { role: 'assistant', content: '' }]);
    setInput('');
    setIsLoading(true);
    setStreamState('streaming');
    setUsedTools([]);

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          user_message: message,
          chat_history: history.slice(0, -1),
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let done = false;

      while (!done) {
        const chunk = await reader.read();
        done = chunk.done;
        buffer += decoder.decode(chunk.value || new Uint8Array(), { stream: !done });

        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          const lines = part.split('\n');
          const eventLine = lines.find((line) => line.startsWith('event:'));
          const dataLine = lines.find((line) => line.startsWith('data:'));
          const eventType = eventLine?.replace('event:', '').trim();
          const payload = dataLine?.replace('data:', '').trim() || '';

          if (eventType === 'token') {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                last.content += payload;
              }
              return updated;
            });
          }

          if (eventType === 'tools' && payload) {
            setUsedTools(payload.split(',').map((item) => item.trim()).filter(Boolean));
          }

          if (eventType === 'error') {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                last.content = `Error: ${payload}`;
              }
              return updated;
            });
          }
        }
      }
    } catch (error) {
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last?.role === 'assistant') {
          last.content = `Connection error: ${(error as Error).message}`;
        }
        return updated;
      });
    } finally {
      setIsLoading(false);
      setStreamState('idle');
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-4 py-6">
      <section className="mb-4 rounded-2xl border border-slate-700/50 bg-slate-900/60 p-4 shadow-2xl">
        <h1 className="text-xl font-semibold text-slate-100">Meridian Electronics Support</h1>
        <p className="mt-1 text-sm text-slate-300">
          AI support assistant powered by Groq + MCP tools for product, order, and account workflows.
        </p>
      </section>

      <section className="mb-4 flex-1 space-y-3 overflow-y-auto rounded-2xl border border-slate-700/50 bg-slate-900/40 p-4">
        {messages.length === 0 ? (
          <p className="text-sm text-slate-400">Start by asking about product availability or order history.</p>
        ) : null}
        {messages.map((msg, index) => (
          <div
            key={`${msg.role}-${index}`}
            className={`rounded-xl px-4 py-3 text-sm ${
              msg.role === 'user'
                ? 'ml-auto max-w-[80%] bg-indigo-500/25 text-indigo-100'
                : 'mr-auto max-w-[90%] bg-slate-800/80 text-slate-100'
            }`}
          >
            {msg.content || (isLoading && index === messages.length - 1 ? 'Thinking...' : '')}
          </div>
        ))}
        {isLoading && streamState === 'streaming' ? (
          <div className="mr-auto max-w-[90%] rounded-xl bg-slate-800/80 px-4 py-2 text-xs text-slate-300">
            Assistant is typing...
          </div>
        ) : null}
        <div ref={messagesEndRef} />
      </section>

      {usedTools.length > 0 ? (
        <div className="mb-3 text-xs text-cyan-300">Tools used: {usedTools.join(', ')}</div>
      ) : null}

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          className="flex-1 rounded-xl border border-slate-600 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none ring-indigo-500 focus:ring"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask about availability, orders, or account lookup..."
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-xl bg-indigo-500 px-4 py-3 text-sm font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-slate-600"
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </main>
  );
}
