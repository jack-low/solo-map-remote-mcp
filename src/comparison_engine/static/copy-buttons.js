(() => {
  const copyWithTextarea = (text) => {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.top = "-1000px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  };

  const copyText = async (text) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
      }
    } catch {
      // Fall through to the textarea path for browsers that gate Clipboard API writes.
    }
    copyWithTextarea(text);
  };

  const markCopied = (button) => {
    const originalLabel = button.dataset.originalLabel || button.getAttribute("aria-label") || "コピー";
    button.dataset.originalLabel = originalLabel;
    button.classList.add("is-copied");
    button.setAttribute("aria-label", "コピーしました");
    button.setAttribute("title", "コピーしました");
    window.setTimeout(() => {
      button.classList.remove("is-copied");
      button.setAttribute("aria-label", originalLabel);
      button.setAttribute("title", "コピー");
    }, 1600);
  };

  document.documentElement.dataset.copyButtonsReady = "true";
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-copy]");
    if (!button) return;
    const code = button.closest(".copy-shell")?.querySelector("code");
    if (!code) return;
    try {
      await copyText(code.innerText.trim());
      markCopied(button);
    } catch {
      button.setAttribute("aria-label", "コピーできませんでした");
      button.setAttribute("title", "コピーできませんでした");
    }
  });
})();
