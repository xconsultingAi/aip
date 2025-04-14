"use client";
import { useState, useEffect } from "react";
import { useUser, useAuth } from '@clerk/nextjs';

interface KnowledgeFile {
  id: string;
  name: string;
}

export default function FileUpload() {
  const { user } = useUser();
  const { getToken } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<KnowledgeFile[]>([]);
  const [organizationId, setOrganizationId] = useState<string | null>(null);

  // Initialize and fetch existing files
  useEffect(() => {
    const initialize = async () => {
      if (!user) return;
      
      try {
        const token = await getToken();
        
        // Fetch organization ID
        const orgRes = await fetch(`http://127.0.0.1:8000/api/users/${user.id}`, {
          method: "GET",
          headers: { Authorization: `Bearer ${token}` }
        });
        
        const orgData = await orgRes.json();
        setOrganizationId(orgData?.data.organization_id || null);

        // Fetch knowledge base files
        const filesRes = await fetch(`http://127.0.0.1:8000/api/knowledge_base`, {
          method: "GET",
          headers: { Authorization: `Bearer ${token}` }
        });

        const filesData = await filesRes.json();

        if (filesData.success && Array.isArray(filesData.data)) {
          setUploadedFiles(filesData.data.slice(0, 5).map(file => ({
            id: file.id,
            name: file.filename || file.name || "Unnamed file"
          })));
        }
      } catch (error) {
        setMessage("Failed to load files");
      }
    };

    initialize();
  }, [user, getToken]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    
    const selectedFile = e.target.files[0];
    const allowedTypes = ["application/pdf", "text/plain"];
    const maxSize = 5 * 1024 * 1024; // 5MB

    if (!allowedTypes.includes(selectedFile.type)) {
      setMessage("Only PDF and TXT files allowed");
      return;
    }

    if (selectedFile.size > maxSize) {
      setMessage("File must be smaller than 5MB");
      return;
    }

    setFile(selectedFile);
    setMessage("");
  };

  const handleUpload = async () => {
    if (!file || !organizationId) {
      setMessage("Please select a file");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const token = await getToken();
      const response = await fetch('http://127.0.0.1:8000/api/upload_knowledge_base', {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        // Add the new file to the beginning of the list
        setUploadedFiles(prev => [
          {
            id: data.id,
            name: data.filename || file.name
          },
          ...prev.slice(0, 4) // Keep only 5 most recent files
        ]);
        
        setMessage("Upload successful!");
        setFile(null);
        
        // Clear the file input
        const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
        if (fileInput) fileInput.value = "";
      } else {
        setMessage(data.error || "Upload failed");
      }
    } catch (error) {
      setMessage("Upload error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-center h-screen">
      <div className="p-6 border rounded-lg shadow-md bg-white max-w-sm w-full text-center dark:bg-gray-900">
        <h2 className="text-lg font-semibold mb-4">Upload Knowledge File</h2>
        
        <input 
          type="file" 
          accept=".pdf,.txt" 
          onChange={handleFileChange} 
          className="mb-4 w-full text-sm border p-2 rounded-lg dark:bg-gray-800"
        />
        
        <button 
          onClick={handleUpload} 
          disabled={loading || !file}
          className={`w-full p-2 rounded-lg text-white ${
            loading || !file ? "bg-gray-400 cursor-not-allowed" 
            : "bg-green-500 hover:bg-green-600"
          }`}
        >
          {loading ? "Uploading..." : "Upload"}
        </button>
        
        {message && (
          <p className={`mt-2 text-sm ${
            message.includes("success") ? "text-green-500" : "text-red-500"
          }`}>
            {message}
          </p>
        )}

        {uploadedFiles.length > 0 && (
          <div className="mt-4">
            <h3 className="font-medium mb-2">Recent Files:</h3>
            <ul className="space-y-1">
              {uploadedFiles.map((file) => (
                <li 
                  key={file.id} 
                  className="p-2 bg-gray-100 dark:bg-gray-800 rounded text-sm"
                >
                  {file.name}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}