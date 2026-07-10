/* AgriBot – Farmer Profile JS */

document.addEventListener("DOMContentLoaded", () => {
  loadProfile();
  document.getElementById("saveProfileBtn")?.addEventListener("click", saveProfile);
});

async function loadProfile() {
  try {
    const data = await apiFetch("/api/profile/");
    if (data && data.name) {
      setVal("pName",      data.name);
      setVal("pVillage",   data.village);
      setVal("pDistrict",  data.district);
      setVal("pState",     data.state);
      setVal("pFarmSize",  data.farm_size);
      setVal("pSoilType",  data.soil_type);
      setVal("pMainCrop",  data.main_crop);
      setVal("pIrrigation",data.irrigation);
    }
  } catch (_) {}
}

async function saveProfile() {
  const payload = {
    name:       document.getElementById("pName")?.value,
    village:    document.getElementById("pVillage")?.value,
    district:   document.getElementById("pDistrict")?.value,
    state:      document.getElementById("pState")?.value,
    farm_size:  document.getElementById("pFarmSize")?.value,
    soil_type:  document.getElementById("pSoilType")?.value,
    main_crop:  document.getElementById("pMainCrop")?.value,
    irrigation: document.getElementById("pIrrigation")?.value,
  };

  if (!payload.name) { showToast("Name is required", "warning"); return; }

  try {
    await apiFetch("/api/profile/save", {
      method: "POST", body: JSON.stringify(payload),
    });
    const alertEl = document.getElementById("profileSaveAlert");
    if (alertEl) {
      alertEl.classList.remove("d-none");
      setTimeout(() => alertEl.classList.add("d-none"), 3000);
    }
  } catch (err) {
    showToast("Save failed: " + err.message, "danger");
  }
}

function setVal(id, val) {
  const el = document.getElementById(id);
  if (!el || val == null) return;
  el.value = val;
}
