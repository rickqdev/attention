const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");

function setStatus(text) {
  statusEl.textContent = text;
}

async function detectLargestImage(tabId) {
  const [result] = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      const images = [...document.images]
        .filter((img) => img.src && img.naturalWidth > 120 && img.naturalHeight > 120)
        .map((img) => ({
          src: img.currentSrc || img.src,
          area: img.naturalWidth * img.naturalHeight,
        }))
        .sort((a, b) => b.area - a.area);
      return images[0]?.src || "";
    },
  });
  return result?.result || "";
}

async function imageUrlToBase64(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`图片下载失败：${response.status}`);
  }
  const blob = await response.blob();
  const mimeType = blob.type || "image/jpeg";
  const buffer = await blob.arrayBuffer();
  let binary = "";
  const bytes = new Uint8Array(buffer);
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return {
    base64: btoa(binary),
    mime_type: mimeType,
  };
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  return data;
}

function renderResult(payload) {
  resultEl.hidden = false;
  document.getElementById("hero").textContent = `视觉主角：${payload.intent?.hero_element || "未识别"}`;
  document.getElementById("question").textContent = `用户最想问：${payload.intent?.viewer_question || "未识别"}`;
  document.getElementById("title").textContent = payload.best_copy?.title_a || "未生成标题";
  document.getElementById("content").textContent = payload.best_copy?.content || payload.why_it_works || "";
}

document.getElementById("runButton").addEventListener("click", async () => {
  resultEl.hidden = true;
  try {
    const apiBase = document.getElementById("apiBase").value.trim().replace(/\/$/, "");
    const provider = document.getElementById("provider").value;
    const apiKey = document.getElementById("apiKey").value.trim();
    const imageOverride = document.getElementById("imageUrl").value.trim();
    const extraContext = document.getElementById("extraContext").value.trim();

    if (!apiKey) {
      setStatus("请先输入 Provider API Key。");
      return;
    }

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const imageUrl = imageOverride || (await detectLargestImage(tab.id));
    if (!imageUrl) {
      setStatus("当前页面没有找到可用图片。");
      return;
    }

    setStatus("正在抓取页面图片并分析视觉切入...");
    const image = await imageUrlToBase64(imageUrl);
    const intent = await postJson(`${apiBase}/v1/intent/analyze`, {
      schema_version: "attention.v1",
      image,
      provider,
      api_key: apiKey,
    });
    if (intent.status !== "ok") {
      setStatus(intent.error?.message || "视觉分析失败。");
      return;
    }

    setStatus("视觉切入已生成，正在继续生成图文草案...");
    const copy = await postJson(`${apiBase}/v1/copy/generate`, {
      schema_version: "attention.v1",
      intent: intent.intent,
      context: {
        subject: { name: "", source: "", price: "", notes: "" },
        supporting: [],
        scene: { location: "", time: "", feeling: "" },
        extra: extraContext,
      },
      provider,
      api_key: apiKey,
      include_viral_research: false,
      tavily_api_key: "",
    });
    if (copy.status !== "ok") {
      setStatus(copy.error?.message || "文案生成失败。");
      return;
    }

    setStatus("已完成。");
    renderResult(copy);
  } catch (error) {
    setStatus(`执行失败：${error.message}`);
  }
});
