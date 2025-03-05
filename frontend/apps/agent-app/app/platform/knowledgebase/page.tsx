"use client";
import { useState } from "react";

export default function FileUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([
    "example1.pdf",
    "notes.txt",
    "report.pdf",
  ]); // Dummy data

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const selectedFile = event.target.files[0];

      // Enforce file type restriction
      const allowedTypes = ["application/pdf", "text/plain"];
      if (!allowedTypes.includes(selectedFile.type)) {
        setMessage("Only PDF and TXT files are allowed.");
        setFile(null);
        return;
      }

      // Enforce file size limit (5MB)
      const maxSize = 5 * 1024 * 1024;
      if (selectedFile.size > maxSize) {
        setMessage("File size must be less than 5MB.");
        setFile(null);
        return;
      }

      setFile(selectedFile);
      setMessage(""); // Clear previous messages
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setMessage("Please select a valid file.");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (response.ok) {
        setUploadedFiles((prevFiles) => [...prevFiles, file.name]); // Store the uploaded file name
        setMessage("File uploaded successfully!");
        setFile(null);
      } else {
        setMessage(data.message || "Upload failed");
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
        />
        <button 
          onClick={handleUpload} 
          className={`w-full p-2 rounded-lg text-white ${loading ? "bg-gray-400 cursor-not-allowed" : "bg-green-500 hover:bg-green-600"}`}
          disabled={loading}
        >
          {loading ? "Uploading..." : "Upload"}
        </button>
        {message && <p className="mt-2 text-sm text-red-500">{message}</p>}

        {/* Uploaded Files List */}
        {uploadedFiles.length > 0 && (
          <div className="mt-4 text-left">
            <h3 className="text-sm block font-semibold">Uploaded Files:</h3>
            <ul className="mt-2 space-y-1">
              {uploadedFiles.map((fileName, index) => (
                <li key={index} className="text-sm block p-1 bg-gray-200 rounded dark:bg-gray-800">
                  {fileName}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
