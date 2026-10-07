// What Teamtailor's own scripts do to the form, cut to the parts the filler reads (chunk-GCY5JIOQ, 2026-10-07):
// the drop box draws a hidden file box after load, a chosen file shows its name + gets its link (window.CAP: too
// big -> the page's error words), the phone box marks a short number invalid, the address box offers places after
// 3 letters + 500 ms and keeps the picked one's id, a requirement answered no shows the form's message, the
// slider's number box moves the slider (onNrInputInput). Nothing leaves the page; Submit only sets a flag.
const PLACES = ["Springfield, IL, USA", "Springfield, MO, USA", "Shelbyville, IL, USA"];
// shown = "hidden" class dropped; the page leaves aria-hidden as it was (the qualifying message keeps "true")
const show = (e, on) => e.classList.toggle("hidden", !on);

setTimeout(() => {
  for (const box of document.querySelectorAll('[data-controller~="forms--inputs--upload"]')) {
    const label = box.querySelector("label[for]");
    const input = Object.assign(document.createElement("input"), { type: "file", id: label.htmlFor });
    input.style.display = "none";
    box.querySelector('[data-forms--inputs--upload-target="trigger"]').append(input);
    input.addEventListener("change", () => {
      const file = input.files[0], error = box.querySelector('[data-forms--inputs--upload-target="errorContainer"]');
      if (window.CAP && file.size > window.CAP) {
        error.querySelector('[data-forms--inputs--upload-target="errorMsg"]').textContent = "File is too big (max 1MB)";
        error.classList.remove("hidden");
        return;
      }
      const preview = box.querySelector('[data-forms--inputs--upload-target="templatePreview"]').content.cloneNode(true);
      preview.querySelector("[data-dz-name]").textContent = file.name;
      box.querySelector('[data-forms--inputs--upload-target="previewsContainer"]').append(preview);
      setTimeout(() => {
        const shown = box.querySelector('[data-forms--inputs--upload-target="previewsContainer"]');
        shown.querySelector("[data-progress]").remove();
        shown.querySelector('[data-forms--inputs--upload-preview-target="name"]').classList.remove("hidden");
        const url = shown.querySelector('[data-forms--inputs--upload-preview-target="urlInput"]');
        url.disabled = false;
        url.value = "https://uploads.example/" + file.name;
      }, 300);
    });
  }
}, 200);

const phone = document.querySelector('input[name="candidate[phone]"]');
phone && phone.addEventListener("blur", () =>
  phone.setAttribute("aria-invalid", phone.value.replace(/\D/g, "").length < 8 ? "true" : "false"));

const where = document.querySelector('input[name="candidate[location][query]"]');
if (where) {
  const box = where.closest('[data-controller~="forms--inputs--location"]');
  const list = box.querySelector('[data-forms--inputs--location-target="suggestionsList"]');
  const kept = box.querySelector('input[name="candidate[location][place_id]"]');
  let timer;
  where.addEventListener("input", () => {
    kept.value = "";
    clearTimeout(timer);
    list.innerHTML = "";
    if (where.value.length < 3) return;
    timer = setTimeout(() => {
      if (window.PLACES_DOWN) {  // the suggestions request failed (blocked, offline): the page's own words
        box.querySelector('[data-forms--inputs--location-target="errorText"]').textContent =
          box.getAttribute("data-forms--inputs--location-error-fetching-suggestions-value");
        return;
      }
      for (const [i, place] of PLACES.entries()) {
        if (!place.toLowerCase().startsWith(where.value.split(",")[0].toLowerCase().trim())) continue;
        const b = Object.assign(document.createElement("button"), { type: "button", textContent: place });
        b.setAttribute("role", "option");
        b.dataset.placeId = "place-" + i;
        b.addEventListener("click", () => setTimeout(() => {
          kept.value = b.dataset.placeId;
          where.value = place;
          list.innerHTML = "";
        }, 150));
        list.append(b);
      }
      show(box.querySelector('[data-forms--inputs--location-target="suggestionsContainer"]'), true);
      show(list, true);
    }, 500);
  });
}

for (const radio of document.querySelectorAll('[data-controller~="questions--qualifying--boolean"]')) {
  radio.addEventListener("click", () =>
    show(document.querySelector('[data-careersite--form-target="qualifyingMessageWrapper"]'), radio.value === "false"));
}

for (const range of document.querySelectorAll('[data-controller~="forms--inputs--range"]')) {
  const nr = range.querySelector('input[name="range-custom_number"]'), slider = range.querySelector("input[type=range]");
  const min = +range.dataset.formsInputsRangeMinValue, max = +range.dataset.formsInputsRangeMaxValue;
  nr.addEventListener("input", () => {
    let t = nr.value || min || 0;
    if (t < min) t = min;
    if (t > max) t = max;
    slider.value = t;
    nr.value = t;
    slider.dispatchEvent(new Event("change"));
  });
}

document.querySelector("#job-application-form").addEventListener("submit", e => { e.preventDefault(); window.submitted = true; });
