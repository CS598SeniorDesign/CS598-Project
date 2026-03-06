export default function GameDetailPage() {
  return (
    <div className="p-10 text-white space-y-10">
      
      <h1 className="text-4xl font-bold">
        Game Title Here
      </h1>

      {/* Rules & Tutorials Section */}
      <section className="bg-gray-900 p-6 rounded-xl border border-gray-800">
        <h2 className="text-2xl font-semibold mb-4">
          Rules & Tutorials
        </h2>

        <button className="bg-indigo-600 px-5 py-2 rounded-lg hover:bg-indigo-500 transition">
          View Official Rulebook
        </button>
      </section>

      {/* Community Strategy Section */}
      <section className="bg-gray-900 p-6 rounded-xl border border-gray-800">
        <h2 className="text-2xl font-semibold mb-4">
          Community Strategy Tips
        </h2>

        <p className="text-gray-400">
          (Coming soon — informations will appear here!)
        </p>
      </section>

    </div>
  )
}