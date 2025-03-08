import { ReactNode } from "react";

export function Card({ children }: { children: ReactNode }) {
  return <div className="border rounded-lg p-4 bg-gray-800">{children}</div>;
}

export function CardContent({ children }: { children: ReactNode }) {
  return <div className="p-4">{children}</div>;
}
