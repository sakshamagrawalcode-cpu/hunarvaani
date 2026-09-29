import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";

import type { Summary } from "./api";
import { useApi } from "./api";
import CallDetail from "./pages/CallDetail";
import Calls from "./pages/Calls";
import Occupations from "./pages/Occupations";
import Overview from "./pages/Overview";
import People from "./pages/People";

const ICON: Record<string, string> = {
  overview: "M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z",
  calls:
    "M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.6 21 3 13.4 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1L6.6 10.8z",
  people:
    "M16 11c1.7 0 3-1.3 3-3s-1.3-3-3-3-3 1.3-3 3 1.3 3 3 3zm-8 0c1.7 0 3-1.3 3-3S9.7 5 8 5 5 6.3 5 8s1.3 3 3 3zm0 2c-2.3 0-7 1.2-7 3.5V19h14v-2.5C15 14.2 10.3 13 8 13zm8 0c-.3 0-.6 0-1 .1 1.2.8 2 2 2 3.4V19h6v-2.5c0-2.3-4.7-3.5-7-3.5z",
  occupations:
    "M20 6h-4V4c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v11c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-6 0h-4V4h4v2z",
};

const NAV = [
  { to: "/", label: "Overview", icon: "overview", end: true },
  { to: "/calls", label: "Calls", icon: "calls", end: false },
  { to: "/people", label: "People", icon: "people", end: false },
  { to: "/occupations", label: "Occupations", icon: "occupations", end: false },
];

const TITLES: [RegExp, string, string][] = [
  [/^\/calls\/.+/, "Call details", "live conversation, background processing and problems"],
  [/^\/calls/, "Calls", "every call, newest first"],
  [/^\/people/, "People", "one row per caller with their latest answers"],
  [/^\/occupations/, "Occupations", "the occupations a call can recognise"],
  [/.*/, "Overview", "what is happening across all calls"],
];

function Icon({ name }: { name: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0 fill-current" aria-hidden>
      <path d={ICON[name]} />
    </svg>
  );
}

function LiveIndicator() {
  const { data } = useApi<Summary>("/summary", 3000);
  const live = data?.live_now ?? [];
  if (!live.length) {
    return <div className="px-3 text-xs text-slate-500">No live calls</div>;
  }
  return (
    <Link
      to={`/calls/${live[0].id}`}
      className="mx-2 flex items-center gap-2 rounded-lg bg-rose-500/15 px-3 py-2 text-sm font-medium text-rose-300 hover:bg-rose-500/25"
    >
      <span className="relative flex h-2.5 w-2.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-400 opacity-75" />
        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-rose-500" />
      </span>
      {live.length} live call{live.length > 1 ? "s" : ""} · watch
    </Link>
  );
}

export default function App() {
  const { pathname } = useLocation();
  const [, title, subtitle] = TITLES.find(([re]) => re.test(pathname)) ?? TITLES[TITLES.length - 1];
  return (
    <div className="min-h-screen lg:flex">
      <aside className="bg-slate-900 text-slate-300 lg:fixed lg:inset-y-0 lg:flex lg:w-60 lg:flex-col">
        <div className="flex items-center gap-3 px-5 py-4 lg:py-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-500 text-sm font-bold text-white">
            HV
          </div>
          <div>
            <div className="font-semibold text-white">HunarVaani</div>
            <div className="text-xs text-slate-400">हुनरवाणी · team console</div>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-2 pb-2 lg:flex-col lg:overflow-visible lg:pb-0">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `flex items-center gap-3 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-slate-800 text-white" : "hover:bg-slate-800/60 hover:text-white"
                }`
              }
            >
              <Icon name={n.icon} />
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden lg:mt-6 lg:block">
          <LiveIndicator />
        </div>
        <div className="mt-auto hidden px-5 py-4 text-xs leading-relaxed text-slate-500 lg:block">
          Numbers show only their last four digits. Pages refresh by themselves.
        </div>
      </aside>
      <div className="min-w-0 flex-1 lg:pl-60">
        <header className="border-b border-slate-200 bg-white px-4 py-4 sm:px-6 dark:border-slate-800 dark:bg-slate-900">
          <h1 className="text-xl font-semibold">{title}</h1>
          <p className="text-sm text-slate-500">{subtitle}</p>
        </header>
        <main className="px-4 py-6 sm:px-6">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/calls" element={<Calls />} />
            <Route path="/calls/:id" element={<CallDetail />} />
            <Route path="/people" element={<People />} />
            <Route path="/occupations" element={<Occupations />} />
            <Route path="*" element={<Overview />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
