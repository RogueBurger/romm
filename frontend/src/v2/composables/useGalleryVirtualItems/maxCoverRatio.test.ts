import { describe, expect, it } from "vitest";
import { computed, ref } from "vue";
import {
  MAX_COVER_RATIO,
  useGalleryVirtualItems,
  type GalleryItem,
} from "./index";

// A 100px-tall card is 200px wide at the 2:1 cap. In an 800px row with 12px
// gaps that is 3 per row — pack a 10:1 banner at its natural 1000px and each
// card takes a row of its own.
const CARD_HEIGHT = 100;
const ROW_WIDTH = 800;

function packedRows(ratio: number): Array<[number, number]> {
  const { virtualItems } = useGalleryVirtualItems({
    layout: ref("grid"),
    groupBy: ref("none"),
    total: ref(6),
    charIndex: ref({ a: 0 }),
    columns: ref(6),
    loadingInitial: computed(() => false),
    emptyMessage: ref(""),
    cardHeight: CARD_HEIGHT,
    rowWidth: ROW_WIDTH,
    gap: 12,
    ratioAt: () => ratio,
  });
  return virtualItems.value
    .filter((i): i is Extract<GalleryItem, { kind: "row" }> => i.kind === "row")
    .map((r) => [r.startPosition, r.endPosition]);
}

describe("useGalleryVirtualItems — maximum cover ratio", () => {
  it("packs a banner wider than the cap at the cap", () => {
    expect(packedRows(10)).toEqual([
      [0, 3],
      [3, 6],
    ]);
  });

  it("packs a cover exactly at the cap unchanged", () => {
    expect(packedRows(MAX_COVER_RATIO)).toEqual([
      [0, 3],
      [3, 6],
    ]);
  });

  it("leaves a cover within the cap at its natural ratio", () => {
    // 1.5:1 is 150px wide: 5 per row (5 * 150 + 4 * 12 = 798).
    expect(packedRows(1.5)).toEqual([
      [0, 5],
      [5, 6],
    ]);
  });
});
