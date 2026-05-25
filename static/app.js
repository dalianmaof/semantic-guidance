// ===== Global Error Handler for Observability =====
window.onerror = function (message, source, lineno, colno, error) {
  console.error("Unhandled JS Error:", message, "at", source, ":", lineno);
  const errMsg = `${message} (${(source || "").split("/").pop()}:${lineno}:${colno})`;
  try {
    showToast(`JS 错误: ${errMsg}`, "error");
  } catch (e) {}
  try {
    const el = document.getElementById("status-text");
    if (el) {
      el.textContent = `JS 错误: ${errMsg}`;
      el.style.color = "#f87171";
    }
  } catch (e) {}
  return false;
};

// ===== State =====
const state = {
  images: [],
  index: 0,
  annotation: null,
  selectedObjectIndex: -1,
  tool: "draw",  // "draw" | "select"
  drawing: false,
  drawStart: null,
  annotationStatus: {}, // imageName -> "done" | "partial" | ""
  isSaved: true,
};

// ===== Drag State =====
const drag = {
  active: false,
  type: "", // "move" | "resize"
  index: -1,
  startX: 0,
  startY: 0,
  startBbox: null,
};

// ===== Utilities =====
function currentImageName() {
  return state.images[state.index];
}

function parseCsv(value) {
  return value.split(",").map((s) => s.trim()).filter(Boolean);
}

// ===== Toast Notifications =====
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const icons = { success: "✅", error: "❌", info: "ℹ️" };
  toast.innerHTML = `<span>${icons[type] || ""}</span> ${message}`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// ===== Section Collapse =====
function toggleSection(id) {
  document.getElementById(id).classList.toggle("collapsed");
}

// ===== Controls Enable/Disable =====
function setControlsEnabled(enabled) {
  const ids = [
    "prev-button", "next-button", "save-button", "footer-save-button",
    "scene-tags", "target-object-id", "notes",
    "add-object-button", "add-relation-button",
  ];
  for (const id of ids) {
    const el = document.getElementById(id);
    if (el) el.disabled = !enabled;
  }
}

function setStatus(message) {
  document.getElementById("status-text").textContent = message;
}

// ===== Progress Tracking =====
function checkAnnotationStatus(annotation) {
  if (!annotation) return "";
  const hasObjects = (annotation.objects || []).length > 0;
  const hasTarget = !!annotation.target_object_id;
  if (hasObjects && hasTarget) return "done";
  if (hasObjects || hasTarget || (annotation.scene_tags || []).length > 0) return "partial";
  return "";
}

async function loadAllProgress() {
  for (const imageName of state.images) {
    try {
      const resp = await fetch(`/api/annotations/${imageName}`);
      const data = await resp.json();
      state.annotationStatus[imageName] = checkAnnotationStatus(data);
    } catch {
      state.annotationStatus[imageName] = "";
    }
  }
  renderSidebar();
  updateProgressBar();
}

function updateProgressBar() {
  const total = state.images.length;
  const done = Object.values(state.annotationStatus).filter((s) => s === "done").length;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  document.getElementById("progress-fill").style.width = `${pct}%`;
  document.getElementById("progress-text").textContent = `已完成 ${done}/${total} (${pct}%)`;
}

// ===== Guide Steps =====
function updateGuide() {
  if (!state.annotation) return;
  const objCount = (state.annotation.objects || []).length;
  const hasTarget = !!state.annotation.target_object_id;
  const hasRelations = (state.annotation.relations || []).length > 0;
  const hasTags = (state.annotation.scene_tags || []).length > 0;

  const steps = [
    { done: objCount > 0, text: "第1步：在图片上拖拽鼠标画框，标注场景中的对象" },
    { done: hasTarget, text: "第2步：在右侧设置对象类型、ID，并选择真实目标" },
    { done: hasRelations || hasTags, text: "第3步：添加对象间的空间关系和场景标签" },
    { done: state.isSaved, text: state.isSaved ? "第4步：标注已成功保存到本地！" : '第4步：确认无误后点击"保存"' },
  ];

  let currentStep = 0;
  for (let i = 0; i < steps.length; i++) {
    const el = document.getElementById(`guide-step-${i + 1}`);
    if (steps[i].done) {
      el.className = "guide-step done";
      currentStep = i + 1;
    } else {
      el.className = "guide-step" + (i === currentStep ? " active" : "");
    }
  }

  const guideText = steps[Math.min(currentStep, steps.length - 1)].text;
  document.getElementById("guide-text").textContent = guideText;
}

