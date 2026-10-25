// Construit une illustration Three.js légère d’un atelier mobile.
import * as THREE from 'three';
import { communeEntries } from './lieux-dits.js';

const mount = document.querySelector('#scene');
const loadingScreen = document.querySelector('#loading-screen');
const loadingProgress = document.querySelector('#loading-progress');
const loadingStatus = document.querySelector('#loading-status');
const page = document.querySelector('.page');
function updateLoadingProgress(value, status) {
  loadingProgress.style.width = `${value}%`;
  loadingStatus.textContent = status;
}
updateLoadingProgress(8, 'Préparation de l’atelier…');
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
updateLoadingProgress(26, 'Installation de la scène…');

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
labelCanvas.height = 320;
const labelContext = labelCanvas.getContext('2d');
labelContext.clearRect(0, 0, labelCanvas.width, labelCanvas.height);
labelContext.textBaseline = 'middle';
labelContext.font = '700 92px Space Grotesk, Arial, sans-serif';
labelContext.fillStyle = '#18211f';
labelContext.fillText("L'Atelier", 34, 105);
const firstWidth = labelContext.measureText("L'Atelier").width;
labelContext.fillStyle = '#ee6b3b';
labelContext.fillText('Roulant', 50 + firstWidth, 105);
labelContext.font = '600 64px Space Grotesk, Arial, sans-serif';
let phoneX = 50;
for (const [phonePart, color] of [['06 63 ', '#18211f'], ['22', '#ee6b3b'], [' ', '#18211f'], ['22', '#ee6b3b'], [' 80', '#18211f']]) {
  labelContext.fillStyle = color;
  labelContext.fillText(phonePart, phoneX, 235);
  phoneX += labelContext.measureText(phonePart).width;
}
const labelTexture = new THREE.CanvasTexture(labelCanvas);
labelTexture.colorSpace = THREE.SRGBColorSpace;
const labelMaterial = new THREE.MeshBasicMaterial({ map: labelTexture, transparent: true, depthWrite: false });
const sideLabel = new THREE.Mesh(new THREE.PlaneGeometry(3.0, 0.8), labelMaterial);
sideLabel.position.set(-0.58, 0.94, -1.085);
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

// Portes, bancs et massifs fleuris donnent vie aux abords des bâtiments.
const wood = mat(0x8a5b3c);
const door = mat(0x394847, 0.55);
worldBox([0.9, 1.25, 0.05], [-3.25, 0.72, -3.56], stone);
worldBox([0.62, 1.0, 0.06], [-3.25, 0.62, -3.6], door);
worldBox([0.05, 1.18, 0.75], [1.68, 0.72, -2.72], stone);
worldBox([0.06, 0.9, 0.5], [1.64, 0.6, -2.72], door);

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

