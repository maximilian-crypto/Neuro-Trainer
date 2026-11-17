// Eigener Stapel-Viewer: int16-HU-Volumen, Fensterung per LUT im Canvas.
// Volumenachsen [z, y, x]; z=0 kaudal. Angezeigt wird "von unten nach oben" wie am Befundplatz:
// Mausrad nach unten = nächste Schicht kranial.

const PRESETS = [
  { key: "1", name: "Hirn", w: 80, l: 40 },
  { key: "2", name: "Subdural", w: 200, l: 80 },
  { key: "3", name: "Schlaganfall", w: 40, l: 40 },
  { key: "4", name: "Knochen", w: 2800, l: 600 },
];

// Maskencodes (preprocess/common.py CATEGORIES): 1 EDH, 2 SDH, 3 SAH, 4 IVH, 5 IPH
const MASK_COLORS = {
  1: [255, 80, 80], 2: [255, 170, 0], 3: [80, 200, 255], 4: [180, 120, 255], 5: [80, 255, 120],
};

class StackViewer {
  constructor(canvas, onChange) {
    this.cv = canvas;
    this.ctx = canvas.getContext("2d");
    this.onChange = onChange || (() => {});
    this.off = document.createElement("canvas");
    this.offCtx = this.off.getContext("2d");
    this.vol = null; this.mask = null; this.showMask = false;
    this.w = 80; this.l = 40;
    this.z = 0; this.zoom = 1; this.panX = 0; this.panY = 0;
    this.lut = new Uint8Array(4096);
    this.hover = null;
    this._buildLut();
    this._bind();
    new ResizeObserver(() => this._resize()).observe(canvas);
  }

  load(vol, shape, spacing, mask) {
    this.vol = vol; this.shape = shape; this.spacing = spacing; this.mask = mask || null;
    const [, ny, nx] = shape;
    this.off.width = nx; this.off.height = ny;
    this.img = this.offCtx.createImageData(nx, ny);
    this.z = Math.floor(shape[0] / 2);
    this.resetView();
  }

  resetView() { this.zoom = 1; this.panX = 0; this.panY = 0; this.draw(); }

  setWindow(w, l) { this.w = Math.max(1, w); this.l = l; this._buildLut(); this.draw(); }

  setSlice(z) {
    if (!this.vol) return;
    this.z = Math.max(0, Math.min(this.shape[0] - 1, z));
    this.draw();
  }

  _buildLut() {
    const lo = this.l - this.w / 2;
    for (let i = 0; i < 4096; i++) {
      const v = ((i - 1024) - lo) / this.w;
      this.lut[i] = v <= 0 ? 0 : v >= 1 ? 255 : Math.round(v * 255);
    }
  }

  _resize() {
    const r = this.cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    this.cv.width = Math.round(r.width * dpr); this.cv.height = Math.round(r.height * dpr);
    this.draw();
  }

  // Bildtransformation: Volumenpixel -> Canvaspixel
  _xf() {
    const [, ny, nx] = this.shape;
    const base = Math.min(this.cv.width / nx, this.cv.height / ny);
    const s = base * this.zoom;
    const dpr = window.devicePixelRatio || 1;
    const ox = (this.cv.width - nx * s) / 2 + this.panX * dpr;
    const oy = (this.cv.height - ny * s) / 2 + this.panY * dpr;
    return { s, ox, oy };
  }

  canvasToVoxel(clientX, clientY) {
    const r = this.cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    const { s, ox, oy } = this._xf();
    const x = ((clientX - r.left) * dpr - ox) / s, y = ((clientY - r.top) * dpr - oy) / s;
    return { x: Math.floor(x), y: Math.floor(y) };
  }

  huAt(x, y) {
    const [, ny, nx] = this.shape;
    if (x < 0 || y < 0 || x >= nx || y >= ny) return null;
    return this.vol[this.z * ny * nx + y * nx + x];
  }

  draw() {
    const ctx = this.ctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = "#000"; ctx.fillRect(0, 0, this.cv.width, this.cv.height);
    if (!this.vol) return;
    const [, ny, nx] = this.shape, n = nx * ny, base = this.z * n;
    const px = this.img.data, vol = this.vol, lut = this.lut;
    const m = this.showMask && this.mask ? this.mask : null;
    for (let i = 0, j = 0; i < n; i++, j += 4) {
      let hu = vol[base + i] + 1024;
      hu = hu < 0 ? 0 : hu > 4095 ? 4095 : hu;
      const g = lut[hu];
      if (m && m[base + i]) {
        const c = MASK_COLORS[m[base + i]] || [255, 0, 0];
        px[j] = (g + c[0]) >> 1; px[j + 1] = (g + c[1]) >> 1; px[j + 2] = (g + c[2]) >> 1;
      } else { px[j] = px[j + 1] = px[j + 2] = g; }
      px[j + 3] = 255;
    }
    this.offCtx.putImageData(this.img, 0, 0);
    const { s, ox, oy } = this._xf();
    ctx.imageSmoothingEnabled = this.zoom < 3;
    ctx.drawImage(this.off, ox, oy, nx * s, ny * s);
    this.onChange(this);
  }

  _bind() {
    const cv = this.cv;
    cv.addEventListener("contextmenu", (e) => e.preventDefault());
    cv.addEventListener("wheel", (e) => {
      e.preventDefault();
      if (!this.vol) return;
      if (e.ctrlKey || e.metaKey) {
        const f = Math.exp(-e.deltaY * 0.0015);
        this._zoomAt(e.clientX, e.clientY, f);
      } else {
        this.setSlice(this.z + (e.deltaY > 0 ? 1 : -1));
      }
    }, { passive: false });
    let drag = null;
    cv.addEventListener("mousedown", (e) => {
      drag = { b: e.button, x: e.clientX, y: e.clientY, panX: this.panX, panY: this.panY, w: this.w, l: this.l };
    });
    window.addEventListener("mouseup", () => { drag = null; });
    window.addEventListener("mousemove", (e) => {
      if (this.vol && e.target === cv) {
        const v = this.canvasToVoxel(e.clientX, e.clientY);
        this.hover = { ...v, hu: this.huAt(v.x, v.y) };
        this.onChange(this);
      }
      if (!drag) return;
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (drag.b === 0 || drag.b === 1) {
        this.panX = drag.panX + dx; this.panY = drag.panY + dy; this.draw();
      } else if (drag.b === 2) {
        const k = Math.max(1, drag.w / 200);
        this.setWindow(Math.round(drag.w + dx * k), Math.round(drag.l + dy * k * 0.5));
      }
    });
  }

  _zoomAt(clientX, clientY, f) {
    const r = this.cv.getBoundingClientRect();
    const nz = Math.max(0.5, Math.min(12, this.zoom * f));
    f = nz / this.zoom;
    // Punkt unter dem Cursor fixieren (CSS-Pixel relativ zur Canvasmitte)
    const cx = clientX - r.left - r.width / 2, cy = clientY - r.top - r.height / 2;
    this.panX = cx - (cx - this.panX) * f; this.panY = cy - (cy - this.panY) * f;
    this.zoom = nz; this.draw();
  }
}
