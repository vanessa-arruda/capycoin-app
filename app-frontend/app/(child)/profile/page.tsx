"use client";

import { useEffect, useState } from "react";
import { getChildProfile, getChildActivities } from "@/lib/api";
import Card from "@/components/ui/Card";

const LEVEL_THRESHOLDS = [0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500];

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);

  useEffect(() => {
    getChildProfile().then((data: any) => setProfile(data));
    getChildActivities().then((data: any) => setActivities(data));
  }, []);

  if (!profile) return null;

  const completed = activities.filter((a) => a.status === "APPROVED").length;
  const nextThreshold = LEVEL_THRESHOLDS[profile.level] ?? "MAX";

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col items-center gap-2 pt-4">
        <img
          src={`data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='80'>🦫</text></svg>`}
          alt="capybara avatar"
          className="w-20 h-20"
        />
        <h1 className="text-xl font-bold text-gray-800">{profile.name}</h1>
        <p className="text-sm text-gray-500">{profile.email}</p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <Card className="flex flex-col items-center gap-1">
          <span className="text-2xl font-bold text-amber-600">{profile.level}</span>
          <span className="text-xs text-gray-500">Level</span>
        </Card>
        <Card className="flex flex-col items-center gap-1">
          <span className="text-2xl font-bold text-amber-600">{profile.points_total}</span>
          <span className="text-xs text-gray-500">Coins</span>
        </Card>
        <Card className="flex flex-col items-center gap-1">
          <span className="text-2xl font-bold text-amber-600">{completed}</span>
          <span className="text-xs text-gray-500">Quests done</span>
        </Card>
      </div>

      <Card>
        <p className="text-sm text-gray-500 mb-1">Next level at</p>
        <p className="text-lg font-semibold text-gray-800">
          {nextThreshold === "MAX" ? "Max level reached!" : `${nextThreshold} coins`}
        </p>
      </Card>
    </div>
  );
}
