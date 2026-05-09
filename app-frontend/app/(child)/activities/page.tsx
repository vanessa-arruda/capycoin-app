"use client";

import { useEffect, useState } from "react";
import { getAvailableActivities, getChildActivities, pickActivity, submitActivity } from "@/lib/api";
import ActivityCard from "@/components/child/ActivityCard";
import Button from "@/components/ui/Button";

export default function ActivitiesPage() {
  const [available, setAvailable] = useState<any[]>([]);
  const [myActivities, setMyActivities] = useState<any[]>([]);

  useEffect(() => {
    getAvailableActivities().then((data: any) => setAvailable(data));
    getChildActivities().then((data: any) => setMyActivities(data));
  }, []);

  const pickedIds = new Set(myActivities.map((a: any) => a.activity_id));
  const ongoing = myActivities.filter((a: any) => a.status === "PENDING" && !a.submitted_at);
  const submitted = myActivities.filter((a: any) => a.status === "PENDING" && a.submitted_at);

  async function handlePick(activityId: number) {
    const ca: any = await pickActivity(activityId);
    setMyActivities((prev) => [...prev, ca]);
  }

  async function handleSubmit(childActivityId: number) {
    const updated: any = await submitActivity(childActivityId);
    setMyActivities((prev) => prev.map((a) => (a.id === childActivityId ? updated : a)));
  }

  return (
    <div className="flex flex-col gap-8">
      <section>
        <h2 className="text-xl font-bold text-gray-800 mb-4">Available quests</h2>
        {available.length === 0 ? (
          <p className="text-gray-400 text-sm">No quests available right now.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {available.map((a) => (
              <ActivityCard
                key={a.id}
                activity={{ id: a.id, name: a.name, description: a.description, points: a.default_points, category: a.category }}
                onPick={handlePick}
                status={pickedIds.has(a.id) ? "PENDING" : undefined}
              />
            ))}
          </div>
        )}
      </section>

      {ongoing.length > 0 && (
        <section>
          <h2 className="text-xl font-bold text-gray-800 mb-4">In progress</h2>
          <ul className="flex flex-col gap-3">
            {ongoing.map((a: any) => (
              <li key={a.id} className="bg-white rounded-xl shadow-sm p-4 flex items-center justify-between">
                <span className="text-gray-800 font-medium">Quest #{a.activity_id}</span>
                <Button onClick={() => handleSubmit(a.id)}>Mark done</Button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {submitted.length > 0 && (
        <section>
          <h2 className="text-xl font-bold text-gray-800 mb-4">Waiting for approval</h2>
          <ul className="flex flex-col gap-3">
            {submitted.map((a: any) => (
              <li key={a.id} className="bg-white rounded-xl shadow-sm p-4 flex items-center justify-between">
                <span className="text-gray-800 font-medium">Quest #{a.activity_id}</span>
                <span className="text-sm text-amber-500 font-medium">Pending review</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
