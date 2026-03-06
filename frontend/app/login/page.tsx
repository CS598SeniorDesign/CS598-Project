export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white">
      <div className="w-full max-w-md bg-gray-900 p-8 rounded-xl">

        <h1 className="text-3xl font-bold mb-6">Login</h1>

        <form className="flex flex-col gap-4">

          <input
            type="email"
            placeholder="Email"
            className="p-3 rounded bg-gray-800 border border-gray-700"
          />

          <input
            type="password"
            placeholder="Password"
            className="p-3 rounded bg-gray-800 border border-gray-700"
          />

          <button
            type="submit"
            className="bg-primary py-2 rounded-lg hover:opacity-90"
          >
            Sign In
          </button>

        </form>

      </div>
    </div>
  )
}