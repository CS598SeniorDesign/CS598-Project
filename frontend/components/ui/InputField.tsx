interface InputFieldProps {
  label: string
  type?: string
  placeholder?: string
}

export default function InputField({
  label,
  type = "text",
  placeholder = "",
}: InputFieldProps) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm text-gray-300">{label}</label>
      <input
        type={type}
        placeholder={placeholder}
        className="px-4 py-2 rounded-xl bg-slate-700 text-white border border-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />
    </div>
  )
}