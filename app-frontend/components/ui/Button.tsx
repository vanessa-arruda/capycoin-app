import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "danger" | "ghost" | "success";

const styles: Record<Variant, string> = {
  primary: "bg-amber-500 hover:bg-amber-600 text-white",
  danger: "bg-red-400 hover:bg-red-500 text-white",
  ghost: "bg-gray-100 hover:bg-gray-200 text-gray-700",
  success: "bg-green-500 hover:bg-green-600 text-white",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export default function Button({ variant = "primary", className = "", children, ...props }: Props) {
  return (
    <button
      className={`font-medium px-4 py-2 rounded-lg text-sm transition disabled:opacity-50 ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
