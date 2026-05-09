"use client";

import { useEffect, useState } from "react";
import { getParentChildren, getPendingReviews, reviewActivity } from "@/lib/api";
import ChildCard from "@/components/parent/ChildCard";
import ReviewQueue from "@/components/parent/ReviewQueue";

export default function ParentDashboard() {
  const [children, setChildren] = useState<any[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);

  useEffect(() => {
    getParentChildren().then((data: any) => setChildren(data));
    getPendingReviews().then((data: any) => setReviews(data));
  }, []);

  async function handleApprove(id: number) {
    await reviewActivity(id, "APPROVED");
    setReviews((prev) => prev.filter((r) => r.id !== id));
  }

  async function handleReject(id: number) {
    await reviewActivity(id, "REJECTED");
    setReviews((prev) => prev.filter((r) => r.id !== id));
  }

  return (
    <div className="flex flex-col gap-8">
      <section>
        <h2 className="text-xl font-bold text-gray-800 mb-4">Your kids</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {children.map((child) => (
            <ChildCard key={child.id} child={child} />
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold text-gray-800 mb-4">
          Pending reviews{" "}
          {reviews.length > 0 && (
            <span className="text-sm font-normal text-amber-600">{reviews.length} pending</span>
          )}
        </h2>
        <ReviewQueue reviews={reviews} onApprove={handleApprove} onReject={handleReject} />
      </section>
    </div>
  );
}
