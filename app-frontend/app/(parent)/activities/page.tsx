"use client";

import { useEffect, useState } from "react";
import { getActivities, getParentActivities, enableActivity, disableActivity, createActivity } from "@/lib/api";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

export default function ActivitiesPage() {
  const [activities, setActivities] = useState<any[]>([]);
  const [enabled, setEnabled] = useState<Record<number, any>>({});
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", default_points: 10, category: "chore" });

  useEffect(() => {
    Promise.all([getActivities(), getParentActivities()]).then(([all, parentOnes]: any) => {
      setActivities(all);
      const map: Record<number, any> = {};
      for (const pa of parentOnes) map[pa.activity_id] = pa;
      setEnabled(map);
    });
  }, []);

  async function handleToggle(activityId: number) {
    const pa = enabled[activityId];
    if (pa?.is_active) {
      const updated: any = await disableActivity(activityId);
      setEnabled((prev) => ({ ...prev, [activityId]: updated }));
    } else {
      const updated: any = await enableActivity(activityId, {});
      setEnabled((prev) => ({ ...prev, [activityId]: updated }));
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const activity: any = await createActivity({ ...form, default_points: Number(form.default_points) });
    setActivities((prev) => [...prev, activity]);
    setShowForm(false);
    setForm({ name: "", description: "", default_points: 10, category: "chore" });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800">Activities</h2>
        <Button onClick={() => setShowForm((v) => !v)}>{showForm ? "Cancel" : "New activity"}</Button>
      </div>

      {showForm && (
        <Card>
          <form onSubmit={handleCreate} className="flex flex-col gap-3">
            <input
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              className="border rounded-lg px-3 py-2 text-sm"
            />
            <input
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="border rounded-lg px-3 py-2 text-sm"
            />
            <div className="flex gap-3">
              <input
                type="number"
                placeholder="Points"
                value={form.default_points}
                onChange={(e) => setForm({ ...form, default_points: Number(e.target.value) })}
                className="border rounded-lg px-3 py-2 text-sm w-24"
              />
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="border rounded-lg px-3 py-2 text-sm"
              >
                <option value="chore">Chore</option>
                <option value="play">Play</option>
                <option value="creative">Creative</option>
                <option value="study">Study</option>
              </select>
            </div>
            <Button type="submit">Create</Button>
          </form>
        </Card>
      )}

      <ul className="flex flex-col gap-3">
        {activities.map((a) => {
          const pa = enabled[a.id];
          const isActive = pa?.is_active ?? false;
          return (
            <li key={a.id}>
              <Card className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-800">{a.name}</p>
                  <p className="text-sm text-gray-500">
                    {pa?.points_override ?? a.default_points} pts · {a.category}
                  </p>
                </div>
                <Button
                  variant={isActive ? "danger" : "success"}
                  onClick={() => handleToggle(a.id)}
                >
                  {isActive ? "Disable" : "Enable"}
                </Button>
              </Card>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
