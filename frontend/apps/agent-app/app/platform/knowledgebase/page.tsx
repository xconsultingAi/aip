"use client";
import { useState, useEffect } from "react";
import { useUser, useAuth } from '@clerk/nextjs';

interface KnowledgeFile {
  id: string;
  name: string;
  // HZ: Define interface for knowledge base file structure
}

export default function FileUpload() {
  const { user } = useUser();
  const { getToken } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<KnowledgeFile[]>([]);
  const [organizationId, setOrganizationId] = useState<string | null>(null);

  // HZ: Initialize organization context and fetch existing files on component mount
  useEffect(() => {
    const initialize = async () => {
      if (!user) return;
      
      try {
        const token = await getToken();
        console.log(token);
        // HZ: Fetch organization ID from user's metadata
        const orgRes = await fetch(`http://127.0.0.1:8000/api/users/${user?.id}`, {
          method: "GET",
          headers: { Authorization: `Bearer ${token}` }
        });
        const orgData = await orgRes.json();
        console.log(orgData?.data.organization_id);
        
        setOrganizationId(orgData?.data.organization_id || null);

        // HZ: Load existing knowledge base files from API
      const filesRes = await fetch(`http://127.0.0.1:8000/api/knowledge_base`, {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` }
      });

      const filesData = await filesRes.json();

      if (filesData.success && Array.isArray(filesData.data)) {
        //HZ: Limit to the latest 5 files
        const formattedFiles = filesData.data.slice(0, 5).map(file => ({
          id: file.id,
          name: file.filename //HZ: Ensure correct property mapping
        }));

        setUploadedFiles(formattedFiles);
      } else {
        setMessage("No files found in knowledge base.");
      }
    } catch (error) {
      setMessage("Failed to load existing files.");
    }
  };

    initialize();
  }, [user, getToken]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const selectedFile = event.target.files[0];

      // HZ: Enforce supported file types (PDF and TXT only)
      const allowedTypes = ["application/pdf", "text/plain"];
      if (!allowedTypes.includes(selectedFile.type)) {
        setMessage("Only PDF and TXT files are allowed.");
        setFile(null);
        return;
      }

      // HZ: Implement size restriction (5MB max)
      const maxSize = 5 * 1024 * 1024;
      if (selectedFile.size > maxSize) {
        setMessage("File size must be less than 5MB.");
        setFile(null);
        return;
      }

      setFile(selectedFile);
      setMessage(""); // HZ: Clear previous error messages
    }
  };

  const handleUpload = async () => {
    if (!file || !organizationId) {
      setMessage("Please select a valid file and ensure organization access");
      return;
    }
  
    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("organization_id", organizationId); //HZ: Ensure organization ID is sent
  
    try {
      const token = await getToken();
      const response = await fetch('http://127.0.0.1:8000/api/Upload_knowledge_base', {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData, //HZ: No need to set Content-Type manually
      });
  
      const data = await response.json();
      if (response.ok) {
        //HZ: Ensure `prev` is always an array
        setUploadedFiles(prev => (Array.isArray(prev) ? [...prev, data] : [data]));
        setMessage("File added to knowledge base successfully!");
        setFile(null);
      } else {
        setMessage(data.error || "Upload failed");
      }
    } catch (error) {
      setMessage("An error occurred during upload.");
    } finally {
      setLoading(false);
    }
  };
  
  

  return (
    <div className="flex justify-center items-center h-screen">
      <div className="p-6 border rounded-lg shadow-md bg-white max-w-sm w-full text-center dark:bg-gray-900">
        <input 
          type="file" 
          accept=".pdf,.txt" 
          onChange={handleFileChange} 
          className="mb-4 w-full text-sm border p-2 rounded-lg dark:bg-gray-800"
          // HZ: Explicitly specify allowed file types
        />
        <button 
          onClick={handleUpload} 
          className={`w-full p-2 rounded-lg text-white ${loading ? "bg-gray-400 cursor-not-allowed" : "bg-green-500 hover:bg-green-600"}`}
          disabled={loading}
        >
          {loading ? "Uploading..." : "Upload"} {/* HZ: Dynamic button text */}
        </button>
        {message && <p className="mt-2 text-sm text-red-500">{message}</p>}

        {/* HZ: Display uploaded files list with organization context */}
        {uploadedFiles.length > 0 && (
          <div className="mt-4 text-left">
            <h3 className="text-sm block font-semibold">Knowledge Base Files:</h3>
            <ul className="mt-2 space-y-1">
              {uploadedFiles.map((file, index) => (
                <li 
                  key={file.id || index} 
                  className="text-sm block p-1 bg-gray-200 rounded dark:bg-gray-800"
                >
                  {file.name}
                  {/* HZ: File metadata can be added here */}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}