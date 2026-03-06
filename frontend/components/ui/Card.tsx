import React from "react"

interface CardProps {
  children: React.ReactNode
  className?: string
}

export default function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`bg-slate-800 p-6 rounded-2xl shadow-lg border border-slate-700 ${className}`}
    >
      {children}
    </div>
  )
}