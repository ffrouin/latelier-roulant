// Construit une illustration Three.js légère d’un atelier mobile.
import * as THREE from 'three';

const mount = document.querySelector('#scene');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 100);
const cameraTarget = new THREE.Vector3(0, 1.45, -1.1);
const cameraDirection = new THREE.Vector3(7.2, 3.7, 11.5).sub(cameraTarget).normalize();
let cameraDistance = 15;
let orbitAzimuth = Math.atan2(cameraDirection.x, cameraDirection.z);
let orbitElevation = Math.asin(cameraDirection.y);
function updateCamera() {
  const horizontal = Math.cos(orbitElevation) * cameraDistance;
  camera.position.set(
    cameraTarget.x + Math.sin(orbitAzimuth) * horizontal,
    cameraTarget.y + Math.sin(orbitElevation) * cameraDistance,
    cameraTarget.z + Math.cos(orbitAzimuth) * horizontal,
  );
  camera.lookAt(cameraTarget);
}
updateCamera();

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
mount.appendChild(renderer.domElement);

const palette = { ink: 0x18211f, orange: 0xee6b3b, green: 0x7d9b76, cream: 0xf3f1e9, metal: 0xd6d2c5 };
const group = new THREE.Group();
group.position.x = 1.65;
group.position.z = 0.95;
group.scale.setScalar(0.49);
scene.add(group);

const mat = (color, roughness = 0.78) => new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.05 });
const box = (size, position, material, radius = 0.08) => {
  const geometry = new THREE.BoxGeometry(...size);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(...position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
  return mesh;
};

const worldBox = (size, position, material) => {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), material);
  mesh.position.set(...position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  scene.add(mesh);
  return mesh;
};

// Approximation stylisée d’un Nissan NV200 : caisse haute, cabine avancée,
// pare-brise incliné et détails utilitaires plutôt qu’un simple pavé.
const body = mat(palette.cream);
const trim = mat(palette.ink, 0.5);
const glass = new THREE.MeshStandardMaterial({ color: 0x263b42, roughness: 0.24, metalness: 0.18 });
const lamp = new THREE.MeshStandardMaterial({ color: 0xffc875, emissive: 0x5b3215, emissiveIntensity: 0.7 });

// Marquage de carrosserie : le nom reprend le traitement noir/orange du site.
const labelCanvas = document.createElement('canvas');
labelCanvas.width = 1200;
labelCanvas.height = 240;
const labelContext = labelCanvas.getContext('2d');
labelContext.clearRect(0, 0, labelCanvas.width, labelCanvas.height);
labelContext.textBaseline = 'middle';
labelContext.font = '700 92px Space Grotesk, Arial, sans-serif';
labelContext.fillStyle = '#18211f';
labelContext.fillText("L'Atelier", 34, 120);
const firstWidth = labelContext.measureText("L'Atelier").width;
labelContext.fillStyle = '#ee6b3b';
labelContext.fillText('Roulant', 50 + firstWidth, 120);
const labelTexture = new THREE.CanvasTexture(labelCanvas);
labelTexture.colorSpace = THREE.SRGBColorSpace;
const labelMaterial = new THREE.MeshBasicMaterial({ map: labelTexture, transparent: true, depthWrite: false });
const sideLabel = new THREE.Mesh(new THREE.PlaneGeometry(3.0, 0.55), labelMaterial);
sideLabel.position.set(0, 1.18, -1.085);
sideLabel.rotation.y = Math.PI;
sideLabel.renderOrder = 3;
group.add(sideLabel);

box([3.9, 1.45, 2.02], [0, 1.02, 0], body);
box([2.48, 1.12, 2.08], [0.65, 2.08, 0], body);
box([1.22, 0.7, 2.08], [-1.28, 1.88, 0], body);
box([0.18, 0.48, 2.12], [-1.9, 1.3, 0], trim);

