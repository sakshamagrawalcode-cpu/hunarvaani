import { NavLink, Route, Routes } from "react-router-dom";

import CallDetail from "./pages/CallDetail";
import Calls from "./pages/Calls";
import Occupations from "./pages/Occupations";
import Overview from "./pages/Overview";
import People from "./pages/People";

const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/calls", label: "Calls", end: false },
  { to: "/people", label: "People", end: false },
  { to: "/occupations", label: "Occupations", end: false },
];

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold text-brand-600 dark:text-blue-400">HunarVaani</span>
            <span className="text-sm text-slate-500">हुनरवाणी · team console</span>
          </div>
          <nav className="flex flex-wrap gap-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm font-medium ${
                    isActive
                      ? "bg-brand-50 text-brand-700 dark:bg-slate-800 dark:text-blue-300"
                      : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/calls" element={<Calls />} />
          <Route path="/calls/:id" element={<CallDetail />} />
          <Route path="/people" element={<People />} />
          <Route path="/occupations" element={<Occupations />} />
          <Route path="*" element={<Overview />} />
        </Routes>
      </main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-slate-500">
        Numbers show only their last four digits. Pages refresh by themselves every few seconds.
      </footer>
    </div>
  );
}
