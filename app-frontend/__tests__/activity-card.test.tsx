import { render, screen, fireEvent } from "@testing-library/react";
import ActivityCard from "@/components/child/ActivityCard";

const mockActivity = {
  id: 1,
  name: "Wash the dishes",
  description: "Clean all dishes after dinner",
  points: 10,
  category: "chore",
};

const mockOnPick = jest.fn();

beforeEach(() => jest.clearAllMocks());

describe("ActivityCard", () => {
  it("renders activity name and points", () => {
    render(<ActivityCard activity={mockActivity} onPick={mockOnPick} />);
    expect(screen.getByText("Wash the dishes")).toBeInTheDocument();
    expect(screen.getByText(/10 points/i)).toBeInTheDocument();
  });

  it("renders description", () => {
    render(<ActivityCard activity={mockActivity} onPick={mockOnPick} />);
    expect(screen.getByText(/clean all dishes/i)).toBeInTheDocument();
  });

  it("calls onPick with activity id when pick button is clicked", () => {
    render(<ActivityCard activity={mockActivity} onPick={mockOnPick} />);
    fireEvent.click(screen.getByRole("button", { name: /pick/i }));
    expect(mockOnPick).toHaveBeenCalledWith(mockActivity.id);
  });

  it("disables pick button when already picked", () => {
    render(<ActivityCard activity={mockActivity} onPick={mockOnPick} status="PENDING" />);
    expect(screen.getByRole("button", { name: /in progress/i })).toBeDisabled();
  });
});
