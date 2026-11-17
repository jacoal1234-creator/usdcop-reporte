/* Escena 3D de la portada: la TRM histórica como una cinta de luz que se abre en el cono de pronóstico.
   Recibe los datos ya cargados de data/trm.csv y data/cono.csv. Si WebGL no está disponible, no hace nada. */
window.initHero3D = function (el, hist, cono, onHover) {
  if (!window.THREE || !el) return;
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch (e) { return; }
  const W = () => el.clientWidth, H = () => el.clientHeight;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(W(), H());
  el.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x0b0e1f, 14, 34);
  const cam = new THREE.PerspectiveCamera(38, W() / H(), 0.1, 100);
  cam.position.set(4, 3.2, 15);

  // ----- escalas -----
  const vals = hist.map(d => d.v).concat(cono.map(d => d.p97_5), cono.map(d => d.p2_5));
  const vmin = Math.min(...vals), vmax = Math.max(...vals);
  const N = hist.length + cono.length;
  const X = i => -9 + (i / (N - 1)) * 18;
  const Y = v => -2.2 + ((v - vmin) / (vmax - vmin)) * 5.2;

  const group = new THREE.Group();
  scene.add(group);

  // piso: grilla de puntos
  const gp = [];
  for (let x = -12; x <= 12; x += 0.6) for (let z = -8; z <= 6; z += 0.6) gp.push(x, -2.8, z);
  const gg = new THREE.BufferGeometry();
  gg.setAttribute("position", new THREE.Float32BufferAttribute(gp, 3));
  group.add(new THREE.Points(gg, new THREE.PointsMaterial({ color: 0x3a4080, size: 0.045 })));

  // cinta histórica (tubo)
  const pts = hist.map((d, i) => new THREE.Vector3(X(i), Y(d.v), 0));
  const curve = new THREE.CatmullRomCurve3(pts);
  const tube = new THREE.Mesh(
    new THREE.TubeGeometry(curve, Math.min(900, pts.length * 2), 0.055, 8, false),
    new THREE.MeshBasicMaterial({ color: 0xffc21a })
  );
  group.add(tube);
  // resplandor
  group.add(new THREE.Mesh(
    new THREE.TubeGeometry(curve, Math.min(900, pts.length * 2), 0.16, 8, false),
    new THREE.MeshBasicMaterial({ color: 0xffc21a, transparent: true, opacity: 0.12 })
  ));
  // cortina bajo la curva
  const cur = [];
  pts.forEach((p, i) => { if (i < pts.length - 1) { const q = pts[i + 1];
    cur.push(p.x, p.y, 0, q.x, q.y, 0, p.x, -2.8, 0, q.x, q.y, 0, q.x, -2.8, 0, p.x, -2.8, 0); } });
  const cg = new THREE.BufferGeometry();
  cg.setAttribute("position", new THREE.Float32BufferAttribute(cur, 3));
  group.add(new THREE.Mesh(cg, new THREE.MeshBasicMaterial({ color: 0x2a2f6b, transparent: true, opacity: 0.35, side: THREE.DoubleSide })));

  // cono: bandas 95% y 80% con volumen en z
  function banda(lo, hi, color, op, depth) {
    const v = [];
    const i0 = hist.length - 1;
    const pre = [{ lo: hist[i0].v, hi: hist[i0].v }].concat(cono.map(d => ({ lo: d[lo], hi: d[hi] })));
    for (let k = 0; k < pre.length - 1; k++) {
      const x1 = X(i0 + k), x2 = X(i0 + k + 1);
      const a = pre[k], b = pre[k + 1];
      const z1 = depth * (k / pre.length), z2 = depth * ((k + 1) / pre.length);
      // cara superior/inferior abiertas en abanico (volumen hacia adelante y atrás)
      for (const s of [1, -1]) {
        v.push(x1, Y(a.lo), s * z1, x2, Y(b.lo), s * z2, x2, Y(b.hi), s * z2);
        v.push(x1, Y(a.lo), s * z1, x2, Y(b.hi), s * z2, x1, Y(a.hi), s * z1);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(v, 3));
    g.computeVertexNormals();
    return new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color, transparent: true, opacity: op, side: THREE.DoubleSide, depthWrite: false }));
  }
  group.add(banda("p2_5", "p97_5", 0xe2462c, 0.16, 1.6));
  group.add(banda("p10", "p90", 0xff8a3d, 0.28, 0.9));
  const mid = cono.map((d, k) => new THREE.Vector3(X(hist.length + k), Y(d.p50), 0));
  const ml = new THREE.BufferGeometry().setFromPoints([pts[pts.length - 1]].concat(mid));
  group.add(new THREE.Line(ml, new THREE.LineDashedMaterial({ color: 0xffffff, dashSize: 0.18, gapSize: 0.12, transparent: true, opacity: 0.7 })));
  group.children[group.children.length - 1].computeLineDistances();

  // punto "hoy" pulsante
  const hoy = new THREE.Mesh(new THREE.SphereGeometry(0.16, 24, 24), new THREE.MeshBasicMaterial({ color: 0xffffff }));
  hoy.position.copy(pts[pts.length - 1]);
  group.add(hoy);
  const halo = new THREE.Mesh(new THREE.RingGeometry(0.22, 0.3, 40), new THREE.MeshBasicMaterial({ color: 0xffc21a, transparent: true, opacity: 0.8, side: THREE.DoubleSide }));
  halo.position.copy(hoy.position);
  group.add(halo);

  // interacción: inclinación con el mouse y tooltip de valor
  let mx = 0, my = 0;
  const ray = new THREE.Raycaster();
  ray.params.Line = { threshold: 0.2 };
  const mouse = new THREE.Vector2();
  el.addEventListener("pointermove", e => {
    const r = el.getBoundingClientRect();
    mx = ((e.clientX - r.left) / r.width) * 2 - 1;
    my = ((e.clientY - r.top) / r.height) * 2 - 1;
    mouse.set(mx, -my);
    ray.setFromCamera(mouse, cam);
    const hit = ray.intersectObject(tube)[0];
    if (hit && onHover) {
      const local = group.worldToLocal(hit.point.clone());
      const i = Math.round(((local.x + 9) / 18) * (N - 1));
      if (i >= 0 && i < hist.length) onHover(hist[i], e.clientX, e.clientY); else onHover(null);
    } else if (onHover) onHover(null);
  });
  el.addEventListener("pointerleave", () => { mx = 0; my = 0; onHover && onHover(null); });

  let t0 = performance.now(), visible = true;
  new IntersectionObserver(es => { visible = es[0].isIntersecting; }).observe(el);
  (function loop(t) {
    requestAnimationFrame(loop);
    if (!visible) return;
    const s = (t - t0) / 1000;
    group.rotation.y += ((mx * 0.35 - 0.28 + Math.sin(s * 0.15) * 0.06) - group.rotation.y) * 0.04;
    group.rotation.x += ((my * 0.12 + 0.06) - group.rotation.x) * 0.04;
    halo.scale.setScalar(1 + 0.35 * Math.abs(Math.sin(s * 2)));
    halo.material.opacity = 0.9 - 0.6 * Math.abs(Math.sin(s * 2));
    halo.lookAt(cam.position);
    renderer.render(scene, cam);
  })(t0);

  window.addEventListener("resize", () => {
    cam.aspect = W() / H(); cam.updateProjectionMatrix(); renderer.setSize(W(), H());
  });
  el.classList.add("ready");
};
