"use client";

import React from 'react';
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button"; // Ensure this import matches your project structure

const ProfilePage = () => {
  const router = useRouter();
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Profile</h1>
      <p>Manage your account details and preferences here.</p>
      <Button
        className="mt-6 bg-blue-600 hover:bg-blue-700 px-6 py-3"
        onClick={() => router.push("/")}
      >
        ⬅️ Back to Home
      </Button>
    </div>
  );
};

export default ProfilePage;
