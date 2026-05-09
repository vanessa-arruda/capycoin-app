import { render, screen } from "@testing-library/react";
import ParentDashboard from "@/app/(parent)/dashboard/page";

jest.mock("@/lib/api", () => ({
  getParentChildren: jest.fn().mockResolvedValue([
    { id: 1, name: "Luca", points_total: 150, level: 2 },
    { id: 2, name: "Sofia", points_total: 80, level: 1 },
  ]),
  getPendingReviews: jest.fn().mockResolvedValue([
    { id: 10, child_name: "Luca", activity_name: "Wash the dishes" },
  ]),
}));

describe("ParentDashboard", () => {
  it("lists all children", async () => {
    render(<ParentDashboard />);
    expect(await screen.findByText("Luca")).toBeInTheDocument();
    expect(await screen.findByText("Sofia")).toBeInTheDocument();
  });

  it("shows each child's points", async () => {
    render(<ParentDashboard />);
    expect(await screen.findByText(/150/)).toBeInTheDocument();
    expect(await screen.findByText(/80/)).toBeInTheDocument();
  });

  it("shows pending review count", async () => {
    render(<ParentDashboard />);
    expect(await screen.findByText(/1 pending/i)).toBeInTheDocument();
  });

  it("shows pending activity name in review queue", async () => {
    render(<ParentDashboard />);
    expect(await screen.findByText(/wash the dishes/i)).toBeInTheDocument();
  });
});