// Pare-brise et vitres latérales de la cabine.
box([0.05, 0.68, 1.7], [-0.72, 2.28, 0], glass);
for (const z of [-1.045, 1.045]) {
  box([0.78, 0.54, 0.045], [-1.22, 2.18, z], glass);
  box([0.78, 0.42, 0.045], [0.02, 2.16, z], glass);
  box([0.05, 0.48, 0.05], [-0.78, 2.16, z * 1.01], trim);
}

// Portes coulissantes, pare-chocs, poignées et bande latérale.
for (const z of [-1.055, 1.055]) {
  box([1.72, 0.045, 0.035], [0.82, 1.34, z], trim);
  box([0.16, 0.035, 0.04], [0.48, 1.92, z * 1.01], trim);
  box([3.1, 0.1, 0.05], [0.25, 0.55, z * 1.01], mat(palette.green));
}
box([0.18, 0.34, 2.16], [-1.94, 0.72, 0], trim);
box([0.2, 0.3, 2.18], [1.95, 0.72, 0], trim);

// Calandre, phares et feux arrière, visibles dans la vue trois-quarts avant.
box([0.06, 0.42, 0.68], [-2.02, 1.12, -0.57], lamp);
box([0.06, 0.42, 0.68], [-2.02, 1.12, 0.57], lamp);
box([0.04, 0.28, 0.82], [-2.04, 0.86, 0], trim);
box([0.05, 0.35, 0.34], [1.98, 1.28, -0.8], lamp);
box([0.05, 0.35, 0.34], [1.98, 1.28, 0.8], lamp);

// Rétroviseurs extérieurs.
for (const z of [-1.2, 1.2]) {
  box([0.22, 0.18, 0.16], [-0.93, 1.94, z], trim);
}

for (const x of [-1.35, 1.35]) {
  for (const z of [-1.08, 1.08]) {
    const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.43, 0.43, 0.3, 32), trim);
    wheel.rotation.x = Math.PI / 2;
    wheel.position.set(x, 0.5, z);
    wheel.castShadow = true;
    group.add(wheel);
    const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.315, 24), mat(palette.metal));
    hub.rotation.x = Math.PI / 2;
    hub.position.set(x, 0.5, z);
    group.add(hub);
  }
}

// L’atelier reste visible à l’arrière : caisse à outils et panneau de service.
box([1.05, 0.58, 0.8], [1.2, 0.58, 0.22], mat(palette.green));
box([0.95, 0.04, 0.62], [1.2, 1.28, 0.65], mat(palette.orange));
box([0.12, 1.05, 0.12], [1.18, 1.35, 0.3], trim);

// Place du village : sol pavé, mairie à gauche et église à droite.
const plaza = new THREE.Mesh(new THREE.PlaneGeometry(14, 12), new THREE.MeshStandardMaterial({ color: 0xd9d4c7, roughness: 1 }));
plaza.rotation.x = -Math.PI / 2;
plaza.position.set(0, 0.07, -0.25);
plaza.receiveShadow = true;
scene.add(plaza);
worldBox([14, 0.03, 0.18], [0, 0.09, 1.15], mat(0xb8b2a5));
worldBox([0.18, 0.03, 12], [-5.2, 0.09, -0.25], mat(0xb8b2a5));

const mairie = mat(0xf1e5c9);
const roof = mat(0xc76b45);
const stone = mat(0xb7a99a);
const church = mat(0xe5e0d5);
const churchRoof = mat(0x556b63);
const darkGlass = new THREE.MeshStandardMaterial({ color: 0x30444a, roughness: 0.25, metalness: 0.1 });

worldBox([2.5, 1.55, 1.55], [-3.25, 0.87, -2.75], mairie);
const mairieRoof = new THREE.Mesh(new THREE.ConeGeometry(1.9, 0.65, 4), roof);
mairieRoof.rotation.y = Math.PI / 4;
mairieRoof.position.set(-3.25, 1.93, -2.75);
mairieRoof.castShadow = true;
scene.add(mairieRoof);
worldBox([0.28, 0.85, 0.05], [-3.25, 1.22, -3.55], darkGlass);
worldBox([0.28, 0.85, 0.05], [-3.25, 1.22, -1.95], darkGlass);

