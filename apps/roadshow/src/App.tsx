import { ArrowRight, Coins, Laptop, Plus } from "@phosphor-icons/react";
import gsap from "gsap";
import { useEffect, useRef, useState } from "react";
import { loadRoadshowData, type RoadshowData } from "./data";
import {
  appleCameraProgress,
  clampSceneProgress,
  clampStoryProgress,
  progressDeltaForKeyboard,
  progressDeltaForWheel,
  STORY_PROGRESS_MAX,
  stageForMasterProgress,
} from "./motion/progress";
import { useRoadshowStore } from "./store";
import { GlobeStage } from "./visuals/GlobeStage";

interface TransitionSignal {
  value: number;
}

function Loader() {
  return (
    <main className="loading-screen cinematic-black" aria-live="polite">
      <p className="scene-status">正在建立新能源汽车全国视角</p>
    </main>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <main className="error-screen" role="alert">
      <p className="error-eyebrow">13110</p>
      <h1>演示数据未能通过校验。</h1>
      <p>{message}</p>
    </main>
  );
}

export default function App() {
  const [data, setData] = useState<RoadshowData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const globeShellRef = useRef<HTMLDivElement>(null);
  const cockpitRef = useRef<HTMLDivElement>(null);
  const cockpitImageRef = useRef<HTMLImageElement>(null);
  const cockpitDisplayRef = useRef<HTMLDivElement>(null);
  const shoppingRef = useRef<HTMLDivElement>(null);
  const subsidyTagRef = useRef<HTMLDivElement>(null);
  const fundingRef = useRef<HTMLDivElement>(null);
  const fundingSourcesRef = useRef<HTMLDivElement>(null);
  const poolRef = useRef<HTMLDivElement>(null);
  const circleBridgeRef = useRef<HTMLDivElement>(null);
  const circleRippleOuterRef = useRef<HTMLDivElement>(null);
  const circleRippleFarRef = useRef<HTMLDivElement>(null);
  const ratioRef = useRef<HTMLDivElement>(null);
  const ratioBaseRef = useRef<HTMLSpanElement>(null);
  const ratioChangedRef = useRef<HTMLSpanElement>(null);
  const ratioWestRef = useRef<HTMLSpanElement>(null);
  const ratioSliderFillRef = useRef<HTMLDivElement>(null);
  const ratioSliderThumbRef = useRef<HTMLDivElement>(null);
  const ratioPresetsRef = useRef<HTMLDivElement>(null);
  const rippleRef = useRef<HTMLDivElement>(null);
  const impactRef = useRef<HTMLDivElement>(null);
  const blackoutRef = useRef<HTMLDivElement>(null);
  const identityRef = useRef<HTMLDivElement>(null);
  const handoffRef = useRef<HTMLDivElement>(null);
  const southChinaSeaRef = useRef<HTMLElement>(null);
  const policyWorldRef = useRef<HTMLDivElement>(null);
  const policyWorldImageRef = useRef<HTMLDivElement>(null);
  const policySignalCopyRef = useRef<HTMLDivElement>(null);
  const provinceScreenRef = useRef<HTMLDivElement>(null);
  const provinceScreenImageRef = useRef<HTMLImageElement>(null);
  const provinceSignalCopyRef = useRef<HTMLDivElement>(null);
  const provinceCloseRef = useRef<HTMLDivElement>(null);
  const provinceCloseImageRef = useRef<HTMLImageElement>(null);
  const vehicleWorldRef = useRef<HTMLDivElement>(null);
  const vehicleWorldImageRef = useRef<HTMLImageElement>(null);
  const cabinEdgesRef = useRef<HTMLDivElement>(null);
  const enterpriseDisplayRef = useRef<HTMLDivElement>(null);
  const enterpriseShadeRef = useRef<HTMLDivElement>(null);
  const enterprisePortalRef = useRef<HTMLDivElement>(null);
  const chapterProgressRef = useRef<HTMLDivElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);
  const transition = useRef<TransitionSignal>({ value: 0 });
  const returnTransition = useRef<TransitionSignal>({ value: 0 });
  const setStage = useRoadshowStore((state) => state.setStage);
  const stage = useRoadshowStore((state) => state.stage);

  useEffect(() => {
    let active = true;
    void loadRoadshowData()
      .then((result) => {
        if (!active) return;
        setData(result);
        setStage("cockpit");
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : "未知数据错误");
        setStage("error");
      });
    return () => {
      active = false;
    };
  }, [setStage]);

  useEffect(() => {
    if (!data) return;
    rootRef.current?.focus({ preventScroll: true });
  }, [data]);

  useEffect(() => {
    if (!data || !rootRef.current) return undefined;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    gsap.ticker.lagSmoothing(0);

    const context = gsap.context(() => {
      gsap.set(globeShellRef.current, {
        scale: reducedMotion ? 1 : 0.4576,
        autoAlpha: reducedMotion ? 1 : 0,
        transformOrigin: "50% 45.75%",
      });
      gsap.set(cockpitRef.current, {
        autoAlpha: reducedMotion ? 0 : 1,
        scale: 1,
        transformOrigin: "50% 45.75%",
      });
      gsap.set(cockpitImageRef.current, { filter: "brightness(0.16)" });
      gsap.set(cockpitDisplayRef.current, { autoAlpha: reducedMotion ? 0 : 1 });
      gsap.set(
        [shoppingRef.current, fundingRef.current, ratioRef.current, rippleRef.current],
        { autoAlpha: 0 },
      );
      gsap.set([ratioChangedRef.current, ratioWestRef.current], { autoAlpha: 0 });
      gsap.set(circleBridgeRef.current, {
        autoAlpha: 0,
        left: "78%",
        top: "58%",
        width: "24%",
        scale: 0.76,
        borderColor: "rgba(99, 213, 199, 0.72)",
        boxShadow: "0 0 0 rgba(83, 184, 222, 0)",
      });
      gsap.set([circleRippleOuterRef.current, circleRippleFarRef.current], { autoAlpha: 0, scale: 1 });
      gsap.set(ratioSliderFillRef.current, { scaleX: 0 });
      gsap.set(ratioSliderThumbRef.current, { xPercent: 0 });
      gsap.set(blackoutRef.current, { autoAlpha: reducedMotion ? 0 : 0.78 });
      gsap.set(policyWorldRef.current, { autoAlpha: 0, scale: 1, transformOrigin: "50% 50%" });
      gsap.set(policyWorldImageRef.current, {
        scale: 3.05,
        xPercent: 10,
        yPercent: 9,
        transformOrigin: "43% 26%",
        clipPath: "inset(4% 38% 53% 17%)",
      });
      gsap.set(policySignalCopyRef.current, { autoAlpha: 0, y: 18 });
      gsap.set(provinceScreenRef.current, { autoAlpha: 0 });
      gsap.set(provinceScreenImageRef.current, {
        filter: "blur(10px) brightness(0.72)",
      });
      gsap.set(provinceSignalCopyRef.current, { autoAlpha: 0, y: 18 });
      gsap.set(provinceCloseRef.current, { autoAlpha: 0 });
      gsap.set(provinceCloseImageRef.current, {
        scale: reducedMotion ? 1.23 : 1.3,
        filter: reducedMotion ? "blur(0px)" : "blur(7px)",
        transformOrigin: "50% 46%",
      });
      gsap.set(vehicleWorldRef.current, {
        autoAlpha: reducedMotion ? 1 : 0,
        scale: reducedMotion ? 1.4 : 1,
        yPercent: reducedMotion ? -1.5 : 0,
        transformOrigin: "50% 81%",
        "--portal-core": "0%",
        "--portal-edge": "0%",
      });
      gsap.set(vehicleWorldImageRef.current, {
        scale: reducedMotion ? 1 : 1.28,
        transformOrigin: "44% 34%",
        autoAlpha: reducedMotion ? 1 : 0,
      });
      gsap.set(cabinEdgesRef.current, { autoAlpha: reducedMotion ? 0 : 0 });
      gsap.set(cabinEdgesRef.current?.querySelectorAll("img") ?? [], {
        scale: 1.02,
        transformOrigin: "44% 34%",
      });
      gsap.set(enterpriseDisplayRef.current, {
        autoAlpha: reducedMotion ? 1 : 0,
        y: reducedMotion ? 0 : 10,
        scale: reducedMotion ? 1 : 0.965,
      });
      gsap.set(enterpriseShadeRef.current, { autoAlpha: reducedMotion ? 0.76 : 0 });
      gsap.set(enterprisePortalRef.current, {
        autoAlpha: reducedMotion ? 0 : 0,
        scale: reducedMotion ? 18 : 0.92,
        transformOrigin: "50% 50%",
      });

      const prelude = gsap.timeline({ paused: true });
      prelude
        .to(
          cockpitImageRef.current,
          { filter: "brightness(0.52)", duration: 3.2, ease: "power3.out" },
          0,
        )
        .to(blackoutRef.current, { autoAlpha: 0, duration: 3.2, ease: "power3.out" }, 0)
        .to(
          cockpitRef.current,
          { scale: 1.48, duration: 3.2, ease: appleCameraProgress },
          3.2,
        )
        .to(
          cockpitImageRef.current,
          { filter: "brightness(1)", duration: 1.9, ease: "power3.out" },
          3.15,
        )
        .fromTo(
          shoppingRef.current,
          { autoAlpha: 0, y: 14, scale: 0.97 },
          { autoAlpha: 1, y: 0, scale: 1, duration: 1.1, ease: "power3.out" },
          3.2,
        )
        .fromTo(
          subsidyTagRef.current,
          { scale: 0.86 },
          { scale: 1, duration: 1.15, ease: appleCameraProgress },
          4.05,
        )
        .to(shoppingRef.current, { autoAlpha: 0, y: -16, scale: 0.94, duration: 0.9 }, 8.15)
        .fromTo(
          fundingRef.current,
          { autoAlpha: 0, y: 16 },
          { autoAlpha: 1, y: 0, duration: 0.9, ease: "power3.out" },
          8.35,
        )
        .fromTo(
          fundingSourcesRef.current?.children ?? [],
          { autoAlpha: 0, x: -12 },
          { autoAlpha: 1, x: 0, duration: 0.75, stagger: 0.14, ease: "power2.out" },
          8.8,
        )
        .fromTo(
          poolRef.current,
          { autoAlpha: 0, scale: 0.76 },
          { autoAlpha: 1, scale: 1, duration: 1.4, ease: appleCameraProgress },
          9.55,
        )
        .to(
          circleBridgeRef.current,
          { autoAlpha: 1, scale: 1, duration: 1.4, ease: appleCameraProgress },
          9.55,
        )
        .to(fundingRef.current, { autoAlpha: 0, scale: 0.92, duration: 0.85 }, 13.05)
        .to(
          circleBridgeRef.current,
          { left: "24.5%", top: "52%", width: "37%", duration: 1.35, ease: appleCameraProgress },
          12.9,
        )
        .fromTo(
          ratioRef.current,
          { autoAlpha: 0, scale: 0.88 },
          { autoAlpha: 1, scale: 1, duration: 1.15, ease: appleCameraProgress },
          13.2,
        )
        .fromTo(
          ratioPresetsRef.current?.children ?? [],
          { autoAlpha: 0, y: 10 },
          { autoAlpha: 1, y: 0, duration: 0.65, stagger: 0.22, ease: "power2.out" },
          13.9,
        )
        .to(ratioPresetsRef.current?.children[2] ?? null, { color: "#63d5c7", duration: 0.45 }, 14.3)
        .to(ratioBaseRef.current, { autoAlpha: 0, y: -10, duration: 0.7 }, 16.35)
        .fromTo(
          ratioChangedRef.current,
          { autoAlpha: 0, y: 10 },
          { autoAlpha: 1, y: 0, duration: 0.9, ease: "power3.out" },
          16.35,
        )
        .to(ratioSliderFillRef.current, { scaleX: 0.5, duration: 1.05, ease: appleCameraProgress }, 16.25)
        .to(ratioSliderThumbRef.current, { left: "50%", duration: 1.05, ease: appleCameraProgress }, 16.25)
        .to(ratioPresetsRef.current?.children[2] ?? null, { color: "rgba(245,245,247,0.46)", duration: 0.35 }, 16.25)
        .to(ratioPresetsRef.current?.children[1] ?? null, { color: "#63d5c7", duration: 0.45 }, 16.45)
        .to(ratioChangedRef.current, { autoAlpha: 0, y: -10, duration: 0.7 }, 18.05)
        .fromTo(
          ratioWestRef.current,
          { autoAlpha: 0, y: 10 },
          { autoAlpha: 1, y: 0, duration: 0.9, ease: "power3.out" },
          18.05,
        )
        .to(ratioSliderFillRef.current, { scaleX: 1, duration: 1.05, ease: appleCameraProgress }, 17.95)
        .to(ratioSliderThumbRef.current, { left: "100%", duration: 1.05, ease: appleCameraProgress }, 17.95)
        .to(ratioPresetsRef.current?.children[1] ?? null, { color: "rgba(245,245,247,0.46)", duration: 0.35 }, 17.95)
        .to(ratioPresetsRef.current?.children[0] ?? null, { color: "#63d5c7", duration: 0.45 }, 18.15)
        .to(ratioRef.current, { autoAlpha: 0, scale: 1.08, duration: 0.9 }, 20.2)
        .to(
          circleBridgeRef.current,
          { left: "24%", top: "50%", width: "32%", duration: 1.05, ease: appleCameraProgress },
          20.1,
        )
        .fromTo(
          rippleRef.current,
          { autoAlpha: 0, scale: 0.88 },
          { autoAlpha: 1, scale: 1, duration: 1.1, ease: appleCameraProgress },
          20.3,
        )
        .fromTo(
          circleRippleOuterRef.current,
          { autoAlpha: 0, scale: 1 },
          { autoAlpha: 0.34, scale: 1.58, duration: 1.55, ease: "power2.out" },
          20.45,
        )
        .fromTo(
          circleRippleFarRef.current,
          { autoAlpha: 0, scale: 1 },
          { autoAlpha: 0.16, scale: 2.05, duration: 1.8, ease: "power2.out" },
          20.7,
        )
        .fromTo(
          impactRef.current?.children ?? [],
          { autoAlpha: 0, y: 9 },
          { autoAlpha: 1, y: 0, duration: 0.58, stagger: 0.18, ease: "power2.out" },
          20.9,
        )
        .to(
          circleBridgeRef.current,
          {
            left: "50%",
            top: "50%",
            width: "54%",
            borderColor: "rgba(111, 205, 238, 0.9)",
            boxShadow: "0 0 24px rgba(83, 184, 222, 0.42)",
            duration: 1.45,
            ease: appleCameraProgress,
          },
          22.05,
        )
        .to(
          [circleRippleOuterRef.current, circleRippleFarRef.current],
          { autoAlpha: 0, scale: 1.1, duration: 0.9, ease: "power2.in" },
          22.05,
        )
        .to(rippleRef.current, { autoAlpha: 0, duration: 0.8, ease: "power2.inOut" }, 22.15)
        .to(globeShellRef.current, { autoAlpha: 1, duration: 1.55, ease: "power2.inOut" }, 22.7)
        .to(circleBridgeRef.current, { autoAlpha: 0, duration: 1.05, ease: "power2.inOut" }, 22.95)
        .to(cockpitDisplayRef.current, { autoAlpha: 0, duration: 1.05, ease: "power2.inOut" }, 23.25)
        .to(
          cockpitRef.current,
          { scale: 3.234, duration: 4.8, ease: appleCameraProgress },
          24.3,
        )
        .to(
          globeShellRef.current,
          { scale: 1, duration: 4.8, ease: appleCameraProgress },
          24.3,
        )
        .to(
          cockpitRef.current,
          { autoAlpha: 0, duration: 0.35, ease: "power2.out" },
          28.7,
        );

      const focusTimeline = gsap.timeline({ paused: true });
      focusTimeline
        .to(
          transition.current,
          { value: 1, duration: reducedMotion ? 0.01 : 6.4, ease: "none" },
          0,
        )
        .fromTo(
          identityRef.current,
          { autoAlpha: 0, y: 44 },
          { autoAlpha: 1, y: 0, duration: reducedMotion ? 0.01 : 1.18, ease: "power3.out" },
          reducedMotion ? 0 : 4.18,
        )
        .fromTo(
          identityRef.current?.querySelectorAll(".identity-item") ?? [],
          { autoAlpha: 0, y: 22 },
          {
            autoAlpha: 1,
            y: 0,
            duration: reducedMotion ? 0.01 : 0.88,
            stagger: reducedMotion ? 0 : 0.16,
            ease: "power3.out",
          },
          reducedMotion ? 0 : 4.3,
        )
        .fromTo(
          handoffRef.current,
          { autoAlpha: 0, y: -14 },
          { autoAlpha: 1, y: 0, duration: reducedMotion ? 0.01 : 0.86, ease: "power2.out" },
          reducedMotion ? 0 : 5.52,
        )
        .fromTo(
          southChinaSeaRef.current,
          { autoAlpha: 0, y: 18 },
          { autoAlpha: 1, y: 0, duration: reducedMotion ? 0.01 : 1.1, ease: "power3.out" },
          reducedMotion ? 0 : 4.72,
        )
        ;

      const policyTimeline = gsap.timeline({ paused: true });
      policyTimeline
        .to(
          [handoffRef.current, identityRef.current, southChinaSeaRef.current, chapterProgressRef.current],
          { autoAlpha: 0, duration: reducedMotion ? 0.01 : 1.15, ease: "power2.inOut" },
          0,
        )
        .to(
          policyWorldRef.current,
          { autoAlpha: 1, duration: reducedMotion ? 0.01 : 1.8, ease: "power2.inOut" },
          0.4,
        )
        .to(
          globeShellRef.current,
          { autoAlpha: 0, duration: reducedMotion ? 0.01 : 1.8, ease: "power2.inOut" },
          1.2,
        )
        .to(
          policyWorldImageRef.current,
          {
            scale: 1.23,
            xPercent: 0,
            yPercent: 0,
            clipPath: "inset(0% 0% 0% 0%)",
            duration: reducedMotion ? 0.01 : 6.4,
            ease: appleCameraProgress,
          },
          0,
        )
        .to(
          policySignalCopyRef.current,
          { autoAlpha: 1, y: 0, duration: reducedMotion ? 0.01 : 0.95, ease: "power3.out" },
          reducedMotion ? 0 : 5.15,
        );

      const vehicleTimeline = gsap.timeline({ paused: true });
      vehicleTimeline
        .to(
          vehicleWorldRef.current,
          { autoAlpha: 1, duration: reducedMotion ? 0.01 : 0.35, ease: "power2.out" },
          0,
        )
        .to(
          cabinEdgesRef.current,
          { autoAlpha: 1, duration: reducedMotion ? 0.01 : 2.8, ease: "power3.inOut" },
          reducedMotion ? 0 : 0.4,
        )
        .to(
          cabinEdgesRef.current?.querySelectorAll("img") ?? [],
          { scale: 1, duration: reducedMotion ? 0.01 : 4.8, ease: appleCameraProgress },
          0,
        )
        .to(
          vehicleWorldImageRef.current,
          { autoAlpha: 1, duration: reducedMotion ? 0.01 : 2, ease: "power2.inOut" },
          reducedMotion ? 0 : 3.5,
        )
        .to(
          cabinEdgesRef.current,
          { autoAlpha: 0, duration: reducedMotion ? 0.01 : 1.8, ease: "power2.inOut" },
          reducedMotion ? 0 : 3.75,
        )
        .to(
          provinceCloseRef.current,
          { autoAlpha: 0, duration: reducedMotion ? 0.01 : 2, ease: "power2.inOut" },
          reducedMotion ? 0 : 3.55,
        )
        .to(
          vehicleWorldImageRef.current,
          { scale: 1, duration: reducedMotion ? 0.01 : 6.4, ease: appleCameraProgress },
          0,
        );

      const provinceTimeline = gsap.timeline({ paused: true });
      provinceTimeline
        .to(
          policySignalCopyRef.current,
          { autoAlpha: 0, y: 12, duration: reducedMotion ? 0.01 : 0.85, ease: "power2.inOut" },
          0,
        )
        .to(
          policyWorldRef.current,
          { scale: 1.62, duration: reducedMotion ? 0.01 : 6.4, ease: appleCameraProgress },
          0,
        )
        .to(
          provinceCloseRef.current,
          {
            autoAlpha: 1,
            duration: reducedMotion ? 0.01 : 2.4,
            ease: "power2.inOut",
          },
          reducedMotion ? 0 : 2.45,
        )
        .to(
          policyWorldRef.current,
          { autoAlpha: 0, duration: reducedMotion ? 0.01 : 2.4, ease: "power2.inOut" },
          reducedMotion ? 0 : 2.55,
        )
        .to(
          provinceCloseImageRef.current,
          {
            scale: 1,
            filter: "blur(0px)",
            duration: reducedMotion ? 0.01 : 5.2,
            ease: appleCameraProgress,
          },
          1.2,
        );

      const enterpriseTimeline = gsap.timeline({ paused: true });
      enterpriseTimeline
        .to(
          vehicleWorldRef.current,
          {
            scale: 1.72,
            yPercent: -8,
            duration: reducedMotion ? 0.01 : 6.4,
            ease: appleCameraProgress,
          },
          0,
        )
        .to(
          enterpriseShadeRef.current,
          { autoAlpha: 0.78, duration: reducedMotion ? 0.01 : 4.4, ease: "power2.inOut" },
          reducedMotion ? 0 : 0.45,
        )
        .to(
          enterpriseDisplayRef.current,
          {
            autoAlpha: 1,
            y: 0,
            scale: 1,
            duration: reducedMotion ? 0.01 : 1.4,
            ease: "power3.out",
          },
          reducedMotion ? 0 : 2.15,
        );

      const earthReturnTimeline = gsap.timeline({ paused: true });
      earthReturnTimeline
        .to(
          enterpriseDisplayRef.current,
          { autoAlpha: 0, scale: 0.9, duration: reducedMotion ? 0.01 : 1.25, ease: "power2.inOut" },
          0,
        )
        .to(
          enterprisePortalRef.current,
          { autoAlpha: 1, duration: reducedMotion ? 0.01 : 0.9, ease: "power2.out" },
          reducedMotion ? 0 : 0.35,
        )
        .to(
          globeShellRef.current,
          { autoAlpha: 1, duration: reducedMotion ? 0.01 : 1.2, ease: "power2.inOut" },
          reducedMotion ? 0 : 0.55,
        )
        .to(
          returnTransition.current,
          { value: 1, duration: reducedMotion ? 0.01 : 6.4, ease: "none" },
          0,
        )
        .to(
          vehicleWorldRef.current,
          {
            "--portal-core": "82%",
            "--portal-edge": "94%",
            duration: reducedMotion ? 0.01 : 6.4,
            ease: appleCameraProgress,
          },
          0,
        )
        .to(
          enterprisePortalRef.current,
          { scale: 18, duration: reducedMotion ? 0.01 : 6.4, ease: appleCameraProgress },
          0,
        )
        .to(
          vehicleWorldRef.current,
          { autoAlpha: 0, duration: reducedMotion ? 0.01 : 1.8, ease: "power2.inOut" },
          reducedMotion ? 0 : 4.25,
        );

      const driver = { current: 0, target: 0 };
      let programmaticTween: gsap.core.Tween | null = null;
      let didPromoteCanvasResolution = false;

      const applyProgress = () => {
        const progress = clampStoryProgress(driver.current);
        const preludeProgress = clampSceneProgress(progress / 0.7);
        const focusProgress = clampSceneProgress((progress - 0.7) / 0.3);
        const policyProgress = clampSceneProgress((progress - 1) / 0.26);
        const provinceProgress = clampSceneProgress((progress - 1.26) / 0.5);
        const vehicleProgress = clampSceneProgress((progress - 1.76) / 0.48);
        const enterpriseProgress = clampSceneProgress((progress - 2.24) / 0.42);
        const earthReturnProgress = clampSceneProgress((progress - 2.66) / (STORY_PROGRESS_MAX - 2.66));
        prelude.progress(preludeProgress);
        focusTimeline.progress(focusProgress);
        policyTimeline.progress(policyProgress);
        provinceTimeline.progress(provinceProgress);
        vehicleTimeline.progress(vehicleProgress);
        enterpriseTimeline.progress(enterpriseProgress);
        earthReturnTimeline.progress(earthReturnProgress);
        gsap.set(progressRef.current, { scaleX: 0.08 + (progress / STORY_PROGRESS_MAX) * 0.92 });
        setStage(stageForMasterProgress(progress));
        if (progress >= 0.7 && !didPromoteCanvasResolution) {
          didPromoteCanvasResolution = true;
          window.requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
        }
      };

      const cancelProgrammaticTween = () => {
        programmaticTween?.kill();
        programmaticTween = null;
      };

      const tickVirtualScroll = (_time: number, deltaTime: number) => {
        if (programmaticTween || Math.abs(driver.target - driver.current) < 0.0001) return;
        const smoothing = 1 - Math.exp(-Math.min(deltaTime, 64) / 180);
        driver.current += (driver.target - driver.current) * smoothing;
        if (Math.abs(driver.target - driver.current) < 0.0005) driver.current = driver.target;
        applyProgress();
      };

      const handleWheel = (event: WheelEvent) => {
        if (event.deltaY === 0) return;
        event.preventDefault();
        cancelProgrammaticTween();
        driver.target = clampStoryProgress(driver.target + progressDeltaForWheel(event.deltaY, event.deltaMode));
      };

      const moveByKeyboard = (event: globalThis.KeyboardEvent) => {
        if (event.metaKey || event.ctrlKey || event.altKey) return;
        const delta = progressDeltaForKeyboard(event.key, driver.target);
        if (delta === 0) return;
        event.preventDefault();
        cancelProgrammaticTween();
        driver.target = clampStoryProgress(driver.target + delta);
      };

      window.addEventListener("wheel", handleWheel, { passive: false });
      window.addEventListener("keydown", moveByKeyboard);
      gsap.ticker.add(tickVirtualScroll);

      if (reducedMotion) {
        driver.current = STORY_PROGRESS_MAX;
        driver.target = STORY_PROGRESS_MAX;
        applyProgress();
      }

      return () => {
        cancelProgrammaticTween();
        window.removeEventListener("wheel", handleWheel);
        window.removeEventListener("keydown", moveByKeyboard);
        gsap.ticker.remove(tickVirtualScroll);
      };
    }, rootRef);

    return () => {
      context.revert();
    };
  }, [data, setStage]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loader />;

  const stageIndex = {
    loading: 0,
    cockpit: 0,
    consumer: 0,
    funding: 0,
    ratio: 0,
    ripple: 0,
    orbital: 0,
    "china-focus": 1,
    "identity-reveal": 2,
    "causal-handoff": 3,
    "policy-signal": 3,
    "province-agent": 3,
    "vehicle-interior": 3,
    "enterprise-agent": 3,
    "earth-return": 0,
    error: 0,
  }[stage];
  const activeChapter = data.content.chapters[stageIndex] ?? data.content.chapters[0];
  const sceneStatus = {
    loading: "正在加载",
    cockpit: "新能源汽车座舱保持暗场",
    consumer: "国补从日常消费界面出现",
    funding: "中央与地方共同承担消费补贴",
    ratio: "三档承担比例依次出现",
    ripple: "比例变化正在触发政策涟漪",
    orbital: "全球视角",
    "china-focus": "镜头正在推进并聚焦中国",
    "identity-reveal": "13110主体结构已经出现",
    "causal-handoff": "全国政策因果舞台准备就绪",
    "policy-signal": "中国地图已显露为省级政策信号屏",
    "province-agent": "典型省份决策画像正在电子屏上展开",
    "vehicle-interior": "视角已后退进入新能源汽车座舱",
    "enterprise-agent": "车企模拟主体正在形成全国行动组合",
    "earth-return": "中控屏正在重新打开地球与中国版图",
    error: "加载失败",
  }[stage];

  return (
    <div
      className="roadshow"
      ref={rootRef}
      data-stage={stage}
      tabIndex={0}
      aria-keyshortcuts="ArrowUp ArrowDown ArrowLeft ArrowRight"
      onPointerDown={(event) => event.currentTarget.focus({ preventScroll: true })}
    >
      <section className="stage" aria-label="13110 新能源汽车产业协同推演开场">
        <div className="globe-shell" ref={globeShellRef}>
          <GlobeStage map={data.map} transition={transition} returnTransition={returnTransition} />
        </div>

        <div className="cockpit-layer" ref={cockpitRef}>
          <div className="cockpit-display" ref={cockpitDisplayRef}>
            <div className="circle-bridge" ref={circleBridgeRef} aria-hidden>
              <div className="circle-ripple circle-ripple-outer" ref={circleRippleOuterRef} />
              <div className="circle-ripple circle-ripple-far" ref={circleRippleFarRef} />
            </div>
            <div className="screen-state screen-shopping" ref={shoppingRef}>
              <div className="shopping-product-icon"><Laptop aria-hidden weight="thin" /></div>
              <div className="shopping-copy">
                <p>{data.content.explainer.consumer.eyebrow}</p>
                <h2>{data.content.explainer.consumer.product}</h2>
                <span>{data.content.explainer.consumer.price_label}</span>
              </div>
              <div className="subsidy-tag" ref={subsidyTagRef}>
                <span>{data.content.explainer.consumer.subsidy_label}</span>
                <strong>{data.content.explainer.consumer.subsidy_rate}</strong>
              </div>
            </div>

            <div className="screen-state screen-funding" ref={fundingRef}>
              <p className="screen-question">{data.content.explainer.funding.question}</p>
              <div className="funding-sources" ref={fundingSourcesRef}>
                <div><span>{data.content.explainer.funding.central_label}</span><strong>85{data.content.explainer.funding.unit_label}</strong></div>
                <Plus aria-hidden weight="light" />
                <div><span>{data.content.explainer.funding.local_label}</span><strong>15{data.content.explainer.funding.unit_label}</strong></div>
                <ArrowRight aria-hidden weight="light" />
              </div>
              <div className="funding-pool" ref={poolRef}>
                <Coins aria-hidden weight="thin" />
                <span>{data.content.explainer.funding.pool_label}</span>
                <strong>100{data.content.explainer.funding.unit_label}</strong>
              </div>
            </div>

            <div className="screen-state screen-ratio" ref={ratioRef}>
              <p>中央承担 / 地方承担</p>
              <div className="ratio-core">
                <span ref={ratioBaseRef}>85 / 15</span>
                <span ref={ratioChangedRef}>90 / 10</span>
                <span ref={ratioWestRef}>95 / 5</span>
              </div>
              <div className="policy-slider" aria-label="中央与地方承担比例变化示意">
                <div className="policy-slider-track">
                  <div className="policy-slider-fill" ref={ratioSliderFillRef} />
                  <div className="policy-slider-thumb" ref={ratioSliderThumbRef} />
                  <i /><i /><i />
                </div>
                <div className="policy-slider-labels"><span>85 / 15</span><span>90 / 10</span><span>95 / 5</span></div>
              </div>
              <div className="ratio-presets" ref={ratioPresetsRef}>
                {data.content.explainer.presets.map((preset) => (
                  <div key={preset.region}>
                    <span>{preset.region}</span>
                    <strong>{preset.central_share} / {preset.local_share}</strong>
                  </div>
                ))}
              </div>
            </div>

            <div className="screen-state screen-ripple" ref={rippleRef}>
              <div className="ripple-orbit" aria-hidden><Coins weight="thin" /></div>
              <h2>{data.content.explainer.ignition_question}</h2>
              <div className="impact-sequence" ref={impactRef}>
                {data.content.explainer.impacts.map((impact) => <span key={impact}>{impact}</span>)}
              </div>
            </div>
          </div>
          <img
            className="cockpit-frame"
            ref={cockpitImageRef}
            src={`${import.meta.env.BASE_URL}assets/cockpit/nev-cockpit-frame.png`}
            alt="新能源汽车座舱，中控屏从国补科普进入中国地球视角"
          />
        </div>
        <div className="opening-blackout" ref={blackoutRef} aria-hidden />

        <div className="policy-world" ref={policyWorldRef} aria-hidden={!(["policy-signal", "province-agent", "vehicle-interior"] as const).includes(stage as "policy-signal" | "province-agent" | "vehicle-interior")}>
          <div className="policy-world-media" ref={policyWorldImageRef}>
            <img
              className="policy-world-base"
              src={`${import.meta.env.BASE_URL}assets/policy-road/high-pylon-policy-signal.png`}
              alt="夜间高速公路旁的高位单柱省级政策信号屏，屏幕展示完整中国地图与南海诸岛"
            />
            <div className="province-screen-mask" ref={provinceScreenRef}>
              <img
                ref={provinceScreenImageRef}
                src={`${import.meta.env.BASE_URL}assets/policy-road/sichuan-province-agent-screen-source.png`}
                alt="四川本次实验省级决策画像：六轴画像、同伴观察与竞争信号、动力电池节点和购车意愿代理指数"
              />
            </div>
          </div>
          <div className="policy-signal-copy" ref={policySignalCopyRef}>
            <p>31 个省级决策主体</p>
            <h2>同一项中央政策，<br />正在发出不同信号。</h2>
          </div>
          <div className="policy-signal-copy province-signal-copy" ref={provinceSignalCopyRef}>
            <p>31 个省级决策主体</p>
            <h2>相似的省份，<br />做出不同选择。</h2>
          </div>
        </div>

        <div className="province-close-world" ref={provinceCloseRef} aria-hidden={stage !== "province-agent" && stage !== "vehicle-interior"}>
          <img
            ref={provinceCloseImageRef}
            src={`${import.meta.env.BASE_URL}assets/policy-road/province-agent-frontal-close.png`}
            alt="正面近距离省级Agent决策画像屏"
          />
        </div>

        <div className="vehicle-world" ref={vehicleWorldRef} aria-hidden={stage !== "vehicle-interior" && stage !== "enterprise-agent" && stage !== "earth-return"}>
          <img
            className="vehicle-full-frame"
            ref={vehicleWorldImageRef}
            src={`${import.meta.env.BASE_URL}assets/policy-road/high-pylon-province-from-nev-interior.png`}
            alt="从无品牌新能源汽车座舱内望向省级Agent决策画像屏"
          />
          <div className="cabin-edge-reveal" ref={cabinEdgesRef} aria-hidden>
            <img className="cabin-edge cabin-edge-left" src={`${import.meta.env.BASE_URL}assets/policy-road/high-pylon-province-from-nev-interior.png`} alt="" />
            <img className="cabin-edge cabin-edge-right" src={`${import.meta.env.BASE_URL}assets/policy-road/high-pylon-province-from-nev-interior.png`} alt="" />
            <img className="cabin-edge cabin-edge-lower" src={`${import.meta.env.BASE_URL}assets/policy-road/high-pylon-province-from-nev-interior.png`} alt="" />
          </div>
          <div className="enterprise-window-shade" ref={enterpriseShadeRef} aria-hidden />
          <div className="enterprise-earth-portal" ref={enterprisePortalRef} aria-hidden />
          <div className="enterprise-display" ref={enterpriseDisplayRef}>
            <p className="enterprise-eyebrow">10 家车企模拟主体</p>
            <h2>车企 Agent｜全国行动组合</h2>
            <div className="enterprise-metrics">
              <div><strong>31</strong><span>省级市场投入</span></div>
              <div><strong>0—3</strong><span>产能行动目标</span></div>
            </div>
            <div className="enterprise-actions"><span>销售投入</span><span>渠道策略</span><span>产能动作</span></div>
            <p className="enterprise-boundary">真实数据基线 / 模拟车企行动</p>
          </div>
        </div>

        <div className="causal-handoff" ref={handoffRef} aria-hidden={stage !== "causal-handoff"}>
          <p>{data.content.identity.handoff_label}</p>
          <h2>{data.content.identity.decision_question}</h2>
        </div>

        <div className="identity-reveal" ref={identityRef} aria-label="13110主体构成">
          {data.content.identity.items.map((item) => (
            <div className="identity-item" key={item.value}>
              <strong>{item.value}</strong>
              <span>{item.label}</span>
            </div>
          ))}
        </div>

        <figure className="south-china-sea-inset" ref={southChinaSeaRef}>
          <img
            src={`${import.meta.env.BASE_URL}assets/maps/south-china-sea-inset.webp`}
            alt="中国南海诸岛示意图"
          />
          <figcaption>南海诸岛</figcaption>
        </figure>

        <p className="scene-status" aria-live="polite">
          {sceneStatus}
        </p>

        <div className="chapter-progress" ref={chapterProgressRef} aria-hidden>
          <span>{String(activeChapter.index).padStart(2, "0")}</span>
          <div className="progress-track">
            <div className="progress-fill" ref={progressRef} />
          </div>
          <span>{String(data.content.chapters.length).padStart(2, "0")}</span>
        </div>

      </section>
    </div>
  );
}
