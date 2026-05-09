"use client";

import { useEffect, useState } from "react";
import { getChildProfile, getChildActivities } from "@/lib/api";

const LEVEL_THRESHOLDS = [0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500];

function xpProgress(points: number, level: number): number {
  const current = LEVEL_THRESHOLDS[level - 1] ?? 0;
  const next = LEVEL_THRESHOLDS[level] ?? current;
  if (next === current) return 100;
  return Math.min(100, Math.round(((points - current) / (next - current)) * 100));
}

const AVATARS: Record<string, string> = {
  capybara_default: "🟤",
  capybara_blue: "🔵",
  capybara_red: "🔴",
  capybara_green: "🟢",
};

export default function ChildDashboard() {
  const [profile, setProfile] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);

  useEffect(() => {
    getChildProfile().then((data: any) => setProfile(data));
    getChildActivities().then((data: any) => setActivities(data));
  }, []);

  if (!profile) return null;

  const pending = activities.filter((a) => a.status === "PENDING");
  const progress = xpProgress(profile.points_total, profile.level);

  return (
    <div className="flex flex-col gap-6">
      {/* Avatar + greeting */}
      <div className="flex flex-col items-center gap-2 pt-4">
        <img
          src={`data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='80'>🦫</text></svg>`}
          alt="capybara avatar"
          className="w-24 h-24"
        />
        <h1 className="text-2xl font-bold text-gray-800">Hey, {profile.name}!</h1>
      </div>

      {/* Points + level */}
      <div className="bg-white rounded-2xl shadow-sm p-5 flex flex-col gap-3">
        <div className="flex justify-between items-center">
          <span className="text-gray-500 text-sm">Your coins</span>
          <span className="text-3xl font-bold text-amber-600">{profile.points_total}</span>
        </div>
        <div className="flex justify-between items-center text-sm text-gray-500">
          <span>Level {profile.level}</span>
          <span>{progress}% to next level</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-3">
          <div
            className="bg-amber-400 h-3 rounded-full transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Active quests */}
      {pending.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm p-5">
          <h2 className="font-bold text-gray-800 mb-3">Active quests</h2>
          <ul className="flex flex-col gap-2">
            {pending.map((a: any) => (
              <li key={a.id} className="flex items-center justify-between text-sm">
                <span className="text-gray-700">Quest #{a.activity_id}</span>
                <span className="text-amber-500 font-medium capitalize">{a.status.toLowerCase()}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