// Panneau d’entrée : communes et lieux-dits associés défilent dans un ordre aléatoire.
function shuffleEntries(entries) {
  const shuffled = [...entries];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [shuffled[index], shuffled[randomIndex]] = [shuffled[randomIndex], shuffled[index]];
  }
  return shuffled;
}
let displayedCommuneEntries = shuffleEntries(communeEntries);
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
let communePrevious = displayedCommuneEntries[0];
let communeChangedAt = 0;
let communeLastSwitch = 0;
function drawCommuneEntry(entry, alpha) {
  communeContext.globalAlpha = alpha;
  communeContext.fillStyle = '#171b1b';
  if (entry.type === 'commune') {
    communeContext.font = '700 110px Arial, sans-serif';
    communeContext.fillText(entry.name, communeCanvas.width / 2, 190);
    communeContext.font = '600 62px Arial, sans-serif';
    communeContext.fillText(entry.department, communeCanvas.width / 2, 335);
  } else {
    communeContext.font = '700 94px Arial, sans-serif';
    communeContext.fillText(entry.name, communeCanvas.width / 2, 145);
    communeContext.font = '600 58px Arial, sans-serif';
    communeContext.fillText(`Commune de ${entry.commune}`, communeCanvas.width / 2, 285);
    communeContext.font = '500 50px Arial, sans-serif';
    communeContext.fillText(entry.department, communeCanvas.width / 2, 390);
  }
  communeContext.globalAlpha = 1;
}
function drawCommuneSign(time) {
  if (time - communeLastSwitch > 3200) {
    communePrevious = displayedCommuneEntries[communeIndex];
    communeIndex += 1;
    if (communeIndex >= displayedCommuneEntries.length) {
      displayedCommuneEntries = shuffleEntries(communeEntries);
      communeIndex = 0;
    }
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
  communeContext.globalAlpha = 1 - transition;
  drawCommuneEntry(communePrevious, 1 - transition);
  drawCommuneEntry(displayedCommuneEntries[communeIndex], transition);
  communeContext.globalAlpha = 1;
  communeTexture.needsUpdate = true;
}
drawCommuneSign(0);
updateLoadingProgress(78, 'Mise en place du village…');

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
const mobileSceneQuery = window.matchMedia('(max-width: 850px)');
let mobileSceneDisabled = mobileSceneQuery.matches;
let animationFrameId = null;
function updateSceneRenderingMode() {
  mobileSceneDisabled = mobileSceneQuery.matches;
  mount.classList.toggle('is-mobile-disabled', mobileSceneDisabled);
  mount.setAttribute('aria-hidden', mobileSceneDisabled ? 'true' : 'false');
  window.__ATELIER_ROULANT_RENDER_ENABLED = !mobileSceneDisabled;
  if (mobileSceneDisabled && animationFrameId !== null) {
    window.cancelAnimationFrame(animationFrameId);
    animationFrameId = null;
  } else if (!mobileSceneDisabled && animationFrameId === null) {
    animationFrameId = window.requestAnimationFrame(animate);
  }
}
mobileSceneQuery.addEventListener('change', updateSceneRenderingMode);
window.addEventListener('resize', () => {
  updateSceneRenderingMode();
  if (!mobileSceneDisabled) resize();
});
resize();
updateSceneRenderingMode();
updateLoadingProgress(88, 'Préparation de l’accueil…');

let welcomeRevealed = false;
function revealWelcome() {
  if (welcomeRevealed) return;
  welcomeRevealed = true;
  updateLoadingProgress(100, 'Prêt');
  page.classList.add('is-ready');
  loadingScreen.classList.add('is-hidden');
}
function animate(time) {
  animationFrameId = null;
  if (mobileSceneDisabled) {
    revealWelcome();
    return;
  }
  drawCommuneSign(time);
  pointerRotation += (targetRotation - pointerRotation) * 0.045;
  group.rotation.y = vehicleOrientation + pointerRotation + Math.sin(time * 0.00035) * 0.035;
  group.position.y = 0.08 + Math.sin(time * 0.0012) * 0.035;
  renderer.render(scene, camera);
  revealWelcome();
  animationFrameId = window.requestAnimationFrame(animate);
}
const offerButton = document.querySelector('.cta');
const mairieButton = document.querySelector('#mairie-button');
const mairieScene = document.querySelector('#mairie-scene');
const mairieBack = document.querySelector('#mairie-back');
const serviceScene = document.querySelector('#service-scene');
const serviceContent = serviceScene.querySelector('.service-content');
const processProgress = document.querySelector('#process-progress');
const processProgressFill = document.querySelector('#process-progress-fill');
const processProgressLabel = document.querySelector('#process-progress-label');
const processProgressPoints = [...document.querySelectorAll('.process-progress-point')];
const servicePanel = document.querySelector('.copy');
const serviceSelection = document.querySelector('#service-selection');
const serviceStepOne = document.querySelector('#service-step-one');
const serviceChoice = document.querySelector('#service-choice');
const serviceDetail = document.querySelector('#service-detail');
const detailTitle = document.querySelector('#detail-title');
const detailIntro = document.querySelector('#detail-intro');
const detailObjectLabel = document.querySelector('#detail-object-label');
const detailObject = document.querySelector('#detail-object');
const detailDescription = document.querySelector('#detail-description');
const detailPhoto = document.querySelector('#detail-photo');
const photoFileName = document.querySelector('#photo-file-name');
const photoGallery = document.querySelector('#summary-photo-gallery');
const photoHoverPreview = document.querySelector('#photo-hover-preview');
const photoHoverImage = document.querySelector('#photo-hover-image');
const detailFeedback = document.querySelector('#detail-feedback');
const serviceLocation = document.querySelector('#service-location');
const locationFeedback = document.querySelector('#location-feedback');
const serviceSummary = document.querySelector('#service-summary');
const summaryFeedback = document.querySelector('#summary-feedback');
const humanVerification = document.querySelector('#human-verification');
const humanGame = document.querySelector('#human-game');
const humanBalls = [...humanGame.querySelectorAll('.human-ball')];
const humanGameStatus = document.querySelector('#human-game-status');
const humanContinue = document.querySelector('#human-continue');
const humanFeedback = document.querySelector('#human-feedback');
const requestPdf = document.querySelector('#request-pdf');
const requestPdfViewer = document.querySelector('#request-pdf-viewer');
const requestPdfDownload = document.querySelector('#request-pdf-download');
const legalFooter = document.querySelector('#legal-footer');
const locationTown = document.querySelector('#location-town');
const locationPostcode = document.querySelector('#location-postcode');
const locationAddress = document.querySelector('#location-address');
const addressSuggestions = document.querySelector('#location-address-suggestions');
const addressStatus = document.querySelector('#location-address-status');
let humanGameRound = 0;
let humanGameSequenceIndex = 0;
const humanGameSequence = ['blue', 'white', 'red'];
let stepTransitionInProgress = false;
let addressLookupTimer;
let addressLookupController;
let addressSuggestionSelected = false;
async function loadPublicConfig() {
  if (!legalFooter) return;
  try {
    const response = await fetch('/api/public-config', { cache: 'no-store' });
    if (!response.ok) return;
    const payload = await response.json();
    const legal = payload.legal || {};
    legalFooter.replaceChildren();
    const addSeparator = () => legalFooter.append(document.createTextNode(' - '));
    const addText = (value) => {
      if (!value) return;
      if (legalFooter.childNodes.length) addSeparator();
      legalFooter.append(document.createTextNode(value));
    };
    const addLink = (value, href) => {
      if (!value) return;
      if (legalFooter.childNodes.length) addSeparator();
      const link = document.createElement('a');
      link.href = href;
      link.textContent = value;
      legalFooter.append(link);
    };
    addText(legal.business_name);
    addText(legal.contact_name);
    if (legal.phone) addLink(legal.phone, `tel:${String(legal.phone).replace(/[^+\d]/g, '')}`);
    addText(legal.registration);
    if (legal.email) addLink(legal.email, `mailto:${legal.email}`);
  } catch (error) {
    // The generic footer remains visible if the public configuration is unavailable.
  }
}
loadPublicConfig();
function updateProcessProgress(percent, label) {
  processProgressFill.style.width = `${percent}%`;
  processProgress.setAttribute('aria-valuenow', String(percent));
  processProgressLabel.textContent = label;
  processProgressPoints.forEach((point, index) => {
    point.classList.toggle('is-active', index * 20 <= percent);
  });
}
function transitionForward(update) {
  if (stepTransitionInProgress) return;
  stepTransitionInProgress = true;
  serviceContent.classList.remove('is-sliding-right');
  serviceContent.classList.add('is-sliding-left');
  window.setTimeout(() => {
    update();
    serviceContent.classList.remove('is-sliding-left');
    serviceContent.classList.add('is-sliding-right');
    window.setTimeout(() => {
      serviceContent.classList.remove('is-sliding-right');
      stepTransitionInProgress = false;
    }, 380);
  }, 260);
}
function moveHumanBalls() {
  const size = 42;
  const padding = 8;
  const gap = 8;
  const width = Math.max(humanGame.clientWidth, 320);
  const height = Math.max(humanGame.clientHeight, 180);
  const maxX = Math.max(padding, width - size - padding);
  const maxY = Math.max(padding, height - size - padding);
  const positions = [];
  humanBalls.forEach((ball) => {
    let position = null;
    for (let attempt = 0; attempt < 120 && !position; attempt += 1) {
      const candidate = {
        x: padding + Math.random() * Math.max(0, maxX - padding),
        y: padding + Math.random() * Math.max(0, maxY - padding),
      };
      if (positions.every((other) => Math.hypot(candidate.x - other.x, candidate.y - other.y) >= size + gap)) {
        position = candidate;
      }
    }
    if (!position) {
      const fallback = [
        { x: padding, y: padding },
        { x: maxX, y: padding },
        { x: Math.max(padding, (width - size) / 2), y: maxY },
      ];
      position = fallback.find((candidate) => positions.every((other) => Math.hypot(candidate.x - other.x, candidate.y - other.y) >= size + gap)) || fallback[positions.length % fallback.length];
    }
    positions.push(position);
    ball.style.left = `${position.x}px`;
    ball.style.top = `${position.y}px`;
  });
}
function resetHumanGame() {
  humanGameRound = 0;
  humanGameSequenceIndex = 0;
  humanGameStatus.textContent = '0 / 3';
  humanBalls.forEach((ball) => { ball.disabled = false; });
  humanContinue.disabled = true;
  humanFeedback.textContent = '';
  moveHumanBalls();
}
const detailCopy = {
  'Électroménager': ['Quel appareil souhaitez-vous faire réparer ?', 'Indiquez l’appareil concerné et décrivez la panne constatée.', 'Appareil ou équipement', 'Ex. lave-linge, four, réfrigérateur…'],
  'Informatique & électronique': ['Quel appareil faut-il remettre en service ?', 'Précisez l’équipement, le symptôme et les éventuels messages d’erreur.', 'Appareil ou équipement', 'Ex. ordinateur portable, écran, imprimante…'],
  'Maison & mobilier': ['Que faut-il remettre en état ?', 'Décrivez la pièce, le meuble ou la réparation à effectuer.', 'Élément ou zone concernée', 'Ex. meuble, mur, parquet, plafond…'],
  'Débarras': ['Que souhaitez-vous débarrasser ?', 'Indiquez le type et le volume approximatif des objets à évacuer.', 'Objets ou volume', 'Ex. cave, mobilier, électroménager…'],
  'Diagnostic': ['Que se passe-t-il ?', 'Décrivez librement le problème : nous vous aiderons à identifier la bonne intervention.', 'Objet ou situation', 'Ex. appareil qui ne démarre plus…'],
  'Autre demande': ['Comment pouvons-nous vous aider ?', 'Décrivez votre demande avec vos propres mots.', 'Sujet de la demande', 'Ex. une autre intervention à domicile…'],
};
offerButton.addEventListener('click', (event) => {
  event.preventDefault();
  updateProcessProgress(0, 'Étape 1 sur 5');
  document.querySelector('#scene').classList.add('is-fading');
  servicePanel.classList.add('is-fading');
  serviceScene.classList.add('is-visible');
});
mairieButton.addEventListener('click', () => {
  mairieScene.hidden = false;
  document.querySelector('.page').classList.add('is-fading-out');
  window.requestAnimationFrame(() => mairieScene.classList.add('is-visible'));
});
mairieBack.addEventListener('click', () => {
  mairieScene.classList.remove('is-visible');
  window.setTimeout(() => {
    mairieScene.hidden = true;
    document.querySelector('.page').classList.remove('is-fading-out');
  }, 800);
});
document.querySelector('#service-home-back').addEventListener('click', () => {
  serviceScene.classList.remove('is-visible');
  document.querySelector('#scene').classList.remove('is-fading');
  servicePanel.classList.remove('is-fading');
  serviceSelection.textContent = 'Sélectionnez une catégorie pour continuer.';
  serviceDetail.hidden = true;
  serviceLocation.hidden = true;
  serviceSummary.hidden = true;
  requestPdf.hidden = true;
  updateProcessProgress(0, 'Étape 1 sur 5');
  serviceStepOne.classList.remove('is-hidden');
  serviceChoice.classList.remove('is-hidden');
  document.querySelectorAll('.service-option').forEach((option) => option.classList.remove('is-selected'));
});
document.querySelectorAll('.service-option').forEach((option) => {
  option.addEventListener('click', () => {
    document.querySelectorAll('.service-option').forEach((item) => item.classList.remove('is-selected'));
    option.classList.add('is-selected');
    const service = option.dataset.service;
    const [title, intro, label, placeholder] = detailCopy[service];
    detailTitle.textContent = title;
    detailIntro.textContent = intro;
    detailObjectLabel.textContent = label;
    detailObject.placeholder = placeholder;
    detailObject.value = '';
    detailDescription.value = '';
    detailFeedback.textContent = '';
    serviceSelection.textContent = `Besoin sélectionné : ${service}.`;
    updateProcessProgress(20, 'Étape 2 sur 5');
    transitionForward(() => {
      serviceStepOne.classList.add('is-hidden');
      serviceChoice.classList.add('is-hidden');
      serviceDetail.hidden = false;
    });
  });
});
document.querySelector('#detail-back').addEventListener('click', () => {
  serviceDetail.hidden = true;
  serviceLocation.hidden = true;
  updateProcessProgress(0, 'Étape 1 sur 5');
  serviceStepOne.classList.remove('is-hidden');
  serviceChoice.classList.remove('is-hidden');
});
document.querySelector('#detail-next').addEventListener('click', () => {
  if (!detailObject.value.trim() && !detailDescription.value.trim()) {
    detailFeedback.textContent = 'Ajoutez au moins une précision avant de continuer.';
    return;
  }
  detailFeedback.textContent = '';
  updateProcessProgress(40, 'Étape 3 sur 5');
  transitionForward(() => {
    serviceDetail.hidden = true;
    serviceLocation.hidden = false;
  });
});
document.querySelector('#location-back').addEventListener('click', () => {
  serviceLocation.hidden = true;
  serviceSummary.hidden = true;
  updateProcessProgress(20, 'Étape 2 sur 5');
  serviceDetail.hidden = false;
});
function closeAddressSuggestions() {
  addressSuggestions.hidden = true;
  locationAddress.setAttribute('aria-expanded', 'false');
}
function renderAddressSuggestions(results) {
  addressSuggestions.replaceChildren();
  results.forEach((result, index) => {
    const suggestion = document.createElement('button');
    suggestion.type = 'button';
    suggestion.className = 'address-suggestion';
    suggestion.role = 'option';
    suggestion.id = `address-suggestion-${index}`;
    suggestion.textContent = result.fulltext || [result.street, result.zipcode, result.city].filter(Boolean).join(', ');
    suggestion.addEventListener('click', () => {
      const fulltext = result.fulltext || '';
      const addressPart = fulltext.includes(',') ? fulltext.split(',')[0].trim() : (result.street || fulltext);
      locationAddress.value = addressPart;
      locationPostcode.value = result.zipcode || '';
      locationTown.value = result.city || '';
      addressSuggestionSelected = true;
      addressStatus.textContent = 'Adresse sélectionnée.';
      closeAddressSuggestions();
    });
    addressSuggestions.append(suggestion);
  });
  addressSuggestions.hidden = results.length === 0;
  locationAddress.setAttribute('aria-expanded', results.length ? 'true' : 'false');
}
function lookupAddress() {
  window.clearTimeout(addressLookupTimer);
  if (addressLookupController) addressLookupController.abort();
  addressSuggestionSelected = false;
  const query = [locationAddress.value.trim(), locationPostcode.value.trim(), locationTown.value.trim()].filter(Boolean).join(' ');
  if (query.length < 3) {
    addressStatus.textContent = '';
    closeAddressSuggestions();
    return;
  }
  addressStatus.textContent = 'Recherche de l’adresse…';
  addressLookupTimer = window.setTimeout(async () => {
    addressLookupController = new AbortController();
    try {
      const url = `https://data.geopf.fr/geocodage/completion/?text=${encodeURIComponent(query)}&maximumResponses=6&type=StreetAddress`;
      const response = await fetch(url, { signal: addressLookupController.signal, headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const results = Array.isArray(payload.results) ? payload.results : [];
      renderAddressSuggestions(results);
      addressStatus.textContent = results.length ? 'Sélectionnez une adresse proposée ou poursuivez la saisie.' : 'Aucune adresse proposée ; vous pouvez continuer manuellement.';
    } catch (error) {
      if (error.name === 'AbortError') return;
      closeAddressSuggestions();
      addressStatus.textContent = 'Vérification momentanément indisponible ; vous pouvez continuer manuellement.';
    }
  }, 450);
}
[locationAddress, locationPostcode, locationTown].forEach((input) => input.addEventListener('input', lookupAddress));
detailPhoto.addEventListener('change', () => {
  const files = [...detailPhoto.files];
  if (files.length > 3) {
    detailPhoto.value = '';
    photoFileName.textContent = '';
    detailFeedback.textContent = 'Vous pouvez joindre au maximum 3 photos.';
    return;
  }
  detailFeedback.textContent = '';
  photoFileName.textContent = files.length ? `${files.length} photo${files.length > 1 ? 's' : ''} sélectionnée${files.length > 1 ? 's' : ''} : ${files.map(file => file.name).join(', ')}` : '';
});
photoGallery.addEventListener('mouseover', (event) => {
  if (!(event.target instanceof HTMLImageElement)) return;
  photoHoverImage.src = event.target.src;
  photoHoverImage.alt = event.target.alt;
  photoHoverPreview.classList.add('is-visible');
  photoHoverPreview.setAttribute('aria-hidden', 'false');
});
photoGallery.addEventListener('mouseout', (event) => {
  const relatedImage = event.relatedTarget instanceof HTMLImageElement ? event.relatedTarget : null;
  if (!(event.target instanceof HTMLImageElement) || (relatedImage && photoGallery.contains(relatedImage))) return;
  photoHoverPreview.classList.remove('is-visible');
  photoHoverPreview.setAttribute('aria-hidden', 'true');
  photoHoverImage.removeAttribute('src');
});
document.addEventListener('click', (event) => {
  if (!event.target.closest('.address-lookup')) closeAddressSuggestions();
});
document.querySelector('#location-next').addEventListener('click', () => {
  const town = locationTown.value.trim();
  const availability = document.querySelector('#location-availability').value;
  const lastname = document.querySelector('#contact-lastname').value.trim();
  const firstname = document.querySelector('#contact-firstname').value.trim();
  const phone = document.querySelector('#contact-phone').value.trim();
  if (!town || !availability || !lastname || !firstname || !phone) {
    locationFeedback.textContent = 'Indiquez la commune, une disponibilité et vos coordonnées.';
    return;
  }
  locationFeedback.textContent = '';
  document.querySelector('#summary-service').textContent = serviceSelection.textContent.replace('Besoin sélectionné : ', '').replace(/\.$/, '');
  document.querySelector('#summary-object').textContent = detailObject.value.trim() || 'Non précisé';
  document.querySelector('#summary-description').textContent = detailDescription.value.trim() || 'Non précisée';
  const address = locationAddress.value.trim();
  const postcode = locationPostcode.value.trim();
  const access = document.querySelector('#location-access').value.trim();
  const photoFiles = [...document.querySelector('#detail-photo').files];
  const photoNames = photoFiles.map(file => file.name);
  document.querySelector('#summary-location').textContent = [address, postcode, town].filter(Boolean).join(', ');
  document.querySelector('#summary-access').textContent = access || 'Aucune précision';
  document.querySelector('#summary-availability').textContent = availability;
  document.querySelector('#summary-urgency').textContent = document.querySelector('#location-urgency').value || 'Non précisée';
  document.querySelector('#summary-photo').textContent = photoNames.length ? `${photoNames.length} photo${photoNames.length > 1 ? 's' : ''} : ${photoNames.join(', ')}` : 'Aucune photo ajoutée';
  document.querySelector('#summary-name').textContent = `${firstname} ${lastname}`;
  document.querySelector('#summary-phone').textContent = phone;
  const photoEmpty = document.querySelector('#summary-photo-empty');
  photoGallery.querySelectorAll('img').forEach((image) => {
    if (image.src.startsWith('blob:')) URL.revokeObjectURL(image.src);
    image.remove();
  });
  if (photoFiles.length) {
    photoFiles.forEach((file, index) => {
      const image = document.createElement('img');
      image.src = URL.createObjectURL(file);
      image.alt = `Aperçu de la photo ${index + 1}`;
      photoGallery.insertBefore(image, photoEmpty);
    });
    photoEmpty.hidden = true;
  } else {
    photoEmpty.hidden = false;
  }
  summaryFeedback.textContent = '';
  humanVerification.hidden = true;
  resetHumanGame();
  requestPdf.hidden = true;
  requestPdfViewer.removeAttribute('data');
  requestPdfDownload.removeAttribute('href');
  updateProcessProgress(60, 'Étape 4 sur 5');
  transitionForward(() => {
    serviceLocation.hidden = true;
    serviceSummary.hidden = false;
  });
});
document.querySelector('#summary-back').addEventListener('click', () => {
  serviceSummary.hidden = true;
  updateProcessProgress(40, 'Étape 3 sur 5');
  serviceLocation.hidden = false;
});
document.querySelector('#summary-confirm').addEventListener('click', () => {
  summaryFeedback.textContent = '';
  updateProcessProgress(80, 'Vérification finale');
  humanVerification.hidden = false;
  resetHumanGame();
  humanGame.focus();
});
humanBalls.forEach((ball) => {
  ball.addEventListener('click', () => {
    if (humanGameSequenceIndex >= humanGameSequence.length) return;
    const color = ball.dataset.ballColor;
    moveHumanBalls();
    if (color === humanGameSequence[humanGameSequenceIndex]) {
      humanGameSequenceIndex += 1;
      humanGameRound = humanGameSequenceIndex;
      humanGameStatus.textContent = `${humanGameRound} / 3`;
      humanFeedback.textContent = '';
      if (humanGameSequenceIndex === humanGameSequence.length) {
        humanBalls.forEach((item) => { item.disabled = true; });
        humanContinue.disabled = false;
        humanFeedback.textContent = 'Vérification validée. Vous pouvez continuer.';
      }
      return;
    }
    humanGameSequenceIndex = 0;
    humanGameRound = 0;
    humanGameStatus.textContent = '0 / 3';
    humanFeedback.textContent = 'Vérification non validée. Recommencez.';
  });
});
function preparePhotoData(files) {
  const selectedFiles = [...(files || [])].slice(0, 3);
  if (!selectedFiles.length) return Promise.resolve([]);
  return Promise.all(selectedFiles.map((file) => new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      const maxDimension = 1200;
      const scale = Math.min(1, maxDimension / Math.max(image.naturalWidth, image.naturalHeight));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(objectUrl);
      resolve(canvas.toDataURL('image/jpeg', 0.78));
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error('Une des photos sélectionnées ne peut pas être préparée.'));
    };
    image.src = objectUrl;
  })));
}
humanContinue.addEventListener('click', async () => {
  if (humanGameRound < 3) return;
  humanContinue.disabled = true;
  humanContinue.textContent = 'Génération et envoi en cours…';
  humanFeedback.textContent = 'Préparation du PDF et envoi du courriel…';
  const photoFiles = [...document.querySelector('#detail-photo').files];
  let photoData = [];
  try {
    photoData = await preparePhotoData(photoFiles);
  } catch (error) {
    humanContinue.disabled = false;
    humanContinue.textContent = 'Réessayer l’envoi →';
    humanFeedback.textContent = error.message;
    return;
  }
  const payload = {
    service: serviceSelection.textContent.replace('Besoin sélectionné : ', '').replace(/\.$/, ''),
    object: detailObject.value.trim(),
    description: detailDescription.value.trim(),
    town: document.querySelector('#location-town').value.trim(),
    postcode: document.querySelector('#location-postcode').value.trim(),
    address: document.querySelector('#location-address').value.trim(),
    access: document.querySelector('#location-access').value.trim(),
    availability: document.querySelector('#location-availability').value,
    urgency: document.querySelector('#location-urgency').value,
    lastname: document.querySelector('#contact-lastname').value.trim(),
    firstname: document.querySelector('#contact-firstname').value.trim(),
    phone: document.querySelector('#contact-phone').value.trim(),
    photo_name: photoFiles.map(file => file.name),
    photo_data: photoData,
    human_confirmed: true,
  };
  try {
    const response = await fetch('/api/submit-request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const result = await response.json();
      throw new Error(result.error || 'Envoi impossible.');
    }
    const pdfBlob = await response.blob();
    const pdfUrl = URL.createObjectURL(pdfBlob);
    const requestId = response.headers.get('X-Request-ID') || 'demande';
    requestPdfViewer.setAttribute('data', pdfUrl);
    requestPdfDownload.href = pdfUrl;
    requestPdfDownload.download = `demande-${requestId}.pdf`;
    updateProcessProgress(100, 'Processus terminé');
    transitionForward(() => {
      serviceSummary.hidden = true;
      requestPdf.hidden = false;
    });
    humanContinue.textContent = 'Demande envoyée';
    humanFeedback.textContent = `Votre demande a été envoyée. Référence : ${requestId}.`;
  } catch (error) {
    humanContinue.disabled = false;
    humanContinue.textContent = 'Réessayer l’envoi →';
    humanFeedback.textContent = error.message;
  }
});
if (!mobileSceneDisabled && animationFrameId === null) animationFrameId = window.requestAnimationFrame(animate);
window.setTimeout(revealWelcome, 700);
window.__ATELIER_ROULANT_READY = true;
window.__ATELIER_ROULANT_CAMERA = camera;
