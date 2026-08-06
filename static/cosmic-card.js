/**
 * Your Cosmic Card — generator kartu 9:16 (1080x1920) gaya tarot vintage
 * untuk hasil klasifikasi astronomi.
 *
 * Sepenuhnya client-side (Canvas 2D). Gambar asli TIDAK diubah warnanya,
 * tidak difilter, tidak di-stylize — hanya di-resize + crop (cover) ke
 * dalam bingkai dekoratif.
 *
 * API publik:
 *   CosmicCard.open({ imageUrl, label, confidence, sourceType, numClasses })
 *     -> generate kartu, tampilkan modal preview + tombol download PNG.
 *   CosmicCard.generate(opts) -> Promise<HTMLCanvasElement> (tanpa modal).
 */
(function () {
  "use strict";

  var CARD_W = 1080;
  var CARD_H = 1920;

  // ---- Palet "kertas tua" -------------------------------------------------
  var PAPER_TOP = "#f0e7d4";
  var PAPER_MID = "#ece1ca";
  var PAPER_BOT = "#e5d7bc";
  var INK = "#3b3226";        // teks utama (tinta tua)
  var INK_SOFT = "#4c4232";   // body text
  var MUTED = "#7d6f56";      // label kecil
  var FAINT = "#93835f";      // disclaimer
  var GOLD = "#9a7b3f";       // ornamen emas pudar
  var GOLD_SOFT = "rgba(154, 123, 63, 0.55)";

  // ---- Nomor Romawi tetap per kelas (JANGAN diacak) -----------------------
  var NUMERALS = {
    galaxies: "I",
    galaxy: "I",
    stars: "II",
    star: "II",
    nebula: "III",
    planets: "IV",
    constellation: "V",
    cosmos_space: "VI",
  };

  // ---- Nama tampilan per kelas -------------------------------------------
  var DISPLAY_NAMES = {
    galaxies: "Galaxy",
    galaxy: "Galaxy",
    stars: "Star",
    star: "Star",
    nebula: "Nebula",
    planets: "Planet",
    constellation: "Constellation",
    cosmos_space: "Deep Space",
  };

  // ---- Penjelasan singkat terkurasi (bukan hasil AI) ----------------------
  var CARD_EXPLANATIONS = {
    galaxies:
      "A galaxy is a massive system of stars, gas, dust, and dark matter " +
      "held together by gravity. Galaxies range from dwarfs of a few " +
      "million stars to giants containing hundreds of billions.",
    galaxy:
      "A galaxy is a massive system of stars, gas, dust, and dark matter " +
      "held together by gravity. Galaxies range from dwarfs of a few " +
      "million stars to giants containing hundreds of billions.",
    stars:
      "A star is a luminous sphere of plasma powered by nuclear fusion in " +
      "its core. Stars forge the chemical elements and are the fundamental " +
      "building blocks of galaxies.",
    star:
      "A star is a luminous sphere of plasma powered by nuclear fusion in " +
      "its core. Stars forge the chemical elements and are the fundamental " +
      "building blocks of galaxies.",
    nebula:
      "A nebula is a vast interstellar cloud of gas and dust. Some nebulae " +
      "are stellar nurseries where new stars ignite; others are the " +
      "glowing remnants of stars that have died.",
    planets:
      "A planet is a celestial body orbiting a star, massive enough for " +
      "its own gravity to pull it into a near-perfect sphere and to clear " +
      "its orbital neighborhood.",
    constellation:
      "A constellation is a recognized pattern of stars in Earth's night " +
      "sky. Its stars only appear close together — in reality they may lie " +
      "hundreds of light-years apart.",
    cosmos_space:
      "A wide-field view of deep space, capturing many objects at once — " +
      "star fields, distant galaxies, and the faint glow of the cosmos as " +
      "recorded by telescopes.",
  };

  var DISCLAIMER =
    "AI classification result. This prediction is not a scientific " +
    "measurement and should not be used as professional astronomical analysis.";

  var SERIF = '"Cormorant Garamond", Georgia, serif';
  var SANS = '"Inter", "Helvetica Neue", Arial, sans-serif';

  // ========================================================================
  // Util gambar
  // ========================================================================

  function loadImage(url) {
    return new Promise(function (resolve, reject) {
      var img = new Image();
      img.onload = function () { resolve(img); };
      img.onerror = function () { reject(new Error("Gagal memuat gambar untuk kartu.")); };
      img.src = url;
    });
  }

  function loadFonts() {
    if (!document.fonts || !document.fonts.load) return Promise.resolve();
    return Promise.all([
      document.fonts.load('500 40px "Cormorant Garamond"'),
      document.fonts.load('600 96px "Cormorant Garamond"'),
      document.fonts.load('700 104px "Cormorant Garamond"'),
      document.fonts.load('400 29px "Inter"'),
      document.fonts.load('600 26px "Inter"'),
    ]).catch(function () { /* fallback ke font sistem */ });
  }

  // Gambar dimuat "cover": di-crop dari tengah, TANPA distorsi & TANPA filter.
  function drawImageCover(ctx, img, x, y, w, h) {
    var scale = Math.max(w / img.width, h / img.height);
    var sw = w / scale;
    var sh = h / scale;
    var sx = (img.width - sw) / 2;
    var sy = (img.height - sh) / 2;
    ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h);
  }

  // Teks dengan letter-spacing manual (kompatibel semua browser).
  function drawTracked(ctx, text, cx, y, tracking) {
    var chars = text.split("");
    var total = 0;
    var i;
    for (i = 0; i < chars.length; i++) {
      total += ctx.measureText(chars[i]).width;
      if (i < chars.length - 1) total += tracking;
    }
    var x = cx - total / 2;
    var prevAlign = ctx.textAlign;
    ctx.textAlign = "left";
    for (i = 0; i < chars.length; i++) {
      ctx.fillText(chars[i], x, y);
      x += ctx.measureText(chars[i]).width + tracking;
    }
    ctx.textAlign = prevAlign;
  }

  function wrapText(ctx, text, maxWidth) {
    var words = text.split(/\s+/);
    var lines = [];
    var line = "";
    for (var i = 0; i < words.length; i++) {
      var attempt = line ? line + " " + words[i] : words[i];
      if (ctx.measureText(attempt).width > maxWidth && line) {
        lines.push(line);
        line = words[i];
      } else {
        line = attempt;
      }
    }
    if (line) lines.push(line);
    return lines;
  }

  // ========================================================================
  // Ornamen
  // ========================================================================

  // Bintang 4 titik (sparkle) klasik.
  function star4(ctx, cx, cy, r, color) {
    var k = r * 0.18;
    ctx.beginPath();
    ctx.moveTo(cx, cy - r);
    ctx.quadraticCurveTo(cx + k, cy - k, cx + r, cy);
    ctx.quadraticCurveTo(cx + k, cy + k, cx, cy + r);
    ctx.quadraticCurveTo(cx - k, cy + k, cx - r, cy);
    ctx.quadraticCurveTo(cx - k, cy - k, cx, cy - r);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
  }

  // Bintang 8 titik: dua sparkle bertumpuk, satu diputar 45°.
  function star8(ctx, cx, cy, r, color) {
    star4(ctx, cx, cy, r, color);
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(Math.PI / 4);
    star4(ctx, 0, 0, r * 0.62, color);
    ctx.restore();
  }

  function diamond(ctx, cx, cy, r, color, fill) {
    ctx.beginPath();
    ctx.moveTo(cx, cy - r);
    ctx.lineTo(cx + r, cy);
    ctx.lineTo(cx, cy + r);
    ctx.lineTo(cx - r, cy);
    ctx.closePath();
    if (fill === false) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.4;
      ctx.stroke();
    } else {
      ctx.fillStyle = color;
      ctx.fill();
    }
  }

  function dot(ctx, cx, cy, r, color) {
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  }

  // ========================================================================
  // Latar kertas tua
  // ========================================================================

  function drawPaper(ctx) {
    // Dasar krem dengan gradasi halus.
    var g = ctx.createLinearGradient(0, 0, 0, CARD_H);
    g.addColorStop(0, PAPER_TOP);
    g.addColorStop(0.5, PAPER_MID);
    g.addColorStop(1, PAPER_BOT);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, CARD_W, CARD_H);

    // Bercak lembab / penuaan (blotch) — radial gradient alpha sangat rendah.
    var i;
    for (i = 0; i < 26; i++) {
      var bx = Math.random() * CARD_W;
      var by = Math.random() * CARD_H;
      var br = 90 + Math.random() * 260;
      var rg = ctx.createRadialGradient(bx, by, 0, bx, by, br);
      var dark = Math.random() < 0.6;
      var a = 0.015 + Math.random() * 0.03;
      rg.addColorStop(0, dark
        ? "rgba(122, 96, 58, " + a + ")"
        : "rgba(255, 250, 235, " + a + ")");
      rg.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = rg;
      ctx.fillRect(bx - br, by - br, br * 2, br * 2);
    }

    // Mottling frekuensi rendah: noise kecil di-upscale.
    var nW = 180, nH = 320;
    var off = document.createElement("canvas");
    off.width = nW;
    off.height = nH;
    var octx = off.getContext("2d");
    var id = octx.createImageData(nW, nH);
    for (i = 0; i < id.data.length; i += 4) {
      var v = 110 + Math.floor(Math.random() * 90);
      id.data[i] = v;
      id.data[i + 1] = v * 0.92;
      id.data[i + 2] = v * 0.78;
      id.data[i + 3] = 255;
    }
    octx.putImageData(id, 0, 0);
    ctx.save();
    ctx.globalAlpha = 0.05;
    ctx.drawImage(off, 0, 0, CARD_W, CARD_H);
    ctx.restore();

    // Speckle halus resolusi penuh (butiran kertas).
    ctx.save();
    for (i = 0; i < 2200; i++) {
      var sx = Math.random() * CARD_W;
      var sy = Math.random() * CARD_H;
      var sr = Math.random() * 1.3 + 0.3;
      ctx.globalAlpha = 0.02 + Math.random() * 0.05;
      ctx.fillStyle = Math.random() < 0.7 ? "#6d5a3c" : "#fffbef";
      ctx.fillRect(sx, sy, sr, sr);
    }
    ctx.restore();

    // Serat kertas tipis.
    ctx.save();
    ctx.globalAlpha = 0.03;
    ctx.strokeStyle = "#7a684a";
    for (i = 0; i < 60; i++) {
      var fx = Math.random() * CARD_W;
      var fy = Math.random() * CARD_H;
      var len = 18 + Math.random() * 60;
      var ang = Math.random() * Math.PI;
      ctx.lineWidth = 0.7;
      ctx.beginPath();
      ctx.moveTo(fx, fy);
      ctx.lineTo(fx + Math.cos(ang) * len, fy + Math.sin(ang) * len);
      ctx.stroke();
    }
    ctx.restore();

    // Vignette tepian menua.
    var vg = ctx.createRadialGradient(
      CARD_W / 2, CARD_H / 2, CARD_H * 0.28,
      CARD_W / 2, CARD_H / 2, CARD_H * 0.72
    );
    vg.addColorStop(0, "rgba(0,0,0,0)");
    vg.addColorStop(1, "rgba(96, 74, 42, 0.16)");
    ctx.fillStyle = vg;
    ctx.fillRect(0, 0, CARD_W, CARD_H);
  }

  // ========================================================================
  // Bingkai dekoratif kartu
  // ========================================================================

  function drawBorder(ctx) {
    // Garis luar tebal.
    ctx.strokeStyle = INK;
    ctx.lineWidth = 3;
    ctx.strokeRect(42, 42, CARD_W - 84, CARD_H - 84);

    // Garis dalam tipis.
    ctx.strokeStyle = GOLD_SOFT;
    ctx.lineWidth = 1.4;
    ctx.strokeRect(58, 58, CARD_W - 116, CARD_H - 116);

    // Ornamen sudut: bintang 8 titik + dua titik diagonal.
    var corners = [
      [50, 50, 1, 1],
      [CARD_W - 50, 50, -1, 1],
      [50, CARD_H - 50, 1, -1],
      [CARD_W - 50, CARD_H - 50, -1, -1],
    ];
    for (var i = 0; i < corners.length; i++) {
      var c = corners[i];
      star8(ctx, c[0] + c[2] * 26, c[1] + c[3] * 26, 15, GOLD);
      dot(ctx, c[0] + c[2] * 54, c[1] + c[3] * 54, 2.4, GOLD_SOFT);
      dot(ctx, c[0] + c[2] * 66, c[1] + c[3] * 66, 1.6, GOLD_SOFT);
    }

    // Wajik kecil di tengah sisi kiri & kanan.
    diamond(ctx, 50, CARD_H / 2, 8, GOLD_SOFT, false);
    diamond(ctx, CARD_W - 50, CARD_H / 2, 8, GOLD_SOFT, false);
  }

  // Divider horizontal: garis + wajik ujung + bintang tengah.
  function drawDivider(ctx, cy, halfLen, starR) {
    var cx = CARD_W / 2;
    ctx.strokeStyle = GOLD_SOFT;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(cx - halfLen, cy);
    ctx.lineTo(cx - starR - 16, cy);
    ctx.moveTo(cx + starR + 16, cy);
    ctx.lineTo(cx + halfLen, cy);
    ctx.stroke();
    diamond(ctx, cx - halfLen, cy, 5, GOLD, true);
    diamond(ctx, cx + halfLen, cy, 5, GOLD, true);
    star8(ctx, cx, cy, starR, GOLD);
  }

  // ========================================================================
  // Render kartu utama
  // ========================================================================

  /**
   * opts:
   *   imageUrl   : URL gambar asli (object URL / blob URL) — WAJIB
   *   label      : label kelas mentah dari model (mis. "nebula")
   *   confidence : 0..1
   *   sourceType : "Image" | "FITS"
   *   numClasses : jumlah kelas model (6 atau 2)
   */
  function generate(opts) {
    return Promise.all([loadImage(opts.imageUrl), loadFonts()]).then(function (res) {
      var img = res[0];
      var canvas = document.createElement("canvas");
      canvas.width = CARD_W;
      canvas.height = CARD_H;
      var ctx = canvas.getContext("2d");
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";

      var label = (opts.label || "").toLowerCase();
      var numeral = NUMERALS[label] || "✶";
      var displayName = DISPLAY_NAMES[label] || opts.label || "Unknown";
      var explanation = CARD_EXPLANATIONS[label] || "";
      var confPct = Math.min(100, opts.confidence * 100);
      var confText = confPct >= 99.95 ? "100%" : confPct.toFixed(1) + "%";

      // ---- 1. Kertas + bingkai -----------------------------------------
      drawPaper(ctx);
      drawBorder(ctx);

      ctx.textAlign = "center";
      ctx.textBaseline = "alphabetic";

      var cx = CARD_W / 2;

      // ---- 2. Nomor Romawi + judul kecil -------------------------------
      ctx.fillStyle = INK;
      ctx.font = '600 96px ' + SERIF;
      ctx.fillText(numeral, cx, 196);

      // Garis pengapit numeral.
      var numW = ctx.measureText(numeral).width;
      ctx.strokeStyle = GOLD_SOFT;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(cx - numW / 2 - 150, 166);
      ctx.lineTo(cx - numW / 2 - 40, 166);
      ctx.moveTo(cx + numW / 2 + 40, 166);
      ctx.lineTo(cx + numW / 2 + 150, 166);
      ctx.stroke();
      dot(ctx, cx - numW / 2 - 150, 166, 3, GOLD);
      dot(ctx, cx + numW / 2 + 150, 166, 3, GOLD);

      ctx.fillStyle = MUTED;
      ctx.font = '600 26px ' + SANS;
      drawTracked(ctx, "YOUR COSMIC CARD", cx, 262, 11);

      // ---- 3. Divider atas ---------------------------------------------
      drawDivider(ctx, 306, 250, 12);

      // ---- 4. Jendela gambar (fokus utama kartu) -----------------------
      var IMG_X = 134, IMG_Y = 352, IMG_W = 812, IMG_H = 800;

      // Bayangan lembut supaya gambar "duduk" di atas kertas.
      ctx.save();
      ctx.shadowColor = "rgba(60, 45, 20, 0.35)";
      ctx.shadowBlur = 26;
      ctx.shadowOffsetY = 10;
      ctx.fillStyle = "#101326";
      ctx.fillRect(IMG_X, IMG_Y, IMG_W, IMG_H);
      ctx.restore();

      // Gambar asli: hanya resize + crop tengah. Tanpa filter apa pun.
      ctx.save();
      ctx.beginPath();
      ctx.rect(IMG_X, IMG_Y, IMG_W, IMG_H);
      ctx.clip();
      drawImageCover(ctx, img, IMG_X, IMG_Y, IMG_W, IMG_H);
      ctx.restore();

      // Bingkai gambar: emas luar + tinta dalam + hairline nempel gambar.
      ctx.strokeStyle = GOLD;
      ctx.lineWidth = 3;
      ctx.strokeRect(IMG_X - 14, IMG_Y - 14, IMG_W + 28, IMG_H + 28);
      ctx.strokeStyle = INK;
      ctx.lineWidth = 1.2;
      ctx.strokeRect(IMG_X - 7, IMG_Y - 7, IMG_W + 14, IMG_H + 14);
      ctx.strokeStyle = GOLD_SOFT;
      ctx.lineWidth = 2;
      ctx.strokeRect(IMG_X - 0.5, IMG_Y - 0.5, IMG_W + 1, IMG_H + 1);

      // Aksen sudut bingkai (siku emas).
      var fx0 = IMG_X - 14, fy0 = IMG_Y - 14;
      var fx1 = IMG_X + IMG_W + 14, fy1 = IMG_Y + IMG_H + 14;
      var L = 34;
      ctx.strokeStyle = GOLD;
      ctx.lineWidth = 5;
      var cornerTicks = [
        [fx0, fy0, 1, 1], [fx1, fy0, -1, 1], [fx0, fy1, 1, -1], [fx1, fy1, -1, -1],
      ];
      for (var t = 0; t < cornerTicks.length; t++) {
        var ct = cornerTicks[t];
        ctx.beginPath();
        ctx.moveTo(ct[0] + ct[2] * L, ct[1]);
        ctx.lineTo(ct[0], ct[1]);
        ctx.lineTo(ct[0], ct[1] + ct[3] * L);
        ctx.stroke();
      }
      // Wajik kecil di tengah atas & bawah bingkai gambar.
      diamond(ctx, cx, fy0, 7, GOLD, true);
      diamond(ctx, cx, fy1, 7, GOLD, true);

      // ---- 5. Nama klasifikasi -----------------------------------------
      star4(ctx, cx, 1218, 11, GOLD);

      var title = displayName.toUpperCase();
      var titleSize = 104;
      ctx.font = "700 " + titleSize + "px " + SERIF;
      var tracking = 8;
      var titleWidth = ctx.measureText(title).width + tracking * (title.length - 1);
      if (titleWidth > 860) {
        titleSize = Math.floor(titleSize * (860 / titleWidth));
        ctx.font = "700 " + titleSize + "px " + SERIF;
      }
      ctx.fillStyle = INK;
      drawTracked(ctx, title, cx, 1316, tracking);

      // Garis bawah judul.
      ctx.strokeStyle = GOLD_SOFT;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(cx - 180, 1348);
      ctx.lineTo(cx + 180, 1348);
      ctx.stroke();
      diamond(ctx, cx - 180, 1348, 4, GOLD, true);
      diamond(ctx, cx + 180, 1348, 4, GOLD, true);

      // ---- 6. Baris statistik ------------------------------------------
      var cols = [
        { x: 250, label: "CONFIDENCE", value: confText },
        { x: 540, label: "SOURCE", value: opts.sourceType || "Image" },
        { x: 830, label: "MODEL", value: opts.numClasses + " classes" },
      ];
      for (var ci = 0; ci < cols.length; ci++) {
        ctx.fillStyle = MUTED;
        ctx.font = '600 21px ' + SANS;
        drawTracked(ctx, cols[ci].label, cols[ci].x, 1412, 5);
        ctx.fillStyle = INK;
        ctx.font = '500 42px ' + SERIF;
        ctx.fillText(cols[ci].value, cols[ci].x, 1464);
      }
      // Pemisah kolom vertikal.
      ctx.strokeStyle = GOLD_SOFT;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(395, 1396);
      ctx.lineTo(395, 1470);
      ctx.moveTo(685, 1396);
      ctx.lineTo(685, 1470);
      ctx.stroke();

      // ---- 7. Penjelasan astronomi -------------------------------------
      var expSize = 29;
      var expLineH = 44;
      ctx.font = "400 " + expSize + "px " + SANS;
      var lines = wrapText(ctx, explanation, 780);
      if (lines.length > 5) {
        expSize = 26;
        expLineH = 40;
        ctx.font = "400 " + expSize + "px " + SANS;
        lines = wrapText(ctx, explanation, 780);
      }
      var expTop = 1520;
      var expBottom = 1740;
      var blockH = (lines.length - 1) * expLineH;
      var startY = expTop + (expBottom - expTop - blockH) / 2;
      ctx.fillStyle = INK_SOFT;
      for (var li = 0; li < lines.length; li++) {
        ctx.fillText(lines[li], cx, startY + li * expLineH);
      }

      // ---- 8. Disclaimer -----------------------------------------------
      dot(ctx, cx, 1774, 2.4, GOLD_SOFT);
      dot(ctx, cx - 22, 1774, 1.6, GOLD_SOFT);
      dot(ctx, cx + 22, 1774, 1.6, GOLD_SOFT);

      ctx.fillStyle = FAINT;
      ctx.font = '400 20px ' + SANS;
      var discLines = wrapText(ctx, DISCLAIMER, 820);
      for (var di = 0; di < discLines.length; di++) {
        ctx.fillText(discLines[di], cx, 1812 + di * 30);
      }

      return canvas;
    });
  }

  // ========================================================================
  // Modal preview + download
  // ========================================================================

  var STYLE_ID = "cosmic-card-style";
  var MODAL_ID = "cosmic-card-modal";

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent =
      "#" + MODAL_ID + "{position:fixed;inset:0;z-index:1000;display:flex;" +
      "flex-direction:column;align-items:center;justify-content:center;gap:18px;" +
      "background:rgba(6,8,18,0.88);backdrop-filter:blur(6px);padding:24px;}" +
      "#" + MODAL_ID + " canvas{max-height:74vh;max-width:min(92vw,42vh);" +
      "width:auto;height:auto;border-radius:10px;" +
      "box-shadow:0 24px 80px rgba(0,0,0,0.6);}" +
      "#" + MODAL_ID + " .cc-actions{display:flex;gap:10px;}" +
      "#" + MODAL_ID + " .cc-btn{padding:12px 22px;border-radius:10px;border:none;" +
      "font-family:'Space Grotesk','Inter',sans-serif;font-weight:600;" +
      "font-size:0.9rem;cursor:pointer;}" +
      "#" + MODAL_ID + " .cc-download{background:#ffb86b;color:#0a0d1a;}" +
      "#" + MODAL_ID + " .cc-download:hover{opacity:0.9;}" +
      "#" + MODAL_ID + " .cc-close{background:transparent;color:#8b90ab;" +
      "border:1px solid #262c48;}" +
      "#" + MODAL_ID + " .cc-close:hover{color:#f2f0ea;}";
    document.head.appendChild(style);
  }

  function closeModal() {
    var modal = document.getElementById(MODAL_ID);
    if (modal) modal.remove();
    document.removeEventListener("keydown", onEsc);
  }

  function onEsc(e) {
    if (e.key === "Escape") closeModal();
  }

  function downloadCanvas(canvas, label) {
    canvas.toBlob(function (blob) {
      if (!blob) return;
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = "cosmic-card-" + (label || "result") + ".png";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
    }, "image/png");
  }

  function open(opts) {
    injectStyles();
    return generate(opts).then(function (canvas) {
      closeModal();
      var modal = document.createElement("div");
      modal.id = MODAL_ID;

      modal.appendChild(canvas);

      var actions = document.createElement("div");
      actions.className = "cc-actions";

      var dl = document.createElement("button");
      dl.className = "cc-btn cc-download";
      dl.textContent = "Download PNG (1080×1920)";
      dl.addEventListener("click", function () {
        downloadCanvas(canvas, (opts.label || "").toLowerCase());
      });

      var close = document.createElement("button");
      close.className = "cc-btn cc-close";
      close.textContent = "Tutup";
      close.addEventListener("click", closeModal);

      actions.appendChild(dl);
      actions.appendChild(close);
      modal.appendChild(actions);

      modal.addEventListener("click", function (e) {
        if (e.target === modal) closeModal();
      });
      document.addEventListener("keydown", onEsc);

      document.body.appendChild(modal);
      return canvas;
    });
  }

  window.CosmicCard = { generate: generate, open: open };
})();
