import Button from "@/components/ui/Button";

interface Activity {
  id: number;
  name: string;
  description?: string;
  points: number;
  category: string;
}

interface Props {
  activity: Activity;
  onPick: (id: number) => void;
  status?: string;
}

export default function ActivityCard({ activity, onPick, status }: Props) {
  const isPicked = !!status;

  return (
    <div className="bg-white rounded-xl shadow-sm p-4 flex flex-col gap-2">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold text-gray-800">{activity.name}</p>
          <p className="text-xs text-amber-600 font-medium">{activity.points} points</p>
        </div>
        <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full capitalize">
          {activity.category}
        </span>
      </div>
      {activity.description && (
        <p className="text-sm text-gray-500">{activity.description}</p>
      )}
      <Button
        variant={isPicked ? "ghost" : "primary"}
        disabled={isPicked}
        onClick={() => onPick(activity.id)}
        className="mt-1 w-full"
      >
        {isPicked ? "In progress" : "Pick"}
      </Button>
    </div>
  );
}
