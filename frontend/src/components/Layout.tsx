import { NavLink, Outlet } from "react-router-dom";
import { clsx } from "clsx";

const NAV_ITEMS = [
  { to: "/today", label: "Today" },
  { to: "/charging", label: "Charging" },
  { to: "/battery", label: "Battery" },
  { to: "/drives", label: "Drives" },
  { to: "/costs", label: "Costs" },
  { to: "/alerts", label: "Alerts" },
  { to: "/assistant", label: "Assistant" },
  { to: "/settings", label: "Settings" },
  { to: "/imports", label: "Import" },
];

export function Layout({ onLogout }: { onLogout?: () => void }) {
  return (
    <div className="min-h-screen flex flex-col sm:pl-48">
      <header className="bg-gray-900 border-b border-gray-800 px-4 py-3 flex items-center justify-between sm:pl-4">
        <span className="text-brand-500 font-semibold tracking-tight text-lg">EV Lens</span>
        {onLogout && (
          <button
            onClick={onLogout}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Sign out
          </button>
        )}
      </header>

      <main className="flex-1 overflow-auto p-4">
        <Outlet />
      </main>

      {/* Mobile bottom nav — first 5 items */}
      <nav className="bg-gray-900 border-t border-gray-800 flex sm:hidden">
        {NAV_ITEMS.slice(0, 5).map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx("flex-1 py-3 text-center text-xs", isActive ? "text-brand-500" : "text-gray-400")
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Desktop sidebar */}
      <aside className="hidden sm:fixed sm:inset-y-0 sm:left-0 sm:flex sm:w-48 sm:flex-col sm:bg-gray-900 sm:border-r sm:border-gray-800 sm:pt-14">
        {NAV_ITEMS.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                "px-6 py-3 text-sm",
                isActive ? "text-brand-500 bg-gray-800" : "text-gray-400 hover:text-gray-100"
              )
            }
          >
            {label}
          </NavLink>
        ))}
        {onLogout && (
          <button
            onClick={onLogout}
            className="mt-auto px-6 py-4 text-sm text-gray-600 hover:text-gray-400 text-left transition-colors"
          >
            Sign out
          </button>
        )}
      </aside>
    </div>
  );
}
