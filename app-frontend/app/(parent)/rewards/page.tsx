"use client";

import { useEffect, useState } from "react";
import { getParentRewards, getPendingRedemptions, createReward, reviewRedemption } from "@/lib/api";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

export default function RewardsPage() {
  const [rewards, setRewards] = useState<any[]>([]);
  const [redemptions, setRedemptions] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", points_cost: 50 });

  useEffect(() => {
    getParentRewards().then((data: any) => setRewards(data));
    getPendingRedemptions().then((data: any) => setRedemptions(data));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const reward: any = await createReward({ ...form, points_cost: Number(form.points_cost) });
    setRewards((prev) => [...prev, reward]);
    setShowForm(false);
    setForm({ name: "", description: "", points_cost: 50 });
  }

  async function handleReview(id: number, status: "APPROVED" | "REJECTED") {
    await reviewRedemption(id, status);
    setRedemptions((prev) => prev.filter((r) => r.id !== id));
  }

  return (
    <div className="flex flex-col gap-8">
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-800">Rewards</h2>
          <Button onClick={() => setShowForm((v) => !v)}>{showForm ? "Cancel" : "New reward"}</Button>
        </div>

        {showForm && (
          <Card className="mb-4">
            <form onSubmit={handleCreate} className="flex flex-col gap-3">
              <input
                placeholder="Reward name"
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
              <input
                type="number"
                placeholder="Points cost"
                value={form.points_cost}
                onChange={(e) => setForm({ ...form, points_cost: Number(e.target.value) })}
                className="border rounded-lg px-3 py-2 text-sm w-32"
              />
              <Button type="submit">Create</Button>
            </form>
          </Card>
        )}

        <ul className="flex flex-col gap-3">
          {rewards.map((r) => (
            <li key={r.id}>
              <Card className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-800">{r.name}</p>
                  <p className="text-sm text-gray-500">{r.points_cost} pts</p>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-bold text-gray-800 mb-4">Pending redemptions</h2>
        {redemptions.length === 0 ? (
          <p className="text-gray-400 text-sm">No pending redemptions</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {redemptions.map((r) => (
              <li key={r.id}>
                <Card className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-800">{r.reward_name}</p>
                    <p className="text-sm text-gray-500">
                      {r.child_name} · {r.points_cost} pts
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="success" onClick={() => handleReview(r.id, "APPROVED")}>Approve</Button>
                    <Button variant="danger" onClick={() => handleReview(r.id, "REJECTED")}>Reject</Button>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
