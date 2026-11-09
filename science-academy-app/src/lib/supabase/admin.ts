import "server-only";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { serviceRoleKey, supabaseUrl } from "../env";

let admin: SupabaseClient | null = null;

/**
 * Service-role client: bypasses RLS. Only use on the server, after checking
 * who the caller is.
 */
export function adminClient(): SupabaseClient {
  admin ??= createClient(supabaseUrl(), serviceRoleKey(), {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  return admin;
}
