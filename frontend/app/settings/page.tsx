"use client";

import { useState, useEffect } from "react";
import { Eye, EyeOff, Settings } from "lucide-react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("account");
  const [showPassword, setShowPassword] = useState(false);
  const [userAvatar, setUserAvatar] = useState<string | null>(null);

  useEffect(() => {
    const avatar = localStorage.getItem("userAvatar");
    if (avatar) setUserAvatar(avatar);
  }, []);

   return (
    <div className="min-h-screen bg-[#0F172A] text-white px-10 py-8">
      {/* HEADER */}
      <div className="flex items-center gap-3 border-b border-gray-500 pb-4 mb-8">
        <Settings className="w-8 h-8" />
        <h1 className="text-4xl font-black tracking-widest">USER SETTINGS</h1>
      </div>

      <div className="grid grid-cols-[300px_1fr] gap-12">
        {/* LEFT SIDEBAR */}
        <div className="space-y-5">
          <button
            onClick={() => setActiveTab("account")}
            className="w-full rounded-full bg-gray-500 py-5 text-xl font-black tracking-wide hover:bg-gray-400 transition"
          >
            ACCOUNT DETAILS
          </button>

          <button
            onClick={() => setActiveTab("security")}
            className="w-full rounded-full bg-gray-500 py-5 text-xl font-black tracking-wide hover:bg-gray-400 transition"
          >
            DATA AND SECURITY
          </button>

          <button
            onClick={() => setActiveTab("privacy")}
            className="w-full rounded-full bg-gray-500 py-5 text-xl font-black tracking-wide hover:bg-gray-400 transition"
          >
            PRIVACY SETTINGS
          </button>
        </div>
        {/* RIGHT CONTENT */}
        <div>
          {activeTab === "account" && (
            <div className="space-y-10">
              <h2 className="text-5xl font-black tracking-wide">PERSONAL DETAILS</h2>

              <div className="space-y-8 text-3xl">
                <div className="flex items-center gap-5">
                  <span className="font-black">EMAIL:</span>
                  <span className="text-gray-300">grgsupriyaa890@gmail.com</span>
                </div>

                <div className="flex items-center gap-5">
                  <span className="font-black">PASSWORD:</span>
                  <span className="text-gray-300">
                    {showPassword ? "meeple123" : "********"}
                  </span>
                  <button onClick={() => setShowPassword(!showPassword)}>
                    {showPassword ? <EyeOff /> : <Eye />}
                  </button>
                </div>

                <div className="flex items-center gap-5">
                  <span className="font-black">USERNAME:</span>
                  <span className="text-gray-300">MeepleTeam</span>
                </div>

                {userAvatar && (
                  <div className="flex items-center gap-5">
                    <span className="font-black">AVATAR:</span>
                    <img
                      src={userAvatar}
                      alt="avatar"
                      className="w-20 h-20 rounded-full object-cover border-2 border-indigo-400"
                    />
                  </div>
                )}
                 </div>
            </div>
          )}

          {activeTab === "security" && (
            <div className="space-y-12">
              <div className="flex items-center justify-between text-2xl">
                <span>Enable Multifactor Authentication</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" defaultChecked />
                  <div className="w-16 h-8 bg-red-400 rounded-full peer peer-checked:bg-red-500 after:content-[''] after:absolute after:top-1 after:left-1 after:bg-white after:w-6 after:h-6 after:rounded-full after:transition-all peer-checked:after:translate-x-8"></div>
                </label>
              </div>

              <div className="flex gap-10 mt-16">
                <button className="rounded-full bg-red-700 px-8 py-3 text-lg font-bold hover:bg-red-600 transition">
                  Clear Game Data
                </button>

                <button className="rounded-full bg-red-700 px-8 py-3 text-lg font-bold hover:bg-red-600 transition">
                  Delete Account
                </button>
              </div>
            </div>
          )}
          {activeTab === "privacy" && (
            <div className="space-y-8 text-2xl">
              {[
                "Allow Chats From Non-Friended Users",
                "Allow Friend Requests From Non-Game Group Users",
                "Mature Language Filter",
              ].map((item) => (
                <div key={item} className="flex items-center justify-between">
                  <span>{item}</span>

                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked />
                    <div className="w-16 h-8 bg-red-400 rounded-full peer peer-checked:bg-red-500 after:content-[''] after:absolute after:top-1 after:left-1 after:bg-white after:w-6 after:h-6 after:rounded-full after:transition-all peer-checked:after:translate-x-8"></div>
                  </label>
                </div>
              ))}

              <div className="mt-10 rounded-3xl bg-red-700 h-56 flex items-start justify-center pt-6 text-3xl font-black tracking-wide">
                BLOCKED ACCOUNTS
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}