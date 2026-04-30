'use client';

import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';

type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
};

function formatAssistantContent(content: string): string {
  const trimmed = content.trim();
  if (!trimmed) return trimmed;

  // If the model returns many catalog items in one dense line, render them as bullets.
  const entries = trimmed.match(/[A-Za-z0-9' ]+ - Model [A-E]/g);
  if (entries && entries.length >= 8) {
    const firstEntry = entries[0];
    const firstIndex = trimmed.indexOf(firstEntry);
    const intro = firstIndex > 0 ? trimmed.slice(0, firstIndex).trim() : '';

    const lastEntry = entries[entries.length - 1];
    const lastStart = trimmed.lastIndexOf(lastEntry);
    const afterLast = lastStart + lastEntry.length;
    const outro = afterLast < trimmed.length ? trimmed.slice(afterLast).trim() : '';

    return [
      intro,
      entries.map((entry) => `- ${entry.trim()}`).join('\n'),
      outro,
    ]
      .filter(Boolean)
      .join('\n\n');
  }

  return trimmed;
}

export default function HomePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
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
          const payload = dataLine
            ? dataLine.startsWith('data: ')
              ? dataLine.slice(6)
              : dataLine.slice(5)
            : '';

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
        <p className="mt-1 text-sm text-slate-300">AI support assistant</p>
      </section>

      <section className="mb-4 flex-1 space-y-3 overflow-x-hidden overflow-y-auto rounded-2xl border border-slate-700/50 bg-slate-900/40 p-4">
        {messages.length === 0 ? (
          <p className="text-sm text-slate-400">Start by asking about product availability or order history.</p>
        ) : null}
        {messages.map((msg, index) => (
          <div
            key={`${msg.role}-${index}`}
            className={`w-fit rounded-xl px-4 py-3.5 text-[15px] leading-7 ${
              msg.role === 'user'
                ? 'ml-auto max-w-[80%] bg-indigo-500/25 text-indigo-100'
                : 'mr-auto max-w-[90%] bg-slate-800/80 text-slate-100'
            }`}
          >
            <p className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">
              {msg.role === 'assistant'
                ? formatAssistantContent(msg.content)
                : msg.content}
            </p>
          </div>
        ))}
        {isLoading && streamState === 'streaming' ? (
          <div className="mr-auto max-w-[90%] rounded-xl bg-slate-800/80 px-4 py-2 text-xs text-slate-300">
            Thinking...
          </div>
        ) : null}
        <div ref={messagesEndRef} />
      </section>

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
          Send
        </button>
      </form>
    </main>
  );
}
