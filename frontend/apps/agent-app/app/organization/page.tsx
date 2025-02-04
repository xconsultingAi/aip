'use client';

import { useUser,useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function OrganizationPage() {
  const { user } = useUser();
  const router = useRouter();
  const { getToken } = useAuth();
console.log(user);
  //HZ: Redirect if the user already has an organization
  useEffect(() => {
    if (user?.publicMetadata?.organization) {
      router.push('/');
    }
  }, [user, router]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const name = formData.get("organizationName") as string;
    const token = await getToken();
  
    try {
      // Send POST request with correct JSON format
      const res = await fetch("http://127.0.0.1:8000/api/organizations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({name}), // FIXED: Sending as an object
      });
  
      // Handle errors
      if (!res.ok) {
        const errorText = await res.text();
        console.error("Error response:", errorText);
        throw new Error("Failed to create organization. Server responded with an error.");
      }
  
      // Parse response
      const data = await res.json();
      console.log("Organization created successfully:", data);
  
      // Navigate after success
      router.push("/");
    } catch (error) {
      console.error("Error creating organization:", error);
    }
  };
  

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="bg-white p-6 rounded-lg shadow-lg w-full max-w-md">
        <h1 className="text-2xl font-bold text-center mb-4">Organization Details</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="text"
            name="organizationName"
            placeholder="Enter your organization name"
            required
            className="p-2 border border-gray-300 rounded-md"
          />
          <button
            type="submit"
            className="bg-green-500 text-white py-2 px-4 rounded-md hover:bg-green-600"
          >
            Submit
          </button>
        </form>
      </div>
    </div>
  );
}
