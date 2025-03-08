import { InputHTMLAttributes } from "react";

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className="px-4 py-2 rounded-md border bg-gray-900 text-white w-full" {...props} />;
}
