import Card from "@/components/ui/Card";

interface ChildSummary {
  id: number;
  name: string;
  avatar: string;
  points_total: number;
  level: number;
}

export default function ChildCard({ child }: { child: ChildSummary }) {
  return (
    <Card className="flex items-center gap-4">
      <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center text-2xl" aria-label="capybara avatar">
        🐾
      </div>
      <div>
        <p className="font-semibold text-gray-800">{child.name}</p>
        <p className="text-sm text-gray-500">Level {child.level} · {child.points_total} pts</p>
      </div>
    </Card>
  );
}
