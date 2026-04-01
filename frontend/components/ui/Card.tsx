import React from "react"

interface CardProps {
  children: React.ReactNode
  className?: string
}

export default function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`bg-slate-800 rounded-xl p-4 shadow-md hover:shadow-lg transition ${className}`}
    >
      {children}
    </div>
  )
}