// Drapeau français et enseigne de la mairie.
worldBox([0.04, 1.1, 0.04], [-3.48, 2.35, -3.59], stone);
worldBox([0.18, 0.36, 0.03], [-3.25, 2.67, -3.59], mat(0x1d4f91));
worldBox([0.18, 0.36, 0.03], [-3.05, 2.67, -3.59], mat(0xf4f1e8));
worldBox([0.18, 0.36, 0.03], [-2.85, 2.67, -3.59], mat(0xd64945));
const mairieSignCanvas = document.createElement('canvas');
mairieSignCanvas.width = 800;
mairieSignCanvas.height = 180;
const mairieSignContext = mairieSignCanvas.getContext('2d');
mairieSignContext.fillStyle = '#f8f3e7';
mairieSignContext.fillRect(0, 0, 800, 180);
mairieSignContext.fillStyle = '#18211f';
mairieSignContext.font = '700 100px Arial, sans-serif';
mairieSignContext.textAlign = 'center';
mairieSignContext.textBaseline = 'middle';
mairieSignContext.fillText('MAIRIE', 400, 92);
const mairieSignTexture = new THREE.CanvasTexture(mairieSignCanvas);
mairieSignTexture.colorSpace = THREE.SRGBColorSpace;
const mairieSign = new THREE.Mesh(
  new THREE.PlaneGeometry(0.95, 0.22),
  new THREE.MeshBasicMaterial({ map: mairieSignTexture })
);
mairieSign.position.set(-1.995, 1.28, -2.75);
mairieSign.rotation.y = Math.PI / 2;
scene.add(mairieSign);

worldBox([2.15, 1.85, 1.6], [3.0, 1.02, -2.7], church);
const churchRoofMesh = new THREE.Mesh(new THREE.ConeGeometry(1.55, 0.7, 4), churchRoof);
churchRoofMesh.rotation.y = Math.PI / 4;
churchRoofMesh.position.set(3.0, 2.28, -2.7);
churchRoofMesh.castShadow = true;
scene.add(churchRoofMesh);
worldBox([0.72, 3.05, 0.78], [2.05, 1.57, -2.72], stone);
const steeple = new THREE.Mesh(new THREE.ConeGeometry(0.58, 1.35, 4), churchRoof);
steeple.rotation.y = Math.PI / 4;
steeple.position.set(2.05, 3.78, -2.72);
steeple.castShadow = true;
scene.add(steeple);
worldBox([0.22, 0.85, 0.05], [2.05, 1.45, -3.12], darkGlass);
worldBox([0.18, 1.0, 0.08], [2.05, 4.55, -2.72], roof);
worldBox([0.8, 0.12, 0.08], [2.05, 4.55, -2.72], roof);

// Portes, bancs et massifs fleuris donnent vie aux abords des bâtiments.
const wood = mat(0x8a5b3c);
const door = mat(0x394847, 0.55);
worldBox([0.9, 1.25, 0.05], [-3.25, 0.72, -3.56], stone);
worldBox([0.62, 1.0, 0.06], [-3.25, 0.62, -3.6], door);
worldBox([0.75, 1.18, 0.05], [3.0, 0.7, -3.53], stone);
worldBox([0.5, 0.9, 0.06], [3.0, 0.58, -3.57], door);

function addBench(x, z, rotation = 0) {
  const bench = new THREE.Group();
  bench.position.set(x, 0, z);
  bench.rotation.y = rotation;
  const seat = new THREE.Mesh(new THREE.BoxGeometry(1.25, 0.12, 0.34), wood);
  seat.position.y = 0.36;
  seat.castShadow = true;
  bench.add(seat);
  for (const legX of [-0.43, 0.43]) {
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.272, 0.24), wood);
    leg.position.set(legX, 0.136, 0);
    leg.castShadow = true;
    bench.add(leg);
  }
  const back = new THREE.Mesh(new THREE.BoxGeometry(1.25, 0.42, 0.1), wood);
  back.position.set(0, 0.63, -0.13);
  back.castShadow = true;
  bench.add(back);
  scene.add(bench);
}
// Un banc sous le fronton de la mairie, puis un banc contre l’église
// tourné vers la ligne des sapins.
addBench(-1.82, -2.75, Math.PI / 2);
addBench(4.35, -2.7, Math.PI / 2);

