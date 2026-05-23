const state = {
  images: [],
  index: 0,
  annotation: null,
};

function currentImageName() {
  return state.images[state.index];
}

function parseCsv(value) {
  return value.split(",").map((part) => part.trim()).filter(Boolean);
}

function setStatus(message) {
  document.getElementById("status-text").textContent = message;
}

function parseAttributes(value) {
  return value.split(",").map((part) => part.trim()).filter(Boolean);
}

function createEmptyObject() {
  return { id: "", type: "target", label: "", bbox: [50, 50, 120, 80], attributes: [] };
}

function createEmptyRelation() {
  return { subject_id: "", predicate: "near", object_id: "" };
}

function syncCanvasSize() {
  const image = document.getElementById("scene-image");
  const canvas = document.getElementById("annotation-canvas");
  canvas.style.width = `${image.clientWidth}px`;
  canvas.style.height = `${image.clientHeight}px`;
}

function renderCanvasBoxes() {
  const canvas = document.getElementById("annotation-canvas");
  canvas.innerHTML = "";
  (state.annotation.objects || []).forEach((obj) => {
    const [x, y, w, h] = obj.bbox || [0, 0, 0, 0];
    const box = document.createElement("div");
    box.className = "canvas-box";
    box.dataset.type = obj.type || "target";
    box.style.left = `${x}px`;
    box.style.top = `${y}px`;
    box.style.width = `${w}px`;
    box.style.height = `${h}px`;
    box.textContent = obj.id || obj.label || obj.type || "object";
    canvas.appendChild(box);
  });
}

function renderSidebar() {
  const list = document.getElementById("image-list");
  list.innerHTML = "";
  state.images.forEach((imageName, index) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.textContent = imageName;
    button.onclick = () => loadImage(index);
    if (index === state.index) {
      button.className = "active-image";
    }
    item.appendChild(button);
    list.appendChild(item);
  });
}

function renderForm() {
  document.getElementById("scene-tags").value = (state.annotation.scene_tags || []).join(", ");
  document.getElementById("target-object-id").value = state.annotation.target_object_id || "";
  document.getElementById("notes").value = state.annotation.notes || "";
  setStatus(`Current image: ${currentImageName()}`);
}

function renderObjectList() {
  const host = document.getElementById("object-list");
  host.innerHTML = "";
  (state.annotation.objects || []).forEach((obj, index) => {
    const row = document.createElement("div");
    row.className = "object-row";
    row.innerHTML = `
      <input data-field="id" placeholder="id" value="${obj.id || ""}">
      <select data-field="type">
        <option value="target">target</option>
        <option value="distractor">distractor</option>
        <option value="landmark">landmark</option>
      </select>
      <input data-field="label" placeholder="label" value="${obj.label || ""}">
      <div class="bbox-grid">
        <input data-bbox="0" type="number" placeholder="x" value="${obj.bbox?.[0] ?? 0}">
        <input data-bbox="1" type="number" placeholder="y" value="${obj.bbox?.[1] ?? 0}">
        <input data-bbox="2" type="number" placeholder="w" value="${obj.bbox?.[2] ?? 0}">
        <input data-bbox="3" type="number" placeholder="h" value="${obj.bbox?.[3] ?? 0}">
      </div>
      <input class="attr-input" data-field="attributes" placeholder="attributes: comma,separated" value="${(obj.attributes || []).join(", ")}">
      <button class="full-row" data-action="delete" type="button">Delete</button>
    `;
    row.querySelector('[data-field="type"]').value = obj.type || "target";
    row.querySelectorAll("input[data-field], select[data-field]").forEach((element) => {
      element.onchange = () => {
        if (element.dataset.field === "attributes") {
          obj.attributes = parseAttributes(element.value);
        } else {
          obj[element.dataset.field] = element.value;
        }
        renderCanvasBoxes();
      };
    });
    row.querySelectorAll("input[data-bbox]").forEach((element) => {
      element.onchange = () => {
        const bboxIndex = Number(element.dataset.bbox);
        obj.bbox[bboxIndex] = Number(element.value);
        renderCanvasBoxes();
      };
    });
    row.querySelector('[data-action="delete"]').onclick = () => {
      state.annotation.objects.splice(index, 1);
      renderObjectList();
      renderCanvasBoxes();
    };
    host.appendChild(row);
  });
}

function renderRelationList() {
  const host = document.getElementById("relation-list");
  host.innerHTML = "";
  (state.annotation.relations || []).forEach((relation, index) => {
    const row = document.createElement("div");
    row.className = "relation-row";
    row.innerHTML = `
      <input data-field="subject_id" placeholder="subject_id" value="${relation.subject_id || ""}">
      <select data-field="predicate">
        <option value="left_of">left_of</option>
        <option value="right_of">right_of</option>
        <option value="near">near</option>
        <option value="in_front_of">in_front_of</option>
        <option value="behind">behind</option>
      </select>
      <input data-field="object_id" placeholder="object_id" value="${relation.object_id || ""}">
      <button data-action="delete" type="button">Delete</button>
    `;
    row.querySelector('[data-field="predicate"]').value = relation.predicate || "near";
    row.querySelectorAll("input[data-field], select[data-field]").forEach((element) => {
      element.onchange = () => {
        relation[element.dataset.field] = element.value;
      };
    });
    row.querySelector('[data-action="delete"]').onclick = () => {
      state.annotation.relations.splice(index, 1);
      renderRelationList();
    };
    host.appendChild(row);
  });
}

async function loadImage(index) {
  state.index = index;
  const imageName = currentImageName();
  const image = document.getElementById("scene-image");
  image.onload = () => {
    syncCanvasSize();
    renderCanvasBoxes();
  };
  image.src = `/data/images/${imageName}`;
  const response = await fetch(`/api/annotations/${imageName}`);
  state.annotation = await response.json();
  renderSidebar();
  renderForm();
  renderObjectList();
  renderRelationList();
}

async function saveAnnotation() {
  state.annotation.scene_tags = parseCsv(document.getElementById("scene-tags").value);
  state.annotation.target_object_id = document.getElementById("target-object-id").value.trim();
  state.annotation.notes = document.getElementById("notes").value;
  await fetch(`/api/annotations/${currentImageName()}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state.annotation),
  });
  setStatus(`Saved ${currentImageName()}`);
}

async function bootstrap() {
  const response = await fetch("/api/images");
  const data = await response.json();
  state.images = data.images;
  document.getElementById("save-button").onclick = saveAnnotation;
  document.getElementById("prev-button").onclick = () => loadImage(Math.max(0, state.index - 1));
  document.getElementById("next-button").onclick = () => loadImage(Math.min(state.images.length - 1, state.index + 1));
  document.getElementById("add-object-button").onclick = () => {
    state.annotation.objects.push(createEmptyObject());
    renderObjectList();
    renderCanvasBoxes();
  };
  document.getElementById("add-relation-button").onclick = () => {
    state.annotation.relations.push(createEmptyRelation());
    renderRelationList();
  };
  if (state.images.length > 0) {
    await loadImage(0);
  } else {
    setStatus("No images found.");
  }
}

bootstrap();
