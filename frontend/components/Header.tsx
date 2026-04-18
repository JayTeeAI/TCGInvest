"use client";

import { getUserClient, logout, getGoogleLoginUrl } from "../lib/auth-client";
import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import type { User } from "../lib/auth-client";

export default function Header() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getUserClient().then((u) => {
      setUser(u.authenticated ? u : null);
      setLoading(false);
    });
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleLogout = async () => {
    await logout();
    setUser(null);
    setDropdownOpen(false);
  };

  return (
    <header className="w-full border-b border-slate-700 bg-slate-900 px-6 py-3">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="text-white font-bold text-lg">
            TCG Invest
          </Link>
          <nav className="hidden sm:flex items-center gap-6">
            <Link href="/tools/tracker" className="text-slate-400 hover:text-white text-sm transition-colors">
              Tracker
            </Link>
            <Link href="/tools/etb-tracker" className="text-slate-400 hover:text-white text-sm transition-colors">
              ETB Tracker
            </Link>
            <Link href="/blog" className="text-slate-400 hover:text-white text-sm transition-colors">
              Blog
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          {loading ? null : user ? (
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen(prev => !prev)}
                className="flex items-center gap-2 text-slate-300 hover:text-white transition-colors text-sm"
              >
                <span>{user.email}</span>
                {user.role === "premium" || user.role === "admin" ? (
                  <span title="Premium" className="text-yellow-400 text-base">&#x1F451;</span>
                ) : (
                  <span title="Free account" className="text-slate-500 text-base">&#x1F451;</span>
                )}
                <svg className={`w-3 h-3 text-slate-500 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-52 bg-slate-800 border border-slate-700 rounded-xl shadow-xl z-50 py-1">
                  {user.role === "premium" && (
                    <div className="px-4 py-2 border-b border-slate-700">
                      <span className="text-xs bg-yellow-500 text-black px-2 py-0.5 rounded-full font-medium">Premium</span>
                    </div>
                  )}
                  <Link
                    href="/account/alerts"
                    onClick={() => setDropdownOpen(false)}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
                  >
                    <span>🔔</span> Price Alerts
                  </Link>
                  <Link
                    href="/account/preferences"
                    onClick={() => setDropdownOpen(false)}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
                  >
                    <span>⚙️</span> Email Preferences
                  </Link>
                  {user.role !== "premium" && (
                    <Link
                      href="/premium"
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm text-yellow-400 hover:text-yellow-300 hover:bg-slate-700 transition-colors"
                    >
                      <span>⭐</span> Upgrade to Premium
                    </Link>
                  )}
                  <div className="border-t border-slate-700 mt-1">
                    <button
                      onClick={handleLogout}
                      className="w-full text-left flex items-center gap-2 px-4 py-2.5 text-sm text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                    >
                      <span>→</span> Sign out
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <a
              href={getGoogleLoginUrl()}
              className="flex items-center gap-2 bg-white text-slate-900 text-sm font-medium px-4 py-2 rounded-lg hover:bg-slate-100 transition-colors"
            >
              Sign in with Google
            </a>
          )}
        </div>
      </div>
    </header>
  );
}
