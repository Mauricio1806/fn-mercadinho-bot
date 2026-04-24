import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  color?: "green" | "blue" | "orange" | "purple";
  subtitle?: string;
}

const COLOR_MAP = {
  green: { bg: "bg-green-50", icon: "text-green-600", border: "border-green-100" },
  blue: { bg: "bg-blue-50", icon: "text-blue-600", border: "border-blue-100" },
  orange: { bg: "bg-orange-50", icon: "text-orange-600", border: "border-orange-100" },
  purple: { bg: "bg-purple-50", icon: "text-purple-600", border: "border-purple-100" },
};

export function StatCard({ title, value, icon: Icon, color = "green", subtitle }: StatCardProps) {
  const colors = COLOR_MAP[color];

  return (
    <Card className={cn("border", colors.border)}>
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">{title}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
            {subtitle && <p className="mt-0.5 text-xs text-gray-400">{subtitle}</p>}
          </div>
          <div className={cn("rounded-full p-3", colors.bg)}>
            <Icon className={cn("h-5 w-5", colors.icon)} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