function addFlowerBed(x, z, colors) {
  worldBox([1.9, 0.12, 0.48], [x, 0.14, z], mat(0x657650));
  const spacing = 0.3;
  colors.forEach((color, index) => {
    const flowerX = x - ((colors.length - 1) * spacing) / 2 + index * spacing;
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.32, 8), mat(0x507045));
    stem.position.set(flowerX, 0.36, z + (index % 2 ? 0.08 : -0.08));
    scene.add(stem);
    const blossom = new THREE.Mesh(new THREE.SphereGeometry(0.09, 12, 8), mat(color));
    blossom.position.set(stem.position.x, 0.55, stem.position.z);
    blossom.castShadow = true;
    scene.add(blossom);
  });
}
addFlowerBed(-3.25, -1.55, [0xd64945, 0xf3c85f, 0x6f78b8, 0xd64945, 0xf3c85f]);
addFlowerBed(3.0, -1.55, [0x6f78b8, 0xf3c85f, 0xd64945, 0x6f78b8, 0xf3c85f]);

// Panneau d’entrée de commune : le nom change régulièrement dans la scène.
const communeNames = [
  'La Châpelle Bâton',
  'Saint-Christophe-sur-Roc',
  'Champdeniers',
  'Cherveux',
  'Augé',
  'La Crêche',
  'Azay-le-Brûle',
];
const communeCanvas = document.createElement('canvas');
communeCanvas.width = 1400;
communeCanvas.height = 500;
const communeContext = communeCanvas.getContext('2d');
const communeTexture = new THREE.CanvasTexture(communeCanvas);
communeTexture.colorSpace = THREE.SRGBColorSpace;
const communeMaterial = new THREE.MeshBasicMaterial({ map: communeTexture, transparent: true, side: THREE.DoubleSide });
const communeBacking = new THREE.Mesh(
  new THREE.BoxGeometry(1.4, 0.5, 0.06),
  new THREE.MeshStandardMaterial({ color: 0xf7f7f2, roughness: 0.8 })
);
communeBacking.position.set(4.9, 1.2, 4.3);
communeBacking.rotation.y = -0.28;
communeBacking.castShadow = true;
scene.add(communeBacking);
const communeSign = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 0.5), communeMaterial);
communeSign.position.set(4.9, 1.2, 4.3);
communeSign.rotation.y = -0.28;
communeSign.translateZ(0.035);
scene.add(communeSign);
worldBox([0.06, 0.9, 0.06], [4.9, 0.48, 4.3], stone);

let communeIndex = 0;
let communePrevious = communeNames[0];
let communeChangedAt = 0;
let communeLastSwitch = 0;
function drawCommuneSign(time) {
  if (time - communeLastSwitch > 4200) {
    communePrevious = communeNames[communeIndex];
    communeIndex = (communeIndex + 1) % communeNames.length;
    communeChangedAt = time;
    communeLastSwitch = time;
  }
  const transition = communeChangedAt ? THREE.MathUtils.clamp((time - communeChangedAt) / 650, 0, 1) : 1;
  communeContext.clearRect(0, 0, communeCanvas.width, communeCanvas.height);
  communeContext.fillStyle = '#f7f7f2';
  communeContext.fillRect(0, 0, communeCanvas.width, communeCanvas.height);
  communeContext.strokeStyle = '#c33d3d';
  communeContext.lineWidth = 28;
  communeContext.strokeRect(18, 18, communeCanvas.width - 36, communeCanvas.height - 36);
  communeContext.textAlign = 'center';
  communeContext.textBaseline = 'middle';
  communeContext.font = '700 104px Arial, sans-serif';
  communeContext.fillStyle = '#171b1b';
  communeContext.globalAlpha = 1 - transition;
  communeContext.fillText(communePrevious, communeCanvas.width / 2, communeCanvas.height / 2);
  communeContext.globalAlpha = transition;
  communeContext.fillText(communeNames[communeIndex], communeCanvas.width / 2, communeCanvas.height / 2);
  communeContext.globalAlpha = 1;
  communeTexture.needsUpdate = true;
}
drawCommuneSign(0);

