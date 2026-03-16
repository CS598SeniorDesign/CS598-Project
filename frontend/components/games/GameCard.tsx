import Card from "@/components/ui/Card"
import Badge from "@/components/ui/Badge"
import Button from "@/components/ui/Button"

interface GameCardProps {
  title: string
  playerCount: string
  complexity: string
  winRate: string
  tags: string[]
}

export default function GameCard({
  title,
  playerCount,
  complexity,
  winRate,
  tags,
}: GameCardProps) {
  return (
    <Card className="flex flex-col gap-4 hover:scale-105 transition-transform duration-200">
      {/* Title */}
      <h2 className="text-2xl font-bold text-white">{title}</h2>

      {/* Stats Section */}
      <div className="grid grid-cols-3 gap-4 text-gray-300 text-sm">
        <div>
          <span className="font-semibold text-white">Players:</span>{" "}
          {playerCount}
        </div>
        <div>
          <span className="font-semibold text-white">Complexity:</span>{" "}
          {complexity}
        </div>
        <div>
          <span className="font-semibold text-white">Win Rate:</span>{" "}
          {winRate}
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-2">
        {tags.map((tag, index) => (
          <Badge key={index} label={tag} color="secondary" />
        ))}
      </div>

      {/* Action Button */}
      <div className="mt-4">
        <Button variant="primary" className="w-full">
          Log Play
          </Button>
      </div>
    </Card>
  )
}