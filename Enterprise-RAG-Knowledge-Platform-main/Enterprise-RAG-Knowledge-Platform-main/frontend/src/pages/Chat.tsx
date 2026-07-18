import { FormEvent, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "../components/AppShell";
import { chatApi, ChatMessage } from "../api/endpoints";

export default function Chat() {
  const queryClient = useQueryClient();
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: history } = useQuery({
    queryKey: ["chat-history"],
    queryFn: () => chatApi.history().then((r) => r.data),
  });

  const { data: activeChat } = useQuery({
    queryKey: ["chat", activeChatId],
    queryFn: () => chatApi.getChat(activeChatId as string).then((r) => r.data),
    enabled: !!activeChatId,
  });

  useEffect(() => {
    if (activeChat) setMessages(activeChat.messages);
  }, [activeChat]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const askMutation = useMutation({
    mutationFn: (message: string) => chatApi.ask(message, activeChatId ?? undefined),
    onSuccess: (res) => {
      setActiveChatId(res.data.chat_id);
      setMessages((prev) => [...prev, res.data.message]);
      queryClient.invalidateQueries({ queryKey: ["chat-history"] });
    },
    onError: (e: any) => setErr(e.message ?? "Something went wrong"),
  });

  function newChat() {
    // No backend call here on purpose: the API only creates a chat once the
    // first message is sent (see `askMutation`), so "New chat" just clears
    // local state back to the empty/pre-chat view.
    setActiveChatId(null);
    setMessages([]);
    setErr(null);
  }

  function send(e: FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    setErr(null);

    const userMsg: ChatMessage = {
      id: `local-${Date.now()}`,
      role: "user",
      content: input,
      citations: null,
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, userMsg]);
    const content = input;
    setInput("");
    askMutation.mutate(content);
  }

  return (
    <AppShell>
      <ChatBody
        history={history}
        activeChatId={activeChatId}
        messages={messages}
        input={input}
        setInput={setInput}
        err={err}
        sending={askMutation.isPending}
        scrollRef={scrollRef}
        onSelectChat={setActiveChatId}
        onNewChat={newChat}
        onSend={send}
      />
    </AppShell>
  );
}

function ChatBody({
  history,
  activeChatId,
  messages,
  input,
  setInput,
  err,
  sending,
  scrollRef,
  onSelectChat,
  onNewChat,
  onSend,
}: {
  history?: { id: string; title: string }[];
  activeChatId: string | null;
  messages: ChatMessage[];
  input: string;
  setInput: (v: string) => void;
  err: string | null;
  sending: boolean;
  scrollRef: React.RefObject<HTMLDivElement>;
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
  onSend: (e: FormEvent) => void;
}) {
  return (
    <div className="flex h-screen">
      <div className="hidden w-64 shrink-0 flex-col border-r border-border/60 bg-card/20 p-4 md:flex">
        <button onClick={onNewChat} className="btn-primary mb-3 w-full text-sm">
          + New chat
        </button>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {(!history || history.length === 0) && (
            <div className="p-2 text-xs text-muted-foreground">No conversations yet.</div>
          )}
          {history?.map((c) => (
            <button
              key={c.id}
              onClick={() => onSelectChat(c.id)}
              className={`block w-full truncate rounded-md px-3 py-2 text-left text-sm transition ${
                activeChatId === c.id
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:bg-muted/40 hover:text-foreground"
              }`}
            >
              {c.title || "Untitled"}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border/60 px-6 py-4">
          <div>
            <h1 className="font-display text-lg font-semibold">
              {history?.find((c) => c.id === activeChatId)?.title || "New conversation"}
            </h1>
            <div className="text-xs text-muted-foreground">Hybrid retrieval · Reranked · Cited</div>
          </div>
          <button onClick={onNewChat} className="rounded-md border border-border/60 px-3 py-1.5 text-xs md:hidden">
            + New
          </button>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <div className="mx-auto max-w-3xl space-y-6">
            {messages.length === 0 && (
              <div className="rounded-2xl border border-dashed border-border/60 p-8 text-center">
                <div className="font-display text-xl">Ask anything about your documents.</div>
                <div className="mt-2 text-sm text-muted-foreground">
                  Upload files in <a href="/documents" className="text-primary">Documents</a>, then ask questions
                  here. Answers are grounded with citations back to source.
                </div>
              </div>
            )}
            {messages.map((m) => (
              <Bubble key={m.id} message={m} />
            ))}
            {sending && (
              <Bubble message={{ id: "pending", role: "assistant", content: "…thinking", citations: null, created_at: "" }} />
            )}
          </div>
        </div>

        <form onSubmit={onSend} className="border-t border-border/60 bg-background/60 px-4 py-4 md:px-8">
          {err && (
            <div className="mx-auto mb-2 max-w-3xl rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
              {err}
            </div>
          )}
          <div className="mx-auto flex max-w-3xl items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSend(e as unknown as FormEvent);
                }
              }}
              rows={1}
              placeholder="Ask a question about your documents…"
              className="input min-h-[52px] flex-1 resize-none py-3"
            />
            <button type="submit" disabled={sending || !input.trim()} className="btn-primary h-[52px] px-6">
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Bubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser ? "bg-primary text-primary-foreground" : "border border-border/60 bg-card/60 text-foreground"
        }`}
      >
        <div className="whitespace-pre-wrap">{message.content}</div>
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 border-t border-border/40 pt-2 text-xs text-muted-foreground">
            <div className="mb-1 font-medium uppercase tracking-wider">Sources</div>
            <ul className="space-y-0.5">
              {message.citations.map((c) => (
                <li key={c.chunk_id}>
                  • {c.document_name}
                  {c.page_number ? `, p.${c.page_number}` : ""}
                  <span className="text-muted-foreground/70"> ({c.score.toFixed(2)})</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
