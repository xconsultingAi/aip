"use client";

import { useState } from "react";
import { useUser, useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

export default function FileUpload() {
  const { user } = useUser();
  const { getToken } = useAuth();

  // File upload states
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [kbFormat, setKbFormat] = useState("pdf");
  const [textContent, setTextContent] = useState(""); // For TXT format
  const [youtubeUrl, setYoutubeUrl] = useState(""); // For YouTube format

  // Website scraping states
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [depth, setDepth] = useState(1);
  const [includeLinks, setIncludeLinks] = useState(false);

  // General UI states
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    setFile(e.target.files[0]);
  };

  // Upload file to backend
  const handleUpload = async () => {
    if (!name.trim() || !kbFormat) {
      setMessage("Please fill all required fields.");
      return;
    }

    // Format-specific validation
    if (kbFormat === "txt" && !textContent.trim()) {
      setMessage("Please enter text content.");
      return;
    }

    if (kbFormat === "youtube" && !youtubeUrl.trim()) {
      setMessage("Please enter a YouTube URL.");
      return;
    }

    if (["pdf", "docx", "html", "csv", "xls", "xlsx"].includes(kbFormat) && !file) {
      setMessage("Please select a file to upload.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const token = await getToken();
      let res: Response;
      let data: any;

      if (kbFormat === "txt") {
        // Handle text content submission to /api/add_text
        res = await fetch("http://127.0.0.1:8000/api/add_text", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: name.trim(),
            content: textContent,
          }),
        });
        data = await res.json();
      } else if (kbFormat === "youtube") {
        // Handle YouTube URL submission to /api/add_youtube
        res = await fetch("http://127.0.0.1:8000/api/add_youtube", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: name.trim(),
            url: youtubeUrl.trim(),
          }),
        });
        data = await res.json();
      } else {
        // Handle file upload to /api/upload_knowledge_base
        const formData = new FormData();
        formData.append("file", file!);
        formData.append("name", name.trim());
        formData.append("kb_format", kbFormat);

        res = await fetch("http://127.0.0.1:8000/api/upload_knowledge_base", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });
        data = await res.json();
      }

      if (res.ok) {
        setMessage("✅ Upload successful!");
        router.push("/platform/knowledgebase/");
      } else {
        setMessage(`❌ Error: ${data.detail || "Upload failed"}`);
      }
    } catch (error) {
      console.error("Upload error:", error);
      setMessage("❌ Upload failed. Server error.");
    } finally {
      setLoading(false);
    }
  };

  // Scrape website content
  const handleWebsiteScrape = async () => {
    if (!name.trim() || !websiteUrl.trim()) {
      setMessage("Please enter both a name and a website URL.");
      return;
    }

    // Basic URL validation
    try {
      new URL(websiteUrl);
    } catch {
      setMessage("Please enter a valid URL.");
      return;
    }

    if (depth < 1) {
      setMessage("Depth must be at least 1.");
      return;
    }

    setLoading(true);
    setMessage("");

    const payload = {
      name: name.trim(),
      url: websiteUrl.trim(),
      depth,
      include_links: includeLinks,
    };

    try {
      const token = await getToken();
      const res = await fetch("http://127.0.0.1:8000/api/add_url", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (res.ok) {
        setMessage("✅ Website content added successfully!");
        router.push("/platform/knowledgebase/");
      } else {
        setMessage(`❌ Error: ${data.detail || "Failed to add website content."}`);
      }
    } catch (error) {
      console.error("Website scrape error:", error);
      setMessage("❌ Request failed. Server error.");
    } finally {
      setLoading(false);
    }
  };

  // Render appropriate input fields based on selected format
  const renderFormatSpecificFields = () => {
    switch (kbFormat) {
      case "website":
        return (
          <>
            <label className="block mt-4 mb-1 text-sm font-medium">Website URL</label>
            <input
              type="url"
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              className="w-full border p-2 rounded-md dark:bg-gray-800 mb-3"
              placeholder="https://example.com"
            />

            <label className="block text-sm font-medium mb-1">Depth</label>
            <input
              type="number"
              min={1}
              max={5}
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              className="w-full border p-2 rounded-md dark:bg-gray-800 mb-3"
            />

            <div className="flex items-center mb-4">
              <input
                type="checkbox"
                checked={includeLinks}
                onChange={(e) => setIncludeLinks(e.target.checked)}
                className="mr-2"
                id="includeLinksCheckbox"
              />
              <label htmlFor="includeLinksCheckbox" className="text-sm">
                Include links
              </label>
            </div>

            <button
              onClick={handleWebsiteScrape}
              disabled={loading}
              className={`w-full p-2 text-white rounded-md ${
                loading ? "bg-gray-400 cursor-not-allowed" : "bg-green-600 hover:bg-green-700"
              }`}
            >
              {loading ? "Scraping..." : "Scrape Website"}
            </button>
          </>
        );

      case "txt":
        return (
          <>
            <label className="block mt-4 mb-1 text-sm font-medium">Text Content</label>
            <textarea
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              className="w-full border p-2 rounded-md dark:bg-gray-800 h-40"
              placeholder="Enter your text content here..."
            />
            <button
              onClick={handleUpload}
              disabled={loading}
              className={`w-full mt-4 p-2 text-white rounded-md ${
                loading ? "bg-gray-400 cursor-not-allowed" : "bg-green-600 hover:bg-green-700"
              }`}
            >
              {loading ? "Uploading..." : "Upload Text"}
            </button>
          </>
        );

      case "youtube":
        return (
          <>
            <label className="block mt-4 mb-1 text-sm font-medium">YouTube URL</label>
            <input
              type="url"
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              className="w-full border p-2 rounded-md dark:bg-gray-800 mb-3"
              placeholder="https://www.youtube.com/watch?v=..."
            />
            <button
              onClick={handleUpload}
              disabled={loading}
              className={`w-full p-2 text-white rounded-md ${
                loading ? "bg-gray-400 cursor-not-allowed" : "bg-green-600 hover:bg-green-700"
              }`}
            >
              {loading ? "Processing..." : "Add YouTube Video"}
            </button>
          </>
        );

      default:
        return (
          <>
            <label className="block mt-4 mb-1 text-sm font-medium">Upload File</label>
            <input
              type="file"
              accept={
                kbFormat === "pdf" ? ".pdf" :
                kbFormat === "docx" ? ".docx" :
                kbFormat === "html" ? ".html" :
                kbFormat === "csv" ? ".csv" :
                kbFormat === "xls" ? ".xls" :
                kbFormat === "xlsx" ? ".xlsx" : ""
              }
              onChange={handleFileChange}
              className="w-full"
            />
            <button
              onClick={handleUpload}
              disabled={loading}
              className={`w-full mt-4 p-2 text-white rounded-md ${
                loading ? "bg-gray-400 cursor-not-allowed" : "bg-green-600 hover:bg-green-700"
              }`}
            >
              {loading ? "Uploading..." : "Upload File"}
            </button>
          </>
        );
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-6 border rounded-lg shadow-lg bg-white dark:bg-gray-900">
      <h2 className="text-lg font-semibold mb-4 text-center">Upload Knowledge Base</h2>

      {/* KB Name */}
      <div className="mb-4">
        <label className="block mb-1 text-sm font-medium">Knowledge Base Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border p-2 rounded-md dark:bg-gray-800"
          placeholder="My KB File or Website Name"
        />
      </div>

      {/* KB Format Select */}
      <div className="mb-4">
        <label className="block mb-1 text-sm font-medium">Select Format</label>
        <select
          value={kbFormat}
          onChange={(e) => setKbFormat(e.target.value)}
          className="w-full border p-2 rounded-md dark:bg-gray-800"
        >
          <option value="pdf">PDF</option>
          <option value="docx">DOCX</option>
          <option value="html">HTML</option>
          <option value="csv">CSV</option>
          <option value="xls">XLS</option>
          <option value="xlsx">XLSX</option>
          <option value="txt">TXT (Direct Text)</option>
          <option value="youtube">YouTube</option>
          <option value="website">Website</option>
        </select>
      </div>

      {/* Render format-specific fields */}
      {renderFormatSpecificFields()}

      {/* Message */}
      {message && (
        <p className="mt-4 text-center text-sm text-red-600 dark:text-red-400 whitespace-pre-wrap">{message}</p>
      )}
    </div>
  );
}