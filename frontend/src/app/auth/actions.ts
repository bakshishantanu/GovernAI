"use server";

import { revalidatePath } from "next/cache";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { passwordPolicyError } from "@/lib/password-policy";

export async function login(formData: FormData) {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;

  if (!email || !password) {
    return { error: "Email and password are required." };
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) {
    return { error: error.message };
  }

  revalidatePath("/", "layout");
  redirect("/");
}

export async function signup(formData: FormData) {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;
  const fullName = formData.get("full_name") as string;

  if (!email || !password) {
    return { error: "Email and password are required." };
  }

  // The real enforcement point — the signup form's live checklist is a
  // convenience, not the boundary. Checked before any Supabase call, so a
  // weak password never leaves this server for their API at all.
  const policyError = passwordPolicyError(password);
  if (policyError) {
    return { error: policyError };
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: fullName || "Team Member",
        role: "agent_builder",
      },
    },
  });

  if (error) {
    return { error: error.message };
  }

  revalidatePath("/", "layout");
  return { success: "Account created! Please check your email to confirm or log in directly." };
}

export async function forgotPassword(formData: FormData) {
  const email = formData.get("email") as string;

  if (!email) {
    return { error: "Email is required." };
  }

  const headerList = await headers();
  const origin =
    headerList.get("origin") ||
    (headerList.get("host") ? `http://${headerList.get("host")}` : "http://localhost:3000");

  const supabase = await createClient();
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${origin}/auth/callback?next=/reset-password`,
  });

  // Supabase does not report whether the address has an account, and
  // neither should this: saying so either way would let someone probe for
  // which emails are registered.
  if (error) {
    return { error: error.message };
  }
  return { success: "If an account exists for that email, a reset link is on its way." };
}

export async function signInWithOAuth(provider: "google" | "github") {
  const headerList = await headers();
  const origin =
    headerList.get("origin") ||
    (headerList.get("host") ? `http://${headerList.get("host")}` : "http://localhost:3000");

  const supabase = await createClient();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: `${origin}/auth/callback?next=/`,
    },
  });

  if (error) {
    return { error: error.message };
  }

  if (data?.url) {
    return { url: data.url };
  }

  return { error: "Failed to generate authorization URL." };
}

export async function logout() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  revalidatePath("/", "layout");
  redirect("/login");
}
