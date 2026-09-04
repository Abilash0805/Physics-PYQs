"use client";

import { useCallback, useMemo, useSyncExternalStore } from "react";

/**
 * A piece of state backed by localStorage, kept in step across every
 * component that reads the same key.
 *
 * Reading the stored value inside an effect and calling setState would make
 * each consumer render twice on load and would not notice writes made
 * elsewhere. `useSyncExternalStore` reads it as what it is - a store outside
 * React - with a separate server snapshot so the markup matches on both
 * sides of hydration.
 */
export function useLocalStorage<T>(key: string, defaultValue: T) {
  const subscribe = useMemo(
    () => (onChange: () => void) => {
      window.addEventListener(`storage:${key}`, onChange);
      window.addEventListener("storage", onChange);
      return () => {
        window.removeEventListener(`storage:${key}`, onChange);
        window.removeEventListener("storage", onChange);
      };
    },
    [key]
  );

  // The snapshot is the raw string: it is compared with Object.is, so parsing
  // here would hand React a new object every call and spin forever.
  const raw = useSyncExternalStore(
    subscribe,
    () => {
      try {
        return localStorage.getItem(key);
      } catch {
        return null;
      }
    },
    () => null
  );

  const value = useMemo<T>(() => {
    if (raw === null) return defaultValue;
    try {
      return JSON.parse(raw) as T;
    } catch {
      return defaultValue;
    }
    // defaultValue is intentionally not a dependency: callers commonly pass a
    // fresh literal, which would rebuild the value on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [raw]);

  const set = useCallback(
    (newValue: T | ((prev: T) => T)) => {
      const next =
        typeof newValue === "function" ? (newValue as (p: T) => T)(value) : newValue;
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {
        // storage unavailable (private mode, quota) - nothing to persist
      }
      window.dispatchEvent(new CustomEvent(`storage:${key}`));
    },
    [key, value]
  );

  return [value, set] as const;
}
