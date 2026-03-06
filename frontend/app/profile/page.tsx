import ProtectedRoute from "@/components/ProtectedRoute"
import Button from "@/components/ui/Button"
import GameCard from "@/components/games/GameCard"

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <div className="p-10 text-white">
        <h1 className="text-3xl mb-8">Profile Page (Protected)</h1>

        {/* Top Action Button */}
        <div className="mb-8">
          <Button variant="primary">Log Game</Button>
        </div>

        {/* Game Cards Section */}
        <div className="max-w-3xl">
          <GameCard
            title="Terraforming Mars"
            playerCount="1–5"
            complexity="4.2 / 5"
            winRate="52%"
            tags={["Strategy", "Engine Building", "Sci-Fi"]}
          />
        </div>
      </div>
    </ProtectedRoute>
  )
}