// Quelques arbres encadrent la place sans concurrencer les bâtiments.
for (const [x, z] of [[-5.2, -2.3], [5.8, -1.65], [-4.8, 2.0], [5.6, 2.5]]) {
  worldBox([0.18, 0.95, 0.18], [x, 0.55, z], stone);
  const crown = new THREE.Mesh(new THREE.ConeGeometry(0.68, 1.45, 8), mat(0x78906c));
  crown.position.set(x, 1.65, z);
  crown.castShadow = true;
  scene.add(crown);
}

const floor = new THREE.Mesh(new THREE.CircleGeometry(7.5, 64), new THREE.MeshStandardMaterial({ color: 0xe5e1d6, roughness: 1 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = 0.05; floor.receiveShadow = true; scene.add(floor);

scene.add(new THREE.HemisphereLight(0xfff9ed, 0x68746e, 2.1));
const key = new THREE.DirectionalLight(0xffeee0, 3.1);
key.position.set(-4, 7, 5); key.castShadow = true; key.shadow.mapSize.set(1024, 1024); scene.add(key);

const vehicleOrientation = Math.PI;
let targetRotation = 0.24;
let pointerRotation = 0.24;
let isOrbiting = false;
let lastPointerX = 0;
let lastPointerY = 0;
mount.addEventListener('pointermove', (event) => {
  if (isOrbiting) {
    const deltaX = event.clientX - lastPointerX;
    const deltaY = event.clientY - lastPointerY;
    lastPointerX = event.clientX;
    lastPointerY = event.clientY;
    orbitAzimuth -= deltaX * 0.006;
    orbitElevation = THREE.MathUtils.clamp(orbitElevation + deltaY * 0.004, 0.05, 0.9);
    updateCamera();
    return;
  }
  const rect = mount.getBoundingClientRect();
  targetRotation = 0.24 + ((event.clientX - rect.left) / rect.width - 0.5) * 0.35;
});
mount.addEventListener('pointerleave', () => { targetRotation = 0.24; });
mount.addEventListener('pointerdown', (event) => {
  isOrbiting = true;
  lastPointerX = event.clientX;
  lastPointerY = event.clientY;
  mount.setPointerCapture(event.pointerId);
  mount.classList.add('is-orbiting');
});
mount.addEventListener('pointerup', (event) => {
  isOrbiting = false;
  if (mount.hasPointerCapture(event.pointerId)) mount.releasePointerCapture(event.pointerId);
  mount.classList.remove('is-orbiting');
});
mount.addEventListener('pointercancel', () => {
  isOrbiting = false;
  mount.classList.remove('is-orbiting');
});
mount.addEventListener('wheel', (event) => {
  event.preventDefault();
  cameraDistance = THREE.MathUtils.clamp(cameraDistance + event.deltaY * 0.008, 12, 18);
  updateCamera();
}, { passive: false });

function resize() {
  const width = mount.clientWidth;
  const height = Math.max(360, mount.clientHeight);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

function animate(time) {
  drawCommuneSign(time);
  pointerRotation += (targetRotation - pointerRotation) * 0.045;
  group.rotation.y = vehicleOrientation + pointerRotation + Math.sin(time * 0.00035) * 0.035;
  group.position.y = 0.08 + Math.sin(time * 0.0012) * 0.035;
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
window.__ATELIER_ROULANT_READY = true;
window.__ATELIER_ROULANT_CAMERA = camera;
