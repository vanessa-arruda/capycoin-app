"use client";

import { useEffect, useState } from "react";
import { getRewards, getChildProfile, redeemReward } from "@/lib/api";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

export default function RewardsPage() {
  const [rewards, setRewards] = useState<any[]>([]);
  const [points, setPoints] = useState(0);
  const [redeemed, setRedeemed] = useState<Set<number>>(new Set());

  useEffect(() => {
    getRewards().then((data: any) => setRewards(data));
    getChildProfile().then((data: any) => setPoints(data.points_total));
  }, []);

  async function handleRedeem(rewardId: number) {
    await redeemReward(rewardId);
    setRedeemed((prev) => new Set(prev).add(rewardId));
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800">Rewards shop</h2>
        <span className="text-amber-600 font-semibold">{points} coins</span>
      </div>

      {rewards.length === 0 ? (
        <p className="text-gray-400 text-sm">No rewards available yet.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {rewards.map((r) => {
            const canAfford = points >= r.points_cost;
            const alreadyRedeemed = redeemed.has(r.id);
            return (
              <li key={r.id}>
                <Card className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-gray-800">{r.name}</p>
                    {r.description && (
                      <p className="text-sm text-gray-500">{r.description}</p>
                    )}
                    <p className="text-sm text-amber-600 font-medium mt-1">{r.points_cost} coins</p>
                  </div>
                  <Button
                    variant={alreadyRedeemed ? "ghost" : canAfford ? "primary" : "ghost"}
                    disabled={!canAfford || alreadyRedeemed}
                    onClick={() => handleRedeem(r.id)}
                  >
                    {alreadyRedeemed ? "Requested" : canAfford ? "Redeem" : "Not enough"}
                  </Button>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
