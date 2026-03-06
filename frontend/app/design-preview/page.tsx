export default function DesignPreview() {
  return (
    <div className="min-h-screen bg-[#0F172A] text-[#F8FAFC] p-10 space-y-12">

      <h1 className="text-4xl font-bold">Design System Preview</h1>

      {/* Color Palette */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Color Palette</h2>
        <div className="flex gap-6 flex-wrap">

          <div className="w-32 h-32 bg-[#4F46E5] flex items-center justify-center rounded-xl">
            Primary
          </div>

          <div className="w-32 h-32 bg-[#10B981] flex items-center justify-center rounded-xl">
            Success
          </div>

          <div className="w-32 h-32 bg-[#FFBF00] text-black flex items-center justify-center rounded-xl">
            Accent
          </div>

          <div className="w-32 h-32 bg-[#EF4444] flex items-center justify-center rounded-xl">
            Error
          </div>

        </div>
      </section>

      {/* Typography */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Typography</h2>
        <h1 className="text-4xl font-bold">Heading Example</h1>
        <p className="text-lg">Body Text Example</p>
      </section>

      {/* Buttons */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Buttons</h2>
        <div className="flex gap-4 flex-wrap">

          <button className="px-6 py-2 bg-[#4F46E5] rounded-lg hover:opacity-80">
            Primary Button
          </button>

          <button className="px-6 py-2 bg-[#10B981] rounded-lg hover:opacity-80">
            Secondary Button
          </button>

          <button className="px-6 py-2 bg-[#EF4444] rounded-lg hover:opacity-80">
            Danger Button
          </button>

        </div>
      </section>

      {/* Card Example */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Game Card Example</h2>

        <div className="bg-[#1E293B] p-6 rounded-xl w-96 shadow-lg">
          <h3 className="text-xl font-semibold">Catan</h3>
          <p className="text-sm text-gray-400">Player Count: 3–4</p>
          <p className="mt-2">Win Rate: 65%</p>
        </div>

      </section>

      {/* Badges */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Badges</h2>
        <div className="flex gap-4">

          <span className="px-4 py-1 bg-[#FFBF00] text-black rounded-full">
            Mortal Enemy
          </span>

          <span className="px-4 py-1 bg-[#4F46E5] rounded-full">
            Sidekick
          </span>

        </div>
      </section>

    </div>
  );
}