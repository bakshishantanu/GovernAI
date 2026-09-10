/**
 * The password complexity policy for new accounts: at least 8 characters,
 * one uppercase letter, one lowercase letter, one digit, one special
 * character. Shared between the server action (the real enforcement point —
 * a client check alone can always be bypassed) and the signup form's live
 * checklist, so the two can never silently drift apart.
 */

export type PasswordRequirement = {
  id: string;
  label: string;
  test: (password: string) => boolean;
};

export const PASSWORD_REQUIREMENTS: PasswordRequirement[] = [
  { id: "length", label: "At least 8 characters", test: (pw) => pw.length >= 8 },
  { id: "upper", label: "One uppercase letter", test: (pw) => /[A-Z]/.test(pw) },
  { id: "lower", label: "One lowercase letter", test: (pw) => /[a-z]/.test(pw) },
  { id: "number", label: "One number", test: (pw) => /[0-9]/.test(pw) },
  {
    id: "special",
    label: "One special character",
    // Deliberately broad (anything not a letter/digit), rather than one
    // fixed set of symbols, so a legitimate special character never gets
    // silently rejected because it wasn't on a hand-picked list.
    test: (pw) => /[^A-Za-z0-9]/.test(pw),
  },
];

export function unmetPasswordRequirements(password: string): PasswordRequirement[] {
  return PASSWORD_REQUIREMENTS.filter((req) => !req.test(password));
}

export function isPasswordValid(password: string): boolean {
  return unmetPasswordRequirements(password).length === 0;
}

/** One combined message for a server-side error response. */
export function passwordPolicyError(password: string): string | null {
  const unmet = unmetPasswordRequirements(password);
  if (unmet.length === 0) return null;
  return `Password must have: ${unmet.map((r) => r.label.toLowerCase()).join(", ")}.`;
}
