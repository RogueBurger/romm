import romApi from "@/services/api/rom";
import type { SimpleRom } from "@/stores/roms";
import { getDownloadPath } from "@/utils/downloadPath";

export interface RuffleSource {
  url: string;
  base?: string;
  urlRewriteRules?: Array<[RegExp, string]>;
}

/**
 * What to hand Ruffle's `load()` for a rom.
 *
 * Ruffle reads bare SWF only. A rom kept as one zip (a Flashpoint GameZIP,
 * which another app may own, so it is never unpacked) plays out of the zip:
 * Ruffle loads the launch SWF by the URL it was originally served from, and
 * every request to an original host — the launch SWF included — is rewritten
 * to the zip member stored for that URL (`content/<host>/<path>`). The game
 * sees its original URL, so sitelocks behave as they did. Relative paths
 * resolve against the SWF's own folder (`base`), as in the standalone player
 * Flashpoint runs these games in; in a page they would resolve against the
 * page's URL instead.
 */
export async function getRuffleSource(rom: SimpleRom): Promise<RuffleSource> {
  const files = rom.files ?? [];
  if (
    files.length !== 1 ||
    !files[0].file_name.toLowerCase().endsWith(".zip")
  ) {
    return { url: getDownloadPath({ rom }) };
  }

  const { data } = await romApi.getRomZipLaunch({ romId: rom.id });
  return {
    url: data.url,
    base: new URL(".", data.url).href,
    urlRewriteRules: [
      [
        /^https?:\/\/(.*)$/,
        `${window.location.origin}/api/roms/${rom.id}/zip/content/$1`,
      ],
    ],
  };
}
