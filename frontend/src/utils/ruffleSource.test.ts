import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SimpleRom } from "@/stores/roms";
import { getRuffleSource } from "./ruffleSource";

const mocks = vi.hoisted(() => ({ getRomZipLaunch: vi.fn() }));

vi.mock("@/services/api/rom", () => ({
  default: { getRomZipLaunch: mocks.getRomZipLaunch },
}));

vi.mock("@/utils/downloadPath", () => ({
  getDownloadPath: ({ rom }: { rom: SimpleRom }) =>
    `/api/roms/${rom.id}/content/${rom.fs_name}`,
}));

function romWith(fileName: string): SimpleRom {
  return {
    id: 5,
    fs_name: fileName,
    files: [{ id: 9, file_name: fileName }],
  } as unknown as SimpleRom;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("getRuffleSource", () => {
  it("hands Ruffle a bare SWF as it is", async () => {
    const source = await getRuffleSource(romWith("game.swf"));

    expect(source).toEqual({ url: "/api/roms/5/content/game.swf" });
    expect(mocks.getRomZipLaunch).not.toHaveBeenCalled();
  });

  it("loads a zipped game by its original URL, rewritten into the zip", async () => {
    mocks.getRomZipLaunch.mockResolvedValue({
      data: {
        path: "content/example.com/game/main.swf",
        url: "http://example.com/game/main.swf?v=2",
      },
    });

    const source = await getRuffleSource(romWith("c85ff4e3-1664775666677.zip"));

    expect(mocks.getRomZipLaunch).toHaveBeenCalledWith({ romId: 5 });
    expect(source.url).toBe("http://example.com/game/main.swf?v=2");
    expect(source.base).toBe("http://example.com/game/");
    const [pattern, replacement] = source.urlRewriteRules![0];
    expect(source.url.replace(pattern, replacement)).toBe(
      `${window.location.origin}/api/roms/5/zip/content/example.com/game/main.swf?v=2`,
    );
    expect(
      "https://cdn.example.net/assets/level1.xml".replace(pattern, replacement),
    ).toBe(
      `${window.location.origin}/api/roms/5/zip/content/cdn.example.net/assets/level1.xml`,
    );
  });

  it("fails when the zip has no known launch file", async () => {
    mocks.getRomZipLaunch.mockRejectedValue(new Error("404"));

    await expect(getRuffleSource(romWith("game.zip"))).rejects.toThrow();
  });
});
