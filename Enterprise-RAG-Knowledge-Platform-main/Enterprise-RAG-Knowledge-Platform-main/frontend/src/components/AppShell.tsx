import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen bg-background text-foreground font-body">
      <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col border-r border-border/60 bg-card/40 p-5 backdrop-blur">
        <Link to="/chat" className="mb-8 flex items-center gap-2 font-display font-semibold">
          <Logo />
          <div className="leading-tight">
            <div className="text-sm">Enterprise RAG</div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Knowledge Platform</div>
          </div>
        </Link>

        <nav className="flex flex-col gap-1">
          <NavItem to="/chat">Chat</NavItem>
          <NavItem to="/documents">Documents</NavItem>
        </nav>

        <div className="mt-auto space-y-3 border-t border-border/60 pt-4 text-xs">
          <div className="truncate text-muted-foreground">{user?.email}</div>
          <button
            onClick={logout}
            className="w-full rounded-md border border-border/60 px-3 py-2 text-left transition hover:bg-muted/40"
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-x-hidden">{children}</main>
    </div>
  );
}

function NavItem({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `rounded-md px-3 py-2 text-sm transition ${
          isActive
            ? "bg-primary/15 text-primary"
            : "text-muted-foreground hover:bg-muted/40 hover:text-foreground"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

export function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32">
      <defs>
        <linearGradient id="lgm" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stopColor="#00f0ff" />
          <stop offset="0.5" stopColor="#7a5cff" />
          <stop offset="1" stopColor="#ff2fd0" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="14" fill="none" stroke="url(#lgm)" strokeWidth="1.5" />
      <circle cx="16" cy="16" r="6" fill="url(#lgm)" opacity="0.9" />
    </svg>
  );
}
