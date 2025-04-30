(function () {
  const agentId = document.currentScript.getAttribute("data-agent");
  const greeting = encodeURIComponent(document.currentScript.getAttribute("data-greeting") || "Hello!");
  const color = encodeURIComponent(document.currentScript.getAttribute("data-color") || "#22c55e");

  const iframe = document.createElement("iframe");
  iframe.src = `https://localhost/embed-chat?agent=${agentId}&greeting=${greeting}&color=${color}`;
  iframe.style.border = "none";
  iframe.style.position = "fixed";
  iframe.style.bottom = "20px";
  iframe.style.right = "20px";
  iframe.style.width = "350px";
  iframe.style.height = "500px";
  iframe.style.borderRadius = "12px";
  iframe.style.zIndex = "9999";
  iframe.allow = "clipboard-write";

  document.body.appendChild(iframe);
})();
