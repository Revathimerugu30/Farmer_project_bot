/* AgriBot – Pest Detection JS */

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("detectPestBtn")?.addEventListener("click", detectPest);

  // Dropzone click to open file picker
  const dropzone = document.getElementById("pestDropzone");
  const input    = document.getElementById("pestImage");
  if (dropzone) {
    dropzone.addEventListener("click", () => input?.click());
    dropzone.addEventListener("dragover",  e => { e.preventDefault(); dropzone.classList.add("drag-over"); });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
    dropzone.addEventListener("drop", e => {
      e.preventDefault(); dropzone.classList.remove("drag-over");
      if (e.dataTransfer.files[0]) { input.files = e.dataTransfer.files; showPreview(e.dataTransfer.files[0]); }
    });
  }
  if (input) input.addEventListener("change", () => { if (input.files[0]) showPreview(input.files[0]); });
});

function showPreview(file) {
  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById("pestPreviewImg").src = e.target.result;
    document.getElementById("pestImagePreview").classList.remove("d-none");
  };
  reader.readAsDataURL(file);
}

async function detectPest() {
  const cropName = document.getElementById("pestCropName")?.value;
  const symptoms = document.getElementById("pestSymptoms")?.value;
  const imageInput = document.getElementById("pestImage");

  const spinner = document.getElementById("pestSpinner");
  const btn     = document.getElementById("detectPestBtn");
  spinner?.classList.remove("d-none");
  if (btn) btn.disabled = true;

  const resultEl = document.getElementById("pestResult");
  if (resultEl) resultEl.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-danger"></div><p class="mt-2 text-muted">Analyzing symptoms…</p></div>';

  try {
    const formData = new FormData();
    formData.append("crop_name", cropName || "");
    formData.append("symptoms", symptoms || "");
    if (imageInput?.files[0]) formData.append("image", imageInput.files[0]);

    const res = await fetch("/api/pest/detect", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Detection failed");
    if (resultEl) resultEl.innerHTML = renderMarkdown(data.diagnosis);
  } catch (err) {
    if (resultEl) resultEl.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
  } finally {
    spinner?.classList.add("d-none");
    if (btn) btn.disabled = false;
  }
}