// ===== Canvas / Image Sync =====
function syncCanvasSize() {
  const image = document.getElementById("scene-image");
  const canvas = document.getElementById("annotation-canvas");
  canvas.style.width = `${image.clientWidth}px`;
  canvas.style.height = `${image.clientHeight}px`;
}

function getImageScale() {
  const img = document.getElementById("scene-image");
  if (!img.naturalWidth) return 1;
  return img.clientWidth / img.naturalWidth;
}

// ===== Canvas Box Rendering =====
function renderCanvasBoxes() {
  const canvas = document.getElementById("annotation-canvas");
  canvas.innerHTML = "";
  if (!state.annotation) return;
  const scale = getImageScale();

  (state.annotation.objects || []).forEach((obj, idx) => {
    const [x, y, w, h] = obj.bbox || [0, 0, 0, 0];
    const box = document.createElement("div");
    box.className = "canvas-box" + (idx === state.selectedObjectIndex ? " selected" : "");
    box.dataset.type = obj.type || "target";
    box.dataset.index = idx;
    box.style.left = `${x * scale}px`;
    box.style.top = `${y * scale}px`;
    box.style.width = `${w * scale}px`;
    box.style.height = `${h * scale}px`;

    const label = document.createElement("span");
    label.className = "box-label";
    label.textContent = obj.id || obj.label || obj.type || "对象";
    box.appendChild(label);

    box.addEventListener("click", (e) => {
      e.stopPropagation();
      selectObject(idx);
    });

    // In Select tool mode, bind mouse drag-to-move listener
    if (state.tool === "select") {
      box.addEventListener("mousedown", (e) => {
        if (e.button !== 0) return; // Only left mouse button
        e.stopPropagation();
        e.preventDefault();

        selectObject(idx);

        drag.active = true;
        drag.type = "move";
        drag.index = idx;
        drag.startX = e.clientX;
        drag.startY = e.clientY;
        drag.startBbox = [...obj.bbox];
      });

      // If selected, add resize handle at bottom-right corner and bind drag-to-resize
      if (idx === state.selectedObjectIndex) {
        const handle = document.createElement("div");
        handle.className = "resize-handle";
        box.appendChild(handle);

        handle.addEventListener("mousedown", (e) => {
          if (e.button !== 0) return; // Only left mouse button
          e.stopPropagation();
          e.preventDefault();

          drag.active = true;
          drag.type = "resize";
          drag.index = idx;
          drag.startX = e.clientX;
          drag.startY = e.clientY;
          drag.startBbox = [...obj.bbox];
        });
      }
    }

    canvas.appendChild(box);
  });
}

