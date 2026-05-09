import { getToken } from "./auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw { status: res.status, detail: error.detail ?? "Unknown error" };
  }

  return res.json();
}

// Auth
export const login = (email: string, password: string) =>
  request<{ access_token: string; role: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

// Parent
export const getParentProfile = () => request("/parents/me");
export const getParentChildren = () => request("/parents/me/children");

// Child
export const getChildProfile = () => request("/children/me");
export const getChildActivities = () => request("/children/me/activities");
export const getChildRewards = () => request("/children/me/rewards");

// Activities
export const getActivities = () => request("/activities");
export const getAvailableActivities = () => request("/activities/available");
export const createActivity = (data: object) =>
  request("/activities", { method: "POST", body: JSON.stringify(data) });
export const enableActivity = (id: number, config: object) =>
  request(`/activities/${id}/enable`, { method: "POST", body: JSON.stringify(config) });
export const disableActivity = (id: number) =>
  request(`/activities/${id}/disable`, { method: "POST" });
export const pickActivity = (activityId: number) =>
  request("/child-activities", { method: "POST", body: JSON.stringify({ activity_id: activityId }) });
export const submitActivity = (childActivityId: number) =>
  request(`/child-activities/${childActivityId}/submit`, { method: "POST" });
export const reviewActivity = (childActivityId: number, status: "APPROVED" | "REJECTED") =>
  request(`/child-activities/${childActivityId}/review`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });

// Rewards
export const getRewards = () => request("/rewards");
export const createReward = (data: object) =>
  request("/rewards", { method: "POST", body: JSON.stringify(data) });
export const redeemReward = (rewardId: number) =>
  request(`/rewards/${rewardId}/redeem`, { method: "POST" });

// Pending reviews (child activities awaiting approval)
export const getPendingReviews = () =>
  request<{ id: number; child_name: string; activity_name: string; submitted_at: string }[]>("/child-activities/pending");

// Parent-specific
export const getParentActivities = () => request("/parents/me/activities");
export const getParentRewards = () => request("/parents/me/rewards");
export const getPendingRedemptions = () => request("/parents/me/redemptions/pending");
export const reviewRedemption = (redemptionId: number, status: "APPROVED" | "REJECTED") =>
  request(`/rewards/redemptions/${redemptionId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
