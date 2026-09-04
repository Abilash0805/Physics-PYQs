"use client";

import { useMemo, useSyncExternalStore } from "react";

/**
 * Reads a localStorage-backed set of ids (bookmarks, solved questions).
 *
 * These values only exist in the browser, so a component cannot read them
 * while rendering on the server without causing a hydration mismatch. The
 * usual workaround - render empty, then setState inside an effect - makes
 * every such component render twice on load, which is what React's
 * set-state-in-effect rule is warning about. `useSyncExternalStore` is the
 * supported way to read an external store: it takes a separate server
 * snapshot, so the markup matches on both sides without a second render.
 */

// Snapshots are compared with Object.is, so the getter must not build a new
// Set on every call - that would never compare equal and React would loop
// forever. The raw string is the snapshot; the parsed Set is cached against
// it so repeated reads (one per question card) stay cheap and referentially
// stable.
const cache = new Map<string, { raw: string | null; set: Set<string> }>();

function setFor(key: string, raw: string | null): Set<string> {
  const hit = cache.get(key);
  if (hit && hit.raw === raw) return hit.set;
  let set: Set<string>;
  try {
    set = new Set<string>(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    set = new Set<string>();
  }
  cache.set(key, { raw, set });
  return set;
}

const EMPTY = new Set<string>();

export function useStoredSet(key: string, changeEvent: string): Set<string> {
  const subscribe = useMemo(
    () => (onChange: () => void) => {
      // the custom event covers writes from this tab, `storage` covers others
      window.addEventListener(changeEvent, onChange);
      window.addEventListener("storage", onChange);
      return () => {
        window.removeEventListener(changeEvent, onChange);
        window.removeEventListener("storage", onChange);
      };
    },
    [changeEvent]
  );

  const raw = useSyncExternalStore(
    subscribe,
    () => {
      try {
        return localStorage.getItem(key);
      } catch {
        return null;
      }
    },
    () => null // nothing is stored during server rendering
  );

  return raw === null ? EMPTY : setFor(key, raw);
}
