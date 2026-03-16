export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white">
      <div className="w-full max-w-md bg-gray-900 p-8 rounded-xl">

        <h1 className="text-3xl font-bold mb-6">Login</h1>

        <form autoComplete="off" className="flex flex-col gap-4">

          <input
            type="email"
            placeholder="Email"
            autoComplete="off"
            className="p-3 rounded bg-gray-800 border border-gray-700"
          />

          <input
            type="password"
            placeholder="Password"
            autoComplete="new-password"
            className="p-3 rounded bg-gray-800 border border-gray-700"
          />

          <button
            type="submit"
            className="bg-primary py-2 rounded-lg hover:opacity-90"
          >
            Sign In
          </button>

        </form>

        {/* Link to Signup */}
        <p className="text-sm text-gray-400 mt-6 text-center">
          Don't have an account? {" "}
          < a href="/signup" className="text-indigo-400 hover:underline">
           Sign Up
          </a>
        </p>

      </div>
    </div>
  )
}