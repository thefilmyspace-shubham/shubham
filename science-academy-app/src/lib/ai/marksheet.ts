import "server-only";
import Anthropic from "@anthropic-ai/sdk";
import { compareMarksheet, parseMarksheetReply, type MarksheetCheck } from "./marksheet-compare";

export { compareMarksheet, parseMarksheetReply, type MarksheetCheck } from "./marksheet-compare";

const MODEL = "claude-sonnet-5-5";

const PROMPT = `You are checking a student's school marksheet (report card) for a coaching institute in India.
Read ONLY what is clearly printed. Do not guess or fill in anything.

Reply with strict JSON and nothing else:
{"readable": boolean, "name": string|null, "percentage": number|null, "note": string}

- "readable": false if the image is blurry, cut off, too dark, not a marksheet, or the student's name or the overall result cannot be read with certainty.
- "name": the student's name exactly as printed, or null if not clearly readable.
- "percentage": the overall percentage as printed (a number like 87.4). If no percentage is printed but total marks obtained and maximum marks are both clearly printed, compute it to one decimal. If neither is clear, null.
- "note": one short sentence in English. If not readable, say what is unclear and ask for a clearer photo.`;

type ImageType = "image/jpeg" | "image/png" | "image/gif" | "image/webp";
const IMAGE_TYPES: ImageType[] = ["image/jpeg", "image/png", "image/gif", "image/webp"];

/**
 * Reads a marksheet with Claude (vision) and compares it with what reception
 * typed. Never guesses: anything unclear comes back as "cant_read".
 * Without ANTHROPIC_API_KEY the result stays "pending".
 */
export async function checkMarksheet(input: {
  data: Buffer;
  mimeType: string;
  typedName: string;
  typedPercentage: number | null;
}): Promise<MarksheetCheck> {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) {
    return { result: "pending", readName: null, readPercentage: null, note: "AI check is not set up yet (no API key). Check by hand." };
  }
  const mime = input.mimeType.toLowerCase();
  let block: Anthropic.ContentBlockParam;
  if (mime === "application/pdf") {
    block = { type: "document", source: { type: "base64", media_type: "application/pdf", data: input.data.toString("base64") } };
  } else if ((IMAGE_TYPES as string[]).includes(mime)) {
    block = { type: "image", source: { type: "base64", media_type: mime as ImageType, data: input.data.toString("base64") } };
  } else {
    return {
      result: "cant_read",
      readName: null,
      readPercentage: null,
      note: "This file type cannot be read. Please upload a JPG, PNG or PDF photo of the marksheet.",
    };
  }
  if (input.data.length > 4.5 * 1024 * 1024 && mime !== "application/pdf") {
    return { result: "cant_read", readName: null, readPercentage: null, note: "Photo is too large to read. Please upload a smaller, clear photo." };
  }

  try {
    const client = new Anthropic({ apiKey: key });
    const res = await client.messages.create({
      model: MODEL,
      max_tokens: 400,
      messages: [{ role: "user", content: [block, { type: "text", text: PROMPT }] }],
    });
    const text = res.content
      .map((c) => (c.type === "text" ? c.text : ""))
      .join("")
      .trim();
    const reply = parseMarksheetReply(text);
    if (!reply) {
      return { result: "cant_read", readName: null, readPercentage: null, note: "Could not read this marksheet. Please upload a clearer photo." };
    }
    return compareMarksheet(reply, input.typedName, input.typedPercentage);
  } catch (err) {
    console.error("marksheet check failed", err);
    return { result: "pending", readName: null, readPercentage: null, note: "AI check could not run just now. Try again later or check by hand." };
  }
}
