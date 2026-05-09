"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken, getRole, clearSession } from "@/lib/auth";

export default function ParentLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (!getToken() || getRole() !== "parent") {
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
        <span className="font-bold text-amber-700 text-lg">Capycoin</span>
        <div className="flex gap-6 text-sm">
          <Link href="/parent/dashboard" className="text-gray-600 hover:text-amber-700 transition">Dashboard</Link>
          <Link href="/parent/activities" className="text-gray-600 hover:text-amber-700 transition">Activities</Link>
          <Link href="/parent/rewards" className="text-gray-600 hover:text-amber-700 transition">Rewards</Link>
        </div>
        <button onClick={logout} className="text-sm text-gray-400 hover:text-red-500 transition">
          Logout
        </button>
      </nav>
      <div className="max-w-4xl mx-auto px-4 py-8">{children}</div>
    </div>
  );
}