// ===== Object Selection =====
function selectObject(index) {
  state.selectedObjectIndex = index;
  renderCanvasBoxes();
  renderObjectList();
  // Scroll the selected card into view
  const cards = document.querySelectorAll(".object-card");
  if (cards[index]) {
    cards[index].scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

// ===== Sidebar Rendering =====
function renderSidebar() {
  const list = document.getElementById("image-list");
  list.innerHTML = "";
  state.images.forEach((imageName, index) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    const statusDot = document.createElement("span");
    const status = state.annotationStatus[imageName] || "";
    statusDot.className = `status-dot ${status}`;
    button.appendChild(statusDot);
    const nameSpan = document.createElement("span");
    nameSpan.textContent = imageName;
    button.appendChild(nameSpan);
    button.onclick = () => loadImage(index);
    if (index === state.index) button.className = "active-image";
    item.appendChild(button);
    list.appendChild(item);
  });
}

// ===== Form Rendering =====
function renderForm() {
  document.getElementById("scene-tags").value = (state.annotation.scene_tags || []).join(", ");
  document.getElementById("notes").value = state.annotation.notes || "";
  document.getElementById("current-image-name").textContent = currentImageName();
  setStatus(`当前: ${currentImageName()}`);
  updateTargetSelect();
  updateGuide();
}

function updateTargetSelect() {
  const select = document.getElementById("target-object-id");
  const currentVal = state.annotation.target_object_id || "";
  select.innerHTML = '<option value="">（选择真实目标）</option>';
  (state.annotation.objects || []).forEach((obj) => {
    if (obj.id) {
      const opt = document.createElement("option");
      opt.value = obj.id;
      opt.textContent = `${obj.id} (${obj.type} — ${obj.label || "?"})`;
      if (obj.id === currentVal) opt.selected = true;
      select.appendChild(opt);
    }
  });
}

// ===== Object List Rendering =====
function renderObjectList() {
  const host = document.getElementById("object-list");
  host.innerHTML = "";
  const objects = state.annotation.objects || [];
  document.getElementById("object-count").textContent = objects.length;

  if (objects.length === 0) {
    host.innerHTML = '<div class="empty-state"><div class="icon">📦</div>还没有标注对象<br>在图上拖拽画框来添加</div>';
    return;
  }

  objects.forEach((obj, index) => {
    const card = document.createElement("div");
    card.className = `object-card is-${obj.type || "target"}${index === state.selectedObjectIndex ? " selected" : ""}`;
    card.onclick = () => selectObject(index);

    // Header
    const header = document.createElement("div");
    header.className = "object-card-header";
    header.innerHTML = `
      <span class="type-badge ${obj.type || "target"}">${obj.type || "target"}</span>
      <span class="obj-id">${obj.id || "(未命名)"}</span>
      <button class="delete-btn" title="删除" data-index="${index}">✕</button>
    `;
    header.querySelector(".delete-btn").onclick = (e) => {
      e.stopPropagation();
      state.annotation.objects.splice(index, 1);
      if (state.selectedObjectIndex >= objects.length - 1) {
        state.selectedObjectIndex = Math.max(-1, objects.length - 2);
      }
      state.isSaved = false;
      renderAll();
    };
    card.appendChild(header);

    // Fields
    const fields = document.createElement("div");
    fields.innerHTML = `
      <div class="field-row">
        <div class="form-group">
          <label class="form-label">ID</label>
          <input class="form-input" data-field="id" value="${obj.id || ""}" placeholder="如 tank_1">
        </div>
        <div class="form-group">
          <label class="form-label">类型</label>
          <select class="form-select" data-field="type">
            <option value="target" ${obj.type === "target" ? "selected" : ""}>target 目标</option>
            <option value="distractor" ${obj.type === "distractor" ? "selected" : ""}>distractor 干扰</option>
            <option value="landmark" ${obj.type === "landmark" ? "selected" : ""}>landmark 地标</option>
          </select>
        </div>
      </div>
      <div class="field-row">
        <div class="form-group">
          <label class="form-label">标签</label>
          <input class="form-input" data-field="label" value="${obj.label || ""}" placeholder="如 tank, hangar">
        </div>
        <div class="form-group">
          <label class="form-label">属性</label>
          <input class="form-input" data-field="attributes" value="${(obj.attributes || []).join(", ")}" placeholder="left, near_road">
        </div>
      </div>
      <div class="bbox-display">bbox: [${(obj.bbox || [0, 0, 0, 0]).join(", ")}]</div>
    `;

    // Bind field change handlers
    fields.querySelectorAll("input[data-field], select[data-field]").forEach((el) => {
      el.addEventListener("change", () => {
        if (el.dataset.field === "attributes") {
          obj.attributes = parseCsv(el.value);
        } else {
          obj[el.dataset.field] = el.value;
        }
        state.isSaved = false;
        renderCanvasBoxes();
        updateTargetSelect();
        updateGuide();
        // Update card styling
        card.className = `object-card is-${obj.type || "target"}${index === state.selectedObjectIndex ? " selected" : ""}`;
        header.querySelector(".type-badge").className = `type-badge ${obj.type}`;
        header.querySelector(".type-badge").textContent = obj.type;
        header.querySelector(".obj-id").textContent = obj.id || "(未命名)";
      });
      // Stop click propagation on inputs
      el.addEventListener("click", (e) => e.stopPropagation());
    });

    card.appendChild(fields);
    host.appendChild(card);
  });
}

// ===== Relation List Rendering =====
function renderRelationList() {
  const host = document.getElementById("relation-list");
  host.innerHTML = "";
  const relations = state.annotation.relations || [];
  document.getElementById("relation-count").textContent = relations.length;

  if (relations.length === 0) {
    host.innerHTML = '<div class="empty-state"><div class="icon">🔗</div>还没有空间关系<br>点击下方按钮添加</div>';
    return;
  }

  const objectIds = (state.annotation.objects || []).map((o) => o.id).filter(Boolean);

  relations.forEach((rel, index) => {
    const card = document.createElement("div");
    card.className = "relation-card";

    // Subject select
    const subSelect = document.createElement("select");
    subSelect.className = "form-select";
    subSelect.innerHTML = '<option value="">主体</option>' +
      objectIds.map((id) => `<option value="${id}" ${rel.subject_id === id ? "selected" : ""}>${id}</option>`).join("");
    subSelect.onchange = () => { rel.subject_id = subSelect.value; state.isSaved = false; updateGuide(); };

    // Predicate select
    const predSelect = document.createElement("select");
    predSelect.className = "form-select";
    const predicates = ["left_of", "right_of", "near", "in_front_of", "behind"];
    const predicateLabels = { left_of: "在…左侧", right_of: "在…右侧", near: "靠近", in_front_of: "在…前方", behind: "在…后方" };
    predSelect.innerHTML = predicates.map((p) =>
      `<option value="${p}" ${rel.predicate === p ? "selected" : ""}>${p} ${predicateLabels[p]}</option>`
    ).join("");
    predSelect.onchange = () => { rel.predicate = predSelect.value; state.isSaved = false; updateGuide(); };

    // Object select
    const objSelect = document.createElement("select");
    objSelect.className = "form-select";
    objSelect.innerHTML = '<option value="">客体</option>' +
      objectIds.map((id) => `<option value="${id}" ${rel.object_id === id ? "selected" : ""}>${id}</option>`).join("");
    objSelect.onchange = () => { rel.object_id = objSelect.value; state.isSaved = false; updateGuide(); };

    // Delete button
    const delBtn = document.createElement("button");
    delBtn.className = "delete-btn";
    delBtn.textContent = "✕";
    delBtn.onclick = () => {
      state.annotation.relations.splice(index, 1);
      state.isSaved = false;
      renderRelationList();
      updateGuide();
    };

    card.appendChild(subSelect);
    card.appendChild(predSelect);
    card.appendChild(objSelect);
    card.appendChild(delBtn);
    host.appendChild(card);
  });
}

// ===== Combined Render =====
function renderAll() {
  renderCanvasBoxes();
  renderForm();
  renderObjectList();
  renderRelationList();
}

// ===== Mouse Drawing on Canvas =====
function setupDrawing() {
  const panel = document.getElementById("canvas-panel");

  function getCanvasCoords(e) {
    const rect = panel.getBoundingClientRect();
    const scale = getImageScale();
    return {
      x: (e.clientX - rect.left) / scale,
      y: (e.clientY - rect.top) / scale,
    };
  }

  panel.addEventListener("mousedown", (e) => {
    if (state.tool !== "draw" || !state.annotation || e.button !== 0) return;
    e.preventDefault();
    const coords = getCanvasCoords(e);
    state.drawing = true;
    state.drawStart = coords;

    // Create preview element
    const preview = document.createElement("div");
    preview.id = "draw-preview";
    preview.className = "draw-preview";
    const scale = getImageScale();
    preview.style.left = `${coords.x * scale}px`;
    preview.style.top = `${coords.y * scale}px`;
    preview.style.width = "0px";
    preview.style.height = "0px";
    document.getElementById("annotation-canvas").appendChild(preview);
  });

  window.addEventListener("mousemove", (e) => {
    if (!state.drawing) return;
    const coords = getCanvasCoords(e);
    const preview = document.getElementById("draw-preview");
    if (!preview) return;

    const scale = getImageScale();
    const x = Math.min(state.drawStart.x, coords.x);
    const y = Math.min(state.drawStart.y, coords.y);
    const w = Math.abs(coords.x - state.drawStart.x);
    const h = Math.abs(coords.y - state.drawStart.y);

    preview.style.left = `${x * scale}px`;
    preview.style.top = `${y * scale}px`;
    preview.style.width = `${w * scale}px`;
    preview.style.height = `${h * scale}px`;
  });

  window.addEventListener("mouseup", (e) => {
    if (!state.drawing) return;
    state.drawing = false;

    const preview = document.getElementById("draw-preview");
    if (preview) preview.remove();

    const coords = getCanvasCoords(e);
    const x = Math.round(Math.min(state.drawStart.x, coords.x));
    const y = Math.round(Math.min(state.drawStart.y, coords.y));
    const w = Math.round(Math.abs(coords.x - state.drawStart.x));
    const h = Math.round(Math.abs(coords.y - state.drawStart.y));

    // Ignore tiny accidental clicks (threshold: 10px in natural coords)
    if (w < 10 || h < 10) return;

    // Auto-increment ID
    const existingIds = (state.annotation.objects || []).map((o) => o.id).filter(Boolean);
    let autoId = "";
    for (let i = 1; i <= 100; i++) {
      const candidate = `obj_${i}`;
      if (!existingIds.includes(candidate)) { autoId = candidate; break; }
    }

    const newObj = {
      id: autoId,
      type: "target",
      label: "",
      bbox: [x, y, w, h],
      attributes: [],
    };
    state.annotation.objects.push(newObj);
    state.selectedObjectIndex = state.annotation.objects.length - 1;
    state.isSaved = false;

    renderAll();
    showToast(`已添加对象框 [${x}, ${y}, ${w}, ${h}]`, "info");
  });
}

// ===== Mouse Dragging (Move/Resize) on Canvas =====
function setupDragging() {
  window.addEventListener("mousemove", (e) => {
    if (!drag.active || !state.annotation || drag.index === -1) return;
    e.preventDefault();

    const obj = state.annotation.objects[drag.index];
    if (!obj) return;

    const scale = getImageScale();
    const dxNatural = (e.clientX - drag.startX) / scale;
    const dyNatural = (e.clientY - drag.startY) / scale;

    const img = document.getElementById("scene-image");
    const maxW = img.naturalWidth || 1000;
    const maxH = img.naturalHeight || 1000;

    if (drag.type === "move") {
      let newX = Math.round(drag.startBbox[0] + dxNatural);
      let newY = Math.round(drag.startBbox[1] + dyNatural);

      // Keep box fully inside the image boundaries
      newX = Math.max(0, Math.min(newX, maxW - drag.startBbox[2]));
      newY = Math.max(0, Math.min(newY, maxH - drag.startBbox[3]));

      obj.bbox = [newX, newY, drag.startBbox[2], drag.startBbox[3]];
    } else if (drag.type === "resize") {
      let newW = Math.round(drag.startBbox[2] + dxNatural);
      let newH = Math.round(drag.startBbox[3] + dyNatural);

      // Limit minimum size to 10px
      newW = Math.max(10, newW);
      newH = Math.max(10, newH);

      // Limit maximum size to remain within image boundary
      newW = Math.min(newW, maxW - drag.startBbox[0]);
      newH = Math.min(newH, maxH - drag.startBbox[1]);

      obj.bbox = [drag.startBbox[0], drag.startBbox[1], newW, newH];
    }

    // Smoothly update box coordinates on canvas in real-time
    const boxEl = document.querySelector(`.canvas-box[data-index="${drag.index}"]`);
    if (boxEl) {
      boxEl.style.left = `${obj.bbox[0] * scale}px`;
      boxEl.style.top = `${obj.bbox[1] * scale}px`;
      boxEl.style.width = `${obj.bbox[2] * scale}px`;
      boxEl.style.height = `${obj.bbox[3] * scale}px`;
    }

    // Update coordinate text in object card if it is open
    const cards = document.querySelectorAll(".object-card");
    if (cards[drag.index]) {
      const bboxDisplay = cards[drag.index].querySelector(".bbox-display");
      if (bboxDisplay) {
        bboxDisplay.textContent = `bbox: [${obj.bbox.join(", ")}]`;
      }
    }
  });

  window.addEventListener("mouseup", (e) => {
    if (!drag.active) return;

    const obj = state.annotation.objects[drag.index];
    if (obj) {
      const moved = obj.bbox[0] !== drag.startBbox[0] ||
                    obj.bbox[1] !== drag.startBbox[1] ||
                    obj.bbox[2] !== drag.startBbox[2] ||
                    obj.bbox[3] !== drag.startBbox[3];
      if (moved) {
        state.isSaved = false;
        showToast(`已修改对象框 [${obj.bbox.join(", ")}]`, "info");
      }
    }

    drag.active = false;
    drag.index = -1;

    // Re-render everything once drag ends to sync select inputs, guides, etc.
    renderAll();
  });
}

// ===== Load / Save =====
async function loadImage(index) {
  setControlsEnabled(false);
  setStatus("加载中...");
  state.index = index;
  state.selectedObjectIndex = -1;
  const imageName = currentImageName();

  const image = document.getElementById("scene-image");
  image.onload = () => {
    syncCanvasSize();
    renderCanvasBoxes();
  };
  image.onerror = () => {
    console.error("Failed to load image:", image.src);
    showToast(`加载图片失败，请确保该文件存在: data/images/${imageName}`, "error");
    setStatus("图片加载失败");
  };
  image.src = `/data/images/${imageName}`;

  try {
    const response = await fetch(`/api/annotations/${imageName}`);
    state.annotation = await response.json();
  } catch (err) {
    showToast(`加载标注失败: ${err.message}`, "error");
    state.annotation = {
      image: `data/images/${imageName}`,
      scene_id: imageName.replace(/\.[^.]+$/, ""),
      scene_tags: [],
      target_object_id: "",
      objects: [],
      relations: [],
      notes: "",
    };
  }

  state.isSaved = true;
  renderSidebar();
  renderAll();
  setControlsEnabled(true);
  setStatus(`当前: ${currentImageName()}`);

  // Scroll active sidebar item into view
  const activeBtn = document.querySelector("#image-list .active-image");
  if (activeBtn) activeBtn.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function saveAnnotation() {
  if (!state.annotation) {
    showToast("标注数据尚未加载", "error");
    return;
  }

  // Sync form values
  state.annotation.scene_tags = parseCsv(document.getElementById("scene-tags").value);
  state.annotation.target_object_id = document.getElementById("target-object-id").value;
  state.annotation.notes = document.getElementById("notes").value;

  // Client-side validation
  const objects = state.annotation.objects || [];
  const ids = objects.map((o) => o.id).filter(Boolean);
  if (ids.length !== new Set(ids).size) {
    showToast("对象 ID 存在重复，请修正", "error");
    return;
  }

  const targetId = state.annotation.target_object_id;
  if (targetId && !ids.includes(targetId)) {
    showToast("真实目标 ID 不在对象列表中", "error");
    return;
  }

  try {
    const resp = await fetch(`/api/annotations/${currentImageName()}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.annotation),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${resp.status}`);
    }
    state.annotationStatus[currentImageName()] = checkAnnotationStatus(state.annotation);
    state.isSaved = true;
    updateProgressBar();
    renderSidebar();
    updateGuide();
    showToast(`${currentImageName()} 保存成功 ✓`, "success");
    setStatus(`已保存: ${currentImageName()}`);
  } catch (err) {
    showToast(`保存失败: ${err.message}`, "error");
  }
}

// ===== Tool Switching =====
function setTool(tool) {
  state.tool = tool;
  document.getElementById("tool-draw").classList.toggle("active", tool === "draw");
  document.getElementById("tool-select").classList.toggle("active", tool === "select");
  const panel = document.getElementById("canvas-panel");
  panel.classList.toggle("drawing", tool === "draw");
  panel.classList.toggle("selecting", tool === "select");
  renderCanvasBoxes();
}

// ===== Keyboard Shortcuts =====
function setupKeyboard() {
  document.addEventListener("keydown", (e) => {
    // Don't interfere with input fields
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") {
      if (e.key === "Escape") e.target.blur();
      return;
    }

    if (e.key === "d" || e.key === "D") {
      setTool("draw");
    } else if (e.key === "s" && !e.ctrlKey) {
      setTool("select");
    } else if (e.key === "s" && e.ctrlKey) {
      e.preventDefault();
      saveAnnotation();
    } else if (e.key === "Delete" || e.key === "Backspace") {
      if (state.selectedObjectIndex >= 0 && state.annotation) {
        state.annotation.objects.splice(state.selectedObjectIndex, 1);
        state.selectedObjectIndex = -1;
        state.isSaved = false;
        renderAll();
        showToast("已删除选中对象", "info");
      }
    } else if (e.key === "ArrowLeft") {
      if (state.index > 0) loadImage(state.index - 1);
    } else if (e.key === "ArrowRight") {
      if (state.index < state.images.length - 1) loadImage(state.index + 1);
    }
  });

  // Ctrl+S anywhere (including in inputs)
  document.addEventListener("keydown", (e) => {
    if (e.key === "s" && e.ctrlKey) {
      e.preventDefault();
      saveAnnotation();
    }
  });
}

