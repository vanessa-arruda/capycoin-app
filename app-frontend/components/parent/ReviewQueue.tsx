import Button from "@/components/ui/Button";

interface Review {
  id: number;
  child_name: string;
  activity_name: string;
  submitted_at: string;
}

interface Props {
  reviews: Review[];
  onApprove: (id: number) => void;
  onReject: (id: number) => void;
}

export default function ReviewQueue({ reviews, onApprove, onReject }: Props) {
  if (reviews.length === 0) {
    return <p className="text-gray-400 text-sm">No pending reviews</p>;
  }

  return (
    <ul className="flex flex-col gap-3">
      {reviews.map((r) => (
        <li key={r.id} className="bg-white rounded-xl shadow-sm p-4 flex items-center justify-between">
          <div>
            <p className="font-medium text-gray-800">{r.activity_name}</p>
            <p className="text-sm text-gray-500">by {r.child_name}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="success" onClick={() => onApprove(r.id)}>Approve</Button>
            <Button variant="danger" onClick={() => onReject(r.id)}>Reject</Button>
          </div>
        </li>
      ))}
    </ul>
  );
}
