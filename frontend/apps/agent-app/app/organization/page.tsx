'use client';

import { useUser, useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function OrganizationPage() {
  const { user } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  console.log({user});
  const organization_id = 1;
  const [organization, setOrganization] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const fetchOrganization = async () => {
      if (!user) return; // HZ: Ensure user is authenticated before fetching
      
      try {
        const token = await getToken();
        const res = await fetch(`http://127.0.0.1:8000/api/organizations/${organization_id}`, {
          method: "GET",
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        });

        if (!res.ok) {
          throw new Error("Failed to fetch organization details.");
        }

        const data = await res.json();
        if (data?.name) {
          setOrganization(data.name); // HZ: Store the existing organization name
        }
      } catch (error) {
        console.error("Error fetching organization:", error);
        setError(error.message);
      } finally {
        setLoading(false);
      }
    };

    fetchOrganization();
  }, [user, getToken]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const formData = new FormData(e.currentTarget);
    const name = formData.get("organizationName") as string;
    const token = await getToken();

    try {
      const res = await fetch("http://127.0.0.1:8000/api/organizations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ name }),
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || "Failed to create organization.");
      }

      const data = await res.json();
      console.log("Organization created successfully:", data);
      setOrganization(data.name); // HZ: Update state with the new organization
    } catch (error) {
      setError(error.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="bg-white p-6 rounded-lg shadow-lg w-full max-w-md">
        <h1 className="text-2xl font-bold text-center mb-4">Organization Details</h1>

        {loading ? (
          <p className="text-center">Loading...</p> // HZ: Show loading state
        ) : organization ? ( // HZ: If an organization exists, show details
          <div className="text-center">
            <p className="text-lg">You belong to <strong>{organization}</strong></p>
            <button 
              className="mt-4 bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600"
              onClick={() => router.push('/')}
            >
              Go to Dashboard
            </button>
          </div>
        ) : ( // HZ: If no organization exists, show the creation form
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <input
              type="text"
              name="organizationName"
              placeholder="Enter your organization name"
              required
              className="p-2 border border-gray-300 rounded-md"
            />
            {error && <p className="text-red-500">{error}</p>} {/* HZ: Show error messages */}
            <button
              type="submit"
              className="bg-green-500 text-white py-2 px-4 rounded-md hover:bg-green-600 disabled:opacity-50"
              disabled={loading} // HZ: Disable button while submitting
            >
              {loading ? "Submitting..." : "Submit"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
