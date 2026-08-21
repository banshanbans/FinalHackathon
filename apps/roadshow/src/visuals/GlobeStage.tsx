import { Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import {
  AdditiveBlending,
  BackSide,
  Color,
  Group,
  Matrix4,
  Mesh,
  MeshBasicMaterial,
  MeshPhysicalMaterial,
  ShaderMaterial,
  SRGBColorSpace,
  TextureLoader,
  Vector2,
  Vector3,
} from "three";
import type { MutableRefObject } from "react";
import type { RoadshowFeatureCollection } from "../contracts";
import { appleCameraProgress } from "../motion/progress";
import { chinaLiftBounds, createChinaLiftTexture } from "./mapTextures";

interface TransitionSignal {
  value: number;
}

interface GlobeWorldProps {
  map: RoadshowFeatureCollection;
  transition: MutableRefObject<TransitionSignal>;
  returnTransition?: MutableRefObject<TransitionSignal>;
}

const atmosphereVertex = `
  varying vec3 vNormal;
  varying vec3 vWorldPosition;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vWorldPosition = worldPosition.xyz;
    gl_Position = projectionMatrix * viewMatrix * worldPosition;
  }
`;

const atmosphereFragment = `
  uniform float uOpacity;
  varying vec3 vNormal;
  varying vec3 vWorldPosition;
  void main() {
    vec3 viewDirection = normalize(cameraPosition - vWorldPosition);
    float fresnel = pow(1.0 - max(dot(vNormal, viewDirection), 0.0), 4.2);
    gl_FragColor = vec4(0.388, 0.835, 0.780, fresnel * 0.58 * uOpacity);
  }
`;

const chinaLiftVertex = `
  uniform float uMorph;
  uniform mat4 uGlobeMatrix;
  uniform vec2 uFlatSize;
  uniform vec2 uFlatOffset;
  varying vec2 vUv;

  const float PI = 3.141592653589793;

  float mercatorY(float latitude) {
    float limited = clamp(latitude, -85.0, 85.0);
    float radiansLatitude = radians(limited);
    return log(tan(PI * 0.25 + radiansLatitude * 0.5));
  }

  void main() {
    vUv = uv;
    float longitude = mix(${chinaLiftBounds.longitudeMin.toFixed(1)}, ${chinaLiftBounds.longitudeMax.toFixed(1)}, uv.x);
    float latitude = mix(${chinaLiftBounds.latitudeMin.toFixed(1)}, ${chinaLiftBounds.latitudeMax.toFixed(1)}, uv.y);
    float phi = radians(90.0 - latitude);
    float theta = radians(longitude + 180.0);
    float radius = 3.172;
    vec3 spherePosition = vec3(
      -radius * sin(phi) * cos(theta),
      radius * cos(phi),
      radius * sin(phi) * sin(theta)
    );
    vec3 sphereWorld = (uGlobeMatrix * vec4(spherePosition, 1.0)).xyz;

    float mercatorMin = mercatorY(${chinaLiftBounds.latitudeMin.toFixed(1)});
    float mercatorMax = mercatorY(${chinaLiftBounds.latitudeMax.toFixed(1)});
    float normalizedMercator = (mercatorY(latitude) - mercatorMin) / (mercatorMax - mercatorMin);
    vec3 flatWorld = vec3(
      (uv.x - 0.5) * uFlatSize.x + uFlatOffset.x,
      (normalizedMercator - 0.5) * uFlatSize.y + uFlatOffset.y,
      3.14
    );

    float smoothMorph = uMorph * uMorph * (3.0 - 2.0 * uMorph);
    vec3 worldPosition = mix(sphereWorld, flatWorld, smoothMorph);
    gl_Position = projectionMatrix * viewMatrix * vec4(worldPosition, 1.0);
  }
`;

const chinaLiftFragment = `
  uniform sampler2D uMap;
  uniform float uOpacity;
  uniform float uGlow;
  varying vec2 vUv;

  void main() {
    vec4 color = texture2D(uMap, vUv);
    if (color.a < 0.015) discard;
    vec3 liftedColor = color.rgb + vec3(0.07, 0.17, 0.16) * uGlow;
    gl_FragColor = vec4(liftedColor, color.a * uOpacity);
  }
`;

function latitudeLongitudeToVector(latitude: number, longitude: number, radius: number): Vector3 {
  const phi = ((90 - latitude) * Math.PI) / 180;
  const theta = ((longitude + 180) * Math.PI) / 180;
  return new Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
}

function GlobeWorld({ map, transition, returnTransition }: GlobeWorldProps) {
  const baseTexture = useLoader(
    TextureLoader,
    `${import.meta.env.BASE_URL}assets/earth/blue-marble-december-4096.webp`,
  );
  const chinaLiftTexture = useMemo(() => createChinaLiftTexture(map), [map]);
  const globeGroup = useRef<Group>(null);
  const baseMaterial = useRef<MeshPhysicalMaterial>(null);
  const pulseOuter = useRef<Mesh>(null);
  const pulseCore = useRef<Mesh>(null);
  const atmosphereMaterial = useRef<ShaderMaterial>(null);
  const chinaLiftMaterial = useRef<ShaderMaterial>(null);
  const chinaLiftUniforms = useMemo(
    () => ({
      uMap: { value: chinaLiftTexture },
      uMorph: { value: 0 },
      uOpacity: { value: 0.84 },
      uGlow: { value: 0 },
      uGlobeMatrix: { value: new Matrix4() },
      uFlatSize: { value: new Vector2(3.18, 2.12) },
      uFlatOffset: { value: new Vector2(1.56, 0.26) },
    }),
    [chinaLiftTexture],
  );

  useEffect(() => {
    baseTexture.colorSpace = SRGBColorSpace;
    baseTexture.anisotropy = 8;
    baseTexture.needsUpdate = true;
    return () => {
      chinaLiftTexture.dispose();
    };
  }, [baseTexture, chinaLiftTexture]);

  const beijing = useMemo(() => latitudeLongitudeToVector(39.9042, 116.4074, 3.182), []);

  useFrame(({ clock, camera }) => {
    const returnProgress = Math.min(1, Math.max(0, returnTransition?.current.value ?? 0));
    const primaryProgress = Math.min(1, Math.max(0, transition.current.value));
    const progress = primaryProgress * (1 - returnProgress) + 0.04 * returnProgress;
    const cameraEase = appleCameraProgress(progress);
    const focusProgress = Math.min(1, Math.max(0, (progress - 0.14) / 0.42));
    const focusStageEase = appleCameraProgress(focusProgress);
    const morphProgress = Math.min(1, Math.max(0, (progress - 0.72) / 0.28));
    const morphEase = morphProgress * morphProgress * (3 - 2 * morphProgress);
    const globeDeparture = Math.min(1, Math.max(0, (progress - 0.74) / 0.26));
    const globeDepartureEase = globeDeparture * globeDeparture * (3 - 2 * globeDeparture);

    if (globeGroup.current) {
      globeGroup.current.position.set(1.62, 0.14, 0);
      globeGroup.current.scale.setScalar(1);
      globeGroup.current.rotation.set(0.58, Math.PI - 0.25, -0.025);
      globeGroup.current.updateMatrixWorld(true);
    }
    if (baseMaterial.current) {
      const globeLight = 1 - globeDepartureEase * 0.68;
      baseMaterial.current.color.setRGB(0.388 * globeLight, 0.475 * globeLight, 0.525 * globeLight);
    }
    if (atmosphereMaterial.current) {
      atmosphereMaterial.current.uniforms.uOpacity.value = 1 - focusStageEase;
    }
    if (chinaLiftMaterial.current && globeGroup.current) {
      chinaLiftMaterial.current.uniforms.uMorph.value = morphEase;
      chinaLiftMaterial.current.uniforms.uOpacity.value =
        0.84 + focusStageEase * 0.16 - morphEase * 0.28;
      chinaLiftMaterial.current.uniforms.uGlow.value =
        focusStageEase * (1 - morphEase * 0.35);
      chinaLiftMaterial.current.uniforms.uGlobeMatrix.value.copy(globeGroup.current.matrixWorld);
    }

    const pulse = 1 + Math.sin(clock.elapsedTime * 2.2) * 0.5;
    if (pulseOuter.current) {
      pulseOuter.current.scale.setScalar(0.8 + pulse * 0.38);
      const material = pulseOuter.current.material as MeshBasicMaterial;
      material.opacity = (0.3 + (1 - pulse / 2) * 0.3) * (1 - morphEase);
    }
    if (pulseCore.current) {
      pulseCore.current.scale.setScalar(0.9 + pulse * 0.08);
      (pulseCore.current.material as MeshBasicMaterial).opacity = 1 - morphEase;
    }
    // One physical dolly: globe scale is fixed and the camera never pulls back.
    // The late projection occupies the same apparent China footprint.
    camera.position.set(1.56 * cameraEase, 0.26 * cameraEase, 8.45 - 2.45 * cameraEase);
    camera.lookAt(1.56 * cameraEase, 0.26 * cameraEase, 3.14 * cameraEase);
  });

  return (
    <>
      <ambientLight intensity={0.22} />
      <directionalLight color="#dceeff" intensity={2.1} position={[5, 5, 7]} />
      <pointLight color="#4ba5c5" intensity={10} distance={14} position={[4.8, 2.8, 4.5]} />
      <pointLight color="#0c3145" intensity={7} distance={12} position={[-4, -2, 1]} />

      <group ref={globeGroup}>
        <mesh>
          <sphereGeometry args={[3.15, 192, 128]} />
          <meshPhysicalMaterial
            ref={baseMaterial}
            map={baseTexture}
            color={new Color("#637986")}
            roughness={0.88}
            metalness={0.05}
            clearcoat={0.12}
            clearcoatRoughness={0.72}
          />
        </mesh>
        <mesh>
          <sphereGeometry args={[3.205, 128, 96]} />
          <shaderMaterial
            ref={atmosphereMaterial}
            vertexShader={atmosphereVertex}
            fragmentShader={atmosphereFragment}
            uniforms={{ uOpacity: { value: 1 } }}
            side={BackSide}
            transparent
            blending={AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
        <group
          position={beijing}
          ref={(node) => {
            if (node) node.lookAt(beijing.clone().multiplyScalar(2));
          }}
        >
          <mesh ref={pulseOuter}>
            <ringGeometry args={[0.055, 0.1, 64]} />
            <meshBasicMaterial color="#f5d991" transparent opacity={0.46} blending={AdditiveBlending} />
          </mesh>
          <mesh ref={pulseCore} position={[0, 0, 0.006]}>
            <circleGeometry args={[0.044, 48]} />
            <meshBasicMaterial color="#fff0ba" blending={AdditiveBlending} />
          </mesh>
        </group>
      </group>

      <mesh frustumCulled={false} renderOrder={12}>
        <planeGeometry args={[1, 1, 192, 120]} />
        <shaderMaterial
          ref={chinaLiftMaterial}
          uniforms={chinaLiftUniforms}
          vertexShader={chinaLiftVertex}
          fragmentShader={chinaLiftFragment}
          transparent
          depthWrite={false}
          depthTest={false}
        />
      </mesh>
    </>
  );
}

interface GlobeStageProps extends GlobeWorldProps {}

export function GlobeStage({ map, transition, returnTransition }: GlobeStageProps) {
  const maxDpr =
    typeof window === "undefined"
      ? 1
      : Math.min(window.innerWidth >= 2560 ? 1 : 1.5, window.devicePixelRatio || 1);
  return (
    <Canvas
      className="globe-canvas"
      dpr={[1, maxDpr]}
      camera={{ fov: 42, near: 0.1, far: 100, position: [0, 0, 8.45] }}
      gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
      onCreated={({ gl }) => gl.setClearColor("#000000", 1)}
    >
      <Suspense fallback={null}>
        <GlobeWorld map={map} transition={transition} returnTransition={returnTransition} />
      </Suspense>
    </Canvas>
  );
}
