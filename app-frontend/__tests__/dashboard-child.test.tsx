import { render, screen } from "@testing-library/react";
import ChildDashboard from "@/app/(child)/dashboard/page";

jest.mock("@/lib/api", () => ({
  getChildProfile: jest.fn().mockResolvedValue({
    name: "Luca",
    points_total: 150,
    level: 2,
    avatar: "capybara_blue",
  }),
  getChildActivities: jest.fn().mockResolvedValue([]),
}));

describe("ChildDashboard", () => {
  it("shows child name", async () => {
    render(<ChildDashboard />);
    expect(await screen.findByText(/luca/i)).toBeInTheDocument();
  });

  it("displays current points", async () => {
    render(<ChildDashboard />);
    expect(await screen.findByText(/150/)).toBeInTheDocument();
  });

  it("displays current level", async () => {
    render(<ChildDashboard />);
    expect(await screen.findByText(/level 2/i)).toBeInTheDocument();
  });

  it("renders capybara avatar", async () => {
    render(<ChildDashboard />);
    const avatar = await screen.findByAltText(/capybara avatar/i);
    expect(avatar).toBeInTheDocument();
  });
});
