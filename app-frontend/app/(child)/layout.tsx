"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken, getRole, clearSession } from "@/lib/auth";

export default function ChildLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (!getToken() || getRole() !== "child") {
      router.replace("/login");
    }
  }, [router]);

  function logout() {
    clearSession();
    router.push("/login");
  }

  return (
    <div className="min-h-screen bg-amber-50">
      <nav className="bg-white shadow-sm px-6 py-3 flex items-center justify-between">
        <span className="font-bold text-amber-700 text-lg">🦫 Capycoin</span>
        <div className="flex gap-6 text-sm">
          <Link href="/child/dashboard" className="text-gray-600 hover:text-amber-700 transition">Home</Link>
          <Link href="/child/activities" className="text-gray-600 hover:text-amber-700 transition">Quests</Link>
          <Link href="/child/rewards" className="text-gray-600 hover:text-amber-700 transition">Shop</Link>
          <Link href="/child/profile" className="text-gray-600 hover:text-amber-700 transition">Profile</Link>
        </div>
        <button onClick={logout} className="text-sm text-gray-400 hover:text-red-500 transition">
          Logout
        </button>
      </nav>
      <div className="max-w-2xl mx-auto px-4 py-8">{children}</div>
    </div>
  );
}
