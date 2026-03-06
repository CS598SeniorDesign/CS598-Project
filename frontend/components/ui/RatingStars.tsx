"use client"

import { useState } from "react"

interface RatingStarsProps {
  rating?: number
  onChange?: (value: number) => void
}

export default function RatingStars({
  rating = 0,
  onChange,
}: RatingStarsProps) {
  const [currentRating, setCurrentRating] = useState<number>(rating)

  const handleClick = (value: number) => {
    setCurrentRating(value)
    if (onChange) {
      onChange(value)
    }
  }

  return (
    <div className="flex gap-2">
      {[1, 2, 3, 4, 5].map((star) => {
        const isActive = star <= currentRating

        return (
          <button
            key={star}
            type="button"
            onClick={() => handleClick(star)}
            className={`text-3xl transition-transform duration-150 ${
              isActive
                ? "text-amber-400 scale-110"
                : "text-gray-500 hover:scale-110"
            }`}
          >
            ★
          </button>
        )
      })}
    </div>
  )
}