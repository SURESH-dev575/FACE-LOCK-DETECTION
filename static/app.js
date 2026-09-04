const video = document.getElementById("video");
const overlay = document.getElementById("overlay");
const octx = overlay.getContext("2d");
const captureCanvas = document.getElementById("captureCanvas");
const cctx = captureCanvas.getContext("2d");

const statusText = document.getElementById("statusText");
const registerBtn = document.getElementById("registerBtn");
const unlockBtn = document.getElementById("unlockBtn");
const usernameInput = document.getElementById("username");
const progressWrap = document.getElementById("progress");
const progressBar = document.getElementById("progressBar");
const logEl = document.getElementById("log");

let stream = null;
let brackets = { x: 0.3, y: 0.25, w: 0.4, h: 0.5 }; // static placeholder box (center-ish)

function log(msg) { logEl.textContent = msg; }

function setStatus(state) {
  statusText.textContent = state.toUpperCase();
  statusText.className = "status-text " + state.toLowerCase();
}

async function initCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error(
      "Camera API unavailable. Open this page via http://localhost:5000 " +
      "(not an IP address) — browsers block camera access on insecure origins."
    );
  }
  stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
  video.srcObject = stream;
  await video.play();
  overlay.width = video.videoWidth || 640;
  overlay.height = video.videoHeight || 480;
  captureCanvas.width = overlay.width;
  captureCanvas.height = overlay.height;
  drawLoop();
}

function drawBrackets(color) {
  octx.clearRect(0, 0, overlay.width, overlay.height);
  const x = brackets.x * overlay.width;
  const y = brackets.y * overlay.height;
  const w = brackets.w * overlay.width;
  const h = brackets.h * overlay.height;
  const len = 25, t = 3;
  octx.strokeStyle = color;
  octx.lineWidth = t;
  octx.beginPath();
  // top-left
  octx.moveTo(x, y); octx.lineTo(x + len, y);
  octx.moveTo(x, y); octx.lineTo(x, y + len);
  // top-right
  octx.moveTo(x + w, y); octx.lineTo(x + w - len, y);
  octx.moveTo(x + w, y); octx.lineTo(x + w, y + len);
  // bottom-left
  octx.moveTo(x, y + h); octx.lineTo(x + len, y + h);
  octx.moveTo(x, y + h); octx.lineTo(x, y + h - len);
  // bottom-right
  octx.moveTo(x + w, y + h); octx.lineTo(x + w - len, y + h);
  octx.moveTo(x + w, y + h); octx.lineTo(x + w, y + h - len);
  octx.stroke();
}

let currentColor = "#ffffff";
function drawLoop() {
  drawBrackets(currentColor);
  requestAnimationFrame(drawLoop);
}

function captureFrameB64() {
  cctx.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
  return captureCanvas.toDataURL("image/jpeg", 0.85);
}

async function registerFace() {
  registerBtn.disabled = true;
  unlockBtn.disabled = true;
  setStatus("SCANNING");
  currentColor = "#ffa940";
  progressWrap.classList.remove("hidden");

  const totalFrames = 20;
  const frames = [];
  for (let i = 0; i < totalFrames; i++) {
    frames.push(captureFrameB64());
    progressBar.style.width = `${Math.round(((i + 1) / totalFrames) * 100)}%`;
    log(`Mapping geometry: frame ${i + 1}/${totalFrames}`);
    await new Promise(r => setTimeout(r, 120));
  }

  try {
    const res = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user: usernameInput.value.trim() || "user", frames }),
    });
    const data = await res.json();
    if (data.ok) {
      currentColor = "#52ffa0";
      setStatus("SUCCESS");
      log(`Registered ${data.saved} frames for "${usernameInput.value}"`);
    } else {
      currentColor = "#ff5c5c";
      setStatus("DENIED");
      log(data.error || "Registration failed");
    }
  } catch (e) {
    currentColor = "#ff5c5c";
    setStatus("DENIED");
    log("Network error during registration");
  }

  progressWrap.classList.add("hidden");
  progressBar.style.width = "0%";
  registerBtn.disabled = false;
  unlockBtn.disabled = false;
  setTimeout(() => { currentColor = "#ffffff"; setStatus("IDLE"); }, 2000);
}

async function unlockScan() {
  registerBtn.disabled = true;
  unlockBtn.disabled = true;
  setStatus("SCANNING");
  currentColor = "#ffa940";
  log("Searching database...");

  const frame = captureFrameB64();

  try {
    const res = await fetch("/api/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frame }),
    });
    const data = await res.json();
    if (!data.ok) {
      throw new Error(data.error || "verify failed to start");
    }
    await pollStatus(data.session_id);
  } catch (e) {
    currentColor = "#ff5c5c";
    setStatus("DENIED");
    log("Network error during verification");
  }

  registerBtn.disabled = false;
  unlockBtn.disabled = false;
}

async function pollStatus(sessionId) {
  for (let i = 0; i < 60; i++) {
    const res = await fetch(`/api/status/${sessionId}`);
    const data = await res.json();

    if (data.status === "SUCCESS") {
      currentColor = "#52ffa0";
      setStatus("SUCCESS");
      log(`Unlocked as "${data.identity}" (distance ${data.distance.toFixed(3)})`);
      break;
    } else if (data.status === "DENIED") {
      currentColor = "#ff5c5c";
      setStatus("DENIED");
      log("Face not recognized");
      break;
    } else if (data.status === "SPOOF") {
      currentColor = "#ff5c5c";
      setStatus("SPOOF");
      log("Liveness failed: fake detected");
      break;
    }
    await new Promise(r => setTimeout(r, 300));
  }
  setTimeout(() => { currentColor = "#ffffff"; setStatus("IDLE"); }, 2500);
}

registerBtn.addEventListener("click", registerFace);
unlockBtn.addEventListener("click", unlockScan);

initCamera().catch(e => log("Camera access denied: " + e.message));