// ===== Resize Handler =====
function setupResize() {
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      syncCanvasSize();
      renderCanvasBoxes();
    }, 100);
  });
}

// ===== Bootstrap =====
async function bootstrap() {
  setControlsEnabled(false);
  setStatus("正在加载图片列表...");

  try {
    const response = await fetch("/api/images");
    const data = await response.json();
    state.images = data.images;
  } catch (err) {
    showToast("无法连接服务器", "error");
    setStatus("连接失败");
    return;
  }

  // Bind buttons
  document.getElementById("save-button").onclick = saveAnnotation;
  document.getElementById("footer-save-button").onclick = saveAnnotation;
  document.getElementById("prev-button").onclick = () => {
    if (state.index > 0) loadImage(state.index - 1);
  };
  document.getElementById("next-button").onclick = () => {
    if (state.index < state.images.length - 1) loadImage(state.index + 1);
  };
  document.getElementById("add-object-button").onclick = () => {
    if (!state.annotation) return;
    const existingIds = (state.annotation.objects || []).map((o) => o.id).filter(Boolean);
    let autoId = "";
    for (let i = 1; i <= 100; i++) {
      const candidate = `obj_${i}`;
      if (!existingIds.includes(candidate)) { autoId = candidate; break; }
    }
    state.annotation.objects.push({
      id: autoId,
      type: "target",
      label: "",
      bbox: [50, 50, 120, 80],
      attributes: [],
    });
    state.selectedObjectIndex = state.annotation.objects.length - 1;
    renderAll();
  };
  document.getElementById("add-relation-button").onclick = () => {
    if (!state.annotation) return;
    state.annotation.relations.push({ subject_id: "", predicate: "near", object_id: "" });
    renderRelationList();
    updateGuide();
  };
  document.getElementById("tool-draw").onclick = () => setTool("draw");
  document.getElementById("tool-select").onclick = () => setTool("select");

  // Scene tags change handler
  document.getElementById("scene-tags").onchange = function () {
    if (state.annotation) {
      state.annotation.scene_tags = parseCsv(this.value);
      state.isSaved = false;
      updateGuide();
    }
  };

  // Target select change handler
  document.getElementById("target-object-id").onchange = function () {
    if (state.annotation) {
      state.annotation.target_object_id = this.value;
      state.isSaved = false;
      updateGuide();
    }
  };

  // Notes change handler
  document.getElementById("notes").onchange = function () {
    if (state.annotation) {
      state.annotation.notes = this.value;
      state.isSaved = false;
      updateGuide();
    }
  };

  // Setup interactions
  setupDrawing();
  setupDragging();
  setupKeyboard();
  setupResize();

  if (state.images.length > 0) {
    await loadImage(0);
    // Load progress in background
    loadAllProgress();
  } else {
    setStatus("data/images 中未找到图片");
    showToast("未找到任何图片文件", "error");
  }
}

bootstrap();
