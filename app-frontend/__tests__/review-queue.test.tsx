import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ReviewQueue from "@/components/parent/ReviewQueue";

const mockReviews = [
  { id: 10, child_name: "Luca", activity_name: "Wash the dishes", submitted_at: "2026-05-09T10:00:00Z" },
];

const mockOnApprove = jest.fn();
const mockOnReject = jest.fn();

beforeEach(() => jest.clearAllMocks());

describe("ReviewQueue", () => {
  it("renders pending submissions", () => {
    render(<ReviewQueue reviews={mockReviews} onApprove={mockOnApprove} onReject={mockOnReject} />);
    expect(screen.getByText(/luca/i)).toBeInTheDocument();
    expect(screen.getByText(/wash the dishes/i)).toBeInTheDocument();
  });

  it("calls onApprove with review id when approve is clicked", async () => {
    render(<ReviewQueue reviews={mockReviews} onApprove={mockOnApprove} onReject={mockOnReject} />);
    fireEvent.click(screen.getByRole("button", { name: /approve/i }));
    await waitFor(() => expect(mockOnApprove).toHaveBeenCalledWith(10));
  });

  it("calls onReject with review id when reject is clicked", async () => {
    render(<ReviewQueue reviews={mockReviews} onApprove={mockOnApprove} onReject={mockOnReject} />);
    fireEvent.click(screen.getByRole("button", { name: /reject/i }));
    await waitFor(() => expect(mockOnReject).toHaveBeenCalledWith(10));
  });

  it("shows empty state when no pending reviews", () => {
    render(<ReviewQueue reviews={[]} onApprove={mockOnApprove} onReject={mockOnReject} />);
    expect(screen.getByText(/no pending reviews/i)).toBeInTheDocument();
  });
});
