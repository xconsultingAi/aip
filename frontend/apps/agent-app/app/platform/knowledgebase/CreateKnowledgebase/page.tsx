"use client";
import { useState, useEffect } from "react";
import { useUser, useAuth } from "@clerk/nextjs";

interface KnowledgeFile {
  id: string;
  name: string;
}

export default function FileUpload() {
  const { user } = useUser();
  const { getToken } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [customName, setCustomName] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<KnowledgeFile[]>([]);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [isClient, setIsClient] = useState(false);

  const [selectedFormat, setSelectedFormat] = useState("pdf");
  const [url, setUrl] = useState("");

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    const initialize = async () => {
      if (!user) return;

      try {
        const token = await getToken();

        const orgRes = await fetch(`http://127.0.0.1:8000/api/users/${user.id}`, {
          method: "GET",
          headers: { Authorization: `Bearer ${token}` },
        });

        const orgData = await orgRes.json();
        setOrganizationId(orgData?.data.organization_id || null);

        const filesRes = await fetch(`http://127.0.0.1:8000/api/org_knowledge_base`, {
          method: "GET",
          headers: { Authorization: `Bearer ${token}` },
        });

        const filesData = await filesRes.json();

        if (filesData.success && Array.isArray(filesData.data)) {
          const parsedFiles = filesData.data.slice(0, 5).map((file) => ({
            id: file.id || file.filename || file.name,
            name: file.filename || file.name || "Unnamed file",
          }));
          setUploadedFiles(parsedFiles);
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
    const maxSize = 5 * 1024 * 1024;

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
    if (selectedFormat === "pdf" || selectedFormat === "txt") {
      if (!file || !organizationId) {
        setMessage("Please select a file");
        return;
      }
    } else {
      // For URL types
      if (!url.trim() || !organizationId) {
        setMessage("Please enter a valid URL");
        return;
      }
    }

    setLoading(true);
    const formData = new FormData();

    if (selectedFormat === "pdf" || selectedFormat === "txt") {
      formData.append("file", file!);
    } else {
      formData.append("url", url.trim());
    }

    if (customName.trim()) {
      formData.append("name", customName.trim());
    }

    formData.append("kb_format", selectedFormat);
    formData.append("organization_id", organizationId!);

    try {
      const token = await getToken();
      const response = await fetch("http://127.0.0.1:8000/api/upload_knowledge_base", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        const newFile = {
          id: data.id || (file ? file.name : url),
          name: data.filename || customName || (file ? file.name : url),
        };

        setUploadedFiles((prev) => [newFile, ...prev.slice(0, 4)]);
        setMessage("Upload successful!");
        setFile(null);
        setCustomName("");
        setUrl("");

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
      <div className="p-6 border rounded-lg shadow-md bg-white max-w-sm w-full text-center dark:bg-gray-900 shadow-2xl">
        <h2 className="text-lg font-semibold mb-4">Upload Knowledge File</h2>
        
        {/* Custom Name Input */}
        <div className="mb-3 text-left">
          <label htmlFor="file-name" className="block text-sm font-medium mb-1 dark:text-white">
            File Name
          </label>
          <input
            id="file-name"
            type="text"
            placeholder="Enter a name for this file"
            value={customName}
            onChange={(e) => setCustomName(e.target.value)}
            className="w-full text-sm border p-2 rounded-lg dark:bg-gray-800"
          />
        </div>
        {/* Format Select */}
        <div className="mb-3 text-left">
          <label htmlFor="format-select" className="block text-sm font-medium mb-1 dark:text-white">
            Select Format
          </label>
          <select
            id="format-select"
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value)}
            className="w-full text-sm border p-2 rounded-lg dark:bg-gray-800"
          >
            <option value="pdf">📄 PDF</option>
            <option value="txt">📃 TXT</option>
            <option value="youtube">🎥 YouTube</option>
            <option value="website">🌐 Website</option>
          </select>
        </div>

        {/* Conditional Input: File or URL */}
        {(selectedFormat === "pdf" || selectedFormat === "txt") && (
          <div className="mb-4 text-left">
            <label htmlFor="file-upload" className="block text-sm font-medium mb-1 dark:text-white">
              Select File <small>(PDF or TXT)</small>
            </label>
            <input
              id="file-upload"
              type="file"
              accept=".pdf,.txt"
              onChange={handleFileChange}
              className="w-full text-sm border p-2 rounded-lg dark:bg-gray-800"
            />
          </div>
        )}

        {(selectedFormat === "youtube" || selectedFormat === "website") && (
          <div className="mb-4 text-left">
            <label htmlFor="url-input" className="block text-sm font-medium mb-1 dark:text-white">
              Enter URL
            </label>
            <input
              id="url-input"
              type="url"
              placeholder={`Enter ${selectedFormat === "youtube" ? "YouTube" : "Website"} URL`}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full text-sm border p-2 rounded-lg dark:bg-gray-800"
            />
          </div>
        )}

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={loading || ((selectedFormat === "pdf" || selectedFormat === "txt") && !file) || ((selectedFormat === "youtube" || selectedFormat === "website") && !url.trim())}
          className={`w-full p-2 rounded-lg text-white ${
            loading ? "bg-gray-400 cursor-not-allowed" : "bg-green-500 hover:bg-green-600"
          }`}
        >
          {loading ? "Uploading..." : "Upload"}
        </button>

        {/* Message */}
        {message && (
          <p
            className={`mt-2 text-sm ${
              message.toLowerCase().includes("success") ? "text-green-500" : "text-red-500"
            }`}
          >
            {message}
          </p>
        )}
      </div>
    </div>
  );
}
