import "server-only";
import { randomUUID } from "node:crypto";
import { adminClient } from "./supabase/admin";

export type Bucket = "marksheets" | "attachments" | "backups";

/** Saves a file in a private bucket and returns its path. */
export async function saveFile(bucket: Bucket, folder: string, file: File | { name: string; type: string; data: Buffer }): Promise<string> {
  const name = file.name.replace(/[^\w.\-]+/g, "_").slice(-80) || "file";
  const path = `${folder}/${randomUUID()}-${name}`;
  const body = "data" in file ? file.data : Buffer.from(await file.arrayBuffer());
  const { error } = await adminClient().storage.from(bucket).upload(path, body, {
    contentType: file.type || "application/octet-stream",
    upsert: false,
  });
  if (error) throw new Error(`upload failed: ${error.message}`);
  return path;
}

/** A short-lived link to a private file (only made after the caller's access is checked). */
export async function signedUrl(bucket: Bucket, path: string, seconds = 300): Promise<string | null> {
  const { data } = await adminClient().storage.from(bucket).createSignedUrl(path, seconds);
  return data?.signedUrl ?? null;
}

export async function readFile(bucket: Bucket, path: string): Promise<Buffer | null> {
  const { data } = await adminClient().storage.from(bucket).download(path);
  return data ? Buffer.from(await data.arrayBuffer()) : null;
}
